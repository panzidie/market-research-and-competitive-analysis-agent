# -*- coding: utf-8 -*-
"""
backend/main.py — FastAPI 入口
"""

import os
import sys

# 将项目根目录（competitor-analysis-mas-v2 内层）加入 sys.path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.routers import ws, chat, reports
from backend.dependencies import session_manager
import config

app = FastAPI(title="智能竞品分析系统", version="1.0.0")

# CORS（开发模式允许所有来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载路由
app.include_router(ws.router)
app.include_router(chat.router)
app.include_router(reports.router)


@app.get("/api/health")
async def health():
    """健康检查"""
    return {
        "status": "ok",
        "llm_provider": config.LLM_PROVIDER,
        "search_provider": config.SEARCH_PROVIDER,
    }


@app.on_event("shutdown")
async def shutdown():
    await session_manager.cleanup_all()


def main():
    host = getattr(config, "SERVER_HOST", "0.0.0.0")
    port = getattr(config, "SERVER_PORT", 8000)

    # 生产模式：挂载前端静态文件
    web_dist = os.path.join(_PROJECT_ROOT, "web", "dist")
    if os.path.isdir(web_dist):
        app.mount("/", StaticFiles(directory=web_dist, html=True), name="frontend")

    print(f"  🌐 API 服务: http://{host}:{port}")
    print(f"  📡 WebSocket: ws://{host}:{port}/ws/{{session_id}}")
    print(f"  📋 文档:     http://{host}:{port}/docs")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
