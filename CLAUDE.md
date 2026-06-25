# 竞品分析智能体

## 项目概述
基于 LangGraph + Claude 构建的多角色协作竞品分析智能体。

## 核心工作流程
1. **研究员**：搜索竞品信息并抓取关键网页
2. **分析师**：解读数据、SWOT 分析、功能对比矩阵
3. **撰稿人**：生成格式化分析报告
4. **核查员**：交叉验证，防止 AI 幻觉

## 数据质量标准
- 所有分析结论必须有来源支撑（URL + 采集时间）
- 数值计算使用确定性代码（pandas），不依赖 LLM 算术
- 冲突数据必须展示多方证据，不做主观取舍
- 无来源的信息必须明确标注为”推断”或”待验证”

## 项目结构
- `.claude/agents/` — 角色定义（研究员、分析师、撰稿人、核查员）
- `.claude/commands/` — 快捷命令（`/research`、`/report`）
- `.claude/skills/` — 技能知识库（数据提取、对比矩阵、SWOT）
- `config/` — 企业级参数管理（YAML + Pydantic）
- `core/` — LangGraph 核心中枢（状态、LLM 网关、检索、追踪）
- `nodes/` — LangGraph 执行节点（research → extract → report）
- `tools/` — Tavily 搜索 + Firecrawl 网页抓取
- `utils/` — 确定性计算层（pandas 指标计算）
- `data/` — 数据持久化（raw/processed/reports/vector_store/evaluation）
- `tests/` — pytest 自动化测试

## 工具调用规范
- 所有网络请求必须设置超时（30s）和重试（最多3次）
- 抓取失败时必须优雅降级，返回部分结果

## 安全与合规
- 禁止采集需要登录才能访问的内容
- 禁止对目标网站发起高频请求（QPS < 1）
- 所有采集的数据仅用于内部分析，不得对外分发

## 常用命令
- `/research [竞品名称]`：启动完整调研流程
- `/report [格式]`：生成分析报告
- `/validate`：对已有数据进行事实核查

## 编码规范
- Python 脚本使用 type hints
- 敏感信息使用环境变量，禁止硬编码
- 包管理：`requirements.txt`