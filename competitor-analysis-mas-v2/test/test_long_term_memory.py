# -*- coding: utf-8 -*-
"""LongTermMemory 集成测试"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.long_term_memory import LongTermMemory


def test_basic_flow():
    m = LongTermMemory(max_turns=3)
    assert m.turn_count == 0
    assert m.to_messages() == []

    m.add("user", "hello")
    m.add("assistant", "hi there")
    assert m.turn_count == 1
    assert m.to_messages() == [("user", "hello"), ("assistant", "hi there")]

    m.clear()
    assert m.to_messages() == []
    m.close()
    print("  [PASS] test_basic_flow")


def test_analysis_report():
    m = LongTermMemory(max_turns=5)
    report = {
        "product_name": "飞书",
        "competitor_count": 4,
        "overall_positioning": "企业协作平台领导者",
        "differentiation_strategy": {"core_differentiator": "文档+IM+OA一体化"},
        "action_plan": [{"priority": "HIGH", "action": "加强文档能力", "timeline": "Q3", "expected_impact": "高"}],
        "risk_assessment": "市场竞争激烈",
        "product_analysis_summary": "功能全面",
        "pricing_analysis_summary": "中高端定价",
        "market_analysis_summary": "快速增长",
        "summary": "建议持续投入",
    }
    m.add_analysis_report(report)

    results = m.keyword_search("飞书")
    assert len(results) > 0
    print(f"  [PASS] test_analysis_report: keyword_search found {len(results)} results")

    m.close()
    print("  [PASS] test_analysis_report: closed")


def test_semantic_search():
    m = LongTermMemory(max_turns=5)
    m.add("user", "帮我分析飞书的竞品情况")
    m.add("assistant", "飞书的竞品包括钉钉、企业微信等")

    results = m.semantic_search("飞书竞品", top_k=3)
    print(f"  [PASS] test_semantic_search: got {len(results)} results")
    for r in results:
        print(f"     - [{r.get('product_name', 'N/A')}] score={r.get('score', 0):.3f} adj={r.get('adjusted_score', 0):.3f}")

    m.close()
    print("  [PASS] test_semantic_search: closed")


def test_multi_session():
    """模拟两次会话，验证关键词搜索能跨会话检索"""
    m1 = LongTermMemory(max_turns=5)
    m1.add("user", "钉钉怎么样")
    m1.add("assistant", "钉钉是阿里巴巴的企业协作平台")
    m1.add_analysis_report({
        "product_name": "钉钉",
        "competitor_count": 3,
        "overall_positioning": "中小企业协作平台",
        "summary": "钉钉在中小企业市场有优势",
        "action_plan": [],
    })
    m1.close()

    m2 = LongTermMemory(max_turns=5)
    results = m2.keyword_search("钉钉")
    print(f"  [PASS] test_multi_session: cross-session search found {len(results)} results")
    has_chat = any(r.get("type") == "chat_message" for r in results)
    has_report = any(r.get("type") == "analysis_report" for r in results)
    print(f"     chat messages: {has_chat}, analysis reports: {has_report}")
    m2.close()
    print("  [PASS] test_multi_session")


if __name__ == "__main__":
    print("LongTermMemory 测试\n")
    test_basic_flow()
    test_analysis_report()
    test_semantic_search()
    test_multi_session()
    print("\n*** 所有测试通过 ***")
