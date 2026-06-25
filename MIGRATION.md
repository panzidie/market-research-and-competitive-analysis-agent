# 竞品分析智能体 — 脱离 Claude Code 部署指南

## 核心概念

本项目有两套"皮肤"可以在不同的环境中运行：

| 运行环境 | 使用方式 | .claude/ 作用 |
|---------|---------|--------------|
| Claude Code 内 | `/research 竞品名` 或 `python agent.py` | 提供子代理/命令/技能，增强交互体验 |
| 无 Claude Code 的服务器 | `python agent.py "竞品名"` | 不需要，所有逻辑已在 Python 中 |

## .claude/ 文件与 Python 代码的映射关系

| .claude/ 文件 | Python 等价实现 | 状态 |
|--------------|----------------|------|
| `.claude/agents/researcher.md` | `config/prompts.py` → `RESEARCHER_PROMPT` | 已迁移 |
| `.claude/agents/analyst.md` | `config/prompts.py` → `ANALYST_PROMPT` | 已迁移 |
| `.claude/agents/writer.md` | `config/prompts.py` → `WRITER_PROMPT` | 已迁移 |
| `.claude/agents/fact_checker.md` | `config/prompts.py` → `FACT_CHECKER_PROMPT` | 已迁移 |
| `.claude/skills/data-extraction/` | `config/skills.py` → `DATA_EXTRACTION_TEMPLATE` | 已迁移 |
| `.claude/skills/competitor-matrix/` | `config/skills.py` → `COMPETITOR_MATRIX_TEMPLATE` | 已迁移 |
| `.claude/skills/swot-analysis/` | `config/skills.py` → `SWOT_ANALYSIS_TEMPLATE` | 已迁移 |
| `.claude/commands/research.md` | `agent.py` → LangGraph 图流程 | 已实现 |
| `.claude/commands/report.md` | `agent.py` → LangGraph 图流程 | 已实现 |
| `.claude/hooks/hooks.json` | `core/security.py` → `SecurityManager` | 已实现 |
| `.mcp.json` | `tools/*.py` → 直接 SDK 调用 | 已实现 |
| `CLAUDE.md` | `config/settings.yaml` + 代码注释 | 无需迁移 |

## 无 Claude Code 部署步骤

```bash
# 1. 复制项目（排除 .claude/ 目录也可）
cp -r 竞品分析智能体/ /opt/competitor-agent/

# 2. 配置环境变量
cd /opt/competitor-agent/
# 编辑 .env，填入真实的 API Key

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行
python agent.py "游戏类小程序"
```

## 迁移后仍保留在 .claude/ 中的文件

以下文件在 Claude Code 环境中使用，但 Python 代码已自包含等价逻辑：

- `.claude/agents/` — Claude Code 子代理定义
- `.claude/commands/` — 斜杠命令（`/research`, `/report`）
- `.claude/skills/` — 动态加载的技能
- `.claude/hooks/hooks.json` — 事件钩子
- `.mcp.json` — MCP 服务器配置
- `CLAUDE.md` / `CLAUDE.local.md` — Claude Code System Prompt

这些文件可以随项目一起分发，在不支持 Claude Code 的服务器上会被忽略。
