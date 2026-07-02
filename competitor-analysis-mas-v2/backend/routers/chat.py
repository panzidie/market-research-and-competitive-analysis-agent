# -*- coding: utf-8 -*-
"""
backend/routers/chat.py — 聊天历史 REST 端点
"""

from fastapi import APIRouter
from backend.dependencies import session_manager

router = APIRouter()


@router.get("/api/sessions")
async def list_sessions():
    """返回当前内存中所有活跃会话"""
    return {"sessions": session_manager.list_sessions()}


@router.get("/api/sessions/{session_id}/history")
async def session_history(session_id: str):
    """返回指定会话的消息历史（从内存读取）"""
    session = session_manager.get_session(session_id)
    if not session:
        return {"messages": []}
    messages = session.agent.memory.to_messages()
    return {"session_id": session_id, "messages": [
        {"role": role, "content": content} for role, content in messages
    ]}


@router.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    await session_manager.remove_session(session_id)
    return {"status": "ok"}
