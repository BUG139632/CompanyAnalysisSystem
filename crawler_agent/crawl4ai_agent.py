import json
import logging
import os
import sys
from urllib.parse import quote
from typing import Dict, List, Optional, Any

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from crawl4ai.extraction_strategy import LLMExtractionStrategy
from common.base_agent import BaseAgent


class Crawl4AIAgent(BaseAgent):
    """
    基于Crawl4AI的爬虫代理，支持智能URL生成和搜索关键词生成
    """
    
    def __init__(self, config_path=None, agent_name=None):
        super().__init__(config_path, agent_name or "Crawl4AIAgent")
        
        # 从配置文件加载配置
        self.load_config_from_file()
        
        # 初始化Crawl4AI爬虫
        crawler_config = self.config.get('crawler', {})
        self.crawler = AsyncWebCrawler(
            verbose=crawler_config.get('verbose', True),
            headless=crawler_config.get('headless', True),
            browser_type=crawler_config.get('browser_type', 'chromium')
        )
        
        # 从配置加载URL模板
        self.url_templates = {}
        self.site_mapping = {}
        data_sources = self.config.get('data_sources', {})
        for source_name, source_config in data_sources.items():
            self.url_templates[source_name] = source_config.get('templates', {})
            self.site_mapping[source_name] = source_config.get('domain', '')
        
        # 从配置加载搜索关键词模板
        self.search_keywords_templates = self.config.get('search_keywords', {})
    
    def load_config_from_file(self):
        """
        从配置文件加载配置
        """
        # 如果没有指定配置文件，使用默认配置文件
        if not hasattr(self, 'config_path') or not self.config_path:
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.config_path = os.path.join(current_dir, 'crawl4ai_config.yaml')
        
        # 如果配置文件存在，加载配置
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                import yaml
                file_config = yaml.safe_load(f)
                # 合并配置
                if hasattr(self, 'config'):
                    self.config.update(file_config)
                else:
                    self.config = file_config
        else:
            self.logger.warning(f"配置文件不存在: {self.config_path}")
    
    def generate_search_keywords(self, company_name: str, company_code: str, data_type: str) -> List[str]:
        """
        生成适合数据源的中文搜索关键词
        """
        keywords = []
        
        # 使用模板生成关键词
        if data_type in self.search_keywords_templates:
            template_keywords = self.search_keywords_templates[data_type]
            for template in template_keywords:
                keyword = template.format(公司名称=company_name, 公司代码=company_code)
                keywords.append(keyword)
        
        # 添加一些通用关键词
        if data_type == "财务报表":
            keywords.extend([f"{company_name} 资产负债表", f"{company_name} 利润表", f"{company_name} 现金流量表"])
        elif data_type == "公司公告":
            keywords.extend([f"{company_name} 临时公告", f"{company_name} 定期报告"])
        elif data_type == "行业研报":
            keywords.extend([f"{company_name} 投资评级", f"{company_name} 目标价"])
        
        # 去重并限制数量
        unique_keywords = list(dict.fromkeys(keywords))  # 保持顺序的去重
        return unique_keywords[:5]  # 最多返回5个关键词
    
    def build_url_from_template(self, source: str, data_type: str, company_code: str, keywords: List[str] = None) -> Optional[str]:
        """
        从URL模板构建完整URL
        """
        try:
            template = self.url_templates.get(source, {}).get(data_type)
            if not template:
                return None
            
            # 根据数据类型选择合适的关键词
            if data_type == "财务报表":
                url = template.format(code=company_code, keyword="")
            elif data_type == "公司公告":
                url = template.format(code=company_code, keyword="")
            elif data_type == "行业研报":
                keyword = keywords[0] if keywords else ""
                url = template.format(code=company_code, keyword=keyword)
            else:
                keyword = keywords[0] if keywords else ""
                url = template.format(code=company_code, keyword=keyword)
            
            self.logger.info(f"[URL模板] 构建{data_type} URL: {url}")
            return url
            
        except Exception as e:
            self.logger.error(f"[URL模板] 构建失败: {e}")
            return None
    
    def generate_google_site_search_url(self, source: str, keywords: List[str]) -> Optional[str]:
        """
        生成Google site搜索URL
        """
        try:
            site_domain = self.site_mapping.get(source)
            if not site_domain or not keywords:
                return None
                
            keyword = keywords[0]
            search_url = f"https://www.google.com/search?q=site:{site_domain}+{quote(keyword)}"
            
            self.logger.info(f"[Google搜索] 生成搜索URL: {search_url}")
            return search_url
            
        except Exception as e:
            self.logger.error(f"[Google搜索] 失败: {e}")
            return None
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理爬虫请求，生成URL和搜索关键词
        """
        try:
            company_name = data.get("公司名称", "")
            company_code = data.get("公司代码", "")
            source = data.get("数据源", "")
            data_type = data.get("数据类型", "")
            
            self.logger.info(f"处理请求: {company_name} - {source} - {data_type}")
            
            # 生成搜索关键词
            search_keywords = self.generate_search_keywords(company_name, company_code, data_type)
            
            # 尝试构建URL
            url = None
            
            # 1. 优先使用URL模板
            if source in self.url_templates:
                url = self.build_url_from_template(source, data_type, company_code, search_keywords)
            
            # 2. 如果是公司官网，使用Google site搜索
            if not url and "官网" in source:
                url = self.generate_google_site_search_url(source, search_keywords)
            
            # 3. 如果还是没有URL，但有搜索关键词，返回搜索关键词
            if not url and search_keywords:
                # 对于没有URL模板的数据源，返回null URL，但提供搜索关键词
                pass
            
            # 构建返回结果
            result = {
                "company_name": company_name,
                "source": source,
                "data_type": data_type,
                "url": url,
                "search_keywords": search_keywords if not url else None
            }
            
            self.logger.info(f"生成结果: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"处理失败: {e}")
            return {
                "company_name": data.get("公司名称", ""),
                "source": data.get("数据源", ""),
                "data_type": data.get("数据类型", ""),
                "url": None,
                "search_keywords": None
            }
    
    async def crawl_url(self, url: str, extraction_strategy: Optional[LLMExtractionStrategy] = None) -> Dict[str, Any]:
        """
        使用Crawl4AI爬取指定URL
        """
        try:
            if not url:
                return {"error": "URL为空"}
            
            self.logger.info(f"开始爬取: {url}")
            
            # 如果没有提供提取策略，使用默认策略
            if not extraction_strategy:
                llm_config = self.config.get('llm', {})
                extraction_strategy = LLMExtractionStrategy(
                    llm_provider=llm_config.get('provider', 'openai/gpt-3.5-turbo'),
                    llm_api_key=llm_config.get('api_key', ''),  # 从配置加载API key
                    llm_model=llm_config.get('model', 'gpt-3.5-turbo'),
                    max_tokens=llm_config.get('max_tokens', 4000),
                    temperature=llm_config.get('temperature', 0.1),
                    system_prompt="你是一个专业的网页内容提取助手。请提取页面中的关键信息，包括标题、正文内容、发布时间等。"
                )
            
            # 执行爬取
            result = await self.crawler.arun(
                url=url,
                extraction_strategy=extraction_strategy
            )
            
            self.logger.info(f"爬取完成: {url}")
            return result
            
        except Exception as e:
            self.logger.error(f"爬取失败: {e}")
            return {"error": str(e)}
    
    def close(self):
        """
        关闭爬虫资源
        """
        try:
            if hasattr(self, 'crawler'):
                self.crawler.close()
            self.logger.info("Crawl4AI爬虫已关闭")
        except Exception as e:
            self.logger.error(f"关闭爬虫失败: {e}")


def main():
    """
    测试函数
    """
    # 测试数据
    test_cases = [
        {
            "公司名称": "贵州茅台",
            "公司代码": "600519",
            "数据源": "巨潮资讯网",
            "数据类型": "财务报表"
        },
        {
            "公司名称": "贵州茅台",
            "公司代码": "600519",
            "数据源": "东方财富网",
            "数据类型": "公司公告"
        },
        {
            "公司名称": "贵州茅台",
            "公司代码": "600519",
            "数据源": "贵州茅台官网",
            "数据类型": "行业研报"
        }
    ]
    
    # 创建爬虫agent
    agent = Crawl4AIAgent()
    
    try:
        # 测试每个用例
        for i, test_case in enumerate(test_cases, 1):
            # print(f"\n=== 测试用例 {i} ===")
            # print(f"输入: {test_case}")
            
            result = agent.process(test_case)
            # print(f"输出: {json.dumps(result, ensure_ascii=False, indent=2)}")
            
    finally:
        agent.close()


if __name__ == "__main__":
    main() 