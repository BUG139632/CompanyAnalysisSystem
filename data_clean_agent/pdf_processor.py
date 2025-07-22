import os
import json
import re
from typing import Dict, List, Optional, Tuple
import PyPDF2
import pdfplumber
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFProcessor:
    """PDF文件处理工具，用于读取和清洗PDF内容"""
    
    def __init__(self):
        self.supported_extensions = ['.pdf']
    
    def extract_text_from_pdf(self, pdf_path: str, method: str = 'pdfplumber') -> str:
        """
        从PDF文件中提取文本内容
        Args:
            pdf_path: PDF文件路径
            method: 提取方法 ('pdfplumber' 或 'pypdf2')
        Returns:
            提取的文本内容
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
        
        if method == 'pdfplumber':
            return self._extract_with_pdfplumber(pdf_path)
        elif method == 'pypdf2':
            return self._extract_with_pypdf2(pdf_path)
        else:
            raise ValueError(f"不支持的提取方法: {method}")
    
    def _extract_with_pdfplumber(self, pdf_path: str) -> str:
        """使用pdfplumber提取文本"""
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            return text
        except Exception as e:
            logger.error(f"pdfplumber提取失败 {pdf_path}: {e}")
            return ""
    
    def _extract_with_pypdf2(self, pdf_path: str) -> str:
        """使用PyPDF2提取文本"""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""
                return text
        except Exception as e:
            logger.error(f"PyPDF2提取失败 {pdf_path}: {e}")
            return ""
    
    def clean_text(self, text: str) -> str:
        """
        清洗提取的文本内容
        Args:
            text: 原始文本
        Returns:
            清洗后的文本
        """
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s\.,;:!?()\[\]{}\-+=*/@#$%&*]', '', text)
        text = re.sub(r'第\s*\d+\s*页', '', text)
        text = re.sub(r'Page\s*\d+', '', text)
        text = re.sub(r'\n\s*\n', '\n', text)
        text = text.strip()
        return text
    
    def extract_metadata(self, pdf_path: str) -> Dict:
        """
        提取PDF文件的元数据
        Args:
            pdf_path: PDF文件路径
        Returns:
            元数据字典
        """
        metadata = {
            'filename': os.path.basename(pdf_path),
            'filepath': pdf_path,
            'filesize': os.path.getsize(pdf_path),
            'pages': 0,
            'title': '',
            'author': '',
            'subject': '',
            'creator': '',
            'producer': '',
            'creation_date': '',
            'modification_date': ''
        }
        try:
            with pdfplumber.open(pdf_path) as pdf:
                metadata['pages'] = len(pdf.pages)
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                doc_info = reader.metadata
                if doc_info:
                    metadata.update({
                        'title': str(doc_info.title) if doc_info.title else '',
                        'author': str(doc_info.author) if doc_info.author else '',
                        'subject': str(doc_info.subject) if doc_info.subject else '',
                        'creator': str(doc_info.creator) if doc_info.creator else '',
                        'producer': str(doc_info.producer) if doc_info.producer else '',
                        'creation_date': str(doc_info.creation_date) if doc_info.creation_date else '',
                        'modification_date': str(doc_info.modification_date) if doc_info.modification_date else ''
                    })
        except Exception as e:
            logger.error(f"提取元数据失败 {pdf_path}: {e}")
        return metadata
    
    def process_pdf_file(self, pdf_path: str, output_dir: str = None) -> Dict:
        """
        处理单个PDF文件，提取文本和元数据
        Args:
            pdf_path: PDF文件路径
            output_dir: 输出目录（可选）
        Returns:
            处理结果字典
        """
        result = {
            'file_path': pdf_path,
            'success': False,
            'metadata': {},
            'text_content': '',
            'cleaned_text': '',
            'error': ''
        }
        try:
            result['metadata'] = self.extract_metadata(pdf_path)
            text_content = self.extract_text_from_pdf(pdf_path)
            result['text_content'] = text_content
            cleaned_text = self.clean_text(text_content)
            result['cleaned_text'] = cleaned_text
            result['success'] = True
            if output_dir and cleaned_text:
                self._save_processed_result(result, output_dir)
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"处理PDF文件失败 {pdf_path}: {e}")
        return result
    
    def _save_processed_result(self, result: Dict, output_dir: str):
        os.makedirs(output_dir, exist_ok=True)
        filename = os.path.splitext(result['metadata']['filename'])[0]
        output_path = os.path.join(output_dir, f"{filename}_processed.json")
        save_data = {
            'metadata': result['metadata'],
            'cleaned_text': result['cleaned_text'],
            'processing_info': {
                'success': result['success'],
                'error': result['error']
            }
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        logger.info(f"处理结果已保存: {output_path}")
    
    def batch_process_pdfs(self, input_dir: str, output_dir: str, file_pattern: str = "*.pdf") -> List[Dict]:
        results = []
        pdf_files = list(Path(input_dir).glob(file_pattern))
        logger.info(f"找到 {len(pdf_files)} 个PDF文件")
        for pdf_file in pdf_files:
            logger.info(f"处理文件: {pdf_file.name}")
            result = self.process_pdf_file(str(pdf_file), output_dir)
            results.append(result)
            if result['success']:
                logger.info(f"✓ 成功处理: {pdf_file.name}")
            else:
                logger.error(f"✗ 处理失败: {pdf_file.name} - {result['error']}")
        return results
    
    def extract_announcement_info(self, text: str) -> Dict:
        info = {
            'company_name': '',
            'announcement_date': '',
            'announcement_type': '',
            'title': '',
            'content_summary': ''
        }
        company_patterns = [
            r'([^\n]*?)(?:股份有限公司|有限公司|集团|控股)',
            r'证券代码[：:]\s*(\d+)',
            r'股票代码[：:]\s*(\d+)'
        ]
        for pattern in company_patterns:
            match = re.search(pattern, text[:1000])
            if match:
                info['company_name'] = match.group(1) if match.group(1) else match.group(0)
                break
        date_patterns = [
            r'(\d{4}年\d{1,2}月\d{1,2}日)',
            r'(\d{4}-\d{1,2}-\d{1,2})',
            r'(\d{4}/\d{1,2}/\d{1,2})'
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                info['announcement_date'] = match.group(1)
                break
        type_patterns = [
            r'(年报|半年报|季报|临时公告|重大事项|董事会决议|股东大会|分红派息|股权变动)',
            r'(Annual Report|Interim Report|Quarterly Report|Announcement)'
        ]
        for pattern in type_patterns:
            match = re.search(pattern, text)
            if match:
                info['announcement_type'] = match.group(1)
                break
        lines = text.split('\n')
        for line in lines[:10]:
            if '公告' in line or 'Announcement' in line:
                info['title'] = line.strip()
                break
        info['content_summary'] = text[:200].replace('\n', ' ').strip()
        return info
    
    def extract_report_info(self, text: str) -> Dict:
        info = {
            'report_title': '',
            'author': '',
            'institution': '',
            'report_date': '',
            'target_company': '',
            'rating': '',
            'target_price': '',
            'content_summary': ''
        }
        lines = text.split('\n')
        for line in lines[:5]:
            if line.strip() and len(line.strip()) > 10:
                info['report_title'] = line.strip()
                break
        author_patterns = [
            r'分析师[：:]\s*([^\n]+)',
            r'作者[：:]\s*([^\n]+)',
            r'研究员[：:]\s*([^\n]+)'
        ]
        for pattern in author_patterns:
            match = re.search(pattern, text)
            if match:
                info['author'] = match.group(1).strip()
                break
        institution_patterns = [
            r'([^\n]*?证券[^\n]*)',
            r'([^\n]*?投资[^\n]*)',
            r'([^\n]*?研究[^\n]*)'
        ]
        for pattern in institution_patterns:
            match = re.search(pattern, text)
            if match:
                info['institution'] = match.group(1).strip()
                break
        date_patterns = [
            r'(\d{4}年\d{1,2}月\d{1,2}日)',
            r'(\d{4}-\d{1,2}-\d{1,2})',
            r'(\d{4}/\d{1,2}/\d{1,2})'
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                info['report_date'] = match.group(1)
                break
        company_patterns = [
            r'([^\n]*?)(?:股份有限公司|有限公司|集团|控股)',
            r'股票代码[：:]\s*(\d+)',
            r'代码[：:]\s*(\d+)'
        ]
        for pattern in company_patterns:
            match = re.search(pattern, text)
            if match:
                info['target_company'] = match.group(1) if match.group(1) else match.group(0)
                break
        rating_patterns = [
            r'(买入|增持|持有|减持|卖出|强烈推荐|推荐|中性|谨慎推荐)',
            r'(Buy|Hold|Sell|Overweight|Underweight|Neutral)'
        ]
        for pattern in rating_patterns:
            match = re.search(pattern, text)
            if match:
                info['rating'] = match.group(1)
                break
        price_patterns = [
            r'目标价[：:]\s*([0-9\.]+)',
            r'目标价格[：:]\s*([0-9\.]+)',
            r'([0-9\.]+)\s*元'
        ]
        for pattern in price_patterns:
            match = re.search(pattern, text)
            if match:
                info['target_price'] = match.group(1)
                break
        info['content_summary'] = text[:300].replace('\n', ' ').strip()
        return info

def main():
    """测试PDF处理工具"""
    processor = PDFProcessor()
    test_pdf = "output/announcements/eastmoney_announcements/pdfs/H2_AN202504291664502884_1.pdf"
    if os.path.exists(test_pdf):
        result = processor.process_pdf_file(test_pdf, "data/cleaned/announcements")
        if result['success']:
            announcement_info = processor.extract_announcement_info(result['cleaned_text'])
            print("提取的公告信息:")
            for key, value in announcement_info.items():
                print(f"  {key}: {value}")
        else:
            print(f"✗ PDF处理失败: {result['error']}")
    else:
        print(f"测试文件不存在: {test_pdf}")

if __name__ == "__main__":
    main() 