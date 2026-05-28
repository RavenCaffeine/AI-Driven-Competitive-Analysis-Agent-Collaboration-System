# 安装与部署指南 (Setup Guide)

本文档面向第一次接触该项目的开发者，从零开始一步步搭建运行环境。

---

## 前置要求

| 依赖 | 最低版本 | 说明 |
|------|---------|------|
| Python | 3.10+ | 推荐 3.11 或 3.12 |
| uv | 0.7+ | 推荐的包管理器（[安装指南](https://docs.astral.sh/uv/getting-started/installation/)） |
| Git | 2.30+ | 版本管理 |

你还需要至少一个 LLM API Key（见下方"配置 LLM"章节）。

---

## Step 1: 安装 uv

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 或使用 pip（任意平台）
pip install uv
```

## Step 2: 克隆项目

```bash
git clone <your-repo-url>
cd Competitive-Analysis-Agent
```

## Step 3: 安装依赖

```bash
# 一键创建 .venv 并安装所有依赖（包含 dev 依赖）
uv sync --extra dev

# 如果需要 Claude + Gemini 支持
uv sync --extra all --extra dev
```

> **备用方式（pip）**：如果不想使用 uv，仍可以用传统方式：
> ```bash
> python -m venv .venv
> source .venv/bin/activate   # Linux/macOS
> pip install -e ".[dev]"
> ```

## Step 4: 配置环境变量

```bash
# 复制模板
cp .env.example .env
```

用编辑器打开 `.env`，填入你的 API Key：

### 配置 LLM（必须选一个）

**方案 A：DeepSeek（推荐，性价比最高）**

```env
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-chat
LLM_API_KEY=sk-xxxxxxxxxxxxxxxx
```

获取 Key：访问 https://platform.deepseek.com → 注册 → API Keys → 创建

**方案 B：OpenAI**

```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-xxxxxxxxxxxxxxxx
```

**方案 C：Anthropic Claude**

```env
LLM_PROVIDER=claude
LLM_MODEL=claude-sonnet-4-20250514
LLM_API_KEY=sk-ant-xxxxxxxxxxxxxxxx
```

**方案 D：Google Gemini**

```env
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.0-flash
LLM_API_KEY=AIzaSyxxxxxxxxxxxxxxxx
```

### 配置搜索工具（推荐）

```env
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxx
```

获取 Key：访问 https://tavily.com → 注册 → Dashboard → API Key（免费额度足够测试）

> **没有 Tavily Key 也能运行**，但 Collector Agent 将无法实际搜索，只能用 fallback 数据。

### 其他配置

```env
MAX_QA_RETRIES=2          # QA 反馈循环最大次数
OUTPUT_DIR=./outputs       # 报告和 trace 输出目录
LOG_LEVEL=INFO            # 日志级别: DEBUG / INFO / WARNING
MEMORY_ENABLED=true       # 是否启用长程记忆
```

## Step 5: 验证安装

```bash
# 检查 uv 管理的 Python 版本
uv run python --version  # 应为 3.10+

# 检查核心依赖
uv run python -c "import langgraph; print('LangGraph OK')"
uv run python -c "import openai; print('OpenAI SDK OK')"
uv run python -c "import pydantic; print('Pydantic OK')"

# 打印 DAG 工作流图
uv run python main.py visualize
```

如果 `visualize` 命令输出 Mermaid 图定义，说明安装成功。

## Step 6: 运行第一次分析

```bash
# 基础示例
uv run python main.py analyze "Compare Notion vs Obsidian vs Logseq" \
    --competitors Notion Obsidian Logseq

# 查看生成的报告
cat outputs/report.md

# 查看 trace（可观测性）
ls outputs/runs/
# 会看到类似 20250527_143022_a1b2c3d4/ 的目录
cat outputs/runs/*/trace.json | python -m json.tool | head -50
```

## Step 7: 运行评估（可选）

```bash
# 运行单个场景
uv run python main.py eval --scenario saas_pm_tools

# 运行所有场景
uv run python main.py eval --scenario all

# 查看评估结果
cat outputs/eval/saas_pm_tools_eval.json
```

## Step 8: 运行测试（开发者）

```bash
# 运行全部测试（42 个）
uv run pytest tests/ -v

# 运行单个测试文件
uv run pytest tests/test_schemas.py -v

# 运行带覆盖率
uv run pytest tests/ -v --tb=short
```

---

## 常见问题

### Q: 报错 `ModuleNotFoundError: No module named 'langgraph'`

```bash
# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install langgraph>=0.2.0 langchain-core>=0.3.0
```

### Q: DeepSeek API 返回 401

检查 `.env` 中的 `LLM_API_KEY` 是否正确，且没有多余空格。

### Q: 想同时测试多个 LLM

在 `.env` 中切换 `LLM_PROVIDER` 即可，无需修改代码。也可以通过代码动态注册：

```python
from competitive_analysis.llm.factory import LLMFactory
llm = LLMFactory.create(provider="deepseek", api_key="sk-xxx")
```

### Q: 如何查看 Agent 的决策过程？

每次运行会在 `outputs/runs/<run_id>/` 下生成：
- `trace.json` — 完整 trace（LLM 调用、工具调用、决策路由）
- `events.jsonl` — 时间线事件流（一行一个事件）
- `report.md` — 最终报告

### Q: 如何添加新的 LLM 供应商？

1. 创建 `competitive_analysis/llm/my_provider.py`
2. 继承 `BaseLLM`，实现 `generate()` 和 `stream_generate()`
3. 在 `factory.py` 的 `_lazy_load()` 中添加注册逻辑

---

## 目录结构速查

```
outputs/
├── runs/
│   └── 20250527_143022_a1b2c3d4/
│       ├── trace.json          # 完整运行 trace
│       ├── events.jsonl        # 事件时间线
│       └── report.md           # 最终报告
├── eval/
│   └── saas_pm_tools_eval.json # 评估结果
└── memory/
    └── competitive_memory.json # 长程记忆
```
