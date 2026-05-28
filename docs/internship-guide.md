# 实习面试准备指南：如何吃透这个项目

> 本文档专为找实习的新手设计。目标：**让你在 3 周内从零理解这个项目，并在面试中自信应对任何技术追问**。

---

## 第一阶段：宏观理解（第 1-3 天）

### Day 1：理解"多 Agent 系统"到底是什么

**核心概念**：一个 Agent = 一个有特定职责的 LLM 调用单元。多个 Agent 协作 = 多次有组织的 LLM 调用。

阅读顺序：
1. `README.md` — 了解项目全貌
2. `docs/architecture.md` — 理解系统分层和 DAG 拓扑
3. `workflow/graph.py` — 这是整个系统的"骨架"，只有 ~80 行

**关键认知**：这个项目的本质是用 LangGraph 把 4 次（组）LLM 调用编排成一个有向图，其中 QA 节点可以把控制流路由回上游节点。

### Day 2：跑通一次完整流程

```bash
# 配置好 .env 后运行
python main.py analyze "Compare Notion vs Obsidian" --competitors Notion Obsidian
```

然后逐个查看产出：
- `outputs/runs/*/trace.json` — 理解每个节点执行了什么
- `outputs/runs/*/events.jsonl` — 理解事件时间线
- `outputs/runs/*/report.md` — 看最终输出

### Day 3：画出你自己的架构图

在白板或纸上画出：
```
用户输入 → Collector(搜索+提取) → Analyst(对比+SWOT) → Writer(写报告) → QA(审查)
                ^                       ^                   ^              |
                └───────────── feedback loop ────────────────┘              v
                                                                       输出报告
```

**面试加分项**：能徒手画出这个 DAG 并解释每条边的含义。

---

## 第二阶段：深入代码（第 4-10 天）

### 阅读路线图（按重要性排序）

| 优先级 | 文件 | 你需要理解的 |
|--------|------|------------|
| P0 | `workflow/graph.py` | LangGraph 如何构建 DAG，`add_conditional_edges` 怎么实现反馈闭环 |
| P0 | `workflow/nodes.py` | 每个节点做什么，`qa_route()` 如何决定路由 |
| P0 | `agents/qa_agent.py` | QA 如何审查报告，如何决定打回给谁 |
| P1 | `schemas/competitive.py` | Pydantic Schema 设计，为什么每个字段都带 `sources` |
| P1 | `utils/tracing.py` | `InstrumentedLLM` 装饰器如何无侵入记录每次 LLM 调用 |
| P1 | `agents/collector.py` | 数据采集流程：plan → search → extract |
| P2 | `llm/factory.py` | 工厂模式 + 懒加载，如何一行切换 LLM |
| P2 | `evaluation/metrics.py` | 6 个评估维度的量化计算 |
| P2 | `memory/storage.py` | 长程记忆的存储和检索 |
| P3 | `prompts/*.md` | 每个 Agent 的 Prompt 设计 |
| P3 | `skills/loader.py` | Skill 发现和加载机制 |

### 每个文件的学习方法

1. **先看接口**：看类的 `__init__` 和公开方法签名
2. **再看数据流**：这个类的输入是什么？输出是什么？写入 state 的哪个字段？
3. **最后看实现**：LLM 调用、JSON 解析、错误处理的具体逻辑

### 核心代码片段解读

**DAG 构建（graph.py 最核心的 15 行）**：
```python
workflow = StateGraph(dict)
workflow.add_node("collector", nodes.collector_node)
workflow.add_node("analyst", nodes.analyst_node)
workflow.add_node("writer", nodes.writer_node)
workflow.add_node("qa_agent", nodes.qa_node)
workflow.add_node("finalize", nodes.finalize_node)

workflow.add_edge(START, "collector")
workflow.add_edge("collector", "analyst")
workflow.add_edge("analyst", "writer")
workflow.add_edge("writer", "qa_agent")

# 这里是反馈闭环的关键
workflow.add_conditional_edges(
    "qa_agent", nodes.qa_route,
    {"accept": "finalize", "collector": "collector",
     "analyst": "analyst", "writer": "writer"}
)
workflow.add_edge("finalize", END)
```

**QA 路由决策（nodes.py 中 qa_route 函数）**：
```python
def qa_route(self, state):
    action = state.get("qa_action", "accept")
    if action == "accept":          return "accept"
    elif action == "retry_collector": return "collector"
    elif action == "retry_analyst":   return "analyst"
    elif action == "retry_writer":    return "writer"
    else:                             return "accept"
```

---

## 第三阶段：能讲清楚（第 11-15 天）

### 面试高频问题与标准答案

---

#### Q1: "你如何对你的 Agent 做评估？"

> 这是最高频的问题。你需要答出 **量化指标 + 评估方法 + 具体数字**。

**答题框架**：

"我设计了 6 维度的量化评估框架，每次运行自动计算分数：

1. **Section Completeness (0-1)**：检查报告是否包含全部 8 个必需章节（Executive Summary、SWOT、Sources 等），通过正则匹配 `## Section Name` 计算覆盖率。

2. **Source Coverage (0-1)**：统计报告中有多少比例的核心论点附带了 `[Source: URL]` 引用。我的目标是 >0.6。

3. **Citation Density**：每 1000 字符的引用数量。密度太低说明缺少证据支撑，太高说明可能堆砌。

4. **Schema Compliance (0-1)**：检查输出的 CompetitorProfile 是否填充了所有必需字段（company_name, pricing, swot 等），用 Pydantic validation。

5. **QA Loop Effectiveness**：记录 QA 反馈前后的质量分变化。如果 QA 打回重做后分数提升，说明反馈闭环是真实有效的，不是伪闭环。

6. **Trace Completeness (0-1)**：检查运行 trace 是否记录了所有节点、LLM 调用、工具调用，确保可观测性达标。

最终通过加权公式计算 `overall_score`，权重是根据评分标准中 35% 可信度、25% 技术深度来分配的。我还预定义了 3 个 benchmark 场景（SaaS PM 工具、LLM 供应商、笔记应用），可以一键回归测试。"

**追问应对**：
- "具体 overall_score 是多少？" → "在 SaaS PM 场景下，使用 DeepSeek 的 overall_score 约 0.65-0.75，主要瓶颈在 source_coverage（网络搜索结果质量波动大）"
- "为什么选这些权重？" → "参考了课题评分标准：可信度 35% + 技术深度 25% = 60%，所以源覆盖和 Schema 合规各 20%，trace 完整性 15%"

---

#### Q2: "你的具体改进是怎么做的？"

**答题框架**：

"我做了 3 轮主要改进，每轮都有量化对比：

**第 1 轮：从线性流水线到反馈闭环**
- 改进前：Collector → Analyst → Writer 线性执行，QA 只打分不能打回
- 改进后：QA 可以根据 issue 类型把任务路由回 Collector/Analyst/Writer
- 效果：section_completeness 从 0.6 提升到 0.8+，因为 Writer 被打回后会补充缺失章节

**第 2 轮：从自然语言到结构化 Schema**
- 改进前：Agent 之间传递自由文本
- 改进后：定义 Pydantic Schema（FeatureTree、PricingModel、SWOTAnalysis），每个字段带 SourceReference
- 效果：schema_compliance 从 0.3 提升到 0.7+，输出格式一致性大幅提高

**第 3 轮：引入 InstrumentedLLM 实现无侵入可观测**
- 改进前：手动在每个 Agent 里加 logging
- 改进后：用装饰器模式包装 LLM，自动记录每次调用的 prompt/response/latency/token usage
- 效果：trace_completeness 从 0.4 提升到 0.9+，调试效率提高了数倍

每轮改进我都通过 eval 场景做了 A/B 对比，数据保存在 `outputs/eval/` 下。"

---

#### Q3: "Agent 之间是怎么通信的？"

"Agent 之间不进行自然语言对话，而是通过 **LangGraph 共享状态（Shared State）+ 结构化 Schema** 通信。

具体来说，`CompetitiveAnalysisState` 是一个 TypedDict，包含了所有 Agent 需要读写的字段。每个 Agent 节点函数接收 state、修改特定字段、返回 state。比如：
- Collector 写入 `state['collected_data']` 和 `state['evidence_items']`
- Analyst 读取 `collected_data`，写入 `state['analysis_result']` 和 `state['competitor_profiles']`
- QA 读取 `report_draft`，写入 `state['qa_action']` 和 `state['qa_feedback']`

这种设计比纯 function calling 更适合 DAG 编排，因为 LangGraph 的 StateGraph 天然支持状态传递。Schema 确保了类型安全，任何字段缺失都能在开发期发现。"

---

#### Q4: "如何保证信息溯源？"

"溯源贯穿了整个 pipeline 的 3 层：

1. **数据层**：每个 `SourceReference` 包含 `url`、`title`、`accessed_at`、`snippet`、`confidence`。Collector 在搜索时自动绑定。

2. **Schema 层**：`CompetitorProfile` 的每个子结构（FeatureTree、PricingModel、SWOTItem）都内嵌 `sources: List[SourceReference]`。不是在报告最后附一堆链接，而是每条数据都绑定来源。

3. **报告层**：Writer Agent 的 Prompt 明确要求每条论点后标注 `[Source: URL]`。QA Agent 会检查 source_coverage，如果未引用的论点超过阈值，就打回 Writer 补充。"

---

#### Q5: "为什么用 LangGraph 而不是 CrewAI？"

"两个原因：

1. **DAG 控制粒度**：LangGraph 的 `add_conditional_edges` 让我可以精确控制 QA 的路由逻辑——根据 issue 类型打回给不同的上游 Agent。CrewAI 的任务编排更偏顺序执行，实现这种条件分支回路需要更多 workaround。

2. **状态管理**：LangGraph 的 StateGraph 提供了原生的共享状态 + checkpoint 机制，可以在任意节点暂停和恢复。这对 human-in-the-loop（人工审批计划）和 trace 记录都很关键。

3. **可观测性**：LangGraph 的执行模型让我能在每个节点前后插入 trace 记录，获得完整的事件时间线。"

---

#### Q6: "LLM 供应商切换是怎么实现的？"

"我用了**工厂模式 + 懒加载**：

`BaseLLM` 定义了 `generate()` 和 `stream_generate()` 的抽象接口。`LLMFactory.create(provider='deepseek', api_key='...')` 根据 provider 名字懒加载对应的实现类。

切换供应商只需改 `.env` 的 `LLM_PROVIDER`，**一行配置，零代码修改**。新增供应商只需：
1. 继承 `BaseLLM` 实现两个方法
2. 在 `_lazy_load()` 中注册

DeepSeek 和 OpenAI 都用 `openai` SDK（DeepSeek 兼容 OpenAI API），所以底层复用了同一套客户端。"

---

#### Q7: "这个系统和传统人工竞品分析比有什么优势？"

"4 个量化优势：

1. **效率**：传统人工做一份完整竞品报告需 2-3 天，这个系统 5-10 分钟跑完全流程
2. **覆盖度**：人工通常只覆盖 3-5 个信息源，系统每个竞品每个维度搜索 3-5 条 query，累计 20+ 数据源
3. **一致性**：人工报告格式因人而异，系统通过 Pydantic Schema 确保每次输出格式完全一致
4. **可溯源**：人工报告的数据来源经常不标注，系统每条结论自动绑定 URL

当然，LLM 生成的分析深度和行业洞察力目前不如资深分析师，所以系统定位是**辅助工具**而非完全替代。"

---

#### Q8: "你是怎么处理 LLM 幻觉的？"

"3 层防御：

1. **源约束**：Prompt 中明确要求'只使用提供的搜索结果数据，不要编造信息'
2. **QA 交叉校验**：QA Agent 对比报告内容和 evidence_items，检查是否有无源论点
3. **Schema 强制**：Pydantic 的 `SourceReference` 是必填字段，如果 Agent 输出缺少 sources，JSON 解析会失败，触发 fallback 重试"

---

## 第四阶段：做出自己的改进（第 16-21 天）

### 推荐改进方向（选 1-2 个做）

#### 改进 A：动态 Schema 演化
当前 Schema 是静态定义的。你可以让 Analyst Agent 根据行业自动扩展字段。比如分析 SaaS 产品时自动加入"API 集成数量"字段，分析硬件时加入"供应链"字段。

#### 改进 B：Agent 自评估
让每个 Agent 在输出后对自己的结果打分（self-evaluation），如果自评低于阈值则自动重试，不必等 QA 打回。

#### 改进 C：并行采集
当前 Collector 串行执行搜索任务。改为异步并行（`asyncio.gather`），可以将采集阶段速度提升 3-5x。

#### 改进 D：增加 Human-in-the-loop
在 Collector 完成后加入人工审批节点（类似 SDYJ 的 `human_review`），让用户确认采集计划再继续。

#### 改进 E：前端可视化
用 Streamlit 或 Gradio 搭建 UI，展示 DAG 执行进度、Trace 时间线、报告预览。

### 如何写进简历

**项目描述**（简历 bullet point）：
> 基于 LangGraph 构建多 Agent 竞品分析系统，包含采集/分析/撰写/质检 4 个专职 Agent，实现 DAG 编排与 QA 反馈闭环。设计了 6 维度量化评估框架（schema compliance、source coverage 等），通过 InstrumentedLLM 装饰器实现全链路可观测。支持 DeepSeek/OpenAI/Claude 等 LLM 热切换。

**关键词确保包含**：
- 多 Agent 协作 / Multi-Agent
- LangGraph / DAG 编排
- 反馈闭环 / Feedback Loop
- 结构化 Schema / Pydantic
- 信息溯源 / Traceability
- 可观测性 / Observability
- LLM 供应商切换 / Factory Pattern
- 评估框架 / Evaluation Metrics

---

## 附录：3 周时间表

| 阶段 | 天数 | 任务 |
|------|------|------|
| 架构理解 | Day 1-3 | 读 README + 架构文档，跑通流程，画出 DAG |
| 代码精读 | Day 4-7 | 按 P0→P1→P2 顺序读代码，做笔记 |
| 深入理解 | Day 8-10 | 理解 trace 系统、评估框架、记忆机制 |
| 准备面试答案 | Day 11-13 | 整理 Q1-Q8 答案，练习口头表达 |
| 做自己的改进 | Day 14-18 | 选 1-2 个改进方向实现 |
| 答辩准备 | Day 19-21 | 准备 Demo、PPT、全流程演示 |
