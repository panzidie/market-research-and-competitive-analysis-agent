"""RAG Pipeline 主入口

用法：
  python main.py                     # 使用默认配置，全流程运行
  python main.py --config config.json  # 从 JSON 配置文件加载
  python main.py --index-only          # 仅构建/更新索引
  python main.py --search-only         # 仅启动交互式检索
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

from chunkers.text_chunker import TextChunker
from config import AppConfig, ChunkConfig, EmbeddingConfig, RetrievalConfig, VectorStoreConfig
from embedding.embedder import Embedder
from loaders.pdf_loader import PdfLoader
from vector_db.search_db import VectorStore, SearchResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("rag")


def build_index(cfg: AppConfig) -> VectorStore:
    """构建/更新向量索引"""
    loader = PdfLoader()
    chunker = TextChunker(cfg.chunk.size, cfg.chunk.overlap)
    embedder = Embedder(cfg.embedding.model_name, cfg.embedding.device)

    store = VectorStore(
        persist_dir=cfg.vector_store.persist_dir,
        collection_name=cfg.vector_store.collection_name,
        embedder=embedder,
    )
    store.delete_collection()

    # 如果 pdf_files 为空，自动扫描 data_dir 下所有 .pdf
    pdf_files = list(cfg.pdf_files)
    if not pdf_files:
        for fname in sorted(os.listdir(cfg.data_dir)):
            if fname.lower().endswith(".pdf"):
                pdf_files.append(os.path.join(cfg.data_dir, fname))

    all_texts: list[str] = []
    all_metas: list[dict[str, str]] = []

    for pdf_path in pdf_files:
        doc = loader.load(pdf_path)
        result = chunker.split_with_source(doc.text, doc.source)

        for chunk in result.chunks:
            all_texts.append(chunk.content)
            all_metas.append({"source": doc.source})

        logger.info("%s → %d chunks", doc.source, result.total_chunks)

    store.add_documents(all_texts, all_metas)
    return store


def interactive_search(store: VectorStore, n_results: int = 3) -> None:
    """启动交互式检索"""
    print("\n====== 语义检索交互 ======")
    print("输入查询内容（输入 q 退出）\n")

    while True:
        try:
            q = input("查询 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not q:
            continue
        if q.lower() in ("q", "quit", "exit"):
            break

        results = store.search(q, n_results=n_results)

        if not results:
            print("  无匹配结果\n")
            continue

        for r in results:
            print(f"\n  [得分 {r.score:.3f}] 来自 {r.source}")
            print(f"  {r.content[:200]}")
        print()


def run_pipeline(cfg: AppConfig) -> None:
    """全流程：构建索引 → 测试检索"""
    logger.info("=" * 50)
    logger.info("RAG Pipeline 启动")
    logger.info("  Chunk: size=%d, overlap=%d", cfg.chunk.size, cfg.chunk.overlap)
    logger.info("  Embedding: %s", cfg.embedding.model_name)
    logger.info("  PDF: %s", [os.path.basename(p) for p in cfg.pdf_files])
    logger.info("=" * 50)

    # 第1步：构建索引
    store = build_index(cfg)

    # 第2步：测试检索
    test_queries = [
        "门卡丢失怎么办",
        "图书馆开放时间",
        "宿舍几点关门",
    ]

    logger.info("测试检索...")
    for q in test_queries:
        results = store.search(q, n_results=2)
        logger.info("查询「%s」→ Top1: %s (得分 %.3f)",
                     q, results[0].source if results else "无结果",
                     results[0].score if results else 0)

    logger.info("Pipeline 完成")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RAG Pipeline")
    parser.add_argument("--config", type=str, default="", help="JSON 配置文件路径")
    parser.add_argument("--index-only", action="store_true", help="仅构建/更新索引")
    parser.add_argument("--search-only", action="store_true", help="仅启动交互式检索")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv or sys.argv[1:])

    # 加载配置
    if args.config:
        cfg = AppConfig.from_json(args.config)
    else:
        cfg = AppConfig(
            chunk=ChunkConfig(size=600, overlap=80),
            embedding=EmbeddingConfig(model_name="BAAI/bge-small-zh-v1.5", device="cpu"),
            retrieval=RetrievalConfig(n_results=3),
            vector_store=VectorStoreConfig(persist_dir="chroma_db", collection_name="iResearch_Report"),
            pdf_files=(),
        )

    # 将当前文件所在目录设为 root
    root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root)
    cfg.resolve(root)

    if args.search_only:
        # 仅检索模式：需保证向量库已存在
        embedder = Embedder(cfg.embedding.model_name, cfg.embedding.device)
        store = VectorStore(
            persist_dir=cfg.vector_store.persist_dir,
            collection_name=cfg.vector_store.collection_name,
            embedder=embedder,
        )
        interactive_search(store, cfg.retrieval.n_results)
        return

    if args.index_only:
        build_index(cfg)
        logger.info("索引构建完成")
        return

    # 默认：全流程
    run_pipeline(cfg)


if __name__ == "__main__":
    main()
