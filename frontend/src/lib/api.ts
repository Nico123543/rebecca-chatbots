import type { PublicConfig, SessionSnapshot, SystemEvent } from "../types";

const apiBase = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed with ${response.status}`);
  }

  return (await response.json()) as T;
}

export const api = {
  getConfig: () => request<PublicConfig>("/api/config"),
  getCurrentSession: () => request<SessionSnapshot>("/api/session/current"),
  startSession: () => request<SessionSnapshot>("/api/session/start", { method: "POST" }),
  pauseSession: () => request<SessionSnapshot>("/api/session/pause", { method: "POST" }),
  resumeSession: () => request<SessionSnapshot>("/api/session/resume", { method: "POST" }),
  stopSession: () => request<SessionSnapshot>("/api/session/stop", { method: "POST" }),
  sendFragment: (rawText: string) =>
    request<SessionSnapshot>("/api/fragments", {
      method: "POST",
      body: JSON.stringify({ rawText })
    })
};

export function openSessionStream(sessionId: string, onEvent: (event: SystemEvent) => void) {
  const wsBase = apiBase.replace(/^http/, "ws");
  const socket = new WebSocket(`${wsBase}/api/session/${sessionId}/stream`);
  socket.onmessage = (message) => {
    const data = JSON.parse(message.data) as SystemEvent;
    onEvent(data);
  };
  return socket;
}
