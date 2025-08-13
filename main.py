#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主程序入口
"""
import os
from crawler_agent.company_data_collector import (
    collect_single_company_data
)
from data_clean_agent.data_clean_agent import DataCleanAgent
from analysis_agent.analysis_agent import run_interactive_analysis


def main():
    """主函数"""
    quiet = os.getenv("QUIET", "1") == "1"
    if not quiet:
        print("🚀 公司数据采集与清洗系统启动")
        print("=" * 50)
    
    # 检测是否为自动测试环境
    if os.getenv("AUTO_TEST") == "1":
        user_input = os.getenv("COMPANY_NAME", "测试公司")
        if not quiet:
            print(f"🧪 自动测试模式，使用公司名称: {user_input}")
    else:
        # 用户交互输入公司名称
        user_input = input("请输入目标公司名称：\n> ").strip()
        if not user_input:
            if not quiet:
                print("未输入有效公司名称，程序退出。")
            return
    
    test_companies = [user_input]
    
    if not quiet:
        print(f"\n🎯 开始采集公司数据: {test_companies[0]}")
    result = collect_single_company_data(test_companies[0])
    if not quiet:
        print(f"✅ 采集完成: {result['公司名称'] if '公司名称' in result else result.get('company_name','')} ")
    
    # 数据清洗和结构化处理
    if not quiet:
        print(f"\n🧹 开始数据清洗和结构化处理...")
        print("=" * 50)
    
    try:
        # 初始化数据清洗代理
        clean_agent = DataCleanAgent(config_path="config/langchain_config.yaml")
        
        # 执行完整的清洗和合并流程
        clean_agent.run_full_clean_and_merge()
        
        if not quiet:
            print(f"\n🎉 数据清洗和结构化处理完成！")
            print("📁 输出文件位置:")
            print("   - 合并财报: data/structured/all_merged_financial_reports.json")
            print("   - 公告信息: data/structured/all_announcements_structured.json")
            print("   - 研报信息: data/structured/all_reports_structured.json")
        
    except Exception as e:
        if not quiet:
            print(f"❌ 数据清洗过程中出现错误: {e}")
            print("请检查数据源和配置是否正确")

    # 运行交互式分析系统 
    if not quiet:
        print("\n🧠 启动公司模式分析系统...")
    run_interactive_analysis()

if __name__ == "__main__":
    main()
