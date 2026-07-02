# -*- coding: utf-8 -*-
"""
backend/routers/ws.py — WebSocket 端点
"""

import asyncio
import time
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.dependencies import session_manager
from backend.services.event_type import EventType

router = APIRouter()


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    session = await session_manager.get_or_create(session_id)

    # 发送会话开始事件
    await session.emitter.emit(EventType.SESSION_STARTED, {
        "session_id": session_id,
    })

    async def _send_events():
        """后台：从事件队列读取并推送 WebSocket"""
        while True:
            try:
                event = await asyncio.wait_for(session.queue.get(), timeout=30.0)
                await websocket.send_json(event.model_dump())
            except asyncio.TimeoutError:
                # 心跳保活
                try:
                    await websocket.send_json({
                        "event_type": EventType.HEARTBEAT,
                        "session_id": session_id,
                        "timestamp": time.time(),
                        "payload": {},
                    })
                except Exception:
                    break

    send_task = asyncio.create_task(_send_events())

    try:
        # 客户端断开
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            action = msg.get("action", "")
            if action == "chat":
                content = msg.get("content", "").strip()
                if content:
                    await session.process_message(content)
            elif action == "stop":
                await session.stop()
            elif action == "ping":
                pass  # 心跳，_send_events 自动处理
    except WebSocketDisconnect:
        pass
    finally:
        send_task.cancel()
        try:
            await send_task
        except asyncio.CancelledError:
            pass
