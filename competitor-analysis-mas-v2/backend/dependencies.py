# -*- coding: utf-8 -*-
"""
backend/dependencies.py — FastAPI 依赖注入
"""

from backend.services.session_manager import SessionManager

# 全局单例（应用启动时创建）
session_manager: SessionManager = SessionManager()
