import { useState, useEffect, useCallback } from 'react';
import { FileCheck, RefreshCw, ScrollText, FileText, BadgeCheck, ClipboardList, ShieldCheck } from 'lucide-react';
import { Badge, EmptyState } from '../components/ui';
import { endpoints, fmtCurrency } from '../lib/api';

const DOC_META = {
  binder: { label: 'Binder', icon: ScrollText, accent: 'text-emerald-400', cls: 'bg-emerald-500/10 text-emerald-400 ring-emerald-500/25 hover:bg-emerald-500/20' },
  policy_worksheet: { label: 'Policy Worksheet', icon: ClipboardList, accent: 'text-sky-400', cls: 'bg-sky-500/10 text-sky-400 ring-sky-500/25 hover:bg-sky-500/20' },
  certificate: { label: 'Certificate of Insurance', icon: BadgeCheck, accent: 'text-amber-400', cls: 'bg-amber-500/10 text-amber-400 ring-amber-500/25 hover:bg-amber-500/20' },
};

function fmtDate(value) {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function fmtDateTime(value) {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' });
}

async function triggerDownload(promise) {
  const { blob, filename } = await promise;
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

function IssuanceCard({ record }) {
  const [busy, setBusy] = useState('');
  const download = async (docType) => {
    setBusy(docType);
    try {
      await triggerDownload(endpoints.issuanceDownload(record.bundle_id, docType));
    } catch (e) {
      alert(e.message);
    } finally {
      setBusy('');
    }
  };

  return (
    <div className="glass-card p-5 animate-slide-up">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="truncate font-semibold text-white">{record.insured_name || 'Unnamed insured'}</h3>
            <Badge status={record.status} />
          </div>
          <p className="mt-1 text-xs text-slate-500">
            <span className="font-mono text-slate-400">{record.policy_number || '—'}</span>
            {' · '}{record.line_of_business || '—'}{' · '}{record.broker_name ? `via ${record.broker_name}` : ''}
          </p>
        </div>
        <div className="shrink-0 text-right">
          <p className="text-xl font-bold text-white">{fmtCurrency(record.premium)}</p>
          <p className="text-[10px] uppercase tracking-wider text-slate-500">annual premium</p>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 rounded-xl bg-black/20 p-3 text-xs sm:grid-cols-4">
        <div>
          <span className="text-slate-500">Policy #</span>
          <p className="mt-0.5 font-mono font-medium text-slate-200">{record.policy_number || '—'}</p>
        </div>
        <div>
          <span className="text-slate-500">Term</span>
          <p className="mt-0.5 font-medium text-slate-200">{fmtDate(record.effective_date)} → {fmtDate(record.expiry_date)}</p>
        </div>
        <div>
          <span className="text-slate-500">Total insured value</span>
          <p className="mt-0.5 font-medium text-slate-200">{fmtCurrency(record.tiv)}</p>
        </div>
        <div>
          <span className="text-slate-500">Bound by</span>
          <p className="mt-0.5 font-medium text-slate-200">{record.bound_by || '—'} <span className="text-slate-500">· {fmtDateTime(record.bound_at)}</span></p>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <span className="font-mono text-[11px] text-slate-600">{record.bundle_id} · {record.issuance_id}</span>
        <div className="flex flex-wrap gap-2">
          {['binder', 'policy_worksheet', 'certificate'].map((dt) => {
            const meta = DOC_META[dt];
            const Icon = meta.icon;
            const found = (record.documents || []).find((d) => d.doc_type === dt);
            if (!found) return null;
            return (
              <button
                key={dt}
                type="button"
                disabled={busy === dt}
                onClick={() => download(dt)}
                className={`inline-flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-medium ring-1 ring-inset transition disabled:opacity-60 ${meta.cls}`}
              >
                <Icon className={`h-3.5 w-3.5 ${busy === dt ? 'animate-pulse' : ''}`} />
                {meta.label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default function IssuancePage() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await endpoints.issuanceRecords();
      setRecords(data.records || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const inForce = records.filter((r) => {
    if (!r.expiry_date) return true;
    const exp = new Date(r.expiry_date);
    return !Number.isNaN(exp.getTime()) && exp >= new Date();
  }).length;
  const totalPremium = records.reduce((s, r) => s + (r.premium || 0), 0);

  return (
    <div className="mx-auto max-w-6xl space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-500/15">
            <FileCheck className="h-6 w-6 text-emerald-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Issuance</h1>
            <p className="mt-1 text-sm text-slate-400">
              Binders, policy worksheets, and certificates of insurance issued when approved coverage goes into effect.
            </p>
          </div>
        </div>
        <button type="button" onClick={load} className="btn-secondary btn-sm text-xs"><RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh</button>
      </div>

      {error && <div className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="glass-card group relative overflow-hidden p-5 animate-slide-up">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-emerald-500 to-teal-400 opacity-60" />
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Packages issued</p>
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
          </div>
          <p className="mt-2 text-3xl font-bold tracking-tight text-white">{records.length}</p>
        </div>
        <div className="glass-card group relative overflow-hidden p-5 animate-slide-up">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-sky-500 to-cyan-400 opacity-60" />
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Policies in force</p>
            <FileText className="h-4 w-4 text-sky-400" />
          </div>
          <p className="mt-2 text-3xl font-bold tracking-tight text-white">{inForce}</p>
        </div>
        <div className="glass-card group relative overflow-hidden p-5 animate-slide-up">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-amber-500 to-orange-400 opacity-60" />
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Annualized premium</p>
            <FileCheck className="h-4 w-4 text-amber-400" />
          </div>
          <p className="mt-2 text-3xl font-bold tracking-tight text-white">{fmtCurrency(totalPremium)}</p>
        </div>
      </div>

      <div className="glass-card p-6">
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
          </div>
        ) : records.length === 0 ? (
          <EmptyState
            icon={FileCheck}
            title="No issued packages yet"
            description="Bind an approved submission to generate its binder, policy worksheet, and certificate of insurance."
          />
        ) : (
          <div className="space-y-4">
            {records.map((r) => <IssuanceCard key={r.issuance_id || r.bundle_id} record={r} />)}
          </div>
        )}
      </div>
    </div>
  );
}
