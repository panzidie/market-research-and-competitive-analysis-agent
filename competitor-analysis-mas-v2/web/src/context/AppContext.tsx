// web/src/context/AppContext.tsx — 全局状态管理

import { createContext, useContext, useReducer } from "react";
import type { ReactNode } from "react";
import type { AppState, AppAction } from "../types/state";
import type { StageState } from "../types/events";

function generateSessionId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

const STAGES_TEMPLATE: StageState[] = [
  { name: "discovery", label: "竞品发现", status: "pending", stageIndex: 0, totalStages: 4 },
  { name: "collection", label: "数据采集", status: "pending", stageIndex: 1, totalStages: 4 },
  { name: "parallel_analysis", label: "并行分析", status: "pending", stageIndex: 2, totalStages: 4 },
  { name: "strategy", label: "策略建议", status: "pending", stageIndex: 3, totalStages: 4 },
];

function resetStages(): StageState[] {
  return STAGES_TEMPLATE.map((s) => ({ ...s }));
}

const initialState: AppState = {
  sessionId: generateSessionId(),
  theme: "dark",
  isConnected: false,
  isStreaming: false,
  messages: [],
  activeWorkflow: null,
  reactEvents: [],
  currentStages: resetStages(),
  error: null,
};

function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case "SET_SESSION_ID":
      return { ...state, sessionId: action.payload };
    case "SET_CONNECTED":
      return { ...state, isConnected: action.payload };
    case "SET_STREAMING":
      return { ...state, isStreaming: action.payload };
    case "ADD_MESSAGE":
      return { ...state, messages: [...state.messages, action.payload] };
    case "WORKFLOW_START": {
      const wp = action.payload as Record<string, unknown>;
      const product = typeof wp.product === "string" ? wp.product : "竞品分析";
      return {
        ...state,
        isStreaming: true,
        activeWorkflow: {
          product,
          stages: resetStages(),
          currentStageIdx: 0,
          startedAt: Date.now(),
        },
        currentStages: resetStages(),
        reactEvents: [],
      };
    }
    case "STAGE_START": {
      const { stage: stageName } = action.payload as Record<string, string>;
      const stages = state.currentStages.map((s) => ({
        ...s,
        status: (s.name === stageName ? "running" : s.status === "completed" ? "completed" : "pending") as StageState["status"],
      }));
      return {
        ...state,
        currentStages: stages,
        activeWorkflow: state.activeWorkflow
          ? { ...state.activeWorkflow, stages, currentStageIdx: stages.findIndex((s) => s.name === stageName) }
          : null,
      };
    }
    case "STAGE_COMPLETE": {
      const p = action.payload as Record<string, unknown>;
      const stage = p.stage as string;
      const stages = state.currentStages.map((s) =>
        s.name === stage
          ? {
              ...s,
              status: "completed" as const,
              elapsedMs: typeof p.elapsed_s === "number" ? Math.round(p.elapsed_s * 1000) : undefined,
              summary: typeof p.result_summary === "string" ? p.result_summary : undefined,
              competitors: Array.isArray(p.competitors) ? p.competitors as { name: string; brief: string }[] : undefined,
              competitorCount: typeof p.competitor_count === "number" ? p.competitor_count : undefined,
              actionPlanCount: typeof p.action_plan_count === "number" ? p.action_plan_count : undefined,
            }
          : s
      );
      return { ...state, currentStages: stages };
    }
    case "WORKFLOW_COMPLETE": {
      return {
        ...state,
        isStreaming: false,
        activeWorkflow: null,
        currentStages: state.currentStages.map((s) => ({ ...s, status: "completed" as const })),
      };
    }
    case "WORKFLOW_ERROR": {
      return {
        ...state,
        isStreaming: false,
        error: typeof action.payload === "string" ? action.payload : "工作流执行出错",
      };
    }
    case "APPEND_REACT_EVENT": {
      return {
        ...state,
        reactEvents: [...state.reactEvents, action.payload],
      };
    }
    case "SET_THEME":
      return { ...state, theme: action.payload };
    case "SET_ERROR":
      return { ...state, error: action.payload };
    case "NEW_SESSION":
      return {
        ...state,
        sessionId: generateSessionId(),
        messages: [],
        currentStages: resetStages(),
        reactEvents: [],
        isStreaming: false,
        error: null,
      };
    default:
      return state;
  }
}

interface AppContextType {
  state: AppState;
  dispatch: (action: AppAction) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, initialState);
  return <AppContext.Provider value={{ state, dispatch }}>{children}</AppContext.Provider>;
}

export function useAppContext() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useAppContext 必须在 AppProvider 内使用");
  return ctx;
}
