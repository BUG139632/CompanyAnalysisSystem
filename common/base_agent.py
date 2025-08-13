import logging
import uuid
import os
import yaml
from datetime import datetime

class BaseAgent:
    def __init__(self, config_path=None, agent_name=None):
        self.agent_name = agent_name or self.__class__.__name__
        self.config = self.load_config(config_path)
        self.logger = self.init_logger()
        self.status = "initialized"
        self.task_id = self.generate_task_id()
        self.memory = {}  # 新增：用于记忆机制
        self.logger.info(f"{self.agent_name} initialized with task_id: {self.task_id}")

    def load_config(self, config_path):
        config = {}
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        # 支持环境变量覆盖
        for k, v in os.environ.items():
            if k.startswith(self.agent_name.upper() + "_"):
                config[k[len(self.agent_name)+1:].lower()] = v
        return config

    def init_logger(self):
        logger = logging.getLogger(self.agent_name)
        # 根据环境变量控制日志级别（默认静默）
        quiet = os.environ.get("QUIET", "1") == "1" or os.environ.get("HIDE_THOUGHTS", "0") == "1"
        logger.setLevel(logging.WARNING if quiet else logging.INFO)
        formatter = logging.Formatter('[%(asctime)s][%(levelname)s][%(name)s] %(message)s')
        if not logger.handlers:
            # 控制台输出在安静模式下不添加
            if not quiet:
                ch = logging.StreamHandler()
                ch.setFormatter(formatter)
                logger.addHandler(ch)
            # 覆盖写入日志文件，每次运行清空
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            log_dir = os.path.join(project_root, 'logs')
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, 'llm.log')
            fh = logging.FileHandler(log_file, mode='w', encoding='utf-8')
            fh.setFormatter(formatter)
            logger.addHandler(fh)
        return logger

    # 状态管理
    def set_status(self, status):
        self.logger.info(f"Status changed: {self.status} -> {status}")
        self.status = status

    def get_status(self):
        return self.status

    # 记忆机制
    def save_memory(self, key, value):
        self.logger.debug(f"Save memory: {key}")
        self.memory[key] = value

    def load_memory(self, key, default=None):
        return self.memory.get(key, default)

    def clear_memory(self):
        self.logger.debug("Clear all memory.")
        self.memory.clear()

    def receive(self, data):
        self.logger.info(f"Received data: {str(data)[:200]}")
        return data

    def send(self, data):
        self.logger.info(f"Send data: {str(data)[:200]}")
        return data

    def process(self, data):
        raise NotImplementedError("Subclasses must implement process method.")

    def run(self, data=None):
        try:
            self.set_status("running")
            self.logger.info(f"{self.agent_name} started running.")
            input_data = self.receive(data)
            result = self.process(input_data)
            self.send(result)
            self.set_status("finished")
            self.logger.info(f"{self.agent_name} finished successfully.")
            return result
        except Exception as e:
            self.set_status("error")
            self.handle_error(e)
            raise

    def handle_error(self, error):
        self.logger.error(f"Error occurred: {error}")

    def generate_task_id(self):
        return f"{self.agent_name}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}" 