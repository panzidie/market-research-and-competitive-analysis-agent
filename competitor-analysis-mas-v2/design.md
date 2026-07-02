# 智能竞品分析多Agent系统

> 最后更新: 2026-07-01 | 设计文档与实际代码保持同步

## 一、系统总体架构

```
┌──────────────────────────────────────────────────────────────────┐
│                     竞品分析协同环境                               │
│                                                                   │
│   ┌────────────────────────────────────────────────┐             │
│   │  ConversationalAgent (对话路由 + 安全检测)      │             │
│   │  ┌─ Prompt Injection 检测 ── 意图分类 ── 路由  │             │
│   │  │  通用对话 → ReAct (web_search + rag_search) │             │
│   │  │  竞品分析 → LangGraph 全管道                 │             │
│   │  └─ LongTermMemory (SQLite + ChromaDB) ───────┘              │
│   └────────────────────────────────────────────────┘             │
│                              │                                     │
│                              ▼                                     │
│   ┌──────────────────────────────────────────────────┐            │
│   │  LangGraph StateGraph DAG 编排                     │            │
│   │                                                  │            │
│   │   ┌──────────────┐    ┌──────────────┐          │            │
│   │   │  竞品发现     │ →  │  数据采集     │          │            │
│   │   │  Agent       │    │  Agent       │          │            │
│   │   │ (搜索+筛选)  │    │ (ReAct决策)  │          │            │
│   │   └──────┬───────┘    └──────┬───────┘          │            │
│   │          │                   │ 发现N个竞品        │            │
│   │          ▼                   ▼                   │            │
│   │   ┌────────────────────────────────────┐         │            │
│   │   │      parallel_analysis 节点        │         │            │
│   │   │  (asyncio.gather 内部并行)          │         │            │
│   │   └────────────────────────────────────┘         │            │
│   │         │              │              │          │            │
│   │         ▼              ▼              ▼          │            │
│   │  ┌─────────┐  ┌─────────┐  ┌─────────┐         │            │
│   │  │产品分析  │  │定价分析  │  │市场分析  │         │            │
│   │  │Agent    │  │Agent    │  │Agent    │         │            │
│   │  └────┬────┘  └────┬────┘  └────┬────┘         │            │
│   │       └────────────┼────────────┘               │            │
│   │                    ▼                             │            │
│   │           ┌──────────────┐                       │            │
│   │           │  策略建议     │                       │            │
│   │           │  Agent       │                       │            │
│   │           │ (综合+建议)  │                       │            │
│   │           └──────────────┘                       │            │
│   └──────────────────────────────────────────────────┘            │
│                                                                   │
│   搜索后端（三段降级链）          LLM 后端（三后端支持）            │
│   Tavily → UAPI → 百度AI搜索    DeepSeek → 千帆 → Ollama          │
│                                                                   │
│   长期记忆（跨会话持久化）        安全机制                          │
│   SQLite (精确检索)              Prompt Injection 检测             │
│   ChromaDB (语义搜索)            权限白名单 / 输入清洗              │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

**协作模式**：混合（串行采集 → 并行分析 → 串行汇总）

**核心理念**：
- **两段式采集**：先发现竞品列表，再逐竞品深度采集，避免盲目搜索
- **三维并行分析**：产品/定价/市场三个维度独立，结果JSON格式传递给策略Agent
- **竞品矩阵表**：产品分析Agent输出功能对比矩阵（✅/🔶/❌）
- **策略Agent看到全貌**：三份分析报告汇聚后一次性输入，保证策略建议的系统性
- **LangGraph StateGraph**：声明式 DAG 定义，天然支持串行 + 并行 + 状态共享
- **三层防护**：安全检测 → 意图分类 → 路由执行，拒绝注入攻击

## 二、Agent角色定义

### 1. 竞品发现Agent（DiscoveryAgent）
- **职责**：根据用户产品描述，搜索并筛选出3~8个核心竞品
- **LLM调用**：2~3次（理解需求1次 + 关键词生成1次 + 结果筛选1次）
- **外部工具**：SearchClient（Tavily → UAPI → 百度AI搜索，自动多后端降级）
- **输入**：用户产品描述（string）
- **输出**：CompetitorList（竞品名称+简介列表）
- **降级策略**：规则引擎关键词生成 + 通过搜索文本提取产品名称

### 2. 数据采集Agent（CollectionAgent）
- **职责**：对每个竞品，采集产品功能、定价、用户评价、市场份额等信息
- **LLM调用**：每竞品1个 ReAct 循环（含N次工具调用 + 1次汇总）
- **外部工具**：ReAct 自主（web_search + rag_search），web_search 内部走 SearchClient
- **输入**：CompetitorList + 用户产品描述
- **输出**：dict[str, CompetitorData]（每竞品一份数据）
- **降级策略**：ReAct 失败 → 硬编码4条搜索query → LLM汇总 → 规则引擎

### 3. 产品分析Agent（ProductAgent）
- **职责**：逐竞品对比功能矩阵，标注优势/劣势/差异点
- **LLM调用**：1次
- **外部工具**：无
- **输入**：全部竞品数据
- **输出**：ProductAnalysis（含功能对比矩阵）
- **降级策略**：基于关键词匹配生成简单对比

### 4. 定价分析Agent（PricingAgent）
- **职责**：对比各竞品定价策略、促销模式、性价比
- **LLM调用**：1次
- **外部工具**：无
- **输入**：全部竞品数据
- **输出**：PricingAnalysis（含定价对比表）
- **降级策略**：提取价格数字进行简单排序

### 5. 市场分析Agent（MarketAgent）
- **职责**：分析市场份额、增长趋势、用户口碑、渠道策略
- **LLM调用**：1次
- **外部工具**：无
- **输入**：全部竞品数据
- **输出**：MarketAnalysis
- **降级策略**：基于采集数据中的关键词统计

### 6. 策略建议Agent（StrategyAgent）
- **职责**：综合三维分析，输出差异化定位建议和行动方案
- **LLM调用**：1次
- **外部工具**：无
- **输入**：ProductAnalysis + PricingAnalysis + MarketAnalysis
- **输出**：StrategyReport
- **降级策略**：基于SWOT模板生成简单建议

## 三、数据流与JSON格式

### 3.1 竞品发现结果（Phase 1）

```json
{
    "product_name": "飞书",
    "product_category": "企业协同办公平台",
    "competitors": [
        {
            "name": "钉钉",
            "brief": "阿里巴巴旗下企业协同平台，市占率领先",
            "relevance": "HIGH"
        },
        {
            "name": "企业微信",
            "brief": "腾讯旗下企业通讯与协同平台",
            "relevance": "HIGH"
        }
    ],
    "search_keywords_used": ["飞书竞品", "企业协同办公平台对比"]
}
```

### 3.2 数据采集结果（Phase 2）

```json
{
    "钉钉": {
        "name": "钉钉",
        "product_features": "即时通讯、审批流程、考勤打卡、项目管理...",
        "pricing_info": "免费版+专业版9800元/年+专属版...",
        "market_share": "超过6亿用户，1000万+企业组织",
        "user_reviews": "流程审批功能强大，但界面较复杂...",
        "strengths": "生态完善、用户基数大、阿里背书",
        "weaknesses": "体验偏重、学习成本高",
        "channels": "直销+渠道代理+阿里云生态",
        "search_sources": ["搜索结果1...", "搜索结果2..."]
    }
}
```

### 3.3 产品分析结果（Phase 3）

```json
{
    "feature_matrix": {
        "features": ["即时通讯", "视频会议", "文档协作", "审批流程", "项目管理"],
        "matrix": {
            "飞书":  ["✅", "✅", "✅", "🔶", "✅"],
            "钉钉":  ["✅", "✅", "🔶", "✅", "✅"],
            "企业微信": ["✅", "✅", "🔶", "🔶", "❌"]
        }
    },
    "competitive_advantages": [
        {"competitor": "钉钉", "our_advantage": "文档协作体验远超", "their_advantage": "审批流程更成熟"}
    ],
    "differentiation_points": ["AI助手深度集成", "跨国协作能力"],
    "summary": "飞书在协作体验上领先，钉钉在流程管控上更强..."
}
```

### 3.4 定价分析结果（Phase 3）

```json
{
    "pricing_comparison": [
        {
            "competitor": "飞书",
            "free_tier": "基础功能免费",
            "paid_tier": "商业版50元/人/月",
            "pricing_model": "按人头订阅"
        }
    ],
    "pricing_strategy_analysis": "整体市场从免费增值模式向订阅制转变...",
    "value_ranking": ["飞书", "钉钉", "企业微信"],
    "summary": "飞书定价中等偏上，但功能覆盖面广..."
}
```

### 3.5 市场分析结果（Phase 3）

```json
{
    "market_share_data": [
        {"competitor": "钉钉", "share_estimate": "40%", "trend": "稳定"},
        {"competitor": "企业微信", "share_estimate": "30%", "trend": "上升"}
    ],
    "growth_trends": "整体市场年增长率约25%...",
    "user_reputation": {
        "钉钉": {"score": "7.5/10", "keywords": ["流程强", "界面重"]},
        "飞书": {"score": "8.2/10", "keywords": ["体验好", "功能新"]}
    },
    "channel_analysis": "直销为主，渠道代理为辅...",
    "summary": "钉钉市占率领先但增速放缓，飞书增速最快..."
}
```

### 3.6 策略建议报告（Phase 4）

```json
{
    "overall_positioning": "飞书应定位为'体验优先的智能协同平台'...",
    "differentiation_strategy": {
        "core_differentiator": "AI原生协同体验",
        "supporting_points": ["智能文档", "多维表格", "AI助手"]
    },
    "action_plan": [
        {
            "priority": "P0",
            "action": "强化AI助手差异化，打造'AI原生办公'心智",
            "timeline": "Q1-Q2",
            "expected_impact": "建立技术领先认知"
        }
    ],
    "risk_assessment": "钉钉可能跟进AI功能，需保持迭代速度...",
    "summary": "基于三维分析，建议飞书走'AI原生+体验优先'差异化路线..."
}
```

## 四、各Agent核心提示词推导

### 4.1 竞品发现Agent提示词推导

**推导思路**：竞品发现是整个流程的起点，需要"两步走"策略——先生成搜索关键词，再从搜索结果中筛选竞品。一次性让LLM完成"生成关键词+搜索+筛选"容易信息过载。

**推导过程**：

1. **第一步：生成搜索关键词**
   - 输入：用户产品描述
   - 核心指令：根据产品描述，生成3-5组竞品搜索关键词
   - 关键约束：关键词要覆盖不同维度（同类产品、替代方案、上下游产品）
   - 输出格式：关键词列表JSON

2. **第二步：筛选核心竞品**
   - 输入：搜索结果汇总
   - 核心指令：从搜索结果中识别3~8个核心竞品
   - 关键约束：去重、评估相关性、排除自身
   - 输出格式：竞品名称+简介+相关性等级

**系统提示词核心要素**：
```
角色：竞品发现专家
原则：关键词多样化 / 结果去重 / 相关性评估 / 排除自身
输出：严格JSON
```

### 4.2 数据采集Agent提示词推导

**推导思路**：数据采集需要"1+N"策略——先生成采集维度框架，再逐竞品搜索汇总。每个竞品需要覆盖功能/定价/市场/口碑/渠道五个维度。

**推导过程**：

1. **第一步：生成采集维度**
   - 输入：用户产品描述 + 竞品列表
   - 核心指令：定义每个竞品需要采集的具体信息维度
   - 输出：采集维度清单

2. **第二步：逐竞品搜索+汇总**
   - 对每个竞品：生成搜索查询 → 调用搜索 → LLM汇总提取
   - 输出：结构化的竞品数据

**系统提示词核心要素**：
```
角色：竞品数据采集专家
采集维度：产品功能 / 定价体系 / 市场份额 / 用户评价 / 渠道策略
原则：多源交叉验证 / 数据可溯源 / 区分事实与观点
输出：每竞品一份结构化数据
```

### 4.3 产品分析Agent提示词推导

**推导思路**：产品分析的核心产出是"功能对比矩阵"——这是一个二维表格（竞品×功能），每个交叉点标注✅/❌/🔶。LLM需要从非结构化的采集数据中提炼出可比较的功能维度。

**推导过程**：

1. **功能维度提炼**：从所有竞品数据中提取共同和差异化功能点
2. **矩阵填充**：逐功能逐竞品标注支持程度
3. **优劣势标注**：识别我方优势和对方优势
4. **差异点提炼**：找出独特的、不可替代的差异

**系统提示词核心要素**：
```
角色：产品竞品分析专家
核心产出：功能对比矩阵（✅完整支持 / 🔶部分支持 / ❌不支持）
分析维度：功能覆盖度 / 体验深度 / 创新点 / 成熟度
原则：客观对比 / 突出差异 / 矩阵可读
输出：feature_matrix + competitive_advantages + differentiation_points
```

### 4.4 定价分析Agent提示词推导

**推导思路**：定价分析需要"横向对比+纵向解读"——横向比价格数字，纵向解读定价策略背后的商业逻辑（免费增值？按人头？按功能模块？）。

**推导过程**：

1. **价格提取**：从采集数据中提取各竞品的价格信息
2. **策略分类**：识别定价模型（免费增值/纯订阅/按量付费/混合）
3. **性价比评估**：功能覆盖 vs 价格的性价比排序
4. **趋势判断**：市场整体定价趋势

**系统提示词核心要素**：
```
角色：定价策略分析专家
分析维度：定价模型 / 价格梯度 / 促销模式 / 性价比 / 定价趋势
原则：数字说话 / 策略解读 / 趋势判断
输出：pricing_comparison + pricing_strategy_analysis + value_ranking
```

### 4.5 市场分析Agent提示词推导

**推导思路**：市场分析需要"定量+定性"结合——定量看市场份额和增长数据，定性看用户口碑和渠道策略。由于公开数据可能不完整，需要明确标注数据来源和置信度。

**推导过程**：

1. **份额估算**：从搜索结果中提取市场份额信息
2. **增长趋势**：分析各竞品的增长态势
3. **口碑分析**：提取用户评价关键词和评分
4. **渠道解读**：分析销售渠道和合作伙伴

**系统提示词核心要素**：
```
角色：市场研究分析专家
分析维度：市场份额 / 增长趋势 / 用户口碑 / 渠道策略 / 竞争格局
原则：数据溯源 / 置信度标注 / 趋势重于快照
输出：market_share_data + growth_trends + user_reputation + channel_analysis
```

### 4.6 策略建议Agent提示词推导

**推导思路**：策略建议是汇聚环节，需要"融会贯通"——不是简单拼接三份分析，而是从三维数据中提炼出统一的战略叙事。核心产出是差异化定位+行动方案。

**推导过程**：

1. **三维交叉**：产品优势+定价空间+市场机会 → 差异化定位
2. **优先级排序**：按影响力和可行性排列行动方案
3. **风险评估**：基于竞品动态预判风险
4. **行动方案**：具体到时间线和预期效果

**系统提示词核心要素**：
```
角色：竞争战略顾问
原则：三维融合 / 差异化优先 / 行动导向 / 风险预判
报告结构：定位→差异化→行动计划→风险评估
输出：overall_positioning + differentiation_strategy + action_plan + risk_assessment
```

## 五、技术实现方案

### 技术栈
- **语言**：Python 3.10+
- **Agent框架**：基于原生Python + asyncio实现（零依赖，便于教学理解）
- **编排框架**：LangGraph StateGraph（声明式 DAG，天然状态共享 + 并行节点）
- **LLM调用**：
  - `llm_client.py` — 竞品分析 Agent 的 LLM 调用封装（DeepSeek/千帆/Ollama 三后端）
  - `react_agent.py` — ReAct 自主决策引擎（基于 LangGraph's create_react_agent + LangChain ChatOpenAI）
  - 默认主后端：DeepSeek API（deepseek-chat）
  - 降级链（Provider 轴）：DeepSeek → Ollama（内置于 ReactAgent._build_model）
  - 降级链（Logic 轴）：LLM 结果 → 规则引擎 → 占位数据（内置于各 Agent.run）
- **搜索后端**：
  - `search_client.py` — 统一搜索客户端，自动多后端降级
  - SearchClient.search() 内部降级链：Tavily → UAPI → 百度AI搜索
  - 工具层 (`tools.py` 的 `web_search`): 一调到底，不明确感知后端
  - `batch_search()` — 批量搜索带间隔防限流
  - `extract_text()` / `extract_links()` — 统一结果提取，兼容所有后端格式
- **ReAct Agent**（LangGraph + LangChain）：
  - LangGraph's `create_react_agent` 预制件，负责"思考-行动-观察"循环
  - 内部 model = ChatOpenAI(DeepSeek).with_fallbacks(ChatOpenAI(Ollama))
  - 挂载 _ThoughtPrinter 回调实时打印推理过程
  - 工具列表: `web_search` + `rag_search`
  - 支持 `task_message` (单次任务) 和 `messages` (多轮对话上下文)
- **长期记忆**：`LongTermMemory` 三层存储（deque 滑动窗口 + SQLite + ChromaDB）
- **安全机制**：`security.py` 提供 Prompt Injection 检测 + 权限白名单 + 输入清洗
- **并行执行**：asyncio.gather（竞品间并行采集 + 三维分析并行阶段）
- **数据格式**：JSON（Agent间数据传递）+ Pydantic/dataclass（内部类型安全）

### 项目结构（实际）
```
competitor-analysis-mas/
├── design.md                    # 本设计文档
├── main.py                      # 主入口（支持 --chat 交互模式 / 单次分析）
├── config.py                    # 配置（DeepSeek/千帆/Ollama + Tavily/UAPI/百度）
├── .gitignore                   # 排除 .env, __pycache__, output/, data/
├── requirements.txt             # 依赖清单
│
├── core/
│   ├── __init__.py              # 导出 llm_call, parse_llm_json, ConversationMemory, LongTermMemory
│   ├── llm_client.py            # LLM调用封装（DeepSeek + 千帆 + Ollama 三后端）
│   ├── search_client.py         # 统一搜索客户端（Tavily → UAPI → 百度自动降级）
│   ├── react_agent.py           # ReAct 自主决策 Agent 引擎（LangGraph create_react_agent）
│   ├── langgraph_orchestrator.py # LangGraph StateGraph 编排器（DAG: 串行→并行→串行）
│   ├── state.py                 # AnalysisState TypedDict（DAG 全局状态类型定义）
│   ├── tools.py                 # ReAct Agent 工具定义（web_search + rag_search）
│   ├── security.py              # Prompt Injection 检测 + 权限白名单 + 输入清洗
│   ├── memory.py                # 对话短期记忆（deque 滑动窗口）
│   ├── long_term_memory.py      # 长期记忆（SQLite 精确检索 + ChromaDB 语义搜索）
│   └── prompt_loader.py         # 提示词模板加载器
│
├── agents/
│   ├── __init__.py
│   ├── base_agent.py            # Agent基类（LLM调用 + 日志 + JSON解析）
│   ├── conversational_agent.py  # 对话式智能体（安全检测 → 意图分类 → 路由）
│   ├── discovery_agent.py       # 竞品发现Agent（搜索+筛选）
│   ├── collection_agent.py      # 数据采集Agent（ReAct 自主决策 + 传统模式降级）
│   ├── product_agent.py         # 产品分析Agent（功能对比矩阵）
│   ├── pricing_agent.py         # 定价分析Agent（价格策略对比）
│   ├── market_agent.py          # 市场分析Agent（份额/趋势/口碑）
│   └── strategy_agent.py        # 策略建议Agent（差异化定位 + 行动方案）
│
├── models/
│   ├── __init__.py
│   └── domain.py                # 领域模型（dataclass 定义全部数据传输对象）
│
├── prompts/                     # 提示词模板（.md格式，按##节分割）
│   ├── discovery_agent.md
│   ├── collection_agent.md
│   ├── product_agent.md
│   ├── pricing_agent.md
│   ├── market_agent.md
│   └── strategy_agent.md
│
├── skill/                       # 技能包
│   ├── __init__.py
│   └── rag_skill/
│       ├── __init__.py
│       └── rag_skill.py         # rag_search 工具（PDF知识库检索）
│
├── test/                        # 测试套件
│   ├── injection_test.py        # Prompt Injection 防护测试（10类×6入口=60项）
│   ├── test_long_term_memory.py # 长期记忆测试
│   ├── test_rag_qa.py           # RAG 知识库问答测试
│   ├── test_react_standalone.py # ReAct Agent 独立测试
│   └── test_uapi_search.py      # UAPI 搜索测试
│
├── data/                        # 运行时数据（gitignore）
│   ├── long_term_memory.db      # SQLite 长期记忆数据库
│   └── chroma_memory/           # ChromaDB 向量存储目录
│
├── output/                      # 分析报告输出（gitignore）
│   ├── {product}_analysis_report.html
│   ├── {product}_analysis_report.json
│   └── injection_test_report_*.txt/json
│
└── prompts/                     # Agent 提示词模板
    └── ... (6 个 .md 文件)
```

### 运行方式
```bash
# 交互式对话模式（推荐）
python3 main.py --chat

# 规则引擎模式（零依赖，无需 API Key）
python3 main.py --chat --rule

# 单次竞品分析
python3 main.py "飞书"

# 切换到本机 Ollama
python3 main.py --ollama "飞书"

# 指定竞品数量
python3 main.py --count 5 "飞书"

# 详细模式（输出中间结果）
python3 main.py --verbose "飞书"

# 帮助
python3 main.py help
```

## 六、Agent间数据传递规范

```
DiscoveryAgent ──(CompetitorList JSON)──→ [串行]
                                             │
CollectionAgent ──(dict[str, CompetitorData])──→ [并行]
                                                   ├── ProductAgent ──(ProductAnalysis)
                                                   ├── PricingAgent ──(PricingAnalysis)
                                                   └── MarketAgent ───(MarketAnalysis)
                                                                      │
                                                      [汇聚] ──────────┘
                                                          │
                                                          ▼
                                                    StrategyAgent
                                                          │
                                                          ▼
                                                  StrategyReport
```

**关键约束**：
- Phase 1 → Phase 2：竞品列表直接传递
- Phase 2 → Phase 3：采集数据对象直接传递（三路共享同一份数据，只读）
- Phase 3 并行三路：输入相同，输出独立
- Phase 3 → Phase 4：三份分析报告汇聚后一次性传给策略Agent

## 七、LLM调用统计

| Agent | 调用次数 | 调用策略 | 降级方案 |
|-------|---------|---------|---------|
| ConversationalAgent | 1次 | 意图分类（LLM → 规则引擎关键词） | 关键词匹配分类 |
| DiscoveryAgent | 2~3次 | 理解需求1次 + 关键词生成1次 + 结果筛选1次 | 规则引擎关键词生成+搜索文本提取 |
| CollectionAgent | ~1次/竞品（ReAct） | ReAct 自主循环（含N次工具调用+1次汇总） | 硬编码4条搜索 → LLM汇总 → 规则引擎 |
| ProductAgent | 1次 | 全量数据一次性分析 | 关键词匹配对比矩阵 |
| PricingAgent | 1次 | 全量数据一次性分析 | 价格数字提取排序 |
| MarketAgent | 1次 | 全量数据一次性分析 | 关键词频率统计 |
| StrategyAgent | 1次 | 三维分析一次性输入 | SWOT模板填充 |
| ReactAgent(对话) | 1个ReAct循环 | 多轮对话中的"思考-行动-观察"循环 | 规则引擎回复（_rule_reply） |
| **总计** | **~8+N次** | N=竞品数 | 每一层都有规则引擎兜底 |

> 注：与原始设计相比，实际加入了 ConversationalAgent 意图分类和长期记忆、安全检测等环节，但安全检测（正则匹配）和长期记忆（SQLite 写入）不消耗 LLM 调用。

## 八、设计要点与决策记录

### 8.1 为什么采用两段式采集而非一步到位？
- 第一步只发现竞品列表，确定分析范围，避免盲目搜索
- 第二步针对已确定的竞品逐个深度采集，搜索关键词更精准
- 分段后每步的LLM调用职责更单一，结果更可控

### 8.2 为什么三维分析并行而非串行？
- 产品/定价/市场三个维度互不依赖，可并行执行，总耗时≈单路
- 并行结果独立输出JSON，避免维度间耦合
- 策略Agent一次性看到全貌，不受串行顺序影响

### 8.3 为什么每个Agent都有规则引擎Fallback？
- 教学演示：即使没有LLM也能跑通完整流程
- 生产安全：LLM故障时系统不宕机
- 成本控制：开发测试阶段可零成本运行

### 8.4 竞品矩阵的符号设计
- ✅ 完整支持：功能完善，体验良好
- 🔶 部分支持：有此功能但不够成熟或体验一般
- ❌ 不支持：无此功能或仅规划中

### 8.5 为什么改用 LangGraph StateGraph 而非自编编排器？
- **声明式图定义**：add_node + add_edge = DAG，比手写编排更可读
- **并行 fan-in 安全**：LangGraph 的单节点不会被多条入边重复触发，解决了`三个分析Agent → 策略Agent`的三条边会触发策略Agent被调用三次的问题
- **状态共享**：TypedDict AnalysisState 在节点间自动传递，无需手动管理结果对象
- **内置编译优化**：graph.compile() 自动检查图的连通性，避免悬空节点

### 8.6 为什么并行分析在单节点内用 asyncio.gather，而非三条边 fan-in 到 Strategy？
```
错误方案 (三条边 fan-in):
  discovery → collection → product_analysis ─┐
                           → pricing_analysis ─┤→ strategy (被执行3次!)
                           → market_analysis  ─┘

正确方案 (单节点内并行):
  discovery → collection → parallel_analysis → strategy
                              ├─ product_analysis (asyncio.gather)
                              ├─ pricing_analysis
                              └─ market_analysis
```
LangGraph 的 add_edge 会导致目标节点被每条入边各执行一次。因此将三个分析 Agent 放在单个 `parallel_analysis` 节点内部，用 asyncio.gather 实现真正的并行，策略节点只被调用一次。

### 8.7 为什么引入 RAG + 长期记忆？
- **RAG 知识库**（`rag_search` Skill）：将行业研究报告 PDF 作为可检索的知识源，使 LLM 回答有事实依据，减少幻觉
- **长期记忆 LT M**：三层架构（deque + SQLite + ChromaDB），跨会话恢复对话历史，支持语义搜索和关键词搜索历史分析报告
- **设计原则**：LongTermMemory 包装 ConversationMemory，保持 API 完全兼容，降级友好

### 8.8 安全机制的设计策略（三层防护）
Prompt Injection 防护采用"3+6×10"架构：
- **3 个防御层面**：
  1. `security.py` 正则检测（输入层，命中即拒）
  2. `conversational_agent.chat()` 前置拦截（调用层，检测结果直接返回）
  3. `CONVERSATION_SYSTEM_PROMPT` 安全要求（LLM 层，即使绕过前两层也有行为约束）
- **6 个测试入口点**：意图分类器、长期记忆、工具调用边界、系统提示词、输入清洗、DAG状态污染
- **10 类攻击场景**：指令覆盖、系统泄露、角色扮演、分隔符绕过、编码绕过、RAG污染模拟、工具越权、无限循环、敏感信息、虚假状态断言

当前检测通过率：70 项测试中 69 项通过（98.6%），2 项注意（非适用场景），0 项失败。

### 8.9 搜索后端的多级降级策略
```
web_search (ReAct 工具)
  ↓
tools.py: _call_with_retry() 重试封装
  ↓
search_client.search(query)
  ├─ 主后端 (tavily): 优先调用
  ├─ 第一降级 (uapi): 主后端失败时自动切换
  └─ 第二降级 (baidu): UAPI 也失败时最后尝试
```
每个后端有独立的 API Key 和配置，互不依赖。只有全部三个后端都失败时，搜索才报错。

### 8.10 LLM 后端的 Provider 和 Logic 双轴降级
```
Provider 轴（基础设施层）:
  主: ChatOpenAI(DeepSeek)
  备: ChatOpenAI(Ollama)
  轴行为: model.with_fallbacks([ollama]) — LangChain 原生 fallback 机制

Logic 轴（业务逻辑层）:
  主: LLM 模型返回 JSON / ReAct 最终回复
  备: 规则引擎关键词匹配
  轴行为: Agent.ask_llm_json() → None → Agent._rule_xxx()
```
两轴独立，互不影响。Provider 降级了但 Logic 仍在 LLM 路径上；Provider 正常但 Logic 降级了说明 LLM 输出不符合预期格式。
