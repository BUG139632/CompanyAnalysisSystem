import os
import json
from pdf_processor import PDFProcessor
from langchain_google_genai import GoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import glob

# 结构化抽取的Prompt模板
STRUCTURED_PROMPT = """
你是一名金融信息抽取专家，请从以下公司公告或研报原文中，提取结构化关键信息，输出标准JSON：

原文：
{content}

请提取以下字段：
- company_name: 公司名称
- announcement_date: 公告或报告发布日期（如有）
- announcement_type: 公告类型（如年报、季报、临时公告、研报等）
- title: 公告或研报标题
- content_summary: 内容摘要（200字以内）
- analysis_tags: 适用的分析维度标签列表（可多选，必须从下列6个中选择，按内容相关性选择2-4个）：
  * management_model: 管理模式
  * assessment_model: 考核模式
  * business_model: 商业模式
  * sales_model: 销售模式
  * rd_production_model: 研发生产模式
  * innovation_capability: 创新能力

要求：
- 只输出JSON，不要输出多余内容
- 没有的信息请填null
- 保持字段名为英文
- analysis_tags字段必须输出，即使没有合适标签也输出[]
"""

class LangchainPDFStructuredExtractor:
    def __init__(self, llm_model="gemini-2.0-flash-lite", google_api_key=None):
        self.pdf_processor = PDFProcessor()
        self.llm = GoogleGenerativeAI(
            model=llm_model,
            google_api_key=google_api_key or os.environ.get("GEMINI_API_KEY"),
            temperature=0.1,
            max_tokens=2000
        )
        self.prompt = PromptTemplate(
            input_variables=["content"],
            template=STRUCTURED_PROMPT
        )
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)

    def extract_structured_info(self, pdf_path: str) -> dict:
        # 1. 读取并清洗PDF文本
        result = self.pdf_processor.process_pdf_file(pdf_path)
        if not result["success"] or not result["cleaned_text"]:
            raise RuntimeError(f"PDF读取失败: {result['error']}")
        text = result["cleaned_text"]
        # 2. LLM结构化抽取
        response = self.chain.run({"content": text})
        # 3. 尝试解析为JSON
        try:
            # 只提取第一个JSON对象
            json_str = response[response.find("{") : response.rfind("}") + 1]
            info = json.loads(json_str)
        except Exception as e:
            info = {"error": f"解析LLM输出失败: {e}", "raw": response}
        return info

    def batch_extract_structured_info(self, pdf_dir: str, output_json: str = None, model: str = None, api_key: str = None) -> list:
        """
        批量处理目录下所有PDF，结构化抽取并保存为一个JSON文件。每次处理前清空历史数据。
        """
        # 确保输出目录存在
        if output_json:
            output_dir = os.path.dirname(output_json)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
        # 清空历史数据
        if output_json and os.path.exists(output_json):
            with open(output_json, 'w', encoding='utf-8') as f:
                json.dump([], f)
        # 递归查找所有PDF文件
        pdf_files = []
        for root, dirs, files in os.walk(pdf_dir):
            for file in files:
                if file.endswith('.pdf'):
                    pdf_files.append(os.path.join(root, file))
        results = []
        for pdf_path in pdf_files:
            print(f"处理: {pdf_path}")
            try:
                info = self.extract_structured_info(pdf_path)
                info['file_path'] = pdf_path
                results.append(info)
            except Exception as e:
                results.append({"file_path": pdf_path, "error": str(e)})
        if output_json:
            with open(output_json, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"已保存批量结构化结果: {output_json}")
        return results

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="LangChain PDF结构化关键信息抽取（Gemini版）")
    parser.add_argument("pdf_path", type=str, nargs="?", help="PDF文件路径（单文件模式）")
    parser.add_argument("--api_key", type=str, default=None, help="Google Gemini API Key，可选")
    parser.add_argument("--model", type=str, default="gemini-2.0-flash-lite", help="Gemini模型名，可选")
    parser.add_argument("--batch_dir", type=str, default=None, help="批量处理PDF目录（所有PDF结构化并合并输出）")
    parser.add_argument("--output_json", type=str, default=None, help="批量输出的JSON文件名")
    parser.add_argument("--data_type", type=str, choices=["announcements", "reports"], default="announcements", 
                       help="数据类型：announcements(公告) 或 reports(行业研报)")
    args = parser.parse_args()
    
    # 根据数据类型自动设置默认路径
    if args.data_type == "announcements":
        default_batch_dir = "data/raw/announcements"
        default_output_json = "data/structured/all_announcements_structured.json"
    else:  # reports
        default_batch_dir = "data/raw/industry_reports"
        default_output_json = "data/structured/all_reports_structured.json"
    
    batch_dir = args.batch_dir or default_batch_dir
    output_json = args.output_json or default_output_json
    
    extractor = LangchainPDFStructuredExtractor(llm_model=args.model, google_api_key=args.api_key)
    if batch_dir:
        print(f"处理数据类型: {args.data_type}")
        print(f"输入目录: {batch_dir}")
        print(f"输出文件: {output_json}")
        extractor.batch_extract_structured_info(batch_dir, output_json)
    elif args.pdf_path:
        info = extractor.extract_structured_info(args.pdf_path)
        print(json.dumps(info, ensure_ascii=False, indent=2))
    else:
        print("请指定pdf_path或--data_type参数") 