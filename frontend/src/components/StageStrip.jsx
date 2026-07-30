import { CheckCircle2, Circle, AlertTriangle, XCircle, MinusCircle, Loader2 } from 'lucide-react';

const ICONS = {
  complete: { Icon: CheckCircle2, dot: 'bg-emerald-400', text: 'text-emerald-400' },
  warning: { Icon: AlertTriangle, dot: 'bg-amber-400', text: 'text-amber-400' },
  failed: { Icon: XCircle, dot: 'bg-red-400', text: 'text-red-400' },
  skipped: { Icon: MinusCircle, dot: 'bg-slate-600', text: 'text-slate-500' },
  pending: { Icon: Circle, dot: 'bg-slate-600', text: 'text-slate-500' },
  active: { Icon: Loader2, dot: 'bg-brand animate-pulse', text: 'text-brand-light' },
};

/**
 * Generic stage strip — used by insurance mini-journey and mortgage/lending parity.
 * stages: [{ id, label, status, detail? }]
 */
export default function StageStrip({ stages = [], compact = false }) {
  if (!stages.length) return <span className="text-xs text-slate-500">—</span>;

  if (compact) {
    return (
      <div className="flex items-center gap-1">
        {stages.map((stage) => {
          const cfg = ICONS[stage.status] || ICONS.pending;
          return (
            <span
              key={stage.id}
              title={`${stage.label}: ${stage.detail || stage.status}`}
              className={`h-2 w-2 rounded-full ${cfg.dot}`}
            />
          );
        })}
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {stages.map((stage, i) => {
        const cfg = ICONS[stage.status] || ICONS.pending;
        const Icon = cfg.Icon;
        return (
          <div key={stage.id} className="flex items-center gap-1.5">
            <div
              className={`flex items-center gap-1 rounded-full px-2 py-0.5 ${
                stage.status === 'failed'
                  ? 'bg-red-500/10'
                  : stage.status === 'complete'
                    ? 'bg-emerald-500/10'
                    : 'bg-black/20'
              }`}
              title={stage.detail || stage.status}
            >
              <Icon className={`h-3 w-3 ${cfg.text} ${stage.status === 'active' ? 'animate-spin' : ''}`} />
              <span className={`text-[10px] ${cfg.text}`}>{stage.label}</span>
            </div>
            {i < stages.length - 1 && <span className="text-[10px] text-slate-600">→</span>}
          </div>
        );
      })}
    </div>
  );
}

/** Map mortgage/lending backend stages or timeline into StageStrip shape. */
export function stagesFromProgress(jobOrResult) {
  const backend =
    jobOrResult?.progress?.pipeline_stages ||
    jobOrResult?.results?.pipeline_stages ||
    jobOrResult?.pipeline_stages;
  if (backend?.length) {
    return backend.map((s) => ({
      id: s.id || s.label,
      label: s.label || s.id,
      status: s.status || 'complete',
      detail: s.detail || '',
    }));
  }

  const timeline = jobOrResult?.timeline || jobOrResult?.results?.timeline || [];
  if (timeline.length) {
    const order = ['ingest', 'validation', 'compliance', 'documents', 'risk', 'pricing', 'decision', 'error'];
    const byPhase = {};
    for (const row of timeline) {
      const phase = (row.phase || 'step').toLowerCase();
      byPhase[phase] = row;
    }
    const ids = order.filter((id) => byPhase[id]);
    const extra = Object.keys(byPhase).filter((k) => !order.includes(k));
    return [...ids, ...extra].map((id) => {
      const row = byPhase[id];
      const st = (row.status || '').toLowerCase();
      let status = 'complete';
      if (st.includes('fail') || st.includes('error') || st.includes('block')) status = 'failed';
      else if (st.includes('refer') || st.includes('warn')) status = 'warning';
      else if (st === 'start' || st === 'processing') status = 'active';
      return {
        id,
        label: id.charAt(0).toUpperCase() + id.slice(1),
        status,
        detail: typeof row.data === 'string' ? row.data : st,
      };
    });
  }

  // Fallback from decision fields (lending sync runs)
  const decision =
    jobOrResult?.decision ||
    jobOrResult?.results?.decision ||
    jobOrResult?.results?.memo?.decision;
  if (decision) {
    const failed = String(jobOrResult?.status || '').toLowerCase() === 'failed';
    return [
      { id: 'intake', label: 'Intake', status: failed ? 'failed' : 'complete' },
      { id: 'score', label: 'Scored', status: failed ? 'failed' : 'complete' },
      { id: 'price', label: 'Priced', status: failed ? 'skipped' : 'complete' },
      {
        id: 'decision',
        label: 'Decision',
        status: failed ? 'failed' : 'complete',
        detail: String(decision).toUpperCase(),
      },
    ];
  }

  if (jobOrResult?.status === 'processing') {
    return [
      { id: 'intake', label: 'Intake', status: 'complete' },
      { id: 'parse', label: 'Parse', status: 'active' },
      { id: 'underwrite', label: 'UW', status: 'pending' },
      { id: 'decision', label: 'Decision', status: 'pending' },
    ];
  }

  return [];
}
