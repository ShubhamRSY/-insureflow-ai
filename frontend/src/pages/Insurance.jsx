import { useState } from 'react';
import { Badge, DecisionBadge, EmptyState } from '../components/ui';
import { fmtCurrency, extractInsurance } from '../lib/api';
import InsuranceSourceHub from '../components/InsuranceSourceHub';
import { Shield } from 'lucide-react';

export default function InsurancePage({ presets, jobs, onRunDemo, onOpenJob, onSubmit }) {
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (payload) => {
    setLoading(true);
    try {
      await onSubmit(payload);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-10 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Commercial Insurance</h1>
        <p className="mt-2 text-sm text-slate-400">
          Connect a document source, pull the broker package, and run underwriting.
        </p>
      </div>

      <InsuranceSourceHub onSubmit={handleSubmit} loading={loading} />

      {(presets?.insurance || []).length > 0 && (
        <div className="space-y-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">One-click samples</p>
          <div className="flex flex-col gap-2">
            {(presets?.insurance || []).map((d) => (
              <button
                key={d.id}
                type="button"
                onClick={() => onRunDemo('insurance', d.id)}
                className="flex items-center justify-between rounded-xl border border-white/[0.06] bg-surface-overlay/30 px-4 py-3 text-left transition hover:border-brand/30 hover:bg-white/[0.02]"
              >
                <span className="text-sm font-medium text-slate-200">{d.name}</span>
                <span className="text-xs text-slate-500">Run sample →</span>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="glass-card overflow-hidden">
        <div className="border-b border-white/[0.06] px-5 py-3">
          <h3 className="text-sm font-semibold">Recent jobs</h3>
        </div>
        {!jobs?.length ? (
          <EmptyState icon={Shield} title="No insurance jobs" description="Upload a broker package or run the Pacific Coast demo" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06] bg-surface-overlay text-left text-xs uppercase tracking-wider text-slate-500">
                  <th className="px-6 py-3">Job ID</th>
                  <th className="px-6 py-3">Insured</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Decision</th>
                  <th className="px-6 py-3">Premium</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {[...jobs].reverse().map(({ id, job }) => {
                  const s = extractInsurance(job);
                  return (
                    <tr key={id} onClick={() => onOpenJob('insurance', id)} className="cursor-pointer transition hover:bg-white/[0.02]">
                      <td className="px-6 py-3.5 font-mono text-xs text-slate-400">{id}</td>
                      <td className="px-6 py-3.5 text-slate-300">{s.insuredName || '—'}</td>
                      <td className="px-6 py-3.5"><Badge status={job?.status} pulse={job?.status === 'processing'} /></td>
                      <td className="px-6 py-3.5"><DecisionBadge decision={s.decision} jobStatus={job?.status} /></td>
                      <td className="px-6 py-3.5 font-medium">{fmtCurrency(s.premium)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
