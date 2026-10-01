// RAAHAT TypeScript type definitions
// Mirrors the Python Pydantic models on the backend

export type TaskStatus = 'pending' | 'active' | 'completed' | 'failed' | 'blocked' | 'skipped' | 'replanned';
export type AgentStatus = 'standby' | 'working' | 'completed' | 'blocked' | 'failed' | 'replanning';
export type DomainType = 'education' | 'insurance' | 'finance' | 'health' | 'communication' | 'legal';
export type EventType = 'hospitalization' | 'accident' | 'family_emergency' | 'bereavement' | 'natural_disaster' | 'other';

export interface ExtractedEvent {
  event_type: EventType;
  event_reason: string;
  start_date?: string;
  end_date?: string;
  duration_days?: number;
  person_role: string;
  affected_domains: DomainType[];
  urgency: string;
  explicit_constraints: string[];
  important_dates: Record<string, string>;
  raw_event: string;
}

export interface DependencyNode {
  node_id: string;
  label: string;
  domain: DomainType;
  status: TaskStatus;
  depends_on: string[];
  metadata: Record<string, any>;
}

export interface DependencyEdge {
  source: string;
  target: string;
  label: string;
  active: boolean;
}

export interface Task {
  task_id: string;
  title: string;
  description: string;
  domain: DomainType;
  agent: string;
  tool?: string;
  status: TaskStatus;
  priority: number;
  depends_on: string[];
  required_documents: string[];
  expected_output: string;
  verification_criteria: string;
  result?: Record<string, any>;
  error?: string;
  attempts: number;
  created_at: string;
  completed_at?: string;
  plan_version: number;
  rag_sources: string[];
}

export interface AgentState {
  agent_name: string;
  status: AgentStatus;
  current_task?: string;
  last_action?: string;
  last_tool?: string;
  last_updated: string;
  message?: string;
}

export interface Document {
  document_id: string;
  document_type: string;
  status: string;
  source: string;
  metadata: Record<string, any>;
  retrieved_at?: string;
}

export interface ToolResult {
  tool_name: string;
  input_summary: string;
  output: Record<string, any>;
  status: string;
  timestamp: string;
  task_id?: string;
}

export interface AgentEvent {
  event_id: string;
  event_type: string;
  agent?: string;
  task_id?: string;
  message: string;
  data: Record<string, any>;
  timestamp: string;
  status: string;
}

export interface ApprovalRequest {
  approval_id: string;
  task_id: string;
  agent: string;
  action: string;
  description: string;
  risk_level: string;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string;
  resolved_at?: string;
  resolver_note?: string;
}

export interface WorldEvent {
  event_id: string;
  description: string;
  affected_tasks: string[];
  injected_at: string;
  processed: boolean;
}

export interface Metrics {
  actions_planned: number;
  actions_completed: number;
  failures_recovered: number;
  replans: number;
  blocked_tasks: number;
  user_interventions: number;
  rag_queries: number;
  tool_calls: number;
  current_plan_version: number;
}

export interface AIDecision {
  decision: string;
  evidence: string;
  dependency?: string;
  next_action: string;
  source?: string;
  timestamp: string;
}

export interface RAAHATState {
  session_id: string;
  created_at: string;
  updated_at: string;
  raw_event: string;
  extracted_event?: ExtractedEvent;
  user_id: string;
  user_profile: Record<string, any>;
  affected_domains: DomainType[];
  dependency_nodes: DependencyNode[];
  dependency_edges: DependencyEdge[];
  tasks: Record<string, Task>;
  active_tasks: string[];
  completed_tasks: string[];
  failed_tasks: string[];
  blocked_tasks: string[];
  documents: Record<string, Document>;
  evidence: any[];
  tool_results: ToolResult[];
  agent_states: Record<string, AgentState>;
  agent_events: AgentEvent[];
  current_plan: string[];
  plan_version: number;
  replans: number;
  world_events: WorldEvent[];
  approval_requests: Record<string, ApprovalRequest>;
  metrics: Metrics;
  ai_decisions: AIDecision[];
  workflow_step: number;
  final_status?: string;
  is_complete: boolean;
  error_message?: string;
}

// UI-specific types
export interface GraphData {
  nodes: DependencyNode[];
  edges: DependencyEdge[];
}

export const AGENT_NAMES = [
  'SituationAgent',
  'ImpactAgent',
  'PlannerAgent',
  'EducationAgent',
  'InsuranceAgent',
  'FinanceAgent',
  'DocumentAgent',
  'CommunicationAgent',
  'VerificationAgent',
  'ReplannerAgent',
] as const;

export type AgentName = typeof AGENT_NAMES[number];

export const DOMAIN_COLORS: Record<DomainType, string> = {
  education: '#3b82f6',
  insurance: '#a855f7',
  finance: '#f59e0b',
  health: '#10b981',
  communication: '#06b6d4',
  legal: '#f97316',
};

export const STATUS_COLORS: Record<TaskStatus, string> = {
  pending: '#64748b',
  active: '#f59e0b',
  completed: '#10b981',
  failed: '#ef4444',
  blocked: '#f97316',
  skipped: '#475569',
  replanned: '#a855f7',
};
