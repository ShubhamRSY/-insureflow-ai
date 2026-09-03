import { CheckCircle2, XCircle } from 'lucide-react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import ScoreGauge from './ScoreGauge';
import { displayText } from '../lib/safe';
import { Hint } from './ui';

const CATEGORY_LABELS = {
  medical: 'medical / health',
  financial: 'financial',
  compliance: 'compliance & regulatory',
  fraud: 'fraud & moral hazard',
  loss: 'loss experience',
  other: 'other',
};

const SEV_DOT = {
  critical: '#f87171',
  high: '#fb923c',
  moderate: '#fbbf24',
  low: '#94a3b8',
};

// The interactive "how healthy is this submission" summary card — a score
// ring, a plain-language summary, a guideline pass/fail checklist derived
// from the same categorized findings "Why This Decision" renders further
// down the page, and a findings-by-severity donut. Everything here is
// derived from data the pipeline already computed (memo, findings, risk
// score) — no separate "guideline engine" invented for this card.
export default function SubmissionOverview({ summaryText, riskPct, riskLegend, counts, categorized, onJumpToFindings }) {
  // One row per finding CATEGORY (not per finding) — a submission with 140
  // individual findings would otherwise produce a 140-row wall of red, which
  // defeats the point of an at-a-glance checklist. Findings within a category
  // arrive pre-sorted by severity (categorized from MemoReportView's already-
  // sorted `sortedFindings`), so [0] is that category's worst finding.
  const items = Object.entries(categorized || {}).map(([cat, findings]) => {
    const label = CATEGORY_LABELS[cat] || cat;
    const list = findings || [];
    if (list.length === 0) {
      return { ok: true, label: `No ${label} issues flagged`, cat };
    }
    const topTitle = displayText(list[0]?.title, `${label} issue`);
    return {
      ok: false,
      label: list.length > 1 ? `${list.length} ${label} issues — ${topTitle}` : topTitle,
      cat,
      sev: list[0]?.severity,
    };
  });
  const metCount = items.filter((i) => i.ok).length;

  const totalFindings = Object.values(counts || {}).reduce((a, b) => a + b, 0);
  const severityData = Object.entries(counts || {})
    .filter(([, n]) => n > 0)
    .map(([sev, n]) => ({ name: sev, value: n }));

  if (riskPct == null && items.length === 0) return null;

  return (
    <div className="rounded-2xl border border-white/[0.08] bg-surface/80 p-5">
      <h2 className="text-base font-bold tracking-tight text-slate-100">Submission Overview</h2>
      <div className="mt-4 grid gap-6 lg:grid-cols-[auto_1fr_auto]">
        {riskPct != null && (
          <div className="flex justify-center lg:justify-start">
            <Hint text={riskLegend || 'Composite 0-100 score combining every finding\'s severity and confidence.'} position="bottom">
              <div className="cursor-help">
                <ScoreGauge value={riskPct} label="Risk Score" sublabel={riskLegend} direction="risk" />
              </div>
            </Hint>
          </div>
        )}

        <div className="min-w-0">
          {summaryText && <p className="text-sm leading-relaxed text-slate-300">{displayText(summaryText)}</p>}

          <div className="mt-4">
            <button
              type="button"
              onClick={() => onJumpToFindings?.()}
              className="text-xs font-semibold text-slate-300 hover:text-white hover:underline disabled:no-underline disabled:cursor-default"
              disabled={!onJumpToFindings}
            >
              {metCount} of {items.length} guidelines met
            </button>
            <div className="mt-2 grid gap-1.5 sm:grid-cols-2">
              {items.map((it, i) => (
                <Hint key={i} text={it.ok ? undefined : 'Click to jump to this finding below.'}>
                  <button
                    type="button"
                    onClick={() => !it.ok && onJumpToFindings?.()}
                    disabled={it.ok || !onJumpToFindings}
                    className={`flex w-full items-center gap-2 rounded-lg border px-2.5 py-1.5 text-left text-xs transition ${
                      it.ok
                        ? 'cursor-default border-emerald-500/20 bg-emerald-500/5 text-emerald-300'
                        : 'border-red-500/20 bg-red-500/5 text-red-300 hover:bg-red-500/10'
                    }`}
                  >
                    {it.ok ? <CheckCircle2 className="h-3.5 w-3.5 shrink-0" /> : <XCircle className="h-3.5 w-3.5 shrink-0" />}
                    <span className="truncate">{it.label}</span>
                  </button>
                </Hint>
              ))}
            </div>
          </div>
        </div>

        {totalFindings > 0 && (
          <div className="flex flex-col items-center justify-center">
            <div style={{ width: 96, height: 96 }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={severityData} dataKey="value" nameKey="name" innerRadius={28} outerRadius={44} paddingAngle={2} isAnimationActive>
                    {severityData.map((entry) => (
                      <Cell key={entry.name} fill={SEV_DOT[entry.name] || '#64748b'} stroke="none" />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(v, n) => [`${v} finding${v === 1 ? '' : 's'}`, n]}
                    contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 11 }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-1 flex flex-wrap justify-center gap-x-2 gap-y-0.5">
              {severityData.map((s) => (
                <span key={s.name} className="flex items-center gap-1 text-[10px] text-slate-500">
                  <span className="h-1.5 w-1.5 rounded-full" style={{ background: SEV_DOT[s.name] }} />
                  {s.value} {s.name}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
