# 智能竞品分析系统 — 前端界面

基于 React + TypeScript + Vite 构建的智能竞品分析系统 Web 前端，提供实时工作流可视化的对话界面。

## 目录结构

```
web/
├── public/                        # 静态资源
├── src/
│   ├── api/
│   │   └── client.ts              # HTTP API 客户端
│   ├── components/
│   │   ├── Chat/                  # 聊天组件
│   │   │   ├── ChatView.tsx       # 消息列表容器
│   │   │   ├── MessageBubble.tsx  # 消息气泡（用户/助手/系统）
│   │   │   ├── ChatInput.tsx      # 输入框 + 发送/停止按钮
│   │   │   └── SessionList.tsx    # 左侧会话栏
│   │   ├── Workflow/              # 工作流可视化
│   │   │   ├── WorkflowTimeline.tsx   # 四阶段时间线（discovery→collection→parallel_analysis→strategy）
│   │   │   ├── StageCard.tsx          # 单阶段卡片（状态、耗时、摘要）
│   │   │   └── ReactPanel.tsx         # ReAct 推理过程面板（Thought→Action→Observation）
│   │   ├── Report/
│   │   │   └── ReportViewer.tsx       # HTML 分析报告查看器
│   │   ├── Settings/
│   │   │   └── SettingsPanel.tsx      # 设置面板（主题切换、连接状态）
│   │   └── common/
│   │       ├── ErrorBoundary.tsx      # 错误边界
│   │       └── LoadingSpinner.tsx     # 加载动画
│   ├── context/
│   │   └── AppContext.tsx             # 全局状态管理（useReducer）
│   ├── hooks/
│   │   └── useWebSocket.ts           # WebSocket 连接管理 Hook
│   ├── types/
│   │   ├── events.ts                 # 事件类型定义（18 种事件）
│   │   └── state.ts                  # 应用状态类型
│   ├── styles/
│   │   └── globals.css               # 全局样式（暗色/亮色主题）
│   ├── App.tsx                       # 根组件
│   └── main.tsx                      # 入口文件
├── index.html
├── vite.config.ts                    # Vite 配置（含 API 代理）
├── package.json
└── tsconfig*.json
```

## 启动方式

### 开发模式

```bash
cd web
npm install
npm run dev
```

前端默认运行在 `http://localhost:5173`，Vite 自动代理 `/api` 和 `/ws` 到 `http://localhost:8000`（后端）。

### 生产模式

```bash
npm run build      # 构建产物到 dist/
```

由后端 FastAPI 自动托管 `dist/` 目录：

```bash
python backend/main.py
# 访问 http://localhost:8000 即可
```

## 架构说明

### 实时事件流

前端通过 WebSocket 与服务端建立长连接，接收实时工作流事件：

```
连接: ws://localhost:8000/ws/{session_id}

发送: {"action": "chat", "content": "帮我分析飞书"}
接收: {"event_type": "workflow_started", "payload": {...}}
     {"event_type": "stage_started", "payload": {"stage": "discovery", ...}}
     {"event_type": "stage_completed", "payload": {"stage": "discovery", ...}}
     {"event_type": "react_thought", "payload": {...}}  // ReAct 推理
     {"event_type": "react_action", "payload": {...}}   // 工具调用
     {"event_type": "react_observation", "payload": {...}} // 工具返回
     {"event_type": "assistant_message", "payload": {"content": "..."}}
```

### 核心事件类型

| 事件 | 说明 |
|------|------|
| `workflow_started` | 竞品分析管道启动 |
| `stage_started` | 单个阶段开始（discovery/collection/parallel_analysis/strategy） |
| `stage_completed` | 阶段完成（含耗时和结果摘要） |
| `react_thought/action/observation` | ReAct 循环详细过程 |
| `assistant_message` | 最终助手回复 |
| `workflow_completed` | 整个管道完成 |
| `workflow_error` | 管道异常 |

### 工作流可视化

页面顶部会展示四阶段时间线：

```
[竞品发现] → [数据采集] → [并行分析] → [策略建议]
  ✅ 3.2s       🔄进行中      ⏳待执行      ⏳待执行
```

- **竞品发现** - 搜索并识别竞品
- **数据采集** - 逐竞品采集功能/定价/市场信息（含 ReAct 推理面板）
- **并行分析** - 产品分析 + 定价分析 + 市场分析 三路并行
- **策略建议** - 生成差异化策略和行动方案

## 技术栈

- **框架**: React 19 + TypeScript 5
- **构建**: Vite 8
- **状态管理**: React Context + useReducer
- **实时通信**: WebSocket
