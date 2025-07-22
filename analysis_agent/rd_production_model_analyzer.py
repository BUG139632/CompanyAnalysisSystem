"""
公司研发生产模式分析模块

基于财务指标和文档内容，使用LLM智能分析公司的研发生产模式
"""

import json
import os
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from .universal_llm_analyzer import UniversalLLMAnalyzer, AnalysisDimension


class RdProductionModelDimension(AnalysisDimension):
    """研发生产模式分析维度"""
    def __init__(self):
        super().__init__(
            name="rd_production_model",
            description="综合分析公司的研发生产模式"
        )
    def get_prompt_template(self) -> str:
        return """
你是一位专业的公司财务分析师。请根据下方提供的财务指标数据，分析各项研发/生产相关指标的年度变化、同比/环比、趋势等，并解释这些指标如何反映公司的研发创新能力、生产效率、成本控制、产能利用等。

公司信息：
- 公司名称：{company_name}
- 所属行业：{industry}

财务指标数据：
{financial_summary}

请完成以下分析任务：

1. **研发/生产指标趋势分析**：分析各项研发/生产相关财务指标的年度变化、同比/环比、趋势等。

2. **研发生产能力评价**：解释这些财务指标如何反映公司的研发创新能力、生产效率、成本控制、产能利用等。


请以如下JSON格式返回：
{{
  "analysis_result": "（包含研发/生产指标趋势分析和能力评价的完整分析内容，不要出现可视化推荐部分）",
  "recommended_visualization_metrics": [["rd_expense", "gross_profit_margin"], ["unit_cost", "capacity_utilization"] ...]
}}
"""
    def get_required_tags(self) -> List[str]:
        return ["rd_model", "production_model", "innovation", "technology", "manufacturing", "cost", "quality", "supply_chain", "automation", "digital"]
    def get_required_metrics(self) -> List[str]:
        return [
            "rd_expense", "rd_expense_ratio", "operating_cost", "capacity_utilization", "fixed_assets",
            "total_assets", "unit_cost", "gross_profit_margin", "net_profit", "net_profit_margin"
        ]


class RdProductionModelAnalyzer:
    """公司研发生产模式分析器（LLM增强版）"""
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.llm_analyzer = UniversalLLMAnalyzer()
        rd_dimension = RdProductionModelDimension()
        self.llm_analyzer.add_custom_dimension(rd_dimension)
        self._financial_data = None
        self._documents_data = None
        self._last_analysis_result = None
    def load_data_from_structured(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        try:
            financial_file = "data/structured/all_merged_financial_reports.json"
            if not os.path.exists(financial_file):
                raise FileNotFoundError(f"财务数据文件不存在: {financial_file}")
            with open(financial_file, 'r', encoding='utf-8') as f:
                financial_data = json.load(f)
            documents_file = "data/structured/all_announcements_structured.json"
            if not os.path.exists(documents_file):
                self.logger.warning(f"文档数据文件不存在: {documents_file}")
                documents_data = []
            else:
                with open(documents_file, 'r', encoding='utf-8') as f:
                    all_documents_data = json.load(f)
                documents_data = [item for item in all_documents_data if "error" not in item]
            self.logger.info(f"成功加载数据: 财务数据{len(financial_data)}条, 文档数据{len(documents_data)}条")
            return financial_data, documents_data
        except Exception as e:
            self.logger.error(f"加载数据失败: {str(e)}")
            raise
    def _ensure_data_loaded(self):
        if self._financial_data is None or self._documents_data is None:
            self._financial_data, self._documents_data = self.load_data_from_structured()
    def analyze_rd_production_model(self) -> Dict[str, Any]:
        try:
            self.logger.info("开始分析研发生产模式")
            self._ensure_data_loaded()
            if not self._financial_data:
                return {"error": "没有找到财务数据"}
            # 只传递财务数据，文档数据传空列表
            result = self.llm_analyzer.analyze_dimension("rd_production_model", self._financial_data, [])
            if "error" in result:
                self.logger.error(f"分析失败: {result['error']}")
                return result
            self._last_analysis_result = result
            result["analyzer_type"] = "RdProductionModelAnalyzer"
            result["analysis_method"] = "LLM增强分析"
            result["analysis_info"] = {
                "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "data_summary": {
                    "financial_records": len(self._financial_data),
                    "document_records": 0,
                    "companies": len(set(item.get("company_code") for item in self._financial_data if item.get("company_code")))
                }
            }
            self.logger.info("研发生产模式分析完成")
            return result
        except Exception as e:
            self.logger.error(f"分析研发生产模式时发生错误: {str(e)}")
            return {"error": f"分析失败: {str(e)}"} 