import os
from typing import Optional

from tavily import TavilyClient


class SearchCompetitorInfo:
    """封装 Tavily API 进行竞品搜索"""

    def __init__(self):
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY 未设置")
        self.client = TavilyClient(api_key=api_key)

    def search(self, query: str, max_results: int = 10) -> list[dict]:
        """搜索竞品信息"""
        response = self.client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_answer=True,
        )
        results = []
        for item in response.get("results", []):
            results.append({
                "source": "tavily",
                "title": item.get("title", ""),
                "content": item.get("content", ""),
                "url": item.get("url", ""),
                "date": item.get("published_date", None),
            })
        return results


search_competitor_info = SearchCompetitorInfo
