# -*- coding: utf-8 -*-
"""
core/search_client.py — 搜索客户端

支持两种搜索后端：
  - 百度AI搜索（baidu_search_v2）
  - Tavily AI Search（tavily）

默认走 config.SEARCH_PROVIDER，可通过环境变量 SEARCH_PROVIDER 切换。
"""

import json
import time

import requests

import config


class SearchClient:
    """搜索客户端：自动多后端降级（Tavily → UAPI → 百度），无需手动切换 Provider。"""

    def __init__(
        self,
        provider: str = config.SEARCH_PROVIDER,
        baidu_api_key: str = config.BAIDU_SEARCH_API_KEY,
        baidu_base_url: str = config.BAIDU_SEARCH_URL,
        baidu_search_source: str = config.BAIDU_SEARCH_SOURCE,
        baidu_recency: str = config.BAIDU_SEARCH_RECENCY,
        baidu_max_results: int = config.BAIDU_MAX_RESULTS,
        tavily_api_key: str = config.TAVILY_API_KEY,
        tavily_base_url: str = config.TAVILY_BASE_URL,
        tavily_depth: str = config.TAVILY_SEARCH_DEPTH,
        tavily_max_results: int = config.TAVILY_MAX_RESULTS,
        tavily_include_answer: bool = config.TAVILY_INCLUDE_ANSWER,
        uapi_api_key: str = config.UAPI_API_KEY,
        uapi_base_url: str = config.UAPI_BASE_URL,
        uapi_max_results: int = config.UAPI_MAX_RESULTS,
    ):
        self.provider = provider.lower().strip()

        # 百度相关配置
        self.baidu_api_key = baidu_api_key
        self.baidu_base_url = baidu_base_url
        self.baidu_search_source = baidu_search_source
        self.baidu_recency = baidu_recency
        self.baidu_max_results = baidu_max_results

        # Tavily 相关配置
        self.tavily_api_key = tavily_api_key
        self.tavily_base_url = tavily_base_url.rstrip("/")
        self.tavily_depth = tavily_depth
        self.tavily_max_results = tavily_max_results
        self.tavily_include_answer = tavily_include_answer

        # UAPI 相关配置
        self.uapi_api_key = uapi_api_key
        self.uapi_base_url = uapi_base_url.rstrip("/")
        self.uapi_max_results = uapi_max_results

        # 搜索后端降级顺序（主后端优先，后续按可靠性排序）
        self._fallback_order = {
            "tavily": ["uapi", "baidu"],
            "baidu": ["uapi", "tavily"],
            "uapi": ["tavily", "baidu"],
        }

    def search(self, query: str, recency: str | None = None, fallback: bool = True) -> dict:
        """执行一次搜索查询，自动多后端降级。

        尝试顺序（以 provider=tavily 为例）：
          tavily → uapi → baidu
          任一后端成功即返回，全部失败则抛出异常。

        Args:
            query: 搜索关键词
            recency: 时间过滤（仅百度有效）
            fallback: 是否启用自动降级（默认 True）

        Returns:
            搜索结果的原始响应字典
        """
        if not fallback:
            return self._search_by_provider(self.provider, query, recency)

        # 构建降级链
        chain = [self.provider]
        for p in self._fallback_order.get(self.provider, ["tavily", "baidu", "uapi"]):
            if p not in chain:
                chain.append(p)

        errors = []
        for provider in chain:
            try:
                result = self._search_by_provider(provider, query, recency)
                if provider != self.provider:
                    print(f"  [SearchClient] {self.provider} 失败 → {provider} 成功")
                return result
            except Exception as e:
                errors.append(f"{provider}: {e}")
                continue

        raise RuntimeError(
            f"所有搜索后端均失败 ({len(chain)} 个): {'; '.join(errors)}"
        )

    def _search_by_provider(self, provider: str, query: str,
                            recency: str | None = None) -> dict:
        """按指定的后端执行搜索"""
        if provider == "tavily":
            return self._search_tavily(query)
        elif provider == "baidu":
            return self._search_baidu(query, recency)
        elif provider == "uapi":
            return self._search_uapi(query)
        else:
            raise ValueError(f"未知搜索后端: {provider}")

    def _search_baidu(self, query: str, recency: str | None = None) -> dict:
        """调用百度千帆 AI 搜索。"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.baidu_api_key}",
        }

        payload = json.dumps(
            {
                "messages": [{"role": "user", "content": query}],
                "edition": "standard",
                "search_source": self.baidu_search_source,
                "search_recency_filter": recency or self.baidu_recency,
            },
            ensure_ascii=False,
        )

        resp = requests.post(
            self.baidu_base_url,
            headers=headers,
            data=payload.encode("utf-8"),
            timeout=60,
        )
        resp.encoding = "utf-8"
        resp.raise_for_status()
        result = resp.json()

        # 限制返回结果条数
        if "references" in result:
            result["references"] = result["references"][:self.baidu_max_results]
        return result

    def _search_tavily(self, query: str) -> dict:
        """调用 Tavily AI Search。"""
        if not self.tavily_api_key:
            raise ValueError("TAVILY_API_KEY 未配置")

        url = f"{self.tavily_base_url}/search"
        payload = {
            "api_key": self.tavily_api_key,
            "query": query,
            "search_depth": self.tavily_depth,
            "include_answer": self.tavily_include_answer,
            "max_results": self.tavily_max_results,
        }

        resp = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
        resp.encoding = "utf-8"
        resp.raise_for_status()
        return resp.json()

    def _search_uapi(self, query: str) -> dict:
        """调用 UAPI 智能搜索（多源聚合）。"""
        if not self.uapi_api_key:
            raise ValueError("UAPI_API_KEY 未配置")

        url = f"{self.uapi_base_url}/api/v1/search/aggregate"
        headers = {
            "Authorization": f"Bearer {self.uapi_api_key}",
            "Content-Type": "application/json",
        }
        payload = {"query": query, "engines": ["web"]}

        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        result = resp.json()

        # 统一返回格式，使之与 Tavily 的 extract_text/extract_links 兼容
        results_list = result.get("results", [])[:self.uapi_max_results]
        formatted = {
            "results": [],
            "total_results": result.get("total_results", 0),
        }
        for item in results_list:
            formatted["results"].append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("snippet", ""),
                "source": item.get("source", ""),
            })
        return formatted

    def batch_search(self, queries: list[str],
                     delay: float = config.SEARCH_DELAY_SECONDS) -> list[dict]:
        """批量搜索，逐条调用并附带间隔，避免限流。"""
        results = []
        total = len(queries)
        for i, q in enumerate(queries):
            print(f"  [SearchClient:{self.provider}] 搜索 {i+1}/{total}: {q[:50]}...")
            try:
                result = self.search(q)
                results.append({"query": q, "result": result})
            except Exception as e:
                print(f"  [SearchClient:{self.provider}] 搜索失败: {q[:50]}... | 错误: {e}")
                results.append({"query": q, "result": None, "error": str(e)})
            if i < total - 1:
                time.sleep(delay)
        return results

    @staticmethod
    def extract_text(search_result: dict) -> str:
        """从搜索结果结构中提取纯文本内容。兼容百度与 Tavily。"""
        if not search_result:
            return ""

        texts = []

        # Tavily 专属：answer + results
        if "answer" in search_result:
            answer = search_result.get("answer")
            if isinstance(answer, str) and answer:
                texts.append(answer)

        if "results" in search_result:
            for sr in search_result.get("results", []):
                title = sr.get("title", "")
                snippet = sr.get("content", "") or sr.get("snippet", "")
                if title or snippet:
                    url = sr.get("url", "")
                    url_line = f"\n    链接: {url}" if url else ""
                    texts.append(f"【{title}】{snippet}{url_line}")
            return "\n".join(texts)

        # 百度 AI 搜索：提取AI摘要
        choices = search_result.get("choices", [])
        for choice in choices:
            message = choice.get("message", {})
            content = message.get("content", "")
            if isinstance(content, str) and content:
                texts.append(content)
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        text = item.get("text", "")
                        if text:
                            texts.append(text)
                    elif isinstance(item, str):
                        texts.append(item)

        # 百度 AI 搜索：提取搜索结果片段
        search_results = search_result.get("references", [])
        for sr in search_results:
            title = sr.get("title", "")
            snippet = sr.get("content", "") or sr.get("snippet", "")
            if title or snippet:
                url = sr.get("url", "")
                url_line = f"\n    链接: {url}" if url else ""
                texts.append(f"【{title}】{snippet}{url_line}")

        return "\n".join(texts)

    @staticmethod
    def extract_links(search_result: dict) -> list[dict]:
        """从搜索结果中提取来源链接（标题 + URL），兼容百度与 Tavily。"""
        if not search_result:
            return []

        links = []

        # Tavily: results 数组中每个条目都有 url 字段
        if "results" in search_result:
            for sr in search_result.get("results", []):
                url = sr.get("url", "")
                if url:
                    links.append({
                        "title": sr.get("title", ""),
                        "url": url,
                    })
            return links

        # 百度 AI 搜索: references 数组中每条都有 url 字段
        references = search_result.get("references", [])
        for sr in references:
            url = sr.get("url", "")
            if url:
                links.append({
                    "title": sr.get("title", ""),
                    "url": url,
                })

        return links
