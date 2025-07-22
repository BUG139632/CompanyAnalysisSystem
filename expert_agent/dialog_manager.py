import json
import os
from datetime import datetime
import sys
from tool.json_exporter import export_expert_json

class DialogManager:
    def __init__(self, expert_agent, analysis_result, company_name, dimension):
        self.expert_agent = expert_agent
        self.analysis_result = analysis_result
        self.company_name = company_name
        self.dimension = dimension
        self.dialog_history = []

    def run(self, save_path=None):
        print("欢迎进入智能分析多轮对话系统。输入 exit 可随时退出。")
        while True:
            user_question = input("请输入你对本维度的进一步问题（输入exit退出）：")
            if user_question.lower() == "exit":
                print("对话结束。")
                break
            self.dialog_history.append({
                "role": "user",
                "content": user_question,
                "timestamp": datetime.now().isoformat(),
                "company_name": self.company_name,
                "dimension": self.dimension
            })
            # 传递对话历史作为上下文
            result = self.expert_agent.generate_strategies(user_question, self.analysis_result, self.dialog_history)
            self.dialog_history.append({
                "role": "agent",
                "content": result,
                "timestamp": datetime.now().isoformat(),
                "company_name": self.company_name,
                "dimension": self.dimension
            })
            # 新增：每次有有效策略建议后立即保存并导出
            if isinstance(result, dict) and result.get("success") and result.get("strategies"):
                if save_path is None:
                    base_dir = os.path.join(os.path.dirname(__file__), '../data/strategy')
                    os.makedirs(base_dir, exist_ok=True)
                    safe_company = str(self.company_name).replace('/', '_').replace(' ', '_')
                    safe_dimension = str(self.dimension).replace('/', '_').replace(' ', '_')
                    filename = f"dialog_history_{safe_company}_{safe_dimension}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    save_path = os.path.join(base_dir, filename)
                with open(save_path, "w", encoding="utf-8") as f:
                    json.dump(self.dialog_history, f, ensure_ascii=False, indent=2)
                export_expert_json(save_path)
            if isinstance(result, dict) and result.get("success"):
                if result.get("strategies"):
                    print("建议：", result["strategies"])
                    print("理由：", result["reasons"])
                    print("风险：", result["risks"])
                    # 新增：询问用户是否需要进一步分析
                    user_input = input("是否需要对这些策略进行进一步的风险与收益分析？(y/n)：")
                    if user_input.lower().startswith("y"):
                        # 调用 business agent
                        try:
                            from business_agent.business_agent import BusinessAgent
                            from common.llm_base_agent import LLMBaseAgent
                            from langchain.vectorstores import FAISS
                            from langchain.embeddings import HuggingFaceEmbeddings
                            llm_agent = LLMBaseAgent(config_path="../config/langchain_config.yaml")
                            embedding_model = HuggingFaceEmbeddings(model_name="BAAI/bge-base-zh-v1.5")
                            vectorstore = FAISS.load_local("faiss_industry_reports", embedding_model, allow_dangerous_deserialization=True)
                            business_agent = BusinessAgent(llm_agent, vectorstore)
                            analysis_results = business_agent.analyze_from_dialog_history(
                                save_path, self.company_name, self.dimension
                            )
                            for item in analysis_results:
                                if isinstance(item, dict):
                                    strategy = item.get('strategy', '')
                                    analysis = item.get('analysis', '')
                                    print(f"策略：{strategy}\n分析报告：{analysis}\n")
                        except Exception as e:
                            print(f"[BusinessAgent分析异常] {e}")
                    print("对话结束。")
                    break
                else:  # 描述性问题，继续对话
                    print("现状描述：", result.get("explanation", "无法提供现状描述"))
            else:
                print("信息不足，请补充：", result.get("explanation", "无进一步信息"))
        # 保存对话历史（如未提前保存）
        if save_path is None or not os.path.exists(save_path):
            base_dir = os.path.join(os.path.dirname(__file__), '../data/strategy')
            os.makedirs(base_dir, exist_ok=True)
            safe_company = str(self.company_name).replace('/', '_').replace(' ', '_')
            safe_dimension = str(self.dimension).replace('/', '_').replace(' ', '_')
            filename = f"dialog_history_{safe_company}_{safe_dimension}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            save_path = os.path.join(base_dir, filename)
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(self.dialog_history, f, ensure_ascii=False, indent=2)
            # 新增：导出为txt/pdf
            export_expert_json(save_path)
        print(f"对话历史已保存到: {save_path}") 