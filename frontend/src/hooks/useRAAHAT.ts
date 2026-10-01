import { useState, useCallback, useRef } from 'react';
import * as api from '../services/api';
import { useWebSocket } from './useWebSocket';
import type { RAAHATState, AgentEvent } from '../types';

const DEMO_EVENT =
  'I was hospitalized for five days after an accident. I have a Data Science exam on October 3 and I have insurance.';

const WORLD_EVENT =
  'The Data Science exam has been moved from October 3 to October 2.';

export function useRAAHAT() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [state, setState] = useState<RAAHATState | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // WebSocket real-time events
  const { connected } = useWebSocket({
    sessionId,
    onEvent: useCallback((evt: AgentEvent) => {
      setEvents(prev => [evt, ...prev].slice(0, 200)); // keep last 200
      // After each event, poll state for fresh data
      if (sessionId) {
        api.getState(sessionId).then(s => setState(s)).catch(() => {});
      }
    }, [sessionId]),
    onConnected: () => setWsConnected(true),
    onDisconnected: () => setWsConnected(false),
  });

  // Polling fallback when WS is unavailable
  const startPolling = useCallback((sid: string) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const s = await api.getState(sid);
        setState(s);
        if (s.is_complete) {
          clearInterval(pollRef.current!);
          pollRef.current = null;
        }
      } catch {}
    }, 1500);
  }, []);

  const stopPolling = useCallback(() => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  }, []);

  const startDemo = useCallback(async (customEvent?: string) => {
    setLoading(true);
    setError(null);
    setEvents([]);
    // Do NOT null state here — keep previous state visible until new data arrives
    stopPolling();

    try {
      // 1. Create session
      const session = await api.startSession();
      setState(null); // only clear after new session is confirmed
      setSessionId(session.session_id);
      startPolling(session.session_id);

      // 2. Submit the event
      const eventText = (customEvent && customEvent.trim()) || DEMO_EVENT;
      await api.submitEvent(session.session_id, eventText);

    } catch (e: any) {
      setError(e.message || 'Failed to start demo');
    } finally {
      setLoading(false);
    }
  }, [startPolling, stopPolling]);

  const injectWorldEvent = useCallback(async () => {
    if (!sessionId) return;
    try {
      await api.injectWorldEvent(sessionId, WORLD_EVENT);
      startPolling(sessionId);
    } catch (e: any) {
      setError(e.message || 'Failed to inject world event');
    }
  }, [sessionId, startPolling]);

  const reset = useCallback(async () => {
    stopPolling();
    if (sessionId) {
      try { await api.resetSession(sessionId); } catch {}
    }
    setSessionId(null);
    setState(null);
    setEvents([]);
    setError(null);
  }, [sessionId, stopPolling]);

  const refreshState = useCallback(async () => {
    if (!sessionId) return;
    try {
      const s = await api.getState(sessionId);
      setState(s);
    } catch {}
  }, [sessionId]);

  return {
    sessionId,
    state,
    events,
    loading,
    error,
    wsConnected,
    startDemo,
    injectWorldEvent,
    reset,
    refreshState,
    demoEvent: DEMO_EVENT,
    worldEvent: WORLD_EVENT,
  };
}
