import { useState } from 'react';
import { DemoCard, Badge, EmptyState } from '../components/ui';
import { extractMortgage } from '../lib/api';
import { Home } from 'lucide-react';

export default function MortgagePage({ presets, jobs, onRunDemo, onOpenJob, onSubmit }) {
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    const fd = new FormData(e.target);
    try {
      await onSubmit({
        directory: fd.get('directory'),
        product_line: fd.get('product_line'),
        use_llm: fd.get('use_llm') === 'on',
        per_borrower: fd.get('per_borrower') === 'on',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-8 animate-fade-in">
      <div className="flex items-start gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-mortgage/15">
          <Home className="h-6 w-6 text-mortgage" />
        </div>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Mortgage Underwriting</h1>
          <p className="mt-1 max-w-xl text-slate-400">Residential & commercial lending — income, credit, property docs → approve/deny + rate quote</p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="glass-card p-6">
          <h3 className="mb-4 font-semibold">Demo Loan Packages</h3>
          <div className="space-y-3">
            {(presets?.mortgage || []).map((d) => (
              <DemoCard key={d.id} name={d.name} description={d.description} tag={d.product_line} tagColor="mortgage" onClick={() => onRunDemo('mortgage', d.id)} />
            ))}
          </div>
        </div>

        <div className="glass-card p-6">
          <h3 className="mb-4 font-semibold">Custom Submission</h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-400">Document Directory *</label>
              <input name="directory" required className="input-field font-mono text-xs" placeholder="simulated_documents/home_mortgage/johnson_marcus_imani" />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-400">Product Line</label>
              <select name="product_line" className="input-field">
                <option value="residential_mortgage">Residential Mortgage</option>
                <option value="commercial_mortgage">Commercial Mortgage</option>
              </select>
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-400">
              <input type="checkbox" name="use_llm" defaultChecked className="rounded" /> Use LLM
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-400">
              <input type="checkbox" name="per_borrower" className="rounded" /> Per borrower
            </label>
            <button type="submit" disabled={loading} className="btn-primary">{loading ? 'Running…' : 'Run Pipeline'}</button>
          </form>
        </div>
      </div>

      <div className="glass-card overflow-hidden">
        <div className="border-b border-white/[0.06] px-6 py-4">
          <h3 className="font-semibold">Job Queue</h3>
        </div>
        {!jobs?.length ? (
          <EmptyState icon={Home} title="No mortgage jobs" description="Run Johnson Family demo to get started" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06] bg-surface-overlay text-left text-xs uppercase tracking-wider text-slate-500">
                  <th className="px-6 py-3">Job ID</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Decision</th>
                  <th className="px-6 py-3">Rate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {[...jobs].reverse().map(({ id, job }) => {
                  const s = extractMortgage(job);
                  return (
                    <tr key={id} onClick={() => onOpenJob('mortgage', id)} className="cursor-pointer transition hover:bg-white/[0.02]">
                      <td className="px-6 py-3.5 font-mono text-xs text-slate-400">{id}</td>
                      <td className="px-6 py-3.5"><Badge status={job?.status} pulse={job?.status === 'processing'} /></td>
                      <td className="px-6 py-3.5">{s.decision ? <Badge status={s.decision} /> : '—'}</td>
                      <td className="px-6 py-3.5 font-medium">{s.rate != null ? `${s.rate}%` : '—'}</td>
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
