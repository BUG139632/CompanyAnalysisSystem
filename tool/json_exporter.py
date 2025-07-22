import os
import json
from datetime import datetime
import markdown2
from fpdf import FPDF
from weasyprint import HTML
import re

# 新增：为三类导出分别指定子目录
ANALYSIS_EXPORT_DIR = os.path.join(os.path.dirname(__file__), '../output/analysis_exports')
EXPERT_EXPORT_DIR = os.path.join(os.path.dirname(__file__), '../output/expert_exports')
BUSINESS_EXPORT_DIR = os.path.join(os.path.dirname(__file__), '../output/business_exports')
os.makedirs(ANALYSIS_EXPORT_DIR, exist_ok=True)
os.makedirs(EXPERT_EXPORT_DIR, exist_ok=True)
os.makedirs(BUSINESS_EXPORT_DIR, exist_ok=True)

# 通用txt导出
def export_to_txt(content, filename_prefix, output_dir):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    txt_path = os.path.join(output_dir, f"{filename_prefix}_{timestamp}.txt")
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"[导出] TXT文件已保存到: {os.path.abspath(txt_path)}")
    return txt_path

# 用weasyprint导出pdf（支持html/markdown）
def export_html_to_pdf(html_content, filename_prefix, output_dir):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    pdf_path = os.path.join(output_dir, f"{filename_prefix}_{timestamp}.pdf")
    HTML(string=html_content).write_pdf(pdf_path)
    print(f"[导出] PDF文件已保存到: {os.path.abspath(pdf_path)}")
    return pdf_path

# 纯文本转pdf（用fpdf）
def export_text_to_pdf(text_content, filename_prefix, output_dir):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    pdf_path = os.path.join(output_dir, f"{filename_prefix}_{timestamp}.pdf")
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in text_content.split('\n'):
        pdf.multi_cell(0, 10, line)
    pdf.output(pdf_path)
    print(f"[导出] PDF文件已保存到: {os.path.abspath(pdf_path)}")
    return pdf_path

# 简单判断内容是否为markdown
def is_markdown(content):
    return any(token in content for token in ['#', '*', '-', '`', '**'])

# 通用导出函数
def export_content(content, filename_prefix, output_dir):
    export_to_txt(content, filename_prefix, output_dir)
    if is_markdown(content):
        html = markdown2.markdown(content)
        export_html_to_pdf(html, filename_prefix, output_dir)
    else:
        export_text_to_pdf(content, filename_prefix, output_dir)

def strip_json_code_block(md_content):
    # 去除markdown中的```json ... ```代码块
    return re.sub(r'```json[\s\S]*?```', '', md_content)

def extract_analysis_from_json_code_block(md_content):
    # 提取markdown中的```json ... ```代码块，并解析其中的analysis_result字段
    import re, json
    match = re.search(r'```json[\s\S]*?({[\s\S]+?})[\s\S]*?```', md_content)
    if match:
        try:
            json_obj = json.loads(match.group(1))
            if 'analysis_result' in json_obj:
                return json_obj['analysis_result']
        except Exception:
            pass
    return None

# 针对analysis类json
def export_analysis_json(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    content = data.get('analysis_result', '')
    # 优先提取json代码块中的analysis_result字段
    extracted = extract_analysis_from_json_code_block(content)
    if extracted:
        content = extracted
    else:
        # 否则去除嵌入的json代码块
        content = strip_json_code_block(content)
    export_content(content.strip(), 'analysis_result', ANALYSIS_EXPORT_DIR)

# 针对expert类json（dialog_history）
def export_expert_json(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    agent_reply = None
    for item in reversed(data):
        if item.get('role') == 'agent':
            agent_reply = item.get('content')
            break
    if agent_reply is None:
        print('No agent reply found.')
        return
    if isinstance(agent_reply, dict) and agent_reply.get('strategies') and len(agent_reply['strategies']) > 0:
        strategies = agent_reply.get('strategies', [])
        reasons = agent_reply.get('reasons', [])
        risks = agent_reply.get('risks', [])
        md_content = ''
        for i, strategy in enumerate(strategies):
            md_content += f'### 策略{i+1}\n- {strategy}\n'
            if i < len(reasons):
                md_content += f'**理由：** {reasons[i]}\n'
            if i < len(risks):
                md_content += f'**风险：** {risks[i]}\n'
            md_content += '\n'
        if 'explanation' in agent_reply and agent_reply['explanation']:
            md_content += '### 说明\n' + agent_reply['explanation'] + '\n'
        export_content(md_content.strip(), 'expert_strategy', EXPERT_EXPORT_DIR)
    else:
        print('No valid strategies found in agent reply, skip export.')

# 针对business类json（biz_analysis）
def export_business_json(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    results = data.get('results', [])
    all_content = ''
    for idx, item in enumerate(results):
        analysis = item.get('analysis', '')
        strategy = item.get('strategy', '')
        all_content += f'## 策略{idx+1}\n- {strategy}\n\n{analysis}\n\n'
    compare = data.get('compare', '')
    if compare:
        all_content += '\n' + ('# 策略横向对比\n' if not compare.strip().startswith('#') else '') + compare.strip() + '\n'
    if all_content:
        export_content(all_content.strip(), 'business_analysis', BUSINESS_EXPORT_DIR)

# 用法示例：
# export_analysis_json('../data/analysis/assessment_analysis.json')
# export_expert_json('../data/strategy/dialog_history_未知公司_研发生产模式分析_20250718_172932.json')
# export_business_json('../data/biz_analysis/biz_analysis_未知公司_考核模式分析_20250719_105039.json') 