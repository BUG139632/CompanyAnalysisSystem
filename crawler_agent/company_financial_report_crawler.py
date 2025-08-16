#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公司官网财报数据爬取器
实现完整的公司官网财报数据爬取流程
"""

import asyncio
import json
import logging
import time
import re
import os
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urljoin, urlparse, quote
from datetime import datetime
import aiohttp
from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from crawl4ai.models import CrawlResultContainer
import yaml
from bs4 import BeautifulSoup
import aiofiles
import mimetypes

# 新增：加载财报栏目关键词和路径特征
FINANCIAL_KEYWORDS = [
    "财报", "公告", "投资者关系", "信息披露", "年度报告", "定期报告", "财务信息", "年报", "半年报", "季报", "报告", "Disclosure", "Investor Relations", "Annual Report", "Financial Report", "定期公告", "财务摘要"
]
FINANCIAL_PATH_PATTERNS = [
    "/investor", "/ir", "/disclosure", "/report", "/finance", "/公告", "/信息披露", "/财务", "/报告"
]

def load_financial_keywords():
    config_path = os.path.join(os.path.dirname(__file__), 'financial_keywords.yaml')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config.get('keywords', FINANCIAL_KEYWORDS), config.get('path_patterns', FINANCIAL_PATH_PATTERNS)
    return FINANCIAL_KEYWORDS, FINANCIAL_PATH_PATTERNS

FINANCIAL_KEYWORDS, FINANCIAL_PATH_PATTERNS = load_financial_keywords()

# 设置日志
def setup_logging():
    """设置日志配置"""
    # 日志目录：可由环境变量 LOG_DIR 指定，默认为 /app/logs（容器挂载点）
    log_dir = os.getenv('LOG_DIR', '/app/logs')
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
        except PermissionError:
            # 回退到 /tmp，保证容器只读层也能写日志
            log_dir = '/tmp/company_crawler_logs'
            os.makedirs(log_dir, exist_ok=True)
    
    # 清空日志文件
    log_file = os.path.join(log_dir, "company_website_crawler.log")
    with open(log_file, 'w', encoding='utf-8') as f:
        f.truncate(0)
    
    # 获取logger
    logger = logging.getLogger(__name__)
    
    # 清除现有的处理器，避免重复添加
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 设置日志级别
    logger.setLevel(logging.INFO)
    
    # 文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 格式化器
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# 初始化日志
logger = setup_logging()

class CompanyFinancialReportCrawler:
    """公司官网财报数据爬取器（专用于官网财报爬取）"""
    
    def __init__(self, config_path: str = "crawl4ai_config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.crawler = None
        self.llm_strategy = None
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}
    
    async def initialize(self):
        """初始化爬虫和LLM"""
        try:
            # 初始化Crawl4AI爬虫
            llm_config = self.config.get('llm', {})
            self.crawler = AsyncWebCrawler(
                verbose=False,
                headless=True,
                browser_type="chrome"
            )

            # 官方推荐方式初始化LLM策略（直接传llm_provider等参数）
            self.llm_strategy = LLMExtractionStrategy(
                llm_provider=llm_config.get('provider', 'google/gemini-2.0-flash'),
                llm_api_key=llm_config.get('api_key'),
                llm_model=llm_config.get('model', 'gemini-2.0-flash'),
                max_tokens=llm_config.get('max_tokens', 4000),
                temperature=llm_config.get('temperature', 0.1),
                system_prompt=llm_config.get('system_prompt', ''),
                timeout=llm_config.get('timeout', 30)
            )

            logger.info("Company website crawler initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize crawler: {e}")
            raise
    
    async def close(self):
        """关闭爬虫"""
        if self.crawler:
            await self.crawler.close()
    
    async def crawl_company_financial_reports(self, company: dict, data_type: str = "财务报表", max_depth: int = 3, timeout: int = 60) -> dict:
        """
        主流程：递归查找财报/公告栏目，若递归已收集到附件则直接下载，否则进入栏目页面抓取和下载。
        data_type: "财务报表" 或 "公司公告"
        max_depth: 递归查找栏目最大深度
        timeout: 递归查找栏目超时时间（秒）
        """
        company_name = company.get('company_name')
        if not company_name:
            logger.error("公司信息缺少 company_name 字段，无法继续")
            return {"error": "缺少公司名称 company_name"}
        logger.info(f"开始爬取 {company_name} 的官网{data_type}数据")
        # 获取公司官网
        website_url = await self._search_company_website(str(company_name))
        if not website_url:
            logger.error(f"未找到 {company_name} 的官网")
            return {"company_name": company_name, "error": "未找到官网"}
        homepage_links = await self._crawl_homepage_links(website_url)
        collected_files = []
        # 限制递归查找栏目部分的超时时间（财务报表和公司公告都适用）
        try:
            financial_page_url = await asyncio.wait_for(
                self._find_financial_page(
                    website_url, homepage_links, str(company_name),
                    collected_files=collected_files, max_reports=5, max_depth=max_depth
                ),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"官网递归查找栏目超时（{timeout}秒），已强制中断")
            financial_page_url = None
        if collected_files:
            logger.info(f"递归已收集到 {len(collected_files)} 个附件，直接下载")
            # 修改保存目录
            if data_type == "公司公告":
                save_dir = "data/raw/announcements/website_announcements"
            else:
                save_dir = "data/raw/financial_reports/website_financial_reports"
            downloaded = await self._download_limited_reports(collected_files, save_dir=save_dir, max_count=5, data_type=data_type)
            return {
                "company_name": company_name,
                "website_url": website_url,
                "financial_reports": downloaded,
                "status": "success"
            }
        elif financial_page_url:
            logger.info(f"未在递归中收集到附件，进入栏目页面抓取和下载: {financial_page_url}")
            # 修改保存目录
            if data_type == "公司公告":
                save_dir = "data/raw/announcements/website_announcements"
            else:
                save_dir = "data/raw/financial_reports/website_financial_reports"
            downloaded = await self._crawl_financial_reports(financial_page_url, save_dir=save_dir, max_reports=5, data_type=data_type)
            return {
                "company_name": company_name,
                "website_url": website_url,
                "financial_page_url": financial_page_url,
                "financial_reports": downloaded,
                "status": "success"
            }
        else:
            logger.warning(f"未找到{data_type}栏目或附件")
            return {
                "company_name": company_name,
                "website_url": website_url,
                "error": f"未找到{data_type}栏目或附件"
            }
    
    async def _search_company_website(self, company_name: str) -> Optional[str]:
        """
        使用Google搜索公司官网
        
        Args:
            company_name: 公司名称
        
        Returns:
            公司官网URL或None
        """
        logger.info(f"搜索 {company_name} 的官网")
        
        try:
            # 构建搜索关键词 - 使用"公司名+官网"格式
            search_keywords = [
                f'{company_name} 官网',
                f'{company_name} 官方网站',
                f'{company_name} 投资者关系',
                f'{company_name} 公司官网'
            ]
            
            # 直接爬取Google搜索结果页面
            search_results = await self._crawl_google_search_results(company_name)
            
            # 使用LLM分析搜索结果，确定最可能的官网
            website_url = await self._analyze_website_search_results(company_name, search_results)
            
            return website_url
            
        except Exception as e:
            logger.error(f"搜索公司官网失败: {e}")
            return None
    
    async def _crawl_google_search_results(self, company_name: str) -> List[Dict]:
        """爬取Google搜索结果"""
        logger.info(f"开始爬取Google搜索结果: {company_name}")
        all_results = []
        
        # 构建搜索关键词
        search_keywords = [
            f'{company_name} 官网',
            f'{company_name} 官方网站',
            f'{company_name} 投资者关系',
            f'{company_name} 公司官网'
        ]
        
        for keyword in search_keywords:
            try:
                # 构建Google搜索URL
                search_url = f"https://www.google.com/search?q={quote(keyword)}&hl=zh-CN&num=10"
                logger.info(f"爬取搜索页面: {search_url}")
                
                # 使用Crawl4AI爬取搜索结果页面
                result = await self.crawler.arun(search_url)
                
                # 解析结果 - 修正raw_content访问
                html_content = None
                if result and hasattr(result, 'html') and result.html:
                    html_content = result.html
                elif result and hasattr(result, 'extracted_content') and result.extracted_content:
                    html_content = result.extracted_content
                elif isinstance(result, dict) and 'html' in result:
                    html_content = result['html']
                elif isinstance(result, dict) and 'extracted_content' in result:
                    html_content = result['extracted_content']
                else:
                    logger.error("未能从CrawlResult中提取到HTML内容")
                    continue
                
                # 提取搜索结果
                results = self._extract_search_results_from_html(html_content)
                logger.info(f"从HTML中提取到 {len(results)} 个搜索结果")
                
                # 使用正则表达式提取链接
                regex_results = self._extract_links_from_html(html_content)
                logger.info(f"使用正则表达式提取到 {len(regex_results)} 个结果")
                
                # 合并结果
                all_results.extend(results)
                all_results.extend(regex_results)
                
            except Exception as e:
                logger.error(f"爬取Google搜索结果失败: {e}")
                continue
        
        # 去重
        unique_results = []
        seen_urls = set()
        for result in all_results:
            url = result.get('url', '')
            if url and url not in seen_urls:
                unique_results.append(result)
                seen_urls.add(url)
        
        logger.info(f"总共提取到 {len(unique_results)} 个搜索结果")
        return unique_results
    
    def _extract_search_results_from_html(self, html_content: str) -> List[Dict]:
        """从Google搜索结果HTML中提取搜索结果（优化版）"""
        results = []
        try:
            import re
            # 多种Google搜索结果匹配模式
            patterns = [
                r'<div[^>]*class="[^"]*g[^"]*"[^>]*>.*?<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>.*?<div[^>]*class="[^"]*VwiC3b[^"]*"[^>]*>([^<]*)</div>',
                r'<a[^>]*href="([^"]*)"[^>]*class="[^"]*LC20lb[^"]*"[^>]*>([^<]*)</a>',
                r'<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>',
                r'<a[^>]*data-ved[^>]*href="([^"]*)"[^>]*>([^<]*)</a>'
            ]
            for pattern in patterns:
                matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
                for match in matches:
                    if len(match) >= 2:
                        url = match[0]
                        title = match[1].strip()
                        # 放宽过滤条件：允许title更短，不过滤.com.cn等
                        if (url.startswith('http') and 
                            'google.com' not in url and 
                            'youtube.com' not in url and
                            not title.startswith('http')):
                            if not any(r['url'] == url for r in results):
                                results.append({
                                    'title': title,
                                    'url': url,
                                    'snippet': f'搜索结果: {title}'
                                })
                if results:
                    break
            if not results:
                all_links = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', html_content, re.IGNORECASE)
                for url, title in all_links:
                    title = title.strip()
                    if (url.startswith('http') and 
                        'google.com' not in url and 
                        'youtube.com' not in url and
                        not title.startswith('http')):
                        if not any(r['url'] == url for r in results):
                            results.append({
                                'title': title,
                                'url': url,
                                'snippet': f'搜索结果: {title}'
                            })
            logger.info(f"从HTML中提取到 {len(results)} 个搜索结果")
            return results[:10]
        except Exception as e:
            logger.error(f"从HTML提取搜索结果失败: {e}")
            return []
    
    async def _mock_google_search(self, company_name: str, keywords: List[str]) -> List[Dict]:
        """模拟Google搜索结果"""
        # 实际实现时应该调用Google Custom Search API
        return [
            {
                'title': f'{company_name} - 官方网站',
                'url': f'https://www.{company_name.lower().replace(" ", "")}.com',
                'snippet': f'{company_name}官方网站，提供公司介绍、投资者关系、财务报告等信息'
            },
            {
                'title': f'{company_name} 投资者关系',
                'url': f'https://ir.{company_name.lower().replace(" ", "")}.com',
                'snippet': f'{company_name}投资者关系页面，包含财务报告、公司公告等信息'
            }
        ]
    
    async def _analyze_website_search_results(self, company_name: str, search_results: List[Dict]) -> Optional[str]:
        """使用LLM分析搜索结果，确定最可能的官网"""
        try:
            logger.info(f"传递给LLM的search_results: {json.dumps(search_results, ensure_ascii=False, indent=2)}")
            prompt = f"""
            你是一名专业的互联网信息分析助手。请根据以下{company_name}的Google搜索结果，判断最可能的公司官网URL。
            
            搜索结果:
            {json.dumps(search_results, ensure_ascii=False, indent=2)}
            
            你的判断标准包括：
            1. URL是否包含公司名称拼音、英文或常用缩写
            2. 标题或摘要是否明确表示是官方网站、公司主页、投资者关系等
            3. URL域名是否为主流公司官网域名（如.com/.cn/.com.cn等）
            4. 排除第三方平台、百科、新闻、招聘、社交媒体等非官网
            5. 如果只有一个结果也请直接返回该URL
            
            请只输出最可能的官网URL，且只输出一行URL，不要输出任何其他内容。
            """
            
            # 使用LLM分析
            result = await self._call_llm(prompt)
            logger.info(f"LLM原始输出：{result}")
            
            # 只提取URL
            url_match = re.search(r'https?://[^\s"\']+', result)
            return url_match.group(0) if url_match else None
                
        except Exception as e:
            logger.error(f"分析搜索结果失败: {e}")
            # 如果LLM分析失败，返回第一个结果的URL
            return search_results[0]['url'] if search_results else None
    
    async def _crawl_homepage_links(self, url: str) -> list:
        """
        抓取首页所有可点击元素（a、button、div、span等），并分析文本，优先提取包含“投资者关系”等关键词的元素。
        """
        logger.info(f"爬取首页链接: {url}")
        html = await self._fetch_html(url)
        if not html:
            logger.warning(f"无法获取 {url} 的HTML内容")
            return []
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        # 1. 普通a标签
        for a in soup.find_all('a'):
            text = a.get_text(strip=True)
            href = a.get('href')
            if href and not href.startswith('javascript'):
                links.append({'text': text, 'url': urljoin(url, href), 'title': a.get('title', ''), 'type': 'a'})
        # 2. 其他可点击元素
        clickable_tags = ['button', 'div', 'span', 'li']
        keywords = ["投资者关系", "investor", "信息披露", "公告", "财务", "报告"]
        for tag in soup.find_all(clickable_tags):
            tag_text = tag.get_text(strip=True)
            if any(kw in tag_text for kw in keywords):
                # 尝试找onclick、data-url、href等属性
                url_candidate = tag.get('onclick') or tag.get('data-url') or tag.get('href')
                # 解析onclick中的URL（如location.href='xxx'）
                if url_candidate and 'location.href' in url_candidate:
                    import re
                    m = re.search(r"location.href=['\"](.*?)['\"]", url_candidate)
                    if m:
                        url_candidate = m.group(1)
                if url_candidate:
                    full_url = urljoin(url, url_candidate)
                    links.append({'text': tag_text, 'url': full_url, 'title': tag.get('title', ''), 'type': tag.name})
        # 3. 去重
        seen = set()
        unique_links = []
        for link in links:
            key = (link['text'], link['url'])
            if key not in seen:
                seen.add(key)
                unique_links.append(link)
        logger.info(f"从首页提取到 {len(unique_links)} 个链接（含可点击元素）")
        return unique_links
    
    async def _fetch_html(self, url: str) -> Optional[str]:
        """
        使用aiohttp获取网页HTML内容。
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        logger.warning(f"Failed to fetch HTML from {url}: Status {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error fetching HTML from {url}: {e}")
            return None
    
    def _extract_links_from_html(self, html_content: str) -> List[Dict]:
        """从HTML中提取链接"""
        links = []
        # 简单的正则表达式提取链接
        link_pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]*)</a>'
        matches = re.findall(link_pattern, html_content)
        
        for url, text in matches:
            if url.startswith('http'):
                links.append({
                    'url': url,
                    'text': text.strip(),
                    'title': text.strip(),
                    'type': 'content'
                })
        
        return links
    
    def _is_internal_link(self, url, main_domain):
        try:
            return main_domain in urlparse(url).netloc
        except Exception:
            return False

    async def _find_financial_page(self, website_url: str, homepage_links: list, company_name: str, depth: int = 1, max_depth: int = 3, collected_files: Optional[list] = None, max_reports: int = 5) -> Optional[str]:
        """
        只递归官网主域名下的内链，并优先递归“投资者关系”等栏目，递归到“财务报告”栏目后立即返回。
        遇到PDF/Excel等附件链接只收集不递归。累计到max_reports个附件后立即停止。
        """
        if collected_files is None:
            collected_files = []
        logger.info(f"查找 {company_name} 的财报页面，当前递归深度: {depth}")
        if len(collected_files) >= max_reports:
            logger.info(f"已累计识别到{max_reports}个财报附件，停止递归。")
            return None
        if depth > max_depth:
            logger.warning(f"递归深度超过最大值({max_depth})，停止递归。")
            return None
        main_domain = urlparse(website_url).netloc
        # 只递归主域名下的内链
        internal_links = [link for link in homepage_links if self._is_internal_link(link.get("url", ""), main_domain)]
        # 先收集所有PDF/Excel等附件链接
        for link in internal_links:
            url = link.get("url", "")
            if url.lower().endswith((".pdf", ".xls", ".xlsx", ".csv")):
                if len(collected_files) < max_reports:
                    logger.info(f"识别到财报附件: {url}")
                    collected_files.append(link)
                if len(collected_files) >= max_reports:
                    logger.info(f"已累计识别到{max_reports}个财报附件，停止递归。")
                    return None
        # 过滤掉附件链接，只递归HTML页面
        html_links = [link for link in internal_links if not link.get("url", "").lower().endswith((".pdf", ".xls", ".xlsx", ".csv"))]
        # 优先递归“投资者关系”等栏目
        priority_keywords = ["投资者关系", "信息披露", "公告", "财务报告"]
        # LLM辅助判断：用LLM分析所有html_links，优先递归LLM判断的最优栏目
        llm_best_url = None
        try:
            llm_best_url = await self._analyze_financial_links(company_name, html_links, website_url)
        except Exception as e:
            logger.warning(f"LLM辅助判断栏目失败: {e}")
        if llm_best_url and llm_best_url.startswith("http"):
            logger.info(f"[LLM优先] 递归LLM判断的最优栏目: {llm_best_url}")
            sub_links = await self._crawl_homepage_links(llm_best_url)
            result = await self._find_financial_page(website_url, sub_links, company_name, depth+1, max_depth, collected_files, max_reports)
            if result:
                return result
            if len(collected_files) >= max_reports:
                logger.info(f"已累计识别到{max_reports}个财报附件，停止递归。")
                return None
        for kw in priority_keywords:
            for link in html_links:
                if kw in link.get("text", "") or kw in link.get("title", ""):
                    logger.info(f"优先递归栏目: {kw} {link.get('url')}")
                    sub_links = await self._crawl_homepage_links(link.get("url"))
                    result = await self._find_financial_page(website_url, sub_links, company_name, depth+1, max_depth, collected_files, max_reports)
                    if result:
                        return result
                    if len(collected_files) >= max_reports:
                        logger.info(f"已累计识别到{max_reports}个财报附件，停止递归。")
                        return None
        # 递归其他栏目
        for link in html_links:
            sub_links = await self._crawl_homepage_links(link.get("url"))
            result = await self._find_financial_page(website_url, sub_links, company_name, depth+1, max_depth, collected_files, max_reports)
            if result:
                return result
            if len(collected_files) >= max_reports:
                logger.info(f"已累计识别到{max_reports}个财报附件，停止递归。")
                return None
        # 如果收集到附件，说明已到达目标栏目
        if collected_files:
            logger.info(f"递归收集到 {len(collected_files)} 个财报附件链接。")
            return None  # 不再递归，主流程可用collected_files
        return None
    
    async def _analyze_financial_links(self, company_name: str, potential_links: list, website_url: str) -> Optional[str]:
        """
        用LLM结构化prompt判断最优财报栏目
        """
        prompt = f"""
你是一名专业的互联网信息分析助手。请根据下列{company_name}公司官网的栏目链接，判断最有可能包含财务报告/公告/定期报告/信息披露内容的栏目URL。

每个栏目信息如下：
"""
        for i, link in enumerate(potential_links):
            prompt += f"\n[{i+1}] 文本: {link.get('text', '')} | 标题: {link.get('title', '')} | URL: {link.get('url', '')}"
        prompt += "\n\n请只输出最有可能的栏目URL（只输出一行URL，不要输出任何其他内容）。"
        # 仅在未隐藏思考时输出prompt日志
        if os.environ.get("HIDE_THOUGHTS") != "1":
            logger.info(f"[LLM财报栏目判断] prompt: {prompt}")
        url = await self._call_llm(prompt)
        url = url.strip().split('\n')[0]
        # 简单校验
        if url.startswith("http"):
            logger.info(f"LLM判断最优财报栏目: {url}")
            return url
        logger.warning(f"LLM未能返回有效URL: {url}")
        return None
    
    async def _crawl_financial_reports_page(self, financial_page_url: str, company_name: str) -> List[Dict]:
        """
        进入财报页面，点击、滚动、翻页，提取财报数据
        
        Args:
            financial_page_url: 财报页面URL
            company_name: 公司名称
        
        Returns:
            财报数据列表
        """
        logger.info(f"爬取财报页面: {financial_page_url}")
        
        try:
            # 使用Crawl4AI爬取财报页面
            result = await self.crawler.arun(
                financial_page_url,
                extraction_strategy=self.llm_strategy,
                extraction_prompt=f"""
                请提取{company_name}的财务报告信息，包括：
                
                1. 报告列表（年报、季报、半年报等）
                2. 每份报告的详细信息：
                   - 报告标题
                   - 报告日期
                   - 报告类型（年报/季报/半年报）
                   - 下载链接
                   - 报告摘要
                
                3. 财务数据（如果页面包含）：
                   - 营业收入
                   - 净利润
                   - 总资产
                   - 负债率等关键指标
                
                请以JSON格式返回：
                {{
                    "reports": [
                        {{
                            "title": "报告标题",
                            "date": "报告日期",
                            "type": "报告类型",
                            "download_url": "下载链接",
                            "summary": "报告摘要"
                        }}
                    ],
                    "financial_data": {{
                        "revenue": "营业收入",
                        "net_profit": "净利润",
                        "total_assets": "总资产",
                        "debt_ratio": "负债率"
                    }}
                }}
                """
            )
            
            # 解析结果
            if result and hasattr(result, 'extracted_content'):
                try:
                    content = json.loads(result.extracted_content)
                    return content.get('reports', [])
                except:
                    logger.warning("LLM返回的结果不是有效的JSON格式")
                    return []
            
            return []
            
        except Exception as e:
            logger.error(f"爬取财报页面失败: {e}")
            return []
    
    async def _call_llm(self, prompt: str) -> str:
        """调用LLM API - 使用common/llm_base_agent.py里的Gemini API"""
        try:
            # 添加项目根目录到Python路径
            import sys
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            
            # 使用common/llm_base_agent.py里的Gemini API
            from common.llm_base_agent import LLMBaseAgent
            
            # 创建临时LLM代理实例
            llm_agent = LLMBaseAgent()
            
            # 直接调用Gemini API
            result = llm_agent.llm_generate(prompt)
            
            if result:
                return result
            else:
                logger.error("Gemini API调用返回空结果")
                return ""
                
        except Exception as e:
            logger.error(f"调用Gemini API失败: {e}")
            return ""
    
    async def _download_file(self, url: str, save_dir: str) -> Optional[str]:
        """
        下载PDF/Excel等附件到本地指定目录，返回本地文件路径。
        """
        os.makedirs(save_dir, exist_ok=True)
        filename = os.path.basename(url.split('?')[0])
        save_path = os.path.join(save_dir, filename)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        async with aiofiles.open(save_path, 'wb') as f:
                            await f.write(await resp.read())
                        logger.info(f"下载成功: {url} -> {save_path}")
                        return save_path
                    else:
                        logger.warning(f"下载失败: {url}, 状态码: {resp.status}")
        except Exception as e:
            logger.error(f"下载文件异常: {url}, 错误: {e}")
        return None

    async def _extract_and_download_attachments(self, html: str, base_url: str, save_dir: str) -> list:
        """
        识别页面中的PDF/Excel等财报附件链接并下载，返回本地文件路径列表。
        """
        soup = BeautifulSoup(html, 'html.parser')
        attachments = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            file_url = urljoin(base_url, href)
            # 识别常见财报文件类型
            if any(file_url.lower().endswith(ext) for ext in ['.pdf', '.xls', '.xlsx', '.csv']):
                local_path = await self._download_file(file_url, save_dir)
                if local_path:
                    attachments.append({'url': file_url, 'local_path': local_path, 'text': a.get_text(strip=True)})
        logger.info(f"共识别并下载 {len(attachments)} 个财报附件")
        return attachments

    async def _analyze_financial_links_with_llm(self, links: list, company_name: str) -> Optional[list]:
        """
        用LLM分析所有候选链接，返回最有可能的财报附件列表（title、url、type）。
        """
        prompt = f"""
你是一名专业的互联网信息分析助手。请根据下列{company_name}官网财报栏目下的所有链接，判断哪些是财报附件（如PDF、Excel等），并输出如下格式的JSON数组，不要输出任何其他内容：
[
  {{"title": "2023年年度报告", "url": "https://...", "type": "pdf"}},
  ...
]
只输出JSON数组，不要输出任何解释或自然语言。
候选链接：
{links}
"""
        llm_result = await self._call_llm(prompt)
        # 尝试解析JSON
        try:
            import json
            result = json.loads(llm_result.strip())
            if isinstance(result, list):
                return result
        except Exception as e:
            logger.warning(f"LLM返回的结果不是有效的JSON格式，将降级为直接提取页面所有PDF/Excel链接: {e}")
            return None
        return []

    def _extract_year(self, text: str) -> int:
        """从文本中提取年份，优先匹配2020-2029，未匹配返回0"""
        match = re.search(r"20[2-9][0-9]", text)
        return int(match.group()) if match else 0

    async def _download_limited_reports(self, links: list, save_dir: str = 'data/raw/financial_reports/website_financial_reports', max_count: int = 5, data_type: str = "财务报表") -> list:
        """
        下载有限数量的报告（如PDF），按年份排序，最多max_count个。
        """
        if data_type == "公司公告":
            filtered_links = [l for l in links if self._extract_year(l['url'] + l.get('title', '')) >= 2025]
            logger.info(f"公司公告模式，仅下载2025年及以后的公告，共{len(filtered_links)}个。")
            links_to_download = filtered_links
        else:
            # 财报逻辑：近五年或max_count个
            links_sorted = sorted(links, key=lambda l: self._extract_year(l['url'] + l.get('title', '')), reverse=True)
            # 限制为最多15个PDF
            max_count = min(max_count, 15)
            links_to_download = links_sorted[:max_count]
            logger.info(f"财报模式，限制下载近五年或最多{max_count}个财报附件，实际下载: {[l['url'] for l in links_to_download]}")
        downloaded = []
        for link in links_to_download:
            logger.info(f"准备下载附件: {link['url']}")
            file_path = await self._download_file(link['url'], save_dir)
            if file_path:
                logger.info(f"下载成功: {file_path}")
                downloaded.append({**link, 'local_path': file_path})
            else:
                logger.warning(f"下载失败: {link['url']}")
        return downloaded

    async def _crawl_financial_reports(self, financial_page_url: str, save_dir: str = 'data/raw/financial_reports/website_financial_reports', max_reports: int = 5, data_type: str = "财务报表") -> list:
        """
        进入财报/公告栏目页面，按数据类型决定下载逻辑。
        """
        logger.info(f"爬取栏目页面: {financial_page_url}")
        html = await self._fetch_html(financial_page_url)
        if not html:
            logger.warning(f"无法获取栏目页面HTML: {financial_page_url}")
            return []
        # 1. 提取所有a标签PDF/Excel链接
        soup = BeautifulSoup(html, 'html.parser')
        all_links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            file_url = urljoin(financial_page_url, href)
            if any(file_url.lower().endswith(ext) for ext in ['.pdf', '.xls', '.xlsx', '.csv']):
                link_info = {'title': a.get_text(strip=True), 'url': file_url, 'type': file_url.split('.')[-1]}
                all_links.append(link_info)
        logger.info(f"栏目页面共识别到 {len(all_links)} 个PDF/Excel等附件链接。")
        # 2. 按数据类型决定下载逻辑
        downloaded = await self._download_limited_reports(all_links, save_dir, max_count=max_reports, data_type=data_type)
        return downloaded
    
    async def batch_crawl_companies(self, companies: List[Dict]) -> List[Dict]:
        """
        批量爬取多个公司的财报数据
        
        Args:
            companies: 公司列表，每个公司包含name和code
        
        Returns:
            爬取结果列表
        """
        logger.info(f"开始批量爬取 {len(companies)} 个公司的财报数据")
        
        results = []
        for company in companies:
            company_name = company.get('name')
            company_code = company.get('code')
            
            if not company_name:
                continue
            
            logger.info(f"爬取公司: {company_name}")
            result = await self.crawl_company_financial_reports(company)
            results.append(result)
            
            # 添加延迟避免被封
            await asyncio.sleep(2)
        
        return results

# 测试函数
async def test_company_website_crawler():
    """测试公司官网爬取器"""
    crawler = CompanyFinancialReportCrawler()
    
    try:
        await crawler.initialize()
        
        # 测试单个公司
        result = await crawler.crawl_company_financial_reports({"company_name": "贵州茅台", "code": "600519"})
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        # 测试批量爬取
        companies = [
            {"company_name": "贵州茅台", "code": "600519"},
            {"company_name": "平安银行", "code": "000001"}
        ]
        batch_results = await crawler.batch_crawl_companies(companies)
        print(json.dumps(batch_results, ensure_ascii=False, indent=2))
        
    finally:
        await crawler.close()

if __name__ == "__main__":
    asyncio.run(test_company_website_crawler()) 