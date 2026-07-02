# -*- coding: utf-8 -*-
"""
backend/services/event_type.py — 事件类型定义
"""

from enum import Enum
from pydantic import BaseModel
from typing import Any


class EventType(str, Enum):
    # 会话生命周期
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"

    # 消息
    USER_MESSAGE = "user_message"
    ASSISTANT_MESSAGE = "assistant_message"

    # LangGraph 工作流阶段
    WORKFLOW_STARTED = "workflow_started"
    STAGE_STARTED = "stage_started"
    STAGE_COMPLETED = "stage_completed"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_ERROR = "workflow_error"

    # Agent 内部进度
    AGENT_PROGRESS = "agent_progress"
    LLM_CALL_START = "llm_call_start"
    LLM_CALL_END = "llm_call_end"
    LLM_TOKEN_STREAM = "llm_token_stream"

    # ReAct 循环
    REACT_STARTED = "react_started"
    REACT_THOUGHT = "react_thought"
    REACT_ACTION = "react_action"
    REACT_OBSERVATION = "react_observation"
    REACT_ENDED = "react_ended"

    # 搜索
    SEARCH_STARTED = "search_started"
    SEARCH_RESULT = "search_result"
    SEARCH_ERROR = "search_error"

    # 报告
    REPORT_GENERATED = "report_generated"

    # 系统
    SYSTEM_INFO = "system_info"
    HEARTBEAT = "heartbeat"


class WorkflowStage(str, Enum):
    DISCOVERY = "discovery"
    COLLECTION = "collection"
    PARALLEL_ANALYSIS = "parallel_analysis"
    STRATEGY = "strategy"


class WSEvent(BaseModel):
    event_type: EventType
    session_id: str
    timestamp: float
    payload: dict[str, Any] = {}
