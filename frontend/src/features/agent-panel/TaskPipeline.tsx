import { motion, AnimatePresence } from 'framer-motion';
import type { RAAHATState, Task } from '../../types';
import { STATUS_COLORS, DOMAIN_COLORS } from '../../types';
import {
  CheckCircle2, XCircle, Clock, AlertCircle, RotateCcw,
  Zap, Terminal, Layers, ArrowDown,
} from 'lucide-react';

const STATUS_ICONS: Record<string, typeof Clock> = {
  pending: Clock,
  active: Zap,
  completed: CheckCircle2,
  failed: XCircle,
  blocked: AlertCircle,
  skipped: Clock,
  replanned: RotateCcw,
};

const TASK_STATUS_STYLE: Record<string, { bg: string; border: string; color: string }> = {
  pending:   { bg: '#f8fafc', border: '#e2e8f0', color: '#94a3b8' },
  active:    { bg: '#fffbeb', border: '#fcd34d', color: '#d97706' },
  completed: { bg: '#f0fdf4', border: '#6ee7b7', color: '#059669' },
  failed:    { bg: '#fef2f2', border: '#fca5a5', color: '#dc2626' },
  blocked:   { bg: '#fff7ed', border: '#fdba74', color: '#ea580c' },
  skipped:   { bg: '#f8fafc', border: '#e2e8f0', color: '#94a3b8' },
  replanned: { bg: '#faf5ff', border: '#c4b5fd', color: '#7c3aed' },
};

interface TaskPipelineProps { state: RAAHATState | null; }

export function TaskPipeline({ state }: TaskPipelineProps) {
  if (!state || Object.keys(state.tasks).length === 0) {
    return (
      <div className="card rounded-xl p-10 text-center">
        <Clock size={28} className="mx-auto mb-3 opacity-20" style={{ color: '#4f46e5' }} />
        <p className="text-sm font-semibold text-slate-500">Planning in progress…</p>
        <p className="text-xs text-slate-400 mt-1">Tasks will appear once the planner completes.</p>
      </div>
    );
  }

  const tasks = Object.values(state.tasks).sort((a, b) => a.priority - b.priority);
  // Exclude replanned tasks from denominator (they are superseded by retry tasks)
  const activeTasks = tasks.filter(t => t.status !== 'replanned');
  const completionPct = state.is_complete
    ? 100
    : activeTasks.length > 0
    ? Math.min(99, Math.round((state.completed_tasks.length / activeTasks.length) * 100))
    : 0;
  const displayTotal = activeTasks.length;

  return (
    <div className="card rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b space-y-2" style={{ borderColor: '#f1f5f9', background: '#fafafa' }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers size={13} style={{ color: '#4f46e5' }} />
            <h2 className="text-sm font-bold text-slate-700">Execution Pipeline</h2>
            <span className="text-[10px] px-2 py-0.5 rounded-full font-mono font-bold"
              style={{ background: '#eef2ff', color: '#4f46e5' }}>
              Plan v{state.plan_version}
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="text-slate-500">{state.is_complete ? displayTotal : state.completed_tasks.length}/{displayTotal}</span>
            <span className="font-bold" style={{ color: completionPct === 100 ? '#059669' : '#4f46e5' }}>
              {completionPct}%
            </span>
          </div>
        </div>

        {/* Progress bar */}
        <div className="h-2 rounded-full overflow-hidden" style={{ background: '#e2e8f0' }}>
          <motion.div
            className="h-full rounded-full"
            style={{ background: completionPct === 100
              ? 'linear-gradient(90deg, #059669, #10b981)'
              : 'linear-gradient(90deg, #4f46e5, #0891b2)'
            }}
            initial={{ width: 0 }}
            animate={{ width: `${completionPct}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>

        {/* Summary pills */}
        <div className="flex gap-1.5 flex-wrap">
          {[
            { label: 'Done',    count: state.completed_tasks.length, color: '#059669', bg: '#f0fdf4' },
            { label: 'Running', count: state.active_tasks.length,    color: '#d97706', bg: '#fffbeb' },
            { label: 'Blocked', count: state.blocked_tasks.length,   color: '#ea580c', bg: '#fff7ed' },
            { label: 'Failed',  count: state.failed_tasks.length,    color: '#dc2626', bg: '#fef2f2' },
          ].map(s => (
            <div
              key={s.label}
              className="flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full"
              style={{ background: s.count > 0 ? s.bg : '#f8fafc', color: s.count > 0 ? s.color : '#94a3b8' }}
            >
              <span>{s.count}</span>
              <span className="font-medium">{s.label}</span>
            </div>
          ))}
          {state.replans > 0 && (
            <div className="flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full"
              style={{ background: '#faf5ff', color: '#7c3aed' }}>
              <RotateCcw size={8} />
              {state.replans} replan{state.replans > 1 ? 's' : ''}
            </div>
          )}
        </div>
      </div>

      {/* Task list */}
      <div className="p-3 space-y-1.5 max-h-[60vh] overflow-y-auto">
        <AnimatePresence initial={false}>
          {tasks.map((task, idx) => (
            <TaskCard
              key={task.task_id}
              task={task}
              index={idx}
              isLast={idx === tasks.length - 1}
              completedTasks={state.completed_tasks}
            />
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}

function TaskCard({ task, index, isLast, completedTasks }: {
  task: Task; index: number; isLast: boolean; completedTasks: string[];
}) {
  const statusStyle = TASK_STATUS_STYLE[task.status] || TASK_STATUS_STYLE.pending;
  const domainColor = DOMAIN_COLORS[task.domain] || '#4f46e5';
  const Icon = STATUS_ICONS[task.status] || Clock;
  const isActive  = task.status === 'active';
  const isReplanned = task.plan_version > 1;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: -16 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      id={`task-${task.task_id}`}
    >
      <div
        className="relative rounded-xl overflow-hidden"
        style={{
          background: statusStyle.bg,
          border: `1px solid ${isActive ? statusStyle.border : '#f1f5f9'}`,
          boxShadow: isActive ? `0 4px 14px ${statusStyle.color}15` : 'none',
        }}
      >
        {/* Active scan line */}
        {isActive && (
          <motion.div
            className="absolute top-0 left-0 right-0 h-0.5"
            style={{ background: `linear-gradient(90deg, transparent, ${statusStyle.color}, transparent)` }}
            animate={{ x: ['-100%', '100%'] }}
            transition={{ duration: 1.8, repeat: Infinity, ease: 'linear' }}
          />
        )}

        <div className="p-3 flex items-start gap-3">
          {/* Index + connector line */}
          <div className="flex flex-col items-center gap-1 shrink-0">
            <div
              className="w-6 h-6 rounded-lg flex items-center justify-center text-[10px] font-bold font-mono"
              style={{ background: `${statusStyle.color}15`, color: statusStyle.color }}
            >
              {index + 1}
            </div>
            {!isLast && (
              <div className="w-px flex-1 min-h-[8px]" style={{ background: '#e2e8f0' }} />
            )}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start gap-2 flex-wrap mb-1.5">
              <Icon
                size={12}
                style={{ color: statusStyle.color, marginTop: 1, flexShrink: 0 }}
                className={isActive ? 'animate-spin-slow' : ''}
              />
              <span className="text-xs font-semibold text-slate-700 leading-tight">{task.title}</span>
              {isReplanned && (
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full shrink-0"
                  style={{ background: '#faf5ff', color: '#7c3aed', border: '1px solid #c4b5fd' }}>
                  replan v{task.plan_version}
                </span>
              )}
            </div>

            <div className="flex items-center flex-wrap gap-1.5 mb-1">
              <span
                className="text-[9px] font-bold px-2 py-0.5 rounded-full capitalize"
                style={{ background: `${domainColor}12`, color: domainColor }}
              >
                {task.domain}
              </span>
              <span className="text-[9px] text-slate-400">{task.agent}</span>
              {task.tool && (
                <span className="flex items-center gap-0.5 text-[9px] text-slate-400 font-mono">
                  <Terminal size={8} />
                  {task.tool.includes('.') ? task.tool.split('.').pop() : task.tool}
                </span>
              )}
              <span
                className="text-[9px] font-bold px-2 py-0.5 rounded-full capitalize ml-auto"
                style={{ background: `${statusStyle.color}12`, color: statusStyle.color }}
              >
                {task.status}
              </span>
            </div>

            {task.error && (
              <div
                className="flex items-start gap-1.5 px-2 py-1.5 rounded-lg text-[10px] mt-1"
                style={{ background: '#fef2f2', borderLeft: '2px solid #dc2626', color: '#dc2626' }}
              >
                <AlertCircle size={9} className="mt-0.5 shrink-0" />
                {task.error.slice(0, 120)}
              </div>
            )}

            {task.rag_sources && task.rag_sources.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1">
                {task.rag_sources.map(src => (
                  <span
                    key={src}
                    className="text-[9px] px-1.5 py-0.5 rounded font-mono"
                    style={{ background: '#f1f5f9', color: '#64748b' }}
                  >
                    {src.split('/').pop()}
                  </span>
                ))}
              </div>
            )}

            {task.depends_on.length > 0 && (
              <div className="flex items-center gap-1 mt-1 flex-wrap">
                <ArrowDown size={8} className="text-slate-300" />
                {task.depends_on.map(dep => {
                  const depDone = completedTasks.includes(dep);
                  return (
                    <span
                      key={dep}
                      className="text-[9px] font-mono px-1.5 py-0.5 rounded"
                      style={{
                        background: depDone ? '#f0fdf4' : '#f8fafc',
                        color: depDone ? '#059669' : '#94a3b8',
                      }}
                    >
                      {depDone ? '✓' : '○'} {dep}
                    </span>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
