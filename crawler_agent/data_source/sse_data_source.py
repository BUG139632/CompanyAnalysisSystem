# -*- coding: utf-8 -*-
"""
上交所公司公告API采集与PDF下载
"""
import requests
import os
import json
from datetime import datetime

def fetch_sse_announcements(company_code: str, start_date: str = "2025-01-01", end_date: str = None, save: bool = True, download_pdfs: bool = True, cookies: dict = None, headers: dict = None):
    """
    采集上交所公司公告API，下载2025年至今所有公告PDF。
    :param company_code: 股票代码（如 '600519'）
    :param start_date: 公告起始日期（如 '2025-01-01'）
    :param end_date: 公告结束日期，默认今天
    :param save: 是否保存API返回数据
    :param download_pdfs: 是否下载PDF
    :param cookies: 可选，用户自定义cookies
    :param headers: 可选，用户自定义headers
    :return: 公告数据列表
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    api_url = 'https://query.sse.com.cn/security/stock/queryCompanyBulletinNew.do'
    params = {
        'jsonCallBack': 'jsonpCallback66265299',
        'isPagination': 'true',
        'pageHelp.pageSize': '100',
        'pageHelp.cacheSize': '1',
        'START_DATE': start_date,
        'END_DATE': end_date,
        'SECURITY_CODE': company_code,
        'TITLE': '公告',
        'BULLETIN_TYPE': '',
        'stockType': '',
        'pageHelp.pageNo': '1',
        'pageHelp.beginPage': '1',
        'pageHelp.endPage': '1',
        '_': str(int(datetime.now().timestamp() * 1000)),
    }
    default_cookies = {
        'gdp_user_id': 'gioenc-89538348%2C5b5a%2C5caa%2C8664%2Cad30dg04g56e',
    }
    default_headers = {
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Pragma': 'no-cache',
        'Referer': 'https://www.sse.com.cn/',
        'Sec-Fetch-Dest': 'script',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'same-site',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
    }
    cookies = cookies or default_cookies
    headers = headers or default_headers
    print(f"请求上交所API: {api_url} 参数: {params}")
    resp = requests.get(api_url, params=params, cookies=cookies, headers=headers, timeout=15)
    resp.raise_for_status()
    # 处理jsonp格式
    text = resp.text
    json_start = text.find('(') + 1
    json_end = text.rfind(')')
    json_str = text[json_start:json_end]
    data = json.loads(json_str)
    # 提取公告列表
    announcements = []
    page_data = data.get('pageHelp', {}).get('data', [])
    for item_list in page_data:
        for item in item_list:
            pdf_path = item.get('URL', '')
            pdf_url = f"https://www.sse.com.cn{pdf_path}" if pdf_path else ''
            item['pdf_url'] = pdf_url
            announcements.append(item)
    save_dir = "data/raw/financial_reports/sse_announcements"
    if save:
        print(f"上交所公告数据获取完成，共 {len(announcements)} 条记录")
    if download_pdfs:
        for ann in announcements:
            pdf_url = ann.get('pdf_url')
            title = ann.get('TITLE', '公告')
            date = ann.get('SSEDATE', '')
            if pdf_url:
                pdf_filename = f"{title}_{date}.pdf".replace('/', '_').replace(' ', '_')
                pdf_path = os.path.join(save_dir, pdf_filename)
                try:
                    print(f"下载PDF: {pdf_url}")
                    pdf_resp = requests.get(pdf_url, headers=headers, timeout=20)
                    pdf_resp.raise_for_status()
                    with open(pdf_path, 'wb') as f:
                        f.write(pdf_resp.content)
                    print(f"已保存: {pdf_path}")
                except Exception as e:
                    print(f"下载失败: {pdf_url}, 错误: {e}")
    return announcements 