# Analysis Agent 模块说明

## 功能简介

Analysis Agent 是一个基于大模型（LLM）和结构化财务/文档数据的上市公司多维度智能分析系统。支持一键式对公司管理模式、商业模式、销售模式、研发生产模式、考核模式、创新能力等六大核心维度进行结构化深度分析。

- 支持自动加载结构化财务与公告数据
- 每个分析维度只计算所需财务指标，效率高、可扩展
- 分析报告为结构化文本，便于后续处理与展示
- 支持自定义分析维度、指标、Prompt
- **所有分析报告自动在内容前标注分析维度和参与分析的财务指标，便于溯源和自动化处理**

## 分析报告结构与自动标注（2024年7月更新）

每个分析报告（如 data/analysis/management_analysis.json）均为结构化JSON，核心字段如下：

- `analysis_result`：结构化分析内容，**正文最前面自动加上如下标注**：
  ```
  【分析维度】：综合分析公司的管理模式（management_model）
  【参与分析的财务指标】：roe, gross_profit_margin, ...
  
  ...（后续为各年度财务指标变化分析、趋势等结构化内容）
  ```
- `dimension`：分析维度英文名（如 management_model）
- `calculated_metrics`：本次参与分析的财务指标列表
- `recommended_visualization_metrics`：LLM推荐的可视化指标组合
- `visualization_image_paths`：本次生成的所有图表图片路径
- 其他元数据（分析时间、数据年份等）

**注意：所有分析维度（管理、商业、销售、研发生产、考核、创新）均自动带有上述标注，无需手动拼接。**

## 支持的分析模式与报告模版

所有分析维度（管理、商业、销售、研发生产、考核、创新）分析报告均采用如下统一结构化输出格式：

```
{
  "analysis_result": "## 财务指标分析\n\n### 1. 指标A\n- 年度数值：2020: xxx, 2021: xxx, ...\n- 趋势分析：...\n\n### 2. 指标B\n- 年度数值：...\n- 趋势分析：...\n\n...\n",
  "recommended_visualization_metrics": [["指标A"], ["指标B", "指标C"]]
}
```

其中：
- `analysis_result` 为各财务指标的年度数值与趋势分析（可多指标分节）。
- `recommended_visualization_metrics` 为 LLM 推荐的可视化指标组合。

**所有分析维度均采用此模版，无需区分。**

## 主要用法

1. 交互式分析：
   ```bash
   python -m analysis_agent.analysis_agent
   ```
   或在 main.py 集成全流程后：
   ```bash
   python main.py
   ```
   按提示选择分析模式，自动输出结构化报告。

2. 代码调用：
   ```python
   from analysis_agent.analysis_agent import analyze_management_model
   result = analyze_management_model()
   print(result['analysis_result'])
   # 输出示例：
   # 【分析维度】：综合分析公司的管理模式（management_model）
   # 【参与分析的财务指标】：roe, gross_profit_margin, ...
   # ...后续为结构化分析内容...
   ```
   其他模式调用方式类似。

## 扩展方式

- 新增分析维度：新建一个分析器文件，继承 AnalysisDimension，定义 get_prompt_template、get_required_tags、get_required_metrics。
- 支持自定义Prompt、指标、标签，灵活扩展。
- 支持多公司、多年度数据分析。

## 依赖说明
- 依赖 LangChain、Google Generative AI、Python >=3.8
- 需配置 GEMINI_API_KEY 环境变量
- 结构化数据需位于 data/structured/

## 目录结构
- analysis_agent/
  - analysis_agent.py（主入口，交互式分析）
  - universal_llm_analyzer.py（通用LLM分析框架）
  - management_model_analyzer.py
  - business_model_analyzer.py
  - sales_model_analyzer.py
  - rd_production_model_analyzer.py
  - assessment_model_analyzer.py
  - innovation_capability_analyzer.py
  - ...

## 联系方式
如需定制分析维度、集成更多LLM、对接外部系统等，请联系开发者。 