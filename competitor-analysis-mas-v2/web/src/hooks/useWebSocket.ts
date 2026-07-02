// web/src/hooks/useWebSocket.ts — WebSocket 连接管理

import { useEffect, useRef, useCallback } from "react";
import { useAppContext } from "../context/AppContext";
import type { WSEvent, ReActEvent } from "../types/events";
import { EventType } from "../types/events";

export function useWebSocket() {
  const { state, dispatch } = useAppContext();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const isMounted = useRef(true);

  const sendMessage = useCallback((content: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: "chat", content }));
    }
  }, []);

  const stopExecution = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: "stop" }));
    }
  }, []);

  useEffect(() => {
    isMounted.current = true;

    const connect = () => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }

      const base = import.meta.env.VITE_WS_URL || `ws://localhost:8000`;
      const url = `${base}/ws/${state.sessionId}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (isMounted.current) {
          dispatch({ type: "SET_CONNECTED", payload: true });
        }
      };

      ws.onmessage = (event) => {
        if (!isMounted.current) return;
        try {
          const evt: WSEvent = JSON.parse(event.data);
          const { payload } = evt;
          const content = typeof payload.content === "string" ? payload.content : "";
          const error = typeof payload.error === "string" ? payload.error : "未知错误";
          const level = typeof payload.level === "string" ? payload.level : "";
          const message = typeof payload.message === "string" ? payload.message : "";

          switch (evt.event_type) {
            case EventType.USER_MESSAGE:
              dispatch({ type: "ADD_MESSAGE", payload: {
                id: `msg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
                role: "user", content, timestamp: evt.timestamp,
              }});
              break;
            case EventType.ASSISTANT_MESSAGE:
              dispatch({ type: "SET_STREAMING", payload: false });
              dispatch({ type: "ADD_MESSAGE", payload: {
                id: `msg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
                role: "assistant", content, timestamp: evt.timestamp,
              }});
              break;
            case EventType.WORKFLOW_STARTED:
              dispatch({ type: "WORKFLOW_START", payload });
              break;
            case EventType.STAGE_STARTED:
              dispatch({ type: "STAGE_START", payload });
              break;
            case EventType.STAGE_COMPLETED:
              dispatch({ type: "STAGE_COMPLETE", payload });
              break;
            case EventType.WORKFLOW_COMPLETED:
              dispatch({ type: "WORKFLOW_COMPLETE", payload });
              dispatch({ type: "SET_STREAMING", payload: false });
              break;
            case EventType.WORKFLOW_ERROR:
              dispatch({ type: "WORKFLOW_ERROR", payload: error });
              dispatch({ type: "SET_STREAMING", payload: false });
              break;
            case EventType.REACT_THOUGHT:
            case EventType.REACT_ACTION:
            case EventType.REACT_OBSERVATION: {
              const re: ReActEvent = {
                type: evt.event_type === EventType.REACT_THOUGHT ? "thought"
                  : evt.event_type === EventType.REACT_ACTION ? "action" : "observation",
                timestamp: evt.timestamp,
                ...(payload as unknown as Record<string, unknown>),
              } as unknown as ReActEvent;
              dispatch({ type: "APPEND_REACT_EVENT", payload: re });
              break;
            }
            case EventType.SYSTEM_INFO:
              if (level === "warning") {
                dispatch({ type: "ADD_MESSAGE", payload: {
                  id: `sys-${Date.now()}`,
                  role: "system", content: `⚠️ ${message}`, timestamp: evt.timestamp,
                }});
              }
              break;
            case EventType.HEARTBEAT:
            case EventType.SESSION_STARTED:
            case EventType.REPORT_GENERATED:
              break;
          }
        } catch (e) {
          console.error("WS 消息解析失败:", e);
        }
      };

      ws.onclose = () => {
        if (isMounted.current) {
          dispatch({ type: "SET_CONNECTED", payload: false });
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    };

    connect();

    return () => {
      isMounted.current = false;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
  }, [state.sessionId, dispatch]);

  return { sendMessage, stopExecution, isConnected: state.isConnected };
}
