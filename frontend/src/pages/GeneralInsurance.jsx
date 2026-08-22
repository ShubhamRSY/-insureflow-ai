import { useEffect, useState } from 'react';
import { Umbrella } from 'lucide-react';
import { endpoints } from '../lib/api';
import { commercialSelectionLabel, defaultCommercialSelection } from '../lib/commercialTaxonomy';
import RunSelector from '../components/RunSelector';
import SubmissionJobsList from '../components/SubmissionJobsList';

export default function GeneralInsuranceHub({ presets, onRunDemo, onSubmit, jobs, onDeleteJob, onDeleteAllJobs }) {
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

  const selectionLabel = commercialSelectionLabel(selection);

  return (
    <div className="mx-auto w-full max-w-[1600px] animate-fade-in space-y-6 pb-12">
      <div>
        <div className="flex items-start gap-3">
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

      <section className="glass-card">
        <div className="border-b border-white/[0.06] px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-100">New submission</h2>
          <p className="mt-0.5 text-sm text-slate-400">
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

      <SubmissionJobsList
        jobs={jobs}
        fallbackLine="General"
        emptyHint={
          <>
            Upload files above for{' '}
            <span className="text-slate-300">{selectionLabel || 'a general product'}</span>
            {' '}to start.
          </>
        }
        onDeleteJob={onDeleteJob}
        onDeleteAll={onDeleteAllJobs}
      />
    </div>
  );
}
