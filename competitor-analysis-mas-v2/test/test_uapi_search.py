#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_uapi_search.py — UAPI 搜索工具独立测试脚本
"""

import sys
import os

# 修复 Windows 终端编码
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# 确保项目根目录在路径中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv()

import config


def test_uapi_direct():
    """方式1: 直接调用 UAPI 搜索 API（/api/v1/search/aggregate）"""
    print("=" * 60)
    print("  方式1: 直接调用 UAPI 搜索 API")
    print("=" * 60)

    if not config.UAPI_API_KEY:
        print("  [FAIL] UAPI_API_KEY 未配置")
        return False

    try:
        import requests

        url = config.UAPI_BASE_URL.rstrip("/") + "/api/v1/search/aggregate"
        headers = {
            "Authorization": f"Bearer {config.UAPI_API_KEY}",
            "Content-Type": "application/json",
        }

        query = "Python编程学习 2025"
        payload = {"query": query, "engines": ["web"]}
        print(f"  [INFO] POST {url}")
        print(f"  [INFO] API Key: {config.UAPI_API_KEY[:12]}...{config.UAPI_API_KEY[-4:]}")
        print(f"\n  [SEARCH] 搜索: {query}")

        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        result = resp.json()

        if not result:
            print("  [FAIL] 返回结果为空")
            return False

        print(f"\n  [OK] 响应 keys: {list(result.keys())}")

        total = result.get("total_results", result.get("total", 0))
        print(f"  [OK] 总结果数: {total}")

        results_list = result.get("results", [])
        print(f"  [OK] 返回条数: {len(results_list)}")

        if results_list:
            print(f"\n  --- 前5条搜索结果 ---")
            for i, item in enumerate(results_list[:5], 1):
                title = item.get("title", "无标题")
                item_url = item.get("url", "")
                snippet = item.get("snippet", "")[:120]
                source = item.get("source", "")
                print(f"\n  [{i}] {title}")
                print(f"      URL: {item_url}")
                if snippet:
                    print(f"      摘要: {snippet}...")
                if source:
                    print(f"      来源: {source}")
        else:
            print("  [WARN] 搜索结果为空列表")

        return True

    except Exception as e:
        print(f"  [FAIL] 调用异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_web_search():
    """通过 core.tools.web_search 工具调用（自动多后端降级到 UAPI）"""
    print("\n" + "=" * 60)
    print("  验证: web_search 自动降级到 UAPI")
    print("=" * 60)

    try:
        from core.tools import web_search

        query = "Python 机器学习 教程 2025"
        print(f"\n  [SEARCH] 搜索: {query}")
        result = web_search.invoke({"query": query})

        if not result:
            print("  [FAIL] 返回结果为空")
            return False

        print(f"\n  [OK] 返回长度: {len(result)} 字符")
        print(f"\n  --- 结果内容 ---")
        print(result[:2000])
        return True

    except Exception as e:
        print(f"  [FAIL] 调用异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print()
    print("=======================================================")
    print("       搜索功能测试脚本（UAPI 直调 + web_search 降级验证）")
    print("=======================================================")
    print()
    print(f"  UAPI_API_KEY = {config.UAPI_API_KEY[:12] if config.UAPI_API_KEY else '(空)'}...")
    print(f"  UAPI_BASE_URL = {config.UAPI_BASE_URL}")
    print()

    r1 = test_uapi_direct()
    r2 = test_web_search()

    print("\n" + "=" * 60)
    print("  测试结果汇总")
    print("=" * 60)
    print(f"  UAPI 直调: {'PASS' if r1 else 'FAIL'}")
    print(f"  web_search: {'PASS' if r2 else 'FAIL'}")
    print()
