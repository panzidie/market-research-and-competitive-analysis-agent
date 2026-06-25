import os
from typing import Optional

from anthropic import Anthropic
from openai import OpenAI

from config import get_config


class LLMGateway:
    """多模型 LLM 网关，支持 Claude/GPT/Qwen 路由与重试"""

    def __init__(self):
        self.config = get_config().llm
        self._clients: dict[str, object] = {}

    def _get_anthropic_client(self) -> Anthropic:
        if "anthropic" not in self._clients:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY 未设置")
            self._clients["anthropic"] = Anthropic(
                api_key=api_key,
                base_url=os.getenv("ANTHROPIC_BASE_URL"),
            )
        return self._clients["anthropic"]

    def _get_openai_client(self, base_url: Optional[str] = None) -> OpenAI:
        key = f"openai_{base_url or 'default'}"
        if key not in self._clients:
            api_key = os.getenv("OPENAI_API_KEY", "sk-placeholder")
            self._clients[key] = OpenAI(api_key=api_key, base_url=base_url)
        return self._clients[key]

    def call(self, model_name: str, messages: list, **kwargs) -> str:
        """调用指定模型并返回文本回复"""
        model_config = self.config.models.get(model_name)
        if not model_config:
            raise ValueError(f"未知模型: {model_name}")

        if model_config.provider == "anthropic":
            return self._call_anthropic(model_config, messages, **kwargs)
        elif model_config.provider == "openai":
            return self._call_openai(model_config, messages, **kwargs)
        else:
            raise ValueError(f"不支持的 provider: {model_config.provider}")

    def _call_anthropic(self, config, messages: list, **kwargs) -> str:
        client = self._get_anthropic_client()
        response = client.messages.create(
            model=config.model_id,
            max_tokens=kwargs.get("max_tokens", config.max_tokens),
            messages=messages,
        )
        return "".join(b.text for b in response.content if b.type == "text")

    def _call_openai(self, config, messages: list, **kwargs) -> str:
        client = self._get_openai_client(config.base_url)
        response = client.chat.completions.create(
            model=config.model_id,
            messages=messages,
            max_tokens=kwargs.get("max_tokens", config.max_tokens),
        )
        return response.choices[0].message.content or ""


def get_llm() -> LLMGateway:
    return LLMGateway()
