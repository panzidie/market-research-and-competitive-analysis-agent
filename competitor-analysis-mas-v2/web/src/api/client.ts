// web/src/api/client.ts — HTTP API 客户端

const API_BASE = import.meta.env.VITE_API_BASE || "";

export async function fetchSessions() {
  const res = await fetch(`${API_BASE}/api/sessions`);
  if (!res.ok) throw new Error("获取会话列表失败");
  return res.json();
}

export async function fetchSessionHistory(sessionId: string) {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/history`);
  if (!res.ok) throw new Error("获取会话历史失败");
  return res.json();
}

export async function deleteSession(sessionId: string) {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("删除会话失败");
  return res.json();
}

export async function fetchReports() {
  const res = await fetch(`${API_BASE}/api/reports`);
  if (!res.ok) throw new Error("获取报告列表失败");
  return res.json();
}

export async function fetchReport(productName: string) {
  const res = await fetch(`${API_BASE}/api/reports/${encodeURIComponent(productName)}`);
  if (!res.ok) throw new Error("获取报告失败");
  return res.text();
}

export async function healthCheck() {
  const res = await fetch(`${API_BASE}/api/health`);
  if (!res.ok) throw new Error("后端不可用");
  return res.json();
}
