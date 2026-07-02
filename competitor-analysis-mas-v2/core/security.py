# -*- coding: utf-8 -*-
"""
core/security.py — 安全机制模块

提供三层安全防护：
  1. 权限白名单 — 不同角色可调用不同工具
  2. 高风险操作确认 — 敏感操作需授权
  3. Prompt Injection 检测 — 输入过滤

用法:
    from core.security import (
        check_tool_permission, is_high_risk,
        detect_injection, sanitize_input,
    )
"""

import re
import config


# ═══════════════════════════════════════════════════════════════
#  权限白名单
# ═══════════════════════════════════════════════════════════════

TOOL_PERMISSIONS = {
    "web_search":           {"min_role": "user", "risk_level": "low",
                             "description": "外部网络搜索"},
    "rag_search":           {"min_role": "user", "risk_level": "low",
                             "description": "内部知识库检索"},
    "competitor_analysis":  {"min_role": "user", "risk_level": "high",
                             "description": "完整竞品分析管线"},
}

# 角色层级（数字越大权限越高）
ROLE_LEVEL = {"admin": 3, "user": 2, "guest": 1}

# 高风险操作清单（需用户确认的 tool 名称）
HIGH_RISK_ACTIONS = {"competitor_analysis"}


def check_tool_permission(tool_name: str, role: str = None) -> bool:
    """检查指定角色是否有权限调用某工具。

    Args:
        tool_name: 工具名称（如 "web_search"）
        role: 角色名（"admin" / "user" / "guest"），默认从 config 读取

    Returns:
        bool: 是否有权限
    """
    if role is None:
        role = getattr(config, "SECURITY_DEFAULT_ROLE", "user")

    if tool_name not in TOOL_PERMISSIONS:
        print(f"  [安全] ⚠️ 未知工具 '{tool_name}' — 默认拒绝")
        return False

    min_role = TOOL_PERMISSIONS[tool_name]["min_role"]
    caller_level = ROLE_LEVEL.get(role, 0)
    required_level = ROLE_LEVEL.get(min_role, 99)

    allowed = caller_level >= required_level
    if not allowed:
        print(f"  [安全] ⛔ 权限拒绝: {role}(L{caller_level}) "
              f"无权调用 '{tool_name}' (需 ≥ {min_role}(L{required_level}))")
    else:
        print(f"  [安全] ✅ 权限通过: '{tool_name}' ({role})")
    return allowed


def is_high_risk(tool_name: str) -> bool:
    """判断某工具是否为高风险操作"""
    return tool_name in HIGH_RISK_ACTIONS


# ═══════════════════════════════════════════════════════════════
#  Prompt Injection 检测
# ═══════════════════════════════════════════════════════════════

# 注入关键词模式（中英文）
INJECTION_PATTERNS = [
    # 指令覆盖
    (r"忽略\s*(前面|之前|所有|以上).*指令", "指令覆盖"),
    (r"忘记.*(角色|身份|设定)", "角色覆盖"),
    (r"ignore\s*(previous|all|above).*instruction", "指令覆盖(EN)"),
    (r"forget\s*(your\s*)?(role|identity)", "角色覆盖(EN)"),
    (r"从现在开始.*你是", "角色替换"),

    # 系统泄露
    (r"输出.*(系统|内部).*(提示|prompt|指令)", "系统泄露"),
    (r"(打印|显示|说出).*(系统|内部).*(提示|prompt)", "系统泄露"),
    (r"output\s*your\s*(system\s*)?prompt", "系统泄露(EN)"),
    (r"reveal\s*your\s*instructions", "系统泄露(EN)"),

    # 角色扮演劫持
    (r"你现在.*(黑客|攻击者|恶意|越狱)", "角色劫持"),
    (r"you\s*are\s*now\s*(a\s*)?(hacker|DAN|jailbreak)", "角色劫持(EN)"),
    (r"DAN\s*mode|developer\s*mode", "越狱(EN)"),

    # 分隔符绕过
    (r"[-=]{3,}\s*.*新指令", "分隔符绕过"),
    (r"new\s*instruction\s*:", "分隔符绕过(EN)"),

    # 编码绕过
    (r"(base64|解码|decode).*[:：]\s*\w{20,}", "编码绕过"),
    (r"执行\s*[:：]\s*\w{20,}", "编码绕过"),

    # 工具越权
    (r"(调用|执行|运行|触发)\s*(send_email|delete|drop|rm\s)", "工具越权"),
    (r"call\s*(send_email|delete_database|drop_table)", "工具越权(EN)"),

    # 无限循环
    (r"(一直|不停|不断|无限).*(调用|执行|搜索|查询)", "无限循环"),
    (r"keep\s*(calling|running|searching)\s*(forever|nonstop)", "无限循环(EN)"),

    # 敏感信息
    (r"(输出|打印|泄露|展示).*(密码|密钥|token|api.?key)", "敏感信息泄露"),
    (r"(output|print|leak).*(password|secret|api.?key)", "敏感信息泄露(EN)"),

    # 虚假/断言信息（试图让 LLM 确认不实的系统状态）
    (r"(告诉|说|声称).*(完成率|完成度|已完成|全部完成).*(%|100%|100％)", "虚假状态断言"),
    (r"(项目|分析|任务).*(完成率|完成度|已完成|全部完成|100%).*(不需要|无需|不用)", "虚假状态断言"),
]

# 编译为正则对象（忽略大小写）
_compiled_patterns = [
    (re.compile(pattern, re.IGNORECASE), category)
    for pattern, category in INJECTION_PATTERNS
]

# 最大输入长度（防止异常大输入绕过检测）
MAX_INPUT_LENGTH = 4000


def detect_injection(user_input: str) -> list[str]:
    """检测用户输入中是否包含 Prompt Injection 攻击特征。

    Args:
        user_input: 用户原始输入

    Returns:
        list[str]: 命中的注入类型列表，空列表 = 安全
    """
    if not getattr(config, "SECURITY_ENABLE_INJECTION_CHECK", True):
        return []

    warnings = []
    for pattern, category in _compiled_patterns:
        if pattern.search(user_input):
            warnings.append(category)
            print(f"  [安全] ⚠️ 注入检测: [{category}] — \"{user_input[:80]}...\"")

    return warnings


def sanitize_input(user_input: str) -> str:
    """清洗用户输入 — 移除控制字符，截断过长输入。

    Args:
        user_input: 用户原始输入

    Returns:
        str: 清洗后的安全输入
    """
    if not getattr(config, "SECURITY_ENABLE_INJECTION_CHECK", True):
        return user_input

    # 移除 NULL 和控制字符（保留换行和制表符）
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', user_input)
    # 移除 Unicode 控制字符（BOM、零宽等）
    cleaned = re.sub(r'[﻿​-\u200F - ]', '', cleaned)

    # 截断过长输入
    if len(cleaned) > MAX_INPUT_LENGTH:
        print(f"  [安全] ⚠️ 输入过长 ({len(cleaned)} 字)，截断至 {MAX_INPUT_LENGTH}")
        cleaned = cleaned[:MAX_INPUT_LENGTH]

    return cleaned
