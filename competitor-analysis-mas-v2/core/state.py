# -*- coding: utf-8 -*-
"""
core/state.py — LangGraph AnalysisState 定义

TypedDict 定义了整个 DAG 各节点间共享的状态。
所有字段使用 total=False 使其可选，节点按需填充。
"""

import operator
from typing import TypedDict, Optional, Annotated

from models.domain import (
    CompetitorList, CompetitorData,
    ProductAnalysis, PricingAnalysis, MarketAnalysis,
    StrategyReport
)


class AnalysisState(TypedDict, total=False):
    """竞品分析流程的全局状态

    LangGraph 每个节点读取 state，返回 dict 做增量更新。
    扇出节点并行执行，扇入时 LangGraph 自动等待并合并结果。
    """
    # ── 输入参数 ──
    product_description: str
    max_competitors: int

    # ── Phase 1 输出 ──
    competitor_list: CompetitorList

    # ── Phase 2 输出 ──
    competitors_data: dict[str, CompetitorData]

    # ── Phase 3 (Fan-out) 输出 ──
    product_analysis: ProductAnalysis
    pricing_analysis: PricingAnalysis
    market_analysis: MarketAnalysis

    # ── Phase 4 (Fan-in) 输出 ──
    strategy_report: StrategyReport

    # ── 元信息 ──
    timings: dict[str, float]
    all_llm_logs: Annotated[list[dict], operator.add]
    error: Optional[str]
