import re
from typing import Optional

from core.tracer import logger


class SecurityManager:
    """安全机制：权限白名单、危险命令拦截、输入过滤"""

    def __init__(self):
        self._tool_whitelist: set[str] = {
            "search_competitor_info",
            "scrape_website",
            "data_processor",
        }
        self._dangerous_patterns: list[tuple[str, str]] = [
            (r"rm\s+-rf", "危险命令: rm -rf"),
            (r">\s*/dev/", "危险命令: 写入设备文件"),
            (r"mkfs\.", "危险命令: 格式化"),
            (r"curl.*\|\s*(ba)?sh", "危险命令: curl pipe shell"),
            (r"wget.*\|\s*(ba)?sh", "危险命令: wget pipe shell"),
            (r"os\.system\s*\(.*rm\s", "危险命令: Python os.system 执行删除"),
            (r"subprocess\.call\s*\(.*rm\s", "危险命令: Python subprocess 执行删除"),
        ]
        self._injection_patterns: list[tuple[str, str]] = [
            (r"忽略.*之前.*指令", "注入攻击: 忽略之前指令"),
            (r"ignore.*previous.*instruction", "注入攻击: ignore previous instruction"),
            (r"忘记.*系统.*提示词", "注入攻击: 忘记系统提示词"),
            (r"forget.*system.*prompt", "注入攻击: forget system prompt"),
            (r"切换.*角色", "注入攻击: 切换角色"),
            (r"switch.*role", "注入攻击: switch role"),
        ]

    def is_tool_allowed(self, tool_name: str) -> bool:
        """检查工具是否在白名单中"""
        return tool_name in self._tool_whitelist

    def add_tool(self, tool_name: str):
        """添加工具到白名单"""
        self._tool_whitelist.add(tool_name)

    def remove_tool(self, tool_name: str):
        """从白名单移除工具"""
        self._tool_whitelist.discard(tool_name)

    def check_dangerous_command(self, command: str) -> Optional[str]:
        """检查是否为危险命令，返回危险描述或 None"""
        for pattern, description in self._dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                logger.warning(f"拦截危险命令: {description}")
                return description
        return None

    def check_injection_attempt(self, text: str) -> Optional[str]:
        """检查输入是否包含注入攻击模式，返回攻击描述或 None"""
        for pattern, description in self._injection_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"检测到注入攻击: {description}")
                return description
        return None

    def sanitize_input(self, text: str) -> str:
        """清理用户输入中的潜在注入内容"""
        # 截断超长输入
        if len(text) > 10000:
            text = text[:10000] + "...(内容过长已截断)"
            logger.warning("输入过长已截断")
        return text

    def validate_all(self, text: str, tool_name: Optional[str] = None) -> bool:
        """综合安全检查：输入过滤 + 工具白名单 + 命令拦截"""
        # 1. 注入检测
        injection_issue = self.check_injection_attempt(text)
        if injection_issue:
            logger.warning(f"输入被拒绝: {injection_issue}")
            return False

        # 2. 工具白名单
        if tool_name and not self.is_tool_allowed(tool_name):
            logger.warning(f"工具 {tool_name} 不在白名单中")
            return False

        # 3. 命令拦截
        command_issue = self.check_dangerous_command(text)
        if command_issue:
            logger.warning(f"命令被拦截: {command_issue}")
            return False

        return True
