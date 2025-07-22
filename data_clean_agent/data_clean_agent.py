import os
import json
from common.llm_base_agent import LLMBaseAgent
import subprocess

def run_integrate_cninfo():
    """调用巨潮三表整合脚本"""
    script_path = os.path.join(os.path.dirname(__file__), 'integrate_cninfo_financials.py')
    result = subprocess.run(['python3', script_path], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError('integrate_cninfo_financials.py 执行失败')

def run_merge_multi_source_financial_reports():
    """调用多源财报合并脚本"""
    script_path = os.path.join(os.path.dirname(__file__), 'merge_multi_source_financials.py')
    result = subprocess.run(['python3', script_path], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError('merge_multi_source_financials.py 执行失败')

def run_announcements_structured_extraction():
    """调用公告结构化抽取脚本"""
    script_path = os.path.join(os.path.dirname(__file__), 'langchain_pdf_structured.py')
    result = subprocess.run([
        'python3', script_path, 
        '--data_type', 'announcements',
        '--batch_dir', 'data/raw/announcements',
        '--output_json', 'data/structured/all_announcements_structured.json'
    ], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError('公告结构化抽取执行失败')

def run_reports_structured_extraction():
    """调用研报结构化抽取脚本"""
    script_path = os.path.join(os.path.dirname(__file__), 'langchain_pdf_structured.py')
    result = subprocess.run([
        'python3', script_path, 
        '--data_type', 'reports',
        '--batch_dir', 'data/raw/industry_reports',
        '--output_json', 'data/structured/all_reports_structured.json'
    ], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError('研报结构化抽取执行失败')

# 新增：深交所、东方财富、同花顺原始财报清洗脚本

def clean_source_financials(source_name, raw_dir, cleaned_dir):
    """
    通用清洗函数：将原始采集数据从data/raw/financial_reports/xxx清洗/标准化后保存到data/cleaned/xxx
    当前为字段透传，后续可扩展为字段映射/标准化
    """
    import glob
    os.makedirs(cleaned_dir, exist_ok=True)
    # 清空历史数据
    removed = 0
    for root, _, files in os.walk(cleaned_dir):
        for file in files:
            if file.endswith('.json'):
                try:
                    os.remove(os.path.join(root, file))
                    removed += 1
                except Exception as e:
                    print(f"[{source_name}] 删除历史文件失败: {file} {e}")
    if removed:
        print(f"[{source_name}] 已清空 {removed} 个历史 .json 文件")
    files = glob.glob(os.path.join(raw_dir, '*.json'))
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as fin:
                data = json.load(fin)
            # TODO: 可在此处做字段标准化/清洗
            out_path = os.path.join(cleaned_dir, os.path.basename(f))
            with open(out_path, 'w', encoding='utf-8') as fout:
                json.dump(data, fout, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[{source_name}] 清洗失败: {f} {e}")
    print(f"[{source_name}] 清洗完成，输出到: {cleaned_dir}")

def run_clean_szse():
    import glob
    from data_clean_agent.pdf_processor import PDFProcessor
    from common.llm_base_agent import LLMBaseAgent
    raw_dir = 'data/raw/financial_reports/szse_financial_reports'
    cleaned_dir = 'data/cleaned/szse_financial_reports'
    os.makedirs(cleaned_dir, exist_ok=True)
    pdf_files = glob.glob(os.path.join(raw_dir, '*.pdf'))
    processor = PDFProcessor()
    llm_agent = LLMBaseAgent()
    for pdf_path in pdf_files:
        try:
            print(f"[深交所] 正在处理PDF: {pdf_path}")
            text = processor.extract_text_from_pdf(pdf_path)
            cleaned_text = processor.clean_text(text)
            # 构造LLM提取表格参数的prompt
            prompt = f"""
你是一名财务数据分析专家。请从以下财报PDF文本中，尽可能提取出主要财务表格的结构化参数（如：报告期、营业收入、净利润、总资产、总负债、股东权益、每股收益等），以JSON格式输出，字段名用中文。

PDF内容：
{cleaned_text[:4000]}
"""
            llm_result = llm_agent.llm_generate(prompt)
            # 尝试解析为dict
            import json
            import re
            import ast
            if isinstance(llm_result, str):
                json_match = re.search(r'\{[\s\S]*\}', llm_result)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    try:
                        data = ast.literal_eval(llm_result)
                    except Exception:
                        data = {"raw_llm_output": llm_result}
            elif isinstance(llm_result, dict):
                data = llm_result
            else:
                data = {"raw_llm_output": str(llm_result)}
            out_path = os.path.join(cleaned_dir, os.path.splitext(os.path.basename(pdf_path))[0] + '.json')
            with open(out_path, 'w', encoding='utf-8') as fout:
                json.dump(data, fout, ensure_ascii=False, indent=2)
            print(f"[深交所] 已保存结构化JSON: {out_path}")
        except Exception as e:
            print(f"[深交所] PDF清洗失败: {pdf_path} {e}")

def run_clean_eastmoney():
    clean_source_financials(
        source_name='东方财富',
        raw_dir='data/raw/financial_reports/eastmoney_financial_reports',
        cleaned_dir='data/cleaned/eastmoney_financial_reports'
    )

def run_clean_thsl():
    clean_source_financials(
        source_name='同花顺',
        raw_dir='data/raw/financial_reports/thsl_financial_reports',
        cleaned_dir='data/cleaned/thsl_financial_reports'
    )

def run_build_vector_db():
    """调用向量数据库构建脚本"""
    import subprocess
    script_path = os.path.join(os.path.dirname(__file__), 'build_vector_db.py')
    result = subprocess.run(['python3', script_path], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError('build_vector_db.py 执行失败')

class DataCleanAgent(LLMBaseAgent):
    def __init__(self, config_path=None, agent_name=None):
        super().__init__(config_path, agent_name or "DataCleanAgent")

    def run_full_clean_and_merge(self):
        """
        一键完成：
        1. 整合巨潮三表为年度财报
        2. 清洗深交所、东方财富、同花顺原始财报
        3. 合并所有数据源年度财报
        4. 结构化抽取公告信息
        5. 结构化抽取研报信息
        6. 构建向量数据库
        """
        print('【1】整合巨潮三表...')
        run_integrate_cninfo()
        print('【2】清洗深交所原始财报...')
        run_clean_szse()
        print('【3】清洗东方财富原始财报...')
        run_clean_eastmoney()
        print('【4】清洗同花顺原始财报...')
        run_clean_thsl()
        print('【5】合并多源年度财报...')
        run_merge_multi_source_financial_reports()
        print('【6】结构化抽取公告信息...')
        run_announcements_structured_extraction()
        print('【7】结构化抽取研报信息...')
        run_reports_structured_extraction()
        print('【8】构建向量数据库...')
        run_build_vector_db()
        print('【完成】多源财报清洗与合并流程已完成！')

if __name__ == "__main__":
    agent = DataCleanAgent(config_path="config/langchain_config.yaml")
    agent.run_full_clean_and_merge()
