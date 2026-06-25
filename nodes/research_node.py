import json
import os
from datetime import datetime
from typing import Any, Dict

from core.state import AgentState
from core.tracer import logger
from tools import search_competitor_info, scrape_website


def research_node(state: AgentState) -> Dict[str, Any]:
    """节点1：搜索与抓取竞品信息，保存原始数据到 data/raw/"""
    competitor = state.get("competitor_name", "")
    security = state.get("security")

    # 安全检查: 校验输入
    if security:
        if not security.validate_all(competitor, tool_name="search_competitor_info"):
            return {
                "error_count": state.get("error_count", 0) + 1,
                "messages": [{"role": "system", "content": "安全检查失败: 输入包含危险内容"}],
            }
    if not competitor:
        return {"error_count": state.get("error_count", 0) + 1}

    try:
        searcher = search_competitor_info()
        search_results = searcher.search(
            query=f"{competitor} 产品 功能 定价 评测",
            max_results=10,
        )

        all_results = list(search_results)
        sources = []  # 记录所有来源

        scraper = scrape_website()
        for item in all_results[:3]:
            url = item.get("url", "")
            if url:
                content = scraper.scrape(url)
                if content:
                    item["content"] = content
                    sources.append({
                        "url": url,
                        "title": item.get("title", ""),
                        "scraped_at": datetime.now().isoformat(),
                        "content_length": len(content),
                    })
                else:
                    sources.append({
                        "url": url,
                        "title": item.get("title", ""),
                        "scraped_at": datetime.now().isoformat(),
                        "status": "scrape_failed",
                    })

        # 保存原始数据到 data/raw/
        os.makedirs("data/raw", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_file = f"data/raw/{competitor}_{timestamp}.json"
        with open(raw_file, "w", encoding="utf-8") as f:
            json.dump({
                "competitor": competitor,
                "searched_at": datetime.now().isoformat(),
                "search_query": f"{competitor} 产品 功能 定价 评测",
                "search_results": all_results,
                "scraped_sources": sources,
            }, f, ensure_ascii=False, indent=2)
        logger.info(f"原始数据已保存: {raw_file}")

        return {
            "research_results": all_results,
            "messages": [{
                "role": "system",
                "content": f"已完成对 {competitor} 的信息采集。抓取来源: {len(sources)} 个。原始数据: {raw_file}"
            }],
        }
    except Exception as e:
        return {
            "error_count": state.get("error_count", 0) + 1,
            "messages": [{"role": "system", "content": f"采集失败: {e}"}],
        }
