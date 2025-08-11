import requests
import os
from .base_agent import BaseAgent

class LLMBaseAgent(BaseAgent):
    def __init__(self, config_path=None, agent_name=None):
        super().__init__(config_path, agent_name or "LLMBaseAgent")
        self.llm_context = []  # 用于存储对话/推理上下文
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY")
        self.gemini_api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent"
        
        # LangChain 支持配置
        self.langchain_enabled = self.config.get('langchain_enabled', False)
        self.fallback_to_original = self.config.get('fallback_to_original', True)
        self.llm = None
        self.langchain_components = {}
        
        # 如果启用了 LangChain，进行初始化
        if self.langchain_enabled:
            self.setup_langchain()

    def setup_langchain(self):
        """
        设置 LangChain 组件
        """
        try:
            from langchain_google_genai import GoogleGenerativeAI
            from langchain.memory import ConversationBufferMemory
            from langchain.chains import LLMChain
            from langchain.prompts import PromptTemplate
            
            # 初始化 LangChain LLM
            self.llm = GoogleGenerativeAI(
                model="gemini-2.0-flash",
                google_api_key=self.gemini_api_key,
                temperature=self.config.get('temperature', 0.1),
                max_tokens=self.config.get('max_tokens', 8000)
            )
            
            # 初始化记忆组件
            self.langchain_components['memory'] = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                max_token_limit=self.config.get('max_memory_tokens', 4000)
            )
            
            # 初始化基础链
            self.langchain_components['basic_chain'] = LLMChain(
                llm=self.llm,
                prompt=PromptTemplate(
                    input_variables=["prompt"],
                    template="{prompt}"
                ),
                memory=self.langchain_components['memory']
            )
            
            self.logger.info("LangChain 组件初始化成功")
            
        except ImportError as e:
            self.logger.warning(f"LangChain 未安装，回退到原有方式: {e}")
            self.langchain_enabled = False
        except Exception as e:
            self.logger.error(f"LangChain 初始化失败: {e}")
            self.langchain_enabled = False

    def llm_generate(self, prompt, **kwargs):
        """
        LLM 推理接口，优先使用 LangChain，失败时回退到原有方式
        prompt: 输入提示
        kwargs: 其他 LLM 参数
        """
        # ------ 新增：自动测试模式下返回占位响应 ------
        if os.getenv("AUTO_TEST") == "1":
            self.logger.info("[AUTO_TEST] 跳过 LLM 调用，返回占位响应")
            return {
                "analysis_result": "这是自动测试模式的占位分析结果。在实际运行中，这里会包含详细的AI分析内容。",
                "recommended_visualization_metrics": ["revenue", "net_profit", "roe"],
                "test_mode": True,
                "status": "success"
            }
        # ---------------------------------------------------
        
        # 如果启用了 LangChain，优先使用
        if self.langchain_enabled and self.llm:
            try:
                result = self.llm_generate_langchain(prompt, **kwargs)
                if result:
                    return result
            except Exception as e:
                self.logger.warning(f"LangChain 调用失败，回退到原有方式: {e}")
        
        # 回退到原有的 Gemini API 调用方式
        return self.llm_generate_original(prompt, **kwargs)

    def llm_generate_langchain(self, prompt, **kwargs):
        """
        使用 LangChain 的 LLM 调用
        """
        if not self.llm:
            raise ValueError("LangChain LLM 未初始化")
        
        self.logger.info(f"[LangChain调用] prompt: {prompt}")
        
        try:
            # 使用基础链进行调用
            result = self.langchain_components['basic_chain'].run(prompt)
            self.logger.info(f"[LangChain调用] 返回: {result}")
            return result
        except Exception as e:
            self.logger.error(f"LangChain 调用失败: {e}")
            raise

    def llm_generate_original(self, prompt, **kwargs):
        """
        原有的 Gemini API 调用方式
        """
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY 未配置，无法调用Gemini API")
        
        headers = {"Content-Type": "application/json"}
        url = f"{self.gemini_api_url}?key={self.gemini_api_key}"
        data = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        
        self.logger.info(f"[原始LLM调用] prompt: {prompt}")
        self.logger.debug(f"[原始LLM调用] 请求体: {data}")
        
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            self.logger.info(f"[原始LLM调用] Gemini返回: {result}")
            # 解析Gemini返回的文本内容
            return result["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            self.logger.error(f"Gemini API调用失败: {e}")
            return None

    def create_chain(self, prompt_template, input_variables=None, memory_key=None):
        """
        创建自定义的 LangChain 链
        prompt_template: 提示模板字符串
        input_variables: 输入变量列表
        memory_key: 记忆键名（可选）
        """
        if not self.langchain_enabled:
            self.logger.warning("LangChain 未启用，无法创建链")
            return None
        
        try:
            from langchain.chains import LLMChain
            from langchain.prompts import PromptTemplate
            
            # 如果没有指定输入变量，从模板中自动提取
            if input_variables is None:
                import re
                input_variables = re.findall(r'\{(\w+)\}', prompt_template)
            
            prompt = PromptTemplate(
                input_variables=input_variables,
                template=prompt_template
            )
            
            # 如果指定了记忆键，使用记忆组件
            memory = None
            if memory_key and 'memory' in self.langchain_components:
                memory = self.langchain_components['memory']
            
            chain = LLMChain(
                llm=self.llm,
                prompt=prompt,
                memory=memory
            )
            
            self.logger.info(f"创建 LangChain 链: {input_variables}")
            return chain
            
        except Exception as e:
            self.logger.error(f"创建 LangChain 链失败: {e}")
            return None

    def add_to_context(self, message):
        """
        添加消息到上下文
        支持 LangChain 记忆和原有上下文
        """
        # 添加到原有上下文
        self.llm_context.append(message)
        
        # 如果启用了 LangChain，也添加到记忆组件
        if self.langchain_enabled and 'memory' in self.langchain_components:
            try:
                self.langchain_components['memory'].save_context(
                    {"input": message},
                    {"output": ""}
                )
            except Exception as e:
                self.logger.warning(f"添加 LangChain 记忆失败: {e}")

    def get_context(self):
        """
        获取上下文
        优先返回 LangChain 记忆，否则返回原有上下文
        """
        if self.langchain_enabled and 'memory' in self.langchain_components:
            try:
                return self.langchain_components['memory'].load_memory_variables({})
            except Exception as e:
                self.logger.warning(f"获取 LangChain 记忆失败: {e}")
        
        return {"llm_context": self.llm_context}

    def clear_context(self):
        """
        清除上下文
        同时清除 LangChain 记忆和原有上下文
        """
        self.llm_context = []
        
        if self.langchain_enabled and 'memory' in self.langchain_components:
            try:
                self.langchain_components['memory'].clear()
                self.logger.info("清除 LangChain 记忆")
            except Exception as e:
                self.logger.warning(f"清除 LangChain 记忆失败: {e}")

    def is_langchain_enabled(self):
        """
        检查 LangChain 是否启用
        """
        return self.langchain_enabled and self.llm is not None

    def get_langchain_status(self):
        """
        获取 LangChain 状态信息
        """
        return {
            "enabled": self.langchain_enabled,
            "llm_initialized": self.llm is not None,
            "components": list(self.langchain_components.keys()),
            "fallback_enabled": self.fallback_to_original
        } 