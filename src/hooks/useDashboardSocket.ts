import { useRef, useEffect, useState, useCallback } from 'react';
import { api } from '../services/api';

type WsEventType =
  | 'complaint:new'
  | 'incident:update'
  | 'incident:appealed';

interface WsEvent {
  type: WsEventType;
  payload: Record<string, unknown>;
}

interface UseDashboardSocketOptions {
  onEvent: (event: WsEvent) => void;
  enabled?: boolean;
}

const INITIAL_RETRY_MS = 1000;
const MAX_RETRY_MS = 30_000;
const PING_INTERVAL_MS = 25_000;

export function useDashboardSocket({ onEvent, enabled = true }: UseDashboardSocketOptions) {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const retryDelayRef = useRef(INITIAL_RETRY_MS);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const cleanup = useCallback(() => {
    if (pingTimerRef.current) {
      clearInterval(pingTimerRef.current);
      pingTimerRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current.onmessage = null;
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const connect = useCallback(async () => {
    cleanup();
    if (!enabled) return;

    try {
      const token = await api.getWsToken();
      const url = api.getWsUrl(token);
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        retryDelayRef.current = INITIAL_RETRY_MS;

        if (pingTimerRef.current) clearInterval(pingTimerRef.current);
        pingTimerRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, PING_INTERVAL_MS);
      };

      ws.onmessage = (msg: MessageEvent) => {
        if (msg.data === '"pong"') return;
        try {
          const event: WsEvent = JSON.parse(msg.data);
          onEventRef.current(event);
        } catch {
          // ignore malformed messages
        }
      };

      ws.onclose = () => {
        setConnected(false);
        cleanup();
        const delay = retryDelayRef.current;
        retryDelayRef.current = Math.min(delay * 2, MAX_RETRY_MS);
        retryTimerRef.current = setTimeout(connect, delay);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      const delay = retryDelayRef.current;
      retryDelayRef.current = Math.min(delay * 2, MAX_RETRY_MS);
      retryTimerRef.current = setTimeout(connect, delay);
    }
  }, [enabled, cleanup]);

  useEffect(() => {
    retryDelayRef.current = INITIAL_RETRY_MS;
    connect();
    return () => {
      cleanup();
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
    };
  }, [connect, cleanup]);

  return { connected };
}
