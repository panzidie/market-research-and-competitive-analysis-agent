---
description: 基于已有数据生成分析报告
arguments: 报告格式 (markdown/html/pdf)
---

# 报告生成命令

## 输入
已有数据位于 `./data/processed/` 目录
报告格式：$ARGUMENTS

## 执行流程
1. 读取 `./data/processed/` 中的所有分析数据
2. 启动 `writer` 子代理整合数据
3. 按目标格式生成报告
4. 启动 `fact_checker` 进行最终核查

## 输出
报告保存至 `./data/reports/report_<timestamp>.<format>`
