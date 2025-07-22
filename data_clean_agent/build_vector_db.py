import os
import json
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# 路径配置
REPORTS_PATH = os.path.join(os.path.dirname(__file__), '../data/structured/all_reports_structured.json')
ANNOUNCEMENTS_PATH = os.path.join(os.path.dirname(__file__), '../data/structured/all_announcements_structured.json')
VECTOR_DB_DIR = os.path.join(os.path.dirname(__file__), '../faiss_industry_reports')

# 1. 读取结构化数据
def load_json(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

# 2. 构建文档对象
def build_documents(items, source_type):
    docs = []
    for item in items:
        content = item.get('content_summary', '')
        if not content:
            continue
        metadata = {
            "title": item.get("title"),
            "company_name": item.get("company_name"),
            "announcement_date": item.get("announcement_date"),
            "analysis_tags": item.get("analysis_tags"),
            "file_path": item.get("file_path"),
            "source_type": source_type,
        }
        docs.append(Document(page_content=content, metadata=metadata))
    return docs

# 3. 文本切分
def split_documents(docs, chunk_size=500, chunk_overlap=50):
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split_documents(docs)

# 4. 构建向量数据库
def build_vector_db(split_docs, model_name="BAAI/bge-base-zh-v1.5"):
    embeddings = HuggingFaceEmbeddings(model_name=model_name)
    vectorstore = FAISS.from_documents(split_docs, embeddings)
    return vectorstore

# 5. 主流程
def main():
    print("加载结构化研报数据...")
    reports = load_json(REPORTS_PATH)
    print(f"共加载{len(reports)}条研报数据")
    print("加载结构化公告数据...")
    announcements = load_json(ANNOUNCEMENTS_PATH)
    print(f"共加载{len(announcements)}条公告数据")

    print("构建文档对象...")
    docs_reports = build_documents(reports, source_type="report")
    docs_announcements = build_documents(announcements, source_type="announcement")
    docs = docs_reports + docs_announcements
    print(f"有效文档总数: {len(docs)}")

    print("切分文档...")
    split_docs = split_documents(docs)
    print(f"切分后文档数: {len(split_docs)}")

    print("构建向量数据库...")
    vectorstore = build_vector_db(split_docs)

    print(f"保存向量数据库到 {VECTOR_DB_DIR}")
    vectorstore.save_local(VECTOR_DB_DIR)
    print("完成！")

if __name__ == "__main__":
    main() 