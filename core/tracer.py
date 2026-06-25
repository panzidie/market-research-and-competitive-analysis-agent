import logging
import sys
from pathlib import Path

# LangSmith 追踪初始化（骨架）
# 设置 LANGSMITH_API_KEY 和 LANGSMITH_PROJECT 环境变量后自动启用


def setup_tracing():
    """初始化 LangSmith 链路追踪"""
    from datetime import datetime

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_dir / f"agent_{datetime.now():%Y%m%d}.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    return logging.getLogger("competitor_agent")


logger = setup_tracing()
