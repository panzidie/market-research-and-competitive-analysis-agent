// web/src/components/Workflow/StageCard.tsx

import type { StageState } from "../../types/events";

interface StageCardProps {
  stage: StageState;
}

const stageIcons: Record<string, string> = {
  discovery: "🔍",
  collection: "📊",
  parallel_analysis: "⚡",
  strategy: "🎯",
};

export function StageCard({ stage }: StageCardProps) {
  const { name, label, status, elapsedMs, summary } = stage;

  const statusIcon = () => {
    switch (status) {
      case "running":
        return (
          <svg className="stage-status-icon running" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 6v6l4 2" strokeLinecap="round" />
          </svg>
        );
      case "completed":
        return (
          <svg className="stage-status-icon" viewBox="0 0 24 24" fill="none" stroke="var(--success)" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <path d="M9 12l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        );
      case "error":
        return (
          <svg className="stage-status-icon" viewBox="0 0 24 24" fill="none" stroke="var(--error)" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <path d="M15 9l-6 6M9 9l6 6" strokeLinecap="round" />
          </svg>
        );
      default:
        return (
          <svg className="stage-status-icon" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="2">
            <circle cx="12" cy="12" r="10" strokeDasharray="4 3" />
          </svg>
        );
    }
  };

  const statusText = () => {
    switch (status) {
      case "running": return "进行中";
      case "completed": return elapsedMs ? `${(elapsedMs / 1000).toFixed(1)}s` : "完成";
      case "error": return "失败";
      default: return "待执行";
    }
  };

  return (
    <div className={`stage-card ${status}`}>
      <div className="stage-name">
        <span>{stageIcons[name] || "•"}</span>
        <span>{label}</span>
        <span style={{ marginLeft: "auto", fontSize: 11, color: "var(--text-muted)" }}>
          {statusText()}
        </span>
        {statusIcon()}
      </div>
      {summary && status === "completed" && (
        <div className="stage-meta" style={{ marginTop: 4 }}>
          {summary}
        </div>
      )}
    </div>
  );
}
