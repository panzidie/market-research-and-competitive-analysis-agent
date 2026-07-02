// web/src/components/Chat/SessionList.tsx

import { useAppContext } from "../../context/AppContext";

export function SessionList() {
  const { state, dispatch } = useAppContext();

  const handleNewSession = () => {
    dispatch({ type: "NEW_SESSION" });
  };

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <span>💬</span>
        <span>会话</span>
        <button
          className="toolbar-btn"
          onClick={handleNewSession}
          title="新建会话"
          style={{ marginLeft: "auto", padding: "4px 8px" }}
        >
          ＋
        </button>
      </div>
      <div className="sidebar-list">
        <div className="session-item" style={{ fontWeight: 500, color: "var(--text-primary)" }}>
          <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{
              width: 8, height: 8, borderRadius: "50%",
              background: state.isConnected ? "var(--success)" : "var(--error)",
              display: "inline-block",
            }} />
            {state.isConnected ? "已连接" : "未连接"}
          </span>
        </div>
        <div className="session-item" style={{ color: "var(--text-muted)", fontSize: 12, marginTop: 8 }}>
          当前会话: {state.sessionId.slice(0, 8)}...
        </div>
      </div>
    </div>
  );
}
