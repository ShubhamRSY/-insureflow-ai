import { useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

// Hierarchy-based back control: always goes to the logical parent route,
// never relies on browser history — so it behaves the same whether the user
// arrived from inside the app or via a deep link / full page load.
export function PageBack({ to, label = 'Back' }) {
  const navigate = useNavigate();
  return (
    <button
      type="button"
      onClick={() => navigate(to)}
      className="inline-flex items-center gap-1.5 rounded-md px-1 py-0.5 text-xs font-medium text-slate-400 transition-colors hover:text-slate-200"
    >
      <ArrowLeft className="h-3.5 w-3.5" />
      {label}
    </button>
  );
}

export function Hint({ text, children, className = '', position = 'top' }) {
  const anchorRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [box, setBox] = useState(null);

  useLayoutEffect(() => {
    if (!open || !anchorRef.current) return undefined;
    const place = () => {
      const rect = anchorRef.current.getBoundingClientRect();
      const width = Math.min(320, window.innerWidth - 16);
      let left = rect.left + rect.width / 2 - width / 2;
      left = Math.max(8, Math.min(left, window.innerWidth - width - 8));
      const preferTop = position !== 'bottom' && rect.top > 88;
      const gap = 8;
      const top = preferTop ? rect.top - gap : rect.bottom + gap;
      setBox({ left, top, width, preferTop });
    };
    place();
    window.addEventListener('scroll', place, true);
    window.addEventListener('resize', place);
    return () => {
      window.removeEventListener('scroll', place, true);
      window.removeEventListener('resize', place);
    };
  }, [open, position, text]);

  if (!text) return children;
  return (
    <span
      ref={anchorRef}
      className={`hint-anchor ${className}`.trim()}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      {children}
      {open && box && createPortal(
        <span
          role="tooltip"
          className="hint-bubble"
          style={{
            position: 'fixed',
            left: box.left,
            width: box.width,
            top: box.preferTop ? undefined : box.top,
            bottom: box.preferTop ? window.innerHeight - box.top : undefined,
          }}
        >
          {text}
        </span>,
        document.body,
      )}
    </span>
  );
}

export function HintCheckbox({
  hint,
  label,
  className = '',
  inputClassName = 'rounded',
  labelClassName = 'flex items-center gap-1.5 text-xs text-slate-300',
  ...inputProps
}) {
  return (
    <Hint text={hint} className={className}>
      <label className={`${labelClassName} hint-label cursor-help`}>
        <input type="checkbox" className={inputClassName} {...inputProps} />
        <span>{label}</span>
      </label>
    </Hint>
  );
}

export function Badge({ status, pulse = false, label }) {
  if (!status) return null;
  const s = String(status).toLowerCase();
  const colors = {
    ok: 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/20',
    healthy: 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/20',
    completed: 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/20',
    approved: 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/20',
    approve: 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/20',
    accept: 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/20',
    bound: 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/20',
    issued: 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/20',
    active: 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/20',
    cleared: 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/20',
    acknowledged: 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/20',
    conditional_accept: 'bg-amber-500/15 text-amber-400 ring-amber-500/20',
    processing: 'bg-amber-500/15 text-amber-400 ring-amber-500/20',
    degraded: 'bg-amber-500/15 text-amber-400 ring-amber-500/20',
    pending: 'bg-amber-500/15 text-amber-400 ring-amber-500/20',
    watch: 'bg-amber-500/15 text-amber-400 ring-amber-500/20',
    monitored: 'bg-sky-500/15 text-sky-400 ring-sky-500/20',
    monitoring: 'bg-sky-500/15 text-sky-400 ring-sky-500/20',
    refer: 'bg-sky-500/15 text-sky-400 ring-sky-500/20',
    sent: 'bg-sky-500/15 text-sky-400 ring-sky-500/20',
    low: 'bg-sky-500/15 text-sky-400 ring-sky-500/20',
    open: 'bg-amber-500/15 text-amber-400 ring-amber-500/20',
    moderate: 'bg-amber-500/15 text-amber-400 ring-amber-500/20',
    high: 'bg-orange-500/15 text-orange-400 ring-orange-500/20',
    critical: 'bg-red-500/15 text-red-400 ring-red-500/20',
    failed: 'bg-red-500/15 text-red-400 ring-red-500/20',
    missing: 'bg-red-500/15 text-red-400 ring-red-500/20',
    error: 'bg-red-500/15 text-red-400 ring-red-500/20',
    decline: 'bg-red-500/15 text-red-400 ring-red-500/20',
    denied: 'bg-red-500/15 text-red-400 ring-red-500/20',
    closed: 'bg-slate-500/15 text-slate-400 ring-slate-500/20',
    pass: 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/20',
    flag: 'bg-amber-500/15 text-amber-400 ring-amber-500/20',
    fail: 'bg-red-500/15 text-red-400 ring-red-500/20',
    waived: 'bg-slate-500/15 text-slate-400 ring-slate-500/20',
    // Bureau / order / issuance lifecycle statuses (MIB, APS, renewal, binder)
    submitted: 'bg-sky-500/15 text-sky-400 ring-sky-500/20',
    submitted_to_vendor: 'bg-sky-500/15 text-sky-400 ring-sky-500/20',
    vendor_processing: 'bg-amber-500/15 text-amber-400 ring-amber-500/20',
    received: 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/20',
    reviewed: 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/20',
    not_requested: 'bg-slate-500/15 text-slate-400 ring-slate-500/20',
    not_ready: 'bg-slate-500/15 text-slate-400 ring-slate-500/20',
    pending_uw_approval: 'bg-amber-500/15 text-amber-400 ring-amber-500/20',
    binder_issued: 'bg-sky-500/15 text-sky-400 ring-sky-500/20',
    policy_requested: 'bg-sky-500/15 text-sky-400 ring-sky-500/20',
    policy_issued: 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/20',
    policy_delivered: 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/20',
    renewal_due: 'bg-amber-500/15 text-amber-400 ring-amber-500/20',
    renewal_overdue: 'bg-red-500/15 text-red-400 ring-red-500/20',
    convertible: 'bg-sky-500/15 text-sky-400 ring-sky-500/20',
    conversion_window_open: 'bg-sky-500/15 text-sky-400 ring-sky-500/20',
    conversion_window_closed: 'bg-slate-500/15 text-slate-400 ring-slate-500/20',
    lapsed: 'bg-red-500/15 text-red-400 ring-red-500/20',
    in_review: 'bg-amber-500/15 text-amber-400 ring-amber-500/20',
    rejected: 'bg-red-500/15 text-red-400 ring-red-500/20',
    changes_requested: 'bg-amber-500/15 text-amber-400 ring-amber-500/20',
    flagged: 'bg-red-500/15 text-red-400 ring-red-500/20',
  };
  const cls = colors[s] || 'bg-slate-500/15 text-slate-400 ring-slate-500/20';
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset capitalize ${cls}`}>
      {(pulse || s === 'processing') && <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-current" />}
      {label ?? status}
    </span>
  );
}

export function DecisionBadge({ decision, jobStatus }) {
  if (jobStatus === 'processing') return <Badge status="processing" pulse />;
  if (jobStatus === 'failed') return <span className="text-slate-500">—</span>;
  if (!decision) return <span className="text-slate-500">—</span>;
  return <Badge status={decision} />;
}

// Shared building blocks for the "Rate Provenance" tool panels (Actuarial,
// Premium Calculator, MIB/APS orders, Beneficiary, Renewal, Issuance) — keeps
// them on the app's theme tokens instead of one-off hardcoded dark colors.
export function RatePanel({ children, className = '' }) {
  return (
    <div className={`rounded-lg border border-white/10 bg-surface-overlay/50 p-3 ${className}`.trim()}>
      {children}
    </div>
  );
}

export function RateStat({ label, value, hint }) {
  return (
    <div className="text-xs">
      <Hint text={hint}>
        <span className={`text-slate-500 ${hint ? 'hint-label cursor-help' : ''}`}>{label}: </span>
      </Hint>
      <span className="ml-1.5 font-medium text-slate-100">{value ?? 'N/A'}</span>
    </div>
  );
}

export function RateField({ label, hint, children }) {
  return (
    <label className="block text-xs text-slate-500">
      <Hint text={hint}>
        <span className={hint ? 'hint-label cursor-help' : ''}>{label}</span>
      </Hint>
      <div className="mt-1">{children}</div>
    </label>
  );
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
    lending: 'text-lending',
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

const PIPELINE_STEPS = [
  { label: 'Intake', desc: 'Connect sources & pull package' },
  { label: 'Parse', desc: 'OCR, classify, extract' },
  { label: 'Verify', desc: 'Oracles / medical UW' },
  { label: 'Score', desc: 'Multi-agent risk analysis' },
  { label: 'Price', desc: 'Indicated premium / rate' },
  { label: 'Decide', desc: 'UW memo & workflow' },
];

export function VerticalExplainer() {
  return (
    <div className="glass-card overflow-hidden">
      <div className="border-b border-white/[0.06] px-6 py-4">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Intake to decision</h3>
        <p className="mt-1 text-sm text-slate-500">
          Every submission runs through a visible pipeline — open any job for the full submission journey
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2 border-b border-white/[0.06] px-6 py-4">
        {PIPELINE_STEPS.map((step, i) => (
          <div key={step.label} className="flex items-center gap-2">
            <div className="rounded-lg bg-surface-overlay px-3 py-2 ring-1 ring-white/[0.04]">
              <p className="text-xs font-semibold text-slate-200">{step.label}</p>
              <p className="text-[10px] text-slate-500">{step.desc}</p>
            </div>
            {i < PIPELINE_STEPS.length - 1 && <span className="text-slate-600">→</span>}
          </div>
        ))}
      </div>
      <div className="grid md:grid-cols-2 lg:grid-cols-4 divide-y md:divide-y-0 md:divide-x divide-white/[0.06]">
        <div className="p-6">
          <h4 className="font-semibold text-insurance">Commercial Insurance</h4>
          <p className="mt-1 text-xs text-slate-500">P&C carriers & MGAs</p>
          <ul className="mt-3 space-y-1.5 text-sm text-slate-400">
            <li>ACORD, loss runs, SOV, inspections</li>
            <li>Premium build-up, oracles, bind-ready memo</li>
          </ul>
        </div>
        <div className="p-6">
          <h4 className="font-semibold text-amber-400">Personal Lines</h4>
          <p className="mt-1 text-xs text-slate-500">Homeowners · Auto · Life</p>
          <ul className="mt-3 space-y-1.5 text-sm text-slate-400">
            <li>HO-3, MVR, paramedical exams</li>
            <li>Filing-grade rating & medical underwriting</li>
          </ul>
        </div>
        <div className="p-6">
          <h4 className="font-semibold text-mortgage">Mortgage</h4>
          <p className="mt-1 text-xs text-slate-500">Banks & credit unions</p>
          <ul className="mt-3 space-y-1.5 text-sm text-slate-400">
            <li>W-2s, tax returns, credit, appraisals</li>
            <li>Income verification, collateral, rate lock</li>
          </ul>
        </div>
        <div className="p-6">
          <h4 className="font-semibold text-emerald-400">Lending</h4>
          <p className="mt-1 text-xs text-slate-500">Consumer & commercial credit</p>
          <ul className="mt-3 space-y-1.5 text-sm text-slate-400">
            <li>Application data, credit pulls, bank statements</li>
            <li>Pricing, compliance, adverse action notices</li>
          </ul>
        </div>
      </div>
      <div className="border-t border-white/[0.06] bg-white/[0.02] px-6 py-3 text-xs text-slate-500">
        Enterprise: oracle feeds · loss control · claims · CRM · human checkpoints · encrypted audit trail
      </div>
    </div>
  );
}
