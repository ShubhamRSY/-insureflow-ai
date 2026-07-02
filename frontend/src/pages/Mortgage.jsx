import { useState } from 'react';
import { DemoCard, Badge, EmptyState } from '../components/ui';
import { extractMortgage, endpoints, fmtCurrency } from '../lib/api';
import { Home, Package, FileText } from 'lucide-react';

export default function MortgagePage({ presets, jobs, onRunDemo, onOpenJob, onSubmit }) {
  const [loading, setLoading] = useState(false);
  const [mortgageProducts, setMortgageProducts] = useState(null);
  const [mortgageAudit, setMortgageAudit] = useState(null);

  const loadMortgageProducts = async () => {
    try { setMortgageProducts(await endpoints.mortgageProducts()); } catch (e) { alert(e.message); }
  };

  const loadMortgageAudit = async (bundleId) => {
    try { setMortgageAudit(await endpoints.mortgageAudit(bundleId)); } catch (e) { alert('No audit data: ' + e.message); }
  };

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
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-mortgage/15">
            <Home className="h-6 w-6 text-mortgage" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Mortgage Underwriting</h1>
            <p className="mt-1 max-w-xl text-slate-400">Residential & commercial lending — income, credit, property docs → approve/deny + rate quote</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={loadMortgageProducts} className="btn-secondary btn-sm text-xs"><Package className="h-3 w-3" /> Products</button>
        </div>
      </div>

      {mortgageProducts && (
        <div className="glass-card p-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400"><Package className="mr-2 inline h-4 w-4" /> Mortgage Products</h3>
            <button onClick={() => setMortgageProducts(null)} className="text-xs text-slate-500 hover:text-slate-300">Close</button>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {(mortgageProducts.products || mortgageProducts.loan_products || []).map((p, i) => (
              <div key={i} className="rounded-lg bg-surface-overlay p-3 ring-1 ring-white/[0.04]">
                <p className="text-sm font-medium text-slate-200">{p.name || p.product_name || p.product_code}</p>
                <p className="text-xs text-slate-500">{p.description || p.product_type || ''}</p>
                {p.rate && <p className="mt-1 text-xs text-slate-400">Rate: {p.rate}%</p>}
                {p.max_loan_amount && <p className="text-xs text-slate-400">Max: {fmtCurrency(p.max_loan_amount)}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {mortgageAudit && (
        <div className="glass-card p-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400"><FileText className="mr-2 inline h-4 w-4" /> Mortgage Audit Trail</h3>
            <button onClick={() => setMortgageAudit(null)} className="text-xs text-slate-500 hover:text-slate-300">Close</button>
          </div>
          <pre className="max-h-80 overflow-y-auto rounded-lg bg-black/20 p-3 text-xs text-slate-400">{JSON.stringify(mortgageAudit, null, 2)}</pre>
        </div>
      )}

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
                  <th className="px-6 py-3">Actions</th>
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
                      <td className="px-6 py-3.5">
                        <div className="flex gap-1" onClick={e => e.stopPropagation()}>
                          {s.bundleId && (
                            <button onClick={() => loadMortgageAudit(s.bundleId)} className="rounded-lg bg-black/30 px-2 py-1 text-xs text-slate-400 hover:text-slate-200" title="Mortgage Audit Trail">Audit</button>
                          )}
                        </div>
                      </td>
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
