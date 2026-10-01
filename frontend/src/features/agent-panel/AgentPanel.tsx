import { motion, AnimatePresence } from 'framer-motion';
import type { RAAHATState, AgentState as AgentStateType } from '../../types';
import { AGENT_NAMES } from '../../types';

const STATUS_COLORS: Record<string, string> = {
  standby: '#64748b',
  working: '#f59e0b',
  completed: '#10b981',
  failed: '#ef4444',
  blocked: '#f97316',
  replanning: '#a855f7',
};

const STATUS_BG: Record<string, string> = {
  standby: 'rgba(100,116,139,0.1)',
  working: 'rgba(245,158,11,0.1)',
  completed: 'rgba(16,185,129,0.08)',
  failed: 'rgba(239,68,68,0.1)',
  blocked: 'rgba(249,115,22,0.1)',
  replanning: 'rgba(168,85,247,0.15)',
};

const AGENT_ICONS: Record<string, string> = {
  SituationAgent: '🔍',
  ImpactAgent: '🕸️',
  PlannerAgent: '📋',
  EducationAgent: '🎓',
  InsuranceAgent: '🛡️',
  FinanceAgent: '💰',
  DocumentAgent: '📄',
  CommunicationAgent: '📨',
  VerificationAgent: '✅',
  ReplannerAgent: '🔄',
};

interface AgentPanelProps {
  state: RAAHATState | null;
}

export function AgentPanel({ state }: AgentPanelProps) {
  return (
    <div className="glass rounded-xl overflow-hidden" id="agent-panel">
      <div className="px-4 py-3 border-b border-white/5 flex items-center justify-between">
        <h2 className="text-sm font-bold text-slate-200">Agent Fleet</h2>
        <span className="text-xs text-slate-500 font-mono">
          {state ? `${Object.keys(state.agent_states).length} active` : 'waiting...'}
        </span>
      </div>

      <div className="p-3 grid grid-cols-1 sm:grid-cols-2 gap-2">
        {AGENT_NAMES.map((name) => {
          const agentState = state?.agent_states[name];
          const status = agentState?.status || 'standby';
          const color = STATUS_COLORS[status] || '#64748b';
          const bg = STATUS_BG[status] || 'rgba(100,116,139,0.1)';

          return (
            <motion.div
              key={name}
              layout
              className="agent-card rounded-lg p-3 border border-white/5 relative overflow-hidden"
              style={{ background: bg, borderColor: `${color}20` }}
              id={`agent-${name.toLowerCase().replace('agent', '')}`}
            >
              {/* Active pulse border */}
              {status === 'working' && (
                <div className="absolute inset-0 border border-amber-400/30 rounded-lg animate-pulse" />
              )}
              {status === 'replanning' && (
                <div className="absolute inset-0 border border-violet-400/40 rounded-lg" style={{ animation: 'pulse 0.5s ease-in-out infinite' }} />
              )}

              <div className="flex items-start gap-2.5 relative">
                <div className="text-xl mt-0.5 shrink-0">{AGENT_ICONS[name] || '🤖'}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="status-dot" style={{ background: color }} />
                    <span className="text-xs font-semibold text-slate-200 truncate">{name}</span>
                  </div>

                  <AnimatePresence mode="wait">
                    {agentState ? (
                      <motion.div
                        key={agentState.current_task || agentState.last_action || 'idle'}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                      >
                        <p className="text-[11px] text-slate-400 truncate leading-relaxed">
                          {agentState.current_task || agentState.last_action || 'Standby'}
                        </p>
                        {agentState.last_tool && (
                          <p className="text-[10px] text-slate-600 font-mono truncate mt-0.5">
                            ⚙ {agentState.last_tool}
                          </p>
                        )}
                      </motion.div>
                    ) : (
                      <p className="text-[11px] text-slate-600">Standby</p>
                    )}
                  </AnimatePresence>
                </div>

                <div className="shrink-0">
                  <span
                    className="text-[10px] font-mono px-1.5 py-0.5 rounded capitalize"
                    style={{ background: `${color}20`, color }}
                  >
                    {status}
                  </span>
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
