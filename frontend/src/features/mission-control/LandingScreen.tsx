import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Zap, Brain, ArrowRight, Edit3, Shield, GraduationCap,
  Hospital, Banknote, FileText, CheckCircle2, RefreshCw, Network
} from 'lucide-react';

interface LandingScreenProps {
  onStart: (customEvent?: string) => void;
  loading: boolean;
  error: string | null;
  demoEvent: string;
}

const PRESETS = [
  {
    label: '🏥 5-Day Hospitalization',
    text: 'I was hospitalized for five days after an accident. I have a Data Science exam on October 3 and I have insurance.',
    tags: ['education', 'insurance', 'finance'],
  },
  {
    label: '🚑 Emergency Surgery (4 Days)',
    text: 'Student admitted to hospital for emergency appendectomy with 4 days recovery required. Has midterm exam and health policy.',
    tags: ['education', 'insurance', 'documents'],
  },
  {
    label: '🩺 Multiple Fractures (7 Days)',
    text: 'Hospitalized for 7 days due to multiple fractures from a road accident. Missed semester finals and upcoming fee deadline.',
    tags: ['education', 'finance', 'insurance', 'documents'],
  },
];

const PIPELINE_STEPS = [
  { icon: Brain,        label: 'Situation Analysis',   color: '#4f46e5', desc: 'AI extracts event details & urgency' },
  { icon: Network,      label: 'Impact Mapping',        color: '#7c3aed', desc: 'Maps cross-domain dependencies' },
  { icon: Zap,          label: 'Task Planning',         color: '#0891b2', desc: 'Generates prioritized action plan' },
  { icon: GraduationCap,label: 'College Portal',        color: '#0284c7', desc: 'Requests exam rescheduling' },
  { icon: Shield,       label: 'Insurance Claims',      color: '#7c3aed', desc: 'Files coverage claims automatically' },
  { icon: Hospital,     label: 'Hospital Coordination', color: '#059669', desc: 'Confirms medical records & discharge' },
  { icon: Banknote,     label: 'Fee Deferral',          color: '#d97706', desc: 'Requests payment extensions' },
  { icon: FileText,     label: 'Document Requests',     color: '#0891b2', desc: 'Collects all needed paperwork' },
  { icon: CheckCircle2, label: 'Verification',          color: '#059669', desc: 'Validates all outcomes achieved' },
  { icon: RefreshCw,    label: 'Dynamic Replanning',    color: '#7c3aed', desc: 'Recovers from failures autonomously' },
];

export function LandingScreen({ onStart, loading, error, demoEvent }: LandingScreenProps) {
  const [eventText, setEventText] = useState(demoEvent);
  const [customizing, setCustomizing] = useState(false);

  return (
    <main className="min-h-[calc(100vh-60px)] flex flex-col items-center px-4 py-10">

      {/* ── Hero ────────────────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="text-center max-w-3xl mx-auto mb-8"
      >
        {/* Tag */}
        <motion.div
          initial={{ opacity: 0, scale: 0.92 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1 }}
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full mb-5 text-xs font-bold uppercase tracking-widest"
          style={{
            background: '#eef2ff',
            color: '#4f46e5',
            border: '1px solid rgba(79,70,229,0.2)',
          }}
        >
          <motion.span
            className="w-1.5 h-1.5 rounded-full"
            style={{ background: '#4f46e5' }}
            animate={{ opacity: [1, 0.3, 1] }}
            transition={{ duration: 1.4, repeat: Infinity }}
          />
          Autonomous Multi-Agent Continuity Engine · Sandbox Demo
        </motion.div>

        {/* Headline */}
        <h2 className="text-4xl md:text-5xl font-black leading-tight mb-4" style={{ color: '#0f172a' }}>
          When life{' '}
          <span style={{
            background: 'linear-gradient(135deg, #dc2626, #ea580c)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}>
            disrupts
          </span>
          ,<br />
          <span style={{
            background: 'linear-gradient(135deg, #4f46e5, #0891b2)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}>
            RAAHAT
          </span>{' '}
          handles everything else.
        </h2>

        <p className="text-slate-500 text-base md:text-lg leading-relaxed max-w-xl mx-auto">
          Describe what happened — RAAHAT's 10 autonomous AI agents detect disruptions,
          coordinate across <span className="font-semibold text-indigo-600">colleges, hospitals, insurance, and banks</span>,
          and dynamically replan when things go wrong.
        </p>
      </motion.div>

      {/* ── Event Input Card ─────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="card-3d w-full max-w-2xl mb-6 overflow-hidden"
      >
        <div
          className="px-5 py-3 border-b flex items-center gap-2"
          style={{ borderColor: '#f1f5f9', background: '#fafafa' }}
        >
          <div className="w-2 h-2 rounded-full animate-pulse" style={{ background: '#4f46e5' }} />
          <span className="text-xs font-bold text-slate-700 uppercase tracking-wide">What happened?</span>
          <button
            onClick={() => setCustomizing(!customizing)}
            className="ml-auto flex items-center gap-1 text-[10px] text-slate-400 hover:text-indigo-500 transition-colors"
          >
            <Edit3 size={10} />
            {customizing ? 'Use preset' : 'Customize'}
          </button>
        </div>

        <div className="p-5">
          {/* Event textarea */}
          <textarea
            value={eventText}
            onChange={e => setEventText(e.target.value)}
            rows={3}
            className="w-full text-sm text-slate-700 leading-relaxed resize-none outline-none bg-transparent font-medium"
            placeholder="Describe the medical or personal emergency..."
            style={{ color: '#334155' }}
          />

          {/* Presets */}
          <div className="flex flex-wrap gap-2 mt-3 mb-4">
            {PRESETS.map(p => (
              <button
                key={p.label}
                onClick={() => { setEventText(p.text); setCustomizing(false); }}
                className="text-[10px] font-semibold px-3 py-1.5 rounded-xl transition-all"
                style={{
                  background: eventText === p.text ? '#eef2ff' : '#f8fafc',
                  color: eventText === p.text ? '#4f46e5' : '#64748b',
                  border: eventText === p.text ? '1px solid rgba(79,70,229,0.3)' : '1px solid #e2e8f0',
                }}
              >
                {p.label}
              </button>
            ))}
          </div>

          {/* Error */}
          {error && (
            <p className="text-xs text-red-500 mb-3 px-3 py-2 rounded-xl" style={{ background: '#fef2f2', border: '1px solid #fca5a5' }}>
              ⚠ {error}
            </p>
          )}

          {/* CTA */}
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => onStart(eventText)}
            disabled={loading || !eventText.trim()}
            className="btn-primary w-full flex items-center justify-center gap-2 text-sm"
            id="start-btn"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Launching 10 Agents…
              </>
            ) : (
              <>
                Launch RAAHAT Autonomous System
                <ArrowRight size={16} />
              </>
            )}
          </motion.button>
        </div>
      </motion.div>

      {/* ── Pipeline Preview ─────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.35 }}
        className="w-full max-w-4xl"
      >
        <p className="text-center text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">
          What RAAHAT does autonomously
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
          {PIPELINE_STEPS.map((step, i) => (
            <motion.div
              key={step.label}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 + i * 0.04 }}
              className="card-3d p-3 text-center group cursor-default"
            >
              <div
                className="w-9 h-9 rounded-xl flex items-center justify-center mx-auto mb-2"
                style={{ background: `${step.color}12` }}
              >
                <step.icon size={16} style={{ color: step.color }} />
              </div>
              <p className="text-[10px] font-bold text-slate-700 leading-tight mb-1">{step.label}</p>
              <p className="text-[9px] text-slate-400 leading-relaxed opacity-0 group-hover:opacity-100 transition-opacity">
                {step.desc}
              </p>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </main>
  );
}
