"""向量数据库服务层"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.api import Collection

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
    """ChromaDB 向量数据库封装"""

    def __init__(
        self,
        persist_dir: str,
        collection_name: str,
        embedder: Embedder,
    ) -> None:
        self._embedder = embedder
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._collection: Optional[Collection] = None
        self._collection_name = collection_name

    @property
    def collection(self) -> Collection:
        if self._collection is None:
            self._collection = self._client.get_or_create_collection(self._collection_name)
        return self._collection

    def add_documents(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, str]]] = None,
    ) -> int:
        """将文本及其向量表示存入向量库"""
        logger.info("开始入库: %d 条记录", len(texts))

        embeddings = self._embedder.encode(texts)
        ids = [f"doc_{i}" for i in range(len(texts))]
        if metadatas is None:
            metadatas = [{} for _ in texts]

        self.collection.add(
            documents=texts,
            embeddings=[e.tolist() for e in embeddings],
            ids=ids,
            metadatas=metadatas,
        )

        logger.info("入库完成: 共 %d 条记录", len(texts))
        return len(texts)

    def search(self, query: str, n_results: int = 3) -> List[SearchResult]:
        """语义检索：输入自然语言查询，返回最相关片段"""
        query_vec = self._embedder.encode_query(query)

        results = self.collection.query(
            query_embeddings=[query_vec.tolist()],
            n_results=n_results,
        )

        if not results["documents"] or not results["documents"][0]:
            return []

        parsed: List[SearchResult] = []
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            # ChromaDB 默认按距离升序排列，用 1/(1+distance) 近似得分
            distance = results["distances"][0][i] if results.get("distances") else 0.0
            score = 1.0 / (1.0 + distance)

            parsed.append(SearchResult(
                content=doc,
                source=meta.get("source", "unknown"),
                score=round(score, 4),
                metadata=meta,
            ))

        return parsed

    def delete_collection(self) -> None:
        """删除当前集合"""
        try:
            self._client.delete_collection(self._collection_name)
        except Exception:
            logger.warning("集合 %s 不存在，跳过删除", self._collection_name)
        self._collection = None
