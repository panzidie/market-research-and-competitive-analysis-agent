from typing import Annotated, Optional, Any

from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class ResearchResult(TypedDict):
    """搜索结果条目"""
    source: str
    title: str
    content: str
    url: str
    date: Optional[str]


class AnalysisResult(TypedDict):
    """分析结果"""
    swot_analysis: Optional[dict]
    feature_matrix: Optional[list]
    summary: Optional[str]


class AgentState(TypedDict):
    """全局状态"""
    competitor_name: str
    messages: Annotated[list, add_messages]
    research_results: list[ResearchResult]
    analysis: Optional[AnalysisResult]
    report: Optional[str]
    error_count: int
    max_errors: int
    memory: Optional[Any]  # ShortTermMemory 实例
    security: Optional[Any]  # SecurityManager 实例


class ResearchState(TypedDict):
    results: list[ResearchResult]
    query: str


class AnalysisState(TypedDict):
    data: list[ResearchResult]
    analysis: Optional[AnalysisResult]


class ReportState(TypedDict):
    analysis: AnalysisResult
    report: Optional[str]
