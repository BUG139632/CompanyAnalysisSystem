import aiohttp
import logging
import time
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode, urljoin
import asyncio
from bs4 import BeautifulSoup
import re
import tempfile
import pdfplumber
import aiofiles
import requests

logger = logging.getLogger(__name__)

class CninfoDataSource:
    """
    巨潮资讯网专用数据源实现
    支持公司财务报表（财报）的搜索与详情获取（含PDF下载链接和文本提取）
    """
    BASE_URL = "http://www.cninfo.com.cn"
    SEARCH_API = BASE_URL + "/new/fulltextSearch"
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    def __init__(self):
        pass

    async def search_financial_reports(self, company_name: str, company_code: str,
                                       page_num: int = 1, page_size: int = 30, keyword: Optional[str] = None) -> List[Dict]:
        """
        搜索公司财务报表（年报、季报、半年报等），并提取详情页链接和PDF内容
        :param company_name: 公司名称
        :param company_code: 公司代码
        :param page_num: 页码
        :param page_size: 每页数量
        :param keyword: 关键词（可选，默认用公司名）
        :return: 财报公告列表（含详情页链接、PDF链接、PDF文本）
        """
        searchkey = keyword or company_name
        search_params = {
            'notautosubmit': '',
            'keyWord': searchkey,
            'searchType': '0',
            'pageNum': page_num,
            'pageSize': page_size,
            'stock': company_code
        }
        logger.info(f"搜索参数: {search_params}")
        async with aiohttp.ClientSession() as session:
            homepage_url = self.BASE_URL + "/new/index"
            logger.info(f"访问主页URL: {homepage_url}")
            async with session.get(homepage_url, headers=self.HEADERS) as resp:
                logger.info(f"主页响应: {resp.status}")
                await resp.text()
                await asyncio.sleep(0.5)
            search_url = self.SEARCH_API + '?' + urlencode(search_params)
            logger.info(f"搜索URL: {search_url}")
            async with session.get(search_url, headers=self.HEADERS) as resp:
                logger.info(f"搜索API响应: {resp.status}")
                if resp.status == 200:
                    content = await resp.text()
                    soup = BeautifulSoup(content, 'html.parser')
                    announcements = []
                    for row in soup.select('table tr')[1:]:  # 跳过表头
                        cols = row.find_all('td')
                        if len(cols) < 4:
                            continue
                        code = cols[0].get_text(strip=True)
                        name = cols[1].get_text(strip=True)
                        title_link = cols[2].find('a')
                        title = title_link.get_text(strip=True) if title_link else cols[2].get_text(strip=True)
                        detail_url = urljoin(self.BASE_URL, title_link['href']) if title_link and title_link.has_attr('href') else ''
                        date = cols[3].get_text(strip=True)
                        if title and detail_url:
                            announcements.append({
                                'companyCode': code,
                                'companyName': name,
                                'announcementTitle': title,
                                'announcementDate': date,
                                'detailUrl': detail_url
                            })
                    logger.info(f"解析到 {len(announcements)} 个财报公告")
                    # 进一步抓取详情页PDF链接和内容
                    for ann in announcements:
                        pdf_url = await self.get_pdf_url_from_detail(ann['detailUrl'], session)
                        ann['pdfUrl'] = pdf_url
                        if pdf_url:
                            ann['pdfText'] = await self.extract_pdf_data(pdf_url, session)
                        else:
                            ann['pdfText'] = ''
                    return announcements
                else:
                    logger.error(f"搜索失败: {resp.status}")
                    return []

    async def get_pdf_url_from_detail(self, detail_url: str, session: aiohttp.ClientSession) -> str:
        """
        访问详情页，提取PDF下载地址
        :param detail_url: 详情页URL
        :param session: aiohttp会话
        :return: PDF下载地址（如有）
        """
        if not detail_url:
            return ''
        try:
            async with session.get(detail_url, headers=self.HEADERS) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    pdf_link = ''
                    for a in soup.find_all('a', href=True):
                        href = a['href']
                        if href.lower().endswith('.pdf'):
                            pdf_link = urljoin(self.BASE_URL, href)
                            break
                    return pdf_link
        except Exception as e:
            logger.error(f"详情页解析失败: {e}")
        return ''

    async def extract_pdf_data(self, pdf_url: str, session: aiohttp.ClientSession) -> str:
        """
        下载PDF并提取文本内容
        :param pdf_url: PDF文件URL
        :param session: aiohttp会话
        :return: PDF文本内容
        """
        if not pdf_url:
            return ''
        try:
            async with session.get(pdf_url, headers=self.HEADERS) as resp:
                if resp.status == 200:
                    # 保存到临时文件
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                        pdf_path = tmp_file.name
                        content = await resp.read()
                        tmp_file.write(content)
                    # 用pdfplumber提取文本
                    text = ''
                    try:
                        with pdfplumber.open(pdf_path) as pdf:
                            for page in pdf.pages:
                                text += page.extract_text() or ''
                    except Exception as e:
                        logger.error(f"PDF解析失败: {e}")
                        text = ''
                    return text.strip()
        except Exception as e:
            logger.error(f"PDF下载或解析失败: {e}")
        return ''

def get_cninfo_financial_table(company_code, org_id, table_type, cookies, headers):
    """
    通用函数：获取巨潮资讯网三大财务报表（利润表、资产负债表、现金流量表）
    table_type: 'income'/'balance'/'cashflow'
    所有sign参数均为1
    """
    api_map = {
        'income': 'getIncomeStatement',
        'balance': 'getBalanceSheets',  # 修改为带s
        'cashflow': 'getCashFlowStatement'
    }
    if table_type not in api_map:
        raise ValueError(f"Unsupported table_type: {table_type}")
    api_name = api_map[table_type]
    url = f'http://www.cninfo.com.cn/data20/financialData/{api_name}'
    params = {
        'scode': company_code,
        'sign': '1'  # 所有财务报表sign都为1
    }
    # Referer建议带orgId和stockCode
    headers = headers.copy()
    headers['Referer'] = f'http://www.cninfo.com.cn/new/disclosure/stock?orgId={org_id}&stockCode={company_code}'
    response = requests.get(url, params=params, cookies=cookies, headers=headers, verify=False)
    response.raise_for_status()
    return response.json()

def get_fresh_cninfo_session():
    """
    自动抓取巨潮资讯网最新的cookie和headers
    :return: tuple (cookies_dict, headers_dict)
    """
    import requests
    from bs4 import BeautifulSoup
    
    session = requests.Session()
    
    # 设置基础headers
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    })
    
    try:
        # 访问巨潮主页获取初始cookie
        print("正在访问巨潮资讯网主页获取session...")
        response = session.get('http://www.cninfo.com.cn/new/index', timeout=10)
        response.raise_for_status()
        
        # 获取cookies
        cookies = session.cookies.get_dict()
        
        # 构建headers
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        }
        
        print(f"成功获取session，cookies数量: {len(cookies)}")
        return cookies, headers
        
    except Exception as e:
        print(f"自动获取session失败: {e}")
        # 返回默认值
        return {}, {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        }

def fetch_cninfo_financial_reports(company_code, org_id, cookies=None, headers=None, auto_session=True):
    """
    一键采集巨潮资讯网三大结构化财报（利润表、资产负债表、现金流量表）
    :param company_code: 股票代码
    :param org_id: 机构ID
    :param cookies: dict，可选，如不提供且auto_session=True则自动获取
    :param headers: dict，可选，如不提供且auto_session=True则自动获取
    :param auto_session: bool，是否自动获取session信息
    :return: dict, 结构为{'income': ..., 'balance': ..., 'cashflow': ...}，如有异常则对应值为None
    """
    # 自动获取session信息
    if auto_session and (cookies is None or headers is None):
        cookies, headers = get_fresh_cninfo_session()
    
    result = {}
    for table_type in ['income', 'balance', 'cashflow']:
        try:
            data = get_cninfo_financial_table(company_code, org_id, table_type, cookies, headers)
            result[table_type] = data
        except Exception as e:
            import traceback
            print(f"{table_type}接口出错: {e}")
            traceback.print_exc()
            result[table_type] = None
    return result 