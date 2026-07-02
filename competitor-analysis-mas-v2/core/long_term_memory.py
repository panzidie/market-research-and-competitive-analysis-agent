# -*- coding: utf-8 -*-
"""
core/long_term_memory.py — 长期记忆（三层存储架构）

三层存储：
  1. deque 滑动窗口（短期对话记忆，同 ConversationMemory）
  2. SQLite（持久化对话消息 + 分析报告，支持关键词检索）
  3. ChromaDB（语义向量搜索，可选依赖，缺失时自动降级至 SQLite LIKE）

设计原则：
  - LongTermMemory 包装 ConversationMemory，保持 API 完全兼容
  - ChromaDB 为可选依赖：未安装时语义搜索降级到 SQLite 模糊匹配
  - clear() 仅清空短期记忆窗口，不影响持久化存储（便于跨会话检索）
  - close() 释放数据库连接，支持跨会话重连
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from datetime import datetime
from typing import Any

from core.memory import ConversationMemory
import config

# ── ChromaDB 可选导入 ──────────────────────────────────────────
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    _HAS_CHROMA = True
except ImportError:
    _HAS_CHROMA = False

# ── 路径解析 ───────────────────────────────────────────────────
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resolve_path(path: str) -> str:
    if not os.path.isabs(path):
        return os.path.normpath(os.path.join(_PROJECT_ROOT, path))
    return path


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ═══════════════════════════════════════════════════════════════
#  LongTermMemory
# ═══════════════════════════════════════════════════════════════


class LongTermMemory:
    """长期记忆 — 三层存储（滑动窗口 + SQLite + ChromaDB）

    用法:
        mem = LongTermMemory(max_turns=10)
        mem.add("user", "帮我分析飞书的竞品")
        mem.add("assistant", "好的，正在分析...")

        # 关键词检索
        results = mem.keyword_search("飞书")

        # 语义搜索（ChromaDB 优先，降级到 SQLite）
        results = mem.semantic_search("企业协作竞品", top_k=5)

        # 持久化分析报告
        mem.add_analysis_report({...})

        mem.close()
    """

    def __init__(self, max_turns: int = 10):
        # ── 第一层：短期滑动窗口 ──
        self._conversation = ConversationMemory(max_turns=max_turns)

        # ── 会话标识 ──
        self._session_id = uuid.uuid4().hex[:12]
        self._doc_counter = 0

        # ── 第二层：SQLite ──
        db_path = _resolve_path(config.LTM_DB_PATH)
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._conn = self._init_sqlite(db_path)

        # ── 第三层：ChromaDB（可选） ──
        self._chroma_client: Any = None
        self._chat_collection: Any = None
        self._report_collection: Any = None
        if _HAS_CHROMA:
            self._init_chroma()

    # ────────────────────────────────────────────────
    #  SQLite 初始化
    # ────────────────────────────────────────────────

    @staticmethod
    def _init_sqlite(db_path: str) -> sqlite3.Connection:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS analysis_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                product_name TEXT NOT NULL,
                report_data TEXT NOT NULL,
                summary TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
            )"""
        )
        conn.commit()
        return conn

    # ────────────────────────────────────────────────
    #  ChromaDB 初始化
    # ────────────────────────────────────────────────

    def _init_chroma(self):
        try:
            chroma_dir = _resolve_path(config.LTM_CHROMA_DIR)
            os.makedirs(chroma_dir, exist_ok=True)
            self._chroma_client = chromadb.PersistentClient(
                path=chroma_dir,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._chat_collection = self._chroma_client.get_or_create_collection(
                name="chat_messages_v2",
                metadata={"hnsw:space": "cosine"},
            )
            self._report_collection = self._chroma_client.get_or_create_collection(
                name="analysis_reports_v2",
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as e:
            print(f"  [LongTermMemory] ChromaDB 初始化失败: {e}，"
                  f"语义搜索将降级到 SQLite")
            self._chroma_client = None
            self._chat_collection = None
            self._report_collection = None

    # ────────────────────────────────────────────────
    #  属性
    # ────────────────────────────────────────────────

    @property
    def turn_count(self) -> int:
        return self._conversation.turn_count

    # ────────────────────────────────────────────────
    #  短期记忆操作（委托给 ConversationMemory）
    # ────────────────────────────────────────────────

    def add(self, role: str, content: str):
        """添加一条对话消息（同时持久化到 SQLite 和 ChromaDB）"""
        self._conversation.add(role, content)
        self._save_message_sqlite(role, content)
        self._save_message_chroma(role, content)

    def to_messages(self) -> list[tuple[str, str]]:
        return self._conversation.to_messages()

    def format_for_prompt(self) -> str:
        return self._conversation.format_for_prompt()

    def clear(self):
        """清空短期记忆窗口（持久化数据不受影响）"""
        self._conversation.clear()

    # ────────────────────────────────────────────────
    #  持久化存储
    # ────────────────────────────────────────────────

    def _save_message_sqlite(self, role: str, content: str):
        self._conn.execute(
            "INSERT INTO chat_messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (self._session_id, role, content, _now()),
        )
        self._conn.commit()

    def _save_message_chroma(self, role: str, content: str):
        if self._chat_collection is None:
            return
        self._doc_counter += 1
        doc_id = f"chat_{self._session_id}_{self._doc_counter}"
        try:
            self._chat_collection.add(
                documents=[content],
                metadatas=[{
                    "type": "chat_message",
                    "role": role,
                    "session_id": self._session_id,
                }],
                ids=[doc_id],
            )
        except Exception:
            pass

    def add_analysis_report(self, report_data: dict):
        """持久化分析报告（到 SQLite 和 ChromaDB）"""
        product_name = report_data.get("product_name", "未知产品")
        report_json = json.dumps(report_data, ensure_ascii=False)
        summary = (report_data.get("summary")
                   or report_data.get("overall_positioning")
                   or product_name)

        # SQLite
        self._conn.execute(
            "INSERT INTO analysis_reports (session_id, product_name, report_data, summary, created_at) VALUES (?, ?, ?, ?, ?)",
            (self._session_id, product_name, report_json, summary, _now()),
        )
        self._conn.commit()

        # ChromaDB
        if self._report_collection is not None:
            self._doc_counter += 1
            doc_id = f"report_{self._session_id}_{self._doc_counter}"
            try:
                self._report_collection.add(
                    documents=[summary[:2000]],
                    metadatas=[{
                        "type": "analysis_report",
                        "product_name": product_name,
                        "session_id": self._session_id,
                    }],
                    ids=[doc_id],
                )
            except Exception:
                pass

    # ────────────────────────────────────────────────
    #  检索
    # ────────────────────────────────────────────────

    def keyword_search(self, query: str, top_k: int = 10) -> list[dict]:
        """基于 SQLite LIKE 的关键词搜索（跨会话）"""
        like = f"%{query}%"
        results: list[dict] = []
        cursor = self._conn.cursor()

        # 搜索对话消息
        cursor.execute(
            "SELECT role, content, created_at FROM chat_messages "
            "WHERE content LIKE ? ORDER BY created_at DESC LIMIT ?",
            (like, top_k),
        )
        for role, content, ts in cursor.fetchall():
            results.append({
                "type": "chat_message",
                "role": role,
                "content": content,
                "created_at": ts,
                "score": 0.5,
                "adjusted_score": 0.5,
            })

        # 搜索分析报告
        cursor.execute(
            "SELECT product_name, report_data, summary, created_at FROM analysis_reports "
            "WHERE product_name LIKE ? OR summary LIKE ? ORDER BY created_at DESC LIMIT ?",
            (like, like, top_k),
        )
        for product_name, report_json, summary, ts in cursor.fetchall():
            results.append({
                "type": "analysis_report",
                "product_name": product_name,
                "content": summary or product_name,
                "created_at": ts,
                "score": 0.5,
                "adjusted_score": 0.5,
            })

        return results

    def semantic_search(self, query: str, top_k: int = 5) -> list[dict]:
        """语义搜索（ChromaDB 优先，降级到 SQLite LIKE）"""
        results: list[dict] = []

        # ── ChromaDB 语义搜索 ──
        if self._chat_collection is not None or self._report_collection is not None:
            try:
                n = max(top_k, 1)
                # 搜索对话集合
                if self._chat_collection is not None:
                    q = self._chat_collection.query(
                        query_texts=[query],
                        n_results=n,
                    )
                    self._merge_chroma_results(q, results, "chat_message")

                # 搜索报告集合
                if self._report_collection is not None:
                    q = self._report_collection.query(
                        query_texts=[query],
                        n_results=n,
                    )
                    self._merge_chroma_results(q, results, "analysis_report")

            except Exception as e:
                print(f"  [LongTermMemory] ChromaDB 查询失败: {e}，"
                      f"降级到 SQLite 搜索")
                results = []

        # ── 降级：SQLite LIKE ──
        if not results:
            return self._fallback_search(query, top_k)

        # 排序并截取
        results.sort(key=lambda r: r.get("adjusted_score", 0), reverse=True)
        return results[:top_k]

    @staticmethod
    def _merge_chroma_results(chroma_result: dict, results: list[dict],
                              default_type: str):
        """将 ChromaDB 查询结果合并到 results 列表中"""
        ids = chroma_result.get("ids", [[]])[0]
        documents = chroma_result.get("documents", [[]])[0]
        metadatas = chroma_result.get("metadatas", [[]])[0]
        distances = chroma_result.get("distances", [[]])[0]

        for i in range(len(ids)):
            meta = metadatas[i] if i < len(metadatas) else {}
            score = 1.0 - distances[i] if i < len(distances) else 0.5
            score = max(0.0, min(1.0, score))

            doc_type = meta.get("type", default_type)
            product_name = meta.get("product_name", "")
            role = meta.get("role", "")

            results.append({
                "type": doc_type,
                "product_name": product_name,
                "content": documents[i] if i < len(documents) else "",
                "role": role,
                "score": score,
                "adjusted_score": round(score * 0.95, 4),
            })

    def _fallback_search(self, query: str, top_k: int) -> list[dict]:
        """语义搜索的 SQLite 降级方案"""
        results = self.keyword_search(query, top_k)

        # 如果直接 LIKE 没有匹配，拆词再搜
        if not results:
            words = re.findall(r"[一-鿿\w]+", query)
            for word in words[:3]:
                if len(word) >= 2:
                    results.extend(self.keyword_search(word, top_k // 2))

        # 去重
        seen: set[str] = set()
        unique: list[dict] = []
        for r in results:
            key = f"{r.get('type', '')}:{r.get('content', '')[:100]}"
            if key not in seen:
                seen.add(key)
                unique.append(r)

        return unique[:top_k]

    # ────────────────────────────────────────────────
    #  生命周期
    # ────────────────────────────────────────────────

    def close(self):
        """释放 SQLite 连接等资源"""
        self._conversation.close()
        try:
            self._conn.close()
        except Exception:
            pass
