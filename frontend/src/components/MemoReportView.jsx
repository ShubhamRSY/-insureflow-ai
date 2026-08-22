import { useState } from 'react';
import { ChevronDown, ChevronRight, Info } from 'lucide-react';
import { displayText, safeLower } from '../lib/safe';

const SEV_COLORS = {
  critical: 'bg-red-500/15 text-red-400 ring-red-500/30',
  high: 'bg-orange-500/15 text-orange-400 ring-orange-500/30',
  moderate: 'bg-amber-500/15 text-amber-400 ring-amber-500/30',
  low: 'bg-slate-500/15 text-slate-400 ring-slate-500/30',
};

const SEV_ORDER = { critical: 0, high: 1, moderate: 2, low: 3 };

const DECISION_COLORS = {
  accept: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400',
  conditional_accept: 'border-amber-500/40 bg-amber-500/10 text-amber-400',
  refer: 'border-sky-500/40 bg-sky-500/10 text-sky-400',
  decline: 'border-red-500/40 bg-red-500/10 text-red-400',
};

const DECISION_LABELS = {
  accept: 'Issue as Applied',
  conditional_accept: 'Issue with Amendments',
  refer: 'Refer for Review',
  decline: 'Decline',
};

function fmtCurrency(v) {
  if (!v || v === 0) return '—';
  return `$${Math.round(v).toLocaleString()}`;
}

function fmtFactor(v) {
  if (v == null || v === '') return '—';
  const n = Number(v);
  if (isNaN(n)) return String(v);
  return n.toFixed(2);
}

function fmtPct(v) {
  if (v == null || v === '' || v === 0) return '0.0%';
  const n = Number(v);
  if (isNaN(n)) return String(v);
  return `${n.toFixed(1)}%`;
}

export function Collapsible({ title, defaultOpen = false, children, badge }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-xl border border-white/[0.06] bg-surface/60">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-4 py-3 text-left transition hover:bg-white/[0.02]"
      >
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{title}</span>
          {badge != null && (
            <span className="rounded-full bg-brand/15 px-1.5 py-0.5 text-[9px] font-bold text-brand">{badge}</span>
          )}
        </div>
        {open ? <ChevronDown className="h-4 w-4 text-slate-500" /> : <ChevronRight className="h-4 w-4 text-slate-500" />}
      </button>
      {open && <div className="border-t border-white/[0.04] px-4 pb-4 pt-3">{children}</div>}
    </div>
  );
}

function FindingCard({ finding, compact = false }) {
  const sev = safeLower(finding?.severity, 'moderate');
  return (
    <div className={`flex items-start gap-2.5 rounded-lg border border-white/[0.04] bg-surface/40 p-3`}>
      <span className={`mt-0.5 shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ring-1 ring-inset ${SEV_COLORS[sev] || SEV_COLORS.moderate}`}>
        {sev}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-slate-200">{displayText(finding?.title, 'Finding')}</p>
        {finding?.description && (
          <p className="mt-1 text-xs leading-relaxed text-slate-400">{displayText(finding.description)}</p>
        )}
      </div>
    </div>
  );
}

function InlineFindings({ findings, maxShow = 4 }) {
  const sorted = [...findings].sort((a, b) => {
    const sa = SEV_ORDER[safeLower(a?.severity, 'moderate')] ?? 2;
    const sb = SEV_ORDER[safeLower(b?.severity, 'moderate')] ?? 2;
    return sa - sb;
  });
  const shown = sorted.slice(0, maxShow);
  const remaining = sorted.length - maxShow;

  if (!shown.length) return null;

  return (
    <div className="space-y-2">
      {shown.map((f, i) => (
        <FindingCard key={f.finding_id || i} finding={f} />
      ))}
      {remaining > 0 && (
        <p className="text-xs text-slate-500">+ {remaining} more finding{remaining > 1 ? 's' : ''} — see All Key Findings below</p>
      )}
    </div>
  );
}

function cleanMemoText(text) {
  if (!text) return '';
  return text
    .replace(/\[(?:CRITICAL|HIGH|MODERATE|LOW|INFO)\]\s*/g, '')
    .replace(/Risk score:\s*\d+\/100\s*·\s*\d+ findings?\s*\([^)]*\)\s*/g, '')
    .trim();
}

export default function MemoReportView({ job }) {
  const results = job?.results || {};
  const memoObj = results.memo && typeof results.memo === 'object' ? results.memo : {};
  const memoText = memoObj.summary || results.memo_text || '';
  const quote = results.quote_full || {};
  const worksheet = results.uw_worksheet || {};

  const decision = safeLower(results.ai_decision || results.outcome || memoObj.decision, 'refer');
  const insuredName = displayText(results.insured_name || memoObj.insured_name);
  const bundleId = results.bundle_id || job?.bundle_id || '';

  const faceAmount = results.tiv || results.face_amount || memoObj.face_amount || (quote.indicated_terms || {}).limit || 0;
  const premium = (quote.indicated_terms || {}).premium || quote.adjusted_premium || worksheet.indicated_terms?.premium || 0;
  const uwClass = (quote.medical || {}).underwriting_class || worksheet.uw_class || '';

  const buildup = worksheet.premium_buildup || [];
  const quoteComponents = (quote.metadata || {}).components || [];
  const premiumSteps = buildup.length > 0 ? buildup : quoteComponents;

  const allFindings = Array.isArray(memoObj.key_findings) ? memoObj.key_findings : [];
  const sortedFindings = [...allFindings].sort((a, b) => {
    const sa = SEV_ORDER[safeLower(a?.severity, 'moderate')] ?? 2;
    const sb = SEV_ORDER[safeLower(b?.severity, 'moderate')] ?? 2;
    return sa - sb;
  });

  const counts = { critical: 0, high: 0, moderate: 0, low: 0 };
  allFindings.forEach((f) => {
    const s = safeLower(f?.severity, 'moderate');
    if (counts[s] != null) counts[s] += 1;
  });

  const riskPct = memoObj.overall_risk_score != null
    ? Math.round(Number(memoObj.overall_risk_score) * 100)
    : null;

  const conditions = memoObj.conditions || [];

  // Extract "What to do next" from memo text (lines starting with digits)
  const memoLines = memoText.split('\n');
  const whyDecisionIdx = memoLines.findIndex((l) => l.trim() === 'Why this decision');
  const whatToDoIdx = memoLines.findIndex((l) => l.trim() === 'What to do next');
  const nextSteps = whatToDoIdx >= 0 ? memoLines.slice(whatToDoIdx).join('\n') : '';

  return (
    <div className="space-y-5">
      {/* Decision Hero */}
      <div className={`rounded-2xl border-2 p-5 ${DECISION_COLORS[decision] || DECISION_COLORS.refer}`}>
        <div className="flex items-start justify-between">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest opacity-70">Underwriting Decision</p>
            <p className="mt-1 text-3xl font-bold tracking-tight uppercase">{DECISION_LABELS[decision] || decision.replace('_', ' ')}</p>
            {insuredName && <p className="mt-1 text-base font-medium text-white">{insuredName}</p>}
          </div>
          <div className="text-right">
            {riskPct != null && (
              <div>
                <p className="text-[10px] uppercase opacity-70">Risk Score</p>
                <p className="text-3xl font-bold">{riskPct}<span className="text-sm font-normal opacity-60">/100</span></p>
              </div>
            )}
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-6 border-t border-white/10 pt-4">
          <div>
            <p className="text-[10px] uppercase opacity-70">Face Amount</p>
            <p className="text-xl font-bold text-white">{fmtCurrency(faceAmount)}</p>
          </div>
          <div>
            <p className="text-[10px] uppercase opacity-70">Indicated Premium</p>
            <p className="text-xl font-bold text-white">{fmtCurrency(premium)}</p>
          </div>
          {uwClass && (
            <div>
              <p className="text-[10px] uppercase opacity-70">UW Class</p>
              <p className="text-lg font-semibold capitalize">{uwClass.replace(/_/g, ' ')}</p>
            </div>
          )}
        </div>
      </div>

      {/* Why This Decision — colored findings */}
      {allFindings.length > 0 && (
        <div className="rounded-2xl border border-white/[0.08] bg-surface/80 p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-bold tracking-tight text-slate-100">Why This Decision</h2>
            <div className="flex gap-2">
              {Object.entries(counts).map(([sev, n]) => n > 0 && (
                <span key={sev} className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ring-1 ring-inset ${SEV_COLORS[sev]}`}>
                  {n} {sev}
                </span>
              ))}
            </div>
          </div>
          <InlineFindings findings={allFindings} />
        </div>
      )}

      {/* Next Steps — from memo text */}
      {nextSteps && (
        <div className="rounded-xl border border-sky-500/20 bg-sky-500/5 p-4">
          <h4 className="mb-2 text-[10px] font-bold uppercase tracking-wider text-sky-400">What To Do Next</h4>
          <pre className="whitespace-pre-wrap font-sans text-[13px] leading-relaxed text-slate-300">{nextSteps}</pre>
        </div>
      )}

      {/* Conditions */}
      {conditions.length > 0 && (
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
          <h4 className="mb-2 text-[10px] font-bold uppercase tracking-wider text-amber-400">Conditions</h4>
          <ul className="space-y-1.5">
            {conditions.map((c, i) => (
              <li key={i} className="flex gap-2 text-sm text-slate-300">
                <span className="text-amber-400 shrink-0">•</span>{displayText(c)}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Memo Text — clean version */}
      {memoText ? (
        <Collapsible title="Full Memo" badge="text">
          <div className="rounded-lg border border-white/[0.04] bg-black/20 p-4">
            <pre className="whitespace-pre-wrap font-sans text-[13px] leading-relaxed text-slate-300">{cleanMemoText(memoText)}</pre>
          </div>
        </Collapsible>
      ) : null}

      {/* Premium Build-up */}
      {premiumSteps.length > 0 && (
        <Collapsible title="Premium Build-up" badge={`${premiumSteps.length} steps`}>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[11px]">
              <thead>
                <tr className="border-b border-white/[0.06] text-slate-500">
                  <th className="py-1.5 pr-3 font-medium">Step</th>
                  <th className="py-1.5 pr-3 font-medium">Basis</th>
                  <th className="py-1.5 pr-3 font-medium">Factor</th>
                  <th className="py-1.5 font-medium">Mod %</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.03]">
                {premiumSteps.map((row, i) => (
                  <tr key={row.step || row.name || i} className="text-slate-300">
                    <td className="py-1.5 pr-3">{displayText(row.step || row.name)}</td>
                    <td className="py-1.5 pr-3 text-slate-500">{displayText(row.basis)}</td>
                    <td className="py-1.5 pr-3 font-mono">{fmtFactor(row.factor || row.amount)}</td>
                    <td className="py-1.5 font-mono">{row.modifier_pct != null ? fmtPct(row.modifier_pct) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Collapsible>
      )}

      {/* All Key Findings */}
      {sortedFindings.length > 0 && (
        <Collapsible title="All Key Findings" badge={allFindings.length}>
          <div className="space-y-2">
            {sortedFindings.map((f, i) => (
              <FindingCard key={f.finding_id || i} finding={f} />
            ))}
          </div>
        </Collapsible>
      )}
    </div>
  );
}
