# AI 驱动的竞品分析 Agent 协作系统

> **Competitive Analysis Multi-Agent System** — 基于 LangGraph 的多 Agent 协作框架，自动完成从信息采集到结构化报告输出的全链路竞品分析。

## 核心亮点

- **4 个专职 Agent**：采集 / 分析 / 撰写 / 质检，职责边界清晰
- **DAG 任务流转**：基于 LangGraph StateGraph 的有向无环图编排，支持可视化
- **反馈闭环**：质检 Agent 可将不足打回给任意上游 Agent，形成真实迭代
- **结构化 Schema**：功能树 / 定价模型 / 用户画像 / SWOT 等标准化输出
- **信息溯源**：每条分析结论标注数据来源 URL，支持一键溯源
- **全链路可观测**：每个 Agent 的 Prompt、输入输出、决策过程、Token 消耗均有 Trace 记录
- **LLM 可切换**：默认 DeepSeek，一行配置切换 OpenAI / Claude / Gemini
- **长程记忆**：借鉴 deerflow 设计，跨 session 持久化竞品知识
- **评估框架**：内置 metrics 和 scenarios，量化回答"你如何评估你的 Agent"

## 快速开始

```bash
# 1. 克隆项目
cd Competitive-Analysis-Agent

# 2. 安装依赖（使用 uv）
uv sync --extra dev          # 自动创建 .venv 并安装所有依赖
# 如需额外 LLM 支持：
# uv sync --extra all        # 安装 Claude + Gemini SDK

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 API Key

# 4. 运行分析
uv run python main.py analyze "Compare Notion vs Obsidian vs Logseq" \
    --competitors Notion Obsidian Logseq

# 5. 查看工作流图
uv run python main.py visualize

# 6. 运行测试
uv run pytest tests/ -v

# 7. 运行评估
uv run python main.py eval --scenario saas_pm_tools
```

## 项目结构

```
Competitive-Analysis-Agent/
├── main.py                          # 入口文件
├── pyproject.toml                   # 项目元数据与依赖 (uv / pip 通用)
├── uv.lock                          # uv 锁定文件 (精确可复现)
├── requirements.txt                 # pip 依赖 (备用)
├── .env.example                     # 环境变量模板
├── competitive_analysis/            # 核心代码包
│   ├── agents/                      # 4 个专职 Agent
│   │   ├── collector.py             # 信息采集 Agent
│   │   ├── analyst.py               # 分析师 Agent
│   │   ├── writer.py                # 报告撰写 Agent
│   │   └── qa_agent.py              # 质检 Agent (反馈闭环核心)
│   ├── workflow/                     # LangGraph DAG 编排
│   │   ├── graph.py                 # DAG 构建与执行
│   │   ├── nodes.py                 # 节点函数与路由逻辑
│   │   └── state.py                 # 共享状态定义
│   ├── llm/                         # LLM 抽象层 (可切换供应商)
│   │   ├── base.py                  # 抽象基类
│   │   ├── factory.py               # 工厂模式，运行时切换
│   │   ├── deepseek_llm.py          # DeepSeek (默认)
│   │   ├── openai_llm.py            # OpenAI
│   │   ├── claude_llm.py            # Anthropic Claude
│   │   └── gemini_llm.py            # Google Gemini
│   ├── schemas/                     # 竞品知识结构化 Schema
│   │   └── competitive.py           # Pydantic Schema 定义
│   ├── tools/                       # 外部工具集成
│   │   ├── tavily_search.py         # Tavily 网页搜索
│   │   └── web_scraper.py           # 网页内容抓取
│   ├── memory/                      # 长程记忆 (借鉴 deerflow)
│   │   └── storage.py               # 文件持久化 + 缓存
│   ├── skills/                      # 可扩展技能系统
│   │   ├── types.py                 # Skill 类型定义
│   │   ├── loader.py                # Skill 发现与加载
│   │   └── builtin/                 # 内置技能
│   ├── evaluation/                  # 评估框架
│   │   ├── metrics.py               # 评估指标计算
│   │   ├── scenarios.py             # 预定义测试场景
│   │   └── runner.py                # 评估执行器
│   ├── prompts/                     # Prompt 模板 (.md)
│   │   ├── loader.py                # 模板加载器
│   │   └── *.md                     # 各 Agent 的 Prompt
│   ├── utils/                       # 工具模块
│   │   ├── config.py                # 配置管理
│   │   ├── logger.py                # 日志系统
│   │   └── tracing.py               # 全链路 Trace
│   └── cli/                         # 命令行接口
│       └── main.py                  # CLI 命令定义
├── tests/                           # 测试
├── docs/                            # 文档
│   ├── architecture.md              # 架构详解
│   ├── SETUP.md                     # 安装指南
│   └── internship-guide.md          # 实习面试指南
├── examples/                        # 示例输出
└── outputs/                         # 运行输出目录
```

## 切换 LLM 供应商

编辑 `.env` 文件，修改 `LLM_PROVIDER` 和 `LLM_API_KEY`：

| Provider | LLM_PROVIDER | 默认 Model | 依赖 |
|----------|-------------|-----------|------|
| DeepSeek | `deepseek` | `deepseek-chat` | `openai` |
| OpenAI | `openai` | `gpt-4o-mini` | `openai` |
| Claude | `claude` | `claude-sonnet-4-20250514` | `anthropic` |
| Gemini | `gemini` | `gemini-2.0-flash` | `google-generativeai` |

## 详细文档

- [架构设计与可扩展性](docs/architecture.md)
- [安装与部署指南](docs/SETUP.md)
- [实习面试准备指南](docs/internship-guide.md)

## 技术栈

- **包管理**: uv (快速、可复现的 Python 包管理器)
- **编排**: LangGraph (StateGraph + Conditional Edges)
- **LLM**: DeepSeek V4 Flash / OpenAI / Claude / Gemini
- **Schema**: Pydantic V2
- **搜索**: Tavily API
- **记忆**: 文件持久化 JSON (deerflow 模式)
- **可观测**: 结构化 Trace + JSONL Events
