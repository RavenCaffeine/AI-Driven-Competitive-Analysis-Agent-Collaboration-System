# 架构设计与可扩展性详解

## 1. 整体架构

本系统采用 **DAG（有向无环图）+ 反馈闭环** 的多 Agent 协作架构，基于 LangGraph StateGraph 实现。

### 1.1 系统分层

```
┌──────────────────────────────────────────────────┐
│                  CLI / API 层                     │
│         (cli/main.py, main.py)                    │
├──────────────────────────────────────────────────┤
│              Workflow 编排层                       │
│    (workflow/graph.py, nodes.py, state.py)        │
│    LangGraph StateGraph + MemorySaver            │
├──────────────────────────────────────────────────┤
│              Agent 业务层                          │
│  ┌─────────┐ ┌─────────┐ ┌────────┐ ┌────────┐  │
│  │Collector│ │ Analyst │ │ Writer │ │   QA   │  │
│  │  Agent  │ │  Agent  │ │ Agent  │ │ Agent  │  │
│  └─────────┘ └─────────┘ └────────┘ └────────┘  │
├──────────────────────────────────────────────────┤
│           基础设施层                               │
│  ┌─────┐ ┌────────┐ ┌───────┐ ┌──────┐ ┌──────┐│
│  │ LLM │ │Schemas │ │Memory │ │Tools │ │Trace ││
│  │Layer│ │(Pydantic)│ │System │ │(Web) │ │System││
│  └─────┘ └────────┘ └───────┘ └──────┘ └──────┘│
└──────────────────────────────────────────────────┘
```

### 1.2 DAG 流转拓扑

```
START ──> Collector ──> Analyst ──> Writer ──> QA Agent
              ^            ^           ^          │
              │            │           │          v
              └─── (feedback loop) ────┘     Finalize ──> END
```

关键设计：QA Agent 通过 `qa_route` 条件路由实现反馈闭环：
- `accept` → 报告合格，进入 Finalize
- `retry_collector` → 数据不足，重新采集
- `retry_analyst` → 分析质量不够，重新分析
- `retry_writer` → 写作问题，重新撰写

## 2. 核心设计模式

### 2.1 LLM 工厂模式 (Factory Pattern)

```python
# 运行时切换 LLM 供应商
llm = LLMFactory.create(
    provider="deepseek",  # 或 "openai", "claude", "gemini"
    api_key="...",
    model="deepseek-chat",
)
```

**可扩展点**：新增 LLM 供应商只需：
1. 继承 `BaseLLM` 实现 `generate()` 和 `stream_generate()`
2. 在 `factory.py` 的 `_lazy_load()` 中注册
3. 或调用 `LLMFactory.register_provider("my_llm", MyLLM)` 动态注册

### 2.2 结构化消息传递 (Schema-based Communication)

Agent 之间不使用自然语言对话，而是通过 **Pydantic Schema** 传递结构化数据：

```python
# schemas/competitive.py 定义了完整的知识 Schema
CompetitorProfile:
  ├── FeatureTree        # 功能树
  ├── PricingModel       # 定价模型
  ├── UserProfile        # 用户画像
  ├── SWOTAnalysis       # SWOT 分析
  ├── ReviewSummary      # 用户评价
  └── SourceReference[]  # 每个字段都有数据来源
```

### 2.3 InstrumentedLLM 装饰器模式

```python
# 自动记录每次 LLM 调用的延迟、Token 用量、输入输出
instrumented = InstrumentedLLM(inner_llm, trace)
```

### 2.4 长程记忆 (deerflow 模式)

```python
memory = MemoryStorage(storage_path="./outputs/memory/competitive_memory.json")
context = memory.get_relevant_context(query, competitors)
memory.add_fact("Notion 在 2024 年推出了 AI 功能", confidence=0.9, source="url")
memory.update_competitor_history("Notion", snapshot)
```

## 3. 可扩展性设计

### 3.1 新增 Agent

1. 在 `agents/` 下创建新 Agent 类
2. 在 `workflow/nodes.py` 添加对应节点函数
3. 在 `workflow/graph.py` 中将新节点加入 DAG

### 3.2 新增搜索工具

1. 在 `tools/` 下实现新工具类，暴露 `search(query) -> Dict` 接口
2. 在配置中添加 API Key
3. 在 `cli/main.py` 的 `build_tools()` 中注册

### 3.3 新增 Skill

1. 在 `skills/builtin/` 或 `skills/custom/` 下创建目录
2. 编写 `SKILL.md` 定义技能描述和 Prompt 模板
3. Skill Loader 会自动发现并加载

### 3.4 新增评估指标

1. 在 `evaluation/metrics.py` 中添加计算函数
2. 在 `evaluate_run()` 中将新指标加入加权计算
3. 在 `evaluation/scenarios.py` 中设置阈值

### 3.5 新增 Schema 字段

1. 在 `schemas/competitive.py` 中扩展 Pydantic Model
2. 相应 Agent 的 Prompt 模板中引用新字段
3. 评估指标中检查新字段的 compliance

## 4. 关键文件导读

| 文件 | 功能 | 阅读优先级 |
|------|------|-----------|
| `workflow/graph.py` | DAG 编排核心，理解系统全貌 | ★★★★★ |
| `workflow/nodes.py` | 节点函数与 QA 路由逻辑 | ★★★★★ |
| `agents/qa_agent.py` | 反馈闭环的关键实现 | ★★★★☆ |
| `schemas/competitive.py` | 知识 Schema，理解数据流 | ★★★★☆ |
| `utils/tracing.py` | 可观测性实现 | ★★★★☆ |
| `llm/factory.py` | LLM 切换机制 | ★★★☆☆ |
| `evaluation/metrics.py` | Agent 评估方法 | ★★★☆☆ |
| `memory/storage.py` | 长程记忆设计 | ★★★☆☆ |

## 5. 与参考项目的关系

| 设计要素 | 本项目 | SDYJ_Multi_Agents | deerflow |
|----------|--------|-------------------|----------|
| LLM 抽象 | BaseLLM + Factory | 相同模式 | Provider Config |
| 编排框架 | LangGraph StateGraph | LangGraph StateGraph | LangGraph |
| Agent 角色 | 4个竞品分析专职 | 4个研究专职 | 多角色动态 |
| 反馈闭环 | QA→任意上游 | Human Review | Middleware |
| 可观测性 | Trace + Events | 相同模式 | Langfuse |
| 记忆系统 | 文件JSON (原创设计) | 无 | FileMemoryStorage |
| Schema | Pydantic V2 | TypedDict | Pydantic |
| Skill | SKILL.md + Loader | 无 | Skill 系统 |
