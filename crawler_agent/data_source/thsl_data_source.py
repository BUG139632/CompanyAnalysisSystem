import requests
import json
import os
from datetime import datetime

def fetch_thsl_financial_reports(company_code: str, save: bool = True):
    """
    采集同花顺指定公司财报数据，并可保存为本地JSON文件。
    :param company_code: 股票代码（如 '000001'）
    :param save: 是否保存为本地文件
    :return: 结构化数据（dict）
    """
    url = f"https://basic.10jqka.com.cn/api/stock/finance/{company_code}_main.json"
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        'Referer': f'https://basic.10jqka.com.cn/{company_code}/finance.html',
    }
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    # 解析flashData字段
    if isinstance(data, dict) and 'flashData' in data and isinstance(data['flashData'], str):
        try:
            data['flashData'] = json.loads(data['flashData'])
        except Exception as e:
            print(f"flashData字段解析失败: {e}")
    # 新增：解析report为可读结构
    if isinstance(data, dict) and 'flashData' in data and isinstance(data['flashData'], dict):
        data['parsed_report'] = parse_thsl_report(data['flashData'])
    # 保存
    if save:
        # 只保存结构化后的parsed_report
        save_dir = os.path.join('data/raw', 'financial_reports', 'thsl_financial_reports')
        os.makedirs(save_dir, exist_ok=True)
        now = datetime.now().strftime('%Y%m%d_%H%M%S')
        save_path = os.path.join(save_dir, f"{company_code}_thsl_financial_reports_{now}.json")
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(data.get('parsed_report', []), f, ensure_ascii=False, indent=2)
        
        # 检查实际保存的文件数量
        actual_files = len([f for f in os.listdir(save_dir) if f.endswith('.json')])
        print(f"同花顺结构化财报数据已保存到: {save_path}，目录共有 {actual_files} 个文件")
    return data

def parse_thsl_report(flash_data):
    """
    将同花顺flashData中的report和title解析为可读性更高的结构。
    返回：
        [
            {"date": "2025-03-31", "净利润": "140.96亿", ...},
            ...
        ]
    """
    report = flash_data.get('report')
    title = flash_data.get('title')
    if not report or not title or len(report) != len(title):
        return []
    dates = report[0]
    result = []
    for col, date in enumerate(dates):
        row = {"date": date}
        for row_idx in range(1, len(report)):
            # title[row_idx] 可能是字符串或数组，取第一个元素为指标名
            t = title[row_idx]
            if isinstance(t, list):
                name = t[0]
            else:
                name = t
            row[name] = report[row_idx][col]
        result.append(row)
    return result 