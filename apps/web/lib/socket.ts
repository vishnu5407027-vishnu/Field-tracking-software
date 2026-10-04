'use client';

import { getToken } from './api';

/**
 * Resolve the WebSocket endpoint. An absolute `ws(s)://…` env value is used
 * as-is (local dev); a relative path like "/ws/live" (production behind a
 * reverse proxy) is resolved against the current page origin, so the served
 * host/IP never needs to be baked into the build.
 */
function resolveWsUrl(): string {
  const configured = process.env.NEXT_PUBLIC_WS_URL;
  if (configured && /^wss?:\/\//.test(configured)) return configured;
  const path = configured && configured.startsWith('/') ? configured : '/ws/live';
  if (typeof window === 'undefined') return path;
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${window.location.host}${path}`;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Handler = (data: any) => void;

/**
 * Thin event-emitter over the Django Channels WebSocket. The server sends
 * `{event, data}` envelopes (location_sync / geofence_event / task_updated);
 * handlers subscribe per event, mirroring the old Socket.io API so consumers
 * keep the same `on`/`off` calls. Reconnects automatically with backoff.
 */
class LiveSocket {
  private ws: WebSocket | null = null;
  private handlers = new Map<string, Set<Handler>>();
  private retryMs = 1000;
  private closedByUser = false;

  connect() {
    const token = getToken();
    if (!token || typeof window === 'undefined') return;

    this.ws = new WebSocket(`${resolveWsUrl()}?token=${encodeURIComponent(token)}`);
    this.ws.onopen = () => {
      this.retryMs = 1000;
    };
    this.ws.onmessage = (msg) => {
      try {
        const { event, data } = JSON.parse(msg.data);
        this.handlers.get(event)?.forEach((fn) => fn(data));
      } catch {
        // Ignore malformed frames.
      }
    };
    this.ws.onclose = () => {
      if (this.closedByUser) return;
      setTimeout(() => this.connect(), this.retryMs);
      this.retryMs = Math.min(this.retryMs * 2, 15_000);
    };
  }

  on(event: string, fn: Handler) {
    if (!this.handlers.has(event)) this.handlers.set(event, new Set());
    this.handlers.get(event)!.add(fn);
  }

  off(event: string, fn: Handler) {
    this.handlers.get(event)?.delete(fn);
  }

  send(event: string, data: unknown) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ event, data }));
    }
  }

  disconnect() {
    this.closedByUser = true;
    this.ws?.close();
    this.ws = null;
  }
}

let socket: LiveSocket | null = null;

/** Singleton socket authenticated with the session JWT; the server locks it into the tenant group. */
export function getSocket(): LiveSocket {
  if (!socket) {
    socket = new LiveSocket();
    socket.connect();
  }
  return socket;
}

export function disconnectSocket() {
  socket?.disconnect();
  socket = null;
}
