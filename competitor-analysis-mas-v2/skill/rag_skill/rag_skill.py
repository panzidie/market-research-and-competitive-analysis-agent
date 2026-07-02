# -*- coding: utf-8 -*-
"""
skill/rag_skill/rag_skill.py — RAG 检索 + LLM 生成 Skill
"""

from __future__ import annotations

import logging
import os
import sys
import time

from dotenv import load_dotenv
from langchain_core.tools import tool

# 加载 .env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

logger = logging.getLogger("rag_skill")

# ── RAG 依赖隔离导入 ──────────────────────────────────────────
_RAG_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "RAG")
)
if _RAG_ROOT not in sys.path:
    sys.path.insert(0, _RAG_ROOT)


def _import_rag_modules():
    """隔离导入 RAG 模块，避免 config 冲突"""
    saved_cwd = os.getcwd()
    conflicted_keys = {
        k for k in sys.modules
        if k.startswith(("config", "embedding", "vector_db", "chunkers", "loaders"))
    }
    conflicted = {k: sys.modules.pop(k) for k in conflicted_keys if k in sys.modules}
    saved_path = list(sys.path)
    sys.path.insert(0, _RAG_ROOT)
    try:
        from config import AppConfig, ChunkConfig, EmbeddingConfig, RetrievalConfig, VectorStoreConfig
        from embedding.embedder import Embedder
        from vector_db.search_db import VectorStore
        return (AppConfig, ChunkConfig, EmbeddingConfig, RetrievalConfig,
                VectorStoreConfig, Embedder, VectorStore)
    finally:
        sys.path.clear()
        sys.path.extend(saved_path)
        for k, v in conflicted.items():
            sys.modules[k] = v
        os.chdir(saved_cwd)


# ── 全局单例 ──────────────────────────────────────────────────
_rag_store = None


def _get_store():
    """懒初始化 VectorStore（首次调用时加载模型）"""
    global _rag_store
    if _rag_store is not None:
        return _rag_store

    t0 = time.time()
    (AppConfig, ChunkConfig, EmbeddingConfig, RetrievalConfig,
     VectorStoreConfig, Embedder, VectorStore) = _import_rag_modules()

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    os.chdir(root)
    cfg = AppConfig(
        chunk=ChunkConfig(size=600, overlap=80),
        embedding=EmbeddingConfig(model_name="BAAI/bge-small-zh-v1.5", device="cpu"),
        retrieval=RetrievalConfig(n_results=3),
        vector_store=VectorStoreConfig(persist_dir="RAG/chroma_db", collection_name="iResearch_Report"),
        pdf_files=(),
    )
    cfg.resolve(root)
    embedder = Embedder(cfg.embedding.model_name, cfg.embedding.device)
    _rag_store = VectorStore(
        persist_dir=cfg.vector_store.persist_dir,
        collection_name=cfg.vector_store.collection_name,
        embedder=embedder,
    )
    logger.info("RAG 引擎初始化完成 (%.2fs)", time.time() - t0)
    return _rag_store


# ═══════════════════════════════════════════════════════════════
#  Tool 定义
# ═══════════════════════════════════════════════════════════════


@tool
def rag_search(query: str) -> str:
    """【内部知识库检索】从内部研究报告 PDF 中搜索相关信息并生成回答。

可用报告：
  - 艾瑞咨询：2025年中国企业级AI应用行业研究报告
  - 艾瑞咨询：AI时代下的金融科技发展洞察报告（2026）

适用场景：
  - AI行业 / 金融科技行业的市场规模、趋势、竞品格局查询
  - AI智能体（Agent）、企业级AI应用的相关信息
  - 我分析的产品如果属于 AI / 金融科技赛道，可以先查一下有无行业背景信息

此工具包含完整 RAG 流程：检索知识库 → 基于检索结果用大模型生成回答。
返回：生成式回答及引用文档片段。

用法示例：rag_search(query="2025年企业级AI市场规模")

Args:
    query: 查询问题（自然语言）"""
    query_display = query[:80]
    logger.info("rag_search 被调用，query=%s", query_display)
    print(f"  [RAG] 🔍 检索: {query_display}...")
    try:
        store = _get_store()
    except Exception as e:
        logger.warning("知识库引擎初始化失败: %s", e)
        print(f"  [RAG] ❌ 知识库引擎初始化失败: {e}")
        return f"[RAG] 知识库引擎初始化失败: {e}"

    results = store.search(query, n_results=3)
    if not results:
        print(f"  [RAG] ⚠️ 未找到相关结果: {query_display}")
        return "[RAG] 知识库中未找到相关信息"

    print(f"  [RAG] ✅ 检索到 {len(results)} 条相关文档")

    context = "\n".join(f"[{i+1}] {r.content}" for i, r in enumerate(results))

    prompt = f"""你是一个基于知识库的问答助手。请根据以下参考文档回答问题。
如果参考文档中没有相关信息，请如实说"我无法从已有文档中找到相关信息"，不要编造。

参考文档：
{context}

问题：{query}"""

    print(f"  [RAG] 🤖 调用 DeepSeek 生成回答...")
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
            base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        )
        resp = client.chat.completions.create(
            model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1024,
        )
        answer = resp.choices[0].message.content.strip()
        print(f"  [RAG] ✅ 回答生成完成 ({len(answer)} 字)")
    except Exception as e:
        answer = f"生成回答失败: {e}"
        print(f"  [RAG] ❌ 回答生成失败: {e}")

    print(f"  [RAG] 💬 回答摘要: {answer[:120]}...")
    return f"[RAG回答]\n{answer}\n\n[引用文档]\n{context}"


# ── 快捷引用 ──────────────────────────────────────────────────
rag_search_tool = rag_search
