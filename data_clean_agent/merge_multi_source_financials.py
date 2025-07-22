import sys
import os
import json
import glob

# 完整标准字段列表
STANDARD_FIELDS = [
    "company_code", "company_name", "year",
    "cash_and_cash_equivalents", "total_current_assets", "total_non_current_assets", 
    "total_assets", "total_current_liabilities", "total_non_current_liabilities", 
    "total_liabilities", "paid_in_capital", "retained_earnings", "total_owners_equity",
    "total_operating_revenue", "total_operating_cost", "operating_profit", 
    "total_profit", "income_tax_expense", "net_profit_attributable_to_parent",
    "net_cash_flow_from_operating_activities", "net_cash_flow_from_investing_activities", 
    "net_cash_flow_from_financing_activities", "earnings_per_share", 
    "earnings_per_share_excluding_non_recurring", "roe", "book_value_per_share", 
    "gross_profit_margin", "accounts_receivable_turnover", "accounts_receivable_days", 
    "inventory_turnover", "inventory_days", "dividend_plan", "dividend_year", 
    "industry", "dividend_yield", "announcement_date"
]

# 各数据源到标准字段的映射（尽量覆盖所有标准字段）
FIELD_MAPS = {
    "巨潮资讯网": {
        "公司代码": "company_code",
        "公司简称": "company_name",
        "年份": "year",
        "货币资金": "cash_and_cash_equivalents",
        "流动资产": "total_current_assets",
        "非流动资产": "total_non_current_assets",
        "总资产": "total_assets",
        "流动负债": "total_current_liabilities",
        "非流动负债": "total_non_current_liabilities",
        "总负债": "total_liabilities",
        "实收资本（或股本）": "paid_in_capital",
        "未分配利润": "retained_earnings",
        "所有者权益": "total_owners_equity",
        "营业总收入": "total_operating_revenue",
        "营业总成本": "total_operating_cost",
        "营业利润": "operating_profit",
        "利润总额": "total_profit",
        "所得税": "income_tax_expense",
        "归属母公司净利润": "net_profit_attributable_to_parent",
        "经营活动产生的现金流量净额": "net_cash_flow_from_operating_activities",
        "投资活动产生的现金流量净额": "net_cash_flow_from_investing_activities",
        "筹资活动产生的现金流量净额": "net_cash_flow_from_financing_activities",
        "基本每股收益": "earnings_per_share",
        "扣非每股收益": "earnings_per_share_excluding_non_recurring",
        "净资产收益率": "roe",
        "每股净资产": "book_value_per_share",
        "销售毛利率": "gross_profit_margin",
        "应收账款周转率": "accounts_receivable_turnover",
        "应收账款周转天数": "accounts_receivable_days",
        "存货周转率": "inventory_turnover",
        "存货周转天数": "inventory_days",
        "分红方案": "dividend_plan",
        "分红年度": "dividend_year",
        "行业名称": "industry",
        "股息率": "dividend_yield",
        "公告日期": "announcement_date"
    },
    "深交所": {
        "公司代码": "company_code",
        "公司简称": "company_name",
        "年份": "year",
        "货币资金": "cash_and_cash_equivalents",
        "流动资产": "total_current_assets",
        "非流动资产": "total_non_current_assets",
        "总资产": "total_assets",
        "流动负债": "total_current_liabilities",
        "非流动负债": "total_non_current_liabilities",
        "总负债": "total_liabilities",
        "实收资本": "paid_in_capital",
        "未分配利润": "retained_earnings",
        "所有者权益": "total_owners_equity",
        "股东权益": "total_owners_equity",
        "营业总收入": "total_operating_revenue",
        "营业收入": "total_operating_revenue",
        "营业总成本": "total_operating_cost",
        "营业利润": "operating_profit",
        "利润总额": "total_profit",
        "所得税": "income_tax_expense",
        "归属于本行股东的净利润": "net_profit_attributable_to_parent",
        "净利润": "net_profit_attributable_to_parent",
        "经营活动产生的现金流量净额": "net_cash_flow_from_operating_activities",
        "投资活动产生的现金流量净额": "net_cash_flow_from_investing_activities",
        "筹资活动产生的现金流量净额": "net_cash_flow_from_financing_activities",
        "基本每股收益": "earnings_per_share",
        "扣非每股收益": "earnings_per_share_excluding_non_recurring",
        "净资产收益率": "roe",
        "加权平均净资产收益率": "roe",
        "每股净资产": "book_value_per_share",
        "销售毛利率": "gross_profit_margin",
        "应收账款周转率": "accounts_receivable_turnover",
        "应收账款周转天数": "accounts_receivable_days",
        "存货周转率": "inventory_turnover",
        "存货周转天数": "inventory_days",
        "分红方案": "dividend_plan",
        "分红年度": "dividend_year",
        "行业名称": "industry",
        "股息率": "dividend_yield",
        "公告日期": "announcement_date"
    },
    "东方财富": {
        "SECURITY_CODE": "company_code",
        "SECURITY_NAME_ABBR": "company_name",
        "DATAYEAR": "year",
        "REPORTDATE": "year",  # 取前4位
        "TOTAL_OPERATE_INCOME": "total_operating_revenue",
        "PARENT_NETPROFIT": "net_profit_attributable_to_parent",
        "TOTAL_ASSETS": "total_assets",
        "TOTAL_LIABILITIES": "total_liabilities",
        "PAID_IN_CAPITAL": "paid_in_capital",
        "RETAINED_EARNINGS": "retained_earnings",
        "TOTAL_OWNERS_EQUITY": "total_owners_equity",
        "BASIC_EPS": "earnings_per_share",
        "DEDUCT_BASIC_EPS": "earnings_per_share_excluding_non_recurring",
        "WEIGHTAVG_ROE": "roe",
        "BPS": "book_value_per_share",
        "GROSS_PROFIT_MARGIN": "gross_profit_margin",
        "ACCOUNTS_RECEIVABLE_TURNOVER": "accounts_receivable_turnover",
        "ACCOUNTS_RECEIVABLE_DAYS": "accounts_receivable_days",
        "INVENTORY_TURNOVER": "inventory_turnover",
        "INVENTORY_DAYS": "inventory_days",
        "DIVIDEND_PLAN": "dividend_plan",
        "PAYYEAR": "dividend_year",
        "PUBLISHNAME": "industry",
        "DIVIDEND_YIELD": "dividend_yield",
        "NOTICE_DATE": "announcement_date"
    },
    "同花顺": {
        "date": "year",  # 取前4位
        "营业总收入": "total_operating_revenue",
        "净利润": "net_profit_attributable_to_parent",
        "总资产": "total_assets",
        "总负债": "total_liabilities",
        "每股净资产": "book_value_per_share",
        "基本每股收益": "earnings_per_share",
        "净资产收益率": "roe",
        "销售毛利率": "gross_profit_margin",
        "应收账款周转率": "accounts_receivable_turnover",
        "应收账款周转天数": "accounts_receivable_days",
        "存货周转率": "inventory_turnover",
        "存货周转天数": "inventory_days",
        "分红方案": "dividend_plan",
        "分红年度": "dividend_year",
        "行业名称": "industry",
        "股息率": "dividend_yield"
    }
}

# 字段映射函数

def map_to_standard(record, field_map, source_name):
    std = {k: None for k in STANDARD_FIELDS}
    for src_k, std_k in field_map.items():
        if src_k in record and record[src_k] is not None:
            # 特殊处理年份
            if std_k == "year":
                val = record[src_k]
                if isinstance(val, str) and len(val) >= 4:
                    std[std_k] = val[:4]
                elif isinstance(val, int):
                    std[std_k] = str(val)
                else:
                    std[std_k] = val
            else:
                std[std_k] = record[src_k]
    std["__source__"] = source_name
    return std

def main():
    sources = [
        ("巨潮资讯网", "data/cleaned/cninfo_financial_reports"),
        ("深交所", "data/cleaned/szse_financial_reports"),
        ("东方财富", "data/cleaned/eastmoney_financial_reports"),
        ("同花顺", "data/cleaned/thsl_financial_reports")
    ]
    priority = [s[0] for s in sources]
    all_records = {}
    for source_name, dir_path in sources:
        if not os.path.exists(dir_path):
            continue
        files = glob.glob(os.path.join(dir_path, '*.json'))
        for f in files:
            try:
                with open(f, 'r', encoding='utf-8') as fin:
                    data = json.load(fin)
                # 兼容list和dict
                if isinstance(data, list):
                    records = data
                elif isinstance(data, dict):
                    # 东方财富特殊结构
                    if source_name == "东方财富" and "result" in data and "data" in data["result"]:
                        records = data["result"]["data"]
                    else:
                        records = [data]
                else:
                    continue
                # 深交所特殊结构
                if source_name == "深交所":
                    mapped = []
                    for rec in records:
                        # 结构为年度list
                        if isinstance(rec, dict) and "报告期" in rec and isinstance(rec["报告期"], list):
                            for item in rec["报告期"]:
                                mapped.append(map_to_standard(item["指标"], FIELD_MAPS[source_name], source_name))
                        else:
                            mapped.append(map_to_standard(rec, FIELD_MAPS[source_name], source_name))
                else:
                    mapped = [map_to_standard(rec, FIELD_MAPS[source_name], source_name) for rec in records]
                for rec in mapped:
                    key = (rec.get("company_code"), rec.get("year"))
                    if not key[1]:
                        continue
                    if key not in all_records:
                        all_records[key] = rec
                    else:
                        # 按优先级补全缺失字段
                        for k in STANDARD_FIELDS:
                            if (not all_records[key].get(k)) and rec.get(k):
                                all_records[key][k] = rec.get(k)
            except Exception as e:
                print(f"⚠️ 读取失败: {f} {e}")
    # 输出
    out_path = 'data/structured/all_merged_financial_reports.json'
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    # 移除 __source__ 字段
    merged = []
    for rec in all_records.values():
        rec.pop("__source__", None)
        merged.append(rec)
    with open(out_path, 'w', encoding='utf-8') as fout:
        json.dump(merged, fout, ensure_ascii=False, indent=2)
    print(f"已输出: {out_path}，合并条数: {len(merged)}")

if __name__ == '__main__':
    main()
 