"""
公司考核模式分析模块

基于财务指标和文档内容，使用LLM智能分析公司的考核模式效果
"""

import json
import os
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from .universal_llm_analyzer import UniversalLLMAnalyzer, AnalysisDimension


class AssessmentModelDimension(AnalysisDimension):
    """考核模式分析维度"""
    
    def __init__(self):
        super().__init__(
            name="assessment_model",
            description="综合分析公司的考核模式效果"
        )
    
    def get_prompt_template(self) -> str:
        return """
你是一位专业的公司财务分析师。请根据下方提供的财务指标数据，分析各项考核相关指标的年度变化、同比/环比、趋势等，并解释这些指标如何反映公司绩效考核体系的有效性（如ROE、利润增长、资产周转等与考核挂钩的指标）。

公司信息：
- 公司名称：{company_name}
- 所属行业：{industry}

财务指标数据：
{financial_summary}

请完成以下分析任务：

1. **考核指标趋势分析**：分析各项考核相关财务指标的年度变化、同比/环比、趋势等。

2. **考核模式能力评价**：解释这些财务指标如何反映公司绩效考核体系的有效性，包括但不限于：盈利能力、增长能力、运营效率等。


请以如下JSON格式返回：
{{
  "analysis_result": "（包含考核指标趋势分析和考核模式能力评价的完整分析内容，不要出现可视化推荐部分）",
  "recommended_visualization_metrics": [["roe", "net_profit"], ["total_asset_turnover", "operating_profit"] ...]
}}
"""
    
    def get_required_tags(self) -> List[str]:
        return ["assessment", "evaluation", "performance", "kpi", "metrics", "governance", "management"]
    
    def get_required_metrics(self) -> List[str]:
        return [
            "roe", "roa", "gross_profit_margin", "net_profit_margin", 
            "total_asset_turnover", "operating_revenue", "operating_profit",
            "revenue", "net_profit", "total_assets", "total_equity",
            "operating_cash_flow", "current_ratio", "debt_to_equity_ratio"
        ]


class AssessmentModelAnalyzer:
    """公司考核模式分析器（LLM增强版）"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 创建通用LLM分析器（使用项目默认配置）
        self.llm_analyzer = UniversalLLMAnalyzer()
        
        # 添加评估模式分析维度
        assessment_dimension = AssessmentModelDimension()
        self.llm_analyzer.add_custom_dimension(assessment_dimension)
        
        # 缓存加载的数据，避免重复加载
        self._financial_data = None
        self._documents_data = None
        self._last_analysis_result = None
    
    def load_data_from_structured(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        从/data/structured目录加载数据
        
        Returns:
            (financial_data, documents_data) 元组
        """
        try:
            # 加载财务数据
            financial_file = "data/structured/all_merged_financial_reports.json"
            if not os.path.exists(financial_file):
                raise FileNotFoundError(f"财务数据文件不存在: {financial_file}")
            
            with open(financial_file, 'r', encoding='utf-8') as f:
                financial_data = json.load(f)
            
            # 加载文档数据
            documents_file = "data/structured/all_announcements_structured.json"
            if not os.path.exists(documents_file):
                self.logger.warning(f"文档数据文件不存在: {documents_file}")
                documents_data = []
            else:
                with open(documents_file, 'r', encoding='utf-8') as f:
                    all_documents_data = json.load(f)
                
                # 过滤有效的文档数据（排除有error字段的条目）
                documents_data = [item for item in all_documents_data if "error" not in item]
            
            self.logger.info(f"成功加载数据: 财务数据{len(financial_data)}条, 文档数据{len(documents_data)}条")
            return financial_data, documents_data
            
        except Exception as e:
            self.logger.error(f"加载数据失败: {str(e)}")
            raise
    
    def _ensure_data_loaded(self):
        """确保数据已加载（内部方法）"""
        if self._financial_data is None or self._documents_data is None:
            self._financial_data, self._documents_data = self.load_data_from_structured()
    
    def analyze_assessment_model(self) -> Dict[str, Any]:
        """
        分析评估模式
        
        Returns:
            分析结果字典
        """
        try:
            self.logger.info("开始分析考核模式")
            
            # 确保数据已加载
            self._ensure_data_loaded()
            
            if not self._financial_data:
                return {"error": "没有找到财务数据"}
            
            # 只传递财务数据，文档数据传空列表
            result = self.llm_analyzer.analyze_dimension("assessment_model", self._financial_data, [])
            
            if "error" in result:
                self.logger.error(f"分析失败: {result['error']}")
                return result
            
            # 缓存分析结果
            self._last_analysis_result = result
            
            # 添加分析器标识和分析信息
            result["analyzer_type"] = "AssessmentModelAnalyzer"
            result["analysis_method"] = "LLM增强分析"
            result["analysis_info"] = {
                "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "data_summary": {
                    "financial_records": len(self._financial_data),
                    "document_records": 0,
                    "companies": len(set(item.get("company_code") for item in self._financial_data if item.get("company_code")))
                }
            }
            
            self.logger.info("考核模式分析完成")
            return result
            
        except Exception as e:
            self.logger.error(f"分析考核模式时发生错误: {str(e)}")
            return {"error": f"分析失败: {str(e)}"}
    
    def get_last_analysis_result(self) -> Optional[Dict[str, Any]]:
        """获取最后一次分析结果"""
        return self._last_analysis_result 