"""
通用LLM分析接口模块

提供通用的LLM分析框架，支持不同维度的自定义prompt分析
"""

import json
import os
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from abc import ABC, abstractmethod

# LLM相关导入
try:
    from langchain_google_genai import GoogleGenerativeAI
    from langchain.prompts import PromptTemplate
    from langchain.chains import LLMChain
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    print("警告: 未安装langchain_google_genai，无法进行分析")


class DataPreprocessor:
    """数据预处理器 - 负责财务指标计算和文档过滤"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def prepare_financial_summary(self, financial_data: List[Dict[str, Any]], 
                                 required_metrics: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        准备财务数据汇总
        
        Args:
            financial_data: 原始财务数据列表
            required_metrics: 需要的财务指标列表，如果为None则计算所有指标
            
        Returns:
            汇总后的财务数据字典
        """
        if not financial_data:
            return {"error": "无财务数据"}
        
        try:
            # 获取公司基本信息
            company_info = financial_data[0]
            company_name = company_info.get("company_name", "未知公司")
            industry = company_info.get("industry", "未知行业")
            
            # 定义所有可用的财务指标映射
            all_metrics_mapping = {
                "roe": "roe",
                "roa": "roa", 
                "gross_profit_margin": "gross_profit_margin",
                "net_profit_margin": "net_profit_margin",
                "total_asset_turnover": "total_asset_turnover",
                "inventory_turnover": "inventory_turnover",
                "current_ratio": "current_ratio",
                "debt_to_equity_ratio": "debt_to_equity_ratio",
                "operating_cash_flow_ratio": "operating_cash_flow_ratio",
                "cash_ratio": "cash_ratio",
                "revenue": "revenue",
                "net_profit": "net_profit",
                "total_assets": "total_assets",
                "total_equity": "total_equity",
                "operating_revenue": "operating_revenue",
                "operating_cost": "operating_cost",
                "operating_profit": "operating_profit",
                "total_liabilities": "total_liabilities",
                "current_assets": "current_assets",
                "current_liabilities": "current_liabilities",
                "fixed_assets": "fixed_assets",
                "inventory": "inventory",
                "accounts_receivable": "accounts_receivable",
                "cash_and_equivalents": "cash_and_equivalents",
                "operating_cash_flow": "operating_cash_flow",
                "investing_cash_flow": "investing_cash_flow",
                "financing_cash_flow": "financing_cash_flow"
            }
            
            # 确定需要计算的指标
            if required_metrics is None:
                # 如果没有指定，计算所有指标
                metrics_to_calculate = all_metrics_mapping
            else:
                # 只计算需要的指标
                metrics_to_calculate = {}
                for metric in required_metrics:
                    if metric in all_metrics_mapping:
                        metrics_to_calculate[metric] = all_metrics_mapping[metric]
                    else:
                        self.logger.warning(f"未知的财务指标: {metric}")
            
            self.logger.info(f"将计算以下财务指标: {list(metrics_to_calculate.keys())}")
            
            # 按年份汇总财务指标
            yearly_metrics = {}
            for data in financial_data:
                year = data.get("year", "未知年份")
                metrics = {}
                
                # 只计算需要的指标
                for metric_name, metric_key in metrics_to_calculate.items():
                    value = data.get(metric_key)
                    if value is not None:
                        metrics[metric_name] = value
                
                if metrics:
                    yearly_metrics[year] = metrics
            
            # 计算趋势指标（只针对需要的指标）
            trends = self._calculate_trends(yearly_metrics, required_metrics)
            
            return {
                "company_name": company_name,
                "industry": industry,
                "yearly_metrics": yearly_metrics,
                "trends": trends,
                "latest_year": max(yearly_metrics.keys()) if yearly_metrics else None,
                "data_years": list(yearly_metrics.keys()),
                "calculated_metrics": list(metrics_to_calculate.keys())
            }
            
        except Exception as e:
            self.logger.error(f"财务数据汇总失败: {str(e)}")
            return {"error": f"财务数据汇总失败: {str(e)}"}
    
    def filter_documents_by_tags(self, documents_data: List[Dict[str, Any]], 
                                required_tags: List[str]) -> List[Dict[str, Any]]:
        """
        根据标签过滤文档
        
        Args:
            documents_data: 原始文档数据列表
            required_tags: 需要的标签列表
            
        Returns:
            过滤后的文档列表
        """
        if not documents_data:
            return []
        
        filtered_docs = []
        for doc in documents_data:
            tags = doc.get("tags", [])
            if any(tag in required_tags for tag in tags):
                filtered_docs.append(doc)
        
        return filtered_docs
    
    def prepare_documents_summary(self, documents_data: List[Dict[str, Any]], 
                                 max_docs: int = 10) -> Dict[str, Any]:
        """
        准备文档摘要汇总
        
        Args:
            documents_data: 文档数据列表
            max_docs: 最大文档数量
            
        Returns:
            文档摘要汇总
        """
        if not documents_data:
            return {"error": "无文档数据"}
        
        try:
            # 按类型分组
            doc_types = {}
            for doc in documents_data[:max_docs]:
                doc_type = doc.get("type", "其他")
                if doc_type not in doc_types:
                    doc_types[doc_type] = []
                doc_types[doc_type].append({
                    "title": doc.get("title", "无标题"),
                    "summary": doc.get("summary", "无摘要"),
                    "tags": doc.get("tags", [])
                })
            
            # 生成摘要文本
            summary_parts = []
            for doc_type, docs in doc_types.items():
                summary_parts.append(f"【{doc_type}】")
                for doc in docs:
                    summary_parts.append(f"- {doc['title']}: {doc['summary']}")
                summary_parts.append("")
            
            return {
                "total_documents": len(documents_data),
                "filtered_documents": len(documents_data[:max_docs]),
                "document_types": list(doc_types.keys()),
                "summary_text": "\n".join(summary_parts).strip(),
                "documents_by_type": doc_types
            }
            
        except Exception as e:
            self.logger.error(f"文档摘要准备失败: {str(e)}")
            return {"error": f"文档摘要准备失败: {str(e)}"}
    
    def _calculate_trends(self, yearly_metrics: Dict[str, Dict[str, Any]], 
                         required_metrics: Optional[List[str]] = None) -> Dict[str, Any]:
        """计算财务指标趋势"""
        if len(yearly_metrics) < 2:
            return {}
        
        trends = {}
        years = sorted(yearly_metrics.keys())
        
        # 确定需要计算趋势的指标
        if required_metrics is None:
            # 如果没有指定，计算关键指标的趋势
            metrics_to_trend = ["roe", "roa", "gross_profit_margin", "net_profit_margin", "revenue", "net_profit"]
        else:
            # 只计算需要的指标的趋势
            metrics_to_trend = required_metrics
        
        for metric in metrics_to_trend:
            values = []
            for year in years:
                if metric in yearly_metrics[year]:
                    values.append({
                        "year": year,
                        "value": yearly_metrics[year][metric]
                    })
            
            if len(values) >= 2:
                first_value = values[0]["value"]
                last_value = values[-1]["value"]
                
                if first_value != 0:
                    change_rate = (last_value - first_value) / first_value * 100
                    trends[metric] = {
                        "start_value": first_value,
                        "end_value": last_value,
                        "change_rate": round(change_rate, 2),
                        "trend": "上升" if change_rate > 5 else "下降" if change_rate < -5 else "稳定",
                        "periods": len(values)
                    }
        
        return trends


class AnalysisDimension(ABC):
    """分析维度抽象基类"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    @abstractmethod
    def get_prompt_template(self) -> str:
        """获取该维度的prompt模板"""
        pass
    
    @abstractmethod
    def get_required_tags(self) -> List[str]:
        """获取该维度需要的文档标签"""
        pass
    
    @abstractmethod
    def get_required_metrics(self) -> List[str]:
        """获取该维度需要的财务指标"""
        pass


class UniversalLLMAnalyzer:
    """通用LLM分析器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        if not LLM_AVAILABLE:
            raise ImportError("需要安装langchain_google_genai才能使用LLM分析功能")
        
        # 获取API密钥
        google_api_key = os.environ.get("GEMINI_API_KEY")
        if not google_api_key:
            raise ValueError("GEMINI_API_KEY 环境变量未设置，无法使用LLM分析功能")
        
        # 初始化LLM（使用项目默认配置）
        self.llm = GoogleGenerativeAI(
            model="gemini-2.0-flash-lite", 
            temperature=0.1,
            google_api_key=google_api_key
        )
        self.preprocessor = DataPreprocessor()
        
        # 分析维度字典
        self.dimensions = {}
    
    def analyze_dimension(self, dimension_name: str, 
                         financial_data: List[Dict[str, Any]], 
                         documents_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析指定维度
        
        Args:
            dimension_name: 维度名称
            financial_data: 财务数据
            documents_data: 文档数据
            
        Returns:
            分析结果
        """
        if dimension_name not in self.dimensions:
            return {"error": f"未知的分析维度: {dimension_name}"}
        
        dimension = self.dimensions[dimension_name]
        
        try:
            # 1. 数据预处理 - 根据维度需要计算特定指标
            required_metrics = dimension.get_required_metrics()
            financial_summary = self.preprocessor.prepare_financial_summary(financial_data, required_metrics)
            if "error" in financial_summary:
                return financial_summary
            
            # 2. 文档过滤
            required_tags = dimension.get_required_tags()
            filtered_docs = self.preprocessor.filter_documents_by_tags(documents_data, required_tags)
            documents_summary = self.preprocessor.prepare_documents_summary(filtered_docs)
            
            # 3. 创建分析链
            prompt_template = PromptTemplate(
                input_variables=["company_name", "industry", "financial_summary", "documents_summary"],
                template=dimension.get_prompt_template()
            )
            
            # 使用新的LangChain语法
            chain = prompt_template | self.llm
            response = chain.invoke({
                "company_name": financial_summary["company_name"],
                "industry": financial_summary["industry"],
                "financial_summary": json.dumps(financial_summary, ensure_ascii=False, indent=2),
                "documents_summary": documents_summary.get("summary_text", "无相关文档")
            })
            # === 新增：在分析内容前拼接维度和指标说明 ===
            dimension_label = f"【分析维度】：{dimension.description}（{dimension_name}）"
            metrics_label = f"【参与分析的财务指标】：{', '.join(financial_summary.get('calculated_metrics', []))}"
            response = f"{dimension_label}\n{metrics_label}\n\n{response}"
            # 直接返回LLM文本结果
            return {
                "analysis_result": response,
                "dimension": dimension_name,
                "calculated_metrics": financial_summary.get('calculated_metrics', []),
                "analysis_timestamp": datetime.now().isoformat(),
                "data_summary": {
                    "financial_years": financial_summary.get("data_years", []),
                    "documents_count": documents_summary.get("filtered_documents", 0),
                    "document_types": documents_summary.get("document_types", [])
                }
            }
            
        except Exception as e:
            self.logger.error(f"{dimension_name}维度分析失败: {str(e)}")
            return {"error": f"{dimension_name}维度分析失败: {str(e)}"}
    
    def analyze_multiple_dimensions(self, dimension_names: List[str],
                                  financial_data: List[Dict[str, Any]], 
                                  documents_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析多个维度
        
        Args:
            dimension_names: 维度名称列表
            financial_data: 财务数据
            documents_data: 文档数据
            
        Returns:
            综合分析结果
        """
        results = {}
        
        for dimension_name in dimension_names:
            result = self.analyze_dimension(dimension_name, financial_data, documents_data)
            results[dimension_name] = result
        
        # 计算综合评分
        scores = []
        for result in results.values():
            if "error" not in result and "score" in result:
                scores.append(result["score"])
        
        overall_score = sum(scores) / len(scores) if scores else 0
        
        return {
            "overall_score": round(overall_score, 2),
            "dimensions": results,
            "analysis_timestamp": datetime.now().isoformat(),
            "total_dimensions": len(dimension_names),
            "successful_dimensions": len([r for r in results.values() if "error" not in r])
        }
    
    def add_custom_dimension(self, dimension: AnalysisDimension):
        """添加自定义分析维度"""
        self.dimensions[dimension.name] = dimension
    
    def get_available_dimensions(self) -> List[str]:
        """获取可用的分析维度"""
        return list(self.dimensions.keys())
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """解析LLM响应"""
        try:
            # 尝试直接解析JSON
            if response.strip().startswith("{"):
                return json.loads(response)
            # 新正则：匹配最后一个 {...}，兼容 ```json ... ``` 包裹和裸 JSON
            import re
            matches = re.findall(r'```json[\s\S]*?({[\s\S]+?})[\s\S]*?```|({[\s\S]+?})', response)
            if matches:
                json_str = matches[-1][0] or matches[-1][1]
                return json.loads(json_str)
            return {
                "error": "无法解析LLM响应",
                "raw_response": response[:500]
            }
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析失败: {str(e)}")
            return {
                "error": f"JSON解析失败: {str(e)}",
                "raw_response": response[:500]
            } 