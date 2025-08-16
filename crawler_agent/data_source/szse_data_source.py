import requests
import json
import os
from datetime import datetime
import re
from typing import Optional

def fetch_szse_announcements(company_code: str, page_num: int = 1, page_size: int = 50, save: bool = True, download_pdfs: bool = False, max_pdfs: int = 5, use_playwright: bool = False, save_dir: Optional[str] = None, datatype: str = "公告"):
    """
    采集深交所公告API，返回JSON数据并可保存，并可下载PDF。
    :param company_code: 股票代码（如 '000001'）
    :param page_num: 页码
    :param page_size: 每页数量
    :param save: 是否保存为本地文件
    :param download_pdfs: 是否下载PDF
    :param max_pdfs: 最多下载PDF数量（仅财报时生效）
    :param use_playwright: 是否用Playwright自动化下载PDF
    :param save_dir: PDF及JSON保存目录
    :param datatype: "公告"或"财报"，决定采集参数
    :return: 结构化数据（dict）
    """
    url = "http://www.szse.cn/api/disc/announcement/annList"
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'Origin': 'http://www.szse.cn',
        'Pragma': 'no-cache',
        'Referer': 'http://www.szse.cn/disclosure/listed/notice/index.html',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        'X-Request-Type': 'ajax',
        'X-Requested-With': 'XMLHttpRequest',
    }
    if datatype == "财报":
        payload = {
            "seDate": ["", ""],
            "stock": [company_code],
            "channelCode": ["listedNotice_disc"],
            "bigCategoryId": ["010301"],
            "pageSize": page_size,
            "pageNum": page_num,
            "searchKey": ["摘要"],
        }
        if save_dir is None:
            save_dir = "data/raw/financial_reports/szse_financial_reports"
    else:  # 公告
        payload = {
            "seDate": ["2025-01-01", "2025-12-31"],
            "stock": [company_code],
            "channelCode": ["listedNotice_disc"],
            "pageSize": page_size,
            "pageNum": page_num,
            "searchKey": ["公告"],
        }
        if save_dir is None:
            save_dir = "data/raw/announcements/szse_announcements"
    response = requests.post(url, headers=headers, json=payload, timeout=15)
    response.raise_for_status()
    data = response.json()
    if save:
        # 只保留PDF下载，去掉原始API数据保存
        pass
    if download_pdfs and data and isinstance(data, dict) and 'data' in data and isinstance(data['data'], list):
        pdf_list = data['data']
        if datatype == "财报":
            if use_playwright:
                download_szse_pdfs_playwright(pdf_list, save_dir, max_count=max_pdfs)
            else:
                download_szse_pdfs(pdf_list, save_dir, max_count=max_pdfs)
            print(f"已下载{min(len([a for a in pdf_list if a.get('attachPath', '').lower().endswith('.pdf')]), max_pdfs)}个PDF文件")
        else:  # 公告
            if use_playwright:
                download_szse_pdfs_playwright(pdf_list, save_dir, max_count=15)
            else:
                download_szse_pdfs(pdf_list, save_dir, max_count=15)
    return data

def download_szse_pdfs(announcements, save_dir, max_count=5):
    """
    下载深交所公告中的PDF附件，按年份排序，最多下载max_count个。
    :param announcements: 公告列表
    :param save_dir: 保存目录
    :param max_count: 最多下载数量
    """
    pdf_base_url = "http://disc.static.szse.cn/download"
    # 提取年份并排序，优先下载近5年
    def extract_year(ann):
        # 优先用公告标题中的年份
        m = re.search(r"(20\\d{2})", ann.get('title', ''))
        if m:
            return int(m.group(1))
        # 其次用发布日期
        date_str = ann.get('publishTime', '')
        m2 = re.match(r"(\\d{4})", date_str)
        if m2:
            return int(m2.group(1))
        return 0
    pdf_anns = [a for a in announcements if a.get('attachPath', '').lower().endswith('.pdf')]
    pdf_anns_sorted = sorted(pdf_anns, key=extract_year, reverse=True)[:max_count]
    os.makedirs(save_dir, exist_ok=True)
    # 新增：用Session先访问首页获取cookie
    session = requests.Session()
    homepage_url = "http://www.szse.cn/disclosure/listed/notice/index.html"
    try:
        session.get(homepage_url, timeout=10)
    except Exception as e:
        print(f"访问深交所首页获取cookie失败: {e}")
    for ann in pdf_anns_sorted:
        # 拼接 PDF 下载地址
        attach_path = ann['attachPath']
        if not attach_path.startswith('/'):
            attach_path = '/' + attach_path
        pdf_url = pdf_base_url + attach_path
        title = ann.get('title', 'report')
        year = extract_year(ann)
        filename = f"{title}_{year}.pdf".replace('/', '_').replace(' ', '_')
        filepath = os.path.join(save_dir, filename)
        headers = {
            'Referer': homepage_url,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
            'Accept': 'application/pdf,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
        }
        try:
            print(f"下载PDF: {pdf_url}")
            resp = session.get(pdf_url, headers=headers, timeout=20)
            resp.raise_for_status()
            with open(filepath, 'wb') as f:
                f.write(resp.content)
            print(f"已保存: {filepath}")
        except Exception as e:
            print(f"下载失败: {pdf_url}, 错误: {e}")

def download_szse_pdfs_playwright(announcements, save_dir, max_count=5):
    """
    用Playwright自动化浏览器下载深交所PDF，按年份排序，最多下载max_count个。
    需先安装playwright及浏览器：pip install playwright && playwright install
    """
    from playwright.sync_api import sync_playwright
    base_url = "http://www.szse.cn"
    def extract_year(ann):
        m = re.search(r"(20\\d{2})", ann.get('title', ''))
        if m:
            return int(m.group(1))
        date_str = ann.get('publishTime', '')
        m2 = re.match(r"(\\d{4})", date_str)
        if m2:
            return int(m2.group(1))
        return 0
    pdf_anns = [a for a in announcements if a.get('attachPath', '').lower().endswith('.pdf')]
    pdf_anns_sorted = sorted(pdf_anns, key=extract_year, reverse=True)[:max_count]
    os.makedirs(save_dir, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chrome.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        for ann in pdf_anns_sorted:
            pdf_url = base_url + ann['attachPath']
            title = ann.get('title', 'report')
            year = extract_year(ann)
            filename = f"{title}_{year}.pdf".replace('/', '_').replace(' ', '_')
            filepath = os.path.join(save_dir, filename)
            try:
                print(f"Playwright下载PDF: {pdf_url}")
                # 直接下载PDF
                with page.expect_download() as download_info:
                    page.goto(pdf_url)
                download = download_info.value
                download.save_as(filepath)
                print(f"已保存: {filepath}")
            except Exception as e:
                print(f"Playwright下载失败: {pdf_url}, 错误: {e}")
        browser.close() 