"""
RAG 问答效果测试脚本

用法：
  D:/anaconda/envs/gemini/python.exe test_rag_qa.py
  D:/anaconda/envs/gemini/python.exe test_rag_qa.py --queries "企业级AI市场规模" "金融科技趋势"
  D:/anaconda/envs/gemini/python.exe test_rag_qa.py --interactive
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "d:/31072/python_learning/competitor-analysis-mas-v2/competitor-analysis-mas-v2")

from skill.rag_skill.rag_skill import rag_search


def test_queries(queries: list[str]):
    for q in queries:
        print(f"\n{'='*60}")
        print(f"  问题: {q}")
        print(f"{'='*60}")
        result = rag_search.invoke({"query": q})
        # 取输出第一行到 "引用文档" 之前
        parts = result.split("[引用文档]")
        answer = parts[0].strip()
        references = parts[1].strip() if len(parts) > 1 else ""

        print(f"\n  [回答]")
        for line in answer.split("\n"):
            print(f"    {line}")
        print(f"\n  [引用] {len(references)} 字符")

        # 评分
        if "无法从已有文档中找到相关信息" in result or "未找到相关信息" in result:
            print(f"  [判定] ❌ 知识库未覆盖此问题")
        else:
            print(f"  [判定] ✅ 知识库有相关信息")


def interactive():
    print("\n========== RAG 问答交互测试 ==========")
    print("输入问题（输入 q 退出）\n")
    while True:
        try:
            q = input(">> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q:
            continue
        if q.lower() in ("q", "quit", "exit"):
            break
        test_queries([q])


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--interactive" in args or not args:
        # 默认：预设测试 + 交互
        preset = [
            "2025年中国企业级AI市场规模是多少",
            "金融科技未来的发展趋势有哪些",
            "企业级AI应用的主要驱动因素是什么",
            "智能体在金融领域有哪些应用场景",
            "报告中提到了哪些AI供应商",
        ]

        print("\n========== RAG 效果测试 ==========")
        print(f"  知识库: 艾瑞咨询研究报告 × 2")
        print(f"  模型: bge-small-zh-v1.5 → DeepSeek")
        print(f"\n  [预设测试 {len(preset)} 条]")
        for q in preset:
            test_queries([q])

        interactive()
    else:
        # 命令行参数做查询
        test_queries(args)
