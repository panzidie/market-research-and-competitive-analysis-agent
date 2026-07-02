# -*- coding: utf-8 -*-
"""
config.py — 智能竞品分析多Agent系统 全局配置

配置加载优先级：
  1. 环境变量
  2. 本文件默认值（仅作兜底，建议通过环境变量或在 .env 文件中设置敏感信息）

LLM后端选择：
  - LLM_PROVIDER = "qianfan"  → 百度千帆API（云端）
  - LLM_PROVIDER = "ollama"   → 本机Ollama（本地）
"""

import os
from dotenv import load_dotenv

# 加载 .env 文件（环境变量优先级高于 .env）
load_dotenv()

# ========================
# LLM 后端选择
# ========================
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "deepseek")

# ========================
# 千帆API配置（LLM_PROVIDER = "qianfan" 时生效）
# ========================
QIANFAN_API_KEY = os.environ.get("QIANFAN_API_KEY", "")
QIANFAN_SECRET_KEY = os.environ.get("QIANFAN_SECRET_KEY", "")
QIANFAN_MODEL = os.environ.get("QIANFAN_MODEL", "ernie-4.0-turbo-8k")

# ========================
# Ollama配置（LLM_PROVIDER = "ollama" 时生效）
# ========================
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")

# ========================
# DeepSeek配置（LLM_PROVIDER = "deepseek" 时生效）
# ========================
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get(
    "DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"
)
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

# ========================
# 搜索后端选择
#   SEARCH_PROVIDER = "baidu"  -> 百度AI搜索（默认）
#   SEARCH_PROVIDER = "tavily" -> Tavily AI Search
# ========================
SEARCH_PROVIDER = os.environ.get("SEARCH_PROVIDER", "tavily")

# ========================
# 百度AI搜索配置
# ========================
BAIDU_SEARCH_API_KEY = os.environ.get("BAIDU_SEARCH_API_KEY", "")
BAIDU_SEARCH_URL = "https://qianfan.baidubce.com/v2/ai_search/web_search"
BAIDU_SEARCH_SOURCE = "baidu_search_v2"
BAIDU_SEARCH_RECENCY = os.environ.get("BAIDU_SEARCH_RECENCY", "month")
BAIDU_MAX_RESULTS = int(os.environ.get("BAIDU_MAX_RESULTS", "5"))

# ========================
# Tavily AI Search 配置
# ========================
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
TAVILY_BASE_URL = os.environ.get("TAVILY_BASE_URL", "https://api.tavily.com")
TAVILY_SEARCH_DEPTH = os.environ.get("TAVILY_SEARCH_DEPTH", "advanced")
TAVILY_MAX_RESULTS = int(os.environ.get("TAVILY_MAX_RESULTS", "5"))
TAVILY_INCLUDE_ANSWER = os.environ.get("TAVILY_INCLUDE_ANSWER", "true").lower() == "true"

# ========================
# Firecrawl 配置
# ========================
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY", "")
FIRECRAWL_BASE_URL = os.environ.get(
    "FIRECRAWL_BASE_URL", "https://api.firecrawl.dev/v1"
)

# ========================
# UAPI 智能搜索配置
# ========================
UAPI_API_KEY = os.environ.get("UAPI_API_KEY", "")
UAPI_BASE_URL = os.environ.get("UAPI_BASE_URL", "https://uapis.cn")
UAPI_MAX_RESULTS = int(os.environ.get("UAPI_MAX_RESULTS", "5"))

# 搜索间隔（秒），避免限流
SEARCH_DELAY_SECONDS = float(os.environ.get("SEARCH_DELAY_SECONDS", "2.0"))

# ========================
# 系统模式配置
# ========================
ENABLE_LLM = True
VERBOSE = False             # --verbose 详细日志模式

# ========================
# 竞品分析参数
# ========================
# 默认竞品数量范围
MIN_COMPETITORS = 3
MAX_COMPETITORS = 8
DEFAULT_COMPETITOR_COUNT = 5

# ========================
# LLM调用参数
# ========================
LLM_TEMPERATURE = 0.3       # 适中温度，保证分析既准确又有洞察
LLM_MAX_TOKENS = 4096       # 竞品数据较多，增大输出上限

# ========================
# 长期记忆（Long-Term Memory）配置
# ========================
LTM_DB_PATH = os.environ.get("LTM_DB_PATH", "data/long_term_memory.db")
LTM_CHROMA_DIR = os.environ.get("LTM_CHROMA_DIR", "data/chroma_memory")

# ========================
# 安全机制配置
# ========================
SECURITY_ENABLE_INJECTION_CHECK = True   # 启用 Prompt Injection 检测
SECURITY_CONFIRM_HIGH_RISK = True        # 高风险操作记录确认日志
SECURITY_DEFAULT_ROLE = "user"           # 默认角色（admin / user / guest）

# ========================
# Web 服务配置
# ========================
SERVER_HOST = os.environ.get("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.environ.get("SERVER_PORT", "8000"))
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")
