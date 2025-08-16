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
import logging

# 压低 webdriver_manager 和 selenium 的日志级别，避免控制台噪声
logging.getLogger("WDM").setLevel(logging.ERROR)
logging.getLogger("webdriver_manager").setLevel(logging.ERROR)
logging.getLogger("selenium").setLevel(logging.WARNING)

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
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from webdriver_manager.chrome import ChromeDriverManager

        # 构造搜索关键词
        query = f"{company_name} 官网"
        url = f"https://www.google.com/search?q={query}"
        if os.environ.get("QUIET", "1") != "1":
            print(f"[官网采集] Google搜索: {url}")

        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        # 设定中英文以提升选择器稳定性
        options.add_argument('--lang=zh-CN,zh')
        options.add_argument('--window-size=1920,1080')
        # 额外的稳定性选项
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')
        options.add_argument('--disable-images')
        options.add_argument('--disable-background-timer-throttling')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--disable-features=TranslateUI')
        options.add_argument('--disable-ipc-flooding-protection')
        
        # 使用随机端口避免冲突
        import random
        debug_port = random.randint(9223, 9300)
        options.add_argument(f'--remote-debugging-port={debug_port}')

        # 创建唯一的用户数据目录
        import tempfile
        import uuid
        import shutil
        tmp_profile = tempfile.mkdtemp(prefix=f"selenium_profile_{uuid.uuid4()}_")
        options.add_argument(f"--user-data-dir={tmp_profile}")

        # 设置Chrome二进制位置和ChromeDriver
        env_bin = os.getenv('CHROME_BIN')
        if env_bin and os.path.exists(env_bin):
            options.binary_location = env_bin
        
        # 检测环境并设置合适的Chrome和Driver路径
        if os.path.exists('/.dockerenv'):
            # Docker环境：使用安装的google-chrome
            candidates = [
                ('/usr/bin/google-chrome', '/usr/local/bin/chromedriver'),
            ]
            service = None
            for bin_path, drv_path in candidates:
                if os.path.exists(bin_path) and os.path.exists(drv_path):
                    if not env_bin:  # 只有在没有环境变量时才覆盖
                        options.binary_location = bin_path
                    service = Service(drv_path)
                    break
            else:
                # 如果都没找到，使用ChromeDriverManager
                service = Service(ChromeDriverManager().install())
        else:
            service = Service(ChromeDriverManager().install())

        if os.environ.get("QUIET", "1") != "1":
            print(f"[官网采集] Chrome binary: {options.binary_location if hasattr(options, 'binary_location') else 'default'}")
            print(f"[官网采集] ChromeDriver: {service.path}")
            print(f"[官网采集] 用户数据目录: {tmp_profile}")

        try:
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            print(f"[官网采集] Chrome启动失败，尝试基本配置: {e}")
            # 使用最基本的配置重试
            basic_options = Options()
            basic_options.add_argument('--headless=new')
            basic_options.add_argument('--no-sandbox')
            basic_options.add_argument('--disable-dev-shm-usage')
            if env_bin and os.path.exists(env_bin):
                basic_options.binary_location = env_bin
            elif os.path.exists('/.dockerenv') and os.path.exists('/usr/bin/google-chrome'):
                basic_options.binary_location = '/usr/bin/google-chrome'
            driver = webdriver.Chrome(service=service, options=basic_options)

        try:
            driver.get(url)

            # 处理可能出现的同意/隐私弹窗
            try:
                WebDriverWait(driver, 5).until(
                    EC.any_of(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label*="同意" i]')),
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label*="接受" i]')),
                        EC.element_to_be_clickable((By.CSS_SELECTOR, '#L2AGLb')),
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(., '同意') or contains(., '接受') or contains(., 'I agree') or contains(., 'Accept all')]") )
                    )
                )
                for sel in [
                    (By.CSS_SELECTOR, 'button[aria-label*="同意" i]'),
                    (By.CSS_SELECTOR, 'button[aria-label*="接受" i]'),
                    (By.CSS_SELECTOR, '#L2AGLb'),
                    (By.XPATH, "//button[contains(., '同意') or contains(., '接受') or contains(., 'I agree') or contains(., 'Accept all')]")
                ]:
                    elems = driver.find_elements(*sel)
                    if elems:
                        try:
                            elems[0].click()
                            break
                        except Exception:
                            pass
            except Exception:
                pass

            # 等待搜索结果加载
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'h3'))
            )

            # 多种选择器回退，尽量拿第一个结果
            # 1) 旧结构
            for sel in ['div.yuRUbf > a']:
                try:
                    elem = driver.find_element(By.CSS_SELECTOR, sel)
                    href = elem.get_attribute('href')
                    if href:
                        if os.environ.get("QUIET", "1") != "1":
                            print(f"[官网采集] 搜索到官网: {href}")
                        return href
                except Exception:
                    pass

            # 2) 新结构：先找标题，再回溯到最近的 a 标签
            h3_elems = driver.find_elements(By.CSS_SELECTOR, 'a h3, h3')
            for h3 in h3_elems:
                try:
                    a = h3.find_element(By.XPATH, './ancestor::a[1]')
                    href = a.get_attribute('href')
                    if not href:
                        continue
                    # 过滤 Google 自身链接
                    if href.startswith('https://www.google.') or href.startswith('/url?'):
                        continue
                    if os.environ.get("QUIET", "1") != "1":
                        print(f"[官网采集] 搜索到官网: {href}")
                    return href
                except Exception:
                    continue

            # 3) 兜底：取搜索区块内的第一个外链
            candidates = driver.find_elements(By.CSS_SELECTOR, 'div#search a[href]')
            for a in candidates:
                href = a.get_attribute('href')
                if not href:
                    continue
                if href.startswith('https://www.google.') or '/search?' in href:
                    continue
                if os.environ.get("QUIET", "1") != "1":
                    print(f"[官网采集] 搜索到官网(兜底): {href}")
                return href

            if os.environ.get("QUIET", "1") != "1":
                print("[官网采集] 未找到官网")
            return None
        finally:
            driver.quit()
            # 清理临时用户数据目录
            try:
                import shutil
                shutil.rmtree(tmp_profile, ignore_errors=True)
            except Exception:
                pass
    except Exception:
        # 打印简短失败信息，避免在控制台输出冗长的Selenium堆栈
        print("官网数据采集失败")
        # 确保临时目录被清理
        try:
            import shutil
            if 'tmp_profile' in locals():
                shutil.rmtree(tmp_profile, ignore_errors=True)
        except Exception:
            pass
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