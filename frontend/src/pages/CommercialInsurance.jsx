import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Shield } from 'lucide-react';
import { endpoints } from '../lib/api';
import { commercialSelectionLabel, defaultCommercialSelection } from '../lib/commercialTaxonomy';
import RunSelector from '../components/RunSelector';
import SubmissionJobsList from '../components/SubmissionJobsList';

export default function CommercialInsuranceHub({ presets, onRunDemo, onSubmit, jobs, onDeleteJob, onDeleteAllJobs }) {
  const [hub, setHub] = useState(null);
  const [error, setError] = useState('');
  const [commercialSelection, setCommercialSelection] = useState(null);

  useEffect(() => {
    let cancelled = false;
    endpoints.commercialInsuranceHub()
      .then((d) => {
        if (cancelled) return;
        setHub(d);
        setCommercialSelection(defaultCommercialSelection(d.taxonomy || []));
      })
      .catch((e) => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, []);

  if (error) {
    return <p className="py-16 text-center text-red-400">{error}</p>;
  }
  if (!hub || !commercialSelection) {
    return (
      <div className="flex justify-center py-24">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
      </div>
    );
  }

  const selectionLabel = commercialSelectionLabel(commercialSelection);

  return (
    <div className="mx-auto w-full max-w-[1600px] animate-fade-in space-y-6 pb-12">
      <div>
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand/15 text-brand">
            <Shield className="h-5 w-5" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight text-slate-100">{hub.title}</h1>
              <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-emerald-400">
                Live
              </span>
            </div>
            <p className="mt-1 text-sm text-slate-400">
              Intake a submission and run the UW pipeline. Need document packs or line guides?{' '}
              <Link to="/reference/commercial" className="text-brand hover:underline">
                Open reference notebook
              </Link>
            </p>
          </div>
        </div>
      </div>

      <section className="glass-card">
        <div className="border-b border-white/[0.06] px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-100">New submission</h2>
          <p className="mt-0.5 text-sm text-slate-400">
            Choose category → product → coverage, then upload the broker package. Triage, rating, and memo follow automatically.
          </p>
        </div>
        <div className="p-5">
          <RunSelector
            presets={presets}
            vertical="insurance"
            productField="insurance_line"
            commercialTaxonomy={hub.taxonomy}
            commercialSelection={commercialSelection}
            onCommercialSelectionChange={setCommercialSelection}
            onRunDemo={onRunDemo}
            onSubmit={onSubmit}
          />
        </div>
      </section>

      <SubmissionJobsList
        jobs={jobs}
        fallbackLine="Commercial"
        emptyHint={
          <>
            Upload files above for{' '}
            <span className="text-slate-300">{selectionLabel || 'a commercial line'}</span>
            {' '}to start.
          </>
        }
        onDeleteJob={onDeleteJob}
        onDeleteAll={onDeleteAllJobs}
      />
    </div>
  );
}
