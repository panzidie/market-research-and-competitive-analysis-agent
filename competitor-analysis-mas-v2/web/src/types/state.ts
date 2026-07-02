// web/src/types/state.ts — 应用状态类型

import type { Message, StageState, ReActEvent, WorkflowState } from "./events";

export interface AppState {
  sessionId: string;
  theme: "dark" | "light";
  isConnected: boolean;
  isStreaming: boolean;
  messages: Message[];
  activeWorkflow: WorkflowState | null;
  reactEvents: ReActEvent[];
  currentStages: StageState[];
  error: string | null;
}

export type AppAction =
  | { type: "SET_SESSION_ID"; payload: string }
  | { type: "SET_CONNECTED"; payload: boolean }
  | { type: "SET_STREAMING"; payload: boolean }
  | { type: "ADD_MESSAGE"; payload: Message }
  | { type: "WORKFLOW_START"; payload: Record<string, unknown> }
  | { type: "STAGE_START"; payload: Record<string, unknown> }
  | { type: "STAGE_COMPLETE"; payload: Record<string, unknown> }
  | { type: "WORKFLOW_COMPLETE"; payload?: Record<string, unknown> }
  | { type: "WORKFLOW_ERROR"; payload: string }
  | { type: "APPEND_REACT_EVENT"; payload: ReActEvent }
  | { type: "SET_THEME"; payload: "dark" | "light" }
  | { type: "SET_ERROR"; payload: string | null }
  | { type: "NEW_SESSION" };
