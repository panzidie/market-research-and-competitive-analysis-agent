import os
from typing import Optional

from firecrawl import V1FirecrawlApp


class ScrapeWebsite:
    """封装 Firecrawl API 进行网页抓取"""

    def __init__(self):
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            raise ValueError("FIRECRAWL_API_KEY 未设置")
        self.client = V1FirecrawlApp(api_key=api_key)

    def scrape(self, url: str) -> Optional[str]:
        """抓取单个网页内容，返回 Markdown 文本"""
        try:
            result = self.client.scrape_url(url, formats=["markdown"])
            if hasattr(result, "markdown"):
                return result.markdown
            if isinstance(result, dict):
                return result.get("markdown") or result.get("content")
            return str(result)
        except Exception as e:
            print(f"抓取失败 {url}: {e}")
            return None

    def crawl(self, url: str, max_pages: int = 5) -> list[dict]:
        """递归爬取网站，返回多页内容"""
        try:
            result = self.client.crawl_url(url, max_pages=max_pages)
            pages = []
            if hasattr(result, "pages"):
                for page in result.pages:
                    pages.append({
                        "url": getattr(page, "url", ""),
                        "content": getattr(page, "markdown", "") or getattr(page, "content", ""),
                    })
            elif isinstance(result, dict):
                for page in result.get("data", result.get("pages", [])):
                    pages.append({
                        "url": page.get("url", ""),
                        "content": page.get("markdown") or page.get("content", ""),
                    })
            return pages
        except Exception as e:
            print(f"爬取失败 {url}: {e}")
            return []


scrape_website = ScrapeWebsite
