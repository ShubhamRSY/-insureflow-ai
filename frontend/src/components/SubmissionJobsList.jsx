import { displayText } from '../lib/safe';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, FileText, Trash2 } from 'lucide-react';
import { ScoreBadge } from './ui';

export default function SubmissionJobsList({
  jobs = [],
  emptyHint,
  fallbackLine = 'Insurance',
  onDeleteJob,
  onDeleteAll,
}) {
  const navigate = useNavigate();
  const runs = (jobs || []).slice(0, 10);

  const removeOne = async (event, id) => {
    event.preventDefault();
    event.stopPropagation();
    if (!window.confirm('Delete this submission? This cannot be undone.')) return;
    try {
      await onDeleteJob?.(id);
    } catch (e) {
      window.alert(e.message || 'Could not delete this submission');
    }
  };

  const removeAll = async () => {
    if (!runs.length) return;
    if (!window.confirm(`Delete all ${runs.length} listed submission${runs.length === 1 ? '' : 's'}? This cannot be undone.`)) return;
    try {
      await onDeleteAll?.(runs.map((r) => r.id));
    } catch (e) {
      window.alert(e.message || 'Could not delete submissions');
    }
  };

  return (
    <section className="glass-card overflow-hidden">
      <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-4">
        <div>
          <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-100">
            <FileText className="h-4 w-4 text-slate-500" /> Your submissions
          </h2>
          <p className="mt-0.5 text-xs text-slate-500">Open a completed run for memo, quote, and audit trail.</p>
        </div>
        <div className="flex items-center gap-3">
          {runs.length > 0 && onDeleteAll && (
            <button
              type="button"
              onClick={removeAll}
              className="inline-flex items-center gap-1 text-xs text-red-400 hover:text-red-300"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Delete all
            </button>
          )}
          <Link to="/insurance" className="text-xs text-brand hover:underline">All jobs →</Link>
        </div>
      </div>
      {!runs.length ? (
        <div className="px-5 py-10 text-center">
          <p className="text-sm text-slate-400">No submissions yet.</p>
          {emptyHint && <p className="mt-1 text-xs text-slate-500">{emptyHint}</p>}
        </div>
      ) : (
        <div className="divide-y divide-white/[0.04]">
          {runs.map(({ id, job }) => {
            const memoObj = job?.results?.memo && typeof job.results.memo === 'object' ? job.results.memo : {};
            const riskPct = memoObj.overall_risk_score != null ? Math.round(Number(memoObj.overall_risk_score) * 100) : null;
            return (
            <div
              key={id}
              className="flex w-full items-center justify-between gap-3 px-5 py-3.5 transition hover:bg-white/[0.02]"
            >
              <button
                type="button"
                onClick={() => navigate(`/insurance/${id}`)}
                className="flex min-w-0 flex-1 items-center justify-between gap-3 text-left"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-200">
                    {displayText(job?.name || job?.results?.insured_name, id)}
                  </p>
                  <p className="text-xs text-slate-500">
                    {job?.results?.commercial_coverage_name
                      ? `${displayText(job?.results?.commercial_product_name, fallbackLine)} · ${displayText(job.results.commercial_coverage_name)}`
                      : displayText(job?.results?.commercial_product_name || job?.results?.insurance_line, fallbackLine)}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {riskPct != null && <ScoreBadge value={riskPct} direction="risk" />}
                  <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium capitalize ${
                    job?.status === 'completed'
                      ? 'bg-emerald-500/10 text-emerald-400'
                      : 'bg-white/[0.06] text-slate-400'
                  }`}>
                    {job?.status || '—'}
                  </span>
                </div>
              </button>
              <div className="flex shrink-0 items-center gap-1">
                {onDeleteJob && (
                  <button
                    type="button"
                    onClick={(e) => removeOne(e, id)}
                    className="rounded-lg p-1.5 text-red-400 hover:bg-red-500/10"
                    title="Delete submission"
                    aria-label={`Delete ${job?.name || id}`}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => navigate(`/insurance/${id}`)}
                  className="rounded-lg p-1.5 text-slate-500 hover:bg-white/5 hover:text-slate-300"
                  aria-label="Open submission"
                >
                  <ArrowRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
