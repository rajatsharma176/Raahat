import { motion } from 'framer-motion';
import { AlertTriangle } from 'lucide-react';

interface WorldEventButtonProps {
  onClick: () => void;
  worldEvent: string;
}

export function WorldEventButton({ onClick, worldEvent }: WorldEventButtonProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="mt-4 glass rounded-xl p-4 border border-amber-500/20 flex items-center justify-between gap-4"
    >
      <div className="flex items-start gap-3">
        <AlertTriangle size={18} className="text-amber-400 shrink-0 mt-0.5" />
        <div>
          <p className="text-amber-300 text-sm font-semibold">Inject World Event</p>
          <p className="text-slate-400 text-xs mt-0.5 leading-relaxed">
            Demo the replanning loop: <span className="text-amber-400">"{worldEvent}"</span>
          </p>
        </div>
      </div>
      <motion.button
        id="inject-world-event-btn"
        whileHover={{ scale: 1.03 }}
        whileTap={{ scale: 0.97 }}
        onClick={onClick}
        className="shrink-0 px-4 py-2 rounded-lg bg-amber-500/20 border border-amber-500/30 text-amber-400 text-xs font-bold hover:bg-amber-500/30 transition-colors"
      >
        Inject Event
      </motion.button>
    </motion.div>
  );
}
