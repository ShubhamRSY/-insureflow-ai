import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { HeartPulse } from 'lucide-react';
import { endpoints } from '../lib/api';
import { commercialSelectionLabel, defaultCommercialSelection } from '../lib/commercialTaxonomy';
import RunSelector from '../components/RunSelector';
import SubmissionJobsList from '../components/SubmissionJobsList';

export default function LifeInsuranceHub({ presets, onRunDemo, onSubmit, jobs, onDeleteJob, onDeleteAllJobs }) {
  const [hub, setHub] = useState(null);
  const [error, setError] = useState('');
  const [selection, setSelection] = useState(null);

  useEffect(() => {
    let cancelled = false;
    endpoints.lifeInsuranceHub()
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

  const selectionLabel = commercialSelectionLabel(selection);

  return (
    <div className="mx-auto w-full max-w-[1600px] animate-fade-in space-y-6 pb-12">
      <div>
          <nav className="flex items-center gap-1.5 text-xs text-slate-500" aria-label="Breadcrumb">
            <Link to="/" className="transition hover:text-slate-300">Dashboard</Link>
            <span className="text-slate-700">/</span>
            <Link to="/insurance" className="transition hover:text-slate-300">Insurance</Link>
            <span className="text-slate-700">/</span>
            <span className="font-semibold text-slate-200">Life Insurance</span>
          </nav>
        <div className="mt-3 flex items-start gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-rose-500/15 text-rose-400">
            <HeartPulse className="h-5 w-5" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight text-slate-100">{hub.title}</h1>
              <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-emerald-400">
                Live
              </span>
            </div>
            <p className="mt-1 max-w-2xl text-sm text-slate-400">{hub.summary}</p>
          </div>
        </div>
      </div>

      <section className="glass-card">
        <div className="border-b border-white/[0.06] px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-100">Start a New Review</h2>
          <p className="mt-0.5 text-sm text-slate-400">
            Upload your life insurance package — we'll extract the key details, run medical and financial checks, and produce an underwriting recommendation.
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
              isLifeProductPicker
              guidedFlow
              onRunDemo={onRunDemo}
              onSubmit={onSubmit}
            />
        </div>
      </section>

      <SubmissionJobsList
        jobs={jobs}
        fallbackLine="Life"
        emptyHint={
          <>
            Upload files above for{' '}
            <span className="text-slate-300">{selectionLabel || 'a life product'}</span>
            {' '}to start.
          </>
        }
        onDeleteJob={onDeleteJob}
        onDeleteAll={onDeleteAllJobs}
      />
    </div>
  );
}
