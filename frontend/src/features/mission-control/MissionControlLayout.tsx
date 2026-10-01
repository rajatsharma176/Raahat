import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { RAAHATState, AgentEvent } from '../../types';
import { AgentExecutionTheater } from '../agent-panel/AgentExecutionTheater';
import { TaskPipeline } from '../agent-panel/TaskPipeline';
import { TimelinePanel } from '../timeline/TimelinePanel';
import { MetricsBar } from '../metrics/MetricsBar';
import { DecisionLog } from '../timeline/DecisionLog';
import { ContinuityBanner } from './ContinuityBanner';
import { WorldEventButton } from './WorldEventButton';
import { DocumentsPanel } from '../agent-panel/DocumentsPanel';
import { EventStatusCard } from './EventStatusCard';
import { SectionBoundary } from '../../App';
import { Layers, Activity, FileText, Brain, Cpu, CheckCircle2, Loader2, AlertTriangle, RefreshCw } from 'lucide-react';
import { AGENT_NAMES } from '../../types';

type Tab = 'execution' | 'pipeline' | 'documents' | 'decisions';

interface MissionControlLayoutProps {
  state: RAAHATState | null;
  events: AgentEvent[];
  sessionId: string | null;
  loading: boolean;
  injectWorldEvent: () => void;
  worldEvent: string;
}

const AGENT_ICONS: Record<string, string> = {
  SituationAgent:    '🔍',
  ImpactAgent:       '🕸️',
  PlannerAgent:      '📋',
  EducationAgent:    '🎓',
  InsuranceAgent:    '🛡️',
  FinanceAgent:      '💰',
  DocumentAgent:     '📄',
  CommunicationAgent:'📨',
  VerificationAgent: '✅',
  ReplannerAgent:    '🔄',
};

const AGENT_ROLE: Record<string, string> = {
  SituationAgent:    'Event Extraction',
  ImpactAgent:       'Impact Analysis',
  PlannerAgent:      'Task Planning',
  EducationAgent:    'College & Exams',
  InsuranceAgent:    'Claims & Policies',
  FinanceAgent:      'Payments',
  DocumentAgent:     'Doc Requests',
  CommunicationAgent:'Notifications',
  VerificationAgent: 'Verification',
  ReplannerAgent:    'Replanning',
};

const STATUS_STYLE: Record<string, { dot: string; bg: string; text: string; border: string }> = {
  standby:    { dot: '#94a3b8', bg: '#f8fafc',  text: '#64748b', border: '#e2e8f0' },
  working:    { dot: '#d97706', bg: '#fffbeb',  text: '#92400e', border: '#fcd34d' },
  completed:  { dot: '#059669', bg: '#f0fdf4',  text: '#065f46', border: '#6ee7b7' },
  failed:     { dot: '#dc2626', bg: '#fef2f2',  text: '#991b1b', border: '#fca5a5' },
  blocked:    { dot: '#ea580c', bg: '#fff7ed',  text: '#9a3412', border: '#fdba74' },
  replanning: { dot: '#7c3aed', bg: '#faf5ff',  text: '#4c1d95', border: '#c4b5fd' },
};

const TAB_CONTENT: Record<Tab, React.FC<any>> = {
  execution: ({ state, events }) => <AgentExecutionTheater state={state} events={events} />,
  pipeline:  ({ state }) => <TaskPipeline state={state} />,
  documents: ({ state }) => <DocumentsPanel state={state} />,
  decisions: ({ state }) => <DecisionLog decisions={state?.ai_decisions || []} />,
};

export function MissionControlLayout({
  state,
  events,
  loading,
  injectWorldEvent,
  worldEvent,
}: MissionControlLayoutProps) {
  const [activeTab, setActiveTab] = useState<Tab>('execution');

  const taskCount  = state ? Object.keys(state.tasks).length : 0;
  const docCount   = state ? Object.keys(state.documents).length : 0;
  const decCount   = state ? state.ai_decisions.length : 0;
  const showWorldEvent = state?.is_complete && !state?.world_events?.some(w => !w.processed);
  const hasWorldEvent  = (state?.world_events?.length ?? 0) > 0;

  const TABS = [
    { id: 'execution' as Tab, label: 'Agents',    icon: Cpu,      badge: state?.active_tasks?.length || undefined },
    { id: 'pipeline'  as Tab, label: 'Tasks',     icon: Layers,   badge: taskCount || undefined },
    { id: 'documents' as Tab, label: 'Documents', icon: FileText, badge: docCount || undefined },
    { id: 'decisions' as Tab, label: 'Decisions', icon: Brain,    badge: decCount || undefined },
  ];

  const TabContent = TAB_CONTENT[activeTab];

  return (
    <div className="max-w-[1920px] mx-auto px-4 pb-10 pt-2">

      {/* Metrics */}
      {state && <MetricsBar state={state} />}

      {/* Continuity Banner */}
      <AnimatePresence>
        {state?.is_complete && (
          <motion.div
            initial={{ opacity: 0, y: -12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.3 }}
          >
            <ContinuityBanner
              status={state.final_status || 'continuity_restored'}
              completed={state.completed_tasks.length}
              total={Object.values(state.tasks).filter(t => t.status !== 'replanned').length}
              planVersion={state.plan_version}
              replans={state.replans}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* World Event */}
      {showWorldEvent && !hasWorldEvent && (
        <WorldEventButton onClick={injectWorldEvent} worldEvent={worldEvent} />
      )}

      {/* 3-Column Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-[300px_1fr_340px] gap-4 mt-4">

        {/* LEFT: Event Info + Agent Fleet Status */}
        <div className="space-y-4">
          <EventStatusCard state={state} loading={loading} />
          <AgentFleetPanel state={state} />
        </div>

        {/* CENTER: Tabs */}
        <div className="space-y-3 min-w-0">

          {/* Active execution banner */}
          <AnimatePresence>
            {state && !state.is_complete && state.active_tasks.length > 0 && (
              <motion.div
                key="exec-banner"
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                className="card-flat flex items-center gap-3 px-4 py-2.5"
                style={{ background: '#fffbeb', borderColor: '#fcd34d' }}
              >
                <div className="flex gap-1">
                  {[0, 1, 2].map(i => (
                    <motion.div
                      key={i}
                      className="w-1.5 h-1.5 rounded-full"
                      style={{ background: '#d97706' }}
                      animate={{ opacity: [0.3, 1, 0.3] }}
                      transition={{ duration: 0.9, delay: i * 0.2, repeat: Infinity }}
                    />
                  ))}
                </div>
                <span className="text-xs font-semibold text-amber-800">
                  {state.active_tasks.length} agent{state.active_tasks.length !== 1 ? 's' : ''} executing autonomously
                </span>
                <div className="ml-auto flex items-center gap-3 text-[11px] font-mono text-amber-700">
                  <span>Plan v{state.plan_version}</span>
                  {state.replans > 0 && (
                    <span className="flex items-center gap-1 text-purple-600">
                      <RefreshCw size={10} />
                      {state.replans} replans
                    </span>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Tab Bar */}
          <div className="card-flat p-1.5 flex gap-1">
            {TABS.map(tab => (
              <button
                key={tab.id}
                id={`tab-${tab.id}`}
                onClick={() => setActiveTab(tab.id)}
                className="flex-1 flex items-center justify-center gap-1.5 text-xs font-semibold py-2 px-2 rounded-lg transition-all duration-200"
                style={{
                  background: activeTab === tab.id ? 'white' : 'transparent',
                  color: activeTab === tab.id ? '#4f46e5' : '#64748b',
                  boxShadow: activeTab === tab.id ? '0 2px 8px rgba(79,70,229,0.15)' : 'none',
                  border: activeTab === tab.id ? '1px solid rgba(99,102,241,0.2)' : '1px solid transparent',
                }}
              >
                <tab.icon size={12} />
                <span className="hidden sm:inline">{tab.label}</span>
                {tab.badge ? (
                  <span
                    className="text-[9px] font-bold px-1.5 py-0.5 rounded-full"
                    style={{
                      background: activeTab === tab.id ? 'rgba(79,70,229,0.1)' : '#e2e8f0',
                      color: activeTab === tab.id ? '#4f46e5' : '#64748b',
                    }}
                  >
                    {tab.badge}
                  </span>
                ) : null}
              </button>
            ))}
          </div>

          {/* Tab Content — section boundaries prevent any panel crash from closing app */}
          <div className="relative min-h-[200px]">
            {activeTab === 'execution' && (
              <motion.div key="ex" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.15 }}>
                <SectionBoundary name="Agents">
                  <AgentExecutionTheater state={state} events={events} />
                </SectionBoundary>
              </motion.div>
            )}
            {activeTab === 'pipeline' && (
              <motion.div key="pi" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.15 }}>
                <SectionBoundary name="Tasks">
                  <TaskPipeline state={state} />
                </SectionBoundary>
              </motion.div>
            )}
            {activeTab === 'documents' && (
              <motion.div key="do" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.15 }}>
                <SectionBoundary name="Documents">
                  <DocumentsPanel state={state} />
                </SectionBoundary>
              </motion.div>
            )}
            {activeTab === 'decisions' && (
              <motion.div key="de" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.15 }}>
                <SectionBoundary name="Decisions">
                  <DecisionLog decisions={state?.ai_decisions || []} />
                </SectionBoundary>
              </motion.div>
            )}
          </div>
        </div>

        {/* RIGHT: Timeline */}
        <div>
          <TimelinePanel events={events} loading={!state && loading} />
        </div>
      </div>
    </div>
  );
}

/* ─── Agent Fleet Status Panel ──────────────────────────────── */
function AgentFleetPanel({ state }: { state: RAAHATState | null }) {
  const activeCount = state
    ? Object.values(state.agent_states).filter(a => a.status === 'working' || a.status === 'replanning').length
    : 0;
  const doneCount = state
    ? Object.values(state.agent_states).filter(a => a.status === 'completed').length
    : 0;

  return (
    <div className="card rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b flex items-center justify-between" style={{ borderColor: '#e2e8f0' }}>
        <div className="flex items-center gap-2">
          <Activity size={13} style={{ color: '#4f46e5' }} />
          <span className="text-xs font-bold text-slate-700 uppercase tracking-wide">Agent Fleet</span>
        </div>
        <div className="flex items-center gap-2">
          {activeCount > 0 ? (
            <span className="flex items-center gap-1 text-[10px] font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
              <div className="w-1.5 h-1.5 rounded-full bg-amber-500 pulse-dot" />
              {activeCount} live
            </span>
          ) : doneCount > 0 ? (
            <span className="flex items-center gap-1 text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
              <CheckCircle2 size={10} />
              {doneCount} done
            </span>
          ) : (
            <span className="text-[10px] text-slate-400 font-mono">idle</span>
          )}
        </div>
      </div>

      {/* Agent rows */}
      <div className="p-2 space-y-0.5">
        {AGENT_NAMES.map(name => {
          const agentSt = state?.agent_states[name];
          const status  = agentSt?.status || 'standby';
          const style   = STATUS_STYLE[status] || STATUS_STYLE.standby;
          const isLive  = status === 'working' || status === 'replanning';

          return (
            <motion.div
              key={name}
              className="relative flex items-center gap-2.5 px-2.5 py-2 rounded-xl overflow-hidden"
              style={{
                background: style.bg,
                border: `1px solid ${isLive ? style.border : 'transparent'}`,
                transition: 'background 0.3s, border 0.3s',
              }}
              id={`fleet-${name.toLowerCase().replace('agent', '')}`}
            >
              {/* Live scan line */}
              {isLive && (
                <div
                  className="scan-line"
                  style={{ color: style.dot }}
                />
              )}

              {/* Icon + status dot */}
              <div className="relative shrink-0 z-10">
                <span className="text-base leading-none">{AGENT_ICONS[name] || '🤖'}</span>
                <div
                  className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-white"
                  style={{ background: style.dot }}
                />
              </div>

              {/* Name + task */}
              <div className="flex-1 min-w-0 z-10">
                <div className="flex items-center gap-1.5">
                  <span className="text-[11px] font-bold" style={{ color: style.text }}>
                    {name.replace('Agent', '')}
                  </span>
                </div>
                {isLive && agentSt?.current_task ? (
                  <p className="text-[9px] truncate font-mono" style={{ color: style.dot }}>
                    → {agentSt.current_task}
                  </p>
                ) : agentSt?.last_tool && status === 'completed' ? (
                  <p className="text-[9px] truncate text-slate-400 font-mono">
                    ↳ {agentSt.last_tool}
                  </p>
                ) : (
                  <p className="text-[9px] text-slate-400">{AGENT_ROLE[name]}</p>
                )}
              </div>

              {/* Status badge */}
              <span
                className="text-[8px] font-bold font-mono uppercase px-1.5 py-0.5 rounded-full z-10 shrink-0"
                style={{ background: isLive ? style.dot : 'transparent', color: isLive ? 'white' : style.text }}
              >
                {isLive ? '▶ live' : status === 'completed' ? '✓' : status === 'standby' ? '—' : status}
              </span>
            </motion.div>
          );
        })}
      </div>

      {/* Summary footer */}
      {state && (
        <div className="px-4 py-2 border-t flex items-center justify-between" style={{ borderColor: '#f1f5f9', background: '#fafafa' }}>
          <span className="text-[10px] text-slate-500 font-mono">
            {state.completed_tasks.length}/{Object.keys(state.tasks).length} tasks done
          </span>
          {state.failed_tasks.length > 0 && (
            <span className="flex items-center gap-1 text-[10px] text-red-600">
              <AlertTriangle size={9} />
              {state.failed_tasks.length} failed
            </span>
          )}
          {state.is_complete && (
            <span className="flex items-center gap-1 text-[10px] text-emerald-600 font-bold">
              <CheckCircle2 size={10} />
              Continuity Restored
            </span>
          )}
        </div>
      )}
    </div>
  );
}
