import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


class LLMModelConfig(BaseModel):
    model_config = {"protected_namespaces": ()}
    provider: str
    model_id: str
    max_tokens: int = 4096
    base_url: Optional[str] = None


class LLMConfig(BaseModel):
    default_model: str = "claude-opus-4-8"
    max_retries: int = 3
    timeout: int = 120
    temperature: float = 0.3
    models: dict[str, LLMModelConfig]


class SearchConfig(BaseModel):
    max_results: int = 10
    max_scrape_pages: int = 5
    request_timeout: int = 30


class CircuitBreakerConfig(BaseModel):
    max_error_count: int = 5
    reset_after_seconds: int = 300


class VectorStoreConfig(BaseModel):
    collection_name: str = "competitor_docs"
    embedding_dim: int = 1536
    top_k: int = 5


class AppConfig(BaseModel):
    app: dict = Field(default_factory=lambda: {"name": "竞品分析智能体", "version": "1.0.0", "debug": False})
    llm: LLMConfig
    search: SearchConfig = Field(default_factory=SearchConfig)
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    vector_store: VectorStoreConfig = Field(default_factory=VectorStoreConfig)


class ConfigLoader:
    """加载和校验 YAML 配置"""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = Path(__file__).parent / "settings.yaml"
        self.config_path = Path(config_path)

    def load(self) -> AppConfig:
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        return AppConfig(**raw)


# 全局单例
def get_config() -> AppConfig:
    return ConfigLoader().load()
