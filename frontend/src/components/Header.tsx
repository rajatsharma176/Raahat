import { Wifi, WifiOff, RotateCcw, Shield, Activity, Cpu, Zap } from 'lucide-react';
import { motion } from 'framer-motion';

interface HeaderProps {
  wsConnected: boolean;
  sessionId: string | null;
  onReset: () => void;
  isRunning: boolean;
}

export function Header({ wsConnected, sessionId, onReset, isRunning }: HeaderProps) {
  return (
    <header
      className="sticky top-0 z-50"
      style={{
        background: 'rgba(255,255,255,0.9)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        borderBottom: '1px solid rgba(148,163,184,0.2)',
        boxShadow: '0 1px 12px rgba(15,23,42,0.06)',
      }}
    >
      <div className="max-w-[1920px] mx-auto px-5 py-2.5 flex items-center justify-between gap-4">

        {/* Logo */}
        <div className="flex items-center gap-3 shrink-0">
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center"
            style={{
              background: 'linear-gradient(135deg, #4f46e5, #0891b2)',
              boxShadow: '0 4px 12px rgba(79,70,229,0.35)',
            }}
          >
            <Shield size={18} className="text-white" />
          </div>
          <div>
            <div className="flex items-baseline gap-2">
              <h1 className="text-xl font-black tracking-wider" style={{ color: '#4f46e5' }}>
                RAAHAT
              </h1>
              <span className="text-[9px] font-bold text-slate-400 tracking-widest hidden sm:block uppercase">
                Autonomous Continuity Engine
              </span>
            </div>
          </div>
        </div>

        {/* Center — system status chips */}
        {isRunning && (
          <div className="hidden lg:flex items-center gap-2">
            <StatusChip icon={Cpu} label="LangGraph" color="#4f46e5" />
            <StatusChip icon={Activity} label="10 Agents" color="#059669" />
            <StatusChip icon={Zap} label="MockLLM" color="#d97706" />
          </div>
        )}

        {/* Right */}
        <div className="flex items-center gap-2.5 shrink-0">
          {sessionId && (
            <div className="hidden md:flex items-center gap-1.5 text-[10px] font-mono">
              <span className="text-slate-400">SESSION</span>
              <span className="font-bold" style={{ color: '#4f46e5' }}>
                {sessionId.split('-')[0].toUpperCase()}
              </span>
            </div>
          )}

          {/* WS Status */}
          <div
            className="flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-lg font-semibold"
            style={
              wsConnected
                ? { background: '#f0fdf4', color: '#059669', border: '1px solid #6ee7b7' }
                : { background: '#f8fafc', color: '#94a3b8', border: '1px solid #e2e8f0' }
            }
          >
            {wsConnected
              ? <><Wifi size={11} /><span className="hidden sm:inline ml-1">Live</span></>
              : <><WifiOff size={11} /><span className="hidden sm:inline ml-1">Offline</span></>
            }
          </div>

          {/* Sandbox badge */}
          <div
            className="hidden lg:flex items-center text-[9px] font-bold uppercase tracking-wider px-2 py-1 rounded-lg"
            style={{ background: '#fffbeb', color: '#d97706', border: '1px solid #fcd34d' }}
          >
            SANDBOX
          </div>

          {isRunning && (
            <motion.button
              whileHover={{ scale: 1.04 }}
              whileTap={{ scale: 0.96 }}
              onClick={onReset}
              className="btn-ghost text-xs flex items-center gap-1.5 py-1.5 px-3"
              id="reset-btn"
            >
              <RotateCcw size={12} />
              <span className="hidden sm:inline">New Session</span>
            </motion.button>
          )}
        </div>
      </div>
    </header>
  );
}

function StatusChip({ icon: Icon, label, color }: { icon: any; label: string; color: string }) {
  return (
    <div
      className="flex items-center gap-1.5 text-[10px] font-semibold px-2.5 py-1 rounded-lg"
      style={{ background: `${color}10`, color, border: `1px solid ${color}25` }}
    >
      <motion.div
        className="w-1.5 h-1.5 rounded-full"
        style={{ background: color }}
        animate={{ opacity: [1, 0.4, 1] }}
        transition={{ duration: 1.5, repeat: Infinity }}
      />
      <Icon size={10} />
      <span>{label}</span>
    </div>
  );
}
