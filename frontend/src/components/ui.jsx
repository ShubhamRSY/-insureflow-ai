export function Badge({ status, pulse = false }) {
  if (!status) return null;
  const s = String(status).toLowerCase();
  const colors = {
    ok: 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/20',
    healthy: 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/20',
    completed: 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/20',
    approved: 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/20',
    approve: 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/20',
    accept: 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/20',
    processing: 'bg-amber-500/15 text-amber-400 ring-amber-500/20',
    degraded: 'bg-amber-500/15 text-amber-400 ring-amber-500/20',
    pending: 'bg-amber-500/15 text-amber-400 ring-amber-500/20',
    refer: 'bg-sky-500/15 text-sky-400 ring-sky-500/20',
    failed: 'bg-red-500/15 text-red-400 ring-red-500/20',
    missing: 'bg-red-500/15 text-red-400 ring-red-500/20',
    error: 'bg-red-500/15 text-red-400 ring-red-500/20',
    decline: 'bg-red-500/15 text-red-400 ring-red-500/20',
    denied: 'bg-red-500/15 text-red-400 ring-red-500/20',
  };
  const cls = colors[s] || 'bg-slate-500/15 text-slate-400 ring-slate-500/20';
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset capitalize ${cls}`}>
      {(pulse || s === 'processing') && <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-current" />}
      {status}
    </span>
  );
}

export function DecisionBadge({ decision, jobStatus }) {
  if (jobStatus === 'processing') return <Badge status="processing" pulse />;
  if (jobStatus === 'failed') return <span className="text-slate-500">—</span>;
  if (!decision) return <span className="text-slate-500">—</span>;
  return <Badge status={decision} />;
}

export function StatCard({ label, value, sub, accent = 'brand' }) {
  const accents = {
    brand: 'from-brand/80 to-indigo-500',
    insurance: 'from-insurance to-cyan-400',
    mortgage: 'from-mortgage to-violet-400',
    success: 'from-emerald-500 to-teal-400',
  };
  return (
    <div className="glass-card group relative overflow-hidden p-5 animate-slide-up">
      <div className={`absolute inset-x-0 top-0 h-px bg-gradient-to-r ${accents[accent]} opacity-60`} />
      <p className="text-xs font-medium uppercase tracking-wider text-slate-500">{label}</p>
      <p className="mt-2 text-3xl font-bold tracking-tight text-white">{value}</p>
      {sub && <p className="mt-1 text-sm text-slate-400">{sub}</p>}
    </div>
  );
}

export function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      {Icon && <Icon className="mb-4 h-12 w-12 text-slate-600" strokeWidth={1.5} />}
      <p className="text-lg font-medium text-slate-300">{title}</p>
      {description && <p className="mt-1 max-w-sm text-sm text-slate-500">{description}</p>}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}

export function DemoCard({ name, description, tag, tagColor = 'brand', onClick, loading }) {
  const tagColors = {
    brand: 'text-brand-light',
    insurance: 'text-insurance',
    mortgage: 'text-mortgage',
  };
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={loading}
      className="glass-card group w-full p-5 text-left transition hover:border-brand/30 hover:shadow-glow disabled:opacity-60"
    >
      <h4 className="font-semibold text-white group-hover:text-brand-light transition">{name}</h4>
      <p className="mt-1.5 text-sm leading-relaxed text-slate-400">{description}</p>
      {tag && (
        <span className={`mt-3 inline-block text-xs font-semibold uppercase tracking-wider ${tagColors[tagColor]}`}>
          {tag}
        </span>
      )}
    </button>
  );
}

export function VerticalExplainer() {
  return (
    <div className="glass-card overflow-hidden">
      <div className="border-b border-white/[0.06] px-6 py-4">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">One Platform, Two Verticals</h3>
        <p className="mt-1 text-sm text-slate-500">Same engine — different document types and outputs</p>
      </div>
      <div className="grid md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-white/[0.06]">
        <div className="p-6">
          <div className="mb-3 flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-insurance/15">
              <span className="text-lg">🛡️</span>
            </div>
            <div>
              <h4 className="font-semibold text-insurance">Commercial Insurance</h4>
              <p className="text-xs text-slate-500">P&C carriers & MGAs</p>
            </div>
          </div>
          <ul className="space-y-2 text-sm text-slate-400">
            <li><span className="text-slate-300">In:</span> ACORD, loss runs, SOV, inspections, broker PDFs</li>
            <li><span className="text-slate-300">Out:</span> UW memo, premium quote, licensed sign-off, bind</li>
          </ul>
        </div>
        <div className="p-6">
          <div className="mb-3 flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-mortgage/15">
              <span className="text-lg">🏠</span>
            </div>
            <div>
              <h4 className="font-semibold text-mortgage">Mortgage / Lending</h4>
              <p className="text-xs text-slate-500">Banks & credit unions</p>
            </div>
          </div>
          <ul className="space-y-2 text-sm text-slate-400">
            <li><span className="text-slate-300">In:</span> W-2s, tax returns, credit, bank statements, appraisals</li>
            <li><span className="text-slate-300">Out:</span> Approve/deny decision, rate quote, compliance check</li>
          </ul>
        </div>
      </div>
      <div className="border-t border-white/[0.06] bg-white/[0.02] px-6 py-3 text-xs text-slate-500">
        Shared: OCR ingestion · multi-agent analysis · job queue · auth · audit trail · encryption
      </div>
    </div>
  );
}
