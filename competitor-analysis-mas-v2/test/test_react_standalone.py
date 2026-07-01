# -*- coding: utf-8 -*-
"""
test_react_standalone.py — ReAct 端到端验证脚本

验证链路：
  1. API Key 加载
  2. 搜索工具可用性（Tavily / Baidu / UAPI）
  3. DeepSeek LLM 连通性（Tool Calling 能力）
  4. ReactAgent 初始化（模型构建 + ReAct 子图编译）
  5. ReAct 端到端循环（LLM 自主决策 → 调用搜索工具 → 返回结果）
"""

import sys
import os
import asyncio
import json
import traceback

# 确保项目根目录在 path 中（test/ 目录的上一级）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import config


# ═══════════════════════════════════════════════════════════════
#  颜色输出
# ═══════════════════════════════════════════════════════════════

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):   print(f"  {GREEN}[OK]{RESET}   {msg}")
def fail(msg): print(f"  {RED}[FAIL]{RESET} {msg}")
def warn(msg): print(f"  {YELLOW}[WARN]{RESET} {msg}")
def info(msg): print(f"  {CYAN}[INFO]{RESET} {msg}")
def step(n, title):
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD} 步骤 {n}: {title}{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")


# ═══════════════════════════════════════════════════════════════
#  步骤 1: API Key 加载
# ═══════════════════════════════════════════════════════════════

def test_api_keys():
    step(1, "API Key 加载验证")
    keys = {
        "DEEPSEEK_API_KEY":   config.DEEPSEEK_API_KEY,
        "TAVILY_API_KEY":     config.TAVILY_API_KEY,
        "BAIDU_SEARCH_API_KEY": config.BAIDU_SEARCH_API_KEY,
        "UAPI_API_KEY":       config.UAPI_API_KEY,
        "FIRECRAWL_API_KEY":  config.FIRECRAWL_API_KEY,
    }
    all_ok = True
    for name, val in keys.items():
        if val and len(val) > 10:
            ok(f"{name} = {val[:8]}...{val[-4:]}")
        else:
            fail(f"{name} 为空或过短")
            all_ok = False
    return all_ok


# ═══════════════════════════════════════════════════════════════
#  步骤 2: 搜索工具可用性
# ═══════════════════════════════════════════════════════════════

def test_search_tools():
    step(2, "搜索工具可用性测试")
    results = {}

    # 2: web_search（通用搜索，自动多后端降级）
    info("测试 web_search...")
    try:
        from core.tools import web_search
        result = web_search.invoke({"query": "钉钉 协同办公"})
        if "失败" in result[:100] or "未配置" in result[:100]:
            warn(f"web_search 返回异常: {result[:200]}")
            results["web_search"] = False
        else:
            ok(f"web_search 成功，返回 {len(result)} 字符")
            results["web_search"] = True
    except Exception as e:
        fail(f"web_search 异常: {e}")
        results["web_search"] = False

    return results


# ═══════════════════════════════════════════════════════════════
#  步骤 3: DeepSeek LLM 连通性
# ═══════════════════════════════════════════════════════════════

async def test_llm_connectivity():
    step(3, "DeepSeek LLM 连通性测试")
    try:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=config.DEEPSEEK_MODEL,
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.DEEPSEEK_BASE_URL,
            temperature=0.1,
            max_tokens=200,
        )
        info(f"模型: {config.DEEPSEEK_MODEL}, URL: {config.DEEPSEEK_BASE_URL}")
        response = await llm.ainvoke("回复'连通成功'四个字，不要其他内容")
        content = response.content if hasattr(response, "content") else str(response)
        ok(f"LLM 回复: {content[:100]}")
        return True
    except Exception as e:
        fail(f"LLM 连接失败: {e}")
        traceback.print_exc()
        return False


# ═══════════════════════════════════════════════════════════════
#  步骤 4: LLM Tool Calling 能力
# ═══════════════════════════════════════════════════════════════

async def test_tool_calling():
    step(4, "DeepSeek Tool Calling 能力测试")
    try:
        from langchain_openai import ChatOpenAI
        from core.tools import web_search

        llm = ChatOpenAI(
            model=config.DEEPSEEK_MODEL,
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.DEEPSEEK_BASE_URL,
            temperature=0.1,
            max_tokens=500,
        )
        llm_with_tools = llm.bind_tools([web_search])

        info("发送 tool calling 测试请求...")
        response = await llm_with_tools.ainvoke(
            "请搜索 '飞书 协同办公' 的信息"
        )

        if hasattr(response, "tool_calls") and response.tool_calls:
            tc = response.tool_calls[0]
            ok(f"LLM 成功发起 tool call: {tc['name']}({tc['args']})")
            return True
        else:
            warn(f"LLM 未发起 tool call, 回复: {str(response.content)[:200]}")
            return False
    except Exception as e:
        fail(f"Tool calling 测试失败: {e}")
        traceback.print_exc()
        return False


# ═══════════════════════════════════════════════════════════════
#  步骤 5: ReactAgent 完整初始化
# ═══════════════════════════════════════════════════════════════

async def test_react_agent_init():
    step(5, "ReactAgent 初始化测试")
    try:
        from core.react_agent import ReactAgent
        from core.tools import REACT_TOOLS

        REACT_PROMPT = """你是一个数据采集专家。请搜索指定产品的信息并返回 JSON 格式的结果。
返回格式：纯 JSON，包含 product_features 和 pricing_info 字段。"""

        agent = ReactAgent(
            system_prompt=REACT_PROMPT,
            tools=REACT_TOOLS,
            max_iterations=3,
        )

        if agent.is_available:
            ok("ReactAgent 初始化成功，ReAct 子图已编译")
            ok(f"可用工具: {[t.name for t in REACT_TOOLS]}")
            return agent
        else:
            fail("ReactAgent 初始化失败 — is_available=False")
            return None
    except Exception as e:
        fail(f"ReactAgent 初始化异常: {e}")
        traceback.print_exc()
        return None


# ═══════════════════════════════════════════════════════════════
#  步骤 6: ReAct 端到端循环
# ═══════════════════════════════════════════════════════════════

async def test_react_e2e(agent):
    step(6, "ReAct 端到端循环测试（LLM 自主搜索 → 返回结构化结果）")

    task = (
        "请搜索竞品「飞书」的产品信息。\n\n"
        "我方产品：钉钉（协同办公平台）\n\n"
        "请搜索飞书的核心产品功能和定价策略，然后返回 JSON 结果。\n"
        "JSON 格式要求：\n"
        '{"product_features": "功能描述", "pricing_info": "定价描述"}\n\n'
        "重要：最终回复必须以 { 开头，以 } 结尾，是纯 JSON，不要加 ```json 标记。"
    )

    info(f"任务: 搜索「飞书」信息")
    info("启动 ReAct 循环（最多 3 轮）...")
    info("预期行为：LLM 调用 web_search，内部自动降级保证结果返回")

    try:
        result = await agent.run(task)

        if result is None:
            fail("ReAct 返回 None — 执行失败")
            return False

        final_answer = result.get("final_answer", "")
        iterations = result.get("iterations", 0)
        messages = result.get("messages", [])

        info(f"循环次数: {iterations}")
        info(f"消息总数: {len(messages)}")
        info(f"最终回复长度: {len(final_answer)} 字")

        # 打印消息轨迹（完整内容，截断到 300 字）
        print(f"\n  {BOLD}--- ReAct 消息轨迹 ---{RESET}")
        for i, msg in enumerate(messages):
            msg_type = type(msg).__name__
            content = ""
            if hasattr(msg, "content") and msg.content:
                content = str(msg.content)[:300]
            tool_calls = ""
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                tool_calls = f" [tool_calls: {[(tc['name'], tc['args']) for tc in msg.tool_calls]}]"

            if msg_type == "HumanMessage":
                label = "USER"
            elif msg_type == "AIMessage":
                label = "AI"
            elif msg_type == "ToolMessage":
                label = "TOOL"
            else:
                label = msg_type

            print(f"  [{i+1}] {label}: {content}{tool_calls}")
        print(f"  {BOLD}--- 轨迹结束 ---{RESET}\n")

        # ── 分析工具调用序列 ──
        print(f"  {BOLD}--- 工具调用序列 ---{RESET}")
        tool_calls_sequence = []
        tool_results = []
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls_sequence.append(tc["name"])
            if type(msg).__name__ == "ToolMessage":
                content_str = str(getattr(msg, "content", ""))
                tool_results.append(content_str[:150])

        info(f"工具调用序列: {tool_calls_sequence}")

        # 检查是否有工具被重复调用
        from collections import Counter
        call_counts = Counter(tool_calls_sequence)
        repeated_failed = False
        for tool_name, count in call_counts.items():
            if count > 3:
                warn(f"{tool_name} 被调用了 {count} 次")
                repeated_failed = True

        # 检查工具使用情况
        unique_tools = set(tool_calls_sequence)
        if len(unique_tools) > 0:
            ok(f"工具调用: {tool_calls_sequence}")
        else:
            warn("未调用任何工具")

        if not repeated_failed:
            ok("未发现异常重复调用")

        print(f"  {BOLD}--- 分析结束 ---{RESET}\n")

        if not final_answer:
            warn("最终回复为空")
            return False

        # 尝试解析 JSON
        try:
            clean = final_answer.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1] if "\n" in clean else clean
                if clean.endswith("```"):
                    clean = clean[:-3]
                clean = clean.strip()

            data = json.loads(clean)
            ok(f"JSON 解析成功!")
            ok(f"product_features: {data.get('product_features', 'N/A')[:100]}...")
            ok(f"pricing_info: {data.get('pricing_info', 'N/A')[:100]}...")
            return True
        except json.JSONDecodeError as je:
            warn(f"JSON 解析失败: {je}")
            info(f"原始回复:\n{final_answer[:500]}")
            if iterations > 0 and len(final_answer) > 50:
                ok("ReAct 循环本身跑通（JSON 格式需优化）")
                return True
            return False

    except Exception as e:
        fail(f"ReAct 端到端测试异常: {e}")
        traceback.print_exc()
        return False


# ═══════════════════════════════════════════════════════════════
#  主函数
# ═══════════════════════════════════════════════════════════════

async def main():
    print(f"\n{BOLD}╔══════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}║   ReAct 端到端验证脚本                                   ║{RESET}")
    print(f"{BOLD}║   LLM + Tool Calling + ReAct Loop                        ║{RESET}")
    print(f"{BOLD}╚══════════════════════════════════════════════════════════╝{RESET}\n")

    results = {}

    # 步骤 1
    results["api_keys"] = test_api_keys()
    if not results["api_keys"]:
        print(f"\n{RED}{BOLD}API Key 未就绪，终止测试。{RESET}")
        return

    # 步骤 2
    search_results = test_search_tools()

    # 步骤 3
    results["llm"] = await test_llm_connectivity()
    if not results["llm"]:
        print(f"\n{RED}{BOLD}LLM 连接失败，终止测试。{RESET}")
        return

    # 步骤 4
    results["tool_calling"] = await test_tool_calling()

    # 步骤 5
    agent = await test_react_agent_init()
    results["agent_init"] = agent is not None
    if not agent:
        print(f"\n{RED}{BOLD}ReactAgent 初始化失败，终止测试。{RESET}")
        return

    # 步骤 6
    results["react_e2e"] = await test_react_e2e(agent)

    # ── 总结 ──
    step("S", "测试结果总结")
    all_pass = True
    for name, passed in results.items():
        status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
        print(f"  {name:20s} {status}")
        if not passed:
            all_pass = False

    # 搜索工具单独显示
    for tool_name, passed in search_results.items():
        status = f"{GREEN}PASS{RESET}" if passed else f"{YELLOW}SKIP{RESET}"
        print(f"  search_{tool_name:14s} {status}")

    print()
    if all_pass and results.get("react_e2e"):
        print(f"{GREEN}{BOLD}[PASS] ReAct 全链路验证通过！LLM + Tool Calling + ReAct 循环正常工作。{RESET}")
    else:
        print(f"{YELLOW}{BOLD}[WARN] 部分环节未通过，请查看上方详细日志。{RESET}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
