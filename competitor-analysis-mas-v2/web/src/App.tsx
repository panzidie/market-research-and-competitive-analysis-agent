// web/src/App.tsx — 根组件

import { useState } from "react";
import { useAppContext } from "./context/AppContext";
import { useWebSocket } from "./hooks/useWebSocket";
import { SessionList } from "./components/Chat/SessionList";
import { ChatView } from "./components/Chat/ChatView";
import { ChatInput } from "./components/Chat/ChatInput";
import { SettingsPanel } from "./components/Settings/SettingsPanel";
import "./styles/globals.css";

function App() {
  const { state } = useAppContext();
  const { sendMessage, stopExecution } = useWebSocket();
  const [showSettings, setShowSettings] = useState(false);

  return (
    <div className="app-layout" data-theme={state.theme}>
      <SessionList />
      <div className="main-area">
        <div className="connection-bar">
          <span className={`connection-dot ${state.isConnected ? "connected" : "disconnected"}`} />
          <span>{state.isConnected ? "已连接" : "未连接"}</span>
          <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
            <button className="toolbar-btn" onClick={() => setShowSettings(true)}>
              ⚙️ 设置
            </button>
          </div>
        </div>
        <ChatView />
        <ChatInput onSend={sendMessage} onStop={stopExecution} />
      </div>
      {showSettings && <SettingsPanel onClose={() => setShowSettings(false)} />}
    </div>
  );
}

export default App;
