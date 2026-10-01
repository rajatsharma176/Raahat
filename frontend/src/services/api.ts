import axios from 'axios';
import type { RAAHATState, GraphData } from '../types';

const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api';

export const WS_BASE = import.meta.env.VITE_WS_URL
  ? import.meta.env.VITE_WS_URL
  : (window.location.protocol === 'https:' ? 'wss' : 'ws') + '://' + window.location.host;


const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

export interface StartSessionResponse {
  session_id: string;
  message: string;
  demo_mode: boolean;
}

export interface HealthResponse {
  status: string;
  version: string;
  llm_provider: string;
  llm_configured: boolean;
  demo_mode: boolean;
}

// ── Session ─────────────────────────────────────────────────────────────── //

export async function startSession(userId = 'demo-user'): Promise<StartSessionResponse> {
  const res = await api.post('/session/start', { user_id: userId });
  return res.data;
}

export async function submitEvent(sessionId: string, event: string): Promise<void> {
  await api.post('/event', { session_id: sessionId, event });
}

export async function getState(sessionId: string): Promise<RAAHATState> {
  const res = await api.get(`/state/${sessionId}`);
  return res.data;
}

export async function getGraphData(sessionId: string): Promise<GraphData> {
  const res = await api.get(`/graph/${sessionId}`);
  return res.data;
}

export async function resetSession(sessionId: string): Promise<void> {
  await api.post(`/reset/${sessionId}`);
}

export async function injectWorldEvent(sessionId: string, description: string): Promise<{ event_id: string }> {
  const res = await api.post('/events/inject', {
    session_id: sessionId,
    description,
  });
  return res.data;
}

export async function resolveApproval(
  approvalId: string,
  approved: boolean,
  note = ''
): Promise<void> {
  await api.post(`/approval/${approvalId}`, { approved, note });
}

export async function getPendingApprovals(): Promise<any[]> {
  const res = await api.get('/approvals/pending');
  return res.data.approvals;
}

export async function health(): Promise<HealthResponse> {
  const res = await api.get('/health');
  return res.data;
}

// ── Agent run (synchronous demo) ─────────────────────────────────────────── //

export async function agentRun(event: string, userId = 'demo-user'): Promise<any> {
  const res = await api.post('/agent/run', { event, user_id: userId });
  return res.data;
}

export default api;
