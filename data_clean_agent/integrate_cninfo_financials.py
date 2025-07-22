import os
import json
from glob import glob

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def extract_year_data(table_data, key_map=None):
    """
    table_data: 原始巨潮单表数据（output/financial_reports/cninfo_financial_reports/xxx.json）
    key_map: {中文科目名: 输出字段名}，如不传则用原始index
    返回：{year: {科目: value, ...}, ...}
    """
    # 兼容原始巨潮结构
    records = None
    if isinstance(table_data, dict):
        raw = table_data.get('raw_data', {})
        data = raw.get('data', {})
        recs = data.get('records', [])
        if recs and isinstance(recs, list):
            rec = recs[0]
            # 优先year，其次middle/one/three
            for k in ['year', 'middle', 'one', 'three']:
                if k in rec:
                    records = rec[k]
                    break
    if not records:
        return {}
    year_dict = {}
    for row in records:
        index = row.get('index')
        if not index:
            continue
        out_key = key_map.get(index, index) if key_map else index
        for y, v in row.items():
            if y == 'index' or v is None:
                continue
            year_dict.setdefault(str(y), {})[out_key] = v
    return year_dict

def integrate_cninfo(company_code, company_name, balance_path, income_path, cashflow_path, output_path):
    # 可自定义映射表：{原始中文: 输出中文}
    # 这里只做简单合并，保留原始中文
    balance = load_json(balance_path)
    income = load_json(income_path)
    cashflow = load_json(cashflow_path)
    balance_years = extract_year_data(balance)
    income_years = extract_year_data(income)
    cashflow_years = extract_year_data(cashflow)
    all_years = set(balance_years) | set(income_years) | set(cashflow_years)
    result = []
    for year in sorted(all_years, reverse=True):
        row = {'公司代码': company_code, '公司简称': company_name, '年份': year}
        row.update(balance_years.get(year, {}))
        row.update(income_years.get(year, {}))
        row.update(cashflow_years.get(year, {}))
        result.append(row)
    save_json(result, output_path)
    print(f"已输出: {output_path}")

def main():
    # 假设所有巨潮原始文件在 data/raw/financial_reports/cninfo_financial_reports/
    input_dir = 'data/raw/financial_reports/cninfo_financial_reports'
    output_dir = 'data/cleaned/cninfo_financial_reports'
    os.makedirs(output_dir, exist_ok=True)
    # 清空历史数据
    removed = 0
    for root, _, files in os.walk(output_dir):
        for file in files:
            if file.endswith('.json'):
                try:
                    os.remove(os.path.join(root, file))
                    removed += 1
                except Exception as e:
                    print(f"⚠️  删除 {file} 失败: {e}")
    print(f"   {output_dir}: 已清空 {removed} 个历史 .json 文件")
    # 按公司分组，假设文件名格式为: 公司名_代码_财务报表_balance_*.json
    files = glob(os.path.join(input_dir, '*_财务报表_*.json'))
    company_map = {}
    for f in files:
        base = os.path.basename(f)
        parts = base.split('_')
        if len(parts) < 5:
            continue
        name, code, _, table_type, _ = parts[:5]
        key = (name, code)
        company_map.setdefault(key, {})[table_type] = f
    for (name, code), table_files in company_map.items():
        if all(t in table_files for t in ['balance', 'income', 'cashflow']):
            output_path = os.path.join(output_dir, f'{name}_{code}_巨潮_年度财报.json')
            integrate_cninfo(code, name, table_files['balance'], table_files['income'], table_files['cashflow'], output_path)
        else:
            print(f"⚠️ 缺少三表文件: {name} {code} {table_files}")

if __name__ == '__main__':
    main() 