"""
提示词加载器 — 从 prompts/ 目录的 .md 文件中读取角色提示词和技能模板。
不依赖 .py 常量文件，.md 是唯一来源。
"""
from pathlib import Path


_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _read_md(filename: str) -> str:
    """读取 prompts/ 下的 .md 文件，去掉 frontmatter 和标题行"""
    filepath = _PROMPTS_DIR / filename
    if not filepath.exists():
        return ""
    content = filepath.read_text(encoding="utf-8")

    # 去掉 YAML frontmatter
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            content = content[end + 3 :]

    return content.strip()


# === 角色提示词（从 prompts/agents/*.md 读取）===

def get_researcher_prompt() -> str:
    return _read_md("agents/researcher.md")


def get_analyst_prompt() -> str:
    return _read_md("agents/analyst.md")


def get_writer_prompt() -> str:
    return _read_md("agents/writer.md")


def get_fact_checker_prompt() -> str:
    return _read_md("agents/fact_checker.md")


# === 技能模板（从 prompts/skills/*.md 读取）===

def get_data_extraction_template() -> str:
    return _read_md("skills/data-extraction.md")


def get_competitor_matrix_template() -> str:
    return _read_md("skills/competitor-matrix.md")


def get_swot_analysis_template() -> str:
    return _read_md("skills/swot-analysis.md")
