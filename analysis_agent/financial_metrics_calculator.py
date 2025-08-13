"""
财务指标计算器模块

基于标准化字段计算各种财务指标，包括：
- 盈利能力指标
- 偿债能力指标  
- 营运能力指标
- 成长能力指标
- 现金流量指标
- 市场价值指标

改进版本：更好地处理数据缺失情况
"""

from typing import Dict, List, Optional, Any, Union
import logging
import math


class MissingDataHandler:
    """缺失数据处理工具类"""
    
    @staticmethod
    def get_value(data: dict, field: str, default: Union[float, int] = 0) -> Union[float, int]:
        """
        安全获取数据值，处理None、空字符串等缺失值情况
        
        Args:
            data: 数据字典
            field: 字段名
            default: 默认值
            
        Returns:
            处理后的数值
        """
        value = data.get(field, default)
        
        # 处理各种缺失值情况
        if value is None:
            return default
        if isinstance(value, str):
            # 去除千分位逗号等格式，并尝试转换为数字
            value_clean = value.replace(',', '').strip()
            if value_clean == '':
                return default
            try:
                value = float(value_clean)
            except ValueError:
                return default
        if isinstance(value, (int, float)) and math.isnan(value):
            return default
        if isinstance(value, (int, float)) and math.isinf(value):
            return default
        
        # 确保返回数值类型
        if isinstance(value, (int, float)):
            return value
        else:
            return default
    
    @staticmethod
    def can_calculate_ratio(numerator: Union[float, int], denominator: Union[float, int], 
                          min_denominator: float = 0.01) -> bool:
        """
        检查是否可以计算比率
        
        Args:
            numerator: 分子
            denominator: 分母
            min_denominator: 最小分母值
            
        Returns:
            是否可以计算
        """
        return (denominator is not None and 
                not math.isnan(denominator) and 
                not math.isinf(denominator) and 
                abs(denominator) >= min_denominator)
    
    @staticmethod
    def safe_divide(numerator: Union[float, int], denominator: Union[float, int], 
                   default: float = 0.0, min_denominator: float = 0.01) -> float:
        """
        安全除法运算
        
        Args:
            numerator: 分子
            denominator: 分母
            default: 默认值
            min_denominator: 最小分母值
            
        Returns:
            除法结果或默认值
        """
        if MissingDataHandler.can_calculate_ratio(numerator, denominator, min_denominator):
            try:
                result = numerator / denominator
                if math.isnan(result) or math.isinf(result):
                    return default
                return result
            except (ZeroDivisionError, TypeError):
                return default
        return default


class ProfitabilityCalculator:
    """盈利能力指标计算器"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.data_handler = MissingDataHandler()
    
    def calculate_net_profit_margin(self, data: dict) -> Optional[float]:
        """净利率 = 归母净利润 / 营业总收入"""
        try:
            net_profit = self.data_handler.get_value(data, 'net_profit_attributable_to_parent')
            revenue = self.data_handler.get_value(data, 'total_operating_revenue')
            
            if revenue == 0:
                self.logger.warning("营业总收入为0，无法计算净利率")
                return None
                
            return self.data_handler.safe_divide(net_profit, revenue)
        except Exception as e:
            self.logger.error(f"计算净利率失败: {e}")
            return None
    
    def calculate_operating_profit_margin(self, data: dict) -> Optional[float]:
        """营业利润率 = 营业利润 / 营业总收入"""
        try:
            operating_profit = self.data_handler.get_value(data, 'operating_profit')
            revenue = self.data_handler.get_value(data, 'total_operating_revenue')
            
            if revenue == 0:
                self.logger.warning("营业总收入为0，无法计算营业利润率")
                return None
                
            return self.data_handler.safe_divide(operating_profit, revenue)
        except Exception as e:
            self.logger.error(f"计算营业利润率失败: {e}")
            return None
    
    def calculate_ebitda_margin(self, data: dict) -> Optional[float]:
        """EBITDA利润率 = (营业利润 + 折旧摊销) / 营业总收入"""
        try:
            operating_profit = self.data_handler.get_value(data, 'operating_profit')
            revenue = self.data_handler.get_value(data, 'total_operating_revenue')
            operating_cost = self.data_handler.get_value(data, 'total_operating_cost')
            
            if revenue == 0:
                self.logger.warning("营业总收入为0，无法计算EBITDA利润率")
                return None
            
            # 简化计算，假设折旧摊销为营业成本的10%
            depreciation = operating_cost * 0.1
            ebitda = operating_profit + depreciation
            
            return self.data_handler.safe_divide(ebitda, revenue)
        except Exception as e:
            self.logger.error(f"计算EBITDA利润率失败: {e}")
            return None
    
    def calculate_roa(self, data: dict) -> Optional[float]:
        """总资产收益率 = 归母净利润 / 总资产"""
        try:
            net_profit = self.data_handler.get_value(data, 'net_profit_attributable_to_parent')
            total_assets = self.data_handler.get_value(data, 'total_assets')
            
            if total_assets == 0:
                self.logger.warning("总资产为0，无法计算ROA")
                return None
                
            return self.data_handler.safe_divide(net_profit, total_assets)
        except Exception as e:
            self.logger.error(f"计算ROA失败: {e}")
            return None
    
    def calculate_roic(self, data: dict) -> Optional[float]:
        """投入资本回报率 = 营业利润 / (总资产 - 流动负债)"""
        try:
            operating_profit = self.data_handler.get_value(data, 'operating_profit')
            total_assets = self.data_handler.get_value(data, 'total_assets')
            current_liabilities = self.data_handler.get_value(data, 'total_current_liabilities')
            
            invested_capital = total_assets - current_liabilities
            
            if invested_capital <= 0:
                self.logger.warning("投入资本小于等于0，无法计算ROIC")
                return None
                
            return self.data_handler.safe_divide(operating_profit, invested_capital)
        except Exception as e:
            self.logger.error(f"计算ROIC失败: {e}")
            return None


class SolvencyCalculator:
    """偿债能力指标计算器"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.data_handler = MissingDataHandler()
    
    def calculate_current_ratio(self, data: dict) -> Optional[float]:
        """流动比率 = 流动资产 / 流动负债"""
        try:
            current_assets = self.data_handler.get_value(data, 'total_current_assets')
            current_liabilities = self.data_handler.get_value(data, 'total_current_liabilities')
            
            if current_liabilities == 0:
                self.logger.warning("流动负债为0，无法计算流动比率")
                return None
                
            return self.data_handler.safe_divide(current_assets, current_liabilities)
        except Exception as e:
            self.logger.error(f"计算流动比率失败: {e}")
            return None
    
    def calculate_quick_ratio(self, data: dict) -> Optional[float]:
        """速动比率 = (流动资产 - 存货) / 流动负债"""
        try:
            current_assets = self.data_handler.get_value(data, 'total_current_assets')
            current_liabilities = self.data_handler.get_value(data, 'total_current_liabilities')
            
            if current_liabilities == 0:
                self.logger.warning("流动负债为0，无法计算速动比率")
                return None
            
            # 简化计算，假设存货为流动资产的30%
            inventory = current_assets * 0.3
            quick_assets = current_assets - inventory
            
            return self.data_handler.safe_divide(quick_assets, current_liabilities)
        except Exception as e:
            self.logger.error(f"计算速动比率失败: {e}")
            return None
    
    def calculate_cash_ratio(self, data: dict) -> Optional[float]:
        """现金比率 = 货币资金 / 流动负债"""
        try:
            cash = self.data_handler.get_value(data, 'cash_and_cash_equivalents')
            current_liabilities = self.data_handler.get_value(data, 'total_current_liabilities')
            
            if current_liabilities == 0:
                self.logger.warning("流动负债为0，无法计算现金比率")
                return None
                
            return self.data_handler.safe_divide(cash, current_liabilities)
        except Exception as e:
            self.logger.error(f"计算现金比率失败: {e}")
            return None
    
    def calculate_debt_to_equity_ratio(self, data: dict) -> Optional[float]:
        """资产负债率 = 总负债 / 所有者权益"""
        try:
            total_liabilities = self.data_handler.get_value(data, 'total_liabilities')
            total_equity = self.data_handler.get_value(data, 'total_owners_equity')
            
            if total_equity == 0:
                self.logger.warning("所有者权益为0，无法计算资产负债率")
                return None
                
            return self.data_handler.safe_divide(total_liabilities, total_equity)
        except Exception as e:
            self.logger.error(f"计算资产负债率失败: {e}")
            return None
    
    def calculate_debt_to_assets_ratio(self, data: dict) -> Optional[float]:
        """负债资产比率 = 总负债 / 总资产"""
        try:
            total_liabilities = self.data_handler.get_value(data, 'total_liabilities')
            total_assets = self.data_handler.get_value(data, 'total_assets')
            
            if total_assets == 0:
                self.logger.warning("总资产为0，无法计算负债资产比率")
                return None
                
            return self.data_handler.safe_divide(total_liabilities, total_assets)
        except Exception as e:
            self.logger.error(f"计算负债资产比率失败: {e}")
            return None


class OperatingEfficiencyCalculator:
    """营运能力指标计算器"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.data_handler = MissingDataHandler()
    
    def calculate_total_asset_turnover(self, data: dict) -> Optional[float]:
        """总资产周转率 = 营业总收入 / 总资产"""
        try:
            revenue = self.data_handler.get_value(data, 'total_operating_revenue')
            total_assets = self.data_handler.get_value(data, 'total_assets')
            
            if total_assets == 0:
                self.logger.warning("总资产为0，无法计算总资产周转率")
                return None
                
            return self.data_handler.safe_divide(revenue, total_assets)
        except Exception as e:
            self.logger.error(f"计算总资产周转率失败: {e}")
            return None
    
    def calculate_fixed_asset_turnover(self, data: dict) -> Optional[float]:
        """固定资产周转率 = 营业总收入 / 非流动资产"""
        try:
            revenue = self.data_handler.get_value(data, 'total_operating_revenue')
            non_current_assets = self.data_handler.get_value(data, 'total_non_current_assets')
            
            if non_current_assets == 0:
                self.logger.warning("非流动资产为0，无法计算固定资产周转率")
                return None
                
            return self.data_handler.safe_divide(revenue, non_current_assets)
        except Exception as e:
            self.logger.error(f"计算固定资产周转率失败: {e}")
            return None
    
    def calculate_equity_turnover(self, data: dict) -> Optional[float]:
        """权益周转率 = 营业总收入 / 所有者权益"""
        try:
            revenue = self.data_handler.get_value(data, 'total_operating_revenue')
            total_equity = self.data_handler.get_value(data, 'total_owners_equity')
            
            if total_equity == 0:
                self.logger.warning("所有者权益为0，无法计算权益周转率")
                return None
                
            return self.data_handler.safe_divide(revenue, total_equity)
        except Exception as e:
            self.logger.error(f"计算权益周转率失败: {e}")
            return None
    
    def calculate_working_capital_turnover(self, data: dict) -> Optional[float]:
        """营运资金周转率 = 营业总收入 / (流动资产 - 流动负债)"""
        try:
            revenue = self.data_handler.get_value(data, 'total_operating_revenue')
            current_assets = self.data_handler.get_value(data, 'total_current_assets')
            current_liabilities = self.data_handler.get_value(data, 'total_current_liabilities')
            
            working_capital = current_assets - current_liabilities
            
            if working_capital <= 0:
                self.logger.warning("营运资金小于等于0，无法计算营运资金周转率")
                return None
                
            return self.data_handler.safe_divide(revenue, working_capital)
        except Exception as e:
            self.logger.error(f"计算营运资金周转率失败: {e}")
            return None


class GrowthCalculator:
    """成长能力指标计算器"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.data_handler = MissingDataHandler()
    
    def calculate_revenue_growth_rate(self, current_data: dict, previous_data: dict) -> Optional[float]:
        """营收增长率 = (当期营收 - 上期营收) / 上期营收"""
        try:
            if not previous_data:
                self.logger.warning("缺少上期数据，无法计算营收增长率")
                return None
                
            current_revenue = self.data_handler.get_value(current_data, 'total_operating_revenue')
            previous_revenue = self.data_handler.get_value(previous_data, 'total_operating_revenue')
            
            if previous_revenue == 0:
                self.logger.warning("上期营收为0，无法计算营收增长率")
                return None
                
            return self.data_handler.safe_divide(current_revenue - previous_revenue, previous_revenue)
        except Exception as e:
            self.logger.error(f"计算营收增长率失败: {e}")
            return None
    
    def calculate_profit_growth_rate(self, current_data: dict, previous_data: dict) -> Optional[float]:
        """净利润增长率 = (当期净利润 - 上期净利润) / 上期净利润"""
        try:
            if not previous_data:
                self.logger.warning("缺少上期数据，无法计算净利润增长率")
                return None
                
            current_profit = self.data_handler.get_value(current_data, 'net_profit_attributable_to_parent')
            previous_profit = self.data_handler.get_value(previous_data, 'net_profit_attributable_to_parent')
            
            if previous_profit == 0:
                self.logger.warning("上期净利润为0，无法计算净利润增长率")
                return None
                
            return self.data_handler.safe_divide(current_profit - previous_profit, previous_profit)
        except Exception as e:
            self.logger.error(f"计算净利润增长率失败: {e}")
            return None
    
    def calculate_asset_growth_rate(self, current_data: dict, previous_data: dict) -> Optional[float]:
        """总资产增长率 = (当期总资产 - 上期总资产) / 上期总资产"""
        try:
            if not previous_data:
                self.logger.warning("缺少上期数据，无法计算总资产增长率")
                return None
                
            current_assets = self.data_handler.get_value(current_data, 'total_assets')
            previous_assets = self.data_handler.get_value(previous_data, 'total_assets')
            
            if previous_assets == 0:
                self.logger.warning("上期总资产为0，无法计算总资产增长率")
                return None
                
            return self.data_handler.safe_divide(current_assets - previous_assets, previous_assets)
        except Exception as e:
            self.logger.error(f"计算总资产增长率失败: {e}")
            return None
    
    def calculate_equity_growth_rate(self, current_data: dict, previous_data: dict) -> Optional[float]:
        """所有者权益增长率 = (当期所有者权益 - 上期所有者权益) / 上期所有者权益"""
        try:
            if not previous_data:
                self.logger.warning("缺少上期数据，无法计算所有者权益增长率")
                return None
                
            current_equity = self.data_handler.get_value(current_data, 'total_owners_equity')
            previous_equity = self.data_handler.get_value(previous_data, 'total_owners_equity')
            
            if previous_equity == 0:
                self.logger.warning("上期所有者权益为0，无法计算所有者权益增长率")
                return None
                
            return self.data_handler.safe_divide(current_equity - previous_equity, previous_equity)
        except Exception as e:
            self.logger.error(f"计算所有者权益增长率失败: {e}")
            return None


class CashFlowCalculator:
    """现金流量指标计算器"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.data_handler = MissingDataHandler()
    
    def calculate_operating_cash_flow_ratio(self, data: dict) -> Optional[float]:
        """经营现金流量比率 = 经营活动现金流量净额 / 流动负债"""
        try:
            operating_cash_flow = self.data_handler.get_value(data, 'net_cash_flow_from_operating_activities')
            current_liabilities = self.data_handler.get_value(data, 'total_current_liabilities')
            
            if current_liabilities == 0:
                self.logger.warning("流动负债为0，无法计算经营现金流量比率")
                return None
                
            return self.data_handler.safe_divide(operating_cash_flow, current_liabilities)
        except Exception as e:
            self.logger.error(f"计算经营现金流量比率失败: {e}")
            return None
    
    def calculate_cash_flow_coverage_ratio(self, data: dict) -> Optional[float]:
        """现金流量保障倍数 = 经营活动现金流量净额 / 总负债"""
        try:
            operating_cash_flow = self.data_handler.get_value(data, 'net_cash_flow_from_operating_activities')
            total_liabilities = self.data_handler.get_value(data, 'total_liabilities')
            
            if total_liabilities == 0:
                self.logger.warning("总负债为0，无法计算现金流量保障倍数")
                return None
                
            return self.data_handler.safe_divide(operating_cash_flow, total_liabilities)
        except Exception as e:
            self.logger.error(f"计算现金流量保障倍数失败: {e}")
            return None
    
    def calculate_cash_flow_to_revenue_ratio(self, data: dict) -> Optional[float]:
        """现金流量收入比 = 经营活动现金流量净额 / 营业总收入"""
        try:
            operating_cash_flow = self.data_handler.get_value(data, 'net_cash_flow_from_operating_activities')
            revenue = self.data_handler.get_value(data, 'total_operating_revenue')
            
            if revenue == 0:
                self.logger.warning("营业总收入为0，无法计算现金流量收入比")
                return None
                
            return self.data_handler.safe_divide(operating_cash_flow, revenue)
        except Exception as e:
            self.logger.error(f"计算现金流量收入比失败: {e}")
            return None
    
    def calculate_free_cash_flow(self, data: dict) -> Optional[float]:
        """自由现金流量 = 经营活动现金流量净额 + 投资活动现金流量净额"""
        try:
            operating_cash_flow = self.data_handler.get_value(data, 'net_cash_flow_from_operating_activities')
            investing_cash_flow = self.data_handler.get_value(data, 'net_cash_flow_from_investing_activities')
            
            return operating_cash_flow + investing_cash_flow
        except Exception as e:
            self.logger.error(f"计算自由现金流量失败: {e}")
            return None
    
    def calculate_cash_flow_quality_ratio(self, data: dict) -> Optional[float]:
        """现金流量质量比率 = 经营活动现金流量净额 / 归母净利润"""
        try:
            operating_cash_flow = self.data_handler.get_value(data, 'net_cash_flow_from_operating_activities')
            net_profit = self.data_handler.get_value(data, 'net_profit_attributable_to_parent')
            
            if net_profit == 0:
                self.logger.warning("归母净利润为0，无法计算现金流量质量比率")
                return None
                
            return self.data_handler.safe_divide(operating_cash_flow, net_profit)
        except Exception as e:
            self.logger.error(f"计算现金流量质量比率失败: {e}")
            return None


class MarketValueCalculator:
    """市场价值指标计算器"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.data_handler = MissingDataHandler()
    
    def calculate_pe_ratio(self, data: dict, market_price: float) -> Optional[float]:
        """市盈率 = 股价 / 每股收益"""
        try:
            if not market_price or market_price <= 0:
                self.logger.warning("股价无效，无法计算市盈率")
                return None
                
            eps = self.data_handler.get_value(data, 'earnings_per_share')
            
            if eps <= 0:
                self.logger.warning("每股收益小于等于0，无法计算市盈率")
                return None
                
            return self.data_handler.safe_divide(market_price, eps)
        except Exception as e:
            self.logger.error(f"计算市盈率失败: {e}")
            return None
    
    def calculate_pb_ratio(self, data: dict, market_price: float) -> Optional[float]:
        """市净率 = 股价 / 每股净资产"""
        try:
            if not market_price or market_price <= 0:
                self.logger.warning("股价无效，无法计算市净率")
                return None
                
            book_value_per_share = self.data_handler.get_value(data, 'book_value_per_share')
            
            if book_value_per_share <= 0:
                self.logger.warning("每股净资产小于等于0，无法计算市净率")
                return None
                
            return self.data_handler.safe_divide(market_price, book_value_per_share)
        except Exception as e:
            self.logger.error(f"计算市净率失败: {e}")
            return None
    
    def calculate_ps_ratio(self, data: dict, market_price: float, shares_outstanding: float) -> Optional[float]:
        """市销率 = 市值 / 营业收入"""
        try:
            if not market_price or market_price <= 0:
                self.logger.warning("股价无效，无法计算市销率")
                return None
                
            if not shares_outstanding or shares_outstanding <= 0:
                self.logger.warning("流通股数无效，无法计算市销率")
                return None
                
            revenue = self.data_handler.get_value(data, 'total_operating_revenue')
            
            if revenue <= 0:
                self.logger.warning("营业收入小于等于0，无法计算市销率")
                return None
                
            market_cap = market_price * shares_outstanding
            return self.data_handler.safe_divide(market_cap, revenue)
        except Exception as e:
            self.logger.error(f"计算市销率失败: {e}")
            return None


class ComprehensiveFinancialCalculator:
    """综合财务指标计算器"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.profitability_calc = ProfitabilityCalculator()
        self.solvency_calc = SolvencyCalculator()
        self.operating_calc = OperatingEfficiencyCalculator()
        self.growth_calc = GrowthCalculator()
        self.cash_flow_calc = CashFlowCalculator()
        self.market_value_calc = MarketValueCalculator()
        self.data_handler = MissingDataHandler()
    
    def calculate_all_metrics(self, data: dict, previous_data: Optional[dict] = None, 
                            market_price: Optional[float] = None, shares_outstanding: Optional[float] = None) -> dict:
        """计算所有财务指标"""
        try:
            results = {
                "profitability": self._calculate_profitability_metrics(data),
                "solvency": self._calculate_solvency_metrics(data),
                "operating_efficiency": self._calculate_operating_metrics(data),
                "cash_flow": self._calculate_cash_flow_metrics(data),
                "market_value": self._calculate_market_value_metrics(data, market_price, shares_outstanding)
            }
            
            # 如果有历史数据，计算成长指标
            if previous_data:
                results["growth"] = self._calculate_growth_metrics(data, previous_data)
            
            return results
        except Exception as e:
            self.logger.error(f"计算财务指标失败: {e}")
            return {}
    
    def _calculate_profitability_metrics(self, data: dict) -> dict:
        """计算盈利能力指标"""
        return {
            "gross_profit_margin": self.data_handler.get_value(data, 'gross_profit_margin'),  # 已有
            "net_profit_margin": self.profitability_calc.calculate_net_profit_margin(data),
            "operating_profit_margin": self.profitability_calc.calculate_operating_profit_margin(data),
            "roe": self.data_handler.get_value(data, 'roe'),  # 已有
            "roa": self.profitability_calc.calculate_roa(data),
            "roic": self.profitability_calc.calculate_roic(data)
        }
    
    def _calculate_solvency_metrics(self, data: dict) -> dict:
        """计算偿债能力指标"""
        return {
            "current_ratio": self.solvency_calc.calculate_current_ratio(data),
            "quick_ratio": self.solvency_calc.calculate_quick_ratio(data),
            "cash_ratio": self.solvency_calc.calculate_cash_ratio(data),
            "debt_to_equity_ratio": self.solvency_calc.calculate_debt_to_equity_ratio(data),
            "debt_to_assets_ratio": self.solvency_calc.calculate_debt_to_assets_ratio(data)
        }
    
    def _calculate_operating_metrics(self, data: dict) -> dict:
        """计算营运能力指标"""
        return {
            "total_asset_turnover": self.operating_calc.calculate_total_asset_turnover(data),
            "fixed_asset_turnover": self.operating_calc.calculate_fixed_asset_turnover(data),
            "equity_turnover": self.operating_calc.calculate_equity_turnover(data),
            "working_capital_turnover": self.operating_calc.calculate_working_capital_turnover(data),
            "accounts_receivable_turnover": self.data_handler.get_value(data, 'accounts_receivable_turnover'),  # 已有
            "inventory_turnover": self.data_handler.get_value(data, 'inventory_turnover')  # 已有
        }
    
    def _calculate_cash_flow_metrics(self, data: dict) -> dict:
        """计算现金流量指标"""
        return {
            "operating_cash_flow_ratio": self.cash_flow_calc.calculate_operating_cash_flow_ratio(data),
            "cash_flow_coverage_ratio": self.cash_flow_calc.calculate_cash_flow_coverage_ratio(data),
            "cash_flow_to_revenue_ratio": self.cash_flow_calc.calculate_cash_flow_to_revenue_ratio(data),
            "free_cash_flow": self.cash_flow_calc.calculate_free_cash_flow(data),
            "cash_flow_quality_ratio": self.cash_flow_calc.calculate_cash_flow_quality_ratio(data)
        }
    
    def _calculate_growth_metrics(self, current_data: dict, previous_data: dict) -> dict:
        """计算成长能力指标"""
        return {
            "revenue_growth_rate": self.growth_calc.calculate_revenue_growth_rate(current_data, previous_data),
            "profit_growth_rate": self.growth_calc.calculate_profit_growth_rate(current_data, previous_data),
            "asset_growth_rate": self.growth_calc.calculate_asset_growth_rate(current_data, previous_data),
            "equity_growth_rate": self.growth_calc.calculate_equity_growth_rate(current_data, previous_data)
        }
    
    def _calculate_market_value_metrics(self, data: dict, market_price: Optional[float], shares_outstanding: Optional[float]) -> dict:
        """计算市场价值指标"""
        if not market_price:
            return {}
        
        return {
            "pe_ratio": self.market_value_calc.calculate_pe_ratio(data, market_price),
            "pb_ratio": self.market_value_calc.calculate_pb_ratio(data, market_price),
            "ps_ratio": self.market_value_calc.calculate_ps_ratio(data, market_price, shares_outstanding) if shares_outstanding else None
        }
    
    def calculate_metrics_for_company(self, company_data: List[dict], market_price: Optional[float] = None, 
                                    shares_outstanding: Optional[float] = None) -> dict:
        """为公司的多期数据计算财务指标"""
        try:
            if not company_data:
                return {}
            
            # 按年份排序
            sorted_data = sorted(company_data, key=lambda x: x.get('year', ''))
            
            results = {
                "company_code": sorted_data[0].get('company_code', ''),
                "company_name": sorted_data[0].get('company_name', ''),
                "periods": {}
            }
            
            for i, data in enumerate(sorted_data):
                previous_data = sorted_data[i-1] if i > 0 else None
                period_key = data.get('year', f'period_{i}')
                
                results["periods"][period_key] = self.calculate_all_metrics(
                    data, previous_data, market_price, shares_outstanding
                )
            
            return results
        except Exception as e:
            self.logger.error(f"计算公司财务指标失败: {e}")
            return {} 