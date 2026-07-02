// web/src/types/events.ts — TypeScript 事件类型定义

export const EventType = {
  SESSION_STARTED: "session_started",
  SESSION_ENDED: "session_ended",
  USER_MESSAGE: "user_message",
  ASSISTANT_MESSAGE: "assistant_message",
  WORKFLOW_STARTED: "workflow_started",
  STAGE_STARTED: "stage_started",
  STAGE_COMPLETED: "stage_completed",
  WORKFLOW_COMPLETED: "workflow_completed",
  WORKFLOW_ERROR: "workflow_error",
  AGENT_PROGRESS: "agent_progress",
  REACT_STARTED: "react_started",
  REACT_THOUGHT: "react_thought",
  REACT_ACTION: "react_action",
  REACT_OBSERVATION: "react_observation",
  REACT_ENDED: "react_ended",
  REPORT_GENERATED: "report_generated",
  SYSTEM_INFO: "system_info",
  HEARTBEAT: "heartbeat",
} as const;

export type EventType = (typeof EventType)[keyof typeof EventType];

export interface WSEvent {
  event_type: string;
  session_id: string;
  timestamp: number;
  payload: Record<string, unknown>;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: number;
}

export interface WorkflowState {
  product: string;
  stages: StageState[];
  currentStageIdx: number;
  startedAt: number;
}

export type StageStatus = "pending" | "running" | "completed" | "error";

export interface StageState {
  name: string;
  label: string;
  status: StageStatus;
  stageIndex: number;
  totalStages: number;
  elapsedMs?: number;
  summary?: string;
  competitors?: { name: string; brief: string }[];
  competitorCount?: number;
  actionPlanCount?: number;
}

export interface ReActEvent {
  type: "thought" | "action" | "observation";
  timestamp: number;
  agentName?: string;
  thought?: string;
  toolName?: string;
  toolInput?: Record<string, unknown>;
  resultPreview?: string;
  resultLength?: number;
  callIndex?: number;
}

export interface ReportSummary {
  product_name: string;
  competitor_count: number;
  html_path?: string;
}
