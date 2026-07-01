# 实验 5-4 · Agent 单工具调用（含 LangChain 扩展）



## 一、实验概要

| 项目 | 内容 |
|------|------|
| 实验类型 | 编码实现型 |
| 核心目标 | 用 DeepSeek API 搭建带 Function Calling 的 Agent，实现至少 2 个工具的自动调用和结果整合 |
| 关键验收 | Agent 能根据用户问题自动选择工具（计算/天气），并行调用，最终输出整合后的答案 |
| 课后扩展 | 附录 A：LangChain 框架版（感兴趣同学课后自行尝试） |

---

## 二、实验内容

1. 用 DeepSeek API 完成 Function Calling 的首次调用（单个计算器工具）
2. 加入第二个工具（天气查询），观察模型如何自动选择工具
3. 实现 ReAct 循环：让 Agent 在多步交互中完成复杂任务
4. 对比"用 Agent"和"不用 Agent"的差异，理解为什么要用 DeepSeek API 做工具决策

---

## 三、实验目标

完成本实验后，你应该能够：

- [ ] 写出一个完整的工具定义 JSON（含 name / description / parameters）
- [ ] 在 Python 中调用 DeepSeek API 的 `tool_choice="auto"` 实现自动工具决策
- [ ] 实现 ReAct 循环：思考 → 调用工具 → 收到结果 → 再思考 → 给出答案
- [ ] 解释"模型只决定调什么工具，不真正执行工具"的关键设计
- [ ] 说出为什么这个任务用 DeepSeek API 而非 Qwen2.5-1.5B

---

## 四、环境要求

| 项目 | 要求 |
|------|------|
| DeepSeek API Key | 已创建，余额 ≥ 1 元 |
| Python 包 | `openai>=1.0.0` |
| 网络 | 能访问 `https://api.deepseek.com` |
| GPU | 本实验不需要 GPU（全部走 API） |

> ⚠️ **余额提醒**：单个 Agent 调用约 0.001 元，此实验全程消耗约 0.1-0.3 元。

---

## 五、为什么用 DeepSeek API 做工具调用？

在正式开始前，理解这个实验的关键决策：

```
Qwen2.5-1.5B（本地微调模型）做工具调用 → ❌ 不稳定
  - 容易忽略工具定义，凭记忆直接回答
  - JSON 格式常出问题（缺括号、字段名拼错）
  - 多工具并行调用顺序混乱

DeepSeek API（云端决策大脑）做工具调用 → ✅ 可靠
  - Function Calling 格式标准化
  - 决策准确率高
  - 成本极低（5 元用完整门课）

本课程的双模型架构：
  DeepSeek API → 负责"想" + "决定用什么工具"（本实验练习这个）
  微调 Qwen2.5-1.5B → 负责"说"（Day6 融合实验练习这个）
```

---

## 六、实验步骤

### Step 1：验证 API 连通性 + 搭建基础框架（10 分钟）

```python
# 文件：/root/autodl-tmp/day5/agent/agent_tools.py
"""
Day5 实验 5-4：Agent 单工具调用实验
从最简单的一个工具开始，逐步加大难度
"""

import json
import math
from openai import OpenAI

# ===== DeepSeek API 客户端 =====
# 把你的 API Key 填入下方（获取地址：https://platform.deepseek.com/api_keys）
DEEPSEEK_API_KEY = "sk-你的APIKey"

client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key=DEEPSEEK_API_KEY
)

# ===== 测试连通性 =====
def test_connection():
    """先确认 API 能通"""
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "你好，请用一句话介绍自己"}],
            max_tokens=50
        )
        print("✅ DeepSeek API 连通成功！")
        print(f"   回复：{response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"❌ 连接失败：{e}")
        print("   请检查：")
        print("   1. API Key 是否正确")
        print("   2. 账户余额是否充足")
        print("   3. 网络是否能访问 api.deepseek.com")
        return False

if __name__ == "__main__":
    test_connection()
```

```bash
cd /root/autodl-tmp/day5
python agent_tools.py
```

预期输出：
```
✅ DeepSeek API 连通成功！
   回复：我是 DeepSeek，由深度求索公司创造的 AI 助手。
```

---

### Step 2：定义第一个工具——计算器（15 分钟）

```python
# 文件：/root/autodl-tmp/day5/agent_step1_single_tool.py
"""
实验 5-4 Step 1：单个工具——计算器
目标：让 DeepSeek 学会"调用工具"而不是"硬算"
"""

import json
import math
from openai import OpenAI

client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key="sk-你的APIKey"  # ← 改成你自己的
)

# ===== 第 1 步：定义工具 =====
# 工具定义 = 告诉模型"我有一个叫 XX 的工具，它能做 YY，输入格式是 ZZ"
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "执行数学计算，支持加减乘除、幂运算、三角函数、阶乘等。例如：'3*4+2'、'math.factorial(10)'",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "要计算的数学表达式，可以使用 math 模块中的函数"
                    }
                },
                "required": ["expression"]
            }
        }
    }
]

# ===== 第 2 步：定义工具的实际执行函数 =====
# 模型只决定"调哪个工具"，真正执行是在 Python 代码里
def execute_calculate(expression: str) -> str:
    """安全地执行数学表达式"""
    # 白名单：只允许 math 模块的函数 + 基本运算符
    allowed_names = {
        "abs": abs, "round": round, "min": min, "max": max,
        "pow": pow, "sum": sum,
        # math 模块常用函数
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "sqrt": math.sqrt, "log": math.log, "log10": math.log10,
        "pi": math.pi, "e": math.e,
        "factorial": math.factorial,
        "ceil": math.ceil, "floor": math.floor,
    }
    try:
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return f"计算结果：{expression} = {result}"
    except Exception as e:
        return f"计算失败：{e}。请检查表达式是否正确。"

# ===== 第 3 步：带工具的单次对话 =====
def chat_with_tools(user_query: str):
    """
    核心流程：
    1. 把用户问题 + 工具列表 发给 DeepSeek
    2. DeepSeek 返回：直接回答 / 调用工具
    3. 如果调用了工具 → 执行 → 把结果发回去 → DeepSeek 给出最终答案
    """
    print(f"\n{'='*60}")
    print(f"用户提问：{user_query}")
    print("=" * 60)
    
    # --- 第一次调用：模型决定"要不要用工具" ---
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": user_query}],
        tools=TOOLS,
        tool_choice="auto"  # 模型自己判断是否需要工具
    )
    
    msg = response.choices[0].message
    
    # --- 情况 1：模型决定直接回答（不需要工具）---
    if not msg.tool_calls:
        print("\n📝 模型直接回答（未调用工具）：")
        print(f"   {msg.content}")
        return msg.content
    
    # --- 情况 2：模型决定调用工具 ---
    print(f"\n🔧 模型决定调用 {len(msg.tool_calls)} 个工具：")
    
    # 构建新的消息列表（包含历史）
    messages = [{"role": "user", "content": user_query}]
    messages.append({
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
            }
            for tc in msg.tool_calls
        ]
    })
    
    # 执行每个工具调用
    for tool_call in msg.tool_calls:
        func_name = tool_call.function.name
        func_args = json.loads(tool_call.function.arguments)
        
        print(f"   工具：{func_name}")
        print(f"   参数：{func_args}")
        
        # 真正执行工具
        if func_name == "calculate":
            result = execute_calculate(func_args["expression"])
        else:
            result = f"未知工具：{func_name}"
        
        print(f"   结果：{result}")
        
        # 把工具执行结果加入消息
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": result
        })
    
    # --- 第二次调用：把工具结果发给模型，让它给出最终答案 ---
    print("\n🤔 模型整理结果中...")
    response2 = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages
    )
    
    final_answer = response2.choices[0].message.content
    print(f"\n✅ 最终回答：")
    print(f"   {final_answer}")
    
    return final_answer


# ===== 测试用例 =====
if __name__ == "__main__":
    print("=" * 60)
    print("实验 5-4 · Step 1：单个工具（计算器）")
    print("=" * 60)
    
    # 测试 1：需要工具的数学问题
    chat_with_tools("计算 12345 × 67890 的结果")
    
    # 测试 2：复杂表达式（有括号、有函数）
    chat_with_tools("100 的阶乘除以 99 的阶乘等于多少？用 factorial 函数计算")
    
    # 测试 3：不需要工具的问题（模型应该直接回答）
    chat_with_tools("你好，请介绍一下你自己")
    
    # 测试 4：需要多步计算的
    chat_with_tools("(3的8次方 + 2的10次方) 除以 13，结果是多少？")
```

```bash
cd /root/autodl-tmp/day5
python agent_step1_single_tool.py
```

**关键观察**（看完输出后思考）：

| 测试 | 模型行为 | 原因 |
|------|---------|------|
| 测试 1（数学题） | 调用 `calculate` | 模型知道这个需要计算 |
| 测试 2（阶乘题） | 调用 `calculate`（带 `math.factorial`） | 模型能写出正确的表达式 |
| 测试 3（闲聊） | 直接回答，不调工具 | `tool_choice="auto"` 判断无需工具 |
| 测试 4（多步） | 调用 `calculate`，在一个表达式中算完 | 模型把多步合成一个表达式 |

> 💡 **核心理解**：模型输出的是 `tool_calls`（"我想调用计算器，表达式是..."），真正执行 `eval()` 的是你的 Python 代码。模型 = 大脑，代码 = 手。

---

### Step 3：扩展——加入第二个工具（天气预报）（20 分钟）

```python
# 文件：/root/autodl-tmp/day5/agent_step2_multi_tools.py
"""
实验 5-4 Step 2：多个工具——计算器 + 天气预报
目标：让 DeepSeek 在多个工具之间自动选择
"""

import json, math, requests, datetime
from openai import OpenAI

client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key="sk-你的APIKey"  # ← 改成你自己的
)

# ===== 工具定义（现在有 2 个工具了）=====
TOOLS = [
    # 工具 1：计算器
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "执行数学计算。例如：'3*4+2'、'math.sqrt(144)'、'math.factorial(5)'",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "数学表达式"}
                },
                "required": ["expression"]
            }
        }
    },
    # 工具 2：天气查询
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的当前天气信息，返回温度、天气状况、风力等",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，如'北京'、'上海'、'广州'"
                    }
                },
                "required": ["city"]
            }
        }
    }
]

# ===== 城市映射（用于真实天气 API）=====
CITY_MAP = {
    "北京": "Beijing", "上海": "Shanghai", "广州": "Guangzhou",
    "深圳": "Shenzhen", "杭州": "Hangzhou", "成都": "Chengdu",
    "武汉": "Wuhan", "南京": "Nanjing", "重庆": "Chongqing",
    "西安": "Xi'an", "天津": "Tianjin", "苏州": "Suzhou",
}

def execute_tool(tool_name: str, arguments: dict) -> str:
    """统一的工具执行入口"""
    if tool_name == "calculate":
        return _execute_calculate(arguments["expression"])
    elif tool_name == "get_weather":
        return _execute_weather(arguments["city"])
    else:
        return f"未知工具：{tool_name}"

def _execute_calculate(expression: str) -> str:
    allowed = {
        "abs": abs, "round": round, "min": min, "max": max,
        "pow": pow, "sum": sum,
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "sqrt": math.sqrt, "log": math.log, "log10": math.log10,
        "pi": math.pi, "e": math.e,
        "factorial": math.factorial,
        "ceil": math.ceil, "floor": math.floor,
    }
    try:
        result = eval(expression, {"__builtins__": {}}, allowed)
        return f"{expression} = {result}"
    except Exception as e:
        return f"计算失败：{e}"

def _execute_weather(city: str) -> str:
    """查询天气（使用 wttr.in 免费 API，无需 Key）"""
    today = datetime.datetime.now().strftime("%Y年%m月%d日")
    if city not in CITY_MAP:
        return f"{today} | 暂无 {city} 的天气数据。支持的城市：{', '.join(CITY_MAP.keys())}"
    city_en = CITY_MAP[city]
    url = f"https://wttr.in/{city_en}?format=j1"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if data and "current_condition" in data:
            current = data["current_condition"][0]
            weather = current["weatherDesc"][0]["value"]
            temp = current["temp_C"]
            humidity = current["humidity"]
            wind_speed = current["windspeedKmph"]
            return f"{today} | {city}天气：{weather}，当前温度 {temp}℃，湿度 {humidity}%，风速 {wind_speed} km/h"
        else:
            return f"{today} | 获取 {city} 天气失败：返回数据格式异常"
    except Exception as e:
        return f"{today} | 获取 {city} 天气失败：{str(e)}"

def multi_tool_chat(user_query: str):
    """支持多工具的 Agent 对话"""
    print(f"\n{'='*60}")
    print(f"用户：{user_query}")
    
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": user_query}],
        tools=TOOLS,
        tool_choice="auto"
    )
    
    msg = response.choices[0].message
    
    if not msg.tool_calls:
        print(f"助手（直接回答）：{msg.content}")
        return msg.content
    
    print(f"调用 {len(msg.tool_calls)} 个工具：")
    messages = [{"role": "user", "content": user_query}]
    messages.append({
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {"id": tc.id, "type": "function",
             "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in msg.tool_calls
        ]
    })
    
    for tc in msg.tool_calls:
        func_name = tc.function.name
        func_args = json.loads(tc.function.arguments)
        result = execute_tool(func_name, func_args)
        print(f"  🔧 {func_name}({func_args})")
        print(f"     → {result[:80]}")
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": result
        })
    
    response2 = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages
    )
    
    final_answer = response2.choices[0].message.content
    print(f"\n✅ 最终回答：{final_answer}")
    return final_answer


if __name__ == "__main__":
    print("=" * 60)
    print("实验 5-4 · Step 2：多工具（计算器 + 天气预报）")
    print("=" * 60)
    
    # 测试 1：只需要天气
    multi_tool_chat("今天广州天气怎么样？")
    
    # 测试 2：只需要计算
    multi_tool_chat("25 的 3 次方是多少？")
    
    # 测试 3：需要两个工具！（核心测试）
    multi_tool_chat("广州今天天气如何？另外帮我算一下 156 × 23 等于多少。")
    
    # 测试 4：不需要工具
    multi_tool_chat("什么是人工智能？请用一句话解释。")
```

```bash
cd /root/autodl-tmp/day5
python agent_step2_multi_tools.py
```

---

### Step 4：实现 ReAct 循环（25 分钟）

> 前面的实验都是一次性调用：用户提问 → API 调工具 → 给出答案。但真实场景中，Agent 可能需要多轮思考——这就是 **ReAct**（Reasoning + Acting）。

```python
# 文件：/root/autodl-tmp/day5/agent_step3_react_loop.py
"""
实验 5-4 Step 3：ReAct 循环
目标：让 Agent 在多轮交互中完成复杂任务
"""

import json, math
from openai import OpenAI

client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key="sk-你的APIKey"
)

# ===== 工具定义（3 个工具）=====
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "执行数学计算",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "数学表达式"}
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称"}
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "获取当前日期和时间",
            "parameters": {"type": "object", "properties": {}}
        }
    }
]

WEATHER_DB = {
    "北京": "晴，18-28℃", "上海": "多云，20-25℃",
    "广州": "多云转阵雨，24-30℃", "深圳": "晴，25-31℃",
}

def execute_tool(tool_name: str, arguments: dict) -> str:
    if tool_name == "calculate":
        allowed = {"abs": abs, "sqrt": math.sqrt, "pow": pow,
                   "sin": math.sin, "cos": math.cos, "pi": math.pi,
                   "factorial": math.factorial, "ceil": math.ceil, "floor": math.floor}
        try:
            result = eval(arguments["expression"], {"__builtins__": {}}, allowed)
            return f"{arguments['expression']} = {result}"
        except Exception as e:
            return f"计算失败：{e}"
    elif tool_name == "get_weather":
        city = arguments["city"]
        return WEATHER_DB.get(city, f"暂无 {city} 的天气数据")
    elif tool_name == "get_time":
        from datetime import datetime
        return datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
    return f"未知工具：{tool_name}"


def agent_loop(user_query: str, max_steps: int = 5):
    """
    ReAct 循环：
    
    用户提问
      ↓
    ┌→ 思考（模型决定：用哪个工具？还是直接回答？）
    │    ↓
    │  行动（如果需要：调用工具）
    │    ↓
    │  观察（拿到工具返回的结果）
    │    ↓
    └── 还需要继续吗？
         ├── 是 → 回到"思考"
         └── 否 → 给出最终答案
    """
    print(f"\n{'='*60}")
    print(f"用户：{user_query}")
    print("=" * 60)
    
    messages = [{"role": "user", "content": user_query}]
    
    for step in range(1, max_steps + 1):
        print(f"\n--- Step {step} ---")
        
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto"
            )
        except Exception as e:
            print(f"❌ API 调用失败：{str(e)}")
            return f"抱歉，服务暂时不可用：{str(e)}"
        
        msg = response.choices[0].message
        
        if msg.tool_calls:
            print(f"🤔 模型决定调用 {len(msg.tool_calls)} 个工具")
            
            tool_call_records = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                }
                for tc in msg.tool_calls
            ]
            
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": tool_call_records
            })
            
            for tc in msg.tool_calls:
                func_name = tc.function.name
                func_args = json.loads(tc.function.arguments)
                result = execute_tool(func_name, func_args)
                
                print(f"  🔧 {func_name}({func_args})")
                print(f"     → {result[:80]}")
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result
                })
        
        else:
            print(f"✅ 最终回答（第 {step} 步得出）：")
            print(f"   {msg.content}")
            return msg.content
    
    print(f"⚠️ 达到最大步数限制（{max_steps}步），强制终止")
    return "任务未完成（步数超限）"


if __name__ == "__main__":
    print("=" * 60)
    print("实验 5-4 · Step 3：ReAct 循环")
    print("=" * 60)
    
    print("\n\n### 测试 A：一步到位")
    agent_loop("今天广州天气怎么样？")
    
    print("\n\n### 测试 B：多工具并行")
    agent_loop("深圳天气如何？帮我算 88 × 125")
    
    print("\n\n### 测试 C：推理链")
    agent_loop("北京和广州今天哪座城市更适合户外运动？请根据天气给出建议。")
    
    print("\n\n### 测试 D：无需工具")
    agent_loop("请解释一下 Function Calling 是什么。")
```

```bash
cd /root/autodl-tmp/day5
python agent_step3_react_loop.py
```

**ReAct 循环图示**（一边看代码一边理解这张图）：

```
        ┌──────────┐
        │ 用户提问  │
        └────┬─────┘
             ↓
        ┌──────────┐
   ┌──→ │  思考    │ ← 模型决定"下一步做什么"
   │    └────┬─────┘
   │         ↓
   │    ┌──────────┐
   │    │ 调用工具  │ ← 执行具体操作（搜索/计算/查天气）
   │    └────┬─────┘
   │         ↓
   │    ┌──────────┐
   │    │ 观察结果  │ ← 工具返回了什么
   │    └────┬─────┘
   │         ↓
   │    还需要继续吗？
   │    ├── 是 ──→ 回到"思考"
   │    └── 否 ──→ ┌──────────┐
   │               │ 给出答案  │
   │               └──────────┘
```

> 💡 **核心理解**：`max_steps` 参数很重要！真实应用中要设上限，防止 Agent 陷入死循环。

---

### Step 5：对比实验——用不用 Agent 有什么区别（10 分钟）

```python
# 文件：/root/autodl-tmp/day5/agent_step4_compare.py
"""
实验 5-4 Step 4：对比——不用 Agent vs 用 Agent
"""

import json, math, time
from openai import OpenAI

client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key="sk-你的APIKey"
)

test_queries = [
    "1234 × 5678 等于多少？",
    "今天北京天气怎么样？",
    "广州天气如何？帮我算 88 × 125 的结果。",
    "2024 年 2 月有几天？"
]

TOOLS = [
    {"type": "function", "function": {"name": "calculate",
     "description": "执行数学计算",
     "parameters": {"type": "object", "properties": {
         "expression": {"type": "string", "description": "数学表达式"}
     }, "required": ["expression"]}}},
    {"type": "function", "function": {"name": "get_weather",
     "description": "查询天气",
     "parameters": {"type": "object", "properties": {
         "city": {"type": "string", "description": "城市"}
     }, "required": ["city"]}}}
]

print("=" * 70)
print("对比实验：不用 Agent（裸调） vs 用 Agent（Function Calling）")
print("=" * 70)

for query in test_queries:
    print(f"\n{'─'*60}")
    print(f"问题：{query}")
    
    # --- 方法 1：不用 Agent ---
    t1 = time.time()
    resp1 = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": query}],
        max_tokens=100
    )
    t_bare = round(time.time() - t1, 2)
    bare_answer = resp1.choices[0].message.content
    print(f"\n🔵 裸调回答（{t_bare}s）：{bare_answer[:80]}")
    
    # --- 方法 2：用 Agent ---
    t2 = time.time()
    resp2 = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": query}],
        tools=TOOLS,
        tool_choice="auto"
    )
    msg = resp2.choices[0].message
    
    if msg.tool_calls:
        tools_used = [tc.function.name for tc in msg.tool_calls]
        print(f"🟢 Agent：调用了 {tools_used}（工具调用决策耗时 {round(time.time()-t2,2)}s）")
    else:
        print(f"🟢 Agent：直接回答（{round(time.time()-t2,2)}s）：{msg.content[:80]}")
```

```bash
cd /root/autodl-tmp/day5
python agent_step4_compare.py
```

**观察要点**：

| 问题类型 | 裸调 DeepSeek | Agent（Function Calling） |
|---------|-------------|--------------------------|
| 简单数学 | 可能算对，也可能算错（LLM 不擅长精确计算） | ✅ 调用 `calculate`，100% 精确 |
| 天气查询 | "我没有实时信息" | ✅ 调用 `get_weather` |
| 混合问题 | 可能只回答一半 | ✅ 并行调用多个工具，完整回答 |

---

### Step 6：讨论与总结（10 分钟）

**讨论 1：Agent 和普通对话模型最大的不同是什么？**

```
普通模型 = 一个人坐在房间里，只能凭记忆回答问题
Agent = 一个人带着工具箱，能查、能算、能做决策
```

**讨论 2：工具调用失败怎么办？**

- 本实验只做了最简单的 `try/except`
- 实际项目中需要考虑：
  - 工具超时 → 设 timeout
  - 工具返回错误 → 让模型基于错误信息重新决策
  - 工具被滥用 → 限制调用次数和参数范围

**讨论 3：为什么不能直接用 Qwen2.5-1.5B 做这个实验？**

试想一下：如果把上面代码的 `client` 指向本地 vLLM 的 Qwen2.5-1.5B...
- 大概率忽略工具定义，直接凭记忆回答
- JSON 格式可能出错，`json.loads(tool_call.function.arguments)` 会崩
- 这就是 Day6 要用"DeepSeek 决策 + 微调 Qwen 生成"双模型架构的原因

---

## 七、常见问题

| 问题 | 现象 | 解决方案 |
|------|------|----------|
| API 返回 401 | `AuthenticationError` | 检查 API Key 是否正确；确认有余额 |
| 模型不调用工具 | 对于明显需要计算的问题，模型却直接硬算 | 检查 `tool_choice` 是否设为 `"auto"` |
| JSON 解析报错 | `json.JSONDecodeError` | DeepSeek 格式标准，很少出错。如遇到，加 `try/except` |
| 工具调用卡在循环里 | 同一个工具被反复调用 | 加 `max_steps` 限制；检查工具描述是否清晰 |
| `eval` 安全吗？ | 理论上可注入代码 | 本实验用 `{"__builtins__": {}}` 限制了；生产环境用专用计算库 |
| 天气数据是假的 | 模拟数据版本不实时 | 使用 wttr.in 真实 API 版本（Step 3 代码中已提供） |

---

## 八、实验检查清单

- [ ] DeepSeek API 连通测试通过（Step 1）
- [ ] 单个工具（calculate）调用成功，模型能自动判断是否调工具（Step 2）
- [ ] 多工具并存时，模型能正确选择（天气用 `get_weather`、计算用 `calculate`）（Step 3）
- [ ] 混合问题中，模型能并行调用多个工具（Step 3 测试 3）
- [ ] ReAct 循环至少跑了一个需要推理链的测试（Step 4）
- [ ] 对比实验完成，能说出 Agent 比裸调好在哪（Step 5）
- [ ] 所有脚本保存在 `/root/autodl-tmp/day5/agent/agent_*.py`
- [ ] 理解 Day6 预告：Agent + RAG 检索 + 微调模型生成 = 完整系统

---

## 九、课后扩展（选做）

### 挑战 1：添加第 3 个工具

参考天气工具的写法，添加一个 `translate` 工具（中英互译）。提示：

```python
TRANSLATIONS = {
    "你好": "Hello", "谢谢": "Thank you",
    "人工智能": "Artificial Intelligence",
}

def translate(text: str, direction: str = "zh2en"):
    if direction == "zh2en":
        return TRANSLATIONS.get(text, "（未收录）")
    else:
        for zh, en in TRANSLATIONS.items():
            if en.lower() == text.lower():
                return zh
        return "（未收录）"
```

### 挑战 2：记录工具调用日志

```python
import time
tool_log = []

def execute_tool_with_log(tool_name, arguments):
    result = execute_tool(tool_name, arguments)
    tool_log.append({
        "time": time.time(),
        "tool": tool_name,
        "args": arguments,
        "result": result[:100]
    })
    return result
```

### 挑战 3：API 余额监控

```python
def check_balance():
    print("⚠️ 提醒：本实验全程约消耗 0.1-0.3 元")
    print("   在 https://platform.deepseek.com 查看实时余额")
```

---

## 附录 A：LangChain 框架版（选做）

> 📌 **定位说明**：这不是本次课堂要求的内容。课堂上你已经用"原生 API"实现了 Agent，这里展示的是业界流行框架 **LangChain** 是如何把同样的事情封装起来的。对比后你会发现：框架帮你省掉了很多"样板代码"，但核心原理完全一样。
>

---

### A.1 LangChain 是什么？

```
原生 API 方式（你今天做的）：
  你 ──→ OpenAI Client ──→ DeepSeek API
         手动管理消息列表、手动执行工具、手动处理多轮循环

LangChain 框架方式：
  你 ──→ LangChain Agent ──→ OpenAI Client ──→ DeepSeek API
         框架自动管理消息列表、自动执行工具、自动处理 ReAct 循环
```

LangChain 是目前最流行的 LLM 应用开发框架，提供：
- `@tool` 装饰器：3 行代码定义一个工具
- `create_react_agent`（来自 `langgraph.prebuilt`）：自动创建并运行 ReAct Agent，无需手写循环
- 底层基于 LangGraph 有向图，支持复杂流程扩展

---

### A.2 安装依赖

```bash
pip install langchain langchain-openai
```

> ⚠️ **注意**：LangChain 迭代较快，本手册基于 `langgraph>=0.2.0, langchain-openai>=0.1.0` 验证通过。
> 若遇接口报错，优先检查版本；推荐始终使用 `langgraph.prebuilt.create_react_agent`（目前最稳定的写法）。

---

### A.3 LangChain 版完整代码

```python
# 文件：/root/autodl-tmp/day5/agent_langchain_version.py
"""
附录 A：LangChain 框架版 Agent
对比原生 API 版，看看框架帮你省了哪些代码
"""

import math
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# ===== 第 1 步：初始化模型（指向 DeepSeek）=====
# LangChain 的 ChatOpenAI 支持任何兼容 OpenAI 接口的模型
llm = ChatOpenAI(
    model="deepseek-chat",
    openai_api_key="sk-你的APIKey",        # ← 改成你自己的
    openai_api_base="https://api.deepseek.com",
    temperature=0
)

# ===== 第 2 步：用 @tool 装饰器定义工具 =====
# 对比原生版：原来需要写 20 行 JSON 的工具定义，现在只需要 docstring

@tool
def calculate(expression: str) -> str:
    """
    执行数学计算，支持加减乘除、幂运算、三角函数、阶乘等。
    例如：'3*4+2'、'math.factorial(10)'、'math.sqrt(144)'
    """
    allowed = {
        "abs": abs, "round": round, "min": min, "max": max,
        "pow": pow, "sum": sum,
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "sqrt": math.sqrt, "log": math.log, "log10": math.log10,
        "pi": math.pi, "e": math.e,
        "factorial": math.factorial,
        "ceil": math.ceil, "floor": math.floor,
    }
    try:
        result = eval(expression, {"__builtins__": {}}, allowed)
        return f"{expression} = {result}"
    except Exception as e:
        return f"计算失败：{e}"


@tool
def get_weather(city: str) -> str:
    """
    查询指定城市的当前天气信息，返回温度、天气状况、风力等。
    支持城市：北京、上海、广州、深圳、杭州、成都、武汉等。
    """
    import requests, datetime
    CITY_MAP = {
        "北京": "Beijing", "上海": "Shanghai", "广州": "Guangzhou",
        "深圳": "Shenzhen", "杭州": "Hangzhou", "成都": "Chengdu",
        "武汉": "Wuhan", "南京": "Nanjing", "重庆": "Chongqing",
    }
    today = datetime.datetime.now().strftime("%Y年%m月%d日")
    if city not in CITY_MAP:
        return f"{today} | 暂无 {city} 的天气，支持：{', '.join(CITY_MAP.keys())}"
    city_en = CITY_MAP[city]
    try:
        response = requests.get(f"https://wttr.in/{city_en}?format=j1", timeout=10)
        data = response.json()
        current = data["current_condition"][0]
        weather = current["weatherDesc"][0]["value"]
        temp = current["temp_C"]
        humidity = current["humidity"]
        return f"{today} | {city}：{weather}，{temp}℃，湿度{humidity}%"
    except Exception as e:
        return f"{today} | 获取 {city} 天气失败：{e}"


@tool
def get_time() -> str:
    """获取当前的日期和时间"""
    from datetime import datetime
    return datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")


# ===== 第 3 步：把工具组装成 Agent =====
tools = [calculate, get_weather, get_time]

# Prompt 模板（Agent 的"行为说明书"）
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个智能助手，可以使用工具来帮助用户解决问题。"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),  # 存放中间推理步骤
])

# 创建 Agent（自动处理 Function Calling 格式）
agent = create_openai_tools_agent(llm, tools, prompt)

# AgentExecutor = 自动跑 ReAct 循环的执行器
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,      # 打印每一步的推理过程（相当于原生版里你手写的 print）
    max_iterations=5,  # 对应原生版的 max_steps=5
    return_intermediate_steps=True  # 返回中间步骤（方便观察）
)


# ===== 第 4 步：运行 Agent =====
def run_agent(query: str):
    print(f"\n{'='*60}")
    print(f"用户：{query}")
    print("=" * 60)
    
    result = agent_executor.invoke({"input": query})
    
    print(f"\n✅ 最终回答：{result['output']}")
    
    # 查看中间步骤
    if result.get("intermediate_steps"):
        print(f"\n📊 共调用了 {len(result['intermediate_steps'])} 次工具")
    
    return result["output"]


if __name__ == "__main__":
    print("=" * 60)
    print("附录 A：LangChain 框架版 Agent 演示")
    print("=" * 60)
    
    # 同样的测试用例，看结果和原生版有没有差别
    run_agent("今天广州天气怎么样？另外帮我算一下 156 × 23 等于多少。")
    run_agent("北京和广州今天哪座城市更适合户外运动？请根据天气给出建议。")
    run_agent("现在几点了？25 的 3 次方是多少？")
```

```bash
cd /root/autodl-tmp/day5
python agent_langchain_version.py
```

---

### A.4 原生 API vs LangChain 对比

运行后，对比两个版本：

| 对比维度 | 原生 API 版（今天课堂做的） | LangChain 框架版（附录） |
|---------|--------------------------|------------------------|
| 工具定义 | 手写 20 行 JSON Schema | `@tool` 装饰器 + docstring，3 行搞定 |
| ReAct 循环 | 手写 `for step in range(max_steps)` | `AgentExecutor` 自动处理 |
| 消息历史管理 | 手动 `messages.append(...)` | 框架自动维护 |
| 代码量 | ~150 行 | ~60 行 |
| 可见度 | 每一步都能看到，适合学习 | 框架内部处理，适合生产 |
| 灵活性 | 完全可控 | 受框架约束 |
| 出错时 | 报错直接定位到你的代码 | 报错可能来自框架内部，较难 debug |

> 💡 **学习建议**：先掌握原生 API，理解底层原理；再用 LangChain 提效。就像学开车要先学手动挡，再开自动挡。

---

### A.5 LangGraph 简介（进阶了解）

如果你对 **LangGraph** 感兴趣，它是 LangChain 的"升级版"，专门用于构建有状态的复杂 Agent：

```
LangChain AgentExecutor：线性的 ReAct 循环
  思考 → 行动 → 观察 → 思考 → ...

LangGraph：有向图结构，支持分支、并行、循环
  ┌→ 分支 A（调用工具 1）─┐
  │                       ↓
  │  分支 B（调用工具 2）─→ 汇合 → 输出
  └→ 条件跳转 ────────────┘
```

适合场景：
- 复杂的多 Agent 协作系统
- 需要条件分支的任务流（比如：如果天气下雨，则推荐室内活动；否则推荐户外）
- 大作业方向 B 的进阶版实现

**LangGraph 最简示例**（仅供了解，不要求跑通）：

```python
from langgraph.prebuilt import create_react_agent

# 和 LangChain 很像，但底层用图结构实现，更灵活
app = create_react_agent(llm, tools=tools)
result = app.invoke({"messages": [("human", "广州天气如何？")]})
print(result["messages"][-1].content)
```

> 参考文档：https://langchain-ai.github.io/langgraph/

