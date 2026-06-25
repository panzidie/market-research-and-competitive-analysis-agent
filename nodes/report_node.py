import json
import os
from datetime import datetime
from typing import Any, Dict

from config.prompt_loader import get_writer_prompt, get_competitor_matrix_template

from core.state import AgentState
from core.llm import get_llm
from core.memory import ShortTermMemory
from core.tracer import logger


def report_node(state: AgentState) -> Dict[str, Any]:
    """节点3：基于分析结果生成最终 Markdown 报告，嵌入数据来源与溯源信息"""
    competitor = state.get("competitor_name", "")
    analysis = state.get("analysis")
    research_results = state.get("research_results", [])
    messages = state.get("messages", [])

    if not analysis:
        return {"error_count": state.get("error_count", 0) + 1}

    # 收集所有数据来源
    sources_list = []
    for r in research_results:
        url = r.get("url", "")
        title = r.get("title", "")
        has_content = bool(r.get("content"))
        if url:
            sources_list.append({
                "url": url,
                "title": title,
                "scraped": has_content,
            })

    # 构建来源清单
    sources_md = "\n".join([
        f"- [{i+1}] [{s['title']}]({s['url']}) {'(已抓取全文)' if s['scraped'] else '(仅摘要)'}"
        for i, s in enumerate(sources_list)
    ]) if sources_list else "- 暂无来源记录"

    # 从 messages 中提取数据文件路径
    raw_file = ""
    processed_file = ""
    for m in messages:
        # LangGraph messages 是对象，使用属性访问
        content = getattr(m, "content", "") or getattr(m, "text", "") or ""
        if isinstance(content, list):
            content = "".join([getattr(c, "text", str(c)) for c in content])
        if "data/raw/" in content:
            raw_file = content.split("data/raw/")[-1].split("\"")[0].strip()
            raw_file = f"data/raw/{raw_file}"
        if "data/processed/" in content:
            processed_file = content.split("data/processed/")[-1].split("\"")[0].strip()
            processed_file = f"data/processed/{processed_file}"

    try:
        # 从记忆获取最近上下文
        memory = state.get("memory")
        memory_context = memory.to_prompt_context(3) if memory else ""

        llm = get_llm()
        report_content = llm.call(
            model_name="deepseek-v3",
            messages=[{
                "role": "user",
                "content": f"""{memory_context}
{get_writer_prompt()}

{get_competitor_matrix_template()}

---
根据以下分析结果，生成一篇专业的竞品分析报告（Markdown 格式）。

竞品名称: {competitor}

分析摘要:
{analysis.get('summary', '')}

请生成完整报告，要求：
1. 包含摘要、背景、功能对比、SWOT 分析、结论与建议
2. 专业、客观、数据驱动
3. 在报告末尾添加 **数据来源** 章节，列出所有引用来源
4. 使用表格展示对比信息

数据来源列表（请引用）:
{sources_md}""",
            }],
        )

        # 拼接最终报告：报告正文 + 数据溯源信息
        full_report = f"""{report_content}

---

## 数据来源与溯源

### 信息采集来源
{sources_md}

### 数据文件
| 类型 | 路径 |
|------|------|
| 原始采集数据 | `{raw_file or 'N/A'}` |
| 分析结果数据 | `{processed_file or 'N/A'}` |
| 最终报告 | `data/reports/{competitor}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md` |

### 溯源说明
- 每条数据均可在 `data/raw/` 中找到对应的原始网页和抓取内容
- 分析结果保存在 `data/processed/` 中，包含 LLM 输出的完整内容
- 用户可通过 URL 直接访问原始网页进行交叉验证

> 报告生成时间: {datetime.now().isoformat()}
"""

        os.makedirs("data/reports", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"data/reports/{competitor}_{timestamp}.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(full_report)

        # 同步保存报告元数据到 processed
        report_meta = {
            "generated_at": datetime.now().isoformat(),
            "competitor": competitor,
            "sources_count": len(sources_list),
            "sources": sources_list,
            "report_path": report_path,
            "report_length": len(full_report),
        }
        meta_path = f"data/processed/report_meta_{timestamp}.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(report_meta, f, ensure_ascii=False, indent=2)

        logger.info(f"报告已保存: {report_path}")
        logger.info(f"报告元数据已保存: {meta_path}")
        logger.info(f"数据来源: {len(sources_list)} 个")

        # 更新记忆
        if memory:
            memory.add_assistant_message(f"报告已生成: {len(full_report)} 字符, {len(sources_list)} 个来源")

        return {
            "report": full_report,
            "messages": [{
                "role": "system",
                "content": f"已完成 {competitor} 的分析报告。来源: {len(sources_list)} 个。报告: {report_path}"
            }],
        }
    except Exception as e:
        return {
            "error_count": state.get("error_count", 0) + 1,
            "messages": [{"role": "system", "content": f"报告生成失败: {e}"}],
        }
