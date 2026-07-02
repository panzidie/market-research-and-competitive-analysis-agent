"""Embedding 向量化模块"""
from __future__ import annotations

import logging
from typing import List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class Embedder:
    """文本向量化器"""

    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5", device: str = "cpu") -> None:
        logger.info("加载 Embedding 模型: %s (device=%s)", model_name, device)

        # 抑制 SentenceTransformer 加载时的进度条和 load report 输出
        import os as _os
        _os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
        _os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
        import logging as _logging
        for _name in ("transformers", "sentence_transformers", "tokenizers"):
            _logging.getLogger(_name).setLevel(_logging.ERROR)

        self.model = SentenceTransformer(model_name, device=device)
        self._dimension: Optional[int] = None

    @property
    def dimension(self) -> int:
        """返回向量维度"""
        if self._dimension is None:
            self._dimension = self.model.get_sentence_embedding_dimension()
        return self._dimension

    def encode(self, texts: List[str]) -> np.ndarray:
        """将文本列表编码为向量矩阵"""
        if not texts:
            return np.array([], dtype=np.float32)
        logger.debug("编码 %d 条文本...", len(texts))
        return self.model.encode(texts, show_progress_bar=False)

    def encode_query(self, query: str) -> np.ndarray:
        """将单条查询编码为向量"""
        return self.encode([query])[0]
