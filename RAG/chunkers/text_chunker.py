"""文本切片器"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """单个文本切片"""
    content: str
    char_start: int
    char_end: int
    chunk_index: int
    source: str = ""


@dataclass
class ChunkResult:
    """切片结果"""
    chunks: List[Chunk] = field(default_factory=list)
    total_chunks: int = 0


class TextChunker:
    """固定窗口文本切片器（带重叠窗口）"""

    def __init__(self, chunk_size: int = 300, overlap: int = 50) -> None:
        if overlap >= chunk_size:
            raise ValueError(f"overlap({overlap}) 必须小于 chunk_size({chunk_size})")
        if chunk_size <= 0:
            raise ValueError(f"chunk_size 必须大于 0")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def split(self, text: str) -> List[Chunk]:
        """将文本切分为多个 Chunk"""
        text = text.strip()
        if not text:
            return []

        chunks: List[Chunk] = []
        start = 0
        step = self.chunk_size - self.overlap
        index = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            content = text[start:end].strip()
            if content:
                chunks.append(Chunk(
                    content=content,
                    char_start=start,
                    char_end=end,
                    chunk_index=index,
                ))
            if end >= len(text):
                break
            start += step
            index += 1

        logger.debug("文本切片完成: %d chunks (size=%d, overlap=%d)", len(chunks), self.chunk_size, self.overlap)
        return chunks

    def split_with_source(self, text: str, source: str) -> ChunkResult:
        """切片并附带来源信息"""
        chunks = self.split(text)
        for c in chunks:
            c.source = source
        return ChunkResult(chunks=chunks, total_chunks=len(chunks))
