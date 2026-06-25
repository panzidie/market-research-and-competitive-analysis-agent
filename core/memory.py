from typing import Optional


class ShortTermMemory:
    """短期记忆：滑动窗口存储最近 N 轮对话"""

    def __init__(self, max_rounds: int = 10, max_tokens_estimate: int = 4000):
        self.max_rounds = max_rounds
        self.max_tokens_estimate = max_tokens_estimate
        self._messages: list[dict] = []

    def add_message(self, role: str, content: str):
        self._messages.append({"role": role, "content": content})
        self._trim()

    def add_user_message(self, content: str):
        self.add_message("user", content)

    def add_assistant_message(self, content: str):
        self.add_message("assistant", content)

    def add_system_message(self, content: str):
        self.add_message("system", content)

    def get_context(self, last_n: Optional[int] = None) -> list[dict]:
        """获取最近 N 轮对话"""
        n = last_n or self.max_rounds
        return self._messages[-n * 2 :]  # 每轮 = user + assistant

    def get_all(self) -> list[dict]:
        return list(self._messages)

    def clear(self):
        self._messages.clear()

    def _trim(self):
        """滑动窗口：超过 token 估算上限时裁剪最旧消息"""
        total_estimate = sum(len(m.get("content", "")) // 4 for m in self._messages)
        while total_estimate > self.max_tokens_estimate and len(self._messages) > 4:
            removed = self._messages.pop(0)
            total_estimate -= len(removed.get("content", "")) // 4

    def to_prompt_context(self, last_n: Optional[int] = None) -> str:
        """将记忆转为 prompt 可用的上下文文本"""
        msgs = self.get_context(last_n)
        if not msgs:
            return ""
        lines = ["[历史对话记录]"]
        for i, m in enumerate(msgs):
            role = m.get("role", "unknown")
            content = m.get("content", "")[:200]
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def is_empty(self) -> bool:
        return len(self._messages) == 0

    def __len__(self) -> int:
        return len(self._messages)
