// web/src/components/Chat/ChatInput.tsx

import { useState, useRef, useEffect } from "react";
import type { KeyboardEvent } from "react";
import { useAppContext } from "../../context/AppContext";

interface Props {
  onSend: (content: string) => void;
  onStop: () => void;
}

export function ChatInput({ onSend, onStop }: Props) {
  const { state } = useAppContext();
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!state.isStreaming && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [state.isStreaming]);

  const adjustHeight = () => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 120) + "px";
    }
  };

  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed || state.isStreaming) return;
    onSend(trimmed);
    setText("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-input-area">
      <div className="chat-input-wrapper">
        <textarea
          ref={textareaRef}
          className="chat-input"
          placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
          value={text}
          onChange={(e) => { setText(e.target.value); adjustHeight(); }}
          onKeyDown={handleKeyDown}
          disabled={state.isStreaming}
          rows={1}
        />
        {state.isStreaming ? (
          <button className="stop-btn" onClick={onStop}>
            ■ 停止
          </button>
        ) : (
          <button className="send-btn" onClick={handleSend} disabled={!text.trim()}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}
