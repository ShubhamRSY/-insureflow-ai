import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, FileText, Shield } from 'lucide-react';
import { endpoints } from '../lib/api';
import { insuranceLineLabel } from '../lib/insuranceLines';
import RunSelector from '../components/RunSelector';

export default function CommercialInsuranceHub({ presets, onRunDemo, onSubmit, jobs }) {
  const navigate = useNavigate();
  const [hub, setHub] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    endpoints.commercialInsuranceHub()
      .then((d) => { if (!cancelled) setHub(d); })
      .catch((e) => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, []);

  if (error) {
    return <p className="py-16 text-center text-red-400">{error}</p>;
  }
  if (!hub) {
    return (
      <div className="flex justify-center py-24">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
      </div>
    );
  }

  const runs = (jobs || []).slice(0, 8);

  return (
    <div className="mx-auto max-w-6xl space-y-8 animate-fade-in pb-12">
      <div>
        <nav className="flex items-center gap-1.5 text-xs text-slate-500" aria-label="Breadcrumb">
          <Link to="/insurance" className="text-slate-600 transition hover:text-slate-300">Underwriting</Link>
          <span className="text-slate-700">/</span>
          <Link to="/insurance" className="text-slate-600 transition hover:text-slate-300">Insurance</Link>
          <span className="text-slate-700">/</span>
          <span className="font-semibold text-slate-200">Business & Commercial</span>
        </nav>
        <div className="mt-3 flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand/15 text-brand">
            <Shield className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-brand/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-brand-light">
                Block 1
              </span>
              <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-emerald-400">
                Live
              </span>
            </div>
            <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-100">{hub.title}</h1>
            <p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-400">{hub.summary}</p>
          </div>
        </div>
      </div>

      {/* Run / pull / connect */}
      <RunSelector
        presets={presets}
        vertical="insurance"
        productField="insurance_line"
        productOptions={(hub.lines || []).map((l) => ({ id: l.insurance_line, label: l.name }))}
        productDefault={(hub.lines || [])[0]?.insurance_line || ''}
        onRunDemo={onRunDemo}
        onSubmit={onSubmit}
      />

      {/* Jump to a line */}
      {(hub.lines || []).length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Jump to a line</span>
          {(hub.lines || []).map((line) => (
            <button
              key={line.id}
              type="button"
              onClick={() => navigate(`/insurance/commercial/${line.slug}`)}
              className="rounded-lg border border-white/[0.08] bg-surface-overlay px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:border-brand/35 hover:text-slate-100"
            >
              {line.name}
            </button>
          ))}
        </div>
      )}

      {/* Runs & reports */}
      <section className="glass-card overflow-hidden">
        <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-4">
          <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
            <FileText className="h-4 w-4" /> Runs & reports
          </h2>
          <Link to="/insurance" className="text-xs text-brand hover:underline">All insurance jobs →</Link>
        </div>
        {!runs.length ? (
          <p className="px-5 py-8 text-sm text-slate-500">
            No submissions yet. Pick a line above, add files or a sample, and run — the memo, quote, and report land here.
          </p>
        ) : (
          <div className="divide-y divide-white/[0.04]">
            {runs.map(({ id, job }) => (
              <button
                key={id}
                type="button"
                onClick={() => navigate(`/insurance/${id}`)}
                className="flex w-full items-center justify-between gap-3 px-5 py-3 text-left hover:bg-white/[0.02]"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-200">
                    {job?.name || job?.results?.insured_name || id}
                  </p>
                  <p className="text-xs text-slate-500">
                    {insuranceLineLabel(job?.results?.insurance_line || job?.results?.product_line || '') || 'Commercial'}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs capitalize text-slate-400">{job?.status || '—'}</span>
                  <ArrowRight className="h-3.5 w-3.5 text-slate-600" />
                </div>
              </button>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
