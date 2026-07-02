# 智能竞品分析多智能体系统 (Competitor Analysis MAS)

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.0+-green.svg)](https://github.com/langchain-ai/langgraph)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61dafb.svg)](https://react.dev/)
[![License](https://img.shields.io/badge/License-Apache%202.0-orange.svg)](LICENSE)

基于 **LangGraph 编排** 的多智能体竞品分析系统。输入一个产品名称，系统自动完成竞品发现、数据采集、三维并行分析（产品/定价/市场）和策略建议，输出 HTML + JSON 格式的专业分析报告。同时提供交互式对话助手，支持多轮对话、网络搜索和 RAG 知识库检索。

## 系统架构

```
用户输入
    │
    ▼
┌─────────────────────────────────────────┐
│  ConversationalAgent (对话路由 + 安全)    │
│  ┌─ Prompt Injection 检测                │
│  ├─ 意图分类 (竞品分析 / 通用对话)        │
│  └─ 长期记忆 (SQLite + ChromaDB)         │
└──────────────┬──────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│  LangGraph StateGraph DAG 编排            │
│                                          │
│  竞品发现 ──→ 数据采集 ──→ 并行分析 ──→ 策略建议 │
│                 (ReAct)     ├─ 产品分析          │
│                             ├─ 定价分析          │
│                             └─ 市场分析          │
│                                          │
│  搜索: Tavily → UAPI → 百度 (三级降级)   │
│  LLM:  DeepSeek / 千帆 / Ollama          │
└──────────────────────────────────────────┘
```

- **串行采集**：竞品发现 → 逐竞品数据采集（ReAct 自主决策），保证信息深度
- **并行分析**：产品 / 定价 / 市场三维度 `asyncio.gather` 并行，总耗时 ≈ 单路
- **串行汇总**：三维分析报告汇聚后一次性传递给策略 Agent，保证建议的系统性

## 核心特性

- **6 个专业 Agent**：竞品发现、数据采集、产品分析、定价分析、市场分析、策略建议
- **ReAct 自主决策**：数据采集 Agent 基于 LangGraph `create_react_agent` 进行「思考—行动—观察」循环
- **多级降级保障**：LLM 层（Provider + Logic 双轴降级）和搜索层（Tavily → UAPI → 百度）各自独立降级，每层都有规则引擎兜底
- **RAG 知识库**：将行业 PDF 报告向量化存储（ChromaDB），语义检索增强回答质量
- **长期记忆**：三层架构（deque 滑动窗口 + SQLite 精确检索 + ChromaDB 语义搜索），跨会话持久化对话历史
- **Prompt Injection 防护**：三层安全机制（正则检测 → 调用层拦截 → LLM 行为约束），覆盖 10 类攻击场景
- **Web 界面**：React 19 + TypeScript 前端 + FastAPI 后端 + WebSocket 实时通信
- **规则引擎模式**：零 API 依赖也可运行完整分析流程，适合教学演示和开发测试

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 20+（Web 前端）
- （可选）Ollama 用于本地 LLM 推理

### 安装

```bash
# 克隆仓库
git clone <repo-url>
cd competitor-analysis-mas-v2

# 安装 Python 依赖
cd competitor-analysis-mas-v2
pip install -r requirements.txt
```

### 配置

在项目根目录创建 `.env` 文件（至少配置一个 LLM 后端和一个搜索后端）：

```env
# LLM 后端（三选一）
LLM_PROVIDER=deepseek                    # deepseek | qianfan | ollama
DEEPSEEK_API_KEY=sk-your-key             # DeepSeek 推荐，性价比高
# QIANFAN_API_KEY=your-key               # 百度千帆
# OLLAMA_BASE_URL=http://localhost:11434  # 本地 Ollama

# 搜索后端
SEARCH_PROVIDER=tavily                   # tavily | uapi | baidu
TAVILY_API_KEY=tvly-your-key
# UAPI_API_KEY=your-key
# BAIDU_SEARCH_API_KEY=your-key
```

### 运行

```bash
# 交互式对话模式（推荐）
python main.py --chat

# 单次竞品分析（LLM 模式）
python main.py "飞书"

# 规则引擎模式（零依赖，无需 API Key）
python main.py --rule "飞书"

# 使用本地 Ollama
python main.py --ollama "飞书"

# 指定竞品数量
python main.py --count 5 "飞书"

# 详细输出模式
python main.py --verbose "飞书"

# 启动 Web 服务（前后端）
python -m backend.main               # API 服务 (默认 :8000)
cd web && npm install && npm run dev  # 前端开发服务器
```

### 交互式对话

在 `--chat` 模式下支持以下能力：

| 功能 | 示例 | 说明 |
|------|------|------|
| 竞品分析 | "帮我分析飞书的竞品" | 自动触发完整分析管道 |
| 通用对话 | "钉钉有哪些主要功能？" | 支持网络搜索 + RAG 检索 |
| 历史搜索 | `/search 飞书` | 语义搜索历史分析报告 |
| 清空记忆 | `/clear` | 清空当前会话上下文 |
| 退出 | `exit` / `quit` / `q` | 自动持久化记忆 |

## 项目结构

```
competitor-analysis-mas-v2/
├── main.py                         # 主入口（CLI + 聊天模式）
├── config.py                       # 全局配置（LLM/搜索/安全）
├── requirements.txt                # Python 依赖
├── design.md                       # 详细设计文档
│
├── core/                           # 核心引擎
│   ├── langgraph_orchestrator.py   # LangGraph StateGraph 编排器
│   ├── react_agent.py              # ReAct 自主决策引擎
│   ├── llm_client.py               # LLM 调用封装（三后端）
│   ├── search_client.py            # 搜索客户端（三级降级）
│   ├── tools.py                    # ReAct 工具定义
│   ├── state.py                    # DAG 全局状态类型
│   ├── security.py                 # Prompt Injection 防护
│   ├── memory.py                   # 短期对话记忆
│   └── long_term_memory.py         # 长期记忆（SQLite + ChromaDB）
│
├── agents/                         # Agent 实现
│   ├── conversational_agent.py     # 对话路由 + 安全检测
│   ├── discovery_agent.py          # 竞品发现
│   ├── collection_agent.py         # 数据采集（ReAct + 降级）
│   ├── product_agent.py            # 产品分析（功能矩阵）
│   ├── pricing_agent.py            # 定价分析
│   ├── market_agent.py             # 市场分析
│   └── strategy_agent.py           # 策略建议
│
├── models/                         # 领域数据模型
│   └── domain.py                   # Pydantic/dataclass 定义
│
├── prompts/                        # Agent 提示词模板 (.md)
│
├── skill/                          # 技能包
│   └── rag_skill/                  # RAG 知识库检索技能
│
├── test/                           # 测试套件
│   ├── injection_test.py           # 安全防护测试 (70 项)
│   ├── test_long_term_memory.py    # 长期记忆测试
│   └── test_rag_qa.py              # RAG 问答测试
│
├── backend/                        # FastAPI 后端
│   ├── main.py                     # API 入口 + WebSocket
│   ├── routers/                    # 路由（ws, chat, reports）
│   └── services/                   # 业务服务层
│
├── web/                            # React 前端
│   ├── src/                        # 组件源码
│   ├── package.json                # Vite + React 19 + TypeScript
│   └── vite.config.ts
│
└── RAG/                            # RAG 知识库管线
    ├── main.py                     # 索引构建 + 交互检索
    ├── chunkers/                   # 文本分割器
    ├── embedding/                  # 向量化模型
    └── vector_db/                  # ChromaDB 向量存储
```

## 数据流与 JSON 协议

六个 Agent 之间通过结构化 JSON 传递数据，关键数据格式如下：

**竞品发现 → 竞品列表**
```json
{
  "product_name": "飞书",
  "product_category": "企业协同办公平台",
  "competitors": [
    { "name": "钉钉", "brief": "阿里旗下企业协同平台", "relevance": "HIGH" }
  ],
  "search_keywords_used": ["飞书竞品", "企业协同办公平台对比"]
}
```

**产品分析 → 功能对比矩阵**
```json
{
  "feature_matrix": {
    "features": ["即时通讯", "视频会议", "文档协作", "审批流程"],
    "matrix": {
      "飞书":      ["✅", "✅", "✅", "🔶"],
      "钉钉":      ["✅", "✅", "🔶", "✅"],
      "企业微信":   ["✅", "✅", "🔶", "❌"]
    }
  },
  "competitive_advantages": [...],
  "differentiation_points": [...]
}
```

> 完整数据格式参见 [design.md](design.md)

## 输出报告

分析完成后自动在 `output/` 目录生成两份报告：

- `{产品名}_analysis_report.html` — 可视化 HTML 报告（含功能矩阵、定价对比、市场数据、策略建议）
- `{产品名}_analysis_report.json` — 结构化 JSON 数据

## 技术栈

| 层次 | 技术 |
|------|------|
| 编排引擎 | LangGraph StateGraph (DAG) |
| LLM 后端 | DeepSeek / 百度千帆 / Ollama |
| 搜索后端 | Tavily / UAPI / 百度 AI 搜索 |
| 向量数据库 | ChromaDB |
| 长期记忆 | SQLite + ChromaDB |
| Web 后端 | FastAPI + WebSocket + uvicorn |
| Web 前端 | React 19 + TypeScript + Vite |
| 嵌入模型 | BAAI/bge-small-zh-v1.5 |
| 安全防护 | 正则检测 + LLM 约束 + 权限白名单 |

## 许可证

[Apache License 2.0](LICENSE)
