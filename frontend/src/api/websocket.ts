/**
 * WebSocket client for live run events.
 *
 * Connects to `/api/v1/ws/runs/{runId}`, replays persisted events since the
 * last observed sequence, then streams live events.  Reconnects with
 * exponential backoff and emits a heartbeat (`ping`) to keep the socket open.
 */

import { getAccessToken } from "@/lib/supabase";

export interface RunEventMessage {
  run_id?: string;
  seq?: number;
  type?: string;
  stage?: string | null;
  status?: string | null;
  summary?: Record<string, unknown> | null;
  payload?: Record<string, unknown> | null;
  ts?: string;
}

export interface RunEventsOptions {
  lastSeq?: number;
  onEvent?: (event: RunEventMessage) => void;
  onStatus?: (status: "connecting" | "open" | "closed") => void;
  maxRetries?: number;
  retryBaseMs?: number;
}

export function getWsBaseUrl(): string {
  const configured = import.meta.env.VITE_WS_BASE_URL as string | undefined;
  const httpBase = (configured ?? "ws://localhost:8000/api/v1").replace(/\/+$/, "");
  if (httpBase.startsWith("ws://") || httpBase.startsWith("wss://")) return httpBase;
  return httpBase.replace(/^http/, "ws");
}

export function connectRunEvents(runId: string, options: RunEventsOptions = {}): () => void {
  const { onEvent, onStatus, maxRetries = 8, retryBaseMs = 500 } = options;
  let socket: WebSocket | null = null;
  let closed = false;
  let retry = 0;
  let timer: ReturnType<typeof setTimeout> | null = null;
  // Track the highest sequence observed so reconnects request exactly the
  // events after the last one we already saw (no dups, no gaps).
  let lastSeq = options.lastSeq ?? 0;

  const heartbeat = () => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "ping" }));
    }
  };

  const connect = () => {
    if (closed) return;
    onStatus?.("connecting");
    // Resolve the session token (if any) before opening the socket so the
    // `access_token` query param is present for the backend auth check.
    void getAccessToken().then((token) => {
      if (closed) return;
      const base = getWsBaseUrl();
      const sep = base.includes("?") ? "&" : "?";
      const url =
        `${base}/ws/runs/${encodeURIComponent(runId)}?last_seq=${lastSeq}` +
        (token ? `${sep}access_token=${encodeURIComponent(token)}` : "");
      socket = new WebSocket(url);

      socket.onopen = () => {
        retry = 0;
        onStatus?.("open");
        const interval = window.setInterval(heartbeat, 30_000);
        const stopHeartbeat = () => window.clearInterval(interval);
        socket!.onclose = () => {
          stopHeartbeat();
          onStatus?.("closed");
          scheduleReconnect();
        };
        socket!.onerror = () => stopHeartbeat();
      };

      socket.onmessage = (evt) => {
        try {
          const parsed = JSON.parse(String(evt.data)) as RunEventMessage;
          if (parsed.type === "ping") return;
          if (typeof parsed.seq === "number" && parsed.seq > lastSeq) {
            lastSeq = parsed.seq;
          }
          onEvent?.(parsed);
        } catch {
          // ignore malformed frames
        }
      };

      socket.onerror = () => {
        try {
          socket?.close();
        } catch {
          // noop
        }
      };
    });
  };

  const scheduleReconnect = () => {
    if (closed) return;
    if (retry >= maxRetries) return;
    const delay = retryBaseMs * 2 ** retry;
    retry += 1;
    timer = setTimeout(connect, Math.min(delay, 10_000));
  };

  connect();

  return () => {
    closed = true;
    if (timer) clearTimeout(timer);
    try {
      socket?.close();
    } catch {
      // noop
    }
  };
}
