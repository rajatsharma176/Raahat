import { motion, AnimatePresence } from 'framer-motion';
import type { RAAHATState, Task } from '../../types';
import { STATUS_COLORS, DOMAIN_COLORS } from '../../types';
import { CheckCircle, XCircle, Clock, AlertCircle, RotateCcw } from 'lucide-react';

const STATUS_ICONS = {
  pending: Clock,
  active: RotateCcw,
  completed: CheckCircle,
  failed: XCircle,
  blocked: AlertCircle,
  skipped: Clock,
  replanned: RotateCcw,
};

interface TaskPanelProps {
  state: RAAHATState | null;
}

export function TaskPanel({ state }: TaskPanelProps) {
  if (!state || Object.keys(state.tasks).length === 0) {
    return (
      <div className="glass rounded-xl p-8 text-center text-slate-600">
        <Clock size={24} className="mx-auto mb-2 opacity-30" />
        <p className="text-sm">Planning in progress...</p>
      </div>
    );
  }

  const tasks = Object.values(state.tasks).sort((a, b) => a.priority - b.priority);

  return (
    <div className="glass rounded-xl overflow-hidden">
      <div className="px-4 py-3 border-b border-white/5 flex items-center justify-between">
        <h2 className="text-sm font-bold text-slate-200">Execution Plan</h2>
        <div className="flex items-center gap-2 text-xs text-slate-500 font-mono">
          <span className="text-cyan-400">Plan v{state.plan_version}</span>
          <span>·</span>
          <span>{state.completed_tasks.length}/{tasks.length} done</span>
        </div>
      </div>

      <div className="p-3 space-y-2 max-h-[60vh] overflow-y-auto">
        <AnimatePresence initial={false}>
          {tasks.map((task) => {
            const statusColor = STATUS_COLORS[task.status] || '#64748b';
            const domainColor = DOMAIN_COLORS[task.domain] || '#64748b';
            const Icon = STATUS_ICONS[task.status] || Clock;
            const isActive = task.status === 'active';
            const isReplanned = task.plan_version > 1;

            return (
              <motion.div
                key={task.task_id}
                layout
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                className="relative rounded-lg border overflow-hidden"
                style={{
                  borderColor: `${statusColor}25`,
                  background: isActive ? `${statusColor}08` : 'rgba(15,23,42,0.5)',
                }}
                id={`task-${task.task_id}`}
              >
                {/* Active progress bar */}
                {isActive && (
                  <div
                    className="absolute top-0 left-0 h-0.5 animate-pulse"
                    style={{ background: statusColor, width: '60%' }}
                  />
                )}

                <div className="p-3 flex items-start gap-3">
                  {/* Status icon */}
                  <Icon
                    size={14}
                    className={`mt-0.5 shrink-0 ${isActive ? 'animate-spin' : ''}`}
                    style={{ color: statusColor }}
                  />

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-0.5">
                      <span className="text-xs font-semibold text-slate-200 truncate">{task.title}</span>
                      {isReplanned && (
                        <span className="text-[10px] bg-violet-500/20 text-violet-400 px-1.5 py-0.5 rounded-full">
                          replan v{task.plan_version}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      {/* Domain badge */}
                      <span
                        className="text-[10px] px-1.5 py-0.5 rounded capitalize"
                        style={{ background: `${domainColor}15`, color: domainColor }}
                      >
                        {task.domain}
                      </span>

                      {/* Agent */}
                      <span className="text-[10px] text-slate-600 truncate">{task.agent}</span>

                      {/* Tool */}
                      {task.tool && (
                        <span className="text-[10px] text-slate-700 font-mono truncate">
                          {task.tool.split('.')[1] || task.tool}
                        </span>
                      )}
                    </div>

                    {/* Error */}
                    {task.error && (
                      <p className="text-[10px] text-red-400 mt-1 truncate">⚠ {task.error}</p>
                    )}

                    {/* Dependencies */}
                    {task.depends_on.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {task.depends_on.map(dep => (
                          <span key={dep} className="text-[9px] font-mono text-slate-700 bg-slate-800 px-1.5 rounded">
                            {dep}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Status badge */}
                  <span
                    className="text-[10px] font-mono px-1.5 py-0.5 rounded capitalize shrink-0"
                    style={{ background: `${statusColor}15`, color: statusColor }}
                  >
                    {task.status}
                  </span>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}
