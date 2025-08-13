import warnings
try:
    from langchain.utils import LangChainDeprecationWarning
    warnings.filterwarnings("ignore", category=LangChainDeprecationWarning)
except ImportError:
    # 旧版本 LangChain 无此类；退化为忽略所有 DeprecationWarning 且过滤包含关键词的warning
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", message=".*LangChainDeprecationWarning.*")

from common.llm_base_agent import LLMBaseAgent
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
import os
from expert_agent.dialog_manager import DialogManager
from keybert import KeyBERT

# 初始化KeyBERT中文模型（只初始化一次）
kw_model = KeyBERT(model='shibing624/text2vec-base-chinese')

def extract_keywords(text, top_n=5):
    keywords = kw_model.extract_keywords(text, top_n=top_n)
    return [kw[0] for kw in keywords]

class ExpertAgent:
    def __init__(self, config_path=None, vector_db_dir=None, embedding_model="BAAI/bge-base-zh-v1.5"):
        self.llm_agent = LLMBaseAgent(config_path=config_path)
        # 加载本地向量数据库
        if vector_db_dir is None:
            # 默认路径，可根据实际情况调整
            vector_db_dir = os.path.join(os.path.dirname(__file__), '../faiss_industry_reports')
        self.embeddings = HuggingFaceEmbeddings(model_name=embedding_model)
        self.vectorstore = FAISS.load_local(vector_db_dir, self.embeddings, allow_dangerous_deserialization=True)

    def search_knowledge(self, query, top_k=5):
        """用向量数据库检索相关知识片段"""
        keywords = extract_keywords(query, top_n=3)
        search_query = " ".join(keywords) if keywords else query
        results = self.vectorstore.similarity_search(search_query, k=top_k)
        return "\n".join([doc.page_content for doc in results])

    def generate_strategies(self, user_question, analysis_result, dialog_history=None):
        """
        输入：用户问题、分析结果、对话历史（可选）
        输出：
            {
                "success": True/False,
                "strategies": [...],
                "reasons": [...],
                "risks": [...],
                "explanation": "信息不足时的引导"
            }
        """
        # 1. 检索相关知识
        related_knowledge = self.search_knowledge(user_question, top_k=5)
        
        # 2. 构建对话历史上下文
        context_info = ""
        if dialog_history and len(dialog_history) > 0:
            context_info = "\n【对话历史】\n"
            for i, turn in enumerate(dialog_history[-6:], 1):  # 只保留最近6轮对话
                if turn["role"] == "user":
                    context_info += f"用户{i}: {turn['content']}\n"
                elif turn["role"] == "agent":
                    content = turn["content"]
                    if isinstance(content, dict):
                        if content.get("success"):
                            strategies = content.get("strategies", [])
                            reasons = content.get("reasons", [])
                            risks = content.get("risks", [])
                            context_info += f"专家{i}: 提供了{len(strategies)}条建议\n"
                        else:
                            context_info += f"专家{i}: {content.get('explanation', '信息不足')}\n"
                    else:
                        context_info += f"专家{i}: {content}\n"
            
            # 添加上下文理解指导
            context_info += "\n【上下文理解指导】\n"
            context_info += "请仔细理解用户的当前问题是否是对之前问题的补充或细化。如果用户的问题看起来不完整或是对之前问题的回应，请结合对话历史来理解用户的真实意图。\n"
        
        # 3. 构建 prompt
        prompt = f"""
【分析结果】
{analysis_result}

【相关知识补充】
{related_knowledge}{context_info}

【当前用户问题】
{user_question}

请仔细分析用户问题的类型和上下文：

1. **描述性问题**：如"该公司的销售模式如何？"、"公司现状怎么样？"等询问现状的问题
2. **策略性问题**：如"如何提升盈利能力？"、"应该采取什么措施？"等请求建议的问题
3. **上下文相关问题**：用户的问题可能是对之前问题的补充、细化或回应

**上下文理解规则：**
- 如果用户的问题看起来不完整（如"利润增长方面"），请结合对话历史理解用户的真实意图
- 如果用户是在回应之前的问题，请基于之前的上下文来回答
- 如果用户的问题是对之前问题的细化，请针对具体方面进行深入分析

**回答规则：**
- 如果是描述性问题：分析现状，不提供策略建议
- 如果是策略性问题：提供具体的改进建议、理由和风险
- 如果是上下文相关问题：基于对话历史理解用户意图，提供相应的分析
- 如果问题不明确：说明需要用户进一步明确

请以JSON格式输出：
{{
  "question_type": "descriptive/strategic/unclear",
  "strategies": [建议1, 建议2, ...],  // 仅在策略性问题时提供
  "reasons": [理由1, 理由2, ...],     // 仅在策略性问题时提供
  "risks": [风险1, 风险2, ...],       // 仅在策略性问题时提供
  "description": "现状描述",          // 仅在描述性问题时提供
  "info_insufficient": true/false,
  "explanation": "当info_insufficient为true时，说明用户问题不明确，需要用户进一步明确；当info_insufficient为false时，此字段应为空字符串"
}}
"""
        result = self.llm_agent.llm_generate(prompt)
        # 尝试结构化解析
        import json
        import re
        if result is None:
            return {
                "success": False,
                "explanation": "LLM未返回结果，无法解析为结构化建议。",
                "strategies": [],
                "reasons": [],
                "risks": []
            }
        
        # 尝试提取JSON内容，处理可能的markdown代码块包装
        json_content = result.strip()
        
        # 如果被markdown代码块包装，提取其中的JSON
        if json_content.startswith("```json"):
            # 移除开头的 ```json 和结尾的 ```
            json_content = re.sub(r'^```json\s*', '', json_content)
            json_content = re.sub(r'\s*```$', '', json_content)
        elif json_content.startswith("```"):
            # 移除开头的 ``` 和结尾的 ```
            json_content = re.sub(r'^```\s*', '', json_content)
            json_content = re.sub(r'\s*```$', '', json_content)
        
        try:
            data = json.loads(json_content)
            question_type = data.get("question_type", "unclear")
            
            if data.get("info_insufficient", False):
                return {
                    "success": False,
                    "explanation": data.get("explanation", "信息不足，请补充更多背景或数据。"),
                    "strategies": [],
                    "reasons": [],
                    "risks": []
                }
            elif question_type == "descriptive":
                # 描述性问题：返回现状描述，不提供策略
                return {
                    "success": True,
                    "strategies": [],
                    "reasons": [],
                    "risks": [],
                    "explanation": data.get("description", "根据分析结果，无法提供现状描述。")
                }
            elif question_type == "strategic":
                # 策略性问题：返回具体建议
                return {
                    "success": True,
                    "strategies": data.get("strategies", []),
                    "reasons": data.get("reasons", []),
                    "risks": data.get("risks", []),
                    "explanation": ""
                }
            else:
                # 问题类型不明确
                return {
                    "success": False,
                    "explanation": "无法确定问题类型，请重新表述您的问题。",
                    "strategies": [],
                    "reasons": [],
                    "risks": []
                }
        except Exception as e:
            # 若解析失败，返回原始文本
            return {
                "success": False,
                "explanation": f"LLM输出无法解析为结构化建议，解析错误: {str(e)}，原始输出：{str(result)}",
                "strategies": [],
                "reasons": [],
                "risks": []
            }

    def run_dialog(self, analysis_result, company_name="未知公司", dimension="未知维度"):
        """在 ExpertAgent 内部直接运行多轮对话流程"""
        dialog_manager = DialogManager(self, analysis_result, company_name, dimension)
        dialog_manager.run()
