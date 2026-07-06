import { CheckCircle2, Circle, AlertTriangle, XCircle, MinusCircle, Loader2 } from 'lucide-react';
import { buildMiniStripStages } from '../lib/pipelineJourney';

const ICONS = {
  complete: { Icon: CheckCircle2, dot: 'bg-emerald-400' },
  warning: { Icon: AlertTriangle, dot: 'bg-amber-400' },
  failed: { Icon: XCircle, dot: 'bg-red-400' },
  skipped: { Icon: MinusCircle, dot: 'bg-slate-600' },
  pending: { Icon: Circle, dot: 'bg-slate-700' },
  active: { Icon: Loader2, dot: 'bg-brand animate-pulse' },
};

const LABELS = {
  parse: 'Parsed',
  verify: 'Verified',
  reconcile: 'Reconciled',
  analyze: 'Scored',
  price: 'Priced',
  decision: 'Decision',
};

export default function JourneyMiniStrip({ job, compact = false }) {
  const stages = buildMiniStripStages(job);

  if (compact) {
    return (
      <div className="flex items-center gap-1">
        {stages.map((stage) => {
          const cfg = ICONS[stage.status] || ICONS.pending;
          return (
            <span
              key={stage.id}
              title={`${LABELS[stage.id] || stage.label}: ${stage.detail || stage.status}`}
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
            <div className="flex items-center gap-1 rounded-full bg-black/20 px-2 py-0.5" title={stage.detail}>
              <Icon className={`h-3 w-3 ${stage.status === 'active' ? 'animate-spin text-brand-light' : 'text-slate-400'}`} />
              <span className="text-[10px] text-slate-400">{LABELS[stage.id] || stage.label}</span>
            </div>
            {i < stages.length - 1 && <span className="text-[10px] text-slate-600">→</span>}
          </div>
        );
      })}
    </div>
  );
}
