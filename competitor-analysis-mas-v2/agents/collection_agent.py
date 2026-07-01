# -*- coding: utf-8 -*-
"""
agents/collection_agent.py — 数据采集Agent

职责：对每个竞品，采集产品功能、定价、用户评价、市场份额等信息。

支持两种模式：
  - ReAct 模式（默认）：LLM 自主决定搜索策略，Tavily 优先，百度备用
  - 传统模式（降级）：硬编码4条搜索query → LLM汇总

LLM调用：
  - ReAct 模式：1次 ReAct循环（内含N次工具调用 + 1次最终回复）
  - 传统模式：1+N次（逐竞品汇总）
"""

from agents.base_agent import BaseAgent
from models.domain import CompetitorList, CompetitorData
from core.prompt_loader import load as load_prompts
from core.search_client import SearchClient
from core.tools import REACT_TOOLS
from core.react_agent import ReactAgent
import config
import asyncio
import time
import json


# ── ReAct 模式专用 system prompt ──

REACT_SYSTEM_PROMPT = """你是一个专业的数据采集专家，负责搜索并汇总竞品的详细信息。

## 任务
对指定的竞品，通过网络搜索收集以下七个维度的信息：
1. product_features — 核心产品功能、与竞品的差异点
2. pricing_info — 定价策略、免费/付费版本、具体价格
3. market_share — 用户量、市占率、增长趋势
4. user_reviews — 正面/负面评价关键词
5. strengths — 相比我方产品的优势
6. weaknesses — 相比我方产品的劣势
7. channels — 销售渠道、合作伙伴

## 工具使用
- web_search（通用搜索，所有搜索需求用此工具，内部自动降级）

## 搜索策略
- 可以用多组不同关键词搜索不同维度
- 如果某个维度数据不足，换角度再搜

## 自主决策原则
- 你要自己决定用什么关键词搜索、搜索几次
- 当你认为七个维度的信息都已充分收集，调用 Final Answer 返回结果
- 如果某个维度确实无法找到信息，标注"暂无公开数据"即可

## 输出格式（强制）
当你认为七个维度的信息已充分收集，或已达最大搜索次数，你必须调用 Final Answer 返回结果。
Final Answer 的内容必须是一个纯 JSON 对象（不要加 ```json ``` 包裹，不要加任何解释文字），包含以下七个字段：
{
  "product_features": "核心产品功能描述",
  "pricing_info": "定价策略描述",
  "market_share": "市场份额描述",
  "user_reviews": "用户评价描述",
  "strengths": "相比我方产品的优势",
  "weaknesses": "相比我方产品的劣势",
  "channels": "销售渠道描述"
}

重要：Final Answer 必须以 { 开头，以 } 结尾。不要输出任何 JSON 以外的内容。
"""


class CollectionAgent(BaseAgent):
    """数据采集Agent — 支持 ReAct 自主决策 + 传统模式降级"""

    def __init__(self):
        prompts = load_prompts("collection_agent")
        super().__init__(
            agent_id="CollectionAgent",
            system_prompt=prompts["system_prompt"],
        )
        self._prompt_collect = prompts["prompt_collect"]
        self.search_client = SearchClient()

        # ── ReAct 引擎（如 API 不可用则 is_available=False） ──
        self._react = ReactAgent(
            system_prompt=REACT_SYSTEM_PROMPT,
            tools=REACT_TOOLS,
            max_iterations=5,
        )
        mode = "ReAct" if self._react.is_available else "传统（无可用模型）"
        self._log(f"初始化完成 — 模式: {mode}")

    async def run(self, product_description: str,
                  competitor_list: CompetitorList) -> dict[str, CompetitorData]:
        """
        主运行逻辑：并行采集所有竞品数据

        Args:
            product_description: 用户产品描述
            competitor_list: 竞品列表

        Returns:
            dict[str, CompetitorData]: 竞品名称 → 采集数据
        """
        competitors = competitor_list.competitors
        self._log(f"[START] 开始并行采集数据，共{len(competitors)}个竞品")

        product_name = competitor_list.product_name
        phase_start = time.time()

        # 并行采集：每个竞品独立启动一个协程
        async def _collect_one(index: int, comp):
            self._log(f"   [{index+1}/{len(competitors)}] {comp.name} (并行)")
            return await self._collect_competitor(product_name, product_description, comp.name)

        tasks = [_collect_one(i, comp) for i, comp in enumerate(competitors)]
        results = await asyncio.gather(*tasks)

        result_data = {}
        for i, comp in enumerate(competitors):
            result_data[comp.name] = results[i]

        elapsed = time.time() - phase_start
        self._log(f"[DONE] 并行采集完成: {len(result_data)}个竞品, 耗时 {elapsed:.1f}s")
        return result_data

    async def _collect_competitor(self, product_name: str,
                                  product_description: str,
                                  competitor_name: str) -> CompetitorData:
        """采集单个竞品数据（ReAct 优先，降级到传统模式）"""

        # ── 路径 A: ReAct 自主决策 ──
        if config.ENABLE_LLM and self._react.is_available:
            result = await self._collect_via_react(
                product_name, product_description, competitor_name
            )
            if result is not None:
                self._log(f"   [OK] {competitor_name} ReAct 采集成功")
                return result
            self._log(f"   [WARN] {competitor_name} ReAct 失败，降级到传统模式")

        # ── 路径 B: 传统硬编码搜索 + LLM汇总 ──
        return self._collect_via_legacy(
            product_name, product_description, competitor_name
        )

    # ═══════════════════════════════════════════════════
    #  ReAct 模式
    # ═══════════════════════════════════════════════════

    async def _collect_via_react(self, product_name: str,
                                 product_description: str,
                                 competitor_name: str) -> CompetitorData | None:
        """使用 ReAct 自主决策采集竞品数据"""

        task = (
            f"请搜索竞品「{competitor_name}」的详细信息。\n\n"
            f"我方产品：{product_name}\n"
            f"我方产品描述：{product_description}\n\n"
            f"请使用工具搜索该竞品的产品功能、定价、市场份额、用户评价、"
            f"优势、劣势、销售渠道七个维度的信息。\n\n"
            f"提示：\n"
            f"1. 用 web_search 搜索，内部自动降级\n"
            f"2. 可以用多组不同关键词搜索不同维度"
        )

        # 运行 ReAct 循环
        try:
            react_result = await self._react.run(task)
        except Exception as e:
            self._log(f"   [FAIL] ReAct 执行异常: {e}")
            return None

        if react_result is None:
            return None

        final_answer = react_result.get("final_answer", "")
        if not final_answer:
            self._log(f"   [WARN] ReAct 最终回复为空")
            return None

        # 解析 JSON
        data = self._parse_react_json(final_answer)
        if not data:
            self._log(f"   [WARN] ReAct JSON 解析失败")
            return None

        # 提取搜索来源（从消息历史中提取 tool 调用结果）
        sources, links = self._extract_react_sources(react_result.get("messages", []))

        return CompetitorData(
            name=competitor_name,
            product_features=data.get("product_features", ""),
            pricing_info=data.get("pricing_info", ""),
            market_share=data.get("market_share", ""),
            user_reviews=data.get("user_reviews", ""),
            strengths=data.get("strengths", ""),
            weaknesses=data.get("weaknesses", ""),
            channels=data.get("channels", ""),
            search_sources=sources,
            search_links=links,
        )

    def _parse_react_json(self, text: str) -> dict:
        """解析 ReAct 最终回复中的 JSON"""
        # DeepSeek 经常在 JSON 前加自然语言说明，截断到第一个 {
        idx = text.find("{")
        if idx > 0:
            text = text[idx:]
        from core.llm_client import parse_llm_json
        return parse_llm_json(text)

    def _extract_react_sources(self, messages: list) -> tuple[list[str], list[dict]]:
        """从 ReAct 消息历史中提取搜索来源和链接"""
        import re
        sources = []
        links = []
        seen_urls = set()

        for msg in messages:
            if hasattr(msg, "content") and hasattr(msg, "name"):
                content = str(msg.content)
                name = getattr(msg, "name", "unknown")
                if name in ("web_search",):
                    sources.append(content[:500])
                    # 从搜索结果文本中提取 URL
                    for url in re.findall(r'https?://[^\s\)\]]+', content):
                        if url not in seen_urls:
                            seen_urls.add(url)
                            links.append({"title": "", "url": url, "query_context": "web_search"})

            # 如果消息有 additional_kwargs 中的搜索结果信息也可以提取
            # （简化处理：主要从 tool 返回中提取）

        return sources, links

    # ═══════════════════════════════════════════════════
    #  传统模式（降级路径，保持原有逻辑）
    # ═══════════════════════════════════════════════════

    def _collect_via_legacy(self, product_name: str,
                            product_description: str,
                            competitor_name: str) -> CompetitorData:
        """传统硬编码搜索 + LLM汇总（原有逻辑，作为降级路径）"""
        # 生成搜索查询
        queries = [
            f"{competitor_name} 产品功能介绍",
            f"{competitor_name} 定价 价格 收费标准",
            f"{competitor_name} 市场份额 用户量 评测",
            f"{competitor_name} vs {product_name} 对比",
        ]

        # 执行搜索
        search_results = self.search_client.batch_search(queries)

        # 提取搜索文本和来源链接
        all_text = ""
        sources = []
        all_links = []
        for sr in search_results:
            query = sr.get("query", "")
            result = sr.get("result")
            text = SearchClient.extract_text(result) if result else ""
            if text:
                all_text += f"\n--- 搜索: {query} ---\n{text[:1500]}\n"
                sources.append(text[:500])
            if result:
                links = SearchClient.extract_links(result)
                for link in links:
                    link["query_context"] = query
                all_links.extend(links)

        # LLM汇总提取
        if config.ENABLE_LLM and all_text:
            prompt = self._prompt_collect.format(
                product_name=product_name,
                product_description=product_description,
                competitor_name=competitor_name,
                search_results=all_text[:8000],
            )
            result = self.ask_llm_json(prompt, max_tokens=4096)
            if result:
                return CompetitorData(
                    name=competitor_name,
                    product_features=result.get("product_features", ""),
                    pricing_info=result.get("pricing_info", ""),
                    market_share=result.get("market_share", ""),
                    user_reviews=result.get("user_reviews", ""),
                    strengths=result.get("strengths", ""),
                    weaknesses=result.get("weaknesses", ""),
                    channels=result.get("channels", ""),
                    search_sources=sources,
                    search_links=all_links,
                )
            else:
                self._log(f"   [WARN] {competitor_name} LLM汇总失败，降级到规则引擎")

        # Fallback: 规则引擎提取
        return CompetitorData(
            name=competitor_name,
            product_features=all_text[:500] if all_text else "数据采集失败",
            search_sources=sources,
            search_links=all_links,
        )
