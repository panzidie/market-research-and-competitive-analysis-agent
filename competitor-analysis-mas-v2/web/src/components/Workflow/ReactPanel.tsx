// web/src/components/Workflow/ReactPanel.tsx

import { useState } from "react";
import type { ReActEvent } from "../../types/events";

interface ReactPanelProps {
  events: ReActEvent[];
}

export function ReactPanel({ events }: ReactPanelProps) {
  const [collapsed, setCollapsed] = useState(false);

  if (events.length === 0) return null;

  return (
    <div className="react-panel">
      <div className="react-panel-header" onClick={() => setCollapsed(!collapsed)}>
        <span>{collapsed ? "▶" : "▼"}</span>
        <span>ReAct 推理过程 ({events.length} 步)</span>
      </div>
      {!collapsed && (
        <div>
          {events.map((evt, i) => (
            <div key={i} className={`react-event ${evt.type}`}>
              <div className={`react-event-label ${evt.type}`}>
                {evt.type === "thought" && "💭 Thought"}
                {evt.type === "action" && "🔧 Action"}
                {evt.type === "observation" && "👁 Observation"}
                {evt.agentName && ` — ${evt.agentName}`}
                {evt.toolName && ` → ${evt.toolName}`}
              </div>
              <div className="react-event-content">
                {evt.type === "thought" && evt.thought}
                {evt.type === "action" && evt.toolInput && JSON.stringify(evt.toolInput, null, 2)}
                {evt.type === "observation" && (
                  <>
                    <div>返回长度: {evt.resultLength} 字符</div>
                    {evt.resultPreview && <div style={{ marginTop: 4 }}>{evt.resultPreview.slice(0, 300)}...</div>}
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
