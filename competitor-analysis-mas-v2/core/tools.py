# -*- coding: utf-8 -*-
"""
core/tools.py — ReAct Agent 工具定义

工具清单：
  - web_search:        通用网页搜索（自动 Tavily / UAPI / 百度多后端降级）
"""

import time

from langchain_core.tools import tool
from core.search_client import SearchClient
import config


def _call_with_retry(
    tool_name: str,
    fn,
    *args,
    retry_delay: float = 1.0,
    **kwargs,
) -> str:
    """通用重试封装：首次失败 → 延迟 → 重试 1 次。"""
    last_error = None
    for attempt in range(2):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_error = str(e)
            if attempt == 0:
                print(f"  [Tool:{tool_name}] 首次失败: {e}，{retry_delay}s 后重试...")
                time.sleep(retry_delay)
                continue
    return f"[{tool_name}] 重试1次后仍失败: {last_error}"


# ═══════════════════════════════════════════════════════════════
#  工具定义
# ═══════════════════════════════════════════════════════════════


def _do_web_search(query: str) -> str:
    """搜索实际执行逻辑"""
    if not config.TAVILY_API_KEY and not config.UAPI_API_KEY and not config.BAIDU_SEARCH_API_KEY:
        return "[搜索] 所有搜索后端均未配置 API Key"
    client = SearchClient()
    try:
        result = client.search(query)  # 内部自动降级 Tavily → UAPI → 百度
    except RuntimeError as e:
        return f"[搜索] 所有后端均失败: {e}"
    text = SearchClient.extract_text(result)
    if text:
        return f"[搜索结果]\n{text[:5000]}"
    return "[搜索] 未找到相关结果"


@tool
def web_search(query: str) -> str:
    """【首选工具】通用网页搜索。所有需要搜索信息的需求都必须优先使用此工具，不要直接编造或猜测 URL！
    适用场景：竞品信息搜索、市场数据搜索、用户评价搜索、定价搜索等。
    内部自动在多个搜索后端之间降级，保证结果返回。
    返回：搜索结果摘要及多条相关结果的标题和内容片段。

    用法示例：web_search(query="飞书 产品功能 2025")

    Args:
        query: 搜索关键词（支持中英文，尽可能具体）
    """
    return _call_with_retry("web_search", _do_web_search, query)


# ═══════════════════════════════════════════════════════════════
#  工具列表（供 ReAct Agent 注册使用）
# ═══════════════════════════════════════════════════════════════

REACT_TOOLS = [web_search]
