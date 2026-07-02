# -*- coding: utf-8 -*-
"""
backend/services/event_bus.py — 事件发射器
"""

import asyncio
import time
from backend.services.event_type import WSEvent, EventType


class EventEmitter:
    """可注入到任何 Agent/Orchestrator 的事件发射器"""

    def __init__(self, queue: asyncio.Queue, session_id: str):
        self._queue = queue
        self.session_id = session_id

    async def emit(self, event_type: EventType, payload: dict = None):
        await self._queue.put(WSEvent(
            event_type=event_type,
            session_id=self.session_id,
            timestamp=time.time(),
            payload=payload or {},
        ))
