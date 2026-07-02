# -*- coding: utf-8 -*-
"""
core/langgraph_orchestrator.py — LangGraph 编排器

使用 LangGraph StateGraph 作为核心编排框架。
DAG 结构:
  discovery → collection → parallel_analysis(internal gather) → strategy

双轴多层降级：
  轴1 (Provider): llm_client 内部 DeepSeek → Ollama → 千帆 (已内置于 llm_call)
  轴2 (Logic):   每个 Agent 内部 LLM → 规则引擎 → 占位数据 (已内置于 Agent.run)
"""

import asyncio
import time

from langgraph.graph import StateGraph, END

from core.state import AnalysisState
from core.llm_client import get_llm_stats
from models.domain import (
    CompetitorList, CompetitorData,
    ProductAnalysis, PricingAnalysis, MarketAnalysis,
    StrategyReport
)
from agents.discovery_agent import DiscoveryAgent
from agents.collection_agent import CollectionAgent
from agents.product_agent import ProductAgent
from agents.pricing_agent import PricingAgent
from agents.market_agent import MarketAgent
from agents.strategy_agent import StrategyAgent
import config


class LangGraphOrchestrator:
    """
    LangGraph 竞品分析编排器

    用法:
        orchestrator = LangGraphOrchestrator()
        report = await orchestrator.analyze("产品描述", max_competitors=5)

    图结构:
      discovery → collection → parallel_analysis → strategy → END

    parallel_analysis 节点内部用 asyncio.gather 并行执行三个分析 Agent，
    这是 LangGraph 推荐的 fan-in 模式——单个节点内做并行，避免了多条边
    fan-in 时目标节点被重复调用的陷阱。
    """

    def __init__(self, event_emitter=None):
        # ── 创建所有Agent（复用现有业务逻辑） ──
        self.discovery_agent = DiscoveryAgent()
        self.collection_agent = CollectionAgent()
        self.product_agent = ProductAgent()
        self.pricing_agent = PricingAgent()
        self.market_agent = MarketAgent()
        self.strategy_agent = StrategyAgent()
        self._emitter = event_emitter

        # ── 编译图（一次性编译，可复用） ──
        self._graph = self._build_graph()

        # ── 缓存（供 report 生成使用） ──
        self.timings: dict[str, float] = {}
        self._last_competitor_list: CompetitorList = None
        self._last_competitors_data: dict[str, CompetitorData] = None
        self._last_product_analysis: ProductAnalysis = None
        self._last_pricing_analysis: PricingAnalysis = None
        self._last_market_analysis: MarketAnalysis = None

    async def _emit(self, event_type: str, payload: dict = None):
        """快捷 emit 事件（emitter 存在时）"""
        if self._emitter:
            try:
                await self._emitter.emit(event_type, payload or {})
            except Exception:
                pass

    def _stage_label(self, stage: str) -> tuple[str, int]:
        labels = {
            "discovery": ("竞品发现", 0),
            "collection": ("数据采集", 1),
            "parallel_analysis": ("并行分析", 2),
            "strategy": ("策略建议", 3),
        }
        return labels.get(stage, (stage, -1))

    # ═══════════════════════════════════════════════════
    #  图构建
    # ═══════════════════════════════════════════════════

    def _build_graph(self):
        """
        构建 LangGraph StateGraph

        边结构：
          discovery → collection → parallel_analysis → strategy → END

        不直接用 3 条边 fan-in[product,pricing,market]→strategy，
        因为 LangGraph 的 add_edge 会导致 strategy 被执行 3 次（每次
        只有部分分析数据就绪）。改用单节点内 asyncio.gather 实现并行。
        """
        graph = StateGraph(AnalysisState)

        # 添加节点
        graph.add_node("discovery", self._node_discovery)
        graph.add_node("collection", self._node_collection)
        graph.add_node("parallel_analysis", self._node_parallel_analysis)
        graph.add_node("strategy", self._node_strategy)

        # 设置入口
        graph.set_entry_point("discovery")

        # 串行管线
        graph.add_edge("discovery", "collection")
        graph.add_edge("collection", "parallel_analysis")
        graph.add_edge("parallel_analysis", "strategy")
        graph.add_edge("strategy", END)

        return graph.compile()

    # ═══════════════════════════════════════════════════
    #  图节点
    # ═══════════════════════════════════════════════════

    async def _node_discovery(self, state: AnalysisState) -> dict:
        """Phase 1: 竞品发现"""
        print(f"\n{'█' * 65}")
        print("  🔍 Phase 1: 竞品发现")
        print(f"{'█' * 65}")

        label, idx = self._stage_label("discovery")
        await self._emit("stage_started", {
            "stage": "discovery", "label": label,
            "stage_index": idx, "total_stages": 4, "product": state["product_description"],
        })

        user_request = state.get("user_analysis_request", state["product_description"])
        phase_start = time.time()
        competitor_list = await self.discovery_agent.run(
            state["product_description"],
            state["max_competitors"],
            user_request=user_request,
        )
        elapsed = time.time() - phase_start

        competitors_summary = []
        if competitor_list and competitor_list.competitors:
            competitors_summary = [
                {"name": c.name, "brief": c.brief[:100] if c.brief else ""}
                for c in competitor_list.competitors
            ]

        await self._emit("stage_completed", {
            "stage": "discovery", "label": label, "elapsed_s": round(elapsed, 2),
            "result_summary": f"发现 {len(competitor_list.competitors)} 个竞品" if competitor_list else "无结果",
            "competitors": competitors_summary,
        })

        print(f"\n  ⏱️ 发现耗时: {elapsed:.2f}s")
        print(f"  📊 发现竞品: {len(competitor_list.competitors)}个")

        return {
            "competitor_list": competitor_list,
            "timings": {**state.get("timings", {}), "discovery": elapsed},
            "all_llm_logs": self.discovery_agent.llm_logs,
        }

    async def _node_collection(self, state: AnalysisState) -> dict:
        """Phase 2: 数据采集（逐竞品串行）"""
        print(f"\n{'█' * 65}")
        print("  📊 Phase 2: 数据采集")
        print(f"{'█' * 65}")

        label, idx = self._stage_label("collection")
        await self._emit("stage_started", {
            "stage": "collection", "label": label,
            "stage_index": idx, "total_stages": 4,
        })

        competitor_list = state.get("competitor_list")
        if not competitor_list or not competitor_list.competitors:
            print("  ⚠️ 无竞品可采集")
            await self._emit("stage_completed", {
                "stage": "collection", "label": label, "elapsed_s": 0,
                "result_summary": "无竞品可采集",
                "competitor_count": 0,
            })
            return {
                "competitors_data": {},
                "error": "no_competitors",
            }

        phase_start = time.time()
        # 透传事件发射器给采集 Agent
        if self._emitter:
            self.collection_agent._react._emitter = self._emitter
        competitors_data = await self.collection_agent.run(
            state["product_description"],
            competitor_list
        )
        elapsed = time.time() - phase_start

        await self._emit("stage_completed", {
            "stage": "collection", "label": label, "elapsed_s": round(elapsed, 2),
            "result_summary": f"采集完成: {len(competitors_data)} 个竞品",
            "competitor_count": len(competitors_data),
        })

        print(f"\n  ⏱️ 采集耗时: {elapsed:.2f}s")
        print(f"  📊 采集完成: {len(competitors_data)}个竞品")

        return {
            "competitors_data": competitors_data,
            "timings": {**state.get("timings", {}), "collection": elapsed},
            "all_llm_logs": self.collection_agent.llm_logs,
        }

    async def _node_parallel_analysis(self, state: AnalysisState) -> dict:
        """
        Phase 3: 三维并行分析

        在 LangGraph 单节点内部使用 asyncio.gather 实现真正的并行 fan-in，
        避免多条边 fan-in 到 strategy 导致节点重复执行。
        """
        print(f"\n{'█' * 65}")
        print("  ⚡ Phase 3: 三维并行分析")
        print(f"{'█' * 65}")

        label, idx = self._stage_label("parallel_analysis")
        await self._emit("stage_started", {
            "stage": "parallel_analysis", "label": label,
            "stage_index": idx, "total_stages": 4,
        })

        product_name = state["competitor_list"].product_name
        competitors_data = state.get("competitors_data", {})

        phase_start = time.time()

        # 内部用 asyncio.gather 做真正的并行fan-in
        product_analysis, pricing_analysis, market_analysis = await asyncio.gather(
            self._run_product(product_name, competitors_data),
            self._run_pricing(product_name, competitors_data),
            self._run_market(product_name, competitors_data),
        )

        elapsed = time.time() - phase_start

        # 聚合三个 Agent 的 LLM 日志
        all_logs = (
            self.product_agent.llm_logs +
            self.pricing_agent.llm_logs +
            self.market_agent.llm_logs
        )

        result_summary = (
            f"产品分析: {len(product_analysis.feature_matrix)}个功能维度, "
            f"定价分析: {len(pricing_analysis.pricing_comparison)}个竞品定价, "
            f"市场分析: {len(market_analysis.market_share_data)}个竞品市场数据"
        )

        await self._emit("stage_completed", {
            "stage": "parallel_analysis", "label": label, "elapsed_s": round(elapsed, 2),
            "result_summary": result_summary,
        })

        print(f"\n  ⏱️ 并行分析耗时: {elapsed:.2f}s")
        print(f"  🔧 产品分析: {len(product_analysis.feature_matrix)}个功能维度")
        print(f"  💰 定价分析: {len(pricing_analysis.pricing_comparison)}个竞品定价")
        print(f"  📈 市场分析: {len(market_analysis.market_share_data)}个竞品市场数据")

        return {
            "product_analysis": product_analysis,
            "pricing_analysis": pricing_analysis,
            "market_analysis": market_analysis,
            "timings": {**state.get("timings", {}), "parallel_analysis": elapsed},
            "all_llm_logs": all_logs,
        }

    async def _run_product(self, product_name: str,
                           competitors_data: dict[str, CompetitorData]) -> ProductAnalysis:
        """运行产品分析（带异常保护）"""
        try:
            return await self.product_agent.run(product_name, competitors_data)
        except Exception as e:
            print(f"  ⚠️ ProductAgent 异常: {e}")
            return ProductAnalysis(summary=f"(分析失败: {e})")

    async def _run_pricing(self, product_name: str,
                           competitors_data: dict[str, CompetitorData]) -> PricingAnalysis:
        """运行定价分析（带异常保护）"""
        try:
            return await self.pricing_agent.run(product_name, competitors_data)
        except Exception as e:
            print(f"  ⚠️ PricingAgent 异常: {e}")
            return PricingAnalysis(summary=f"(分析失败: {e})")

    async def _run_market(self, product_name: str,
                          competitors_data: dict[str, CompetitorData]) -> MarketAnalysis:
        """运行市场分析（带异常保护）"""
        try:
            return await self.market_agent.run(product_name, competitors_data)
        except Exception as e:
            print(f"  ⚠️ MarketAgent 异常: {e}")
            return MarketAnalysis(summary=f"(分析失败: {e})")

    async def _node_strategy(self, state: AnalysisState) -> dict:
        """Phase 4: 策略建议"""
        print(f"\n{'█' * 65}")
        print("  🎯 Phase 4: 策略建议")
        print(f"{'█' * 65}")

        label, idx = self._stage_label("strategy")
        await self._emit("stage_started", {
            "stage": "strategy", "label": label,
            "stage_index": idx, "total_stages": 4,
        })

        competitor_list = state.get("competitor_list")
        product_name = competitor_list.product_name if competitor_list else ""

        phase_start = time.time()
        report = await self.strategy_agent.run(
            product_name,
            len(competitor_list.competitors) if competitor_list else 0,
            state.get("product_analysis", ProductAnalysis()),
            state.get("pricing_analysis", PricingAnalysis()),
            state.get("market_analysis", MarketAnalysis()),
        )
        elapsed = time.time() - phase_start

        # 聚合所有LLM日志到报告
        report.raw_llm_logs = state.get("all_llm_logs", []) + self.strategy_agent.llm_logs

        await self._emit("stage_completed", {
            "stage": "strategy", "label": label, "elapsed_s": round(elapsed, 2),
            "result_summary": f"生成 {len(report.action_plan)} 项行动方案",
            "action_plan_count": len(report.action_plan),
        })

        print(f"\n  ⏱️ 策略耗时: {elapsed:.2f}s")

        return {
            "strategy_report": report,
            "timings": {**state.get("timings", {}), "strategy": elapsed},
            "all_llm_logs": state.get("all_llm_logs", []) + self.strategy_agent.llm_logs,
        }

    # ═══════════════════════════════════════════════════
    #  公共接口
    # ═══════════════════════════════════════════════════

    async def analyze(self, product_description: str,
                      max_competitors: int = config.DEFAULT_COMPETITOR_COUNT,
                      user_analysis_request: str = None,
                      event_emitter=None) -> StrategyReport:
        """
        执行完整的竞品分析流程

        Args:
            product_description: 用户产品描述
            max_competitors: 最大竞品数量
            user_analysis_request: 用户原始请求
            event_emitter: 事件发射器（用于实时推送进度）

        Returns:
            StrategyReport: 完整策略建议报告
        """
        total_start = time.time()

        if event_emitter:
            self._emitter = event_emitter

        # 发送工作流开始事件
        await self._emit("workflow_started", {
            "product": product_description,
            "stages": ["discovery", "collection", "parallel_analysis", "strategy"],
            "total_stages": 4,
            "max_competitors": max_competitors,
        })

        print("\n" + "═" * 65)
        print("  🔍 智能竞品分析多Agent系统")
        print("  框架: LangGraph StateGraph | 模式: 串行 → 并行 → 串行 | "
              f"决策: {'🧠 LLM' if config.ENABLE_LLM else '📋 规则引擎'}")
        print("═" * 65)

        # ── 初始状态 ──
        initial_state: AnalysisState = {
            "product_description": product_description,
            "max_competitors": max_competitors,
            "user_analysis_request": user_analysis_request or product_description,
            "competitor_list": None,
            "competitors_data": None,
            "product_analysis": None,
            "pricing_analysis": None,
            "market_analysis": None,
            "strategy_report": None,
            "timings": {},
            "all_llm_logs": [],
            "error": None,
        }

        # ── 执行 DAG（带异常保护） ──
        print(f"\n  🚀 启动 LangGraph DAG 执行...")
        error = None
        try:
            final_state = await self._graph.ainvoke(initial_state)
        except Exception as e:
            error = str(e)
            print(f"\n  ❌ DAG 执行异常: {error}")
            final_state = initial_state

        # ── 统计总耗时 ──
        total_elapsed = time.time() - total_start
        timings = final_state.get("timings", {})
        timings["total"] = total_elapsed

        self.timings = timings

        if error:
            await self._emit("workflow_error", {
                "error": error, "elapsed_s": round(total_elapsed, 2),
            })
            report = StrategyReport(product_name=product_description)
            return report

        # ── 获取报告 ──
        report = final_state.get("strategy_report")
        if report is None:
            report = StrategyReport(product_name=product_description)

        # ── 工作流完成事件 ──
        await self._emit("workflow_completed", {
            "product_name": report.product_name,
            "elapsed_s": round(total_elapsed, 2),
            "competitor_count": report.competitor_count,
            "action_plan_count": len(report.action_plan),
            "summary": report.summary[:200] if report.summary else "",
        })

        # ── 缓存数据（供HTML报告生成） ──
        self._last_competitor_list = final_state.get("competitor_list")
        self._last_competitors_data = final_state.get("competitors_data")
        self._last_product_analysis = final_state.get("product_analysis")
        self._last_pricing_analysis = final_state.get("pricing_analysis")
        self._last_market_analysis = final_state.get("market_analysis")

        print(f"\n{'═' * 65}")
        print(f"  🏁 分析完成 | 总耗时: {total_elapsed:.2f}s")
        print(f"  🎯 行动方案: {len(report.action_plan)}项")
        print(f"{'═' * 65}")

        # ── 打印格式化报告 ──
        formatted = self.strategy_agent.format_report(report)
        print(formatted)

        return report

    def get_timings(self) -> dict:
        """获取各阶段耗时"""
        return self.timings.copy()

    def print_stats(self):
        """打印统计信息"""
        print("\n" + "─" * 65)
        print("  📈 分析统计")
        print("─" * 65)
        print(f"  ⏱️ 各阶段耗时:")
        for name, duration in self.timings.items():
            print(f"    • {name}: {duration:.2f}s")

        if config.ENABLE_LLM:
            stats = get_llm_stats()
            print(f"\n  🧠 LLM调用统计:")
            print(f"    • 总调用: {stats['total']}")
            print(f"    • 成功: {stats['success']}")
            print(f"    • 降级: {stats['fallback']}")
            if stats['total'] > 0:
                rate = stats['success'] / stats['total'] * 100
                print(f"    • 成功率: {rate:.0f}%")
