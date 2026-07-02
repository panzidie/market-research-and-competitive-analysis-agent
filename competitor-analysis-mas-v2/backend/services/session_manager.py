# -*- coding: utf-8 -*-
"""
backend/services/session_manager.py — 多用户会话管理
"""

import asyncio
import uuid
from typing import Optional
from agents.conversational_agent import ConversationalAgent
from backend.services.event_bus import EventEmitter
from backend.services.event_type import EventType


class Session:
    """单个会话：包含独立 Agent、事件队列和记忆"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.queue: asyncio.Queue = asyncio.Queue()
        self.emitter = EventEmitter(self.queue, session_id)
        self.agent = ConversationalAgent(max_turns=10)
        self.created_at: float = 0
        self._running_task: Optional[asyncio.Task] = None

    async def process_message(self, content: str):
        """在后台任务中处理用户消息"""
        loop = asyncio.get_event_loop()

        async def _run():
            await self.emitter.emit(EventType.USER_MESSAGE, {
                "content": content,
                "session_id": self.session_id,
            })
            try:
                reply = await self.agent.chat(content, event_emitter=self.emitter)
                await self.emitter.emit(EventType.ASSISTANT_MESSAGE, {
                    "content": reply,
                    "session_id": self.session_id,
                })
            except asyncio.CancelledError:
                await self.emitter.emit(EventType.WORKFLOW_ERROR, {
                    "error": "用户取消了操作",
                })
            except Exception as e:
                await self.emitter.emit(EventType.WORKFLOW_ERROR, {
                    "error": str(e),
                })

        self._running_task = asyncio.create_task(_run())

    async def stop(self):
        """取消当前正在执行的任务"""
        if self._running_task and not self._running_task.done():
            self._running_task.cancel()
            try:
                await self._running_task
            except asyncio.CancelledError:
                pass

    async def cleanup(self):
        """清理会话资源"""
        if self._running_task and not self._running_task.done():
            self._running_task.cancel()
            try:
                await self._running_task
            except asyncio.CancelledError:
                pass
        self.agent.memory.close()


class SessionManager:
    """管理多用户 WebSocket 连接和 Agent 实例"""

    def __init__(self):
        self._sessions: dict[str, Session] = {}

    async def get_or_create(self, session_id: str = None) -> Session:
        if session_id is None:
            session_id = str(uuid.uuid4())
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(session_id)
        return self._sessions[session_id]

    async def create_session(self) -> Session:
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = Session(session_id)
        return self._sessions[session_id]

    async def remove_session(self, session_id: str):
        session = self._sessions.pop(session_id, None)
        if session:
            await session.cleanup()

    def get_session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    async def cleanup_all(self):
        for sid in list(self._sessions.keys()):
            await self.remove_session(sid)

    def list_sessions(self) -> list[dict]:
        """返回会话列表摘要"""
        result = []
        for sid, session in self._sessions.items():
            result.append({
                "session_id": sid,
                "message_count": session.agent.memory.turn_count,
                "created_at": session.created_at,
            })
        return result
