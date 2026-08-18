import { useEffect, useMemo, useState } from 'react';
import { endpoints } from '../lib/api';
import { displayText } from '../lib/safe';

/**
 * Glass-box grounding: click a field → highlight its page bbox.
 * Confidence heat: low confidence shades warmer so the desk verifies before Approve.
 */
function confidenceTone(c) {
  if (c == null || Number.isNaN(Number(c))) return 'bg-slate-500/20 text-slate-300';
  const v = Number(c);
  if (v >= 0.9) return 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/30';
  if (v >= 0.75) return 'bg-sky-500/15 text-sky-300 ring-sky-500/30';
  if (v >= 0.55) return 'bg-amber-500/20 text-amber-200 ring-amber-500/40';
  return 'bg-red-500/20 text-red-200 ring-red-500/40';
}

function PageCanvas({ pageNumber, bbox, label }) {
  // Normalized bbox [x0,y0,x1,y1] drawn on a schematic page plane (no PDF bytes required).
  const box = Array.isArray(bbox) && bbox.length >= 4 ? bbox : null;
  const style = box
    ? {
        left: `${Math.max(0, Math.min(100, box[0] * 100))}%`,
        top: `${Math.max(0, Math.min(100, box[1] * 100))}%`,
        width: `${Math.max(1, Math.min(100, (box[2] - box[0]) * 100))}%`,
        height: `${Math.max(1, Math.min(100, (box[3] - box[1]) * 100))}%`,
      }
    : null;

  return (
    <div className="relative aspect-[8.5/11] w-full overflow-hidden rounded-xl border border-white/10 bg-[#0b1220]">
      <div className="absolute inset-0 opacity-40" style={{
        backgroundImage: 'linear-gradient(to bottom, transparent 0, transparent calc(100% - 1px), rgba(148,163,184,0.15) calc(100% - 1px)), linear-gradient(to right, transparent 0, transparent calc(100% - 1px), rgba(148,163,184,0.08) calc(100% - 1px))',
        backgroundSize: '100% 8%, 12% 100%',
      }} />
      <p className="absolute left-3 top-3 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
        Page {pageNumber ?? '—'}
      </p>
      {style ? (
        <div
          className="absolute rounded-sm border-2 border-amber-300/90 bg-amber-300/20 shadow-[0_0_0_1px_rgba(251,191,36,0.35)]"
          style={style}
          title={label}
        />
      ) : (
        <p className="absolute inset-x-4 bottom-4 text-center text-xs text-slate-500">
          No bounding box on this field — citation is page-only or missing.
        </p>
      )}
    </div>
  );
}

export default function PdfGroundingViewer({ bundleId }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    let cancelled = false;
    if (!bundleId) return undefined;
    endpoints.grounding(bundleId)
      .then((payload) => {
        if (!cancelled) {
          setData(payload);
          setError(null);
          const first = (payload.fields || []).find((f) => f.grounded) || (payload.fields || [])[0];
          setSelected(first || null);
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e.message || 'Could not load grounding map');
      });
    return () => { cancelled = true; };
  }, [bundleId]);

  const fields = useMemo(() => data?.fields || [], [data]);
  const ungroundedCount = data?.ungrounded?.length || 0;

  if (!bundleId) return null;
  if (error) {
    return (
      <div className="rounded-xl border border-white/10 bg-surface/40 p-4 text-sm text-slate-400">
        Grounding map unavailable: {error}
      </div>
    );
  }
  if (!data) {
    return (
      <div className="rounded-xl border border-white/10 bg-surface/40 p-4 text-sm text-slate-500">
        Loading source citations…
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-500">Glass box</p>
          <h3 className="text-lg font-semibold text-slate-100">Every figure is a hypothesis until you see the page</h3>
          <p className="mt-1 text-xs text-slate-400">
            Click a value to highlight its source box. Warm cells are low confidence — verify before Approve.
            {ungroundedCount > 0 ? ` ${ungroundedCount} ungrounded field(s) must not be treated as fact.` : ''}
            {data?.zero_hallucination && data.zero_hallucination.hallucination_count != null
              ? ` Hallucination count: ${data.zero_hallucination.hallucination_count} (max ${data.zero_hallucination.max_allowed ?? 0})${data.zero_hallucination.passed === false ? ' — REFER' : ''}.`
              : ''}
          </p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="max-h-[28rem] space-y-2 overflow-y-auto rounded-xl border border-white/10 bg-surface/50 p-3">
          {fields.length === 0 && (
            <p className="text-sm text-slate-500">No extracted fields with spatial data on this file yet.</p>
          )}
          {fields.map((f) => {
            const active = selected && selected.field_name === f.field_name && selected.submission_id === f.submission_id;
            return (
              <button
                key={`${f.submission_id}:${f.field_name}:${f.value}`}
                type="button"
                onClick={() => setSelected(f)}
                className={`flex w-full items-start gap-2 rounded-lg border px-3 py-2 text-left transition ${
                  active ? 'border-amber-400/50 bg-amber-400/10' : 'border-white/5 bg-black/20 hover:border-white/15'
                }`}
              >
                <span className={`mt-0.5 shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold ring-1 ring-inset ${confidenceTone(f.confidence)}`}>
                  {f.confidence != null ? `${Math.round(Number(f.confidence) * 100)}%` : '—'}
                </span>
                <span className="min-w-0">
                  <span className="block truncate text-sm font-medium text-slate-200">{displayText(f.field_name)}</span>
                  <span className="block truncate text-xs text-slate-400">{displayText(f.value)}</span>
                  <span className="mt-0.5 block text-[10px] text-slate-500">
                    {f.grounded
                      ? (f.source_ref || `page ${f.page_number}`)
                      : 'UNGROUNDED — hypothesis only'}
                  </span>
                </span>
              </button>
            );
          })}
        </div>

        <PageCanvas
          pageNumber={selected?.page_number}
          bbox={selected?.bbox}
          label={selected ? `${selected.field_name}=${selected.value}` : ''}
        />
      </div>
    </div>
  );
}
