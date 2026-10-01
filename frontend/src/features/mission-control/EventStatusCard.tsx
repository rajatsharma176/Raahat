import { motion, AnimatePresence } from 'framer-motion';
import type { RAAHATState } from '../../types';
import { DOMAIN_COLORS } from '../../types';
import { Calendar, Clock, AlertTriangle, CheckCircle2, Zap, User, MapPin, Heart } from 'lucide-react';

interface EventStatusCardProps {
  state: RAAHATState | null;
  loading: boolean;
}

const URGENCY_STYLE: Record<string, { color: string; bg: string; border: string }> = {
  critical: { color: '#dc2626', bg: '#fef2f2', border: '#fca5a5' },
  high:     { color: '#ea580c', bg: '#fff7ed', border: '#fdba74' },
  medium:   { color: '#d97706', bg: '#fffbeb', border: '#fcd34d' },
  low:      { color: '#059669', bg: '#f0fdf4', border: '#6ee7b7' },
};

export function EventStatusCard({ state, loading }: EventStatusCardProps) {
  if (loading && !state) {
    return (
      <div className="card rounded-xl p-4 space-y-2.5">
        {[3, 4, 2].map((w, i) => (
          <div key={i} className={`h-3 shimmer rounded-lg w-${w}/4`} />
        ))}
      </div>
    );
  }

  if (!state) return null;

  const evt = state.extracted_event;
  const urg = evt?.urgency || 'high';
  const urgStyle = URGENCY_STYLE[urg] || URGENCY_STYLE.high;

  return (
    <div className="card rounded-xl overflow-hidden">
      {/* Header */}
      <div
        className="px-3 py-2.5 border-b flex items-center gap-2"
        style={{ borderColor: '#f1f5f9', background: '#fafafa' }}
      >
        <motion.div
          className="w-2 h-2 rounded-full"
          style={{ background: '#4f46e5' }}
          animate={{ opacity: [1, 0.4, 1] }}
          transition={{ duration: 1.5, repeat: Infinity }}
        />
        <h2 className="text-xs font-bold text-slate-700 uppercase tracking-wide">Incident Event</h2>
        {state.is_complete && (
          <span className="ml-auto flex items-center gap-1 text-[10px] font-bold text-emerald-600">
            <CheckCircle2 size={9} /> Complete
          </span>
        )}
      </div>

      <div className="p-3 space-y-2.5">
        {/* Raw event quote */}
        <div
          className="px-3 py-2.5 rounded-xl text-xs leading-relaxed text-slate-600"
          style={{
            background: '#f8f7ff',
            borderLeft: '3px solid #4f46e5',
          }}
        >
          {state.raw_event.length > 150
            ? `"${state.raw_event.slice(0, 150)}..."`
            : `"${state.raw_event}"`}
        </div>

        {/* Extracted info */}
        {evt && (
          <AnimatePresence>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-2"
            >
              {/* Event type + urgency badges */}
              <div className="flex items-center gap-1.5 flex-wrap">
                <span
                  className="text-[10px] font-bold uppercase px-2.5 py-1 rounded-full"
                  style={{ background: '#eef2ff', color: '#4f46e5' }}
                >
                  {evt.event_type?.replace(/_/g, ' ')}
                </span>
                <span
                  className="text-[10px] font-bold capitalize px-2.5 py-1 rounded-full"
                  style={{
                    background: urgStyle.bg,
                    color: urgStyle.color,
                    border: `1px solid ${urgStyle.border}`,
                  }}
                >
                  ⚡ {urg} urgency
                </span>
              </div>

              {/* Person info */}
              <div className="space-y-1.5">
                {evt.person_name && (
                  <InfoRow icon={User} label="Patient" value={evt.person_name} color="#4f46e5" />
                )}
                {evt.person_role && (
                  <InfoRow icon={Heart} label="Role" value={evt.person_role} color="#0891b2" />
                )}
                {evt.location && (
                  <InfoRow icon={MapPin} label="Location" value={evt.location} color="#7c3aed" />
                )}
                {evt.duration_days && (
                  <InfoRow icon={Clock} label="Duration" value={`${evt.duration_days} days`} color="#d97706" />
                )}
                {evt.start_date && (
                  <InfoRow
                    icon={Calendar}
                    label="Period"
                    value={evt.end_date ? `${evt.start_date} → ${evt.end_date}` : evt.start_date}
                    color="#059669"
                  />
                )}
              </div>

              {/* Affected domains */}
              {evt.affected_domains.length > 0 && (
                <div>
                  <p className="text-[9px] text-slate-400 uppercase font-semibold tracking-wide mb-1.5">
                    Affected Domains
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {evt.affected_domains.map(d => (
                      <span
                        key={d}
                        className="text-[9px] font-bold capitalize px-2 py-0.5 rounded-full"
                        style={{
                          background: `${DOMAIN_COLORS[d] || '#4f46e5'}15`,
                          color: DOMAIN_COLORS[d] || '#4f46e5',
                          border: `1px solid ${DOMAIN_COLORS[d] || '#4f46e5'}30`,
                        }}
                      >
                        {d}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Constraints */}
              {evt.explicit_constraints.length > 0 && (
                <div className="space-y-1">
                  {evt.explicit_constraints.slice(0, 3).map((c, i) => (
                    <div key={i} className="flex items-start gap-1.5 text-[10px]">
                      <Zap size={8} style={{ color: '#d97706', marginTop: 2 }} className="shrink-0" />
                      <span className="text-slate-500 leading-relaxed">{c}</span>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        )}

        {/* World events */}
        {state.world_events.length > 0 && (
          <div className="pt-2 border-t" style={{ borderColor: '#f1f5f9' }}>
            <p className="text-[10px] font-bold text-amber-600 mb-1.5 flex items-center gap-1">
              <AlertTriangle size={9} /> World Events
            </p>
            {state.world_events.map(we => (
              <div
                key={we.event_id}
                className="text-[10px] text-amber-700 px-2.5 py-2 rounded-xl leading-relaxed"
                style={{
                  background: '#fffbeb',
                  borderLeft: '3px solid #fcd34d',
                }}
              >
                {we.description}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function InfoRow({ icon: Icon, label, value, color }: {
  icon: any; label: string; value: string; color: string;
}) {
  return (
    <div className="flex items-center gap-2 text-[11px]">
      <Icon size={10} style={{ color }} className="shrink-0" />
      <span className="text-slate-400 w-16 shrink-0">{label}</span>
      <span className="text-slate-700 font-medium truncate">{value}</span>
    </div>
  );
}
