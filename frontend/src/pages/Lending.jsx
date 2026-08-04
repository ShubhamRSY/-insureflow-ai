import { useCallback, useEffect, useState } from 'react';
import { Wallet, RefreshCw, Package } from 'lucide-react';
import { Badge, EmptyState } from '../components/ui';
import { endpoints, fmtCurrency } from '../lib/api';
import StageStrip, { stagesFromProgress } from '../components/StageStrip';
import RunSelector from '../components/RunSelector';

function sampleResult(res) {
  return {
    application_id: res.application_id,
    decision: res.decision,
    approved_rate: res.approved_rate,
    approved_amount: res.approved_amount,
    risk_score: res.risk_score,
    human_review_required: res.human_review_required,
    document_count: res.documents_ingested || res.document_count || 0,
    extracted_from_docs: true,
    timeline: res.timeline || [],
  };
}

export default function LendingPage({ presets, demoResult, onRunDemo }) {
  const [products, setProducts] = useState(null);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      await endpoints.lendingProducts().catch(() => {});
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadProducts = async () => {
    try { setProducts(await endpoints.lendingProducts()); } catch (e) { alert(e.message); }
  };

  useEffect(() => {
    load();
    if (demoResult) setResults((prev) => [sampleResult(demoResult), ...prev]);
  }, [demoResult, load]);

  const addResult = (res, prefix) => {
    const result = res.result || {};
    setResults((prev) => [{
      application_id: res.application_id,
      decision: result.decision,
      approved_rate: result.approved_rate,
      approved_amount: result.approved_amount,
      risk_score: result.risk_score,
      human_review_required: result.human_review_required,
      document_count: result.document_count || res.documents_ingested || 0,
      extracted_from_docs: res.extracted_from_docs,
      timeline: res.timeline || [],
    }, ...prev]);
    setMessage(
      `${prefix}: ${result.decision}` +
      (res.documents_ingested ? ` · ${res.documents_ingested} doc(s) ingested` : '') +
      (result.human_review_required ? ' · human review required' : ''),
    );
  };

  const handleSubmit = async (body) => {
    setSubmitting(true);
    setError('');
    setMessage('');
    try {
      const res = await endpoints.runLending(body);
      addResult(res, 'Underwrite');
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleConnectResult = async (res) => {
    setError('');
    setMessage('');
    addResult(res, 'Connect & pull');
  };

  return (
    <div className="mx-auto max-w-7xl space-y-8 animate-fade-in">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-lending/15">
            <Wallet className="h-6 w-6 text-lending" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Lending Underwriting</h1>
            <p className="mt-1 max-w-xl text-slate-400">
              Load one package, then run underwriting — application, P&amp;L, balance sheet, bank, credit, tax.
            </p>
          </div>
        </div>
        <button type="button" onClick={loadProducts} className="btn-secondary btn-sm text-xs">
          <Package className="h-3 w-3" /> Products
        </button>
      </div>

      {error && <div className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}
      {message && <div className="rounded-xl bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">{message}</div>}

      {products && (
        <div className="glass-card p-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
              <Package className="mr-2 inline h-4 w-4" /> Lending Products
            </h3>
            <button onClick={() => setProducts(null)} className="text-xs text-slate-500 hover:text-slate-300">Close</button>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {(products.products || []).map((p, i) => {
              const name = typeof p === 'string' ? p : (p.name || p.product_name || p.value || JSON.stringify(p));
              const desc = typeof p === 'string' ? '' : (p.description || p.product_type || '');
              return (
                <div key={`${name}-${i}`} className="rounded-lg bg-surface-overlay p-3 ring-1 ring-white/[0.04]">
                  <p className="text-sm font-medium text-slate-200">{name}</p>
                  {desc && <p className="text-xs text-slate-500">{desc}</p>}
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-12">
        {/* Left rail — loan package input */}
        <div className="lg:col-span-4">
          <div className="lg:sticky lg:top-20">
            <RunSelector
              vertical="lending"
              samples={presets?.lending || []}
              productField="product_type"
              productOptions={[
                { id: 'business_term_loan', label: 'Business term' },
                { id: 'sba_7a', label: 'SBA 7A' },
                { id: 'cre', label: 'Commercial RE' },
                { id: 'personal_term', label: 'Personal' },
                { id: 'auto', label: 'Auto' },
              ]}
              productDefault="business_term_loan"
              includePurpose
              purposeOptions={[
                { id: 'working_capital', label: 'Working capital' },
                { id: 'equipment', label: 'Equipment' },
                { id: 'real_estate', label: 'Real estate' },
                { id: 'debt_consolidation', label: 'Debt consolidation' },
                { id: 'other', label: 'Other' },
              ]}
              purposeDefault="working_capital"
              onSubmit={handleSubmit}
              onRunDemo={onRunDemo}
              onRunResult={handleConnectResult}
            />
          </div>
        </div>

        {/* Right column — recent decisions + samples */}
        <div className="lg:col-span-8 space-y-6">
          {results.length > 0 ? (
            <div className="glass-card overflow-hidden">
              <div className="border-b border-white/[0.06] px-5 py-3">
                <h3 className="text-sm font-semibold">Recent Decisions</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/[0.06] bg-surface-overlay text-left text-xs uppercase tracking-wider text-slate-500">
                      <th className="px-6 py-3">Application</th>
                      <th className="px-6 py-3">Journey</th>
                      <th className="px-6 py-3">Decision</th>
                      <th className="px-6 py-3">Rate</th>
                      <th className="px-6 py-3">Amount</th>
                      <th className="px-6 py-3">Risk</th>
                      <th className="px-6 py-3">Docs</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.04]">
                    {results.map((r) => (
                      <tr key={r.application_id}>
                        <td className="px-6 py-3.5 font-mono text-xs text-slate-300">{r.application_id}</td>
                        <td className="px-6 py-3.5">
                          <StageStrip stages={stagesFromProgress(r)} />
                        </td>
                        <td className="px-6 py-3.5"><Badge status={r.decision} /></td>
                        <td className="px-6 py-3.5 font-medium">{r.approved_rate != null ? `${Number(r.approved_rate).toFixed(2)}%` : '—'}</td>
                        <td className="px-6 py-3.5 font-mono">{fmtCurrency(r.approved_amount)}</td>
                        <td className="px-6 py-3.5">{r.risk_score != null ? Number(r.risk_score).toFixed(1) : '—'}</td>
                        <td className="px-6 py-3.5 text-slate-400">{r.document_count || 0}{r.extracted_from_docs ? ' · extracted' : ''}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <EmptyState icon={Wallet} title="No lending runs yet" description="Load a loan package above to underwrite — upload, server path, connect & pull, or a sample" />
          )}

          {(presets?.lending || []).length > 0 && (
            <div className="glass-card p-5">
              <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Quick samples</p>
              <div className="flex flex-col gap-2">
                {(presets?.lending || []).filter((d) => ['blue-harbor-bakery', 'keller-logistics'].includes(d.id)).map((d) => (
                  <button key={d.id} type="button" onClick={() => onRunDemo('lending', d.id)}
                    className="flex items-center justify-between gap-3 rounded-xl border border-white/[0.06] bg-surface-overlay/30 px-4 py-3 text-left transition hover:border-lending/35">
                    <span className="min-w-0 flex items-center gap-3">
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-lending/15">
                        <Wallet className="h-4 w-4 text-lending" />
                      </span>
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-medium text-slate-200">{d.name}</span>
                        <span className="block truncate text-xs text-slate-500">{d.description}</span>
                      </span>
                    </span>
                    <span className="flex shrink-0 items-center gap-2">
                      <span className="rounded-md bg-white/[0.04] px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-lending/80">
                        {String(d.product_type || 'business').replace(/_/g, ' ')}
                      </span>
                      <span className="rounded-md bg-white/[0.04] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-lending">Run</span>
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
