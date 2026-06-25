import json
import os
from datetime import datetime
from typing import Any, Dict

from config.prompt_loader import get_analyst_prompt, get_data_extraction_template, get_swot_analysis_template

from core.state import AgentState
from core.llm import get_llm
from core.memory import ShortTermMemory
from core.tracer import logger


def extract_node(state: AgentState) -> Dict[str, Any]:
    """节点2：调用 LLM 提取结构化数据，保存分析结果到 data/processed/"""
    research_results = state.get("research_results", [])
    if not research_results:
        return {"error_count": state.get("error_count", 0) + 1}

    # 构建带来源标注的输入
    sources_summary = []
    for r in research_results:
        sources_summary.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content_snippet": (r.get("content", "") or r.get("content_snippet", ""))[:2000],
        })

    combined_text = "\n\n---\n\n".join([
        f"来源 [{i+1}]: {s['title']}\nURL: {s['url']}\n\n{s['content_snippet']}"
        for i, s in enumerate(sources_summary)
    ])

    try:
        # 从记忆获取最近上下文
        memory = state.get("memory")
        memory_context = memory.to_prompt_context(3) if memory else ""

        llm = get_llm()
        response = llm.call(
            model_name="deepseek-v3",
            messages=[{
                "role": "user",
                "content": f"""{memory_context}
{get_analyst_prompt()}

{get_data_extraction_template()}

{get_swot_analysis_template()}

---
分析以下竞品信息，每条分析结论必须标注数据来源（用 [来源N] 引用）。

{combined_text}

请输出：
1. 产品名称和所属公司
2. 核心功能列表（每项标注来源）
3. 定价信息（标注来源）
4. 目标用户画像
5. SWOT 分析（每点标注来源）
6. 优劣势总结""",
            }],
        )

        # 保存分析结果到 data/processed/
        os.makedirs("data/processed", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        processed_file = f"data/processed/analysis_{timestamp}.json"
        with open(processed_file, "w", encoding="utf-8") as f:
            json.dump({
                "analyzed_at": datetime.now().isoformat(),
                "sources": sources_summary,
                "analysis_summary": response,
            }, f, ensure_ascii=False, indent=2)
        logger.info(f"分析结果已保存: {processed_file}")

        # 更新记忆
        if memory:
            memory.add_user_message(f"分析竞品: {state.get('competitor_name', '')}")
            memory.add_assistant_message(f"分析结果已生成，长度 {len(response)} 字符")

        return {
            "analysis": {
                "summary": response,
                "feature_matrix": None,
                "swot_analysis": None,
            },
            "messages": [{"role": "system", "content": f"已完成数据分析。分析结果: {processed_file}"}],
        }
    except Exception as e:
        return {
            "error_count": state.get("error_count", 0) + 1,
            "messages": [{"role": "system", "content": f"分析失败: {e}"}],
        }
