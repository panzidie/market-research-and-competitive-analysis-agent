
"""
技能模板库 — 从 .claude/skills/ 迁移到 Python 代码
提供数据提取、竞品矩阵、SWOT 分析等标准化模板
"""

# === 数据提取模板 ===
DATA_EXTRACTION_TEMPLATE = """从以下文本中提取结构化的竞品信息：

## 提取字段
- product_name: 产品名称
- company: 所属公司
- launch_date: 发布时间
- target_audience: 目标用户
- core_features: 核心功能列表（数组）
- pricing: 定价信息 {model, price, currency, period}
- platforms: 支持的平台
- integrations: 第三方集成

## 定价模式识别
- Freemium / Free Trial / Subscription / One-time / Usage-based
- 提取各套餐的价格、功能和用户限制

## 输出格式
始终输出标准 JSON 格式，便于后续程序化处理。"""

# === 竞品矩阵模板 ===
COMPETITOR_MATRIX_TEMPLATE = """建立竞品功能对比矩阵，进行横向对比分析。

## 功能对比维度
- 核心功能完整性
- 用户体验（UI/UX）
- 移动端支持
- API 开放性
- 第三方集成数量
- 安全合规认证
- 客户支持质量

## 商业对比维度
- 定价模式与价格区间
- 市场份额 / 融资情况 / 团队规模 / 客户案例

## 技术对比维度
- 技术架构 / 部署方式（SaaS/自托管）/ 扩展性 / 性能指标

## 矩阵格式
| 对比维度 | 竞品A | 竞品B | 竞品C | 信息来源 |
|---------|-------|-------|-------|---------|
| ...     | ...   | ...   | ...   | ...     |

使用 ✅/❌/⚠️ 表示支持情况，数值型数据使用具体数字"""

# === SWOT 分析模板 ===
SWOT_ANALYSIS_TEMPLATE = """对竞品进行 SWOT 分析。

## 优势 (Strengths)
- 产品差异化特点、技术壁垒、品牌影响力、客户忠诚度、成本优势

## 劣势 (Weaknesses)
- 功能缺失、用户体验问题、市场覆盖不足、资源限制

## 机会 (Opportunities)
- 市场增长空间、新技术应用、政策利好、竞争对手弱点

## 威胁 (Threats)
- 新进入者、替代品、政策风险、技术变革

## 输出格式
每个维度 3-5 点，每点附带简要说明和来源。"""
