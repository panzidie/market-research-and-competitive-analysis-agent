"""RAG 系统配置管理"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class ChunkConfig:
    size: int = 300
    overlap: int = 50


@dataclass
class EmbeddingConfig:
    model_name: str = "BAAI/bge-small-zh-v1.5"
    device: str = "cpu"


@dataclass
class RetrievalConfig:
    n_results: int = 3


@dataclass
class VectorStoreConfig:
    persist_dir: str = "chroma_db"
    collection_name: str = "campus"


@dataclass
class AppConfig:
    chunk: ChunkConfig = field(default_factory=ChunkConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    vector_store: VectorStoreConfig = field(default_factory=VectorStoreConfig)

    data_dir: str = "data"
    # PDF 文件路径列表
    pdf_files: tuple[str, ...] = ("data/campus_manual.pdf", "data/library_rules.pdf")

    _root_dir: str = ""

    @classmethod
    def from_json(cls, path: str) -> AppConfig:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        chunk_raw = raw.get("chunk", {})
        emb_raw = raw.get("embedding", {})
        ret_raw = raw.get("retrieval", {})
        vs_raw = raw.get("vector_store", {})

        return cls(
            chunk=ChunkConfig(**chunk_raw),
            embedding=EmbeddingConfig(**emb_raw),
            retrieval=RetrievalConfig(**ret_raw),
            vector_store=VectorStoreConfig(**vs_raw),
            data_dir=raw.get("data_dir", "data"),
            pdf_files=tuple(raw.get("pdf_files", [])),
        )

    def resolve(self, root_dir: str) -> AppConfig:
        """将配置中的相对路径基于 root_dir 解析为绝对路径"""
        self._root_dir = root_dir

        def _abs(p: str) -> str:
            if not os.path.isabs(p):
                return os.path.normpath(os.path.join(root_dir, p))
            return p

        self.data_dir = _abs(self.data_dir)
        self.pdf_files = tuple(_abs(f) for f in self.pdf_files)
        self.vector_store.persist_dir = _abs(self.vector_store.persist_dir)
        return self

    @property
    def root_dir(self) -> str:
        return self._root_dir


# 默认配置（生产环境下建议使用 JSON 配置文件覆盖）
DEFAULT_CONFIG = AppConfig()
