import { motion } from 'framer-motion';
import { CheckCircle2, AlertTriangle, GitBranch, RotateCcw, Zap, Target } from 'lucide-react';

interface ContinuityBannerProps {
  status: string;
  completed: number;
  total: number;
  planVersion: number;
  replans: number;
}

export function ContinuityBanner({ status, completed, total, planVersion, replans }: ContinuityBannerProps) {
  const isSuccess = status === 'continuity_restored';
  // Force 100% when continuity is restored — replanned tasks skew the raw math
  const pct = isSuccess ? 100 : Math.min(99, Math.round((completed / Math.max(total, 1)) * 100));
  const color = isSuccess ? '#059669' : '#d97706';
  const bg    = isSuccess ? 'linear-gradient(135deg, #ecfdf5, #f0fdf4)' : 'linear-gradient(135deg, #fffbeb, #fff7ed)';
  const border = isSuccess ? '#6ee7b7' : '#fcd34d';
  const shadowColor = isSuccess ? 'rgba(5,150,105,0.2)' : 'rgba(217,119,6,0.2)';

  return (
    <motion.div
      initial={{ opacity: 0, y: -16, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -16 }}
      className="mt-4 rounded-2xl overflow-hidden relative"
      id="continuity-banner"
      style={{
        background: bg,
        border: `1.5px solid ${border}`,
        boxShadow: `0 0 0 4px ${shadowColor}, 0 8px 32px ${shadowColor}`,
      }}
    >
      {/* Scan shimmer */}
      <motion.div
        className="absolute top-0 left-0 right-0 h-px"
        style={{ background: `linear-gradient(90deg, transparent, ${color}60, transparent)` }}
        animate={{ x: ['-100%', '100%'] }}
        transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
      />

      <div className="p-4 flex items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          {/* Icon */}
          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0"
            style={{ background: `${color}15`, border: `1px solid ${color}30` }}
          >
            {isSuccess
              ? <CheckCircle2 size={22} style={{ color }} />
              : <AlertTriangle size={22} style={{ color }} />
            }
          </div>

          <div>
            <p className="font-black text-base" style={{ color }}>
              {isSuccess ? '✅ Continuity Restored' : '⚠️ Partial Recovery'}
            </p>
            <p className="text-xs text-slate-500 mt-0.5">
              {completed} of {total} tasks completed · Plan v{planVersion}
              {replans > 0 && ` · ${replans} autonomous replan${replans > 1 ? 's' : ''}`}
            </p>
          </div>
        </div>

        {/* Stats */}
        <div className="hidden md:flex items-center gap-2">
          <StatPill icon={Target}     value={`${pct}%`}          label="Recovery" color={color}    />
          <StatPill icon={GitBranch}  value={`v${planVersion}`}  label="Plan"     color="#4f46e5"  />
          {replans > 0 && <StatPill icon={RotateCcw} value={String(replans)} label="Replans" color="#7c3aed" />}
          <StatPill icon={Zap}        value={String(completed)}  label="Done"     color="#059669"  />
        </div>

        {/* Big % */}
        <div className="text-right shrink-0">
          <motion.p
            className="text-4xl font-black"
            style={{ color }}
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', stiffness: 200, delay: 0.2 }}
          >
            {pct}%
          </motion.p>
          <p className="text-xs text-slate-400">recovered</p>
        </div>
      </div>
    </motion.div>
  );
}

function StatPill({ icon: Icon, value, label, color }: {
  icon: any; value: string; label: string; color: string;
}) {
  return (
    <div
      className="flex flex-col items-center px-3 py-1.5 rounded-xl"
      style={{ background: `${color}10`, border: `1px solid ${color}20` }}
    >
      <Icon size={10} style={{ color }} className="mb-0.5" />
      <span className="text-sm font-black" style={{ color }}>{value}</span>
      <span className="text-[9px] text-slate-500">{label}</span>
    </div>
  );
}
