import { motion, AnimatePresence } from 'framer-motion';
import type { RAAHATState, AgentEvent } from '../../types';
import { AGENT_NAMES } from '../../types';
import {
  Cpu, CheckCircle2, XCircle, Clock, RefreshCw, AlertCircle,
  Terminal, Zap, ArrowRight, Send, Building2, GraduationCap,
  Shield, Hospital, Banknote, Bell
} from 'lucide-react';

/* ─── Config ─────────────────────────────────────────────────── */
const STATUS_CFG: Record<string, { color: string; bg: string; border: string; label: string }> = {
  standby:    { color: '#94a3b8', bg: '#f8fafc',  border: '#e2e8f0', label: 'idle'       },
  working:    { color: '#d97706', bg: '#fffbeb',  border: '#fcd34d', label: 'executing'  },
  completed:  { color: '#059669', bg: '#f0fdf4',  border: '#6ee7b7', label: 'done'       },
  failed:     { color: '#dc2626', bg: '#fef2f2',  border: '#fca5a5', label: 'failed'     },
  blocked:    { color: '#ea580c', bg: '#fff7ed',  border: '#fdba74', label: 'blocked'    },
  replanning: { color: '#7c3aed', bg: '#faf5ff',  border: '#c4b5fd', label: 'replanning' },
};

const AGENT_META: Record<string, { icon: string; role: string; color: string }> = {
  SituationAgent:    { icon: '🔍', role: 'Event Extraction',  color: '#0891b2' },
  ImpactAgent:       { icon: '🕸️', role: 'Impact Analysis',   color: '#7c3aed' },
  PlannerAgent:      { icon: '📋', role: 'Task Planning',     color: '#4f46e5' },
  EducationAgent:    { icon: '🎓', role: 'College & Exams',   color: '#0284c7' },
  InsuranceAgent:    { icon: '🛡️', role: 'Insurance Claims',  color: '#7c3aed' },
  FinanceAgent:      { icon: '💰', role: 'Finance & Payments',color: '#d97706' },
  DocumentAgent:     { icon: '📄', role: 'Document Requests', color: '#059669' },
  CommunicationAgent:{ icon: '📨', role: 'Notifications',     color: '#0891b2' },
  VerificationAgent: { icon: '✅', role: 'Result Verification',color: '#059669' },
  ReplannerAgent:    { icon: '🔄', role: 'Dynamic Replanning', color: '#7c3aed' },
};

/* Tool → external system mapping */
const TOOL_SYSTEM: Record<string, { name: string; icon: typeof Building2; color: string }> = {
  'HospitalAPI':      { name: 'City General Hospital', icon: Hospital,       color: '#059669' },
  'CollegeAPI':       { name: 'University Portal',     icon: GraduationCap,  color: '#0284c7' },
  'InsuranceAPI':     { name: 'Insurance Portal',      icon: Shield,         color: '#7c3aed' },
  'BankAPI':          { name: 'Bank System',            icon: Banknote,       color: '#d97706' },
  'NotificationAPI':  { name: 'Notification Service',  icon: Bell,           color: '#0891b2' },
};

function getToolSystem(toolName: string) {
  for (const [key, val] of Object.entries(TOOL_SYSTEM)) {
    if (toolName?.includes(key)) return val;
  }
  return null;
}

interface Props { state: RAAHATState | null; events: AgentEvent[]; }

export function AgentExecutionTheater({ state, events }: Props) {
  if (!state) {
    return (
      <div className="card rounded-xl p-10 text-center">
        <Cpu size={32} className="mx-auto mb-3 opacity-20" style={{ color: '#4f46e5' }} />
        <p className="text-sm font-semibold text-slate-500">Agents standing by</p>
        <p className="text-xs text-slate-400 mt-1">Submit an event to start the autonomous pipeline</p>
      </div>
    );
  }

  const agents = AGENT_NAMES.map(name => ({
    name, meta: AGENT_META[name] || { icon: '🤖', role: 'Agent', color: '#64748b' },
    agentState: state.agent_states[name],
  }));

  const working = agents.filter(a =>
    a.agentState?.status === 'working' || a.agentState?.status === 'replanning'
  );
  const completed = agents.filter(a => a.agentState?.status === 'completed');
  const others    = agents.filter(a =>
    !['working', 'replanning', 'completed'].includes(a.agentState?.status || 'standby')
  );

  const recentToolResults = (state.tool_results || []).slice(-6).reverse();

  return (
    <div className="space-y-3">

      {/* ── ACTIVE AGENTS SPOTLIGHT ─────────────────────────── */}
      <AnimatePresence>
        {working.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="space-y-2">
              {working.map(({ name, meta, agentState }) => (
                <ActiveAgentSpotlight
                  key={name}
                  name={name}
                  meta={meta}
                  agentState={agentState}
                  events={(events || []).filter(e => e.agent === name).slice(0, 3)}
                />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── ALL AGENTS GRID ──────────────────────────────────── */}
      <div className="card rounded-xl overflow-hidden">
        <div className="px-4 py-3 border-b flex items-center justify-between" style={{ borderColor: '#f1f5f9' }}>
          <div className="flex items-center gap-2">
            <Cpu size={13} style={{ color: '#4f46e5' }} />
            <span className="text-sm font-bold text-slate-700">Agent Execution Status</span>
          </div>
          <div className="flex items-center gap-3 text-xs font-mono">
            <span style={{ color: '#059669' }}>{completed.length} done</span>
            <span className="text-slate-300">·</span>
            <span style={{ color: '#d97706' }}>{working.length} running</span>
            <span className="text-slate-300">·</span>
            <span style={{ color: '#ea580c' }}>{state.blocked_tasks.length} blocked</span>
          </div>
        </div>

        <div className="p-3 grid grid-cols-1 sm:grid-cols-2 gap-2">
          {agents.map(({ name, meta, agentState }) => (
            <AgentCard key={name} name={name} meta={meta} agentState={agentState} />
          ))}
        </div>
      </div>

      {/* ── COMMUNICATION FLOWS ──────────────────────────────── */}
      {recentToolResults.length > 0 && (
        <CommunicationFlows results={recentToolResults} />
      )}

      {/* ── REPLANNING INDICATOR ─────────────────────────────── */}
      {state.replans > 0 && (
        <ReplanningCard replans={state.replans} planVersion={state.plan_version} state={state} />
      )}
    </div>
  );
}

/* ─── Active Agent Spotlight Card ───────────────────────────── */
function ActiveAgentSpotlight({
  name, meta, agentState, events,
}: {
  name: string; meta: any; agentState: any; events: AgentEvent[];
}) {
  const status = agentState?.status || 'working';
  const cfg = STATUS_CFG[status] || STATUS_CFG.working;

  return (
    <motion.div
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative overflow-hidden rounded-xl"
      style={{
        background: `linear-gradient(135deg, ${cfg.bg}, white)`,
        border: `1.5px solid ${cfg.border}`,
        boxShadow: `0 4px 20px ${cfg.color}20, 0 2px 8px rgba(15,23,42,0.06)`,
      }}
    >
      {/* Animated scan line */}
      <motion.div
        className="absolute top-0 left-0 right-0 h-0.5"
        style={{ background: `linear-gradient(90deg, transparent, ${cfg.color}, transparent)` }}
        animate={{ x: ['-100%', '100%'] }}
        transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
      />

      <div className="p-4">
        <div className="flex items-start gap-3 mb-3">
          {/* Agent avatar */}
          <div
            className="w-11 h-11 rounded-xl flex items-center justify-center text-2xl shrink-0"
            style={{ background: `${cfg.color}15`, border: `1px solid ${cfg.color}30` }}
          >
            {meta.icon}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-bold text-slate-800">{name}</span>
              <motion.span
                className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full"
                style={{ background: cfg.color, color: 'white' }}
                animate={{ opacity: [0.7, 1, 0.7] }}
                transition={{ duration: 1.2, repeat: Infinity }}
              >
                ▶ {cfg.label}
              </motion.span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">{meta.role}</p>
          </div>
          {agentState?.last_tool && (
            <div className="shrink-0 text-right">
              <p className="text-[9px] text-slate-400 uppercase font-mono">Calling</p>
              <p className="text-[10px] font-mono font-semibold" style={{ color: meta.color }}>
                {agentState.last_tool}
              </p>
            </div>
          )}
        </div>

        {/* Current task */}
        {agentState?.current_task && (
          <div
            className="flex items-start gap-2 px-3 py-2 rounded-lg mb-2"
            style={{ background: `${cfg.color}10`, border: `1px solid ${cfg.color}20` }}
          >
            <Zap size={11} style={{ color: cfg.color, marginTop: 1 }} className="shrink-0" />
            <span className="text-xs font-semibold" style={{ color: cfg.color }}>
              {agentState.current_task}
            </span>
          </div>
        )}

        {/* Recent events */}
        {events.length > 0 && (
          <div className="space-y-1 mt-1">
            {events.map((evt, i) => (
              <div key={evt.event_id || i} className="flex items-start gap-2 text-[10px] text-slate-500">
                <ArrowRight size={9} className="shrink-0 mt-0.5" style={{ color: cfg.color }} />
                <span className="truncate">{evt.message}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}

/* ─── Individual Agent Card ──────────────────────────────────── */
function AgentCard({ name, meta, agentState }: { name: string; meta: any; agentState: any }) {
  const status = agentState?.status || 'standby';
  const cfg = STATUS_CFG[status] || STATUS_CFG.standby;
  const isLive = status === 'working' || status === 'replanning';

  return (
    <motion.div
      className="relative rounded-xl overflow-hidden"
      style={{
        background: isLive ? cfg.bg : 'white',
        border: `1px solid ${isLive ? cfg.border : '#f1f5f9'}`,
        boxShadow: isLive
          ? `0 4px 16px ${cfg.color}15, 0 1px 4px rgba(15,23,42,0.04)`
          : '0 1px 3px rgba(15,23,42,0.04)',
        transition: 'all 0.3s ease',
      }}
      id={`agent-card-${name.toLowerCase().replace('agent', '')}`}
    >
      {isLive && (
        <motion.div
          className="absolute top-0 left-0 right-0 h-0.5"
          style={{ background: `linear-gradient(90deg, transparent, ${cfg.color}, transparent)` }}
          animate={{ x: ['-100%', '100%'] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: 'linear' }}
        />
      )}

      <div className="p-3 flex items-start gap-2.5">
        {/* Icon */}
        <div className="relative shrink-0 mt-0.5">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center text-lg"
            style={{ background: isLive ? `${cfg.color}15` : '#f8fafc' }}
          >
            {meta.icon}
          </div>
          <div
            className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-white flex items-center justify-center"
            style={{ background: cfg.color }}
          />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className="text-[11px] font-bold text-slate-700">{name}</span>
            <span
              className="text-[8px] font-bold uppercase px-1.5 py-0.5 rounded-full"
              style={{
                background: isLive ? cfg.color : `${cfg.color}15`,
                color: isLive ? 'white' : cfg.color
              }}
            >
              {cfg.label}
            </span>
          </div>
          <p className="text-[9px] text-slate-400 mb-1">{meta.role}</p>

          <AnimatePresence>
            {agentState?.current_task && isLive && (
              <motion.div
                key={agentState.current_task}
                initial={{ opacity: 0, x: -4 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
                className="flex items-start gap-1"
              >
                <ArrowRight size={8} style={{ color: cfg.color, marginTop: 2 }} className="shrink-0" />
                <span className="text-[10px] leading-tight font-medium" style={{ color: cfg.color }}>
                  {agentState.current_task}
                </span>
              </motion.div>
            )}
            {agentState?.last_tool && (
              <motion.div
                key={`tool-${agentState.last_tool}`}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center gap-1 mt-0.5"
              >
                <Terminal size={8} className="text-slate-400 shrink-0" />
                <span className="text-[9px] text-slate-400 font-mono truncate">{agentState.last_tool}</span>
              </motion.div>
            )}
            {agentState?.message && status === 'completed' && (
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-[9px] text-emerald-600 mt-0.5 truncate"
              >
                ✓ {agentState.message.slice(0, 60)}
              </motion.p>
            )}
            {agentState?.message && status === 'failed' && (
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-[9px] text-red-500 mt-0.5 truncate"
              >
                ✗ {agentState.message.slice(0, 60)}
              </motion.p>
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  );
}

/* ─── Communication Flows ────────────────────────────────────── */
function CommunicationFlows({ results }: { results: any[] }) {
  return (
    <div className="card rounded-xl overflow-hidden">
      <div className="px-4 py-3 border-b flex items-center gap-2" style={{ borderColor: '#f1f5f9' }}>
        <Send size={13} style={{ color: '#4f46e5' }} />
        <span className="text-sm font-bold text-slate-700">Communication Flows</span>
        <span className="ml-auto text-[10px] text-slate-400 font-mono">
          Real API calls made by agents
        </span>
      </div>
      <div className="p-3 space-y-2">
        <AnimatePresence>
          {results.map((r, i) => {
            const sys = getToolSystem(r.tool_name);
            const isSuccess = r.status === 'success' || r.status === 'submitted';
            const isReject  = r.status === 'rejected' || r.status === 'failed';
            const color = isSuccess ? '#059669' : isReject ? '#dc2626' : '#4f46e5';
            const SysIcon = sys?.icon || Terminal;

            return (
              <motion.div
                key={`${r.tool_name}-${i}`}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="rounded-xl overflow-hidden"
                style={{
                  background: isSuccess ? '#f0fdf4' : isReject ? '#fef2f2' : '#f8f7ff',
                  border: `1px solid ${color}25`,
                }}
              >
                <div className="flex items-center gap-3 px-3 py-2.5">
                  {/* Agent → System flow */}
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <span className="text-[10px] font-bold text-slate-600 font-mono truncate">
                      {r.tool_name?.split('.')[0] || 'Agent'}
                    </span>
                    <div className="flex items-center gap-1 text-slate-300">
                      <motion.div
                        animate={{ x: [0, 4, 0] }}
                        transition={{ duration: 1.2, repeat: Infinity }}
                      >
                        <ArrowRight size={11} style={{ color }} />
                      </motion.div>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <SysIcon size={11} style={{ color: sys?.color || color }} />
                      <span className="text-[10px] font-semibold truncate" style={{ color: sys?.color || color }}>
                        {sys?.name || r.tool_name?.split('.')[1] || 'External System'}
                      </span>
                    </div>
                  </div>

                  {/* Method */}
                  <span className="text-[9px] font-mono text-slate-400 hidden sm:block truncate max-w-[120px]">
                    {r.tool_name?.split('.')[1] || ''}
                  </span>

                  {/* Status */}
                  <span
                    className="text-[9px] font-bold uppercase px-2 py-0.5 rounded-full shrink-0"
                    style={{ background: `${color}15`, color }}
                  >
                    {isSuccess ? '✓ ok' : isReject ? '✗ rejected' : r.status}
                  </span>
                </div>

                {/* Input summary */}
                {r.input_summary && (
                  <div className="px-3 pb-2.5">
                    <p className="text-[9px] font-mono text-slate-500 truncate">
                      Sent: {r.input_summary}
                    </p>
                  </div>
                )}
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}

/* ─── Replanning Card ────────────────────────────────────────── */
function ReplanningCard({ replans, planVersion, state }: { replans: number; planVersion: number; state: RAAHATState }) {
  const failedTasks = state.failed_tasks
    .map(id => state.tasks[id])
    .filter(Boolean)
    .slice(0, 3);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="card-flat rounded-xl overflow-hidden"
      style={{ background: '#faf5ff', borderColor: '#c4b5fd' }}
    >
      <div className="px-4 py-3 border-b flex items-center gap-2" style={{ borderColor: '#e9d5ff' }}>
        <RefreshCw size={13} style={{ color: '#7c3aed' }} className="animate-spin-slow" />
        <span className="text-sm font-bold text-purple-800">Dynamic Replanning</span>
        <div className="ml-auto flex items-center gap-2">
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-purple-100 text-purple-700">
            {replans} replan{replans !== 1 ? 's' : ''}
          </span>
          <span className="text-[10px] font-mono text-purple-500">Plan v{planVersion}</span>
        </div>
      </div>
      <div className="p-3">
        <p className="text-xs text-purple-700 mb-2">
          The ReplannerAgent detected failures and added new tasks to resolve them:
        </p>
        {failedTasks.map(task => (
          <div key={task.task_id} className="flex items-center gap-2 text-[11px] mb-1">
            <AlertCircle size={10} style={{ color: '#dc2626' }} className="shrink-0" />
            <span className="text-slate-600 font-medium">{task.title}</span>
            <span className="ml-auto text-[9px] font-mono text-red-500">{task.error?.slice(0, 40) || 'failed'}</span>
          </div>
        ))}
        {state.completed_tasks.filter(id => {
          const t = state.tasks[id];
          return t && t.plan_version > 1;
        }).length > 0 && (
          <p className="text-[10px] text-purple-600 mt-2 font-medium">
            ✓ {state.completed_tasks.filter(id => state.tasks[id]?.plan_version > 1).length} new tasks added and completed by replanning
          </p>
        )}
      </div>
    </motion.div>
  );
}
