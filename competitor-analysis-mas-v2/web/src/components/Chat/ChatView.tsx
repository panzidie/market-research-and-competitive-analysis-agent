// web/src/components/Chat/ChatView.tsx

import { useEffect, useRef } from "react";
import { useAppContext } from "../../context/AppContext";
import { MessageBubble } from "./MessageBubble";
import { WorkflowTimeline } from "../Workflow/WorkflowTimeline";

export function ChatView() {
  const { state } = useAppContext();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [state.messages, state.currentStages]);

  if (state.messages.length === 0) {
    return (
      <div className="empty-state">
        <h2>🤖 智能竞品分析助手</h2>
        <p>
          输入产品名称即可自动进行竞品分析，或直接提问进行通用对话。<br />
          试试说「帮我分析飞书」或「你好」。
        </p>
        <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 8 }}>
          {state.isConnected ? "🟢 已连接" : "🔴 未连接"}
        </div>
      </div>
    );
  }

  return (
    <>
      <WorkflowTimeline />
      <div className="chat-view">
        {state.messages.map((msg, i) => (
          <MessageBubble key={msg.id || i} message={msg} />
        ))}
        <div ref={bottomRef} />
      </div>
    </>
  );
}
