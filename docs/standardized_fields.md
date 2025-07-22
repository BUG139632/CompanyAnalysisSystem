# 财务数据标准化字段说明

## 概述

本文档描述了多源财务数据合并后的标准化字段结构。通过LLM驱动的数据清洗流程，所有字段名已统一为英文，确保数据结构的一致性和可分析性。

## 字段分类

### 1. 基础信息字段 (3个)

| 字段名 | 英文名称 | 数据类型 | 说明 |
|--------|----------|----------|------|
| 公司代码 | company_code | String | 公司股票代码 |
| 公司名称 | company_name | String | 公司全称 |
| 年份 | year | String | 财务报告年份 |

### 2. 资产负债表字段 (10个)

| 字段名 | 英文名称 | 数据类型 | 说明 |
|--------|----------|----------|------|
| 货币资金 | cash_and_cash_equivalents | Number | 现金及现金等价物 |
| 流动资产 | total_current_assets | Number | 流动资产合计 |
| 非流动资产 | total_non_current_assets | Number | 非流动资产合计 |
| 总资产 | total_assets | Number | 资产总计 |
| 流动负债 | total_current_liabilities | Number | 流动负债合计 |
| 非流动负债 | total_non_current_liabilities | Number | 非流动负债合计 |
| 总负债 | total_liabilities | Number | 负债合计 |
| 实收资本 | paid_in_capital | Number | 实收资本（或股本） |
| 未分配利润 | retained_earnings | Number | 未分配利润 |
| 所有者权益 | total_owners_equity | Number | 所有者权益合计 |

### 3. 利润表字段 (6个)

| 字段名 | 英文名称 | 数据类型 | 说明 |
|--------|----------|----------|------|
| 营业总收入 | total_operating_revenue | Number | 营业收入 |
| 营业总成本 | total_operating_cost | Number | 营业成本 |
| 营业利润 | operating_profit | Number | 营业利润 |
| 利润总额 | total_profit | Number | 利润总额 |
| 所得税费用 | income_tax_expense | Number | 所得税费用 |
| 归母净利润 | net_profit_attributable_to_parent | Number | 归属于母公司所有者的净利润 |

### 4. 现金流量表字段 (3个)

| 字段名 | 英文名称 | 数据类型 | 说明 |
|--------|----------|----------|------|
| 经营活动现金流量净额 | net_cash_flow_from_operating_activities | Number | 经营活动产生的现金流量净额 |
| 投资活动现金流量净额 | net_cash_flow_from_investing_activities | Number | 投资活动产生的现金流量净额 |
| 筹资活动现金流量净额 | net_cash_flow_from_financing_activities | Number | 筹资活动产生的现金流量净额 |

### 5. 财务指标字段 (4个)

| 字段名 | 英文名称 | 数据类型 | 说明 |
|--------|----------|----------|------|
| 基本每股收益 | earnings_per_share | Number | 每股收益（基本） |
| 扣非每股收益 | earnings_per_share_excluding_non_recurring | Number | 扣除非经常性损益的每股收益 |
| 净资产收益率 | roe | Number | 加权平均净资产收益率 |
| 每股净资产 | book_value_per_share | Number | 每股净资产 |

### 6. 运营指标字段 (4个)

| 字段名 | 英文名称 | 数据类型 | 说明 |
|--------|----------|----------|------|
| 销售毛利率 | gross_profit_margin | Number | 毛利率 |
| 应收账款周转率 | accounts_receivable_turnover | Number | 应收账款周转率 |
| 应收账款周转天数 | accounts_receivable_days | Number | 应收账款周转天数 |
| 存货周转率 | inventory_turnover | Number | 存货周转率 |
| 存货周转天数 | inventory_days | Number | 存货周转天数 |

### 7. 其他信息字段 (6个)

| 字段名 | 英文名称 | 数据类型 | 说明 |
|--------|----------|----------|------|
| 分红方案 | dividend_plan | String | 分红方案描述 |
| 分红年度 | dividend_year | String | 分红年度 |
| 行业名称 | industry | String | 所属行业 |
| 股息率 | dividend_yield | Number | 最新股息率 |
| 公告日期 | announcement_date | String | 公告发布日期 |

## 数据源优先级

数据合并时按以下优先级选择：

1. **巨潮资讯网** (最高优先级)
2. **深交所**
3. **东方财富**
4. **同花顺** (最低优先级)

## 数据完整性

- **总字段数**: 36个
- **基础信息**: 3/3 (100%)
- **资产负债表**: 10/10 (100%)
- **利润表**: 6/6 (100%)
- **现金流量表**: 3/3 (100%)
- **财务指标**: 4/4 (100%)
- **运营指标**: 5/5 (100%)
- **其他信息**: 5/5 (100%)

## 数据质量说明

### 缺失值处理
- 缺失的字段统一标记为 `null`
- 数值型字段缺失时不影响其他字段的计算
- 字符串字段缺失时不影响数据结构的完整性

### 数据验证
- 每条记录都包含完整的36个字段
- 通过 `validate_and_complete_record()` 函数确保字段完整性
- LLM输出后自动补全缺失字段为 `null`

### 字段标准化
- 所有字段名统一为英文
- 数值型字段保持原始精度
- 字符串字段保留原始格式（包括中文内容）

## 使用示例

```json
{
  "company_code": "600519",
  "company_name": "贵州茅台",
  "year": "2024",
  "cash_and_cash_equivalents": 5929582.3,
  "total_current_assets": 25172667.46,
  "total_non_current_assets": 4721790.53,
  "total_assets": 29894457.99,
  "total_current_liabilities": 5651599.06,
  "total_non_current_liabilities": 41727.42,
  "total_liabilities": 5693326.48,
  "paid_in_capital": 125619.78,
  "retained_earnings": 18278741.52,
  "total_owners_equity": 24201131.51,
  "total_operating_revenue": 174144070000.0,
  "total_operating_cost": 5452397.15,
  "operating_profit": 11968857.95,
  "total_profit": 11963857.82,
  "income_tax_expense": 3030385.02,
  "net_profit_attributable_to_parent": 86228146421.62,
  "net_cash_flow_from_operating_activities": 9246369.22,
  "net_cash_flow_from_investing_activities": -178520.26,
  "net_cash_flow_from_financing_activities": -7106750.65,
  "earnings_per_share": 68.64,
  "earnings_per_share_excluding_non_recurring": 68.65,
  "roe": 36.02,
  "book_value_per_share": 185.564713136315,
  "gross_profit_margin": 91.9312166361,
  "accounts_receivable_turnover": 28.6104,
  "accounts_receivable_days": null,
  "inventory_turnover": null,
  "inventory_days": null,
  "dividend_plan": "10派276.73元(含税,扣税后249.057元)",
  "dividend_year": "2024",
  "industry": "酿酒行业",
  "dividend_yield": 1.92727703258,
  "announcement_date": "2025-04-03 00:00:00"
}
```

## 技术实现

### LLM Prompt标准化
通过精心设计的prompt，让LLM直接输出标准化的英文字段格式，避免后续复杂的字段映射工作。

### 数据验证机制
```python
def validate_and_complete_record(record):
    """验证并补全记录，确保包含所有标准字段"""
    standard_fields = {field: None for field in STANDARD_FIELDS}
    validated_record = standard_fields.copy()
    
    for field, value in record.items():
        if field in standard_fields:
            validated_record[field] = value
    
    return validated_record
```

### 标准字段列表
```python
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
```

## 更新记录

- **2025-07-12**: 创建标准化字段文档
- **2025-07-12**: 完成LLM驱动的字段标准化
- **2025-07-12**: 实现数据验证和补全机制 