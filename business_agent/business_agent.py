import json
import os
from typing import List, Dict
import datetime
import sys
from tool.json_exporter import export_business_json

from common.llm_base_agent import LLMBaseAgent
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

# 维度到分析报告文件的映射
DIMENSION_TO_FILE = {
    "管理模式分析": "management_analysis.json",
    "商业模式分析": "business_analysis.json",
    "销售模式分析": "sales_analysis.json",
    "研发生产模式分析": "rd_production_analysis.json",
    "考核模式分析": "assessment_analysis.json",
    "创新能力分析": "innovation_analysis.json",
}

# LLM分析Prompt模板
EVAL_PROMPT = """
你是一名企业策略分析专家。请基于以下内容，对每条策略进行结构化分析，输出格式严格如下：

## 策略分析：{strategy}

1. 策略简要评价
2. 该策略对指定经营维度的正面和负面影响
3. 主要风险点与应对建议
4. 可行性与改进建议

请用markdown格式输出，所有小节均需有内容，禁止省略。

- 理由：{reasons}
- 风险：{risks}
- 公司财务数据概要：{financial_data_summary}
- 行业背景及类似案例：{industry_context}
"""

COMPARE_PROMPT = """
你是一名企业策略分析专家。请对以下所有策略的结构化分析结果进行横向对比，输出：
1. 各策略的核心优劣势对比
2. 哪些策略更适合当前公司和经营维度，理由是什么
3. 策略间的互补性或冲突点
4. 综合建议（可推荐优先级或组合策略）

请用markdown格式输出。

所有策略分析结果如下：
{all_analyses}
"""

def load_financial_analysis(dimension: str) -> Dict:
    filename = DIMENSION_TO_FILE.get(dimension)
    if not filename:
        raise ValueError(f"未知分析维度: {dimension}")
    path = os.path.join("data/analysis", filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"未找到分析报告: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def retrieve_industry_context(strategy_text: str, vectorstore, top_k: int = 5) -> str:
    docs = vectorstore.similarity_search(strategy_text, k=top_k)
    return "\n".join([doc.page_content for doc in docs])

class BusinessAgent:
    def __init__(self, llm_base_agent: LLMBaseAgent, vectorstore):
        self.llm_base_agent = llm_base_agent
        self.vectorstore = vectorstore
        # 创建分析链
        self.analysis_chain = self.llm_base_agent.create_chain(
            prompt_template=EVAL_PROMPT,
            input_variables=["strategy", "reasons", "risks", "financial_data_summary", "industry_context"]
        )

    def analyze_from_dialog_history(self, dialog_history_path, company_name, dimension, analysis_result=None):
        if not os.path.exists(dialog_history_path):
            raise FileNotFoundError(f"未找到对话历史文件: {dialog_history_path}")
        with open(dialog_history_path, "r", encoding="utf-8") as f:
            dialog_history = json.load(f)
        strategies, reasons, risks = [], [], []
        for turn in dialog_history:
            if (
                turn["role"] == "agent"
                and turn.get("company_name") == company_name
                and turn.get("dimension") == dimension
                and turn["content"].get("success")
            ):
                strategies = turn["content"].get("strategies", [])
                reasons = turn["content"].get("reasons", [])
                risks = turn["content"].get("risks", [])
                break  # 只取第一个匹配的agent输出
        results = []
        for i in range(len(strategies)):
            strategy = strategies[i]
            reason = reasons[i] if i < len(reasons) else ""
            risk = risks[i] if i < len(risks) else ""
            financial_analysis = load_financial_analysis(dimension)
            # 优先取 analysis_result 字段
            financial_data_summary = financial_analysis.get("analysis_result", "无该公司财报分析数据")
            industry_context = retrieve_industry_context(strategy, self.vectorstore)
            # 使用LLMBaseAgent的分析链
            if self.analysis_chain:
                analysis = self.analysis_chain.run(
                    strategy=strategy,
                    reasons=reason,
                    risks=risk,
                    financial_data_summary=financial_data_summary,
                    industry_context=industry_context
                )
            else:
                # 回退到直接拼prompt
                prompt = EVAL_PROMPT.format(
                    strategy=strategy,
                    reasons=reason,
                    risks=risk,
                    financial_data_summary=financial_data_summary,
                    industry_context=industry_context
                )
                analysis = self.llm_base_agent.llm_generate(prompt)
            
            print("\n================ Business 策略分析 ================")
            print(f"策略 {i+1}: {strategy}\n")
            print(analysis)
            print("====================================================\n")

            results.append({"strategy": strategy, "analysis": analysis})
        # 新增：策略对比分析
        all_analyses = "\n\n".join([r["analysis"] for r in results])
        compare_result = self.llm_base_agent.llm_generate(
            COMPARE_PROMPT.format(all_analyses=all_analyses)
        )
        
        print("\n================ Business 策略对比分析 ================")
        print(compare_result)
        print("=======================================================\n")
        # 保存文件时一并写入对比分析
        save_dir = "data/biz_analysis"
        os.makedirs(save_dir, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_company = str(company_name).replace('/', '_').replace(' ', '')
        safe_dim = str(dimension).replace('/', '_').replace(' ', '')
        save_path = os.path.join(save_dir, f"biz_analysis_{safe_company}_{safe_dim}_{ts}.json")
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump({"results": results, "compare": compare_result}, f, ensure_ascii=False, indent=2)
        print(f"Business分析结果已保存到: {save_path}")
        # 新增：导出为txt/pdf
        export_business_json(save_path)
        return results, compare_result
