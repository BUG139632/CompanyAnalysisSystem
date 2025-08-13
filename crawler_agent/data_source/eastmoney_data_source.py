import requests
import json
import os
import re
from datetime import datetime
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
from common.llm_base_agent import LLMBaseAgent
import logging

# 压低 webdriver_manager 和 selenium 的日志级别，避免控制台噪声
logging.getLogger("WDM").setLevel(logging.ERROR)
logging.getLogger("webdriver_manager").setLevel(logging.ERROR)
logging.getLogger("selenium").setLevel(logging.WARNING)

def get_fresh_eastmoney_session():
    """
    自动抓取东方财富网最新的cookie和headers；增加重试与备用域名，超时后 graceful fallback。
    :return: tuple (cookies_dict, headers_dict)
    """
    import requests, random, time as _time
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    session = requests.Session()
    # retry config
    retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retry_strategy))
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    })

    candidate_urls = [
        'https://data.eastmoney.com/report/industry.jshtml',
        'https://www.eastmoney.com',
        'https://quote.eastmoney.com/center'
    ]
    for url in candidate_urls:
        try:
            if os.environ.get("QUIET", "1") != "1":
                print(f"正在访问东方财富 {url} 获取session...")
            resp = session.get(url, timeout=15)
            resp.raise_for_status()
            cookies = session.cookies.get_dict()
            if cookies:
                headers = {
                    'Accept': '*/*',
                    'Accept-Language': 'zh-CN,zh;q=0.9',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'Pragma': 'no-cache',
                    'User-Agent': session.headers['User-Agent'],
                    'Referer': url,
                }
                if os.environ.get("QUIET", "1") != "1":
                    print(f"成功获取东方财富session，cookies数量: {len(cookies)}")
                return cookies, headers
        except Exception as e:
            # 随机等待再重试下一 URL
            _time.sleep(random.uniform(0.5,1.5))
            if os.environ.get("QUIET", "1") != "1":
                print(f"获取 {url} 失败: {e}")
            continue
    # 全部失败 fallback
    if os.environ.get("QUIET", "1") != "1":
        print("自动获取东方财富session失败，使用最小 headers 继续")
    return {}, {
        'User-Agent': session.headers['User-Agent']
    }

def fetch_eastmoney_annual_reports(company_code: str, page_size: int = 50, page_number: int = 1, save: bool = True):
    """
    采集东方财富网指定公司年报数据，并可保存为本地JSON文件。
    :param company_code: 股票代码（如 '000001'）
    :param page_size: 每页数量
    :param page_number: 页码
    :param save: 是否保存为本地文件
    :return: 结构化数据（dict）
    """
    # 构造请求参数
    url = (
        "https://datacenter-web.eastmoney.com/api/data/v1/get?"
        f"sortColumns=REPORTDATE&sortTypes=-1&pageSize={page_size}&pageNumber={page_number}"
        f"&columns=ALL&filter=(SECURITY_CODE%3D%22{company_code}%22)(DATEMMDD%3D%22%E5%B9%B4%E6%8A%A5%22)"
        "&reportName=RPT_LICO_FN_CPD"
    )
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Pragma': 'no-cache',
        'Referer': f'https://data.eastmoney.com/bbsj/yjbb/{company_code}.html',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
    }
    # 发送请求
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    text = resp.text
    # 去除 callback 包裹
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        data = json.loads(match.group(0))
    else:
        data = resp.json() if resp.headers.get('Content-Type', '').startswith('application/json') else {}
    # 保存
    if save:
        save_dir = 'data/raw/financial_reports/eastmoney_financial_reports'
        os.makedirs(save_dir, exist_ok=True)
        now = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{company_code}_eastmoney_annual_reports_{now}.json"
        filepath = os.path.join(save_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"东方财富网年报数据已保存到: {filepath}")
    return data

def fetch_eastmoney_announcements(company_code: str, page_size: int = 50, page_index: int = 1, save: bool = True, save_dir: Optional[str] = None, auto_session: bool = True, cookies: Optional[dict] = None, headers: Optional[dict] = None):
    """
    采集东方财富网指定公司公告数据，并可保存为本地JSON文件。
    :param company_code: 股票代码（如 '000001'）
    :param page_size: 每页数量
    :param page_index: 页码
    :param save: 是否保存为本地文件
    :param save_dir: 保存目录
    :param auto_session: 是否自动获取session信息
    :param cookies: dict，可选，如不提供且auto_session=True则自动获取
    :param headers: dict，可选，如不提供且auto_session=True则自动获取
    :return: 结构化数据（dict）
    """
    # 自动获取session信息
    if auto_session and (cookies is None or headers is None):
        cookies, headers = get_fresh_eastmoney_session()
    
    # 构造请求参数
    url = "https://np-anotice-stock.eastmoney.com/api/security/ann"
    
    # 使用动态获取的cookies，如果没有则使用默认值
    if not cookies:
        cookies = {
            'fullscreengg': '1',
            'fullscreengg2': '1',
            'qgqp_b_id': 'd39ab9b2c942a1a44fcdd7915eaf152c',
            'st_si': '54534400170597',
            'HAList': f'ty-0-{company_code}-%u5E73%u5B89%u94F6%u884C',
            'st_asi': 'delete',
            'st_pvi': '61270758899253',
            'st_sp': '2025-07-06%2011%3A24%3A10',
            'st_inirUrl': 'https%3A%2F%2Fdata.eastmoney.com%2F',
            'st_sn': '54',
            'st_psi': '20250708181230720-113300301472-0936177342',
        }
    
    # 使用动态获取的headers，如果没有则使用默认值
    if not headers:
        headers = {
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Referer': f'https://data.eastmoney.com/notices/stock/{company_code}.html',
            'Sec-Fetch-Dest': 'script',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
        }
    
    params = {
        'cb': 'jQuery112305796371692327644_1752014122609',
        'sr': '-1',
        'page_size': str(page_size),
        'page_index': str(page_index),
        'ann_type': 'A',
        'client_source': 'web',
        'stock_list': company_code,
        'f_node': '0',
        's_node': '0',
    }
    
    # 发送请求
    resp = requests.get(url, params=params, cookies=cookies, headers=headers)
    resp.raise_for_status()
    text = resp.text
    
    # 去除 callback 包裹
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        data = json.loads(match.group(0))
    else:
        data = resp.json() if resp.headers.get('Content-Type', '').startswith('application/json') else {}
    
    # 处理公告列表数据，获取详情页内容
    if 'data' in data and 'list' in data['data']:
        announcements = data['data']['list']
        print(f"获取到 {len(announcements)} 条公告")
        
        # 创建PDF保存目录
        pdf_save_dir = os.path.join(save_dir, 'pdfs') if save_dir else 'data/raw/announcements/eastmoney_announcements/pdfs'
        if save:
            os.makedirs(pdf_save_dir, exist_ok=True)
        
        # 为每条公告获取详情页内容
        pdf_downloaded = 0
        for i, announcement in enumerate(announcements):
            art_code = announcement.get('art_code', '')
            if art_code:
                detail_url = f"https://data.eastmoney.com/notices/detail/{company_code}/{art_code}.html"
                announcement['detail_url'] = detail_url
                
                # 获取详情页内容
                try:
                    detail_result = get_announcement_detail(detail_url, cookies, headers)
                    announcement['detail_content'] = detail_result['content']
                    announcement['detail_metadata'] = detail_result['metadata']
                    announcement['detail_raw_html'] = detail_result['raw_html']
                    announcement['detail_success'] = detail_result['success']
                    if not detail_result['success']:
                        announcement['detail_error'] = detail_result.get('error', 'unknown')
                    
                    # 不再保存详情页HTML文件，只保留PDF下载功能
                    
                    # 用selenium自动提取PDF链接并下载，限制最多15个
                    pdf_url = None
                    pdf_path = None
                    if pdf_downloaded < 15:
                        pdf_url = get_pdf_link_by_selenium(detail_url)
                        announcement['pdf_url'] = pdf_url
                        if pdf_url and pdf_url.lower().endswith('.pdf'):
                            pdf_path = download_pdf(pdf_url, pdf_save_dir)
                            announcement['pdf_path'] = pdf_path
                            pdf_downloaded += 1
                        else:
                            announcement['pdf_path'] = None
                    else:
                        announcement['pdf_url'] = None
                        announcement['pdf_path'] = None
                    
                    print(f"已获取公告详情: {announcement.get('title', 'Unknown')}")
                except Exception as e:
                    print(f"获取公告详情失败: {e}")
                    announcement['detail_content'] = ''
                    announcement['detail_success'] = False
                    announcement['detail_error'] = str(e)
    
    # 不再保存JSON文件，只返回数据
    if save:
        print(f"东方财富网公告数据获取完成，共 {len(data.get('data', {}).get('list', []))} 条记录")
    
    return data

def fetch_eastmoney_industry_reports(
    industry_code: str,
    page_num: int = 1,
    page_size: int = 20,
    begin_time: str = "2023-07-09",
    end_time: str = "2025-07-09",
    cookies: dict = None,
    headers: dict = None,
    save: bool = True,
    save_dir: str = "data/raw/industry_reports/eastmoney"
):
    """
    采集东方财富网指定行业的行业研报。
    :param industry_code: 行业代码（如“546”）
    :param page_num: 页码
    :param page_size: 每页数量
    :param begin_time: 起始日期
    :param end_time: 截止日期
    :param cookies: 浏览器cookies
    :param headers: 浏览器headers
    :param save: 是否保存为本地文件
    :param save_dir: 保存目录
    :return: 结构化数据（dict）
    """
    url = (
        "https://reportapi.eastmoney.com/report/list?"
        f"industryCode={industry_code}"
        f"&pageSize={page_size}"
        f"&industry=*"
        f"&rating=*"
        f"&ratingChange=*"
        f"&beginTime={begin_time}"
        f"&endTime={end_time}"
        f"&pageNo={page_num}"
        f"&fields="
        f"&qType=1"
        f"&orgCode="
        f"&rcode="
    )
    if headers is None:
        headers = {
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Referer': 'https://data.eastmoney.com/report/industry.jshtml',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
        }
    if cookies is None:
        cookies = {}
    resp = requests.get(url, headers=headers, cookies=cookies)
    resp.raise_for_status()
    data = resp.json()
    if save:
        print(f"东方财富行业研报数据获取完成，共 {len(data.get('data', []))} 条记录")
    return data

def get_announcement_detail(detail_url: str, cookies: dict, headers: dict) -> dict:
    """
    获取公告详情页内容
    :param detail_url: 公告详情页URL
    :param cookies: cookies
    :param headers: headers
    :return: 包含详细内容的字典
    """
    try:
        # 更新Referer为详情页
        detail_headers = headers.copy()
        detail_headers['Referer'] = detail_url
        
        if os.environ.get("QUIET", "1") != "1":
            print(f"正在获取详情页: {detail_url}")
        resp = requests.get(detail_url, cookies=cookies, headers=detail_headers, timeout=15)
        resp.raise_for_status()
        
        # 使用BeautifulSoup解析HTML内容
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 提取公告标题
        title_selectors = [
            '.detail-title',
            '.title',
            'h1',
            '.article-title',
            '.notice-title'
        ]
        
        title = ''
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get_text(strip=True)
                if title:
                    break
        
        # 提取公告内容（根据东方财富网的页面结构）
        content_selectors = [
            '.detail-body',      # 详情页主体内容
            '.content',          # 通用内容选择器
            '.article-content',  # 文章内容
            '.notice-content',   # 公告内容
            '.detail-content',   # 详情内容
            '.main-content',     # 主要内容
            '.body-content',     # 主体内容
            '#content',          # ID选择器
            '.text-content'      # 文本内容
        ]
        
        content = ''
        raw_html = ''
        for selector in content_selectors:
            element = soup.select_one(selector)
            if element:
                # 保存原始HTML
                raw_html = str(element)
                
                # 移除不需要的标签
                for unwanted in element.find_all(["script", "style", "iframe", "img"]):
                    unwanted.decompose()
                
                # 获取清理后的文本内容
                content = element.get_text(separator='\n', strip=True)
                if content and len(content) > 50:  # 确保内容足够长
                    break
        
        # 如果没有找到内容，尝试获取整个body
        if not content:
            body = soup.find('body')
            if body:
                # 移除不需要的标签
                for unwanted in body.find_all(["script", "style", "iframe", "img", "nav", "header", "footer"]):
                    unwanted.decompose()
                content = body.get_text(separator='\n', strip=True)
                raw_html = str(body)
        
        # 提取发布时间
        time_selectors = [
            '.detail-time',
            '.publish-time',
            '.time',
            '.date',
            '.article-time'
        ]
        
        publish_time = ''
        for selector in time_selectors:
            element = soup.select_one(selector)
            if element:
                publish_time = element.get_text(strip=True)
                if publish_time:
                    break
        
        # 提取其他元数据
        metadata = {
            'url': detail_url,
            'title': title,
            'publish_time': publish_time,
            'content_length': len(content) if content else 0,
            'html_length': len(raw_html) if raw_html else 0
        }
        
        result = {
            'metadata': metadata,
            'content': content if content else "无法提取公告内容",
            'raw_html': raw_html if raw_html else "",
            'success': True
        }
        
        if os.environ.get("QUIET", "1") != "1":
            print(f"成功获取详情页内容，标题: {title[:50]}...")
        return result
        
    except requests.exceptions.Timeout:
        error_msg = f"获取详情页超时: {detail_url}"
        print(error_msg)
        return {
            'metadata': {'url': detail_url},
            'content': error_msg,
            'raw_html': '',
            'success': False,
            'error': 'timeout'
        }
    except requests.exceptions.RequestException as e:
        error_msg = f"网络请求失败: {str(e)}"
        print(error_msg)
        return {
            'metadata': {'url': detail_url},
            'content': error_msg,
            'raw_html': '',
            'success': False,
            'error': 'request_error'
        }
    except Exception as e:
        error_msg = f"解析详情页失败: {str(e)}"
        print(error_msg)
        return {
            'metadata': {'url': detail_url},
            'content': error_msg,
            'raw_html': '',
            'success': False,
            'error': 'parse_error'
        } 

def get_pdf_link_by_selenium(detail_url):
    """
    使用Selenium获取PDF链接
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.common.by import By
        from webdriver_manager.chrome import ChromeDriverManager
        import time
        
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        # 为每个 Selenium 会话创建唯一的临时 profile，避免 "user data dir in use" 报错
        import tempfile, uuid, shutil
        tmp_profile = tempfile.mkdtemp(prefix=f"selenium_profile_{uuid.uuid4()}_")
        options.add_argument(f"--user-data-dir={tmp_profile}")
        
        # 在 Docker 环境中使用系统安装的 Chromium 和 ChromeDriver
        if os.path.exists('/.dockerenv'):
            options.binary_location = '/usr/bin/chromium'
            service = Service('/usr/bin/chromedriver')
        else:
            service = Service(ChromeDriverManager().install())
        
        driver = webdriver.Chrome(service=service, options=options)
        
        try:
            driver.get(detail_url)
            time.sleep(3)
            
            # 查找"查看pdf原文"按钮 - 使用多种方式
            pdf_btns = []
            # 方式1: 通过class属性查找
            pdf_btns.extend(driver.find_elements(By.CSS_SELECTOR, "a.pdf-link"))
            # 方式2: 通过包含文本查找
            pdf_btns.extend(driver.find_elements(By.XPATH, "//a[contains(text(), '查看PDF原文')]"))
            pdf_btns.extend(driver.find_elements(By.XPATH, "//a[contains(text(), '查看pdf原文')]"))
            # 方式3: 通过span内的文本查找父级a标签
            pdf_btns.extend(driver.find_elements(By.XPATH, "//a[.//span[contains(text(), '查看PDF原文')]]"))
            pdf_btns.extend(driver.find_elements(By.XPATH, "//a[.//span[contains(text(), '查看pdf原文')]]"))
            
            # 去重
            pdf_btns = list(set(pdf_btns))
            pdf_link = None
            for btn in pdf_btns:
                href = btn.get_attribute('href')
                text = btn.text.strip()
                if href and href.lower().endswith('.pdf'):
                    pdf_link = href
                    break
            
            return pdf_link
            
        finally:
            driver.quit()
            # 清理临时 profile
            shutil.rmtree(tmp_profile, ignore_errors=True)
            
    except Exception as e:
        print(f'[selenium] 获取PDF链接失败: {e}')
        # ===== 回退：直接在详情页源码中尝试提取 PDF 直链 =====
        try:
            import requests, re
            from urllib.parse import urljoin
            resp = requests.get(detail_url, timeout=10)
            m = re.search(r'href="([^\"]+\.pdf)"', resp.text, re.I)
            if m:
                pdf_link = urljoin(detail_url, m.group(1))
                print(f"[fallback] 从页面源码提取到 PDF 链接: {pdf_link}")
                return pdf_link
        except Exception as e2:
            print(f"[fallback] 源码提取 PDF 链接失败: {e2}")
        return None

def download_pdf(pdf_url, save_dir):
    import requests
    if not pdf_url or not pdf_url.lower().endswith('.pdf'):
        print('[selenium] 无效的PDF链接')
        return None
    os.makedirs(save_dir, exist_ok=True)
    filename = os.path.join(save_dir, os.path.basename(pdf_url.split('?')[0]))
    resp = requests.get(pdf_url, timeout=20)
    if resp.status_code == 200:
        with open(filename, 'wb') as f:
            f.write(resp.content)
        if os.environ.get("QUIET", "1") != "1":
            print(f'[selenium] 已保存PDF: {filename}')
        return filename
    else:
        print('[selenium] 下载失败')
        return None 

# 东方财富行业列表（部分示例，实际可补全）
EASTMONEY_INDUSTRY_LIST = [
    {"bkCode": "546", "bkName": "玻璃玻纤"},
    {"bkCode": "545", "bkName": "通用设备"},
    {"bkCode": "539", "bkName": "综合行业"},
    {"bkCode": "538", "bkName": "化学制品"},
    {"bkCode": "486", "bkName": "文化传媒"},
    {"bkCode": "485", "bkName": "旅游酒店"},
    {"bkCode": "484", "bkName": "贸易行业"},
    {"bkCode": "482", "bkName": "商业百货"},
    {"bkCode": "481", "bkName": "汽车零部件"},
    {"bkCode": "480", "bkName": "航天航空"},
    {"bkCode": "479", "bkName": "钢铁行业"},
    {"bkCode": "478", "bkName": "有色金属"},
    {"bkCode": "477", "bkName": "酿酒行业"},
    {"bkCode": "476", "bkName": "装修建材"},
    {"bkCode": "475", "bkName": "银行"},
    {"bkCode": "474", "bkName": "保险"},
    {"bkCode": "473", "bkName": "证券"},
    {"bkCode": "471", "bkName": "化纤行业"},
    {"bkCode": "470", "bkName": "造纸印刷"},
    {"bkCode": "465", "bkName": "化学制药"},
    {"bkCode": "464", "bkName": "石油行业"},
    {"bkCode": "459", "bkName": "电子元件"},
    {"bkCode": "458", "bkName": "仪器仪表"},
    {"bkCode": "457", "bkName": "电网设备"},
    {"bkCode": "456", "bkName": "家电行业"},
    {"bkCode": "454", "bkName": "塑料制品"},
    {"bkCode": "451", "bkName": "房地产开发"},
    {"bkCode": "450", "bkName": "航运港口"},
    {"bkCode": "448", "bkName": "通信设备"},
    {"bkCode": "447", "bkName": "互联网服务"},
    {"bkCode": "440", "bkName": "家用轻工"},
    {"bkCode": "438", "bkName": "食品饮料"},
    {"bkCode": "437", "bkName": "煤炭行业"},
    {"bkCode": "436", "bkName": "纺织服装"},
    {"bkCode": "433", "bkName": "农牧饲渔"},
    {"bkCode": "429", "bkName": "交运设备"},
    {"bkCode": "428", "bkName": "电力行业"},
    {"bkCode": "427", "bkName": "公用事业"},
    {"bkCode": "425", "bkName": "工程建设"},
    {"bkCode": "424", "bkName": "水泥建材"},
    {"bkCode": "422", "bkName": "物流行业"},
    {"bkCode": "421", "bkName": "铁路公路"},
    {"bkCode": "420", "bkName": "航空机场"},
    {"bkCode": "1046", "bkName": "游戏"},
    {"bkCode": "1045", "bkName": "房地产服务"},
    {"bkCode": "1044", "bkName": "生物制品"},
    {"bkCode": "1043", "bkName": "专业服务"},
    {"bkCode": "1042", "bkName": "医药商业"},
    {"bkCode": "1041", "bkName": "医疗器械"},
    {"bkCode": "1040", "bkName": "中药"},
    {"bkCode": "1039", "bkName": "电子化学品"},
    {"bkCode": "1038", "bkName": "光学光电子"},
    {"bkCode": "1037", "bkName": "消费电子"},
    {"bkCode": "1036", "bkName": "半导体"},
    {"bkCode": "1035", "bkName": "美容护理"},
    {"bkCode": "1034", "bkName": "电源设备"},
    {"bkCode": "1033", "bkName": "电池"},
    {"bkCode": "1032", "bkName": "风电设备"},
    {"bkCode": "1031", "bkName": "光伏设备"},
    {"bkCode": "1030", "bkName": "电机"},
    {"bkCode": "1029", "bkName": "汽车整车"},
    {"bkCode": "1028", "bkName": "燃气"},
    {"bkCode": "1027", "bkName": "小金属"},
    {"bkCode": "1020", "bkName": "非金属材料"},
    {"bkCode": "1019", "bkName": "化学原料"},
    {"bkCode": "1018", "bkName": "橡胶制品"},
    {"bkCode": "1017", "bkName": "采掘行业"},
    {"bkCode": "1016", "bkName": "汽车服务"},
    {"bkCode": "1015", "bkName": "能源金属"},
    {"bkCode": "910", "bkName": "专用设备"},
    {"bkCode": "740", "bkName": "教育"},
    {"bkCode": "739", "bkName": "工程机械"},
    {"bkCode": "738", "bkName": "多元金融"},
    {"bkCode": "737", "bkName": "软件开发"},
    {"bkCode": "736", "bkName": "通信服务"},
    {"bkCode": "735", "bkName": "计算机设备"},
    {"bkCode": "734", "bkName": "珠宝首饰"},
    {"bkCode": "733", "bkName": "包装材料"},
    {"bkCode": "732", "bkName": "贵金属"},
    {"bkCode": "731", "bkName": "化肥行业"},
    {"bkCode": "730", "bkName": "农药兽药"},
    {"bkCode": "729", "bkName": "船舶制造"},
    {"bkCode": "728", "bkName": "环保行业"},
    {"bkCode": "727", "bkName": "医疗服务"},
    {"bkCode": "726", "bkName": "工程咨询服务"},
    {"bkCode": "725", "bkName": "装修装饰"}
]

def classify_company_to_bkname(company_name: str, industry_list, llm_func=None) -> str:
    """
    用LLM判断公司名最可能属于哪个东方财富行业（bkName），只返回一个行业名。
    """
    prompt = f"""
    已知东方财富行业分类如下：{[item['bkName'] for item in industry_list]}
    请判断公司“{company_name}”最可能属于哪个行业？只输出一个行业名称，必须严格从列表中选。
    """
    if llm_func:
        industry_name = llm_func(prompt)
        return industry_name.strip()
    else:
        # 默认返回食品饮料
        return "食品饮料"

def get_bkcode_by_bkname(bkname: str, industry_list) -> str:
    for item in industry_list:
        if item['bkName'] == bkname:
            return item['bkCode']
    return None

def fetch_eastmoney_industry_reports_by_company(
    company_name: str,
    llm_func=None,
    industry_list=EASTMONEY_INDUSTRY_LIST,
    page_num: int = 1,
    page_size: int = 50,
    begin_time: str = "2023-07-09",
    end_time: str = "2025-07-09",
    save: bool = True,
    save_dir: str = "data/raw/industry_reports/eastmoney",
    cookies: dict = None,
    headers: dict = None,
    max_pdfs: int = 30
):
    """
    输入公司名，自动归类行业并采集东方财富行业研报，并自动下载PDF。
    """
    bkname = classify_company_to_bkname(company_name, industry_list, llm_func=llm_func)
    bkcode = get_bkcode_by_bkname(bkname, industry_list)
    if not bkcode:
        print(f"未找到行业代码: {bkname}")
        return None
    print(f"公司 {company_name} 归类为行业 {bkname}，bkCode={bkcode}")
    data = fetch_eastmoney_industry_reports(
        industry_code=bkcode,
        page_num=page_num,
        page_size=max_pdfs,
        begin_time=begin_time,
        end_time=end_time,
        cookies=cookies,
        headers=headers,
        save=save,
        save_dir=save_dir
    )
    # === PDF下载流程集成 ===
    reports = data.get('data', []) if isinstance(data, dict) else []
    pdf_save_dir = os.path.join(save_dir, 'pdfs')
    os.makedirs(pdf_save_dir, exist_ok=True)
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        import time
    except ImportError as e:
        print(f"[警告] 未安装selenium及相关依赖，无法自动下载PDF: {e}")
        return data
    pdf_downloaded = 0
    for i, report in enumerate(reports):
        infocode = report.get('infoCode') or report.get('infocode')
        if not infocode:
            print(f"跳过第{i+1}条研报，无infoCode")
            continue
        detail_url = f"https://data.eastmoney.com/report/zw_industry.jshtml?infocode={infocode}"
        report['detail_url'] = detail_url
        print(f"处理第{i+1}条研报: {detail_url}")
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.common.by import By
            from webdriver_manager.chrome import ChromeDriverManager
            import time
            
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # 在 Docker 环境中使用系统安装的 Chromium 和 ChromeDriver
            if os.path.exists('/.dockerenv'):
                options.binary_location = '/usr/bin/chromium'
                service = Service('/usr/bin/chromedriver')
            else:
                service = Service(ChromeDriverManager().install())
            
            driver = webdriver.Chrome(service=service, options=options)
            
            try:
                driver.get(detail_url)
                time.sleep(4)
                
                pdf_link = None
                # 只查找"查看pdf原文"按钮
                # 查找"查看pdf原文"按钮 - 使用多种方式
                pdf_btns = []
                # 方式1: 通过class属性查找
                pdf_btns.extend(driver.find_elements(By.CSS_SELECTOR, "a.pdf-link"))
                # 方式2: 通过包含文本查找
                pdf_btns.extend(driver.find_elements(By.XPATH, "//a[contains(text(), '查看PDF原文')]"))
                pdf_btns.extend(driver.find_elements(By.XPATH, "//a[contains(text(), '查看pdf原文')]"))
                # 方式3: 通过span内的文本查找父级a标签
                pdf_btns.extend(driver.find_elements(By.XPATH, "//a[.//span[contains(text(), '查看PDF原文')]]"))
                pdf_btns.extend(driver.find_elements(By.XPATH, "//a[.//span[contains(text(), '查看pdf原文')]]"))
                # 去重
                pdf_btns = list(set(pdf_btns))
                for btn in pdf_btns:
                    href = btn.get_attribute('href')
                    text = btn.text.strip()
                    if href and href.lower().endswith('.pdf'):
                        pdf_link = href
                        break
            finally:
                driver.quit()
            report['pdf_url'] = pdf_link
            if pdf_link and pdf_downloaded < max_pdfs:
                pdf_filename = os.path.join(pdf_save_dir, os.path.basename(pdf_link.split('?')[0]))
                import requests
                try:
                    resp = requests.get(pdf_link, stream=True)
                    if resp.status_code == 200:
                        with open(pdf_filename, 'wb') as f:
                            for chunk in resp.iter_content(chunk_size=8192):
                                f.write(chunk)
                        report['pdf_path'] = pdf_filename
                        pdf_downloaded += 1
                    else:
                        report['pdf_path'] = None
                except Exception as req_e:
                    report['pdf_path'] = None
            else:
                if not pdf_link:
                    print(f"未找到PDF链接")
                elif pdf_downloaded >= max_pdfs:
                    print(f"已达到最大PDF下载数量: {max_pdfs}")
                report['pdf_path'] = None
        except Exception as e:
            print(f"[selenium] 获取PDF失败: {e}")
            report['pdf_url'] = None
            report['pdf_path'] = None
    print(f"PDF下载流程完成，共下载 {pdf_downloaded} 个PDF")
    return data

def gemini_llm_func(prompt: str) -> str:
    """
    调用本项目内置的Gemini LLM接口，返回行业名称。
    """
    agent = LLMBaseAgent()
    result = agent.llm_generate(prompt)
    return result.strip() if result else "食品饮料" 