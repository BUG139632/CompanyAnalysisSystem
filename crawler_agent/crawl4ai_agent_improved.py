#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进的Crawl4AI爬虫代理
支持异步处理、并发爬取、多种提取策略和数据结构化处理
"""

import asyncio
import json
import logging
import time
import os
import uuid
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlencode, urljoin
import yaml
from functools import wraps
from concurrent.futures import ThreadPoolExecutor
import aiohttp
from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import LLMExtractionStrategy, JsonCssExtractionStrategy, JsonXPathExtractionStrategy
from crawl4ai.models import CrawlResultContainer
import re
from datetime import datetime
from crawler_agent.company_financial_report_crawler import CompanyFinancialReportCrawler

# 设置日志
quiet_mode = os.environ.get("QUIET", "1") == "1" or os.environ.get("HIDE_THOUGHTS", "0") == "1"
logging.basicConfig(level=logging.WARNING if quiet_mode else logging.INFO)
# 静默第三方冗余日志（在 quiet 模式下尤其显著）
if quiet_mode:
	logging.getLogger("WDM").setLevel(logging.ERROR)
	logging.getLogger("webdriver_manager").setLevel(logging.ERROR)
	logging.getLogger("selenium").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

def error_handler(func):
    """错误处理装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            return None
    return wrapper

def performance_monitor(func):
    """性能监控装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        logger.info(f"{func.__name__} took {end_time - start_time:.2f} seconds")
        return result
    return wrapper

class DynamicConfigProcessor:
    """动态配置处理器 - 支持模板变量、环境变量、动态值生成"""
    
    def __init__(self):
        self.dynamic_values = {
            'timestamp': lambda: str(int(time.time())),
            'random_uuid': lambda: str(uuid.uuid4()),
            'random_user_agent': lambda: self._get_random_user_agent(),
            'current_date': lambda: time.strftime('%Y-%m-%d'),
            'current_time': lambda: time.strftime('%H:%M:%S')
        }
    
    def _get_random_user_agent(self) -> str:
        """获取随机User-Agent"""
        user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36'
        ]
        return user_agents[int(time.time()) % len(user_agents)]
    
    def process_value(self, value: str, context: Optional[Dict] = None) -> str:
        """处理单个值的动态配置"""
        if not isinstance(value, str):
            return value
        
        context = context or {}
        
        # 处理环境变量 ${ENV_VAR}
        value = self._process_env_vars(value)
        
        # 处理模板变量 {variable}
        value = self._process_template_vars(value, context)
        
        # 处理动态值 {dynamic_function}
        value = self._process_dynamic_values(value)
        
        return value
    
    def _process_env_vars(self, value: str) -> str:
        """处理环境变量 ${ENV_VAR}"""
        def replace_env_var(match):
            env_var = match.group(1)
            return os.getenv(env_var, match.group(0))
        
        return re.sub(r'\$\{([^}]+)\}', replace_env_var, value)
    
    def _process_template_vars(self, value: str, context: Dict) -> str:
        """处理模板变量 {variable}"""
        def replace_template_var(match):
            var_name = match.group(1)
            return context.get(var_name, match.group(0))
        
        return re.sub(r'\{([^}]+)\}', replace_template_var, value)
    
    def _process_dynamic_values(self, value: str) -> str:
        """处理动态值 {dynamic_function}"""
        def replace_dynamic_var(match):
            func_name = match.group(1)
            if func_name in self.dynamic_values:
                return self.dynamic_values[func_name]()
            return match.group(0)
        
        return re.sub(r'\{([^}]+)\}', replace_dynamic_var, value)
    
    def process_dict(self, data: Dict, context: Optional[Dict] = None) -> Dict:
        """处理字典中的所有值"""
        if not isinstance(data, dict):
            return data
        
        context = context or {}
        result = {}
        
        for key, value in data.items():
            if isinstance(value, dict):
                result[key] = self.process_dict(value, context)
            elif isinstance(value, list):
                result[key] = [self.process_value(str(item), context) if isinstance(item, str) else item for item in value]
            else:
                result[key] = self.process_value(str(value), context)
        
        return result

class ConfigManager:
    """配置管理器 - 支持按数据种类分类的配置"""
    
    def __init__(self, config_path: str = "crawler_agent/crawl4ai_config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"Configuration loaded from {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}
    
    def get_llm_config(self) -> Dict:
        """获取LLM配置"""
        return self.config.get('llm', {})
    
    def get_crawler_config(self) -> Dict:
        """获取爬虫配置"""
        return self.config.get('crawler', {})
    
    def get_data_sources_by_type(self, data_type: str) -> Dict:
        """根据数据类型获取数据源配置"""
        data_sources = self.config.get('data_sources', {})
        return data_sources.get(data_type, {})
    
    def get_search_keywords(self, data_type: str) -> List[str]:
        """获取指定数据类型的搜索关键词"""
        keywords = self.config.get('search_keywords', {})
        return keywords.get(data_type, [])
    
    def get_extraction_strategies(self) -> Dict:
        """获取提取策略配置"""
        return self.config.get('extraction_strategies', {})
    
    def get_data_processing_config(self, data_type: str) -> Dict:
        """获取数据处理配置"""
        processing = self.config.get('data_processing', {})
        return processing.get(data_type, {})
    
    def get_cache_config(self) -> Dict:
        """获取缓存配置"""
        return self.config.get('cache', {})
    
    def get_error_handling_config(self) -> Dict:
        """获取错误处理配置"""
        return self.config.get('error_handling', {})

class URLBuilder:
    """URL构建器 - 支持按数据种类分类的URL构建"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.dynamic_processor = DynamicConfigProcessor()
    
    def build_urls_by_data_type(self, company_name: str, company_code: str, data_type: str) -> List[Dict]:
        """根据数据类型构建URL列表"""
        data_sources = self.config_manager.get_data_sources_by_type(data_type)
        urls = []
        
        # 生成关键词（如有）
        keywords = self.config_manager.get_search_keywords(data_type)
        keyword = keywords[0] if keywords else ""
        
        # 构建上下文
        context = {
            'company_name': company_name,
            'company_code': company_code,
            'keyword': keyword
        }
        
        for source_name, source_config in data_sources.items():
            try:
                # 检查是否为LLM+Google搜索策略
                if source_config.get('search_strategy') == 'llm_google_search':
                    # LLM+Google搜索类型：需要动态发现URL
                    urls.append({
                        'source_name': source_name,
                        'data_type': data_type,
                        'priority': source_config.get('priority', 999),
                        'domain': source_config.get('domain', ''),
                        'search_strategy': 'llm_google_search',
                        'search_keywords': source_config.get('search_keywords', []),
                        'llm_prompt': source_config.get('llm_prompt', ''),
                        'is_llm_search': True,
                        'company_code': company_code,
                        'company_name': company_name
                    })
                # 检查是否为API类型数据源
                elif 'api_endpoints' in source_config:
                    # API类型：为每个endpoint创建URL
                    for endpoint_name, endpoint_path in source_config['api_endpoints'].items():
                        url = self._build_url_from_template(
                            source_config['url_template'],
                            api_name=endpoint_path,
                            company_name=company_name,
                            company_code=company_code,
                            keyword=keyword,
                            source_config=source_config
                        )
                        
                        # 处理动态配置
                        processed_config = self.dynamic_processor.process_dict(source_config, context)
                        # 修正params['scode']重复拼接问题
                        params = processed_config.get('params', {}).copy()
                        if 'scode' in params:
                            params['scode'] = company_code  # 强制只用一次company_code
                        urls.append({
                            'url': url,
                            'source_name': source_name,
                            'data_type': data_type,
                            'endpoint_type': endpoint_name,
                            'priority': processed_config.get('priority', 999),
                            'domain': processed_config.get('domain', ''),
                            'params': params,
                            'headers': processed_config.get('headers', {}),
                            'cookies': processed_config.get('cookies', {}),
                            'is_api': True,
                            'company_code': company_code,
                            'company_name': company_name
                        })
                # 新增：支持api_url/method/json/save_dir配置的API型数据源
                elif 'api_url' in source_config and 'method' in source_config:
                    processed_config = self.dynamic_processor.process_dict(source_config, context)
                    url = processed_config['api_url']
                    params = processed_config.get('params', {})
                    json_data = processed_config.get('json', None)
                    headers = processed_config.get('headers', {})
                    cookies = processed_config.get('cookies', {})
                    save_dir = processed_config.get('save_dir', None)
                    urls.append({
                        'url': url,
                        'source_name': source_name,
                        'data_type': data_type,
                        'priority': processed_config.get('priority', 999),
                        'domain': processed_config.get('domain', ''),
                        'params': params,
                        'json': json_data,
                        'headers': headers,
                        'cookies': cookies,
                        'is_api': True,
                        'api_method': processed_config['method'],
                        'save_dir': save_dir,
                        'company_code': company_code,
                        'company_name': company_name
                    })
                else:
                    # 网页类型：传统方式
                    url = self._build_url_from_template(
                        source_config['url_template'],
                        company_name=company_name,
                        company_code=company_code,
                        keyword=keyword,
                        source_config=source_config
                    )
                    
                    # 处理动态配置
                    processed_config = self.dynamic_processor.process_dict(source_config, context)
                    
                    urls.append({
                        'url': url,
                        'source_name': source_name,
                        'data_type': data_type,
                        'priority': processed_config.get('priority', 999),
                        'domain': processed_config.get('domain', ''),
                        'selectors': processed_config.get('selectors', {}),
                        'params': processed_config.get('params', {}),
                        'headers': processed_config.get('headers', {}),
                        'cookies': processed_config.get('cookies', {}),
                        'is_api': False,
                        'company_code': company_code,
                        'company_name': company_name
                    })
            except Exception as e:
                logger.error(f"Failed to build URL for {source_name}: {e}")
        
        # 按优先级排序，保证 int() 不会收到 None
        urls.sort(key=lambda x: int(x.get('priority', 999) or 999))
        return urls
    
    def _build_url_from_template(self, template: str, **kwargs) -> str:
        """从模板构建URL（只返回主路径，不拼接params）"""
        # 替换模板变量
        url = template.format(**kwargs)
        # 不再拼接params到url，params全部通过aiohttp的params参数传递
        return url
    
    def generate_search_keywords(self, company_name: str, company_code: str, data_type: str) -> List[str]:
        """生成搜索关键词"""
        keywords = self.config_manager.get_search_keywords(data_type)
        return [
            keyword.format(公司名称=company_name, 公司代码=company_code)
            for keyword in keywords
        ]

class ExtractionStrategyFactory:
    """提取策略工厂"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
    
    def create_strategy(self, strategy_type: str, **kwargs) -> Any:
        """创建提取策略"""
        strategies_config = self.config_manager.get_extraction_strategies()
        
        if strategy_type == 'llm':
            return self._create_llm_strategy(strategies_config.get('llm', {}))
        elif strategy_type == 'css':
            return self._create_css_strategy(strategies_config.get('css_selector', {}))
        elif strategy_type == 'xpath':
            return self._create_xpath_strategy(strategies_config.get('xpath', {}))
        else:
            raise ValueError(f"Unknown strategy type: {strategy_type}")
    
    def _create_llm_strategy(self, config: Dict) -> LLMExtractionStrategy:
        """创建LLM提取策略"""
        if not config.get('enabled', True):
            raise ValueError("LLM strategy is disabled")
        
        llm_config = self.config_manager.get_llm_config()
        return LLMExtractionStrategy(
            llm_provider=llm_config.get('provider', 'google/gemini-2.0-flash-exp'),
            llm_api_key=llm_config.get('api_key', ''),
            llm_model=llm_config.get('model', 'gemini-2.0-flash-exp'),
            max_tokens=config.get('max_tokens', 4000),
            temperature=config.get('temperature', 0.1),
            system_prompt=config.get('system_prompt', ''),
            timeout=llm_config.get('timeout', 30)
        )
    
    def _create_css_strategy(self, config: Dict) -> JsonCssExtractionStrategy:
        """创建CSS选择器提取策略"""
        if not config.get('enabled', True):
            raise ValueError("CSS strategy is disabled")
        
        extraction_pattern = {
            "title": config.get('selectors', {}).get('title', ['.title']),
            "content": config.get('selectors', {}).get('content', ['.content']),
            "date": config.get('selectors', {}).get('date', ['.date']),
            "author": config.get('selectors', {}).get('author', ['.author']),
            "source": config.get('selectors', {}).get('source', ['.source'])
        }
        schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "content": {"type": "string"},
                "date": {"type": "string"},
                "author": {"type": "string"},
                "source": {"type": "string"}
            }
        }
        return JsonCssExtractionStrategy(
            extraction_pattern=extraction_pattern,
            schema=schema
        )
    
    def _create_xpath_strategy(self, config: Dict) -> JsonXPathExtractionStrategy:
        """创建XPath提取策略"""
        if not config.get('enabled', True):
            raise ValueError("XPath strategy is disabled")
        
        extraction_pattern = {
            "title": config.get('selectors', {}).get('title', '//h1'),
            "content": config.get('selectors', {}).get('content', '//div[@class=\"content\"]'),
            "date": config.get('selectors', {}).get('date', '//span[@class=\"date\"]'),
            "author": config.get('selectors', {}).get('author', '//span[@class=\"author\"]'),
            "source": config.get('selectors', {}).get('source', '//span[@class=\"source\"]')
        }
        schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "content": {"type": "string"},
                "date": {"type": "string"},
                "author": {"type": "string"},
                "source": {"type": "string"}
            }
        }
        return JsonXPathExtractionStrategy(
            extraction_pattern=extraction_pattern,
            schema=schema
        )

class DataProcessor:
    """数据处理器"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
    
    def process_data(self, raw_data: Dict, data_type: str) -> Dict:
        """处理原始数据，结构化/清洗"""
        # 如果是API返回的数据，自动提取data字段
        if 'api_data' in raw_data:
            api_data = raw_data['api_data']
            financial_data = api_data.get('data', api_data)
            result = {
                'source_url': raw_data.get('source_url', ''),
                'source_name': raw_data.get('source_name', ''),
                'data_type': raw_data.get('data_type', data_type),
                'endpoint_type': raw_data.get('endpoint_type', ''),
                'crawl_timestamp': raw_data.get('crawl_timestamp', ''),
                'financial_data': financial_data,
                'status_code': raw_data.get('status_code', None),
            }
            return result
        # 其他情况，直接返回原始数据
        return raw_data

class CacheManager:
    """缓存管理器"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager.get_cache_config()
        self.cache = {}
        self.enabled = self.config.get('enabled', True)
        self.ttl = self.config.get('ttl', 3600)
        self.max_size = self.config.get('max_size', 1000)
    
    def get(self, key: str) -> Optional[Dict]:
        """获取缓存数据"""
        if not self.enabled:
            return None
        
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return data
            else:
                del self.cache[key]
        
        return None
    
    def set(self, key: str, data: Dict):
        """设置缓存数据"""
        if not self.enabled:
            return
        
        # 检查缓存大小
        if len(self.cache) >= self.max_size:
            # 删除最旧的条目
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
        
        self.cache[key] = (data, time.time())

class ConcurrencyManager:
    """并发管理器"""
    
    def __init__(self, max_concurrent: int = 5):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
    
    async def acquire(self):
        """获取并发许可"""
        await self.semaphore.acquire()
    
    def release(self):
        """释放并发许可"""
        self.semaphore.release()
    
    def run_in_executor(self, func, *args):
        """在线程池中运行函数"""
        return asyncio.get_event_loop().run_in_executor(self.executor, func, *args)

class DataSaver:
    """数据保存器"""
    
    def __init__(self, save_dir: str = "crawl_results"):
        self.save_dir = save_dir
        self.dynamic_processor = DynamicConfigProcessor()
        self._ensure_dir_exists(save_dir)
    
    def _ensure_dir_exists(self, path: str):
        """确保目录存在"""
        if not os.path.exists(path):
            os.makedirs(path)
    
    def clear_directory(self):
        """清空保存目录"""
        if os.path.exists(self.save_dir):
            for filename in os.listdir(self.save_dir):
                file_path = os.path.join(self.save_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                        logger.info(f"已删除文件: {file_path}")
                    elif os.path.isdir(file_path):
                        import shutil
                        shutil.rmtree(file_path)
                        logger.info(f"已删除目录: {file_path}")
                except Exception as e:
                    logger.error(f"删除文件失败 {file_path}: {e}")
            logger.info(f"已清空目录: {self.save_dir}")
        else:
            logger.info(f"目录不存在，无需清空: {self.save_dir}")
    
    def _generate_filename(self, data_type: str, company_name: str, company_code: str,
                           endpoint_type: str = "", timestamp: Optional[str] = None) -> str:
        # 确保 timestamp 一定为字符串
        if not timestamp or not isinstance(timestamp, str):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{company_name}_{company_code}_{data_type}"
        if endpoint_type:
            filename += f"_{endpoint_type}"
        filename += f"_{timestamp}.json"
        return filename
    
    def _process_filename_template(self, template: str, **kwargs) -> str:
        """从模板生成文件名"""
        # 替换模板变量
        filename = template.format(**kwargs)
        
        # 处理动态值
        filename = self.dynamic_processor.process_value(filename, kwargs)
        
        return filename
    
    def save_data(self, data: Union[Dict, List], data_type: str, company_name: str, company_code: str,
                   endpoint_type: str = "", timestamp: Optional[str] = None) -> str:
        """保存数据到JSON文件"""
        filename = self._generate_filename(data_type, company_name, company_code, endpoint_type, timestamp)
        # 确保多级目录存在
        self._ensure_dir_exists(self.save_dir)
        # 处理动态配置
        context = {'company_name': company_name, 'company_code': company_code}
        if isinstance(data, list):
            processed_data = [self.dynamic_processor.process_dict(item, context) for item in data]
        else:
            processed_data = self.dynamic_processor.process_dict(data, context)
        try:
            with open(os.path.join(self.save_dir, filename), 'w', encoding='utf-8') as f:
                json.dump(processed_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Data saved to {os.path.join(self.save_dir, filename)}")
            return os.path.join(self.save_dir, filename)
        except Exception as e:
            logger.error(f"Failed to save data to {os.path.join(self.save_dir, filename)}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return ""

class ImprovedCrawl4AIAgent:
    """改进的Crawl4AI爬虫代理 - 支持按数据种类分类"""
    
    def __init__(self, config_path: str = "crawler_agent/crawl4ai_config.yaml"):
        self.config_manager = ConfigManager(config_path)
        self.url_builder = URLBuilder(self.config_manager)
        self.strategy_factory = ExtractionStrategyFactory(self.config_manager)
        self.data_processor = DataProcessor(self.config_manager)
        self.cache_manager = CacheManager(self.config_manager)
        self.data_saver = DataSaver(save_dir=self.config_manager.config.get('save_dir', 'crawl_results'))
        
        crawler_config = self.config_manager.get_crawler_config()
        self.concurrency_manager = ConcurrencyManager(
            max_concurrent=crawler_config.get('concurrent_limit', 5)
        )
        
        self.dynamic_processor = DynamicConfigProcessor()
        self.crawler = None
        self._setup_logging()
    
    def _setup_logging(self):
        """设置日志"""
        log_config = self.config_manager.config.get('logging', {})
        if log_config.get('file'):
            # 确保日志目录存在
            log_dir = os.path.dirname(log_config['file'])
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
    
    async def initialize(self):
        """初始化爬虫"""
        crawler_config = self.config_manager.get_crawler_config()
        
        self.crawler = AsyncWebCrawler(
            verbose=False,
            headless=True,
            browser_type=crawler_config.get('browser_type', 'chrome'),
            wait_for=crawler_config.get('wait_for', 3000),
            timeout=crawler_config.get('timeout', 30000)
        )
        
        logger.info("Crawl4AI agent initialized")
    
    async def close(self):
        """关闭爬虫"""
        if self.crawler:
            await self.crawler.close()
            logger.info("Crawl4AI agent closed")
    
    @error_handler
    @performance_monitor
    async def crawl_by_data_type(self, company_name: str, company_code: str, data_type: str, 
                                strategy_type: str = 'llm', max_results: int = 10) -> List[Dict]:
        logger.info(f"Starting crawl for {company_name} ({company_code}) - {data_type}")
        if not self.crawler:
            await self.initialize()
        self.data_saver.clear_directory()
        urls = self.url_builder.build_urls_by_data_type(company_name, company_code, data_type)
        if not urls:
            logger.warning(f"No URLs found for data type: {data_type}")
            return []
        try:
            strategy = self.strategy_factory.create_strategy(strategy_type)
        except Exception as e:
            logger.error(f"Failed to create strategy {strategy_type}: {e}")
            return []
        processed_results = []
        tasks = []
        for url_info in urls[:max_results]:
            # 深交所公司公告专用采集逻辑
            if (
                url_info.get('source_name') in ['深交所', '深圳证券交易所官网']
                and data_type == '公司公告'
            ):
                try:
                    from crawler_agent.data_source.szse_data_source import fetch_szse_announcements
                    company_code = url_info.get('company_code')
                    # 传递专用参数
                    result = fetch_szse_announcements(
                        company_code=company_code,
                        download_pdfs=True,
                        max_pdfs=5,
                        save_dir="data/raw/announcements/szse_announcements",
                        datatype="公告"
                    )
                    if result:
                        # 包装为dict，添加元数据，兼容主流程
                        processed_results.append({
                            'source_name': url_info.get('source_name'),
                            'data_type': data_type,
                            'crawl_timestamp': time.time(),
                            'financial_data': result
                        })
                    continue
                except Exception as e:
                    logger.error(f"深交所公司公告专用采集失败: {e}")
                    continue
            # 东方财富网公司公告专用采集逻辑
            elif url_info.get('source_name') == "东方财富" and data_type == "公司公告":
                try:
                    # 东方财富网公司公告专用采集逻辑
                    from crawler_agent.data_source.eastmoney_data_source import fetch_eastmoney_announcements
                    result = fetch_eastmoney_announcements(
                        company_code=company_code,
                        save_dir="data/raw/announcements/eastmoney_announcements"
                    )
                    if result:
                        # 包装为dict，添加元数据，兼容主流程
                        processed_results.append({
                            'source_name': url_info.get('source_name'),
                            'data_type': data_type,
                            'crawl_timestamp': time.time(),
                            'financial_data': result
                        })
                except Exception as e:
                    logger.error(f"东方财富网公司公告专用采集失败: {e}")
                continue
            # 修复官网数据源调用参数
            if url_info.get('search_strategy') == 'llm_google_search':
                result = await self._crawl_llm_search(url_info, strategy)
                if result and isinstance(result, dict):
                    processed_data = self.data_processor.process_data(result, data_type)
                    processed_results.append(processed_data)
                continue
            task = self._crawl_single_url(url_info, strategy)
            tasks.append(task)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Crawl task failed: {result}")
                continue
            if result and isinstance(result, dict):
                processed_data = self.data_processor.process_data(result, data_type)
                processed_results.append(processed_data)
        if processed_results:
            self._save_crawl_results(processed_results, company_name, company_code, data_type)
        logger.info(f"Crawl completed for {data_type}: {len(processed_results)} results")
        return processed_results
    
    def _save_crawl_results(self, results: List[Dict], company_name: str, company_code: str, data_type: str):
        """保存爬取结果，按数据源分流到各自 save_dir"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        # 按 source_name 分组
        source_groups = {}
        for result in results:
            source = result.get('source_name', 'unknown')
            if source not in source_groups:
                source_groups[source] = []
            source_groups[source].append(result)
        # 保存每个数据源分组
        for source, group in source_groups.items():
            # 查找 save_dir
            save_dir = None
            try:
                ds_cfg = self.config_manager.get_data_sources_by_type(data_type).get(source, {})
                save_dir = ds_cfg.get('save_dir', None)
                # 新增：如果save_dir为dict（如company_website），则按data_type分流
                if isinstance(save_dir, dict):
                    save_dir = save_dir.get(data_type, None)
                # 修正：只有在save_dir为str且非空时才赋值
                if isinstance(save_dir, str) and save_dir:
                    self.data_saver.save_dir = save_dir
                else:
                    self.data_saver.save_dir = self.config_manager.config.get('save_dir', 'crawl_results')
            except Exception:
                pass
            # 判断是否 API 分端点
            api_endpoints = ds_cfg.get('api_endpoints', None)
            if api_endpoints:
                # 按 endpoint_type 再分组
                endpoint_groups = {}
                for item in group:
                    endpoint = item.get('endpoint_type', '')
                    if endpoint not in endpoint_groups:
                        endpoint_groups[endpoint] = []
                    endpoint_groups[endpoint].append(item)
                for endpoint, endpoint_results in endpoint_groups.items():
                    if endpoint_results:
                        self.data_saver.save_data(
                            data=endpoint_results,
                            data_type=data_type,
                            company_name=company_name,
                            company_code=company_code,
                            endpoint_type=endpoint,
                            timestamp=timestamp
                        )
            else:
                # 普通网页/LLM型或无端点API
                self.data_saver.save_data(
                    data=group,
                    data_type=data_type,
                    company_name=company_name,
                    company_code=company_code,
                    timestamp=timestamp
                )
    
    @error_handler
    async def _crawl_single_url(self, url_info: Dict, strategy: Any) -> Optional[Dict]:
        """爬取单个URL"""
        source_name = url_info['source_name']
        data_type = url_info['data_type']
        is_api = url_info.get('is_api', False)
        is_llm_search = url_info.get('is_llm_search', False)
        
        # 获取并发许可
        await self.concurrency_manager.acquire()
        
        try:
            if is_llm_search:
                # LLM+Google搜索类型：动态发现和爬取
                extracted_data = await self._crawl_llm_search(url_info, strategy)
            elif is_api:
                # API类型：直接HTTP请求
                url = url_info['url']
                cache_key = f"{url}_{data_type}_{source_name}"
                if 'endpoint_type' in url_info:
                    cache_key += f"_{url_info['endpoint_type']}"
                
                cached_result = self.cache_manager.get(cache_key)
                if cached_result:
                    logger.info(f"Using cached result for {url}")
                    return cached_result
                
                extracted_data = await self._crawl_api_url(url_info)
                
                # 仅在 extracted_data 非 None 时 set 缓存
                if extracted_data is not None:
                    self.cache_manager.set(cache_key, extracted_data)
            else:
                # 网页类型：使用Crawl4AI
                url = url_info['url']
                cache_key = f"{url}_{data_type}_{source_name}"
                
                cached_result = self.cache_manager.get(cache_key)
                if cached_result:
                    logger.info(f"Using cached result for {url}")
                    return cached_result
                
                if not self.crawler:
                    logger.error("Crawler not initialized")
                    return None
                    
                result = await self.crawler.arun(
                    url=url,
                    extraction_strategy=strategy
                )
                
                if result and hasattr(result, 'extracted_content') and result.extracted_content:
                    extracted_data = result.extracted_content
                else:
                    logger.warning(f"No content extracted from {url}")
                    return None
                
                if extracted_data is not None:
                    self.cache_manager.set(cache_key, extracted_data)
            
            # 添加元数据
            if isinstance(extracted_data, dict):
                extracted_data.update({
                    'source_name': source_name,
                    'data_type': data_type,
                    'crawl_timestamp': time.time()
                })
                
                if is_api and 'endpoint_type' in url_info:
                    extracted_data['endpoint_type'] = url_info['endpoint_type']
                elif is_llm_search:
                    extracted_data['search_strategy'] = 'llm_google_search'
                else:
                    extracted_data['source_url'] = url_info.get('url', '')
            
            logger.info(f"Successfully processed {source_name}")
            return extracted_data
                
        except Exception as e:
            logger.error(f"Failed to process {source_name}: {e}")
            return None
        finally:
            self.concurrency_manager.release()
    
    async def _crawl_llm_search(self, url_info: Dict, strategy: Any) -> Optional[Dict]:
        company = {
            'company_name': url_info.get('company_name'),
            'company_code': url_info.get('company_code')
        }
        data_type = url_info.get('data_type', '财务报表')
        crawler = CompanyFinancialReportCrawler()
        await crawler.initialize()
        result = await crawler.crawl_company_financial_reports(company, data_type=data_type)
        await crawler.close()
        return result
    
    async def _mock_google_search(self, keyword: str) -> List[Dict]:
        """模拟Google搜索结果（实际实现时需要替换为真实的Google搜索API）"""
        # 这里返回模拟的搜索结果
        # 实际实现时应该调用Google Custom Search API
        return [
            {
                'title': f'{keyword} - 搜索结果1',
                'url': f'https://example1.com/{keyword}',
                'snippet': f'这是关于{keyword}的搜索结果摘要1'
            },
            {
                'title': f'{keyword} - 搜索结果2', 
                'url': f'https://example2.com/{keyword}',
                'snippet': f'这是关于{keyword}的搜索结果摘要2'
            }
        ]
    
    async def _analyze_with_llm(self, prompt: str, strategy: Any) -> Dict:
        """使用LLM分析搜索结果"""
        try:
            # 这里应该调用LLM API进行分析
            # 暂时返回模拟结果
            return {
                'analysis': f'LLM分析结果: {prompt[:100]}...',
                'extracted_data': {
                    'website_url': 'https://example.com',
                    'financial_data': '模拟财务数据'
                }
            }
        except Exception as e:
            logger.error(f"LLM分析失败: {e}")
            return {'error': f'LLM analysis failed: {e}'}

    async def _crawl_api_url(self, url_info: Dict) -> Optional[Dict]:
        url = url_info['url']
        params = url_info.get('params', {})
        headers = url_info.get('headers', {})
        cookies = url_info.get('cookies', {})
        json_data = url_info.get('json', None)
        method = url_info.get('api_method', 'GET').upper()
        save_dir = url_info.get('save_dir', None)
        try:
            logger.info(f"[API采集] 请求 {method} {url}")
            logger.info(f"[API采集] params: {params}")
            logger.info(f"[API采集] headers: {headers}")
            logger.info(f"[API采集] cookies: {cookies}")
            logger.info(f"[API采集] json: {json_data}")
            async with aiohttp.ClientSession() as session:
                if method == 'POST':
                    response = await session.post(url, params=params, headers=headers, cookies=cookies, json=json_data, ssl=False)
                else:
                    response = await session.get(url, params=params, headers=headers, cookies=cookies, ssl=False)
                logger.info(f"[API采集] 响应状态码: {response.status}")
                logger.info(f"[API采集] 响应headers: {dict(response.headers)}")
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"[API采集] 响应内容(部分): {str(data)[:500]}")
                    # 保存目录分流
                    if save_dir:
                        self.data_saver.save_dir = save_dir
                    return {
                        'api_data': data,
                        'status_code': response.status,
                        'content_type': response.headers.get('content-type', '')
                    }
                else:
                    text = await response.text()
                    logger.error(f"[API采集] API request failed: {response.status}")
                    logger.error(f"[API采集] 错误响应内容(部分): {text[:500]}")
                    return {
                        'error': f"HTTP {response.status}",
                        'status_code': response.status,
                        'response_text': text[:1000],
                        'url': url,
                        'params': params,
                        'headers': headers,
                        'cookies': cookies
                    }
        except Exception as e:
            logger.error(f"[API采集] 请求异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'error': f"Exception: {e}",
                'status_code': None,
                'params': params,
                'headers': headers,
                'cookies': cookies
            }
    
    @error_handler
    @performance_monitor
    async def crawl_with_retry(self, company_name: str, company_code: str, data_type: str,
                              strategy_type: str = 'llm', max_results: int = 10,
                              max_retries: int = None) -> List[Dict]:
        """带重试机制的爬取"""
        if max_retries is None:
            max_retries = self.config_manager.get_error_handling_config().get('max_retries', 3) or 3
        
        for attempt in range(max_retries + 1):
            try:
                results = await self.crawl_by_data_type(
                    company_name, company_code, data_type, strategy_type, max_results
                )
                
                if results:
                    return results
                
                if attempt < max_retries:
                    delay = self.config_manager.get_error_handling_config().get('retry_delay', 2.0)
                    logger.info(f"Retry {attempt + 1}/{max_retries} in {delay} seconds...")
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries:
                    delay = self.config_manager.get_error_handling_config().get('retry_delay', 2.0)
                    await asyncio.sleep(delay)
        
        logger.error(f"All {max_retries + 1} attempts failed")
        return []
    
    @error_handler
    @performance_monitor
    async def batch_crawl(self, companies: List[Dict], data_types: List[str],
                         strategy_type: str = 'llm', max_results: int = 10) -> Dict:
        """批量爬取多个公司的多种数据类型"""
        logger.info(f"Starting batch crawl for {len(companies)} companies, {len(data_types)} data types")
        
        all_results = {}
        
        for company in companies:
            company_name = company['name']
            company_code = company['code']
            
            company_results = {}
            for data_type in data_types:
                try:
                    results = await self.crawl_by_data_type(
                        company_name, company_code, data_type, strategy_type, max_results
                    )
                    company_results[data_type] = results
                except Exception as e:
                    logger.error(f"Failed to crawl {data_type} for {company_name}: {e}")
                    company_results[data_type] = []
            
            all_results[f"{company_name}_{company_code}"] = company_results
        
        logger.info(f"Batch crawl completed: {len(all_results)} companies processed")
        return all_results
    
    def get_available_data_types(self) -> List[str]:
        """获取可用的数据类型"""
        data_sources = self.config_manager.config.get('data_sources', {})
        return list(data_sources.keys())
    
    def get_data_sources_for_type(self, data_type: str) -> List[str]:
        """获取指定数据类型的数据源列表"""
        data_sources = self.config_manager.get_data_sources_by_type(data_type)
        return list(data_sources.keys())
    
    def get_search_keywords_for_type(self, data_type: str) -> List[str]:
        """获取指定数据类型的搜索关键词"""
        return self.url_builder.generate_search_keywords("示例公司", "000001", data_type)
    
    @error_handler
    @performance_monitor
    async def crawl_cninfo_financial_reports(self, company_name: str, company_code: str, max_reports: int = 5) -> List[Dict]:
        """
        爬取巨潮资讯网财务报表
        :param company_name: 公司名称
        :param company_code: 公司代码
        :param max_reports: 最大报告数量
        :return: 财务报表列表
        """
        # 先校验 company_code，避免传入 None 或非法值
        if not company_code or not str(company_code).strip().isdigit():
            logger.warning(f"跳过巨潮采集：无效的公司代码 '{company_code}' for {company_name}")
            return []
        company_code = str(company_code).strip()
        
        logger.info(f"开始爬取 {company_name}({company_code}) 的巨潮资讯网财务报表")
        
        try:
            # 获取巨潮资讯网配置
            cninfo_config = self.config_manager.get_data_sources_by_type("财务报表").get("巨潮资讯网", {})
            if not cninfo_config:
                logger.error("未找到巨潮资讯网配置")
                return []
            
            # 构建API请求
            base_url = cninfo_config.get("base_url", "http://www.cninfo.com.cn")
            api_endpoints = cninfo_config.get("api_endpoints", {})
            
            results = []
            
            # 遍历不同的财务报表类型
            for report_type, api_name in api_endpoints.items():
                try:
                    url = f"{base_url}/data20/financialData/{api_name}"
                    params = {
                        "scode": company_code,
                        "sign": "1"
                    }
                    
                    headers = cninfo_config.get("headers", {})
                    cookies = cninfo_config.get("cookies", {})
                    
                    # 处理动态参数
                    headers = self.dynamic_processor.process_dict(headers, {
                        "company_code": company_code,
                        "timestamp": str(int(time.time())),
                        "random_uuid": str(uuid.uuid4())
                    })
                    
                    logger.info(f"请求巨潮资讯网 {report_type} 数据: {url}")
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, params=params, headers=headers, cookies=cookies) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                if data and isinstance(data, dict):
                                    # 处理返回的数据
                                    processed_data = {
                                        "source": "巨潮资讯网",
                                        "report_type": report_type,
                                        "company_name": company_name,
                                        "company_code": company_code,
                                        "api_name": api_name,
                                        "raw_data": data,
                                        "timestamp": datetime.now().isoformat()
                                    }
                                    results.append(processed_data)
                                    logger.info(f"成功获取 {report_type} 数据")
                                else:
                                    logger.warning(f"{report_type} 返回数据格式异常")
                            else:
                                logger.warning(f"{report_type} 请求失败: {resp.status}")
                
                except Exception as e:
                    logger.error(f"获取 {report_type} 数据时出错: {e}")
                    continue
            
            logger.info(f"巨潮资讯网爬取完成，共获取 {len(results)} 份报告")
            return results[:max_reports]
            
        except Exception as e:
            logger.error(f"巨潮资讯网爬取失败: {e}")
            return []
    
    @error_handler
    async def _cninfo_step1_search_reports(self, company_name: str, company_code: str) -> List[Dict]:
        """
        巨潮资讯网步骤1：搜索财务报表
        """
        logger.info(f"步骤1: 在巨潮网搜索 {company_name} 的财务报表")
        
        try:
            # 使用搜索API
            search_url = "http://www.cninfo.com.cn/new/fulltextSearch"
            params = {
                "notautosubmit": "",
                "keyWord": f"{company_name} 年报 季报",
                "searchType": "0",
                "pageNum": "1",
                "pageSize": "10",
                "stock": company_code
            }
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, params=params, headers=headers) as resp:
                    if resp.status == 200:
                        content = await resp.text()
                        # 这里需要解析HTML内容，提取搜索结果
                        # 简化实现，返回模拟数据
                        return [
                            {
                                "title": f"{company_name} 2024年年度报告",
                                "type": "年报",
                                "publish_date": "2024-03-31",
                                "url": f"http://www.cninfo.com.cn/new/disclosure/detail?stockCode={company_code}&announcementId=123456"
                            }
                        ]
                    else:
                        logger.warning(f"搜索请求失败: {resp.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"搜索财务报表失败: {e}")
            return []
    
    @error_handler
    async def _cninfo_step2_3_view_report_detail(self, report_info: Dict) -> Optional[Dict]:
        """
        巨潮资讯网步骤2&3：查看报告详情
        """
        logger.info(f"步骤2&3: 获取报告详细信息")
        
        try:
            # 这里应该访问详情页并提取信息
            # 简化实现，返回模拟数据
            return {
                "title": report_info.get("title", "Unknown"),
                "source": "巨潮资讯网",
                "search_date": datetime.now().isoformat(),
                "financial_data": {
                    "revenue": "1000亿元",
                    "net_profit": "500亿元",
                    "total_assets": "2000亿元",
                    "equity": "1500亿元"
                }
            }
            
        except Exception as e:
            logger.error(f"获取报告详情失败: {e}")
            return None

# 使用示例
async def main():
    """主函数示例"""
    async with ImprovedCrawl4AIAgent() as agent:
        # 爬取贵州茅台的财务报表
        results = await agent.crawl_by_data_type(
            company_name="贵州茅台",
            company_code="600519",
            data_type="财务报表",
            strategy_type="llm",
            max_results=5
        )
        
        print(f"Found {len(results)} results")
        for result in results:
            print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(main()) 