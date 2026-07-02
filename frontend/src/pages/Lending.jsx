import { useState, useEffect, useCallback } from 'react';
import { Wallet, RefreshCw } from 'lucide-react';
import { StatCard, Badge, EmptyState } from '../components/ui';
import { endpoints, fmtCurrency } from '../lib/api';

export default function LendingPage() {
  const [products, setProducts] = useState([]);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    applicant_name: '', annual_income: '', credit_score: '', loan_amount: '', property_value: '', employment_years: '',
  });

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [p, r] = await Promise.all([
        endpoints.lendingProducts().catch(() => ({ products: [] })),
        Promise.resolve([]),
      ]);
      setProducts(p.products || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      const res = await endpoints.runLending({
        applicant_name: form.applicant_name,
        annual_income: Number(form.annual_income),
        credit_score: Number(form.credit_score),
        loan_amount: Number(form.loan_amount),
        property_value: Number(form.property_value),
        employment_years: Number(form.employment_years),
      });
      const detail = await endpoints.lendingResult(res.application_id);
      setResults((prev) => [detail, ...prev]);
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-8 animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-500/15">
            <Wallet className="h-6 w-6 text-emerald-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Lending Underwriting</h1>
            <p className="mt-1 max-w-xl text-slate-400">Consumer & commercial loan applications — credit risk, compliance, and pricing</p>
          </div>
        </div>
        <button type="button" onClick={load} className="btn-secondary btn-sm text-xs">
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {error && (
        <div className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="glass-card p-6">
          <h3 className="mb-4 font-semibold">New Application</h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-400">Applicant Name</label>
              <input className="input-field w-full text-sm" value={form.applicant_name} onChange={e => setForm(f => ({ ...f, applicant_name: e.target.value }))} required />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Annual Income</label>
                <input type="number" className="input-field w-full text-sm" value={form.annual_income} onChange={e => setForm(f => ({ ...f, annual_income: e.target.value }))} required />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Credit Score</label>
                <input type="number" className="input-field w-full text-sm" value={form.credit_score} onChange={e => setForm(f => ({ ...f, credit_score: e.target.value }))} required />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Loan Amount</label>
                <input type="number" className="input-field w-full text-sm" value={form.loan_amount} onChange={e => setForm(f => ({ ...f, loan_amount: e.target.value }))} required />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Property Value</label>
                <input type="number" className="input-field w-full text-sm" value={form.property_value} onChange={e => setForm(f => ({ ...f, property_value: e.target.value }))} required />
              </div>
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-400">Years Employed</label>
              <input type="number" className="input-field w-full text-sm" value={form.employment_years} onChange={e => setForm(f => ({ ...f, employment_years: e.target.value }))} required />
            </div>
            <button type="submit" disabled={submitting} className="btn-primary">{submitting ? 'Processing…' : 'Submit Application'}</button>
          </form>
        </div>

        <div className="glass-card p-6">
          <h3 className="mb-4 font-semibold">Loan Products</h3>
          {products.length === 0 ? (
            <p className="text-sm text-slate-500">No products available</p>
          ) : (
            <div className="space-y-3">
              {products.map((p) => (
                <div key={p.product_id || p.name} className="rounded-xl bg-surface-overlay p-4 ring-1 ring-white/[0.04]">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-slate-200">{p.name}</span>
                    <span className="text-xs text-slate-500">{p.type}</span>
                  </div>
                  <div className="mt-2 flex gap-4 text-xs text-slate-400">
                    <span>Min rate: {p.min_rate}%</span>
                    <span>Max rate: {p.max_rate}%</span>
                    <span>Max LTV: {p.max_ltv}%</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {results.length > 0 && (
        <div className="glass-card overflow-hidden">
          <div className="border-b border-white/[0.06] px-5 py-3">
            <h3 className="text-sm font-semibold">Recent Decisions</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06] bg-surface-overlay text-left text-xs uppercase tracking-wider text-slate-500">
                  <th className="px-6 py-3">Applicant</th>
                  <th className="px-6 py-3">Decision</th>
                  <th className="px-6 py-3">Rate</th>
                  <th className="px-6 py-3">Amount</th>
                  <th className="px-6 py-3">Risk Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {results.map((r, i) => (
                  <tr key={i}>
                    <td className="px-6 py-3.5 text-slate-300">{r.applicant_name || r.application_id}</td>
                    <td className="px-6 py-3.5"><Badge status={r.decision} /></td>
                    <td className="px-6 py-3.5 font-medium">{r.offered_rate != null ? `${r.offered_rate}%` : '—'}</td>
                    <td className="px-6 py-3.5 font-mono">{fmtCurrency(r.approved_amount)}</td>
                    <td className="px-6 py-3.5">{r.risk_score != null ? r.risk_score.toFixed(1) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
