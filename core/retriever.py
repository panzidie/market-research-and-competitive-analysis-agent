import uuid
from pathlib import Path
from typing import Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from core.tracer import logger


class Retriever:
    """文档检索器：TF-IDF 向量化 + Qdrant 本地持久化 + 多路召回"""

    def __init__(self, collection_name: str = "competitor_docs", embedding_dim: int = 768):
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
        self._vector_store_path = Path("data/vector_store")
        self._vector_store_path.mkdir(parents=True, exist_ok=True)

        # Qdrant 本地持久化
        self._qdrant = QdrantClient(path=str(self._vector_store_path))

        # TF-IDF 向量器（中文支持：字符级 n-gram 1~3）
        self._vectorizer = TfidfVectorizer(
            analyzer="char",
            ngram_range=(1, 3),
            max_features=embedding_dim,
            lowercase=False,
        )
        self._fitted = False
        self._all_texts: list[str] = []
        self._all_metadata: list[dict] = []

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
        """将文本按语义边界分块（优先在段落/句号处断开）"""
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            if end >= len(text):
                chunks.append(text[start:].strip())
                break
            candidate = text[start:end]
            last_period = candidate.rfind("。")
            if last_period > chunk_size // 2:
                end = start + last_period + 1
            else:
                last_newline = candidate.rfind("\n")
                if last_newline > chunk_size // 3:
                    end = start + last_newline + 1
            chunks.append(text[start:end].strip())
            start = end - overlap
        return [c for c in chunks if c]

    def _ensure_fitted(self):
        """懒加载：首次检索/添加时拟合 TF-IDF 向量化器"""
        if self._fitted:
            return
        all_docs = self._all_texts[:]
        if not all_docs:
            all_docs = ["空文档占位"]
        self._vectorizer.fit(all_docs)
        self._fitted = True

    def _texts_to_vectors(self, texts: list[str]) -> np.ndarray:
        """将文本转为 TF-IDF 向量，补齐到 embedding_dim 维度"""
        self._ensure_fitted()
        vecs = self._vectorizer.transform(texts).toarray()
        if vecs.shape[1] < self.embedding_dim:
            padded = np.zeros((vecs.shape[0], self.embedding_dim), dtype=np.float32)
            padded[:, :vecs.shape[1]] = vecs
            vecs = padded
        elif vecs.shape[1] > self.embedding_dim:
            vecs = vecs[:, :self.embedding_dim]
        return vecs.astype(np.float32)

    def _init_collection(self):
        """初始化 Qdrant collection（不存在时创建）"""
        if not self._qdrant.collection_exists(self.collection_name):
            self._qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=Distance.COSINE,
                ),
            )

    def _recreate_collection(self):
        """强制重建 collection（绕过内部缓存不一致问题）"""
        self._qdrant.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.embedding_dim,
                distance=Distance.COSINE,
            ),
        )

    def add_documents(self, texts: list[str], metadata: Optional[list[dict]] = None):
        """添加文档到向量库"""
        if not texts:
            return

        if metadata is None:
            metadata = [{}] * len(texts)

        self._all_texts.extend(texts)
        self._all_metadata.extend(metadata)
        self._fitted = False

        vectors = self._texts_to_vectors(texts)
        self._init_collection()

        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vectors[i].tolist(),
                payload={"text": texts[i], **metadata[i]},
            )
            for i in range(len(texts))
        ]

        self._qdrant.upsert(collection_name=self.collection_name, points=points)
        logger.info(f"已添加 {len(texts)} 条文档到向量库 (collection={self.collection_name})")

    def search(
        self,
        query: str,
        top_k: int = 5,
        use_keyword: bool = True,
    ) -> list[dict]:
        """多路召回：向量语义检索 + 关键词匹配融合"""
        if not self._all_texts:
            return []

        query_vec = self._texts_to_vectors([query])[0].tolist()
        vector_results = self._qdrant.query_points(
            collection_name=self.collection_name,
            query=query_vec,
            limit=top_k * 2,
        )

        candidates = []
        for p in vector_results.points:
            candidates.append({
                "text": p.payload.get("text", ""),
                "score": p.score,
                "metadata": {k: v for k, v in p.payload.items() if k != "text"},
            })

        if use_keyword:
            query_terms = set(query)
            for c in candidates:
                text_terms = set(c["text"])
                overlap = len(query_terms & text_terms)
                if overlap > 0:
                    c["score"] = (c["score"] or 0) + 0.1 * overlap / len(query_terms)

        seen = set()
        merged = []
        for c in sorted(candidates, key=lambda x: x.get("score", 0), reverse=True):
            key = c["text"][:50]
            if key not in seen:
                seen.add(key)
                merged.append(c)

        return merged[:top_k]

    def _recreate_client(self):
        """关闭旧客户端并重新打开，确保内部缓存刷新"""
        self._qdrant.close()
        self._qdrant = QdrantClient(path=str(self._vector_store_path))

    def rebuild_index(self):
        """重建索引：滚动删除全部旧点后重新写入"""
        if not self._all_texts:
            return

        self._fitted = False
        self._vectorizer = TfidfVectorizer(
            analyzer="char",
            ngram_range=(1, 3),
            max_features=self.embedding_dim,
            lowercase=False,
        )

        # 滚动删除所有已有记录（不重建 collection，避免文件锁问题）
        if self._qdrant.collection_exists(self.collection_name):
            while True:
                records, offset = self._qdrant.scroll(
                    collection_name=self.collection_name,
                    limit=1000,
                    with_payload=False,
                    with_vectors=False,
                )
                if not records:
                    break
                ids = [r.id for r in records]
                self._qdrant.delete(collection_name=self.collection_name, points_selector=ids)

        self._init_collection()

        vectors = self._texts_to_vectors(self._all_texts)
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vectors[i].tolist(),
                payload={"text": self._all_texts[i], **self._all_metadata[i]},
            )
            for i in range(len(self._all_texts))
        ]
        self._qdrant.upsert(collection_name=self.collection_name, points=points)
        logger.info(f"索引重建完成: {len(points)} 条文档")

    def get_document_count(self) -> int:
        if not self._qdrant.collection_exists(self.collection_name):
            return 0
        return self._qdrant.count(collection_name=self.collection_name).count

    def close(self):
        self._qdrant.close()
