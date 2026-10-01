import { motion, AnimatePresence } from 'framer-motion';
import type { AIDecision } from '../../types';
import { Brain, ArrowRight, BookOpen, Link, Lightbulb, AlertTriangle } from 'lucide-react';

interface DecisionLogProps { decisions: AIDecision[]; }

export function DecisionLog({ decisions }: DecisionLogProps) {
  const reversed = [...decisions].reverse();

  return (
    <div className="card rounded-xl overflow-hidden" id="decision-log">
      <div
        className="px-4 py-3 border-b flex items-center justify-between"
        style={{ borderColor: '#f1f5f9', background: '#fafafa' }}
      >
        <div className="flex items-center gap-2">
          <Brain size={13} style={{ color: '#4f46e5' }} />
          <h2 className="text-sm font-bold text-slate-700">AI Decision Log</h2>
        </div>
        <span className="text-[10px] text-slate-400 font-mono">{decisions.length} decisions</span>
      </div>

      <div className="p-3 space-y-2 max-h-[65vh] overflow-y-auto">
        {decisions.length === 0 && (
          <div className="text-center py-12 text-slate-400">
            <Brain size={24} className="mx-auto mb-2 opacity-20" />
            <p className="text-xs">AI decisions will appear here as agents reason...</p>
          </div>
        )}

        <AnimatePresence initial={false}>
          {reversed.map((decision, i) => {
            const isReplan = (decision.decision?.toLowerCase() || '').includes('replan')
              || (decision.decision?.toLowerCase() || '').includes('blocked');
            const color = isReplan ? '#7c3aed' : '#4f46e5';
            const bg    = isReplan ? '#faf5ff' : '#f8f7ff';
            const border = isReplan ? '#c4b5fd' : 'rgba(79,70,229,0.2)';

            return (
              <motion.div
                key={decisions.length - 1 - i}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25 }}
                className="rounded-xl overflow-hidden"
                id={`decision-${decisions.length - 1 - i}`}
                style={{
                  background: bg,
                  border: `1px solid ${border}`,
                  borderLeft: `3px solid ${color}`,
                }}
              >
                <div className="p-3 space-y-2">
                  {/* Decision */}
                  <div className="flex items-start gap-2">
                    {isReplan
                      ? <AlertTriangle size={11} style={{ color, marginTop: 2 }} className="shrink-0" />
                      : <Lightbulb size={11} style={{ color, marginTop: 2 }} className="shrink-0" />
                    }
                    <p className="text-xs font-bold text-slate-700 leading-tight">{decision.decision}</p>
                  </div>

                  {/* Evidence */}
                  {decision.evidence && (
                    <div
                      className="ml-5 px-2.5 py-2 rounded-xl"
                      style={{ background: 'rgba(0,0,0,0.03)' }}
                    >
                      <p className="text-[10px] text-slate-500 leading-relaxed">{decision.evidence}</p>
                    </div>
                  )}

                  {/* Dependency */}
                  {decision.dependency && (
                    <div className="ml-5 flex items-center gap-1.5">
                      <Link size={9} style={{ color: '#7c3aed' }} className="shrink-0" />
                      <p className="text-[10px] font-mono" style={{ color: '#7c3aed' }}>
                        {decision.dependency}
                      </p>
                    </div>
                  )}

                  {/* Next action */}
                  <div
                    className="ml-5 flex items-start gap-1.5 px-2.5 py-1.5 rounded-xl"
                    style={{ background: `${color}08` }}
                  >
                    <ArrowRight size={9} style={{ color, marginTop: 2 }} className="shrink-0" />
                    <p className="text-[10px] font-semibold" style={{ color }}>{decision.next_action}</p>
                  </div>

                  {/* Source */}
                  <div className="ml-5 flex items-center justify-between">
                    {decision.source && (
                      <div className="flex items-center gap-1.5">
                        <BookOpen size={9} className="text-slate-400 shrink-0" />
                        <p className="text-[9px] text-slate-400 font-mono">Source: {decision.source}</p>
                      </div>
                    )}
                    <span className="text-[9px] text-slate-400 font-mono ml-auto">
                      {decision.timestamp
                        ? new Date(decision.timestamp).toLocaleTimeString('en', { hour12: false })
                        : ''}
                    </span>
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
