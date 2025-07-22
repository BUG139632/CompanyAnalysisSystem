# Business Agent 使用说明

## 功能简介
Business Agent 负责对 expert agent 生成的公司经营策略进行结构化分析，包括：
- 单条策略的风险、收益、可行性等多维度分析
- 多策略横向对比分析，给出优劣势、适配性、互补/冲突点和综合建议
- 自动保存分析结果，便于后续查阅和复盘

## 输入说明
- **对话历史文件**：由 expert agent 生成，包含策略、理由、风险等结构化内容
- **分析维度**：如“管理模式分析”、“商业模式分析”等，由 analysis agent 传入
- **公司名**：当前分析的目标公司
- **行业背景向量库**：用于检索相关行业案例和背景信息
- **公司财报分析数据**：从 `data/analysis/` 目录下按维度读取

## 输出说明
- 每条策略的结构化分析（markdown格式，分为四部分）
- 所有策略的横向对比分析
- 结果自动保存到 `data/biz_analysis/` 目录，文件名格式为：
  `biz_analysis_公司名_维度_时间戳.json`

## 主要流程
1. 读取对话历史文件，提取所有策略、理由、风险
2. 读取公司财报分析摘要和行业背景信息
3. 对每条策略调用 LLM 进行结构化分析，输出统一格式
4. 汇总所有策略分析，调用 LLM 生成横向对比分析
5. 将结果以如下结构写入 json 文件：

```json
{
  "results": [
    {"strategy": "...", "analysis": "...markdown..."},
    ...
  ],
  "compare": "...横向对比分析markdown..."
}
```

## 与 expert/analysis agent 的联动
- expert agent 生成策略后，询问用户是否需要进一步分析，确认后自动调用 business agent
- analysis agent 负责传递分析维度和公司名，保证数据链路一致

## 输出文件结构示例
```json
{
  "results": [
    {
      "strategy": "策略A",
      "analysis": "## 策略分析：策略A\n1. ...\n2. ...\n3. ...\n4. ..."
    },
    {
      "strategy": "策略B",
      "analysis": "## 策略分析：策略B\n1. ...\n2. ...\n3. ...\n4. ..."
    }
  ],
  "compare": "# 策略横向对比\n1. ...\n2. ...\n3. ...\n4. ..."
}
```

## 常见问题
- **Q: 为什么公司财务数据概要为“无该公司财报分析数据”？**
  - A: 说明 `data/analysis/` 目录下对应维度的 json 文件没有 `analysis_result` 字段或内容为空。
- **Q: 读取结果时报 list indices must be integers or slices, not str？**
  - A: 现在输出文件是 dict 结构，需用 `data["results"]` 和 `data["compare"]` 访问。

## 扩展建议
- 支持多公司、多维度批量分析
- 输出格式可扩展为 html、pdf 或数据库存储
- 可集成前端界面，支持可视化展示和交互 