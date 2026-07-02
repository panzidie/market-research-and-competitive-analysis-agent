# -*- coding: utf-8 -*-
"""
core/memory.py — 对话短期记忆（deque 滑动窗口）

ConversationMemory 使用固定长度的 deque 维护最近 N 轮对话，
为 ReAct Agent 和对话式智能体提供上下文窗口。
"""

from collections import deque


class ConversationMemory:
    """对话短期记忆 — 滑动窗口

    用法:
        mem = ConversationMemory(max_turns=10)
        mem.add("user", "你好")
        mem.add("assistant", "你好！有什么可以帮助你的？")
        for role, content in mem.to_messages():
            print(f"{role}: {content}")
    """

    def __init__(self, max_turns: int = 10):
        self._messages: deque[tuple[str, str]] = deque(maxlen=max(max_turns * 2, 2))

    @property
    def turn_count(self) -> int:
        """当前对话轮数（一对 user+assistant 算一轮）"""
        return len(self._messages) // 2

    def add(self, role: str, content: str):
        """添加一条消息

        Args:
            role: "user" 或 "assistant"
            content: 消息文本
        """
        self._messages.append((role, content))

    def to_messages(self) -> list[tuple[str, str]]:
        """返回所有消息列表，每项为 (role, content) 元组"""
        return list(self._messages)

    def format_for_prompt(self) -> str:
        """格式化为供 LLM prompt 使用的文本"""
        lines = []
        for role, content in self._messages:
            prefix = "用户" if role == "user" else "助手"
            lines.append(f"{prefix}: {content}")
        return "\n".join(lines)

    def clear(self):
        """清空所有消息"""
        self._messages.clear()

    def close(self):
        """释放资源（兼容 LongTermMemory 接口，短期记忆无外部资源）"""
        pass
