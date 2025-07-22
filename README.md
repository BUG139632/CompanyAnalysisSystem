# 上市公司投资研究数据采集、清洗与智能分析系统

## 项目概述

本项目是一个完整的上市公司投资研究数据采集、清洗与智能分析系统。系统通过多源数据采集、智能清洗和结构化处理，并集成大模型（LLM）驱动的多维度公司智能分析，为投资研究和决策提供高质量、结构化、可解释的金融数据与深度洞察。

- 支持多源财务、公告、研报等数据自动采集
- LLM辅助数据清洗、字段标准化与多源合并
- Analysis Agent支持六大核心维度的结构化智能分析（管理、商业、销售、研发生产、考核、创新能力）
- Expert Agent支持多轮对话、策略生成与知识检索
- Business Agent支持策略结构化风险收益分析与横向对比，自动保存分析结果
- 一体化自动流程，采集-清洗-分析全自动

## 系统架构

```
agents/
├── crawler_agent/          # 数据采集模块
│   ├── company_data_collector.py      # 公司数据采集器
│   ├── company_financial_report_crawler.py  # 财报爬虫
│   └── data_source/        # 多数据源实现
├── data_clean_agent/       # 数据清洗模块
│   ├── data_clean_agent.py            # 数据清洗代理
│   ├── integrate_cninfo_financials.py # 巨潮三表整合
│   ├── merge_multi_source_financials.py # 多源财报合并
│   ├── langchain_pdf_structured.py    # PDF结构化抽取
│   └── pdf_processor.py    # PDF处理器
├── analysis_agent/         # 智能分析模块（LLM驱动多维度分析）
│   ├── analysis_agent.py               # 交互式分析主入口
│   ├── universal_llm_analyzer.py       # 通用LLM分析框架
│   ├── management_model_analyzer.py    # 管理模式分析
│   ├── business_model_analyzer.py      # 商业模式分析
│   ├── sales_model_analyzer.py         # 销售模式分析
│   ├── rd_production_model_analyzer.py # 研发生产模式分析
│   ├── assessment_model_analyzer.py    # 考核模式分析
│   ├── innovation_capability_analyzer.py # 创新能力分析
│   └── ...
├── visualization_agent/    # 可视化联动模块（自动生成与保存图表）
│   ├── visualization_agent.py      # 图表自动生成与保存
│   └── ...
├── expert_agent/           # 专家智能对话与知识检索模块
│   ├── expert_agent.py     # 专家代理主类，支持多轮对话、上下文理解
│   ├── dialog_manager.py   # 多轮对话管理器
│   ├── ...                 # 相关实现与配置
│   └── README.md           # expert_agent模块说明文档（推荐）
├── business_agent/         # 策略结构化分析与对比模块
│   ├── business_agent.py   # Business Agent主类，结构化分析与横向对比
│   └── README.md           # business_agent模块说明文档
├── common/                 # 公共模块
│   ├── base_agent.py       # 基础代理类
│   └── llm_base_agent.py   # LLM基础代理
├── config/                 # 配置文件
│   └── langchain_config.yaml
└── main.py                 # 主程序入口（采集-清洗-分析一体化）
```

> **可视化联动说明：**
> visualization_agent/ 目录为系统的自动可视化模块，负责根据 LLM 推荐的指标组合，批量生成并保存各类趋势图。所有分析模式均可自动调用该模块，无需手动干预，图片统一输出到 data/visualize/ 目录。

> **expert_agent说明：**
> expert_agent/ 目录为系统的专家智能对话与知识检索模块，支持：
> - 多轮上下文对话，自动理解用户意图
> - 结合FAISS向量库进行相关知识检索，辅助LLM生成更专业的策略建议
> - 支持对分析结果的追问、补充、细化，自动保存对话历史
> - 关键词抽取辅助知识检索，提升召回相关性
> 
> **详细设计与接口文档请见 [expert_agent/README.md](expert_agent/README.md)**

> **business_agent说明：**
> business_agent/ 目录为系统的策略结构化分析与对比模块，负责对 expert agent 生成的策略进行风险、收益、可行性等多维度结构化分析，并自动生成多策略横向对比分析，结果自动保存，便于后续查阅和复盘。

## 工作流程

### 1. 数据采集阶段

#### 1.1 多源数据采集
系统支持从以下数据源采集数据：

- **巨潮资讯网 (CNINFO)**
  - 三大财务报表（资产负债表、利润表、现金流量表）
  - 公司公告
  - 年报、季报等定期报告

- **东方财富 (Eastmoney)**
  - 财务数据
  - 行业研报
  - 公司公告

- **深交所 (SZSE)**
  - 上市公司财务数据
  - 公告信息

- **同花顺 (THSL)**
  - 财务数据（季度数据）
  - 市场数据

#### 1.2 数据采集流程
```python
# 单个公司数据采集
result = collect_single_company_data("贵州茅台")
```

> **说明：** 当前系统仅支持单公司采集流程，已移除批量公司采集相关功能。

### 2. 数据清洗与整合阶段

#### 2.1 巨潮三表整合
将巨潮资讯网的三大财务报表整合为年度财报：

```python
# 整合资产负债表、利润表、现金流量表
# 输出：data/cleaned/cninfo_financial_reports/
```

**处理逻辑：**
- 按公司代码和年份分组
- 合并三大表的字段
- 标准化字段名称
- 统一数据格式

#### 2.2 多源财报合并
使用LLM智能合并多个数据源的财报数据：

```python
# 数据源优先级：巨潮资讯网 > 深交所 > 东方财富 > 同花顺
# 输出：data/structured/all_merged_financial_reports.json
```

**合并策略：**
- 按公司代码和年份匹配
- 按数据源优先级解决冲突
- 使用Gemini LLM进行智能字段合并
- 去除重复和空值字段
- **字段标准化**：通过LLM prompt直接输出36个标准英文字段

**标准化字段**：详细字段说明请参考 [标准化字段文档](docs/standardized_fields.md)

#### 2.3 PDF文档结构化处理

**公告结构化抽取：**
```python
# 处理：output/announcements/
# 输出：data/structured/all_announcements_structured.json
```

**研报结构化抽取：**
```python
# 处理：output/industry_reports/
# 输出：data/structured/all_reports_structured.json
```

**抽取字段：**
- `company_name`: 公司名称
- `announcement_date`: 发布日期
- `announcement_type`: 公告/报告类型
- `title`: 标题
- `content_summary`: 内容摘要

### 3. 智能分析与专家对话阶段（Analysis Agent & Expert Agent）

#### 3.1 分析模式与能力
系统集成了基于大模型（LLM）和结构化数据的上市公司多维度智能分析模块（analysis_agent），支持一键式对公司进行六大核心维度的结构化深度分析：

- 管理模式分析
- 商业模式分析
- 销售模式分析
- 研发生产模式分析
- 考核模式分析
- 创新能力分析

#### 3.2 分析流程示例
```python
# 运行主程序，自动进入交互式分析
python main.py

# 或单独运行分析模块
python -m analysis_agent.analysis_agent
```

#### 3.3 分析报告输出
- data/analysis/management_analysis.json
- data/analysis/business_analysis.json
- data/analysis/sales_analysis.json
- data/analysis/rd_production_analysis.json
- data/analysis/assessment_analysis.json
- data/analysis/innovation_analysis.json

详细分析模式、报告模版、扩展方式等请见 [analysis_agent/README.md](analysis_agent/README.md)

#### 3.4 分析-可视化联动与智能推荐

系统支持“分析-可视化联动”闭环：
- LLM在结构化分析报告结尾，自动推荐最值得可视化的3-5组核心财务指标组合（如["roe", "gross_profit_margin", "net_profit_margin"]）。
- 主流程自动解析LLM返回的JSON推荐，批量生成组合折线图，每组指标一张图。
- 图片自动保存到 `data/visualize/` 目录，文件名包含指标组合和“llm_trend”后缀。
- 终端输出每张图片的保存路径，便于快速定位和查看。
- 支持所有分析模式（管理、商业、销售、研发、考核、创新）自动驱动可视化，无需手动传递数据。

**示例终端输出：**
```
[图片已保存到]: data/visualize/roe_gross_profit_margin_net_profit_margin_llm_trend.png
[图片已保存到]: data/visualize/roe_total_assets_llm_trend.png
```

如需自定义推荐逻辑、图表样式或导出方式，可在 analysis_agent/ 和 visualization_agent/ 目录下灵活扩展。

#### 3.5 专家智能对话与知识检索（Expert Agent）
- 支持多轮追问、上下文理解、知识检索与策略建议
- 结合FAISS向量库和LLM，提升专业性
- 对话历史自动保存，便于后续复盘与量化分析
- 关键词抽取辅助知识检索，提升召回相关性

> **详细用法与交互流程见“3.7 专家对话典型流程与用法”**

#### 3.7 专家对话典型流程与用法

**典型交互流程：**
1. 用户选择分析维度，系统输出结构化分析报告
2. 系统自动进入专家对话环节，用户可针对分析结果反复追问
3. 专家Agent自动结合知识库检索和LLM，生成专业建议或现状解读
4. 支持多轮追问，所有对话自动保存到 data/strategy/ 目录

**命令行示例：**
```
请选择要分析的模式 (输入数字): 2
=== 开始商业模式分析 ===
...（分析报告输出）...
欢迎进入智能分析多轮对话系统。输入 exit 可随时退出。
请输入你对本维度的进一步问题（输入exit退出）：如何提升市场规模？
建议： ...
理由： ...
风险： ...
对话结束。
对话历史已保存到: data/strategy/dialog_history_...json
```

> **详细设计与接口文档请见 [expert_agent/README.md](expert_agent/README.md)**

### 3.8 Business Agent（公司策略结构化与对比分析）

Business Agent 负责对 expert agent 生成的公司经营策略进行结构化分析，包括：
- 单条策略的风险、收益、可行性等多维度分析
- 多策略横向对比分析，给出优劣势、适配性、互补/冲突点和综合建议
- 自动保存分析结果，便于后续查阅和复盘

#### 输入
- expert agent 生成的对话历史文件（含策略、理由、风险等）
- analysis agent 传入的分析维度、公司名
- 行业背景向量库、公司财报分析数据

#### 输出
- 每条策略的结构化分析（markdown格式，分为四部分）
- 所有策略的横向对比分析
- 结果自动保存到 `data/biz_analysis/` 目录，文件名格式为：
  `biz_analysis_公司名_维度_时间戳.json`

#### 输出文件结构示例
```json
{
  "results": [
    {"strategy": "...", "analysis": "...markdown..."},
    ...
  ],
  "compare": "...横向对比分析markdown..."
}
```

详细说明请见 [business_agent/README.md](business_agent/README.md)

## 分析结果TXT/PDF自动导出说明

系统支持在analysis、expert、business三大流程中，自动将每一步的分析结果导出为txt和pdf文件，便于归档、查阅和后续处理。

- **导出目录结构**：
  - `/output/analysis_exports/`：存放analysis各维度分析结果的txt/pdf
  - `/output/expert_exports/`：存放expert多轮对话策略建议的txt/pdf
  - `/output/business_exports/`：存放business策略结构化分析及横向对比的txt/pdf

- **导出内容说明**：
  - analysis：导出每个分析维度的核心分析正文（自动去除嵌入的json代码块）
  - expert：仅在LLM生成有效策略建议时导出，每条策略与理由、风险一一对应
  - business：所有策略及其分析、横向对比合并为一个文件输出

- **内容格式**：
  - txt：原始分析内容（支持markdown或纯文本）
  - pdf：自动渲染markdown为富文本，纯文本自动排版

- **命令行提示**：
  - 每次导出后，命令行会输出如下提示，便于快速定位：
    ```
    [导出] TXT文件已保存到: /完整/绝对/路径/xxx.txt
    [导出] PDF文件已保存到: /完整/绝对/路径/xxx.pdf
    ```

- **依赖说明**：
  - 需安装 `markdown2`、`weasyprint`、`fpdf` 等依赖，详见 requirements_pdf.txt

如需自定义导出内容、格式或目录结构，可修改 `tool/json_exporter.py` 实现。

## 技术特性

### 1. 智能数据清洗
- **LLM辅助合并**：使用Gemini 2.0-flash-lite模型进行智能字段合并
- **多源数据融合**：支持4个主要数据源的自动整合
- **字段标准化**：统一中英文字段名，标准化数据格式

### 2. PDF文档处理
- **多格式支持**：支持PDF文本提取和结构化
- **智能信息抽取**：使用LangChain + Gemini进行关键信息提取
- **批量处理**：支持递归目录扫描和批量处理（仅限PDF等文档，不含公司数据采集）

### 3. 错误处理与容错
- **API配额管理**：自动处理LLM API配额限制
- **数据验证**：多层数据验证和错误恢复
- **日志记录**：完整的执行日志和错误追踪

## 使用方法

### 环境准备

```bash
# 1. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 2. 安装依赖
pip install -r requirements_langchain.txt
pip install -r requirements_pdf.txt

# 3. 配置API密钥
export GEMINI_API_KEY="your_gemini_api_key"
```

### 运行完整流程

```bash
# 设置Python路径
export PYTHONPATH=.

# 运行主程序（包含采集和清洗）
python main.py
```

### 单独运行模块

```bash
# 1. 只运行数据采集
python -m crawler_agent.company_data_collector

# 2. 只运行数据清洗
python -m data_clean_agent.data_clean_agent

# 3. 只运行PDF结构化抽取
python -m data_clean_agent.langchain_pdf_structured --data_type announcements
```

## 输出文件结构

```
data/
├── cleaned/                    # 中间清洗数据
│   ├── cninfo_financial_reports/    # 巨潮整合财报
│   ├── eastmoney_financial_reports/ # 东方财富财报
│   ├── szse_financial_reports/      # 深交所财报
│   └── thsl_financial_reports/      # 同花顺财报
└── structured/                 # 最终结构化数据
    ├── all_merged_financial_reports.json    # 合并财报
    ├── all_announcements_structured.json    # 公告信息
    └── all_reports_structured.json          # 研报信息

docs/
└── standardized_fields.md      # 标准化字段说明文档
```

## 配置说明

### LangChain配置 (config/langchain_config.yaml)
```yaml
llm:
  model: gemini-2.0-flash-lite
  temperature: 0.1
  max_tokens: 2000
  api_key: ${GEMINI_API_KEY}
```

### 数据源配置
- 支持自定义数据源优先级
- 可配置字段映射规则
- 支持数据源开关控制

## 性能优化

### 1. 文档批量处理
- 支持PDF文档批量处理
- 数据清洗批量执行

### 2. 缓存机制
- 中间结果缓存
- API调用结果缓存
- 避免重复处理

### 3. 内存管理
- 大文件分块处理
- 及时释放内存
- 流式数据处理

## 扩展性

### 1. 新数据源接入
- 实现标准数据源接口
- 配置字段映射规则
- 添加到合并流程

### 2. 新数据类型支持
- 扩展PDF处理器
- 添加新的结构化抽取模板
- 配置新的输出格式

### 3. LLM模型切换
- 支持多种LLM提供商
- 可配置模型参数
- 支持模型热切换

## 故障排除

### 常见问题

1. **LLM API配额超限**
   - 解决方案：切换API密钥或使用备用模型
   - 系统会自动降级到传统合并方法

2. **PDF解析失败**
   - 检查PDF文件完整性
   - 尝试不同的PDF解析库
   - 查看详细错误日志

3. **数据源连接失败**
   - 检查网络连接
   - 验证数据源配置
   - 查看数据源状态

### 日志查看

```bash
# 查看系统日志
tail -f logs/llm.log

# 查看爬虫日志
tail -f logs/company_website_crawler.log
```

## 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 联系方式

如有问题或建议，请通过以下方式联系：
- 提交Issue
- 发送邮件
- 参与讨论

---

**注意**：使用本系统时请遵守相关数据源的使用条款和法律法规。 