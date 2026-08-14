import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { GitCompare } from 'lucide-react';
import { endpoints } from '../lib/api';
import { insuranceLineLabel } from '../lib/insuranceLines';

export default function SimilarPriors({ bundleId }) {
  const navigate = useNavigate();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!bundleId) return undefined;
    let cancelled = false;
    setLoading(true);
    endpoints.similarDecisions(bundleId)
      .then((d) => {
        if (!cancelled) setRows(d.similar || []);
      })
      .catch(() => {
        if (!cancelled) setRows([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [bundleId]);

  if (!bundleId) return null;
  if (loading) {
    return <p className="text-sm text-slate-500">Looking up similar prior files…</p>;
  }
  if (!rows.length) {
    return (
      <p className="text-sm text-slate-500">
        No similar prior files yet. Pattern memory fills as this desk decides more files of the same shape (line, state, TIV band) — not the same named insured.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-xs text-slate-500">
        Same risk shape — line / state / TIV band. Names and source files stay in the carrier PAS.
      </p>
      {rows.map((r) => (
        <button
          key={r.bundle_id}
          type="button"
          onClick={() => navigate(`/insurance/${r.bundle_id}`)}
          className="flex w-full items-center justify-between gap-3 rounded-lg bg-black/20 px-3 py-2 text-left ring-1 ring-white/[0.04] transition hover:ring-brand/30"
        >
          <div className="min-w-0">
            <p className="font-mono text-xs text-slate-300">{r.bundle_id}</p>
            <p className="mt-0.5 text-xs text-slate-500">
              {insuranceLineLabel(r.line) || r.line || '—'}
              {r.state ? ` · ${r.state}` : ''}
              {r.tiv_band ? ` · ${r.tiv_band}` : ''}
              {r.naics ? ` · NAICS ${r.naics}` : ''}
            </p>
          </div>
          <div className="shrink-0 text-right">
            <p className="text-xs font-medium capitalize text-slate-200">{r.decision || '—'}</p>
            <p className="text-[10px] tabular-nums text-slate-500">{Math.round((r.score || 0) * 100)}% match</p>
          </div>
        </button>
      ))}
    </div>
  );
}

export function SimilarPriorsHint() {
  return (
    <span className="inline-flex items-center gap-1 text-xs text-slate-500">
      <GitCompare className="h-3 w-3" /> Pattern memory
    </span>
  );
}
