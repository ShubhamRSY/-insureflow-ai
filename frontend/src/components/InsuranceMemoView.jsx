import { Badge } from './ui';
import { fmtCurrency, extractInsurance } from '../lib/api';

const SEV = {
  critical: 'bg-red-500/20 text-red-300 ring-red-500/30',
  high: 'bg-orange-500/20 text-orange-300 ring-orange-500/30',
  moderate: 'bg-amber-500/20 text-amber-300 ring-amber-500/30',
  low: 'bg-slate-500/20 text-slate-300 ring-slate-500/30',
};

function severityCounts(findings) {
  const counts = { critical: 0, high: 0, moderate: 0, low: 0 };
  (findings || []).forEach((f) => {
    const s = (f.severity || 'moderate').toLowerCase();
    if (counts[s] != null) counts[s] += 1;
  });
  return counts;
}

const SEV_ORDER = { critical: 0, high: 1, moderate: 2, low: 3 };

function sortFindings(findings) {
  return [...(findings || [])].sort((a, b) => {
    const sa = SEV_ORDER[(a.severity || 'moderate').toLowerCase()] ?? 2;
    const sb = SEV_ORDER[(b.severity || 'moderate').toLowerCase()] ?? 2;
    return sa - sb;
  });
}

function FindingRow({ finding }) {
  const sev = (finding.severity || 'moderate').toLowerCase();
  return (
    <div className="rounded-xl border border-white/[0.06] bg-surface/60 p-3">
      <div className="flex items-start gap-2">
        <span className={`mt-0.5 shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ring-1 ring-inset ${SEV[sev] || SEV.moderate}`}>
          {sev}
        </span>
        <div className="min-w-0">
          <p className="text-sm font-medium text-slate-200">{finding.title}</p>
          {finding.description && (
            <p className="mt-1 text-xs leading-relaxed text-slate-400">{finding.description}</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default function InsuranceMemoView({ job }) {
  const s = extractInsurance(job);
  const memo = s.memoData || {};
  const allFindings = memo.key_findings || [];
  const counts = severityCounts(allFindings);
  const decision = (s.decision || 'refer').toLowerCase();
  const decisionStyle = {
    accept: 'from-emerald-600/30 to-emerald-900/10 border-emerald-500/40 text-emerald-300',
    refer: 'from-sky-600/30 to-sky-900/10 border-sky-500/40 text-sky-300',
    decline: 'from-red-600/30 to-red-900/10 border-red-500/40 text-red-300',
  }[decision] || 'from-slate-600/30 to-slate-900/10 border-white/10 text-slate-300';

  const riskPct = memo.overall_risk_score != null
    ? Math.round(Number(memo.overall_risk_score) * 100)
    : null;

  const agentSections = [
    ['risk_analyst_findings', 'Risk Analyst'],
    ['loss_run_findings', 'Loss Run'],
    ['compliance_findings', 'Compliance'],
    ['fraud_findings', 'Fraud Detection'],
  ].filter(([key]) => (memo[key] || []).length > 0);

  return (
    <div className="space-y-6">
      {/* Decision hero */}
      <div className={`rounded-2xl border bg-gradient-to-br p-6 ${decisionStyle}`}>
        <p className="text-xs font-semibold uppercase tracking-widest opacity-80">Underwriting Decision</p>
        <p className="mt-1 text-4xl font-bold tracking-tight uppercase">{decision}</p>
        <p className="mt-2 text-lg font-medium text-white">{s.insuredName}</p>
        <div className="mt-4 flex flex-wrap gap-4">
          <div>
            <p className="text-xs uppercase opacity-70">Indicated Premium</p>
            <p className="text-2xl font-bold text-white">{fmtCurrency(s.premium)}</p>
          </div>
          {riskPct != null && (
            <div>
              <p className="text-xs uppercase opacity-70">Risk Score</p>
              <p className="text-2xl font-bold">{riskPct}<span className="text-base font-normal opacity-70">/100</span></p>
            </div>
          )}
          {memo.overall_risk_severity && (
            <div>
              <p className="text-xs uppercase opacity-70">Severity</p>
              <p className="text-lg font-semibold capitalize">{memo.overall_risk_severity}</p>
            </div>
          )}
        </div>
      </div>

      {/* Findings breakdown */}
      {allFindings.length > 0 && (
        <div>
          <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Findings Overview</h4>
          <div className="grid grid-cols-4 gap-2">
            {Object.entries(counts).map(([sev, n]) => (
              <div key={sev} className={`rounded-xl p-3 text-center ring-1 ring-inset ${SEV[sev]}`}>
                <p className="text-2xl font-bold">{n}</p>
                <p className="text-[10px] uppercase tracking-wide">{sev}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Narrative */}
      {s.memo && (
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">Executive Summary</h4>
          <p className="rounded-xl bg-surface/80 p-4 text-sm leading-relaxed text-slate-300">{s.memo}</p>
        </div>
      )}

      {/* Key findings (sorted high→low) */}
      {allFindings.length > 0 && (
        <div>
          <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Key Findings</h4>
          <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
            {sortFindings(allFindings).slice(0, 8).map((f, i) => (
              <FindingRow key={f.finding_id || i} finding={f} />
            ))}
          </div>
        </div>
      )}

      {/* Agent sections (sorted high→low) */}
      {agentSections.map(([key, label]) => (
        <div key={key}>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</h4>
          <div className="space-y-2">
            {sortFindings(memo[key]).slice(0, 3).map((f, i) => (
              <FindingRow key={i} finding={f} />
            ))}
          </div>
        </div>
      ))}

      {/* Conditions */}
      {(memo.conditions || []).length > 0 && (
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">Conditions</h4>
          <ul className="space-y-1.5">
            {memo.conditions.map((c, i) => (
              <li key={i} className="flex gap-2 text-sm text-slate-300">
                <span className="text-brand-light">•</span>{c}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Quote & workflow */}
      <div className="grid grid-cols-2 gap-3 text-sm">
        {s.quote?.policy_admin_reference && (
          <div className="rounded-xl bg-surface-overlay p-3 ring-1 ring-white/[0.04]">
            <p className="text-[10px] uppercase text-slate-500">Quote Ref</p>
            <p className="font-mono text-xs">{s.quote.policy_admin_reference}</p>
          </div>
        )}
        {s.workflowState && (
          <div className="rounded-xl bg-surface-overlay p-3 ring-1 ring-white/[0.04]">
            <p className="text-[10px] uppercase text-slate-500">Workflow</p>
            <Badge status={s.workflowState} />
          </div>
        )}
      </div>

      <p className="font-mono text-[10px] text-slate-600">Bundle {s.bundleId}</p>
    </div>
  );
}
