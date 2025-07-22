# LangChain 集成指南

## 概述

本项目已经成功集成了 LangChain，为所有 agent 提供了强大的 LLM 应用开发能力。集成采用渐进式方案，确保向后兼容性和稳定性。

## 升级内容

### 1. LLMBaseAgent 升级

- ✅ 添加了 LangChain 支持
- ✅ 保持向后兼容原有 Gemini API 调用
- ✅ 智能回退机制
- ✅ 增强的上下文管理
- ✅ 链式处理支持

### 2. 新增功能

- **智能回退**：LangChain 失败时自动回退到原有方式
- **记忆管理**：支持 LangChain 的记忆组件
- **链式处理**：可以创建自定义的处理链
- **配置驱动**：通过 YAML 配置文件控制功能

## 安装步骤

### 1. 安装依赖

```bash
# 运行安装脚本
./install_langchain.sh
```

或者手动安装：

```bash
# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements_langchain.txt
```

### 2. 设置环境变量

```bash
export GEMINI_API_KEY="your_gemini_api_key_here"
```

### 3. 验证安装

```bash
python3 test_llm_base_agent.py
```

## 配置说明

### 配置文件位置

`config/langchain_config.yaml`

### 主要配置项

```yaml
# 启用 LangChain
langchain_enabled: true

# 回退到原有方式
fallback_to_original: true

# LLM 参数
temperature: 0.1
max_tokens: 2000
max_memory_tokens: 4000
```

## 使用方法

### 1. 基本使用（保持原有方式）

```python
from common.llm_base_agent import LLMBaseAgent

# 不启用 LangChain，使用原有方式
agent = LLMBaseAgent(agent_name="MyAgent")
result = agent.llm_generate("请分析这个数据")
```

### 2. 启用 LangChain

```python
from common.llm_base_agent import LLMBaseAgent

# 启用 LangChain
agent = LLMBaseAgent(
    config_path="config/langchain_config.yaml",
    agent_name="MyLangChainAgent"
)

# 检查 LangChain 状态
print(agent.get_langchain_status())

# 使用 LangChain 调用
result = agent.llm_generate("请分析这个数据")
```

### 3. 创建自定义链

```python
# 创建数据清洗链
cleaning_chain = agent.create_chain(
    prompt_template="请根据以下规则清洗数据：\n规则：{rules}\n数据：{data}\n清洗后的数据：",
    input_variables=["rules", "data"]
)

# 使用链
result = cleaning_chain.run(
    rules="去除空值，标准化日期格式",
    data="原始数据内容"
)
```

### 4. 上下文管理

```python
# 添加上下文
agent.add_to_context("用户: 请分析财务数据")
agent.add_to_context("助手: 好的，我来帮您分析")

# 获取上下文
context = agent.get_context()

# 清除上下文
agent.clear_context()
```

## 渐进式集成策略

### 第一阶段：基础设施 ✅

- [x] 升级 LLMBaseAgent
- [x] 添加 LangChain 支持
- [x] 实现回退机制
- [x] 创建配置文件

### 第二阶段：选择性增强

- [ ] 升级 DataCleanAgent
- [ ] 添加智能数据清洗功能
- [ ] 集成 PDF 处理能力

### 第三阶段：逐步扩展

- [ ] 升级 AnalysisAgent
- [ ] 升级 BusinessAgent
- [ ] 升级 ExpertAgent
- [ ] 升级 VisualizationAgent

### 第四阶段：多 Agent 协作

- [ ] 实现 Agent 编排系统
- [ ] 创建处理流水线
- [ ] 优化协作机制

## 故障排除

### 常见问题

1. **LangChain 导入失败**
   ```bash
   pip install langchain langchain-google-genai
   ```

2. **Gemini API 调用失败**
   - 检查 GEMINI_API_KEY 环境变量
   - 确认 API 配额和权限

3. **回退机制不工作**
   - 检查 fallback_to_original 配置
   - 查看日志中的错误信息

### 调试技巧

```python
# 检查 LangChain 状态
agent = LLMBaseAgent(config_path="config/langchain_config.yaml")
print(agent.get_langchain_status())

# 测试回退机制
result = agent.llm_generate("测试提示")
print(f"结果: {result}")
```

## 性能优化

### 1. 记忆管理

```python
# 限制记忆大小
max_memory_tokens: 4000

# 定期清理记忆
agent.clear_context()
```

### 2. 链式处理

```python
# 预创建常用链
analysis_chain = agent.create_chain(
    prompt_template="分析数据：{data}",
    input_variables=["data"]
)

# 重复使用链
for data in data_list:
    result = analysis_chain.run(data=data)
```

## 下一步计划

1. **开发 DataCleanAgent**：使用 LangChain 进行智能数据清洗
2. **增强分析能力**：为其他 agent 添加 LangChain 功能
3. **优化性能**：改进记忆管理和链式处理
4. **扩展工具**：集成更多 LangChain 工具和组件

## 贡献指南

1. 遵循渐进式集成原则
2. 保持向后兼容性
3. 添加适当的测试
4. 更新文档和配置

---

**注意**：LangChain 集成是可选的，原有功能完全不受影响。可以根据需要逐步启用 LangChain 功能。 