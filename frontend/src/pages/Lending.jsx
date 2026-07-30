import { useState, useEffect, useCallback } from 'react';
import { Wallet, RefreshCw, FileUp, FolderOpen } from 'lucide-react';
import { Badge, EmptyState } from '../components/ui';
import { endpoints, fmtCurrency } from '../lib/api';
import StageStrip, { stagesFromProgress } from '../components/StageStrip';

const emptyForm = {
  product_type: 'business_term_loan',
  purpose: 'working_capital',
  business_name: '',
  industry: '',
  amount: '',
  term_months: '12',
  revenue: '',
  net_income: '',
  ebitda: '',
  debt_service: '',
  credit_score: '',
  annual_income: '',
  years_in_business: '',
  directory: '',
};

function fileToPayload(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error(`Failed to read ${file.name}`));
    reader.onload = () => {
      const result = String(reader.result || '');
      const isBinary = /\.(pdf|png|jpe?g|tiff?|bmp)$/i.test(file.name);
      if (isBinary) {
        const base64 = result.includes(',') ? result.split(',')[1] : result;
        resolve({ filename: file.name, content: base64, encoding: 'base64' });
      } else {
        resolve({ filename: file.name, content: result, encoding: 'utf-8' });
      }
    };
    if (/\.(pdf|png|jpe?g|tiff?|bmp)$/i.test(file.name)) reader.readAsDataURL(file);
    else reader.readAsText(file);
  });
}

export default function LendingPage() {
  const [products, setProducts] = useState([]);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [form, setForm] = useState(emptyForm);
  const [files, setFiles] = useState([]);
  const [mode, setMode] = useState('form'); // form | documents | directory

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const p = await endpoints.lendingProducts().catch(() => ({ products: [] }));
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
    setMessage('');
    try {
      const body = {
        product_type: form.product_type,
        purpose: form.purpose,
        business_name: form.business_name,
        industry: form.industry,
        amount: Number(form.amount) || 0,
        term_months: Number(form.term_months) || 12,
        revenue: Number(form.revenue) || 0,
        net_income: Number(form.net_income) || 0,
        ebitda: Number(form.ebitda) || 0,
        debt_service: Number(form.debt_service) || 0,
        credit_score: Number(form.credit_score) || 0,
        annual_income: Number(form.annual_income) || 0,
        years_in_business: Number(form.years_in_business) || 0,
        require_documents: mode !== 'form',
      };

      if (mode === 'directory' && form.directory.trim()) {
        body.directory = form.directory.trim();
      } else if (mode === 'documents') {
        if (!files.length) throw new Error('Choose at least one application document');
        body.documents = await Promise.all([...files].map(fileToPayload));
      }

      const res = await endpoints.runLending(body);
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
        `Decision: ${result.decision}` +
        (res.documents_ingested ? ` · ${res.documents_ingested} doc(s) ingested` : '') +
        (result.human_review_required ? ' · human review required' : ''),
      );
      setFiles([]);
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setSubmitting(false);
    }
  };

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  return (
    <div className="mx-auto max-w-6xl space-y-8 animate-fade-in">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-500/15">
            <Wallet className="h-6 w-6 text-emerald-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Lending Underwriting</h1>
            <p className="mt-1 max-w-xl text-slate-400">Form fields or raw application packages — OCR/LLM extraction, compliance, pricing</p>
          </div>
        </div>
        <button type="button" onClick={load} className="btn-secondary btn-sm text-xs">
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {error && <div className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}
      {message && <div className="rounded-xl bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">{message}</div>}

      <div className="flex flex-wrap gap-2">
        {[
          ['form', 'Structured form'],
          ['documents', 'Upload documents'],
          ['directory', 'Server directory'],
        ].map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={`btn-sm text-xs ${mode === id ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setMode(id)}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="glass-card p-6">
          <h3 className="mb-4 font-semibold">New Application</h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Product</label>
                <select className="input-field w-full text-sm" value={form.product_type} onChange={set('product_type')}>
                  {(products.length ? products : [
                    'business_term_loan', 'sba_7a', 'cre', 'personal_term', 'auto',
                  ]).map((p) => {
                    const val = typeof p === 'string' ? p : (p.value || p.name || p);
                    return <option key={val} value={val}>{val}</option>;
                  })}
                </select>
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Purpose</label>
                <select className="input-field w-full text-sm" value={form.purpose} onChange={set('purpose')}>
                  <option value="working_capital">Working capital</option>
                  <option value="equipment">Equipment</option>
                  <option value="real_estate">Real estate</option>
                  <option value="debt_consolidation">Debt consolidation</option>
                  <option value="other">Other</option>
                </select>
              </div>
            </div>

            {mode === 'documents' && (
              <div>
                <label className="mb-1.5 flex items-center gap-2 text-xs font-medium text-slate-400">
                  <FileUp className="h-3.5 w-3.5" /> Application package (PDF/TXT/MD/XML)
                </label>
                <input
                  type="file"
                  multiple
                  accept=".pdf,.txt,.md,.xml,.json,.csv,.png,.jpg,.jpeg"
                  className="input-field w-full text-sm"
                  onChange={(e) => setFiles(e.target.files || [])}
                />
                <p className="mt-1 text-xs text-slate-500">{files.length ? `${files.length} file(s) selected` : 'Financials extracted from docs; form fields override blanks only'}</p>
              </div>
            )}

            {mode === 'directory' && (
              <div>
                <label className="mb-1.5 flex items-center gap-2 text-xs font-medium text-slate-400">
                  <FolderOpen className="h-3.5 w-3.5" /> Server path
                </label>
                <input
                  className="input-field w-full text-sm"
                  placeholder="e.g. simulated_documents/commercial_mortgage/oak_street_retail"
                  value={form.directory}
                  onChange={set('directory')}
                  required
                />
              </div>
            )}

            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-400">Business / applicant name</label>
              <input className="input-field w-full text-sm" value={form.business_name} onChange={set('business_name')} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Requested amount</label>
                <input type="number" className="input-field w-full text-sm" value={form.amount} onChange={set('amount')} />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Term (months)</label>
                <input type="number" className="input-field w-full text-sm" value={form.term_months} onChange={set('term_months')} />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Annual revenue</label>
                <input type="number" className="input-field w-full text-sm" value={form.revenue} onChange={set('revenue')} />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Net income</label>
                <input type="number" className="input-field w-full text-sm" value={form.net_income} onChange={set('net_income')} />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Credit score</label>
                <input type="number" className="input-field w-full text-sm" value={form.credit_score} onChange={set('credit_score')} />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Years in business</label>
                <input type="number" className="input-field w-full text-sm" value={form.years_in_business} onChange={set('years_in_business')} />
              </div>
            </div>
            <button type="submit" disabled={submitting} className="btn-primary">
              {submitting ? 'Underwriting…' : 'Run lending pipeline'}
            </button>
          </form>
        </div>

        <div className="glass-card p-6">
          <h3 className="mb-4 font-semibold">Loan Products</h3>
          {products.length === 0 ? (
            <p className="text-sm text-slate-500">Product list from API — defaults available in form</p>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {products.map((p) => {
                const name = typeof p === 'string' ? p : (p.name || p.value || JSON.stringify(p));
                return (
                  <div key={name} className="rounded-xl bg-surface-overlay px-4 py-3 text-sm text-slate-300 ring-1 ring-white/[0.04]">
                    {name}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

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
        <EmptyState icon={Wallet} title="No lending runs yet" description="Submit a structured application or upload a package to underwrite" />
      )}
    </div>
  );
}
