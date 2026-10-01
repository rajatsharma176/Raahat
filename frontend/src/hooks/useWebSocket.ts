import { useEffect, useRef, useCallback, useState } from 'react';
import type { AgentEvent } from '../types';

interface UseWebSocketOptions {
  sessionId: string | null;
  onEvent?: (event: AgentEvent) => void;
  onConnected?: () => void;
  onDisconnected?: () => void;
}

interface WebSocketState {
  connected: boolean;
  error: string | null;
}

export function useWebSocket({
  sessionId,
  onEvent,
  onConnected,
  onDisconnected,
}: UseWebSocketOptions): WebSocketState {
  const wsRef = useRef<WebSocket | null>(null);
  const pingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [state, setState] = useState<WebSocketState>({ connected: false, error: null });

  const connect = useCallback(() => {
    if (!sessionId) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const wsUrl = `ws://${window.location.host}/ws/events/${sessionId}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setState({ connected: true, error: null });
      onConnected?.();
      // Keep-alive ping every 25s
      pingRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send('ping');
      }, 25000);
    };

    ws.onmessage = (msg) => {
      try {
        const event = JSON.parse(msg.data);
        if (event.type !== 'pong') {
          onEvent?.(event as AgentEvent);
        }
      } catch {
        // Not JSON — ignore
      }
    };

    ws.onerror = () => {
      setState(prev => ({ ...prev, error: 'WebSocket error' }));
    };

    ws.onclose = () => {
      setState({ connected: false, error: null });
      onDisconnected?.();
      if (pingRef.current) clearInterval(pingRef.current);
      // Auto-reconnect after 2s
      setTimeout(connect, 2000);
    };
  }, [sessionId, onEvent, onConnected, onDisconnected]);

  useEffect(() => {
    connect();
    return () => {
      if (pingRef.current) clearInterval(pingRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return state;
}
