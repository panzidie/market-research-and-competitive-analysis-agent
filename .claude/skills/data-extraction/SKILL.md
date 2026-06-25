---
name: data-extraction
description: 从非结构化文本中提取结构化的竞品信息（功能列表、定价、发布时间等）
---

# 数据提取技能

## 触发条件
当用户需要从网页、PDF、新闻稿等文本中提取竞品信息时触发。

## 提取模板

### 产品信息提取
从文本中提取以下字段：
- `product_name`: 产品名称
- `company`: 所属公司
- `launch_date`: 发布时间
- `target_audience`: 目标用户
- `core_features`: 核心功能列表（数组）
- `pricing`: 定价信息 {model, price, currency, period}
- `platforms`: 支持的平台
- `integrations`: 第三方集成

### 定价信息提取
识别以下定价模式：
- Freemium / Free Trial / Subscription / One-time / Usage-based
- 提取各套餐的价格、功能和用户限制

### 版本迭代提取
提取版本号、发布时间、新增功能、修复内容

## 输出格式
始终输出标准 JSON 格式，便于后续程序化处理。
