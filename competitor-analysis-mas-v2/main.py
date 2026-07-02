#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py — 智能竞品分析多Agent系统 主入口

运行示例:
  python3 main.py "飞书"                        # 默认：LLM + 搜索
  python3 main.py --ollama "飞书"               # 切换到本机Ollama
  python3 main.py --rule "飞书"                 # 规则引擎模式（零依赖）
  python3 main.py --count 5 "飞书"              # 指定竞品数量
  python3 main.py --verbose "飞书"              # 详细模式
  python3 main.py help                          # 显示帮助
"""

import asyncio
import json
import sys
import os

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 修复 Windows 终端编码问题（GBK 无法打印 emoji）
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from core.langgraph_orchestrator import LangGraphOrchestrator
from agents.conversational_agent import ConversationalAgent
from core.memory import ConversationMemory
import config


def print_banner():
    banner = """
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║     智能竞品分析 — 多Agent协同系统                                ║
║     Intelligent Competitor Analysis MAS                          ║
║                                                                  ║
║     ◆ LangGraph编排  ◆ 串行采集  ◆ 并行分析  ◆ 差异化策略       ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
"""
    print(banner)


async def run_analysis(product_description: str,
                       use_llm: bool = True,
                       max_competitors: int = config.DEFAULT_COMPETITOR_COUNT):
    """运行竞品分析"""
    config.ENABLE_LLM = use_llm

    print_banner()
    decision_mode = "🧠 LLM智能分析" if use_llm else "📋 规则引擎分析"
    print(f"  框架: LangGraph StateGraph")
    print(f"  决策模式: {decision_mode}")
    if use_llm:
        from core.llm_client import check_llm_backend
        backend = check_llm_backend()
        provider_label = {"qianfan": "百度千帆", "ollama": "本机Ollama", "deepseek": "DeepSeek"}.get(
            backend["provider"], backend["provider"])
        print(f"  LLM后端: {provider_label}")
        print(f"  模型: {backend['model']}")
        avail_mark = "✅" if backend["available"] else "❌"
        print(f"  后端状态: {avail_mark} {backend['detail']}")
    print(f"  分析目标: {product_description}")
    print(f"  最大竞品数: {max_competitors}")
    print()

    orchestrator = LangGraphOrchestrator()
    report = await orchestrator.analyze(product_description, max_competitors)

    # 打印统计
    orchestrator.print_stats()

    # 详细信息模式
    if config.VERBOSE:
        from core.llm_client import get_llm_stats
        stats = get_llm_stats()
        print("\n📋 === 详细日志 ===")
        print(f"  竞品数量: {report.competitor_count}")
        print(f"  整体定位: {report.overall_positioning[:100]}...")
        print(f"  差异化策略: {report.differentiation_strategy[:100]}...")
        print(f"  行动项数: {len(report.action_plan)}")
        print(f"  LLM调用次数: {stats['total']} (成功: {stats['success']}, 降级: {stats['fallback']})")
        timings = orchestrator.get_timings()
        if timings:
            total = sum(timings.values())
            print(f"  总耗时: {total:.2f}s")
            for node, t in timings.items():
                print(f"    - {node}: {t:.2f}s")

    # 保存报告（仅有效报告）
    is_valid = report.competitor_count > 0 and len(report.action_plan) > 0
    if is_valid:
        report_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "output"
        )
        os.makedirs(report_dir, exist_ok=True)

        # 保存HTML报告
        html_content = orchestrator.strategy_agent.format_html_report(
            report,
            product_analysis=getattr(orchestrator, "_last_product_analysis", None),
            pricing_analysis=getattr(orchestrator, "_last_pricing_analysis", None),
            market_analysis=getattr(orchestrator, "_last_market_analysis", None),
            competitor_list=getattr(orchestrator, "_last_competitor_list", None),
            competitors_data=getattr(orchestrator, "_last_competitors_data", None),
            timings=orchestrator.get_timings(),
        )
        html_path = os.path.join(report_dir, report.product_name + "_analysis_report.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"\n💾 HTML报告已保存: {html_path}")

        # 保存JSON报告
        json_path = os.path.join(report_dir, report.product_name + "_analysis_report.json")
        report_data = {
            "product_name": report.product_name,
            "competitor_count": report.competitor_count,
            "overall_positioning": report.overall_positioning,
            "differentiation_strategy": report.differentiation_strategy,
            "action_plan": [
                {
                    "priority": ap.priority,
                    "action": ap.action,
                    "timeline": ap.timeline,
                    "expected_impact": ap.expected_impact,
                }
                for ap in report.action_plan
            ],
            "risk_assessment": report.risk_assessment,
            "product_analysis_summary": report.product_analysis_summary,
            "pricing_analysis_summary": report.pricing_analysis_summary,
            "market_analysis_summary": report.market_analysis_summary,
            "summary": report.summary,
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        print(f"💾 JSON报告: {json_path}")
    else:
        print("\n⚠️ 报告无效（可能API调用失败或分析中断），跳过文件保存")

    return report


# ═══════════════════════════════════════════════════════════════
#  聊天模式（多轮对话 + 竞品分析）
# ═══════════════════════════════════════════════════════════════


async def run_chat_mode(use_llm: bool = True):
    """运行交互式聊天模式"""
    config.ENABLE_LLM = use_llm

    print("""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║     智能竞品分析助手 — 多轮对话模式                               ║
║     Intelligent Competitor Analysis Assistant                    ║
║                                                                  ║
║     ◆ 多轮对话  ◆ 网络搜索  ◆ RAG知识库  ◆ 竞品分析             ║
║     ◆ 长期记忆（自动持久化 + 跨会话恢复）                         ║
║     ◆ 语义搜索 / 关键词搜索历史                                   ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝

  试试说 "帮我分析飞书的竞品" 或直接问我任何问题！
  输入 exit / quit / q 退出
  输入 /clear 清空对话历史
  输入 /search <关键词> 搜索历史记忆
""")

    agent = ConversationalAgent(max_turns=10)
    print(f"  决策模式: {'🧠 LLM智能模式' if use_llm else '📋 规则引擎模式'}")
    print(f"  长期记忆: SQLite + ChromaDB（跨会话持久化）")
    print()

    try:
        while True:
            try:
                user_input = input(">>> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                print("再见！")
                break

            if user_input.lower() == "/clear":
                agent.memory.clear()
                print("[记忆] 对话历史已清空\n")
                continue

            if user_input.lower().startswith("/search "):
                query = user_input[8:].strip()
                if not query:
                    print("[搜索] 请输入搜索关键词，如 /search 飞书\n")
                    continue
                print(f"[搜索] 语义搜索: {query}")
                results = agent.memory.semantic_search(query, top_k=5)
                if not results:
                    print("[搜索] 未找到相关结果\n")
                    continue
                print(f"[搜索] 找到 {len(results)} 条相关结果：")
                for i, r in enumerate(results, 1):
                    product = r.get("product_name") or r.get("doc_type", "")
                    score = r.get("adjusted_score", r.get("score", 0))
                    content = r.get("content", "")[:200]
                    print(f"  {i}. [{product}] (相关度: {score:.2f})")
                    print(f"     {content}")
                print()
                continue

            print()
            try:
                response = await agent.chat(user_input)
                print(response)
            except Exception as e:
                print(f"[错误] {e}")
            print()
    finally:
        agent.memory.close()
        print("[记忆] 会话已持久化")


if __name__ == "__main__":
    args = sys.argv[1:]

    # 解析 --rule 标志
    use_rule = "--rule" in args
    if use_rule:
        args.remove("--rule")
    use_llm = not use_rule

    # 解析 --ollama 标志
    if "--ollama" in args:
        config.LLM_PROVIDER = "ollama"
        args.remove("--ollama")

    # 解析 --product 标志（支持 --product "产品名" 或位置参数）
    product_description = None
    if "--product" in args:
        idx = args.index("--product")
        if idx + 1 < len(args):
            product_description = args[idx + 1]
            args = args[:idx] + args[idx + 2:]
        else:
            print("❌ --product 需要指定产品名")
            sys.exit(1)

    # 解析 --count / --competitors 标志
    max_competitors = config.DEFAULT_COMPETITOR_COUNT
    for flag in ("--count", "--competitors"):
        if flag in args:
            idx = args.index(flag)
            if idx + 1 < len(args):
                max_competitors = int(args[idx + 1])
                args = args[:idx] + args[idx + 2:]
            else:
                print(f"❌ {flag} 需要指定数量")
                sys.exit(1)

    # 获取产品描述（位置参数 或 --product）
    if product_description is None:
        product_description = args[0] if args else ""

    # 解析 --verbose 标志
    if "--verbose" in args:
        config.VERBOSE = True
        args.remove("--verbose")

    # ── 聊天模式（先检测，从 args 移除以免干扰位置参数解析） ──
    chat_mode = "--chat" in args
    if chat_mode:
        args.remove("--chat")

    # 帮助（支持 help / -h / --help 作为位置参数）
    help_words = ("help", "-h", "--help")
    if not product_description or product_description in help_words:
        # 显示帮助（含聊天模式说明）
        print("""
╔══════════════════════════════════════════════════════════════╗
║  智能竞品分析多Agent系统 — 运行模式                           ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  python3 main.py "产品名"              使用LLM分析           ║
║  python3 main.py --chat               交互式对话模式（推荐） ║
║  python3 main.py --chat --rule        交互模式+规则引擎      ║
║  python3 main.py --ollama "产品名"     切换到本机Ollama       ║
║  python3 main.py --rule "产品名"       规则引擎模式（零依赖） ║
║  python3 main.py --count 5 "产品名"    指定竞品数量(3~8)     ║
║  python3 main.py --product "产品名"    指定分析产品（推荐）   ║
║  python3 main.py --competitors 5 "产品名" 指定竞品数量       ║
║  python3 main.py help                 显示帮助               ║
║                                                              ║
║  交互模式（--chat）:                                          ║
║    多轮对话 + 短期记忆 + 自动意图识别                         ║
║    "帮我分析飞书的竞品" → 自动触发竞品分析管道                ║
║    "你好" → 通用对话（可使用网络搜索）                        ║
║                                                              ║
║  编排框架: LangGraph StateGraph (声明式DAG)                  ║
║                                                              ║
║  协作架构:                                                   ║
║    串行采集: 竞品发现 → 数据采集                              ║
║    并行分析: 产品分析 + 定价分析 + 市场分析                   ║
║    串行汇总: 策略建议                                        ║
║                                                              ║
║  LLM后端:                                                    ║
║    默认: DeepSeek API，失败自动降级到规则引擎                ║
║    Ollama(--ollama): 本机部署，零费用，需先ollama serve      ║
║    规则引擎(--rule): 关键词匹配+模板，零依赖                 ║
║                                                              ║
║  配置方式(config.py 或环境变量):                             ║
║    LLM_PROVIDER=deepseek|qianfan|ollama 选择LLM后端          ║
║    DEEPSEEK_API_KEY=xxx               DeepSeek API密钥       ║
║    QIANFAN_API_KEY=xxx                千帆API密钥            ║
║    OLLAMA_BASE_URL=http://...         Ollama服务地址          ║
║    OLLAMA_MODEL=qwen2.5:7b           Ollama模型名称          ║
╚══════════════════════════════════════════════════════════════╝
""")
        sys.exit(0)

    if not product_description:
        print("❌ 请提供产品描述，例如: python3 main.py --product \"飞书\"")
        print("   运行 python3 main.py help 查看帮助")
        sys.exit(1)

    # LLM模式校验
    if use_llm and not chat_mode:
        from core.llm_client import check_llm_backend
        backend = check_llm_backend()
        if not backend["available"]:
            print(f"⚠️  LLM后端不可用：{backend['detail']}")
            if backend["provider"] == "qianfan":
                print("   请设置环境变量：")
                print("     export QIANFAN_API_KEY=your_api_key")
            elif backend["provider"] == "ollama":
                print("   请确保Ollama服务已启动：")
                print("     ollama serve")
                print(f"   并拉取模型：ollama pull {config.OLLAMA_MODEL}")
            elif backend["provider"] == "deepseek":
                print("   请设置环境变量：")
                print("     export DEEPSEEK_API_KEY=your_api_key")
            print("   降级为规则引擎模式运行...\n")
            use_llm = False

    # ── 聊天模式 ──
    if chat_mode:
        # LLM 后端校验
        if use_llm:
            from core.llm_client import check_llm_backend
            backend = check_llm_backend()
            if not backend["available"]:
                print(f"⚠️  LLM后端不可用：{backend['detail']}")
                print("   降级为规则引擎模式运行...\n")
                use_llm = False
        asyncio.run(run_chat_mode(use_llm=use_llm))
        sys.exit(0)

    # 运行分析
    asyncio.run(run_analysis(product_description, use_llm=use_llm,
                              max_competitors=max_competitors))
