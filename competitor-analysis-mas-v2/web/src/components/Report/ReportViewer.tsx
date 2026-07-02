// web/src/components/Report/ReportViewer.tsx

import { fetchReport } from "../../api/client";
import { useState, useEffect } from "react";

interface Props {
  productName: string;
  onClose: () => void;
}

export function ReportViewer({ productName, onClose }: Props) {
  const [html, setHtml] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchReport(productName)
      .then((content) => {
        setHtml(content);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [productName]);

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div style={{
        width: "90%", height: "100%", background: "var(--bg-primary)",
        display: "flex", flexDirection: "column",
      }} onClick={(e) => e.stopPropagation()}>
        <div style={{
          padding: "12px 24px", borderBottom: "1px solid var(--border-color)",
          display: "flex", alignItems: "center", justifyContent: "space-between",
        }}>
          <span style={{ fontWeight: 600 }}>📄 {productName} 分析报告</span>
          <button onClick={onClose} style={{
            background: "none", border: "none", color: "var(--text-secondary)",
            cursor: "pointer", fontSize: 18,
          }}>✕</button>
        </div>
        <div style={{ flex: 1, overflow: "auto" }}>
          {loading && (
            <div className="empty-state">
              <p>加载报告中...</p>
            </div>
          )}
          {error && (
            <div className="empty-state">
              <p style={{ color: "var(--error)" }}>加载失败: {error}</p>
            </div>
          )}
          {html && !loading && (
            <iframe
              srcDoc={html}
              style={{ width: "100%", height: "100%", border: "none" }}
              title="分析报告"
            />
          )}
        </div>
      </div>
    </div>
  );
}
