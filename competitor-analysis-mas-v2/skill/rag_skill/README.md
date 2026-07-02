# RAG 知识库检索 Skill

## 功能

从内部知识库（艾瑞咨询研究报告 PDF）中语义检索相关信息，并用 DeepSeek 模型生成回答。

## 文件说明

| 文件 | 说明 |
|------|------|
| `__init__.py` | 包标识 |
| `rag_skill.py` | 核心逻辑：向量检索 + DeepSeek 生成（@tool 注册） |
| `test_rag_qa.py` | RAG 问答效果测试脚本（预设 + 交互） |
| `README.md` | 使用说明（本文件） |

## 使用方式

### 在 tools.py 中注册

```python
from skill.rag_skill.rag_skill import rag_search
REACT_TOOLS = [web_search, rag_search]
```

### 直接调用测试

```python
from skill.rag_skill.rag_skill import rag_search
result = rag_search.invoke({"query": "2025年企业级AI市场规模"})
print(result)
```

### 运行效果测试

```bash
# 默认：5条预设测试 + 交互模式
D:/anaconda/envs/gemini/python.exe skill/rag_skill/test_rag_qa.py

# 纯交互模式
D:/anaconda/envs/gemini/python.exe skill/rag_skill/test_rag_qa.py --interactive

# 测试指定问题
D:/anaconda/envs/gemini/python.exe skill/rag_skill/test_rag_qa.py --queries "金融科技趋势" "AI供应商"
```

## 知识库

| 项目 | 说明 |
|------|------|
| PDF 来源 | `RAG/data/` 目录（自动扫描所有 `.pdf`） |
| 当前文档 | 艾瑞咨询研究报告 × 2 |
| Chunk 参数 | size=500, overlap=80 |
| Embedding 模型 | BAAI/bge-small-zh-v1.5 (384维) |
| 向量数据库 | ChromaDB（collection: `iResearch_Report`） |
| 生成模型 | DeepSeek（通过 openai.OpenAI 直连） |

## 返回格式

```
[RAG回答]
{LLM 基于文档生成的回答}

[引用文档]
[1] {命中文档片段 1}
[2] {命中文档片段 2}
...
```

## 重新索引

当 `RAG/data/` 目录新增或替换 PDF 后，需要重建向量索引：

```bash
D:/anaconda/envs/gemini/python.exe RAG/main.py --index-only
```

## 依赖

- `RAG/` 目录中的向量库（ChromaDB + BAAI/bge-small-zh-v1.5）
- `RAG/data/` 目录放置 PDF 文件
- DeepSeek API（通过 `.env` 中 `DEEPSEEK_API_KEY` 配置）
