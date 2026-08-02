import { useState } from 'react';
import { Badge, EmptyState } from '../components/ui';
import { extractMortgage, endpoints, fmtCurrency } from '../lib/api';
import MortgageSourceHub from '../components/MortgageSourceHub';
import StageStrip, { stagesFromProgress } from '../components/StageStrip';
import { Home, Package, FileText, Building2 } from 'lucide-react';

export default function MortgagePage({ presets, jobs, onRunDemo, onOpenJob, onRunConnect, onSubmit }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [mortgageProducts, setMortgageProducts] = useState(null);
  const [mortgageAudit, setMortgageAudit] = useState(null);

  const loadMortgageProducts = async () => {
    try { setMortgageProducts(await endpoints.mortgageProducts()); } catch (e) { alert(e.message); }
  };

  const loadMortgageAudit = async (bundleId) => {
    try { setMortgageAudit(await endpoints.mortgageAudit(bundleId)); } catch (e) { alert('No audit data: ' + e.message); }
  };

  const handleSubmit = async (body) => {
    setLoading(true);
    setError('');
    try {
      await onSubmit(body);
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-7xl space-y-8 animate-fade-in">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Mortgage Underwriting</h1>
          <p className="mt-2 text-sm text-slate-400 max-w-xl">
            Income, credit, and property → decision + rate.
          </p>
        </div>
        <button type="button" onClick={loadMortgageProducts} className="btn-secondary btn-sm text-xs">
          <Package className="h-3 w-3" /> Products
        </button>
      </div>

      {error && <div className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}

      {mortgageProducts && (
        <div className="glass-card p-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
              <Package className="mr-2 inline h-4 w-4" /> Mortgage Products
            </h3>
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
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
              <FileText className="mr-2 inline h-4 w-4" /> Mortgage Audit Trail
            </h3>
            <button onClick={() => setMortgageAudit(null)} className="text-xs text-slate-500 hover:text-slate-300">Close</button>
          </div>
          <pre className="max-h-80 overflow-y-auto rounded-lg bg-black/20 p-3 text-xs text-slate-400">{JSON.stringify(mortgageAudit, null, 2)}</pre>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-12">
        {/* Left rail — loan package input */}
        <div className="lg:col-span-4">
          <div className="lg:sticky lg:top-20">
            <MortgageSourceHub
              presets={presets}
              onSubmit={handleSubmit}
              onRunDemo={onRunDemo}
              onRunConnect={onRunConnect}
              loading={loading}
            />
          </div>
        </div>

        {/* Right column — recent runs + samples */}
        <div className="lg:col-span-8 space-y-6">
          {/* Quick samples */}
          {(presets?.mortgage || []).length > 0 && (
            <div className="glass-card p-5">
              <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Quick samples</p>
              <div className="flex flex-col gap-2">
                {(presets?.mortgage || []).map((d) => {
                  const isCommercial = String(d.product_line || '').includes('commercial');
                  return (
                    <button key={d.id} type="button" onClick={() => onRunDemo('mortgage', d.id)}
                      className="flex items-center justify-between gap-3 rounded-xl border border-white/[0.06] bg-surface-overlay/30 px-4 py-3 text-left transition hover:border-mortgage/35">
                      <span className="min-w-0 flex items-center gap-3">
                        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-mortgage/15">
                          {isCommercial ? <Building2 className="h-4 w-4 text-mortgage" /> : <Home className="h-4 w-4 text-mortgage" />}
                        </span>
                        <span className="min-w-0">
                          <span className="block text-sm font-medium text-slate-200 truncate">{d.name}</span>
                          <span className="block text-xs text-slate-500 truncate">{d.description}</span>
                        </span>
                      </span>
                      <span className="shrink-0 rounded-md bg-white/[0.04] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-mortgage">Run</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          <div className="glass-card overflow-hidden">
        <div className="border-b border-white/[0.06] px-6 py-4">
          <h3 className="font-semibold">Job Queue</h3>
        </div>
        {!jobs?.length ? (
          <EmptyState icon={Home} title="No mortgage jobs" description="Upload a package or run a sample above" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06] bg-surface-overlay text-left text-xs uppercase tracking-wider text-slate-500">
                  <th className="px-6 py-3">Job ID</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Journey</th>
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
                      <td className="px-6 py-3.5"><StageStrip stages={stagesFromProgress(job)} compact /></td>
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
    </div>
    </div>
  );
}
