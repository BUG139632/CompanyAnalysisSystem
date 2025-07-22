# Expert Agent 模块说明

## 模块简介

`expert_agent` 是上市公司投资研究系统中的专家智能对话与知识检索模块。它支持基于LLM的多轮上下文对话、行业知识检索、上下文理解与策略建议生成，帮助用户在分析报告基础上获得更深入、个性化的专家解答。

## 主要功能
- 多轮上下文对话，自动理解用户意图
- 结合 FAISS 向量库进行相关知识检索，辅助 LLM 生成更专业的策略建议
- 支持对分析结果的追问、补充、细化，自动保存对话历史
- 关键词抽取辅助知识检索，提升召回相关性
- 自动区分描述性/策略性/补充性问题，智能引导对话

## 核心类与接口

- `ExpertAgent`
  - 入口类，负责多轮对话、知识检索、LLM调用、上下文管理
  - 主要方法：
    - `generate_strategies(user_question, analysis_result, dialog_history=None)`
    - `search_knowledge(query, top_k=5)`
    - `run_dialog(analysis_result, company_name, dimension)`
- `DialogManager`
  - 多轮对话管理器，负责对话流程、历史记录、用户输入管理

## 用法示例

```python
from expert_agent.expert_agent import ExpertAgent

agent = ExpertAgent()
analysis_result = "..."  # analysis_agent 生成的分析报告
agent.run_dialog(analysis_result, company_name="贵州茅台", dimension="商业模式分析")
```

或在主流程自动集成：
- analysis_agent 分析后，自动调用 expert_agent 进入多轮对话环节
- 用户可针对分析结果反复追问，系统自动检索知识并生成建议

## 知识检索与关键词抽取
- 内置 KeyBERT 中文关键词抽取模型，自动从用户问题中提取关键词，用于向量库检索
- 支持自定义检索模型和参数

## 对话历史管理
- 每次对话自动保存到 data/strategy/ 目录，文件名包含公司、维度、时间戳
- 便于后续复盘、量化分析和策略追踪

## 依赖说明
- 依赖 FAISS、KeyBERT、sentence-transformers、text2vec、LangChain、HuggingFace Embeddings 等
- 需提前构建好行业知识向量库（faiss_industry_reports/）

## 扩展建议
- 可集成更强的 LLM 或自定义 Prompt 优化对话体验
- 支持多语言、多行业知识库
- 可扩展为 RESTful API 或 Web 服务

---
如需详细接口文档或二次开发支持，请联系项目维护者。 