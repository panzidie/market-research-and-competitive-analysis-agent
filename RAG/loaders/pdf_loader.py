"""PDF 文档加载器"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

from pypdf import PdfReader

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """加载后的文档"""
    text: str
    source: str
    title: str = ""
    total_pages: int = 0
    char_count: int = 0


class PdfLoader:
    """PDF 文件加载器"""

    def __init__(self) -> None:
        self._reader: Optional[PdfReader] = None

    def load(self, pdf_path: str) -> Document:
        """加载 PDF 文件，返回文档对象"""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")

        self._reader = PdfReader(pdf_path)
        texts: list[str] = []

        logger.info("加载 PDF: %s（共 %d 页）", os.path.basename(pdf_path), len(self._reader.pages))

        for _, page in enumerate(self._reader.pages):
            text = page.extract_text()
            if text and text.strip():
                texts.append(text.strip())

        full_text = "\n".join(texts)
        meta = self._reader.metadata
        title = meta.get("/Title", os.path.splitext(os.path.basename(pdf_path))[0]) if meta else os.path.splitext(os.path.basename(pdf_path))[0]

        logger.info("提取完成: %d 字符, %d 页有内容", len(full_text), len(texts))

        return Document(
            text=full_text,
            source=os.path.basename(pdf_path),
            title=title,
            total_pages=len(self._reader.pages),
            char_count=len(full_text),
        )
