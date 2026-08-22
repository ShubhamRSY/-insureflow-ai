import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { displayText, safeLower } from '../lib/safe';

const SEV_COLORS = {
  critical: 'bg-red-500/15 text-red-400 ring-red-500/30',
  high: 'bg-orange-500/15 text-orange-400 ring-orange-500/30',
  moderate: 'bg-amber-500/15 text-amber-400 ring-amber-500/30',
  low: 'bg-slate-500/15 text-slate-400 ring-slate-500/30',
};

const DECISION_COLORS = {
  accept: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400',
  conditional_accept: 'border-amber-500/40 bg-amber-500/10 text-amber-400',
  refer: 'border-sky-500/40 bg-sky-500/10 text-sky-400',
  decline: 'border-red-500/40 bg-red-500/10 text-red-400',
};

export function Collapsible({ title, defaultOpen = false, children }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-xl border border-white/[0.06] bg-surface/60">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-4 py-3 text-left transition hover:bg-white/[0.02]"
      >
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{title}</span>
        {open ? <ChevronDown className="h-4 w-4 text-slate-500" /> : <ChevronRight className="h-4 w-4 text-slate-500" />}
      </button>
      {open && <div className="border-t border-white/[0.04] px-4 pb-4 pt-3">{children}</div>}
    </div>
  );
}

function MemoSection({ number, title, children }) {
  return (
    <div className="space-y-2">
      <h3 className="flex items-center gap-2 text-sm font-bold text-slate-100">
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand/15 text-[11px] font-bold text-brand">
          {number}
        </span>
        {title}
      </h3>
      <div className="ml-8 space-y-1 text-sm leading-relaxed text-slate-300">{children}</div>
    </div>
  );
}

function MemoField({ label, value }) {
  if (!value && value !== 0) return null;
  return (
    <div className="flex flex-wrap items-baseline gap-x-2">
      <span className="text-xs font-semibold text-slate-400">{label}:</span>
      <span className="text-sm text-slate-200">{value}</span>
    </div>
  );
}

function MemoRow({ children }) {
  return <div className="flex flex-wrap gap-x-6 gap-y-1">{children}</div>;
}

function CheckItem({ checked, label }) {
  return (
    <div className="flex items-center gap-2">
      <span className={`text-xs font-bold ${checked ? 'text-emerald-400' : 'text-red-400'}`}>
        {checked ? '[X]' : '[ ]'}
      </span>
      <span className={`text-sm ${checked ? 'text-slate-300' : 'text-slate-500'}`}>{label}</span>
    </div>
  );
}

function DecisionCheckboxes({ decision }) {
  const d = safeLower(decision, 'refer');
  return (
    <div className="space-y-1.5">
      <CheckItem checked={d === 'accept' || d === 'conditional_accept'} label="ISSUE AS APPLIED" />
      <CheckItem checked={d === 'conditional_accept'} label="ISSUE WITH AMENDMENTS / RATED" />
      <CheckItem checked={d === 'refer'} label="POSTPONE / PENDING REQUIREMENTS" />
      <CheckItem checked={d === 'decline'} label="DECLINE" />
    </div>
  );
}

function PremiumTable({ components }) {
  if (!components || !components.length) return null;
  return (
    <div className="overflow-hidden rounded-lg border border-white/[0.06]">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-white/[0.06] bg-surface-overlay text-left text-[10px] uppercase tracking-wider text-slate-500">
            <th className="px-3 py-2">Component</th>
            <th className="px-3 py-2">Basis</th>
            <th className="px-3 py-2 text-right">Amount</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-white/[0.04]">
          {components.map((c, i) => (
            <tr key={i}>
              <td className="px-3 py-1.5 text-slate-300">{displayText(c.name)}</td>
              <td className="px-3 py-1.5 text-slate-500">{displayText(c.basis, '—')}</td>
              <td className="px-3 py-1.5 text-right font-mono text-slate-300">{displayText(c.amount)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function MemoReportView({ job }) {
  const results = job?.results || {};
  const memo = results.memo || '';
  const memoData = results.memo_data || {};
  const quote = results.quote_full || {};
  const decision = safeLower(results.decision, 'refer');
  const insuredName = displayText(results.insured_name || memoData.insured_name);
  const bundleId = results.bundle_id || job?.bundle_id || '';

  const allFindings = Array.isArray(memoData.key_findings) ? memoData.key_findings : [];
  const counts = { critical: 0, high: 0, moderate: 0, low: 0 };
  allFindings.forEach((f) => {
    const s = safeLower(f?.severity, 'moderate');
    if (counts[s] != null) counts[s] += 1;
  });

  const riskPct = memoData.overall_risk_score != null
    ? Math.round(Number(memoData.overall_risk_score) * 100)
    : null;

  const uwClass = quote?.medical?.underwriting_class || '';
  const premium = quote?.indicated_premium || quote?.gross_premium || 0;
  const components = quote?.components || [];
  const conditions = memoData.conditions || [];

  return (
    <div className="space-y-6">
      {/* Decision Hero */}
      <div className={`rounded-2xl border-2 p-6 ${DECISION_COLORS[decision] || DECISION_COLORS.refer}`}>
        <p className="text-xs font-semibold uppercase tracking-widest opacity-80">Underwriting Decision</p>
        <p className="mt-1 text-3xl font-bold tracking-tight uppercase">{decision.replace('_', ' ')}</p>
        {insuredName && <p className="mt-1 text-lg font-medium text-white">{insuredName}</p>}
        <div className="mt-4 flex flex-wrap gap-6">
          {premium > 0 && (
            <div>
              <p className="text-xs uppercase opacity-70">Indicated Premium</p>
              <p className="text-2xl font-bold text-white">${Math.round(premium).toLocaleString()}</p>
            </div>
          )}
          {riskPct != null && (
            <div>
              <p className="text-xs uppercase opacity-70">Risk Score</p>
              <p className="text-2xl font-bold">{riskPct}<span className="text-sm font-normal opacity-70">/100</span></p>
            </div>
          )}
          {uwClass && (
            <div>
              <p className="text-xs uppercase opacity-70">UW Class</p>
              <p className="text-lg font-semibold capitalize">{uwClass.replace(/_/g, ' ')}</p>
            </div>
          )}
        </div>
      </div>

      {/* Findings Summary */}
      {allFindings.length > 0 && (
        <div className="flex items-center gap-3">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Findings</h4>
          <div className="flex gap-2">
            {Object.entries(counts).map(([sev, n]) => n > 0 && (
              <span key={sev} className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ring-1 ring-inset ${SEV_COLORS[sev]}`}>
                {n} {sev}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Clean Memo */}
      {memo ? (
        <div className="rounded-2xl border border-white/[0.08] bg-surface/80 p-6">
          <div className="mb-4 border-b border-white/[0.06] pb-4">
            <h2 className="text-lg font-bold tracking-tight text-slate-100">Underwriting Evaluation Memo</h2>
            <div className="mt-2 flex flex-wrap gap-x-6 text-xs text-slate-400">
              <span>Case: <span className="font-mono font-semibold text-slate-200">{bundleId}</span></span>
              <span>Product: <span className="font-semibold text-slate-200">{displayText(results.product_line || results.insurance_line)}</span></span>
              <span>Face: <span className="font-semibold text-slate-200">${Number(results.face_amount || 0).toLocaleString()}</span></span>
            </div>
          </div>
          <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-slate-300">{memo}</pre>
        </div>
      ) : (
        <div className="rounded-2xl border border-white/[0.08] bg-surface/80 p-6">
          <p className="text-sm text-slate-400">Memo not available for this submission.</p>
        </div>
      )}

      {/* Conditions */}
      {conditions.length > 0 && (
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">Conditions</h4>
          <ul className="space-y-1.5">
            {conditions.map((c, i) => (
              <li key={i} className="flex gap-2 text-sm text-slate-300">
                <span className="text-brand">•</span>{displayText(c)}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Technical Details — collapsed */}
      <Collapsible title="Premium Build-up" defaultOpen={components.length > 0}>
        <PremiumTable components={components} />
      </Collapsible>

      <Collapsible title="Key Findings">
        {allFindings.length === 0 ? (
          <p className="text-xs text-slate-500">No findings.</p>
        ) : (
          <div className="space-y-2">
            {allFindings.map((f, i) => (
              <div key={i} className="flex items-start gap-2">
                <span className={`mt-0.5 shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ring-1 ring-inset ${SEV_COLORS[safeLower(f?.severity, 'moderate')] || SEV_COLORS.moderate}`}>
                  {safeLower(f?.severity, 'moderate')}
                </span>
                <div>
                  <p className="text-sm font-medium text-slate-200">{displayText(f?.title, 'Finding')}</p>
                  {f?.description && <p className="mt-0.5 text-xs text-slate-400">{displayText(f.description)}</p>}
                </div>
              </div>
            ))}
          </div>
        )}
      </Collapsible>
    </div>
  );
}
