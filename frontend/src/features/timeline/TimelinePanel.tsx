import { useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { AgentEvent } from '../../types';
import {
  Activity, CheckCircle2, XCircle, AlertTriangle, RefreshCw,
  Cpu, Database, Info, Terminal, Shield, Zap,
} from 'lucide-react';

const EVENT_CONFIG: Record<string, { icon: typeof Activity; color: string; label: string }> = {
  agent_started:          { icon: Activity,      color: '#4f46e5', label: 'Started'     },
  agent_completed:        { icon: CheckCircle2,  color: '#059669', label: 'Done'        },
  tool_called:            { icon: Terminal,      color: '#0891b2', label: 'Tool Call'   },
  tool_completed:         { icon: CheckCircle2,  color: '#059669', label: 'Success'     },
  tool_failed:            { icon: XCircle,       color: '#dc2626', label: 'Failed'      },
  verification_started:   { icon: Shield,        color: '#d97706', label: 'Verifying'   },
  verification_completed: { icon: CheckCircle2,  color: '#059669', label: 'Verified'    },
  replan_started:         { icon: RefreshCw,     color: '#7c3aed', label: 'Replanning'  },
  replan_completed:       { icon: CheckCircle2,  color: '#7c3aed', label: 'Replanned'   },
  world_event_added:      { icon: AlertTriangle, color: '#d97706', label: 'World Event' },
  continuity_restored:    { icon: CheckCircle2,  color: '#059669', label: 'Restored'    },
  task_created:           { icon: Database,      color: '#4f46e5', label: 'Task'        },
  workflow_error:         { icon: XCircle,       color: '#dc2626', label: 'Error'       },
};

interface TimelinePanelProps { events: AgentEvent[]; loading: boolean; }

export function TimelinePanel({ events, loading }: TimelinePanelProps) {
  const topRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    topRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [events.length]);

  return (
    <div
      className="card rounded-xl overflow-hidden flex flex-col"
      style={{ height: 'calc(100vh - 180px)', minHeight: 400 }}
      id="timeline-panel"
    >
      {/* Header */}
      <div
        className="px-4 py-3 border-b flex items-center justify-between flex-shrink-0"
        style={{ borderColor: '#f1f5f9', background: '#fafafa' }}
      >
        <div className="flex items-center gap-2">
          <div className="relative">
            <div className="w-2 h-2 rounded-full" style={{ background: '#4f46e5' }} />
            {loading && (
              <div className="absolute inset-0 rounded-full animate-ping"
                style={{ background: '#4f46e5', opacity: 0.5 }} />
            )}
          </div>
          <h2 className="text-xs font-bold text-slate-700 uppercase tracking-wide">Live Event Stream</h2>
        </div>
        <div className="flex items-center gap-2">
          {loading && (
            <span className="text-[9px] font-semibold px-2 py-0.5 rounded-full animate-pulse"
              style={{ background: '#eef2ff', color: '#4f46e5' }}>
              streaming
            </span>
          )}
          <span className="text-[10px] text-slate-400 font-mono">{events.length} events</span>
        </div>
      </div>

      {/* Empty */}
      {events.length === 0 && !loading && (
        <div className="flex-1 flex flex-col items-center justify-center text-slate-400 p-8">
          <Activity size={24} className="mb-3 opacity-30" />
          <p className="text-xs text-center leading-relaxed">
            Events will stream here in real time as agents execute...
          </p>
        </div>
      )}

      {/* Skeleton */}
      {loading && events.length === 0 && (
        <div className="p-3 space-y-2 flex-1">
          {[...Array(6)].map((_, i) => (
            <div
              key={i}
              className="h-12 rounded-xl shimmer"
              style={{ animationDelay: `${i * 0.1}s` }}
            />
          ))}
        </div>
      )}

      {/* Events list — newest first */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        <div ref={topRef} />
        <AnimatePresence initial={false}>
          {events.map((evt, idx) => {
            const cfg = EVENT_CONFIG[evt.event_type] || { icon: Info, color: '#64748b', label: evt.event_type };
            const Icon = cfg.icon;
            const isSpecial = ['replan_started', 'world_event_added', 'continuity_restored', 'tool_failed'].includes(evt.event_type);
            const isReplan = evt.event_type.includes('replan');
            const isContinuity = evt.event_type === 'continuity_restored';
            const isError = evt.event_type.includes('failed') || evt.event_type === 'workflow_error';
            const isWorldEvent = evt.event_type === 'world_event_added';

            const bg = isContinuity ? '#f0fdf4'
              : isReplan ? '#faf5ff'
              : isWorldEvent ? '#fffbeb'
              : isError ? '#fef2f2'
              : 'white';
            const border = isContinuity ? '#6ee7b7'
              : isReplan ? '#c4b5fd'
              : isWorldEvent ? '#fcd34d'
              : isError ? '#fca5a5'
              : '#f1f5f9';

            return (
              <motion.div
                key={evt.event_id || idx}
                layout
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.18 }}
                className="rounded-xl overflow-hidden"
                style={{ border: `1px solid ${border}`, background: bg }}
              >
                <div className="px-3 py-2 flex items-start gap-2.5">
                  <div
                    className="shrink-0 mt-0.5 w-5 h-5 rounded-lg flex items-center justify-center"
                    style={{ background: `${cfg.color}15` }}
                  >
                    <Icon size={10} style={{ color: cfg.color }} />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-start gap-1 min-w-0">
                      {evt.agent && (
                        <span className="text-[10px] font-bold shrink-0" style={{ color: cfg.color }}>
                          {evt.agent.replace('Agent', '')}:
                        </span>
                      )}
                      <span className="text-[10px] text-slate-600 leading-tight min-w-0">
                        {evt.message.length > 90 ? `${evt.message.slice(0, 90)}…` : evt.message}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-[9px] font-mono text-slate-400">
                        {evt.timestamp
                          ? new Date(evt.timestamp).toLocaleTimeString('en', { hour12: false })
                          : ''}
                      </span>
                      <span
                        className="text-[8px] font-semibold px-1.5 rounded-full capitalize"
                        style={{ color: cfg.color, background: `${cfg.color}15` }}
                      >
                        {cfg.label}
                      </span>
                      {evt.data?.tool && (
                        <span className="text-[9px] font-mono text-slate-400 truncate">
                          {evt.data.tool}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}
