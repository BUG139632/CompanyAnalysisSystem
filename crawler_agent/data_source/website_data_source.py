#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公司官网财报/公告采集复用函数
"""
import requests
from typing import List, Dict, Optional
import re
import os
import time
from urllib.parse import urljoin

# 可选：如需LLM辅助，可引入自定义llm_func
# from common.llm_base_agent import LLMBaseAgent

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"


def search_company_website(company_name: str, llm_func=None) -> Optional[str]:
    """
    通过Playwright爬取Google搜索结果页，提取公司官网首页链接。
    :param company_name: 公司名称
    :param llm_func: 可选，LLM辅助生成搜索关键词
    :return: 官网URL或None
    """
    try:
        from playwright.sync_api import sync_playwright
        import time
        
        # 构造搜索关键词
        query = f"{company_name} 官网"
        url = f"https://www.google.com/search?q={query}"
        print(f"[官网采集] Google搜索: {url}")
        
        with sync_playwright() as p:
            # 启动浏览器
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # 设置用户代理
            page.set_extra_http_headers({"User-Agent": USER_AGENT})
            
            # 访问搜索页面
            page.goto(url)
            page.wait_for_load_state('networkidle')
            
            # 提取第一个自然结果
            results = page.query_selector_all('div.yuRUbf > a')
            if results:
                link = results[0].get_attribute('href')
                print(f"[官网采集] 搜索到官网: {link}")
                browser.close()
                return link
            
            print("[官网采集] 未找到官网")
            browser.close()
            return None
            
    except Exception as e:
        print(f"[官网采集] Playwright功能失败: {e}")
        return None


def find_investor_page(website_url: str, llm_func=None) -> Optional[str]:
    """
    尝试定位官网的投资者关系/财报/公告页面
    :param website_url: 公司官网首页
    :param llm_func: 可选，LLM辅助分析
    :return: 投资者关系页URL或None
    """
    try:
        resp = requests.get(website_url, headers={"User-Agent": USER_AGENT}, timeout=10)
        html = resp.text
        # 常见关键词
        patterns = [r"投资者关系", r"投资者服务", r"财务报告", r"公告", r"信息披露"]
        for pat in patterns:
            match = re.search(f'<a[^>]+href=["\\\']([^"\\\']+)["\\\'][^>]*>[^<]*{pat}[^<]*</a>', html, re.I)
            if match:
                page_url = urljoin(website_url, match.group(1))
                print(f"[官网采集] 找到投资者关系/财报页: {page_url}")
                return page_url
        # 可选：用LLM辅助分析html
        if llm_func:
            return llm_func(html)
    except Exception as e:
        print(f"[官网采集] 访问官网失败: {e}")
    return None


def extract_report_links(page_url: str, patterns: List[str]=None) -> List[str]:
    """
    从投资者关系/财报/公告页面提取PDF或公告链接
    :param page_url: 目标页面URL
    :param patterns: 匹配PDF/公告的正则列表
    :return: 链接列表
    """
    if patterns is None:
        patterns = [r'href=["\\\']([^"\\\']+\.pdf)["\\\']', r'href=["\\\']([^"\\\']+公告[^"\\\']*)["\\\']']
    links = []
    try:
        resp = requests.get(page_url, headers={"User-Agent": USER_AGENT}, timeout=10)
        html = resp.text
        for pat in patterns:
            for m in re.finditer(pat, html, re.I):
                link = urljoin(page_url, m.group(1))
                links.append(link)
        print(f"[官网采集] 提取到{len(links)}个PDF/公告链接")
    except Exception as e:
        print(f"[官网采集] 提取链接失败: {e}")
    return links


def download_file(url: str, save_dir: str, filename: str=None) -> Optional[str]:
    """
    下载PDF/公告文件到本地
    :param url: 文件URL
    :param save_dir: 保存目录
    :param filename: 文件名（可选）
    :return: 本地文件路径或None
    """
    try:
        os.makedirs(save_dir, exist_ok=True)
        if not filename:
            filename = url.split('/')[-1].split('?')[0]
        save_path = os.path.join(save_dir, filename)
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        with open(save_path, 'wb') as f:
            f.write(resp.content)
        print(f"[官网采集] 已下载: {save_path}")
        return save_path
    except Exception as e:
        print(f"[官网采集] 下载失败: {e}")
    return None


# 复用主流程时可按如下方式组合：
# 1. url = search_company_website(company_name)
# 2. page = find_investor_page(url)
# 3. links = extract_report_links(page)
# 4. for link in links: download_file(link, save_dir) 