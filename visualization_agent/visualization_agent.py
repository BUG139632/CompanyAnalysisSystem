import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

# ---- 中文字体自动检测 ----
preferred_fonts = ["Noto Sans CJK SC", "Noto Sans CJK", "WenQuanYi Zen Hei", "Arial Unicode MS"]
available_fonts = {f.name for f in fm.fontManager.ttflist}
for font in preferred_fonts:
    if font in available_fonts:
        plt.rcParams["font.sans-serif"] = [font]
        break
else:
    # 若没有可用中文字体，只给一次性警告
    import warnings
    warnings.warn("⚠️ 未检测到中文字体，中文字符可能无法显示")

plt.rcParams['axes.unicode_minus'] = False
import seaborn as sns
import numpy as np
import json
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../analysis_agent')))
from financial_metrics_calculator import ComprehensiveFinancialCalculator


# 只包含financial_metrics_calculator.py输出的所有财政指标的映射表
METRIC_CHART_TYPE_MAP = {
    # 盈利能力
    "gross_profit_margin": "trend",
    "net_profit_margin": "trend",
    "operating_profit_margin": "trend",
    "roe": "trend",
    "roa": "trend",
    "roic": "trend",
    # 偿债能力
    "current_ratio": "trend",
    "quick_ratio": "trend",
    "cash_ratio": "trend",
    "debt_to_equity_ratio": "trend",
    "debt_to_assets_ratio": "trend",
    # 营运能力
    "total_asset_turnover": "trend",
    "fixed_asset_turnover": "trend",
    "equity_turnover": "trend",
    "working_capital_turnover": "trend",
    "accounts_receivable_turnover": "trend",
    "inventory_turnover": "trend",
    # 成长能力
    "revenue_growth_rate": "trend",
    "profit_growth_rate": "trend",
    "asset_growth_rate": "trend",
    "equity_growth_rate": "trend",
    # 现金流量
    "operating_cash_flow_ratio": "trend",
    "cash_flow_coverage_ratio": "trend",
    "cash_flow_to_revenue_ratio": "trend",
    "free_cash_flow": "trend",
    "cash_flow_quality_ratio": "trend",
    # 市场价值
    "pe_ratio": "trend",
    "pb_ratio": "trend",
    "ps_ratio": "trend",
}

def choose_chart_type(metric_name: str) -> str:
    """
    根据指标名返回推荐的图表类型（trend, compare, structure, radar），默认为trend。
    """
    return METRIC_CHART_TYPE_MAP.get(metric_name, "trend")


def auto_visualize_metric(metric_type, x=None, y=None, labels=None, sizes=None, categories=None, values=None, title="", xlabel="", ylabel="", legend=None, save_path=None, show=True):
    """
    根据metric_type自动选择图表类型并绘制。
    支持：trend（折线图）、compare（柱状图）、structure（饼图）、radar（雷达图）
    参数：
        metric_type: str, 图表类型（trend, compare, structure, radar）
        x, y: 折线/柱状图的x、y数据
        labels, sizes: 饼图的标签和数值
        categories, values: 雷达图的维度和数值
        title, xlabel, ylabel, legend: 图表标题和标签
        save_path: 保存路径（如不为None则保存图片）
        show: 是否直接展示
    """
    plt.figure(figsize=(8, 5))
    if metric_type == "trend":
        # 折线图
        sns.lineplot(x=x, y=y, marker="o", label=legend)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.xticks(rotation=45)  # 旋转横坐标标签，避免重叠
    elif metric_type == "compare":
        # 柱状图
        sns.barplot(x=x, y=y)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.xticks(rotation=45)  # 旋转横坐标标签，避免重叠
    elif metric_type == "structure":
        # 饼图
        plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        plt.axis('equal')
    elif metric_type == "radar":
        # 雷达图
        if categories is None or values is None:
            raise ValueError("雷达图需提供categories和values参数")
        num_vars = len(categories)
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
        values = list(values)
        values += values[:1]
        angles += angles[:1]
        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
        ax.plot(angles, values, 'o-', linewidth=2)
        ax.fill(angles, values, alpha=0.25)
        ax.set_thetagrids(np.degrees(angles[:-1]), categories)
        ax.set_ylim(0, max(values))
        plt.title(title)
        if save_path:
            plt.savefig(save_path, bbox_inches='tight')
        if show:
            plt.show()
        return
    else:
        raise ValueError(f"未知的metric_type: {metric_type}")
    plt.title(title)
    if legend and metric_type != "structure":
        plt.legend()
    if save_path:
        plt.savefig(save_path, bbox_inches='tight')
    if show:
        plt.show()


class LineChartVisualizer:
    """
    折线图可视化实现类
    """
    def __init__(self):
        pass

    def plot(self, x, y, title="", xlabel="", ylabel="", legend=None, save_path=None, show=True):
        import matplotlib.pyplot as plt
        import seaborn as sns
        plt.figure(figsize=(8, 5))
        sns.lineplot(x=x, y=y, marker="o", label=legend)
        plt.title(title)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.xticks(rotation=45)  # 旋转横坐标标签，避免重叠
        if legend:
            plt.legend()
        if save_path:
            plt.savefig(save_path, bbox_inches='tight')
        if show:
            plt.show()


def plot_multi_line_chart(x, y_dict, title="", xlabel="", ylabel="", save_path=None, show=True):
    """
    绘制多指标组合折线图（每个指标一条线）。
    1. 自动将 None 值替换为 np.nan 以避免绘图错误
    2. 如果所有值均为 nan 或空，则跳过该指标
    3. 在保存图片前自动创建目录
    """
    import matplotlib.pyplot as plt
    import numpy as np

    plt.figure(figsize=(10, 6))
    has_valid_line = False
    for metric, y in y_dict.items():
        # 将 None 转为 np.nan，保持列表长度一致
        y_processed = [np.nan if v is None else v for v in y]
        # 如果全部为 nan，跳过该指标
        if all(v is np.nan or (isinstance(v, float) and np.isnan(v)) for v in y_processed):
            continue
        plt.plot(x, y_processed, marker="o", label=metric.upper())
        has_valid_line = True

    if not has_valid_line:
        raise ValueError("所有指标值均为空，无法绘制图表")

    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xticks(rotation=45)
    plt.legend()

    if save_path:
        # 自动创建保存目录
        save_dir = os.path.dirname(save_path)
        if save_dir and not os.path.exists(save_dir):
            os.makedirs(save_dir, exist_ok=True)
        plt.savefig(save_path, bbox_inches='tight')
        print(f"[图片已保存到]: {save_path}")
    if show:
        plt.show()


# 示例：绘制ROE折线图并保存
if __name__ == "__main__":
    # 1. 读取结构化财报数据
    with open("data/structured/all_merged_financial_reports.json", "r", encoding="utf-8") as f:
        company_data = json.load(f)

    # 2. 计算每年ROE
    calc = ComprehensiveFinancialCalculator()
    years = []
    roe_values = []
    for report in company_data:
        year = report.get("year") or report.get("报告期") or report.get("date")
        metrics = calc._calculate_profitability_metrics(report)
        roe = metrics.get("roe")
        if roe is not None and year is not None:
            years.append(str(year))
            roe_values.append(roe)

    # 3. 可视化
    save_path = "output/visualize/roe_trend.png"
    visualizer = LineChartVisualizer()
    visualizer.plot(
        x=years,
        y=roe_values,
        title="ROE趋势",
        xlabel="年份",
        ylabel="ROE",
        legend="ROE",
        save_path=save_path,
        show=False
    )
    print(f"ROE折线图已保存到: {save_path}")
