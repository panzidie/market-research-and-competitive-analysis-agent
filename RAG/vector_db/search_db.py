"""向量数据库服务层（NumPy原生实现，无需ChromaDB）"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from embedding.embedder import Embedder

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """检索结果"""
    content: str
    source: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class VectorStore:
    """基于NumPy与JSON持久化的向量数据库封装"""

    def __init__(
        self,
        persist_dir: str,
        collection_name: str,
        embedder: Embedder,
    ) -> None:
        self._embedder = embedder
        self._persist_dir = persist_dir
        self._collection_name = collection_name
        self._data_path = os.path.join(persist_dir, f"{collection_name}.json")
        os.makedirs(persist_dir, exist_ok=True)

        self._texts: list[str] = []
        self._metadatas: list[dict[str, str]] = []
        self._embeddings: Optional[np.ndarray] = None
        self._load()

    def _load(self) -> None:
        """从磁盘恢复数据"""
        if not os.path.exists(self._data_path):
            return
        with open(self._data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._texts = data["texts"]
        self._metadatas = data["metadatas"]
        if data.get("embeddings"):
            self._embeddings = np.array(data["embeddings"], dtype=np.float32)
        logger.info("已恢复集合 %s: %d 条记录", self._collection_name, len(self._texts))

    def _save(self) -> None:
        """持久化到磁盘"""
        embeddings_list = self._embeddings.tolist() if self._embeddings is not None else []
        with open(self._data_path, "w", encoding="utf-8") as f:
            json.dump({
                "texts": self._texts,
                "metadatas": self._metadatas,
                "embeddings": embeddings_list,
            }, f, ensure_ascii=False)

    def add_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, str]]] = None,
    ) -> int:
        """将文本及其向量表示存入向量库"""
        if not texts:
            return 0
        logger.info("开始入库: %d 条记录", len(texts))

        embeddings = self._embedder.encode(texts)
        if self._embeddings is None:
            self._embeddings = embeddings.astype(np.float32)
        else:
            self._embeddings = np.vstack([self._embeddings, embeddings.astype(np.float32)])

        self._texts.extend(texts)
        if metadatas is None:
            metadatas = [{}] * len(texts)
        self._metadatas.extend(metadatas)

        self._save()
        logger.info("入库完成: 共 %d 条记录", len(self._texts))
        return len(texts)

    def search(self, query: str, n_results: int = 3) -> List[SearchResult]:
        """语义检索：输入自然语言查询，返回最相关片段（余弦相似度）"""
        if self._embeddings is None or len(self._texts) == 0:
            return []

        query_vec = self._embedder.encode_query(query).astype(np.float32)

        # 余弦相似度计算
        norm = np.linalg.norm(self._embeddings, axis=1)
        q_norm = np.linalg.norm(query_vec)
        if q_norm == 0 or (norm == 0).all():
            return []

        similarities = self._embeddings @ query_vec / (norm * q_norm + 1e-10)

        top_k = min(n_results, len(similarities))
        top_indices = np.argsort(similarities)[-top_k:][::-1]

        parsed: List[SearchResult] = []
        for idx in top_indices:
            parsed.append(SearchResult(
                content=self._texts[idx],
                source=self._metadatas[idx].get("source", "unknown"),
                score=round(float(similarities[idx]), 4),
                metadata=self._metadatas[idx],
            ))
        return parsed

    def delete_collection(self) -> None:
        """删除当前集合"""
        self._texts.clear()
        self._metadatas.clear()
        self._embeddings = None
        if os.path.exists(self._data_path):
            os.remove(self._data_path)
        logger.info("集合 %s 已清空", self._collection_name)
