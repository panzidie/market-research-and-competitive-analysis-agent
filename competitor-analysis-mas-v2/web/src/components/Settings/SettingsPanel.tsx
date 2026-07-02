// web/src/components/Settings/SettingsPanel.tsx

import { useState } from "react";
import { useAppContext } from "../../context/AppContext";

interface Props {
  onClose: () => void;
}

export function SettingsPanel({ onClose }: Props) {
  const { state, dispatch } = useAppContext();
  const [theme, setTheme] = useState(state.theme);

  const handleThemeChange = (t: "dark" | "light") => {
    setTheme(t);
    dispatch({ type: "SET_THEME", payload: t });
    document.documentElement.setAttribute("data-theme", t);
    localStorage.setItem("theme", t);
  };

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-panel" onClick={(e) => e.stopPropagation()}>
        <div className="settings-title">
          <span>⚙️ 设置</span>
          <button className="settings-close" onClick={onClose}>✕</button>
        </div>

        <div className="settings-group">
          <label className="settings-label">主题</label>
          <select
            className="settings-select"
            value={theme}
            onChange={(e) => handleThemeChange(e.target.value as "dark" | "light")}
          >
            <option value="dark">暗色</option>
            <option value="light">亮色</option>
          </select>
        </div>

        <div className="settings-group">
          <label className="settings-label">当前会话 ID</label>
          <input className="settings-input" value={state.sessionId} readOnly />
        </div>

        <div className="settings-group">
          <label className="settings-label">连接状态</label>
          <div style={{ fontSize: 13, display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{
              width: 8, height: 8, borderRadius: "50%",
              background: state.isConnected ? "var(--success)" : "var(--error)",
              display: "inline-block",
            }} />
            {state.isConnected ? "已连接" : "未连接"}
          </div>
        </div>

        <div className="settings-group">
          <label className="settings-label">消息数</label>
          <div style={{ fontSize: 13 }}>{state.messages.length} 条</div>
        </div>
      </div>
    </div>
  );
}
