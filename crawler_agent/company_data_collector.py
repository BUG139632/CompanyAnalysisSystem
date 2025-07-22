#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公司数据采集器
用于采集指定公司的财报、公告和行业研报
"""
import json
import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional

# 导入数据源模块
from crawler_agent.data_source.eastmoney_data_source import (
    fetch_eastmoney_announcements,
    fetch_eastmoney_annual_reports,
    fetch_eastmoney_industry_reports_by_company,
    get_fresh_eastmoney_session,
    EASTMONEY_INDUSTRY_LIST,
    gemini_llm_func
)
from crawler_agent.data_source.cninfo_data_source import (
    fetch_cninfo_financial_reports
)
from crawler_agent.data_source.szse_data_source import (
    fetch_szse_announcements
)
from crawler_agent.data_source.thsl_data_source import (
    fetch_thsl_financial_reports
)
from crawler_agent.crawl4ai_agent_improved import ImprovedCrawl4AIAgent
from common.llm_base_agent import LLMBaseAgent
import asyncio
# 导入官网采集复用函数
from crawler_agent.data_source.website_data_source import (
    search_company_website,
    find_investor_page,
    extract_report_links,
    download_file
)

def get_company_code_by_llm(company_name: str) -> str:
    """
    使用LLM根据公司名称获取股票代码
    """
    prompt = f"""
    请根据公司名称"{company_name}"返回其股票代码。
    只返回股票代码，不要其他内容。
    例如：
    贵州茅台 -> 600519
    平安银行 -> 000001
    腾讯控股 -> 00700
    阿里巴巴 -> 09988
    """
    print(f"[LLM PROMPT] {prompt}")
    
    try:
        # 使用真实的LLM接口
        agent = LLMBaseAgent()
        result = agent.llm_generate(prompt)
        if result:
            return result.strip()
    except Exception as e:
        print(f"[警告] LLM调用失败: {e}")

class CompanyDataCollector:
    """公司数据采集器"""
    
    def __init__(self, output_dir: str = "data/raw"):
        self.output_dir = output_dir
        self.setup_output_dirs()
        
    def setup_output_dirs(self):
        """设置输出目录结构"""
        dirs = [
            "announcements",
            "financial_reports", 
            "industry_reports",
            "announcements/eastmoney_announcements",
            "announcements/szse_announcements",
            "announcements/cninfo_announcements",
            "financial_reports/eastmoney_financial_reports",
            "financial_reports/szse_financial_reports", 
            "financial_reports/cninfo_financial_reports",
            "financial_reports/thsl_financial_reports",
            "industry_reports/eastmoney"
        ]
        for dir_path in dirs:
            full_path = os.path.join(self.output_dir, dir_path)
            os.makedirs(full_path, exist_ok=True)
    
    def clear_historical_data(self, company_code: str = None):
        """
        清空历史数据
        :param company_code: 如果指定公司代码，只清空该公司的数据；否则清空所有历史数据
        """
        print(f"🧹 开始清空历史数据...")
        
        # 需要清空的目录
        raw_dirs = [
            "announcements/eastmoney_announcements",
            "announcements/szse_announcements", 
            "announcements/cninfo_announcements",
            "financial_reports/eastmoney_financial_reports",
            "financial_reports/szse_financial_reports",
            "financial_reports/cninfo_financial_reports", 
            "financial_reports/thsl_financial_reports",
            "industry_reports/eastmoney"
        ]
        # 修正拼接方式，直接基于 self.output_dir 拼接
        dirs_to_clear = [os.path.join(self.output_dir, d) for d in raw_dirs]
        
        total_cleared = 0
        for full_path in dirs_to_clear:
            if os.path.exists(full_path):
                if company_code:
                    # 只清空指定公司的数据
                    for filename in os.listdir(full_path):
                        if filename.startswith(company_code):
                            file_path = os.path.join(full_path, filename)
                            try:
                                os.remove(file_path)
                                total_cleared += 1
                                print(f"   - 删除: {file_path}")
                            except Exception as e:
                                print(f"   - 删除失败: {file_path}, 错误: {e}")
                else:
                    # 清空整个目录
                    try:
                        shutil.rmtree(full_path)
                        os.makedirs(full_path, exist_ok=True)
                        print(f"   - 清空目录: {full_path}")
                    except Exception as e:
                        print(f"   - 清空目录失败: {full_path}, 错误: {e}")
        
        # 清空汇总文件
        if company_code:
            # 删除指定公司的汇总文件
            for filename in os.listdir(self.output_dir):
                if filename.startswith(company_code) and filename.endswith('.json'):
                    file_path = os.path.join(self.output_dir, filename)
                    try:
                        os.remove(file_path)
                        total_cleared += 1
                        print(f"   - 删除汇总文件: {file_path}")
                    except Exception as e:
                        print(f"   - 删除汇总文件失败: {file_path}, 错误: {e}")
        else:
            # 删除所有汇总文件
            for filename in os.listdir(self.output_dir):
                if filename.endswith('_公司数据汇总_') and filename.endswith('.json'):
                    file_path = os.path.join(self.output_dir, filename)
                    try:
                        os.remove(file_path)
                        total_cleared += 1
                        print(f"   - 删除汇总文件: {file_path}")
                    except Exception as e:
                        print(f"   - 删除汇总文件失败: {file_path}, 错误: {e}")
        
        print(f"✅ 历史数据清空完成，共删除 {total_cleared} 个文件")
    
    def collect_company_data(self, company_name: str):
        """
        采集指定公司的所有数据
        :param company_name: 公司名称
        :return: 采集结果字典
        """
        print(f"\n{'='*60}")
        print(f"开始采集公司数据: {company_name}")
        print(f"{'='*60}")
        
        # 使用LLM获取股票代码
        print("正在获取股票代码...")
        company_code = get_company_code_by_llm(company_name)
        print(f"获取到股票代码: {company_code}")
        
        # 清空所有历史数据
        self.clear_historical_data()
        
        # 获取东方财富session
        print("正在获取东方财富session...")
        cookies, headers = get_fresh_eastmoney_session()
        
        results = {
            "company_name": company_name,
            "company_code": company_code,
            "collect_time": datetime.now().isoformat(),
            "data": {}
        }
        
        # 1. 采集公司公告
        print(f"\n📢 开始采集公司公告...")
        announcement_results = self.collect_announcements(company_name, company_code, cookies, headers)
        results["data"]["announcements"] = announcement_results
        
        # 2. 采集财务报表
        print(f"\n📊 开始采集财务报表...")
        financial_results = self.collect_financial_reports(company_name, company_code, cookies, headers)
        results["data"]["financial_reports"] = financial_results
        
        # 3. 采集行业研报
        print(f"\n📈 开始采集行业研报...")
        industry_results = self.collect_industry_reports(company_name, cookies, headers)
        results["data"]["industry_reports"] = industry_results

        # 【公司官网采集示例 - 启用LLM辅助关键词生成】
        print(f"\n🌐 尝试采集公司官网财报/公告...")
        website_url = search_company_website(company_name, llm_func=gemini_llm_func)
        if website_url:
            investor_page = find_investor_page(website_url)
            if investor_page:
                links = extract_report_links(investor_page)
                for link in links:
                    download_file(link, save_dir="data/raw/announcements/website_announcements")
        
        # 保存汇总结果
        print(f"\n✅ 公司 {company_name} 数据采集完成！")
        return results
    
    def collect_announcements(self, company_name: str, company_code: str, cookies: dict, headers: dict) -> dict:
        """采集公司公告"""
        results = {"sources": {}}
        
        try:
            # 东方财富公告
            print("  - 采集东方财富公告...")
            eastmoney_data = fetch_eastmoney_announcements(
                company_code=company_code,
                page_size=30,
                page_index=1,
                save=True,
                save_dir=f"{self.output_dir}/announcements/eastmoney_announcements",
                cookies=cookies,
                headers=headers
            )
            results["sources"]["eastmoney"] = {
                "status": "success",
                "count": len(eastmoney_data.get('data', [])),
                "data": eastmoney_data
            }
        except Exception as e:
            print(f"  - 东方财富公告采集失败: {e}")
            results["sources"]["eastmoney"] = {"status": "failed", "error": str(e)}
        
        try:
            # 深交所公告
            print("  - 采集深交所公告...")
            szse_data = fetch_szse_announcements(
                company_code=company_code,
                page_size=30,
                save=True,
                save_dir=f"{self.output_dir}/announcements/szse_announcements"
            )
            results["sources"]["szse"] = {
                "status": "success", 
                "count": len(szse_data.get('data', [])),
                "data": szse_data
            }
        except Exception as e:
            print(f"  - 深交所公告采集失败: {e}")
            results["sources"]["szse"] = {"status": "failed", "error": str(e)}
        
        return results
    
    def collect_financial_reports(self, company_name: str, company_code: str, cookies: dict, headers: dict) -> dict:
        """采集财务报表"""
        results = {"sources": {}}
        
        try:
            # 东方财富财报
            print("  - 采集东方财富财报...")
            eastmoney_data = fetch_eastmoney_annual_reports(company_code)
            if (
                isinstance(eastmoney_data, dict)
                and isinstance(eastmoney_data.get('result'), dict)
                and isinstance(eastmoney_data['result'].get('data'), list)
                and eastmoney_data['result']['data']
            ):
                results["sources"]["eastmoney"] = {
                    "status": "success",
                    "count": len(eastmoney_data['result']['data']),
                    "data": eastmoney_data
                }
                print(f"  - 东方财富财报采集成功: {len(eastmoney_data['result']['data'])}条记录")
            else:
                results["sources"]["eastmoney"] = {
                    "status": "no_data",
                    "message": "未获取到有效数据",
                    "data": eastmoney_data
                }
                print("  - 东方财富财报未获取到有效数据")
        except Exception as e:
            print(f"  - 东方财富财报采集失败: {e}")
            results["sources"]["eastmoney"] = {"status": "failed", "error": str(e)}
        
        try:
            # 深交所财报
            print("  - 采集深交所财报...")
            szse_data = fetch_szse_announcements(
                company_code=company_code,
                download_pdfs=True,
                max_pdfs=5,
                datatype='财报'
            )
            if isinstance(szse_data, dict) and szse_data.get('data'):
                results["sources"]["szse"] = {
                    "status": "success",
                    "count": len(szse_data.get('data', [])),
                    "data": szse_data
                }
                print(f"  - 深交所财报采集成功: {len(szse_data.get('data', []))}条记录")
            else:
                results["sources"]["szse"] = {
                    "status": "no_data",
                    "message": "未获取到有效数据",
                    "data": szse_data
                }
                print("  - 深交所财报未获取到有效数据")
        except Exception as e:
            print(f"  - 深交所财报采集失败: {e}")
            results["sources"]["szse"] = {"status": "failed", "error": str(e)}
        
        try:
            # 巨潮资讯网财报 - 使用改进的Crawl4AI代理
            print("  - 采集巨潮资讯网财报...")
            cninfo_data = self._collect_cninfo_financial_reports(company_name, company_code)
            if cninfo_data and len(cninfo_data) > 0:
                results["sources"]["cninfo"] = {
                    "status": "success",
                    "count": len(cninfo_data),
                    "data": cninfo_data
                }
                print(f"  - 巨潮资讯网财报采集成功: {len(cninfo_data)}份报告")
            else:
                results["sources"]["cninfo"] = {
                    "status": "no_data",
                    "message": "未获取到有效数据",
                    "data": cninfo_data
                }
                print("  - 巨潮资讯网财报未获取到有效数据")
        except Exception as e:
            print(f"  - 巨潮资讯网财报采集失败: {e}")
            results["sources"]["cninfo"] = {"status": "failed", "error": str(e)}
        
        try:
            # 同花顺财报
            print("  - 采集同花顺财报...")
            thsl_data = fetch_thsl_financial_reports(company_code)
            if isinstance(thsl_data, dict) and thsl_data:
                results["sources"]["thsl"] = {
                    "status": "success",
                    "count": len(thsl_data.get('data', [])) if isinstance(thsl_data, dict) else 0,
                    "data": thsl_data
                }
                print(f"  - 同花顺财报采集成功: {len(thsl_data.get('data', [])) if isinstance(thsl_data, dict) else 0}条记录")
            else:
                results["sources"]["thsl"] = {
                    "status": "no_data",
                    "message": "未获取到有效数据",
                    "data": thsl_data
                }
                print("  - 同花顺财报未获取到有效数据")
        except Exception as e:
            print(f"  - 同花顺财报采集失败: {e}")
            results["sources"]["thsl"] = {"status": "failed", "error": str(e)}
        
        return results
    
    def _collect_cninfo_financial_reports(self, company_name: str, company_code: str) -> List[Dict]:
        """
        使用改进的Crawl4AI代理采集巨潮资讯网财报
        :param company_name: 公司名称
        :param company_code: 公司代码
        :return: 财报数据列表
        """
        try:
            # 创建异步事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def _async_collect():
                async with ImprovedCrawl4AIAgent() as agent:
                    # 使用巨潮资讯网专用方法
                    results = await agent.crawl_cninfo_financial_reports(
                        company_name=company_name,
                        company_code=company_code,
                        max_reports=5
                    )
                    return results
            
            # 运行异步任务
            results = loop.run_until_complete(_async_collect())
            print(f"[DEBUG] 巨潮返回: {results}")
            loop.close()

            # 保存每份报告到 output/financial_reports/cninfo_financial_reports/
            import os, json, datetime
            save_dir = os.path.join('data/raw', 'financial_reports', 'cninfo_financial_reports')
            os.makedirs(save_dir, exist_ok=True)
            now_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            for report in results:
                report_type = report.get('report_type', 'unknown')
                fname = f"{company_name}_{company_code}_财务报表_{report_type}_{now_str}.json"
                fpath = os.path.join(save_dir, fname)
                with open(fpath, 'w', encoding='utf-8') as f:
                    json.dump(report, f, ensure_ascii=False, indent=2)
                print(f"[巨潮] 已保存: {fpath}")

            return results
            
        except Exception as e:
            print(f"    - 巨潮资讯网财报采集异常: {e}")
            return []
    
    def collect_industry_reports(self, company_name: str, cookies: dict, headers: dict) -> dict:
        """采集行业研报"""
        results = {"sources": {}}
        
        try:
            # 东方财富行业研报
            print("  - 采集东方财富行业研报...")
            eastmoney_data = fetch_eastmoney_industry_reports_by_company(
                company_name=company_name,
                llm_func=gemini_llm_func,
                page_num=1,
                page_size=30,
                save=True,
                save_dir=f"{self.output_dir}/industry_reports/eastmoney",
                cookies=cookies,
                headers=headers,
                max_pdfs=20
            )
            results["sources"]["eastmoney"] = {
                "status": "success",
                "count": len(eastmoney_data.get('data', [])),
                "data": eastmoney_data
            }
        except Exception as e:
            print(f"  - 东方财富行业研报采集失败: {e}")
            results["sources"]["eastmoney"] = {"status": "failed", "error": str(e)}
        
        return results
    
    def save_summary_results(self, company_name: str, results: dict):
        """保存汇总结果"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{company_name}_公司数据汇总_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n📁 汇总结果已保存到: {filepath}")
        
        # 打印统计信息
        self.print_statistics(results)
    
    def print_statistics(self, results: dict):
        """打印采集统计信息"""
        print(f"\n📊 采集统计:")
        print(f"   公司名称: {results['company_name']}")
        print(f"   采集时间: {results['collect_time']}")
        
        data = results.get('data', {})
        
        # 公告统计
        if 'announcements' in data:
            announcement_stats = data['announcements']['sources']
            total_announcements = sum(
                source.get('count', 0) 
                for source in announcement_stats.values() 
                if source.get('status') == 'success'
            )
            print(f"   公告总数: {total_announcements}")
        
        # 财报统计
        if 'financial_reports' in data:
            financial_stats = data['financial_reports']['sources']
            total_financial = sum(
                source.get('count', 0)
                for source in financial_stats.values()
                if source.get('status') == 'success'
            )
            print(f"   财报总数: {total_financial}")
        
        # 研报统计
        if 'industry_reports' in data:
            industry_stats = data['industry_reports']['sources']
            total_industry = sum(
                source.get('count', 0)
                for source in industry_stats.values()
                if source.get('status') == 'success'
            )
            print(f"   研报总数: {total_industry}")

def collect_single_company_data(company_name: str, output_dir: str = "data/raw"):
    """
    采集单个公司的所有数据
    :param company_name: 公司名称
    :param output_dir: 输出目录
    :return: 采集结果
    """
    collector = CompanyDataCollector(output_dir)
    return collector.collect_company_data(company_name)

def collect_multiple_companies_data(companies: List[str], output_dir: str = "data/raw"):
    """
    批量采集多个公司的数据
    :param companies: 公司名称列表
    :param output_dir: 输出目录
    :return: 所有公司的采集结果
    """
    collector = CompanyDataCollector(output_dir)
    all_results = []
    
    for company_name in companies:
        try:
            result = collector.collect_company_data(company_name)
            all_results.append(result)
        except Exception as e:
            print(f"❌ 采集公司 {company_name} 数据时出错: {e}")
            continue
    
    return all_results

def clear_all_historical_data(output_dir: str = "output"):
    """
    清空所有历史数据
    :param output_dir: 输出目录
    """
    collector = CompanyDataCollector(output_dir)
    collector.clear_historical_data()

def clear_company_historical_data(company_code: str, output_dir: str = "output"):
    """
    清空指定公司的历史数据
    :param company_code: 公司代码
    :param output_dir: 输出目录
    """
    collector = CompanyDataCollector(output_dir)
    collector.clear_historical_data(company_code) 