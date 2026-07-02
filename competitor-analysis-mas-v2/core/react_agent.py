# -*- coding: utf-8 -*-
"""
core/react_agent.py — ReAct 自主决策 Agent 引擎

基于 LangGraph 的 create_react_agent 预制件，为每个业务 Agent 提供
"思考-行动-观察"循环能力。

核心机制：
  Thought: LLM 分析当前信息，判断是否需要调用工具
  Action:  如果需要 → 选择工具 + 生成参数 → 执行工具
  Observe: 接收工具返回 → 回到 Thought
  终止:    LLM 判定信息足够 → 返回 Final Answer

架构：
  外层 DAG (不变) → 每个节点内部调用 ReactAgent.run()
  ReactAgent 内部是一个 ReAct 子图 (create_react_agent)

降级链：
  轴1 (Provider):  ChatOpenAI(DeepSeek) → ChatOpenAI(Ollama)
                    如果都不可用 → 返回 None → 调用方降级到规则引擎
  轴2 (Logic):      ReAct 成功 → 返回结果
                    ReAct 失败/无API → 降级到规则引擎 (Agent 内部)
                    max_iterations 超限 → 强制终止 → 返回中间结果
"""

from __future__ import annotations

from typing import Optional

from langgraph.prebuilt import create_react_agent
from langgraph.graph.state import CompiledStateGraph
from langchain_openai import ChatOpenAI
from langchain_core.tools import BaseTool
from langchain_core.callbacks import BaseCallbackHandler

import config


# ── 模型构建（带 Provider 降级） ──

def _build_model(temperature: float = None) -> Optional[ChatOpenAI]:
    """构建 ChatOpenAI 模型，支持 DeepSeek → Ollama 降级。

    Returns:
        ChatOpenAI 实例（带 with_fallbacks），如果所有 Provider 都不可用则返回 None。
    """
    temp = temperature if temperature is not None else config.LLM_TEMPERATURE
    models = []

    # ① DeepSeek（主后端；API 完全兼容 OpenAI tool calling）
    if config.DEEPSEEK_API_KEY:
        try:
            models.append(ChatOpenAI(
                model=config.DEEPSEEK_MODEL,
                api_key=config.DEEPSEEK_API_KEY,
                base_url=config.DEEPSEEK_BASE_URL,
                temperature=temp,
                max_tokens=config.LLM_MAX_TOKENS,
            ))
            print(f"  [ReAct] [OK] DeepSeek 模型已就绪 ({config.DEEPSEEK_MODEL})")
        except Exception as e:
            print(f"  [ReAct] [WARN] DeepSeek 模型初始化失败: {e}")

    # ② Ollama（备用后端）
    try:
        import requests as _req
        base = config.OLLAMA_BASE_URL.rstrip("/")
        resp = _req.get(f"{base}/api/tags", timeout=5)
        if resp.status_code == 200:
            models.append(ChatOpenAI(
                model=config.OLLAMA_MODEL,
                api_key="ollama",  # Ollama 不校验 key
                base_url=f"{base}/v1",
                temperature=temp,
                max_tokens=config.LLM_MAX_TOKENS,
            ))
            print(f"  [ReAct] [OK] Ollama 模型已就绪 ({config.OLLAMA_MODEL})")
    except Exception as _e:
        print(f"  [ReAct] [info] Ollama 不可用 ({type(_e).__name__})，跳过")

    if not models:
        print("  [ReAct] [FAIL] 无可用模型，ReAct 模式不可用，将降级到规则引擎")
        return None

    # 构建降级链：DeepSeek → Ollama
    if len(models) == 1:
        return models[0]
    return models[0].with_fallbacks(models[1:])

class _ThoughtEmitter(BaseCallbackHandler):
    """实时推送 ReAct 推理过程到前端"""

    def __init__(self, emitter=None, agent_name: str = "ReAct"):
        self._emitter = emitter
        self._agent_name = agent_name
        self._last_content: str = ""
        self._call_index = 0
        self._started = False

    def on_chat_model_end(self, output, **kwargs):
        """LLM 输出结束时发射事件"""
        try:
            msg = output.generations[0][0].message
            content = getattr(msg, "content", "") or ""
            tool_calls = getattr(msg, "tool_calls", []) or []

            # 工具调用：即使 content 为空也要打印
            if tool_calls:
                names = [t.get("name", "?") for t in tool_calls]
                # 用工具调用信息作为 THOUGHT 显示
                thought = content.strip() if content.strip() else f"需要查询相关信息，决定调用 {names}"
                if thought != self._last_content:
                    self._last_content = thought
                    print(f"\n  [ReAct] [THOUGHT] {thought[:200]}")
                    print(f"  [ReAct] [ACTION] → 调用工具: {names}")

                if self._emitter:
                    self._emit_safe("react_thought", {
                        "agent_name": self._agent_name, "thought": thought[:500],
                    })
                for tc in tool_calls:
                    self._call_index += 1
                    if self._emitter:
                        self._emit_safe("react_action", {
                            "agent_name": self._agent_name,
                            "tool_name": tc.get("name", "?"),
                            "tool_input": tc.get("args", {}),
                            "call_index": self._call_index,
                        })
                return

            # 纯文本回复（Final Answer 或 Thought）
            if not content.strip():
                return
            if content.strip() == self._last_content:
                return
            self._last_content = content.strip()

            print(f"\n  [ReAct] [THOUGHT] {content.strip()[:200]}")
            if self._emitter:
                self._emit_safe("react_thought", {
                    "agent_name": self._agent_name, "thought": content.strip()[:500],
                })
        except Exception:
            pass

    def on_tool_end(self, output, **kwargs):
        """工具执行结束时打印并发射 OBSERVATION 事件"""
        try:
            preview = str(output)[:300]
            tool_name = kwargs.get("name", "?")
            print(f"  [ReAct] [OBSERVE] ← {tool_name}: {preview}")
            if self._emitter:
                self._emit_safe("react_observation", {
                    "agent_name": self._agent_name,
                    "tool_name": tool_name,
                    "result_preview": preview,
                    "result_length": len(str(output)),
                    "call_index": self._call_index,
                })
        except Exception:
            pass

    def _emit_safe(self, event_type: str, payload: dict):
        """安全发射事件（同步 callback 中执行 async emit）"""
        if self._emitter:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._emitter.emit(event_type, payload))
            except Exception:
                pass


# ── ReAct Agent 封装 ──

class ReactAgent:
    """ReAct 自主决策 Agent 封装。

    每个业务 Agent（如 CollectionAgent）内嵌一个 ReactAgent 实例，
    在需要自主决策时调用 run()。

    Loop 行为:
      Thought → Action(Tool Call) → Observe → Thought → ...
      直到 LLM 返回 Final Answer 或达到 max_iterations 上限。

    用法:
        agent = ReactAgent(
            system_prompt="你是数据采集专家...",
            tools=[web_search],
            max_iterations=5,
        )
        if agent.is_available:
            result = await agent.run("请收集钉钉的产品信息")
    """

    def __init__(
        self,
        system_prompt: str,
        tools: list[BaseTool],
        max_iterations: int = 5,
        temperature: float = None,
        event_emitter=None,
    ):
        """

        Args:
            system_prompt: 系统提示词（给 LLM 的角色设定和任务说明）
            tools: 可用工具列表
            max_iterations: 最大思考-行动-观察循环次数（默认 5）
            temperature: LLM 温度（默认使用 config.LLM_TEMPERATURE）
            event_emitter: 事件发射器（用于实时推送 ReAct 推理过程）
        """
        self.system_prompt = system_prompt
        self.tools = tools
        self.max_iterations = max_iterations
        self.temperature = temperature
        self._emitter = event_emitter
        self._agent_name = "ReAct"

        # 创建模型 + 编译 ReAct 子图
        self.model = _build_model(temperature)
        self._graph: Optional[CompiledStateGraph] = None

        if self.model:
            try:
                self._graph = create_react_agent(
                    model=self.model,
                    tools=self.tools,
                    prompt=self.system_prompt,
                )
                print(f"  [ReAct] [OK] ReAct 子图已编译（max_iterations={max_iterations}）")
            except Exception as e:
                print(f"  [ReAct] [FAIL] ReAct 子图编译失败: {e}")

    @property
    def is_available(self) -> bool:
        """ReAct 模式是否可用"""
        return self._graph is not None

    async def run(self, task_message: str = None, messages: list = None) -> Optional[dict]:
        """执行 ReAct 自主决策循环。

        Args:
            task_message: 任务描述文本（作为 user message 传入 ReAct loop）
            messages: 消息列表（用于多轮对话），每个元素为 (role, content) 元组，
                      如 [("user", "你好"), ("assistant", "你好！"), ("user", "帮我搜索")]

        Returns:
            {
                "final_answer": str,   # LLM 的最终回复
                "messages": list,       # 完整的消息历史（可追溯）
                "iterations": int,      # 实际循环次数
            }
            如果 ReAct 不可用或执行失败，返回 None。
        """
        if not self._graph:
            print("  [ReAct] [WARN] ReAct 子图未就绪，跳过")
            return None

        # 构建输入消息
        if messages is not None:
            input_messages = messages
        elif task_message is not None:
            input_messages = [("user", task_message)]
        else:
            print("  [ReAct] [WARN] run() 需要 task_message 或 messages 参数")
            return None

        print(f"  [ReAct] [START] 启动 ReAct 循环 (max_iterations={self.max_iterations}, "
              f"messages={len(input_messages)}条)")

        # 发射 ReAct 开始事件
        if self._emitter:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._emitter.emit("react_started", {
                        "agent_name": self._agent_name if hasattr(self, '_agent_name') else "ReAct",
                        "task": str(input_messages[-1])[:200] if input_messages else "",
                        "max_iterations": self.max_iterations,
                    }))
            except Exception:
                pass

        # 区分 Tools（core.tools 定义）与 Skill（skill/ 包注册）
        _tool_list = []
        _skill_list = []
        for t in self.tools:
            mod = getattr(getattr(t, "func", None), "__module__", "") or ""
            if mod.startswith("skill"):
                _skill_list.append(t.name)
            else:
                _tool_list.append(t.name)
        if _tool_list:
            print(f"  [ReAct] [TOOLS] 可用工具: {_tool_list}")
        if _skill_list:
            print(f"  [ReAct] [SKILL] 可用工具: {_skill_list}")

        # 挂载 ReAct THOUGHT 回调到执行链
        _emitter_obj = _ThoughtEmitter(
            emitter=self._emitter,
            agent_name=getattr(self, '_agent_name', 'ReAct'),
        )
        _run_config = {
            "recursion_limit": self.max_iterations * 2 + 5,
            "callbacks": [_emitter_obj],
        }

        try:
            result = await self._graph.ainvoke(
                {"messages": input_messages},
                config=_run_config,
            )

            messages = result.get("messages", [])
            iterations = sum(
                1 for m in messages
                if hasattr(m, "tool_calls") and m.tool_calls
            )

            # 提取最终回复
            final_answer = ""
            for msg in reversed(messages):
                if hasattr(msg, "content") and msg.content and not hasattr(msg, "tool_calls"):
                    final_answer = msg.content
                    break
                # AIMessage 可能同时有 content 和 tool_calls，跳过有 tool_calls 的
                if hasattr(msg, "content") and msg.content:
                    if not (hasattr(msg, "tool_calls") and msg.tool_calls):
                        final_answer = msg.content
                        break

            # 报告循环完成
            print(f"  [ReAct] [DONE] 循环完成 ({iterations} 次工具调用)")
            print(f"  [ReAct] [RESULT] 最终回复长度: {len(final_answer)} 字")

            # 发射 ReAct 结束事件
            if self._emitter:
                try:
                    import asyncio as _aio
                    loop = _aio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(self._emitter.emit("react_ended", {
                            "agent_name": self._agent_name,
                            "iterations": iterations,
                            "final_answer_length": len(final_answer),
                        }))
                except Exception:
                    pass

            return {
                "final_answer": final_answer,
                "messages": messages,
                "iterations": iterations,
            }

        except Exception as e:
            error_msg = str(e)
            # GraphRecursionError 意味着达到 recursion_limit（主动终止）
            if "RecursionError" in type(e).__name__ or "recursion" in error_msg.lower():
                print(f"  [ReAct] [LIMIT] 达到最大循环次数 ({self.max_iterations})，强制终止")
                return {"final_answer": "", "messages": [], "iterations": self.max_iterations,
                        "error": "max_iterations_exceeded"}
            print(f"  [ReAct] [FAIL] ReAct 执行异常: {e}")
            return None
