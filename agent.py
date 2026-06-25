"""
竞品分析智能体 — LangGraph 入口
"""
from typing import Literal

from dotenv import load_dotenv; load_dotenv()

from langgraph.graph import StateGraph, END

from core.state import AgentState
from core.tracer import logger
from core.memory import ShortTermMemory
from core.security import SecurityManager
from nodes import research_node, extract_node, report_node


def should_continue(state: AgentState) -> Literal["extract", "report", "__end__"]:
    """条件边：根据错误计数决定是否继续或熔断"""
    if state.get("error_count", 0) >= state.get("max_errors", 5):
        logger.warning(f"错误次数 {state['error_count']} 达到上限，熔断")
        return "__end__"
    if not state.get("research_results"):
        return "__end__"
    if not state.get("analysis"):
        return "extract"
    if not state.get("report"):
        return "report"
    return "__end__"


def build_agent() -> StateGraph:
    """编译 LangGraph 图"""
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("research", research_node)
    workflow.add_node("extract", extract_node)
    workflow.add_node("report", report_node)

    # 设置入口
    workflow.set_entry_point("research")

    # 添加条件边
    workflow.add_conditional_edges(
        "research",
        should_continue,
        {"extract": "extract", "__end__": END},
    )
    workflow.add_conditional_edges(
        "extract",
        should_continue,
        {"report": "report", "__end__": END},
    )
    workflow.add_edge("report", END)

    return workflow.compile()


def run_agent(competitor_name: str, max_steps: int = 10) -> str:
    """运行竞品分析智能体"""
    agent = build_agent()
    logger.info(f"开始分析竞品: {competitor_name}")

    memory = ShortTermMemory(max_rounds=10)
    memory.add_system_message(f"开始竞品分析: {competitor_name}")
    security = SecurityManager()

    initial_state = AgentState(
        competitor_name=competitor_name,
        messages=[],
        research_results=[],
        analysis=None,
        report=None,
        error_count=0,
        max_errors=5,
        memory=memory,
        security=security,
    )

    result = agent.invoke(initial_state, {"recursion_limit": max_steps})
    report = result.get("report")
    if not report:
        logger.warning(f"报告生成为空，使用备用报告")
        report = f"# {competitor_name} 竞品分析报告\n\n分析过程已完成，但报告生成节点未返回有效结果。请检查日志。"
    logger.info(f"分析完成: {competitor_name}")

    # 保存报告
    import os
    from datetime import datetime

    reports_dir = "data/reports"
    os.makedirs(reports_dir, exist_ok=True)
    filename = f"{competitor_name}_{datetime.now():%Y%m%d_%H%M%S}.md"
    filepath = os.path.join(reports_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)
    logger.info(f"报告已保存: {filepath}")

    return report


if __name__ == "__main__":
    import sys

    name = sys.argv[1] if len(sys.argv) > 1 else "示例竞品"
    print(run_agent(name))
