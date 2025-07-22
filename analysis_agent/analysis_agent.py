"""
分析代理主模块

提供公司管理模式分析的主要接口
"""

import json
import os
import logging
from typing import Dict, Optional, Any
from datetime import datetime
from analysis_agent.management_model_analyzer import ManagementModelAnalyzer
from analysis_agent.assessment_model_analyzer import AssessmentModelAnalyzer
from analysis_agent.business_model_analyzer import BusinessModelAnalyzer
from analysis_agent.sales_model_analyzer import SalesModelAnalyzer
from analysis_agent.rd_production_model_analyzer import RdProductionModelAnalyzer
from analysis_agent.innovation_capability_analyzer import InnovationCapabilityAnalyzer
from visualization_agent.visualization_agent import auto_visualize_metric, choose_chart_type
import re
from expert_agent.expert_agent import ExpertAgent
from expert_agent.dialog_manager import DialogManager
import sys
from tool.json_exporter import export_analysis_json


def get_available_analysis_modes() -> Dict[str, str]:
    """
    获取可用的分析模式
    
    Returns:
        分析模式字典 {模式代码: 模式描述}
    """
    return {
        "1": "管理模式分析",
        "2": "商业模式分析", 
        "3": "销售模式分析",
        "4": "研发生产模式分析",
        "5": "考核模式分析",
        "6": "创新能力分析"
    }


def display_analysis_modes():
    """显示可用的分析模式"""
    modes = get_available_analysis_modes()
    print("\n=== 可用的分析模式 ===")
    for code, description in modes.items():
        print(f"{code}. {description}")
    print("0. 退出")


def get_user_choice() -> str:
    """
    获取用户选择的分析模式
    
    Returns:
        用户选择的模式代码
    """
    while True:
        try:
            choice = input("\n请选择要分析的模式 (输入数字): ").strip()
            if choice == "0":
                return "0"
            
            modes = get_available_analysis_modes()
            if choice in modes:
                return choice
            else:
                print(f"❌ 无效选择: {choice}")
                print("请输入有效的数字选项")
        except KeyboardInterrupt:
            print("\n\n用户取消操作")
            return "0"
        except Exception as e:
            print(f"❌ 输入错误: {e}")


def analyze_management_model(output_path: str = "data/analysis/management_analysis.json") -> Dict[str, Any]:
    """
    分析管理模式
    
    Args:
        output_path: 输出文件路径，默认为data/analysis/management_analysis.json
        
    Returns:
        分析结果字典
    """
    try:
        logger = logging.getLogger(__name__)
        logger.info("开始分析管理模式")
        
        # 创建管理模式分析器（使用项目默认配置）
        analyzer = ManagementModelAnalyzer()
        
        # 进行分析（现在直接返回包含洞察的完整结果）
        result = analyzer.analyze_management_model()
        
        # 自动可视化并收集图片路径
        visualization_image_paths = []
        if "error" not in result:
            # 1. 先尝试直接取 result 的 recommended_visualization_metrics
            metric_groups = result.get('recommended_visualization_metrics', [])
            # 2. 如果没有，再尝试从 analysis_result 里提取 JSON
            def extract_json_from_response(response):
                import re, json
                matches = re.findall(r'```json[\s\S]*?({[\s\S]+?})[\s\S]*?```|({[\s\S]+?})', response)
                if matches:
                    json_str = matches[-1][0] or matches[-1][1]
                    try:
                        return json.loads(json_str)
                    except Exception as e:
                        print("JSON解析失败:", e)
                return None
            if not metric_groups and isinstance(result.get('analysis_result'), str):
                parsed = extract_json_from_response(result['analysis_result'])
                if parsed and 'recommended_visualization_metrics' in parsed:
                    metric_groups = parsed['recommended_visualization_metrics']
            if metric_groups and analyzer._financial_data:
                years = [str(item.get("year")) for item in analyzer._financial_data if item.get("year") is not None]
                from visualization_agent.visualization_agent import plot_multi_line_chart
                for group in metric_groups:
                    y_dict = {metric: [item.get(metric) for item in analyzer._financial_data] for metric in group}
                    save_path = f"output/visualize/{'_'.join(group)}_llm_trend.png"
                    try:
                        plot_multi_line_chart(
                            x=years,
                            y_dict=y_dict,
                            title=f"{'/'.join(group).upper()} 趋势",
                            xlabel="年份",
                            ylabel="指标值",
                            save_path=save_path,
                            show=False
                        )
                        visualization_image_paths.append(save_path)
                        print(f"{group} 组合图表已保存到: {save_path}")
                    except Exception as e:
                        print(f"[ERROR] 绘制 {group} 组合图表失败: {e}")
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            # 写入图片路径字段
            result['visualization_image_paths'] = visualization_image_paths
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.info(f"分析结果已保存到: {output_path}")
            # 新增：分析结果导出为txt/pdf
            export_analysis_json(output_path)
        logger.info("管理模式分析完成")
        return result
    except Exception as e:
        logging.error(f"分析管理模式失败: {str(e)}")
        return {"error": f"分析失败: {str(e)}"}


def analyze_business_model(output_path: str = "data/analysis/business_analysis.json") -> Dict[str, Any]:
    """
    分析商业模式
    
    Args:
        output_path: 输出文件路径，默认为data/analysis/business_analysis.json
        
    Returns:
        分析结果字典
    """
    try:
        logger = logging.getLogger(__name__)
        logger.info("开始分析商业模式")
        analyzer = BusinessModelAnalyzer()
        result = analyzer.analyze_business_model()
        visualization_image_paths = []
        if "error" not in result:
            metric_groups = result.get('recommended_visualization_metrics', [])
            def extract_json_from_response(response):
                import re, json
                matches = re.findall(r'```json[\s\S]*?({[\s\S]+?})[\s\S]*?```|({[\s\S]+?})', response)
                if matches:
                    json_str = matches[-1][0] or matches[-1][1]
                    try:
                        return json.loads(json_str)
                    except Exception as e:
                        print("JSON解析失败:", e)
                return None
            if not metric_groups and isinstance(result.get('analysis_result'), str):
                parsed = extract_json_from_response(result['analysis_result'])
                if parsed and 'recommended_visualization_metrics' in parsed:
                    metric_groups = parsed['recommended_visualization_metrics']
            if metric_groups and analyzer._financial_data:
                years = [str(item.get("year")) for item in analyzer._financial_data if item.get("year") is not None]
                from visualization_agent.visualization_agent import plot_multi_line_chart
                for group in metric_groups:
                    y_dict = {metric: [item.get(metric) for item in analyzer._financial_data] for metric in group}
                    save_path = f"output/visualize/{'_'.join(group)}_llm_trend.png"
                    try:
                        plot_multi_line_chart(
                            x=years,
                            y_dict=y_dict,
                            title=f"{'/'.join(group).upper()} 趋势",
                            xlabel="年份",
                            ylabel="指标值",
                            save_path=save_path,
                            show=False
                        )
                        visualization_image_paths.append(save_path)
                        print(f"{group} 组合图表已保存到: {save_path}")
                    except Exception as e:
                        print(f"[ERROR] 绘制 {group} 组合图表失败: {e}")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            result['visualization_image_paths'] = visualization_image_paths
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.info(f"分析结果已保存到: {output_path}")
            # 新增：分析结果导出为txt/pdf
            export_analysis_json(output_path)
        logger.info("商业模式分析完成")
        return result
    except Exception as e:
        logging.error(f"分析商业模式失败: {str(e)}")
        return {"error": f"分析失败: {str(e)}"}


def analyze_sales_model(output_path: str = "data/analysis/sales_analysis.json") -> Dict[str, Any]:
    """
    分析销售模式
    
    Args:
        output_path: 输出文件路径，默认为data/analysis/sales_analysis.json
        
    Returns:
        分析结果字典
    """
    try:
        logger = logging.getLogger(__name__)
        logger.info("开始分析销售模式")
        analyzer = SalesModelAnalyzer()
        result = analyzer.analyze_sales_model()
        visualization_image_paths = []
        if "error" not in result:
            metric_groups = result.get('recommended_visualization_metrics', [])
            def extract_json_from_response(response):
                import re, json
                matches = re.findall(r'```json[\s\S]*?({[\s\S]+?})[\s\S]*?```|({[\s\S]+?})', response)
                if matches:
                    json_str = matches[-1][0] or matches[-1][1]
                    try:
                        return json.loads(json_str)
                    except Exception as e:
                        print("JSON解析失败:", e)
                return None
            if not metric_groups and isinstance(result.get('analysis_result'), str):
                parsed = extract_json_from_response(result['analysis_result'])
                if parsed and 'recommended_visualization_metrics' in parsed:
                    metric_groups = parsed['recommended_visualization_metrics']
            if metric_groups and analyzer._financial_data:
                years = [str(item.get("year")) for item in analyzer._financial_data if item.get("year") is not None]
                from visualization_agent.visualization_agent import plot_multi_line_chart
                for group in metric_groups:
                    y_dict = {metric: [item.get(metric) for item in analyzer._financial_data] for metric in group}
                    save_path = f"output/visualize/{'_'.join(group)}_llm_trend.png"
                    try:
                        plot_multi_line_chart(
                            x=years,
                            y_dict=y_dict,
                            title=f"{'/'.join(group).upper()} 趋势",
                            xlabel="年份",
                            ylabel="指标值",
                            save_path=save_path,
                            show=False
                        )
                        visualization_image_paths.append(save_path)
                        print(f"{group} 组合图表已保存到: {save_path}")
                    except Exception as e:
                        print(f"[ERROR] 绘制 {group} 组合图表失败: {e}")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            result['visualization_image_paths'] = visualization_image_paths
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.info(f"分析结果已保存到: {output_path}")
            # 新增：分析结果导出为txt/pdf
            export_analysis_json(output_path)
        logger.info("销售模式分析完成")
        return result
    except Exception as e:
        logging.error(f"分析销售模式失败: {str(e)}")
        return {"error": f"分析失败: {str(e)}"}


def analyze_rd_production_model(output_path: str = "data/analysis/rd_production_analysis.json") -> Dict[str, Any]:
    """
    分析研发生产模式
    
    Args:
        output_path: 输出文件路径，默认为data/analysis/rd_production_analysis.json
        
    Returns:
        分析结果字典
    """
    try:
        logger = logging.getLogger(__name__)
        logger.info("开始分析研发生产模式")
        analyzer = RdProductionModelAnalyzer()
        result = analyzer.analyze_rd_production_model()
        visualization_image_paths = []
        if "error" not in result:
            metric_groups = result.get('recommended_visualization_metrics', [])
            def extract_json_from_response(response):
                import re, json
                matches = re.findall(r'```json[\s\S]*?({[\s\S]+?})[\s\S]*?```|({[\s\S]+?})', response)
                if matches:
                    json_str = matches[-1][0] or matches[-1][1]
                    try:
                        return json.loads(json_str)
                    except Exception as e:
                        print("JSON解析失败:", e)
                return None
            if not metric_groups and isinstance(result.get('analysis_result'), str):
                parsed = extract_json_from_response(result['analysis_result'])
                if parsed and 'recommended_visualization_metrics' in parsed:
                    metric_groups = parsed['recommended_visualization_metrics']
            if metric_groups and analyzer._financial_data:
                years = [str(item.get("year")) for item in analyzer._financial_data if item.get("year") is not None]
                from visualization_agent.visualization_agent import plot_multi_line_chart
                for group in metric_groups:
                    y_dict = {metric: [item.get(metric) for item in analyzer._financial_data] for metric in group}
                    save_path = f"output/visualize/{'_'.join(group)}_llm_trend.png"
                    try:
                        plot_multi_line_chart(
                            x=years,
                            y_dict=y_dict,
                            title=f"{'/'.join(group).upper()} 趋势",
                            xlabel="年份",
                            ylabel="指标值",
                            save_path=save_path,
                            show=False
                        )
                        visualization_image_paths.append(save_path)
                        print(f"{group} 组合图表已保存到: {save_path}")
                    except Exception as e:
                        print(f"[ERROR] 绘制 {group} 组合图表失败: {e}")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            result['visualization_image_paths'] = visualization_image_paths
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.info(f"分析结果已保存到: {output_path}")
            # 新增：分析结果导出为txt/pdf
            export_analysis_json(output_path)
        logger.info("研发生产模式分析完成")
        return result
    except Exception as e:
        logging.error(f"分析研发生产模式失败: {str(e)}")
        return {"error": f"分析失败: {str(e)}"}


def analyze_assessment_model(output_path: str = "data/analysis/assessment_analysis.json") -> Dict[str, Any]:
    """
    分析考核模式
    
    Args:
        output_path: 输出文件路径，默认为data/analysis/assessment_analysis.json
        
    Returns:
        分析结果字典
    """
    try:
        logger = logging.getLogger(__name__)
        logger.info("开始分析考核模式")
        analyzer = AssessmentModelAnalyzer()
        result = analyzer.analyze_assessment_model()
        visualization_image_paths = []
        if "error" not in result:
            metric_groups = result.get('recommended_visualization_metrics', [])
            def extract_json_from_response(response):
                import re, json
                matches = re.findall(r'```json[\s\S]*?({[\s\S]+?})[\s\S]*?```|({[\s\S]+?})', response)
                if matches:
                    json_str = matches[-1][0] or matches[-1][1]
                    try:
                        return json.loads(json_str)
                    except Exception as e:
                        print("JSON解析失败:", e)
                return None
            if not metric_groups and isinstance(result.get('analysis_result'), str):
                parsed = extract_json_from_response(result['analysis_result'])
                if parsed and 'recommended_visualization_metrics' in parsed:
                    metric_groups = parsed['recommended_visualization_metrics']
            if metric_groups and analyzer._financial_data:
                years = [str(item.get("year")) for item in analyzer._financial_data if item.get("year") is not None]
                from visualization_agent.visualization_agent import plot_multi_line_chart
                for group in metric_groups:
                    y_dict = {metric: [item.get(metric) for item in analyzer._financial_data] for metric in group}
                    save_path = f"output/visualize/{'_'.join(group)}_llm_trend.png"
                    try:
                        plot_multi_line_chart(
                            x=years,
                            y_dict=y_dict,
                            title=f"{'/'.join(group).upper()} 趋势",
                            xlabel="年份",
                            ylabel="指标值",
                            save_path=save_path,
                            show=False
                        )
                        visualization_image_paths.append(save_path)
                        print(f"{group} 组合图表已保存到: {save_path}")
                    except Exception as e:
                        print(f"[ERROR] 绘制 {group} 组合图表失败: {e}")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            result['visualization_image_paths'] = visualization_image_paths
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.info(f"分析结果已保存到: {output_path}")
            # 新增：分析结果导出为txt/pdf
            export_analysis_json(output_path)
        logger.info("考核模式分析完成")
        return result
    except Exception as e:
        logging.error(f"分析考核模式失败: {str(e)}")
        return {"error": f"分析失败: {str(e)}"}


def analyze_innovation_capability(output_path: str = "data/analysis/innovation_analysis.json") -> Dict[str, Any]:
    """
    分析创新能力
    
    Args:
        output_path: 输出文件路径，默认为data/analysis/innovation_analysis.json
        
    Returns:
        分析结果字典
    """
    try:
        logger = logging.getLogger(__name__)
        logger.info("开始分析创新能力")
        analyzer = InnovationCapabilityAnalyzer()
        result = analyzer.analyze_innovation_capability()
        visualization_image_paths = []
        if "error" not in result:
            metric_groups = result.get('recommended_visualization_metrics', [])
            def extract_json_from_response(response):
                import re, json
                matches = re.findall(r'```json[\s\S]*?({[\s\S]+?})[\s\S]*?```|({[\s\S]+?})', response)
                if matches:
                    json_str = matches[-1][0] or matches[-1][1]
                    try:
                        return json.loads(json_str)
                    except Exception as e:
                        print("JSON解析失败:", e)
                return None
            if not metric_groups and isinstance(result.get('analysis_result'), str):
                parsed = extract_json_from_response(result['analysis_result'])
                if parsed and 'recommended_visualization_metrics' in parsed:
                    metric_groups = parsed['recommended_visualization_metrics']
            if metric_groups and analyzer._financial_data:
                years = [str(item.get("year")) for item in analyzer._financial_data if item.get("year") is not None]
                from visualization_agent.visualization_agent import plot_multi_line_chart
                for group in metric_groups:
                    y_dict = {metric: [item.get(metric) for item in analyzer._financial_data] for metric in group}
                    save_path = f"output/visualize/{'_'.join(group)}_llm_trend.png"
                    try:
                        plot_multi_line_chart(
                            x=years,
                            y_dict=y_dict,
                            title=f"{'/'.join(group).upper()} 趋势",
                            xlabel="年份",
                            ylabel="指标值",
                            save_path=save_path,
                            show=False
                        )
                        visualization_image_paths.append(save_path)
                        print(f"{group} 组合图表已保存到: {save_path}")
                    except Exception as e:
                        print(f"[ERROR] 绘制 {group} 组合图表失败: {e}")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            result['visualization_image_paths'] = visualization_image_paths
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.info(f"分析结果已保存到: {output_path}")
            # 新增：分析结果导出为txt/pdf
            export_analysis_json(output_path)
        logger.info("创新能力分析完成")
        return result
    except Exception as e:
        logging.error(f"分析创新能力失败: {str(e)}")
        return {"error": f"分析失败: {str(e)}"}


def visualize_metrics_from_analysis(result, financial_data=None):
    # 新版：支持 LLM JSON 格式推荐
    import os
    from visualization_agent.visualization_agent import plot_multi_line_chart
    def extract_json_from_response(response):
        import re, json
        matches = re.findall(r'```json[\s\S]*?({[\s\S]+?})[\s\S]*?```|({[\s\S]+?})', response)
        if matches:
            json_str = matches[-1][0] or matches[-1][1]
            try:
                return json.loads(json_str)
            except Exception as e:
                print("JSON解析失败:", e)
        return None
    # 1. 先尝试直接取 result 的 recommended_visualization_metrics
    metric_groups = result.get('recommended_visualization_metrics', [])
    # 2. 如果没有，再尝试从 analysis_result 里提取 JSON
    if not metric_groups and isinstance(result.get('analysis_result'), str):
        parsed = extract_json_from_response(result['analysis_result'])
        if parsed and 'recommended_visualization_metrics' in parsed:
            metric_groups = parsed['recommended_visualization_metrics']
    if not metric_groups:
        print("未获得 LLM 推荐的可视化指标组合")
        return
    # 3. 获取年份和数据
    if financial_data is None:
        print("未传入结构化财务数据，无法自动可视化")
        return
    years = [str(item.get("year")) for item in financial_data if item.get("year") is not None]
    for group in metric_groups:
        y_dict = {metric: [item.get(metric) for item in financial_data] for metric in group}
        save_path = f"output/visualize/{'_'.join(group)}_llm_trend.png"
        try:
            plot_multi_line_chart(
                x=years,
                y_dict=y_dict,
                title=f"{'/'.join(group).upper()} 趋势",
                xlabel="年份",
                ylabel="指标值",
                save_path=save_path,
                show=False
            )
            print(f"{group} 组合图表已保存到: {save_path}")
        except Exception as e:
            print(f"[ERROR] 绘制 {group} 组合图表失败: {e}")


def extract_json_from_response(response):
    # 匹配最后一个 {...} 或 ```json ... ```
    matches = re.findall(r'```json\\s*({[\\s\\S]+?})\\s*```|({[\\s\\S]+?})', response)
    if matches:
        json_str = matches[-1][0] or matches[-1][1]
        try:
            return json.loads(json_str)
        except Exception as e:
            print("JSON解析失败:", e)
    return None


def run_expert_dialog_after_analysis(result, company_name, dimension):
    """
    在分析后自动调用 ExpertAgent 进行多轮专家建议对话，并保存对话历史。
    """
    expert_agent = ExpertAgent()
    expert_agent.run_dialog(result, company_name, dimension)


def run_interactive_analysis():
    """
    运行交互式分析
    """
    print("欢迎使用公司模式分析系统！")
    while True:
        display_analysis_modes()
        choice = get_user_choice()
        if choice == "0":
            print("感谢使用，再见！")
            break
        modes = get_available_analysis_modes()
        mode_name = modes[choice]
        print(f"\n=== 开始{mode_name} ===")
        # 新增：根据模式选择对应的输出路径
        output_paths = {
            "1": "data/analysis/management_analysis.json",
            "2": "data/analysis/business_analysis.json",
            "3": "data/analysis/sales_analysis.json",
            "4": "data/analysis/rd_production_analysis.json",
            "5": "data/analysis/assessment_analysis.json",
            "6": "data/analysis/innovation_analysis.json"
        }
        output_path = output_paths.get(choice)
        if not output_path:
            # fallback: 默认路径
            output_path = f"data/analysis/analysis_{choice}.json"
        # 先定义 dimension
        dimension = ""
        if choice == "1":
            result = analyze_management_model(output_path=output_path)
            dimension = "管理模式分析"
        elif choice == "2":
            result = analyze_business_model(output_path=output_path)
            dimension = "商业模式分析"
        elif choice == "3":
            result = analyze_sales_model(output_path=output_path)
            dimension = "销售模式分析"
        elif choice == "4":
            result = analyze_rd_production_model(output_path=output_path)
            dimension = "研发生产模式分析"
        elif choice == "5":
            result = analyze_assessment_model(output_path=output_path)
            dimension = "考核模式分析"
        elif choice == "6":
            result = analyze_innovation_capability(output_path=output_path)
            dimension = "创新能力分析"
        else:
            print("❌ 未知的分析模式")
            continue
        # 自动可视化（如有需要）
        if "error" not in result:
            print("✓ 分析完成")
            print("\n分析结果:")
            llm_response = result.get('analysis_result', '')
            parsed = extract_json_from_response(llm_response)
            if parsed and 'analysis_result' in parsed:
                print(parsed['analysis_result'])
            else:
                print(llm_response)
            # 新增：分析结果导出为txt/pdf
            export_analysis_json(output_path)
            # === 集成 ExpertAgent 多轮对话 ===
            company_name = result.get("company_name", "未知公司")
            run_expert_dialog_after_analysis(result, company_name, dimension)
        else:
            print(f"❌ 分析失败: {result['error']}")
        try:
            continue_choice = input("\n是否继续分析其他模式？(y/n): ").strip().lower()
            if continue_choice not in ['y', 'yes', '是']:
                print("感谢使用，再见！")
                break
        except KeyboardInterrupt:
            print("\n\n感谢使用，再见！")
            break


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 运行交互式分析
    run_interactive_analysis()
