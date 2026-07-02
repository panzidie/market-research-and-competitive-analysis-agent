// web/src/main.tsx — 入口文件

import React from "react";
import ReactDOM from "react-dom/client";
import { AppProvider } from "./context/AppContext";
import { ErrorBoundary } from "./components/common/ErrorBoundary";
import App from "./App";

// 恢复主题偏好
const savedTheme = localStorage.getItem("theme") as "dark" | "light" | null;
if (savedTheme) {
  document.documentElement.setAttribute("data-theme", savedTheme);
} else {
  document.documentElement.setAttribute("data-theme", "dark");
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <AppProvider>
        <App />
      </AppProvider>
    </ErrorBoundary>
  </React.StrictMode>
);
