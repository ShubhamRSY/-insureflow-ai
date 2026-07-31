import { useState, useEffect } from 'react';
import { Badge, DecisionBadge, EmptyState } from '../components/ui';
import { fmtCurrency, extractInsurance, endpoints } from '../lib/api';
import InsuranceSourceHub from '../components/InsuranceSourceHub';
import JourneyMiniStrip from '../components/JourneyMiniStrip';
import { Shield, ArrowRight, Download, Trash2, RotateCcw, FileText } from 'lucide-react';

const FLOW_STEPS = [
  { label: 'Intake', desc: 'Connect & pull broker package' },
  { label: 'Parse', desc: 'OCR, classify, extract fields' },
  { label: 'Verify', desc: 'Oracles, COPE, reconciliation' },
  { label: 'Score', desc: 'Multi-agent risk analysis' },
  { label: 'Price', desc: 'Indicated premium build-up' },
  { label: 'Decide', desc: 'UW memo & workflow' },
];

export default function InsurancePage({ presets, jobs, onRunDemo, onOpenJob, onSubmit, onRefresh }) {
  const [loading, setLoading] = useState(false);
  const [retryingId, setRetryingId] = useState(null);

  const handleSubmit = async (payload) => {
    setLoading(true);
    try {
      await onSubmit(payload);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (e, id) => {
    e.stopPropagation();
    try {
      const data = await endpoints.downloadJob(id);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${id}-results.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(err.message);
    }
  };

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    try {
      await endpoints.deleteJob(id);
      if (onRefresh) onRefresh();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleRetry = async (e, id) => {
    e.stopPropagation();
    setRetryingId(id);
    try {
      const r = await endpoints.retryJob(id);
      if (onRefresh) onRefresh();
    } catch (err) {
      alert(err.message);
    } finally {
      setRetryingId(null);
    }
  };

  const handleClearAll = async () => {
    if (!confirm('Clear all insurance jobs?')) return;
    const ids = (jobs || []).map((j) => j.id);
    for (const id of ids) {
      await endpoints.deleteJob(id).catch(() => {});
    }
    if (onRefresh) onRefresh();
  };

  const handleReport = async (e, id) => {
    e.stopPropagation();
    try {
      const { blob, filename } = await endpoints.insuranceReport(id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(err.message);
    }
  };

  return (
    <div className="mx-auto max-w-7xl space-y-8 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Insurance Underwriting</h1>
        <p className="mt-2 text-sm text-slate-400">
          Commercial P&amp;C plus personal homeowners, auto, and life — parse, verify, score, price, decide.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-12">
        {/* Left rail — input sources */}
        <div className="lg:col-span-4">
          <div className="lg:sticky lg:top-20">
            <InsuranceSourceHub onSubmit={handleSubmit} loading={loading} />
          </div>
        </div>

        {/* Right column — recent runs + samples */}
        <div className="lg:col-span-8 space-y-6">
          {/* Pipeline flow narrative */}
          <div className="glass-card p-5">
            <p className="mb-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Underwriting pipeline</p>
            <div className="flex flex-wrap items-center gap-2">
              {FLOW_STEPS.map((step, i) => (
                <div key={step.label} className="flex items-center gap-2">
                  <div className="rounded-lg bg-surface-overlay px-3 py-2 ring-1 ring-white/[0.04]">
                    <p className="text-xs font-semibold text-slate-200">{step.label}</p>
                    <p className="text-[10px] text-slate-500">{step.desc}</p>
                  </div>
                  {i < FLOW_STEPS.length - 1 && <ArrowRight className="h-3.5 w-3.5 text-slate-600" />}
                </div>
              ))}
            </div>
            <p className="mt-3 text-xs text-slate-500">Open any job to see the full submission journey — COPE, provenance, checkpoints, and pricing breakdown.</p>
          </div>

          {/* Quick samples */}
          {(presets?.insurance || []).length > 0 && (
            <div className="glass-card p-5">
              <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Quick samples</p>
              <div className="flex flex-col gap-2">
                {(presets?.insurance || []).map((d) => (
                  <button key={d.id} type="button" onClick={() => onRunDemo('insurance', d.id)}
                    className="flex items-center justify-between gap-3 rounded-xl border border-white/[0.06] bg-surface-overlay/30 px-4 py-3 text-left transition hover:border-brand/30">
                    <span className="min-w-0">
                      <span className="block text-sm font-medium text-slate-200">{d.name}</span>
                      <span className="block text-xs text-slate-500 truncate">{d.description}</span>
                    </span>
                    <span className="shrink-0 rounded-md bg-white/[0.04] px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-slate-400">
                      {(d.insurance_line || 'commercial').replace(/_/g, ' ')}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="glass-card overflow-hidden">
        <div className="border-b border-white/[0.06] px-5 py-3 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold">Recent jobs</h3>
            <p className="text-xs text-slate-500">Click row for full detail</p>
          </div>
          {jobs?.length > 0 && (
            <button type="button" onClick={handleClearAll} className="text-xs text-red-400/70 hover:text-red-400 flex items-center gap-1">
              <Trash2 className="h-3 w-3" /> Clear all
            </button>
          )}
        </div>
        {!jobs?.length ? (
          <EmptyState icon={Shield} title="No insurance jobs" description="Upload a broker package or run a demo" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06] bg-surface-overlay text-left text-xs uppercase tracking-wider text-slate-500">
                  <th className="px-6 py-3">Job</th>
                  <th className="px-6 py-3">Insured</th>
                  <th className="px-6 py-3">Journey</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Decision</th>
                  <th className="px-6 py-3">Premium</th>
                  <th className="px-6 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {[...jobs].reverse().map(({ id, job }) => {
                  const s = extractInsurance(job);
                  return (
                    <tr key={id} onClick={() => onOpenJob('insurance', id)} className="cursor-pointer transition hover:bg-white/[0.02]">
                      <td className="px-6 py-3.5 font-mono text-xs text-slate-400">{id}</td>
                      <td className="px-6 py-3.5 text-slate-300">{s.insuredName || '—'}</td>
                      <td className="px-6 py-3.5"><JourneyMiniStrip job={job} /></td>
                      <td className="px-6 py-3.5"><Badge status={job?.status} pulse={job?.status === 'processing'} /></td>
                      <td className="px-6 py-3.5"><DecisionBadge decision={s.decision} jobStatus={job?.status} /></td>
                      <td className="px-6 py-3.5 font-medium">{fmtCurrency(s.premium)}</td>
                      <td className="px-6 py-3.5">
                        <div className="flex items-center gap-2">
                          <button type="button" onClick={(e) => handleRetry(e, id)} disabled={retryingId === id} className="text-slate-500 hover:text-amber-400 transition disabled:opacity-40" title={retryingId === id ? 'Retrying…' : 'Retry pipeline'}>
                            <RotateCcw className={`h-4 w-4 ${retryingId === id ? 'animate-spin' : ''}`} />
                          </button>
                          <button type="button" onClick={(e) => handleReport(e, id)} className="text-slate-500 hover:text-emerald-400 transition" title="Download full report (PDF)">
                            <FileText className="h-4 w-4" />
                          </button>
                          <button type="button" onClick={(e) => handleDownload(e, id)} className="text-slate-500 hover:text-brand-light transition" title="Download results">
                            <Download className="h-4 w-4" />
                          </button>
                          <button type="button" onClick={(e) => handleDelete(e, id)} className="text-slate-500 hover:text-red-400 transition" title="Delete job">
                            <Trash2 className="h-4 w-4" />
                          </button>
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
