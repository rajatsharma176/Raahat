import { motion, AnimatePresence } from 'framer-motion';
import type { RAAHATState, Document } from '../../types';
import { FileCheck, FileX, File, Clock, CheckCircle2, AlertCircle, Download, Hospital } from 'lucide-react';

interface DocumentsPanelProps { state: RAAHATState | null; }

const ALL_DOCS = [
  {
    key: 'admission_note',
    label: 'Hospital Admission Note',
    color: '#059669',
    desc: 'Official hospital admission record',
    usedFor: ['Insurance claim', 'Exam deferral'],
    icon: '🏥',
  },
  {
    key: 'discharge_summary',
    label: 'Discharge Summary',
    color: '#0891b2',
    desc: 'Medical discharge certificate',
    usedFor: ['Insurance claim (required)', 'College records'],
    icon: '📋',
  },
  {
    key: 'medical_certificate',
    label: 'Medical Certificate',
    color: '#4f46e5',
    desc: 'Doctor-issued fitness certificate',
    usedFor: ['Exam deferral', 'Attendance waiver'],
    icon: '🩺',
  },
];

function formatDate(iso?: string): string {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleString('en-IN', {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    });
  } catch { return iso; }
}

function MetaField({ label, value, wide }: { label: string; value: string; wide?: boolean }) {
  return (
    <div className={`${wide ? 'col-span-2' : ''} rounded-xl px-2.5 py-2`}
      style={{ background: '#f8fafc', border: '1px solid #e2e8f0' }}>
      <p className="text-[9px] text-slate-400 uppercase tracking-wide font-mono">{label}</p>
      <p className="text-[11px] text-slate-700 mt-0.5 font-medium truncate">{value}</p>
    </div>
  );
}

function DocCard({ docMeta, doc }: { docMeta: typeof ALL_DOCS[0]; doc: Document | undefined }) {
  const acquired = !!doc;
  const { color, label, desc, usedFor, key, icon } = docMeta;

  return (
    <motion.div
      layout
      className="rounded-xl overflow-hidden"
      style={{
        border: `1px solid ${acquired ? `${color}30` : '#e2e8f0'}`,
        background: acquired ? `${color}06` : 'white',
        boxShadow: acquired ? `0 4px 16px ${color}10` : '0 1px 3px rgba(15,23,42,0.04)',
      }}
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      id={`doc-${key}`}
    >
      {/* Header */}
      <div
        className="flex items-center gap-3 px-4 py-3"
        style={{ borderBottom: `1px solid ${acquired ? `${color}15` : '#f1f5f9'}` }}
      >
        <div
          className="w-9 h-9 rounded-xl flex items-center justify-center text-lg shrink-0"
          style={{ background: acquired ? `${color}12` : '#f8fafc' }}
        >
          {acquired ? icon : <File size={16} className="text-slate-300" />}
        </div>
        <div className="flex-1 min-w-0">
          <p className={`text-sm font-semibold truncate ${acquired ? 'text-slate-800' : 'text-slate-400'}`}>
            {label}
          </p>
          <p className="text-[10px] text-slate-400 mt-0.5">{desc}</p>
        </div>
        <span
          className="text-[10px] font-bold px-2.5 py-1 rounded-full shrink-0"
          style={{
            background: acquired ? `${color}15` : '#f8fafc',
            color: acquired ? color : '#94a3b8',
            border: `1px solid ${acquired ? `${color}25` : '#e2e8f0'}`,
          }}
        >
          {acquired ? '✓ received' : '○ pending'}
        </span>
      </div>

      {/* Acquired body */}
      {acquired && doc && (
        <div className="px-4 py-3 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-[9px] text-slate-400 uppercase tracking-wide font-mono">Doc ID</span>
              <span className="text-xs font-mono font-bold" style={{ color }}>{doc.document_id}</span>
            </div>
            <button
              className="flex items-center gap-1 text-[10px] text-slate-400 hover:text-indigo-500 transition-colors"
              title="View document (sandbox)"
            >
              <Download size={10} />
              <span>View</span>
            </button>
          </div>

          <div className="grid grid-cols-2 gap-1.5">
            {doc.metadata?.issued_by !== undefined && (
              <MetaField label="Issued By" value={String(doc.metadata.issued_by)} wide />
            )}
            {doc.metadata?.admission_date && (
              <MetaField label="Admission" value={String(doc.metadata.admission_date)} />
            )}
            {doc.metadata?.discharge_date && (
              <MetaField label="Discharge" value={String(doc.metadata.discharge_date)} />
            )}
            {doc.metadata?.diagnosis && (
              <MetaField label="Diagnosis" value={String(doc.metadata.diagnosis)} wide />
            )}
            {doc.metadata?.treating_physician && (
              <MetaField label="Physician" value={String(doc.metadata.treating_physician)} />
            )}
            {doc.metadata?.fit_to_resume && (
              <MetaField label="Fit to Resume" value={String(doc.metadata.fit_to_resume)} />
            )}
            {doc.metadata?.valid_from && (
              <MetaField label="Valid From" value={String(doc.metadata.valid_from)} />
            )}
            {doc.metadata?.valid_to && (
              <MetaField label="Valid To" value={String(doc.metadata.valid_to)} />
            )}
            {doc.metadata?.reason && (
              <MetaField label="Reason" value={String(doc.metadata.reason)} wide />
            )}
          </div>

          <div className="flex flex-wrap gap-1.5">
            {usedFor.map(use => (
              <span
                key={use}
                className="text-[9px] font-bold px-2 py-0.5 rounded-full"
                style={{ background: `${color}12`, color, border: `1px solid ${color}20` }}
              >
                → {use}
              </span>
            ))}
          </div>

          {doc.retrieved_at && (
            <div className="flex items-center gap-1.5 text-[10px] text-slate-400">
              <Clock size={9} />
              <span>Retrieved {formatDate(doc.retrieved_at)}</span>
              <CheckCircle2 size={9} className="ml-auto" style={{ color }} />
              <span style={{ color }} className="text-[9px] font-semibold">Verified</span>
            </div>
          )}
        </div>
      )}

      {/* Pending body */}
      {!acquired && (
        <div className="px-4 py-3">
          <div className="flex items-center gap-2 text-[10px] text-slate-400">
            <AlertCircle size={10} />
            <span>Will be requested by DocumentAgent when triggered</span>
          </div>
          <div className="flex flex-wrap gap-1 mt-2">
            {usedFor.map(use => (
              <span
                key={use}
                className="text-[9px] px-2 py-0.5 rounded-full font-mono"
                style={{ background: '#f8fafc', color: '#94a3b8', border: '1px solid #e2e8f0' }}
              >
                → {use}
              </span>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}

export function DocumentsPanel({ state }: DocumentsPanelProps) {
  const docs = state?.documents ?? {};
  const acquiredCount = Object.keys(docs).length;
  const totalDocs = ALL_DOCS.length;
  const extraDocs = Object.entries(docs).filter(([key]) => !ALL_DOCS.find(d => d.key === key));
  const pct = Math.round((acquiredCount / totalDocs) * 100);

  return (
    <div className="card rounded-xl overflow-hidden">
      {/* Header */}
      <div
        className="px-4 py-3 border-b flex items-center justify-between"
        style={{ borderColor: '#f1f5f9', background: '#fafafa' }}
      >
        <div>
          <h2 className="text-sm font-bold text-slate-700">Document Vault</h2>
          <p className="text-xs text-slate-400 mt-0.5">Medical documents acquired by autonomous agents</p>
        </div>
        <div className="text-right">
          <div
            className="text-xl font-black font-mono"
            style={{ color: acquiredCount > 0 ? '#059669' : '#94a3b8' }}
          >
            {acquiredCount}/{totalDocs}
          </div>
          <div className="text-[10px] text-slate-400">acquired</div>
        </div>
      </div>

      {/* Progress bar */}
      <div className="px-4 py-2 border-b" style={{ borderColor: '#f8fafc' }}>
        <div className="h-2 rounded-full overflow-hidden" style={{ background: '#e2e8f0' }}>
          <motion.div
            className="h-full rounded-full"
            style={{ background: 'linear-gradient(90deg, #059669, #10b981)' }}
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.6 }}
          />
        </div>
        <div className="flex justify-between text-[9px] text-slate-400 font-mono mt-1">
          <span>{acquiredCount === 0 ? 'Awaiting DocumentAgent' : `${acquiredCount} doc${acquiredCount !== 1 ? 's' : ''} secured`}</span>
          <span>{pct}% complete</span>
        </div>
      </div>

      <div className="p-3 space-y-2">
        <AnimatePresence>
          {ALL_DOCS.map(docMeta => (
            <DocCard key={docMeta.key} docMeta={docMeta} doc={docs[docMeta.key]} />
          ))}
          {extraDocs.map(([key, doc]) => (
            <motion.div
              key={key}
              layout
              className="rounded-xl px-4 py-3"
              style={{ border: '1px solid #6ee7b7', background: '#f0fdf4' }}
            >
              <div className="flex items-center gap-2">
                <FileCheck size={14} style={{ color: '#059669' }} className="shrink-0" />
                <span className="text-xs font-semibold text-emerald-700 capitalize">
                  {key.replace(/_/g, ' ')}
                </span>
                <span className="text-[10px] font-mono text-slate-400 ml-auto">{doc.document_id}</span>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {!state && (
          <div className="text-center py-8 text-slate-400">
            <FileX size={24} className="mx-auto mb-3 opacity-20" />
            <p className="text-xs">Start a scenario to see documents acquired by agents</p>
          </div>
        )}

        <div
          className="mt-2 px-3 py-2 rounded-xl text-center"
          style={{ background: '#fffbeb', border: '1px solid #fde68a' }}
        >
          <p className="text-[9px] text-amber-600 font-mono">
            ⚠️ SANDBOX — All documents are synthetic demo data. No real systems connected.
          </p>
        </div>
      </div>
    </div>
  );
}
