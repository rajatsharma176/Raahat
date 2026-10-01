import { motion } from 'framer-motion';
import type { RAAHATState } from '../../types';
import { CheckSquare, XSquare, RefreshCw, Database, Zap, Target, GitBranch, Cpu } from 'lucide-react';

interface MetricsBarProps { state: RAAHATState; }

export function MetricsBar({ state }: MetricsBarProps) {
  const { metrics, plan_version, replans, completed_tasks, tasks, blocked_tasks, failed_tasks } = state;

  // Exclude 'replanned' tasks from denominator — they're replaced by newer retry tasks
  const activeTasks = Object.values(tasks).filter(t => t.status !== 'replanned');
  const totalTasks = activeTasks.length;
  // If backend says complete, force 100%. Otherwise use completed / non-replanned total.
  const completionPct = state.is_complete
    ? 100
    : totalTasks > 0
    ? Math.min(99, Math.round((completed_tasks.length / totalTasks) * 100))
    : 0;

  const METRICS = [
    {
      label: 'Progress', value: `${completionPct}%`, icon: Target,
      color: completionPct === 100 ? '#059669' : completionPct > 50 ? '#d97706' : '#4f46e5',
      sub: `${completed_tasks.length}/${totalTasks} tasks`, hot: completionPct > 0,
    },
    {
      label: 'Completed', value: state.is_complete ? totalTasks : completed_tasks.length, icon: CheckSquare,
      color: '#059669', sub: 'tasks done', hot: completed_tasks.length > 0,
    },
    {
      label: 'Plan', value: `v${plan_version}`, icon: GitBranch,
      color: '#4f46e5', sub: `${replans} replan${replans !== 1 ? 's' : ''}`, hot: replans > 0,
    },
    {
      label: 'Blocked', value: blocked_tasks.length, icon: XSquare,
      color: blocked_tasks.length > 0 ? '#ea580c' : '#94a3b8',
      sub: 'waiting', hot: blocked_tasks.length > 0,
    },
    {
      label: 'Tool Calls', value: metrics.tool_calls, icon: Cpu,
      color: '#4f46e5', sub: 'API calls', hot: metrics.tool_calls > 0,
    },
    {
      label: 'RAG Queries', value: metrics.rag_queries, icon: Database,
      color: '#0891b2', sub: 'policy lookups', hot: metrics.rag_queries > 0,
    },
    {
      label: 'Replans', value: replans, icon: RefreshCw,
      color: replans > 0 ? '#7c3aed' : '#94a3b8', sub: 'recovery', hot: replans > 0,
    },
    {
      label: 'Failures', value: failed_tasks.length, icon: Zap,
      color: failed_tasks.length > 0 ? '#dc2626' : '#059669',
      sub: failed_tasks.length === 0 ? 'none' : 'recovered', hot: failed_tasks.length > 0,
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      className="grid grid-cols-4 md:grid-cols-8 gap-2 mt-4"
    >
      {METRICS.map((m, i) => (
        <motion.div
          key={m.label}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.04 }}
          className="card-3d p-3 rounded-xl relative overflow-hidden"
          style={{ borderColor: m.hot ? `${m.color}30` : undefined }}
        >
          {m.hot && (
            <div
              className="absolute inset-0 opacity-40 pointer-events-none"
              style={{ background: `radial-gradient(circle at 10% 10%, ${m.color}18, transparent 70%)` }}
            />
          )}
          <div className="flex items-center gap-1.5 mb-1.5 relative z-10">
            <m.icon size={10} style={{ color: m.hot ? m.color : '#94a3b8' }} />
            <span className="text-[9px] text-slate-500 font-mono uppercase tracking-wide">{m.label}</span>
          </div>
          <p
            className="text-xl font-black leading-none relative z-10 font-mono"
            style={{ color: m.hot ? m.color : '#94a3b8' }}
          >
            {m.value}
          </p>
          <p className="text-[9px] text-slate-400 mt-0.5 relative z-10">{m.sub}</p>
        </motion.div>
      ))}
    </motion.div>
  );
}
