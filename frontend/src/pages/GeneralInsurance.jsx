import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, FileText, Umbrella } from 'lucide-react';
import { endpoints } from '../lib/api';
import { commercialSelectionLabel, defaultCommercialSelection } from '../lib/commercialTaxonomy';
import RunSelector from '../components/RunSelector';

export default function GeneralInsuranceHub({ presets, onRunDemo, onSubmit, jobs }) {
  const navigate = useNavigate();
  const [hub, setHub] = useState(null);
  const [error, setError] = useState('');
  const [selection, setSelection] = useState(null);

  useEffect(() => {
    let cancelled = false;
    endpoints.generalInsuranceHub()
      .then((d) => {
        if (cancelled) return;
        setHub(d);
        setSelection(defaultCommercialSelection(d.taxonomy || []));
      })
      .catch((e) => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, []);

  if (error) {
    return <p className="py-16 text-center text-red-400">{error}</p>;
  }
  if (!hub || !selection) {
    return (
      <div className="flex justify-center py-24">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
      </div>
    );
  }

  const runs = (jobs || []).slice(0, 10);
  const selectionLabel = commercialSelectionLabel(selection);

  return (
    <div className="mx-auto max-w-4xl animate-fade-in space-y-6 pb-12">
      <div>
        <nav className="flex items-center gap-1.5 text-xs text-slate-500" aria-label="Breadcrumb">
          <Link to="/insurance" className="transition hover:text-slate-300">Insurance</Link>
          <span className="text-slate-700">/</span>
          <Link to="/insurance" className="transition hover:text-slate-300">Insurance</Link>
          <span className="text-slate-700">/</span>
          <span className="font-semibold text-slate-200">General / Non-Life</span>
        </nav>
        <div className="mt-3 flex items-start gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-sky-500/15 text-sky-400">
            <Umbrella className="h-5 w-5" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight text-slate-100">{hub.title}</h1>
              <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-amber-400">
                Catalog
              </span>
            </div>
            <p className="mt-1 max-w-2xl text-sm text-slate-400">{hub.summary}</p>
          </div>
        </div>
      </div>

      <section className="glass-card overflow-hidden">
        <div className="border-b border-white/[0.06] px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-100">New submission</h2>
          <p className="mt-0.5 text-xs text-slate-500">
            Choose category → product → coverage, then upload the leaf-specific pack. Motor TP ≠ comprehensive,
            cargo ≠ hull, crop ≠ pet. Catalog-only until a filed general rate manual exists.
          </p>
        </div>
        <div className="p-5">
          <RunSelector
            presets={presets}
            vertical="insurance"
            productField="insurance_line"
            commercialTaxonomy={hub.taxonomy}
            commercialSelection={selection}
            onCommercialSelectionChange={setSelection}
            isGeneralProductPicker
            onRunDemo={onRunDemo}
            onSubmit={onSubmit}
          />
        </div>
      </section>

      <section className="glass-card overflow-hidden">
        <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-4">
          <div>
            <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-100">
              <FileText className="h-4 w-4 text-slate-500" /> Your submissions
            </h2>
            <p className="mt-0.5 text-xs text-slate-500">Open a completed run for memo, quote, and audit trail.</p>
          </div>
          <Link to="/insurance" className="text-xs text-brand hover:underline">All jobs →</Link>
        </div>
        {!runs.length ? (
          <div className="px-5 py-10 text-center">
            <p className="text-sm text-slate-400">No submissions yet.</p>
            <p className="mt-1 text-xs text-slate-500">
              Upload files above for{' '}
              <span className="text-slate-300">{selectionLabel || 'a general product'}</span>
              {' '}to start.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-white/[0.04]">
            {runs.map(({ id, job }) => (
              <button
                key={id}
                type="button"
                onClick={() => navigate(`/insurance/${id}`)}
                className="flex w-full items-center justify-between gap-3 px-5 py-3.5 text-left transition hover:bg-white/[0.02]"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-200">
                    {job?.name || job?.results?.insured_name || id}
                  </p>
                  <p className="text-xs text-slate-500">
                    {job?.results?.commercial_coverage_name
                      ? `${job?.results?.commercial_product_name || 'General'} · ${job.results.commercial_coverage_name}`
                      : (job?.results?.commercial_product_name || job?.results?.insurance_line || 'General')}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium capitalize ${
                    job?.status === 'completed'
                      ? 'bg-emerald-500/10 text-emerald-400'
                      : 'bg-white/[0.06] text-slate-400'
                  }`}>
                    {job?.status || '—'}
                  </span>
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
