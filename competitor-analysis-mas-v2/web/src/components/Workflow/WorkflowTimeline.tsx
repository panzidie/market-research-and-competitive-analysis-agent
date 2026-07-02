// web/src/components/Workflow/WorkflowTimeline.tsx

import { useAppContext } from "../../context/AppContext";
import { StageCard } from "./StageCard";
import { ReactPanel } from "./ReactPanel";
import { useEffect, useState } from "react";

export function WorkflowTimeline() {
  const { state } = useAppContext();
  const { currentStages, activeWorkflow, reactEvents } = state;
  const [elapsed, setElapsed] = useState(0);

  const isRunning = currentStages.some((s) => s.status === "running") || state.isStreaming;

  useEffect(() => {
    if (!isRunning) {
      setElapsed(0);
      return;
    }
    const start = Date.now();
    const timer = setInterval(() => setElapsed(Date.now() - start), 100);
    return () => clearInterval(timer);
  }, [isRunning]);

  const isVisible = isRunning || currentStages.some((s) => s.status === "completed");

  if (!isVisible) return null;

  const productName = activeWorkflow?.product || "竞品分析";

  return (
    <div className="workflow-timeline">
      <div className="timeline-header">
        <span className="timeline-title">📋 {productName}</span>
        <span className="timeline-timer">
          {elapsed > 0 && `⏱ ${(elapsed / 1000).toFixed(1)}s`}
        </span>
      </div>
      <div className="stage-row">
        {currentStages.map((stage, i) => (
          <>
            <StageCard key={stage.name} stage={stage} />
            {i < currentStages.length - 1 && <span className="stage-arrow">→</span>}
          </>
        ))}
      </div>
      {reactEvents.length > 0 && <ReactPanel events={reactEvents} />}
    </div>
  );
}
