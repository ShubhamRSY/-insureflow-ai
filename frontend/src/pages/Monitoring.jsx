import { useState, useEffect, useCallback } from 'react';
import { useOutletContext } from 'react-router-dom';
import {
  Activity, RefreshCw, AlertTriangle, Plus, CheckCircle2, XCircle, LineChart,
  ChevronDown, BellRing, Clock,
} from 'lucide-react';
import { Badge, EmptyState } from '../components/ui';
import { endpoints, fmtCurrency } from '../lib/api';

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

function lossRatioColor(ratio) {
  if (ratio >= 0.9) return 'bg-red-500/80';
  if (ratio >= 0.7) return 'bg-amber-500/80';
  if (ratio > 0) return 'bg-emerald-500/80';
  return 'bg-white/10';
}

function LossRatioBar({ ratio }) {
  const pct = Math.max(0, Math.min(100, (ratio || 0) * 100));
  return (
    <div>
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-slate-500">Latest loss ratio</span>
        <span className={`font-semibold ${ratio >= 0.9 ? 'text-red-400' : ratio >= 0.7 ? 'text-amber-400' : 'text-slate-300'}`}>
          {ratio ? `${(ratio * 100).toFixed(0)}%` : '—'}
        </span>
      </div>
      <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-white/10">
        <div className={`h-full rounded-full ${lossRatioColor(ratio)}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function SeverityMeta(sev) {
  return {
    low: { cls: 'text-sky-400 bg-sky-500/15 ring-sky-500/25' },
    moderate: { cls: 'text-amber-400 bg-amber-500/15 ring-amber-500/25' },
    high: { cls: 'text-orange-400 bg-orange-500/15 ring-orange-500/25' },
    critical: { cls: 'text-red-400 bg-red-500/15 ring-red-500/25' },
  }[sev] || { cls: 'text-slate-400 bg-white/5 ring-white/10' };
}

function openItem(item) {
  return ['open', 'monitoring'].includes(item.status);
}

export default function MonitoringPage() {
  const { user } = useOutletContext() || {};
  const [policies, setPolicies] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);
  const [error, setError] = useState('');
  const [detail, setDetail] = useState(null); // { policyId, record }
  const [busy, setBusy] = useState('');
  const [showAddItem, setShowAddItem] = useState(false);
  const [showLossDev, setShowLossDev] = useState(false);
  const [itemForm, setItemForm] = useState({ title: '', description: '', severity: 'moderate', source: 'manual', due_by: '' });
  const [lossForm, setLossForm] = useState({ policy_year: 0, earned_premium: '', incurred_losses: '', paid_losses: '', claim_count: 0 });

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [p, a] = await Promise.all([
        endpoints.monitoringPolicies().catch(() => ({ policies: [] })),
        endpoints.monitoringAlerts().catch(() => ({ alerts: [] })),
      ]);
      setPolicies(p.policies || []);
      setAlerts(a.alerts || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const runEvaluation = async () => {
    setEvaluating(true);
    try {
      const res = await endpoints.monitoringEvaluate();
      setPolicies(res.policies || []);
      setAlerts(res.alerts || []);
      if (detail) {
        const fresh = await endpoints.monitoringPolicy(detail.policyId).catch(() => null);
        if (fresh) setDetail({ policyId: detail.policyId, record: fresh });
      }
    } catch (e) {
      alert(e.message);
    } finally {
      setEvaluating(false);
    }
  };

  const openDetail = async (policyId) => {
    setDetail((d) => (d && d.policyId === policyId ? { policyId, record: null } : { policyId, record: null }));
    try {
      const record = await endpoints.monitoringPolicy(policyId);
      setDetail({ policyId, record });
    } catch (e) {
      alert(e.message);
      setDetail(null);
    }
  };

  const afterMutation = async (policyId) => {
    const fresh = await endpoints.monitoringPolicy(policyId).catch(() => null);
    if (fresh) setDetail({ policyId, record: fresh });
    await load();
  };

  const addItem = async (e) => {
    e.preventDefault();
    if (!detail) return;
    try {
      await endpoints.addMonitoringItem(detail.policyId, itemForm);
      setItemForm({ title: '', description: '', severity: 'moderate', source: 'manual', due_by: '' });
      setShowAddItem(false);
      await afterMutation(detail.policyId);
    } catch (err) {
      alert(err.message);
    }
  };

  const resolveItem = async (itemId, status) => {
    if (!detail) return;
    setBusy(`item-${itemId}`);
    const note = status === 'waived'
      ? window.prompt('Reason for waiving this item?', '') || ''
      : '';
    try {
      await endpoints.resolveMonitoringItem(detail.policyId, itemId, { status, note, resolved_by: user?.username || 'uw' });
      await afterMutation(detail.policyId);
    } catch (err) {
      alert(err.message);
    } finally {
      setBusy('');
    }
  };

  const recordLossDev = async (e) => {
    e.preventDefault();
    if (!detail) return;
    try {
      await endpoints.recordLossDevelopment(detail.policyId, {
        policy_year: Number(lossForm.policy_year || 0),
        earned_premium: Number(lossForm.earned_premium || 0),
        incurred_losses: Number(lossForm.incurred_losses || 0),
        paid_losses: Number(lossForm.paid_losses || 0),
        claim_count: Number(lossForm.claim_count || 0),
      });
      setLossForm({ policy_year: 0, earned_premium: '', incurred_losses: '', paid_losses: '', claim_count: 0 });
      setShowLossDev(false);
      await afterMutation(detail.policyId);
    } catch (err) {
      alert(err.message);
    }
  };

  const watchCount = policies.filter((p) => p.status === 'watch').length;
  const openAlerts = alerts.filter((a) => !a.resolved);
  const avgLossRatio = policies.length
    ? policies.reduce((s, p) => s + (p.latest_loss_ratio || 0), 0) / policies.length
    : 0;

  return (
    <div className="mx-auto max-w-7xl space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-violet-500/15">
            <Activity className="h-6 w-6 text-violet-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Policy Monitoring</h1>
            <p className="mt-1 text-sm text-slate-400">
              In-force policies tracked between bind and renewal — UW memo conditions, loss development, expiry, and renewal alerts.
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={runEvaluation} disabled={evaluating} className="btn-secondary btn-sm text-xs">
            <LineChart className={`h-3.5 w-3.5 ${evaluating ? 'animate-pulse' : ''}`} /> Run evaluation
          </button>
          <button type="button" onClick={load} className="btn-secondary btn-sm text-xs"><RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh</button>
        </div>
      </div>

      {error && <div className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="glass-card group relative overflow-hidden p-5 animate-slide-up">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-violet-500 to-fuchsia-400 opacity-60" />
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Monitored policies</p>
            <Activity className="h-4 w-4 text-violet-400" />
          </div>
          <p className="mt-2 text-3xl font-bold tracking-tight text-white">{policies.length}</p>
        </div>
        <div className="glass-card group relative overflow-hidden p-5 animate-slide-up">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-red-500 to-rose-400 opacity-60" />
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Open alerts</p>
            <BellRing className="h-4 w-4 text-red-400" />
          </div>
          <p className="mt-2 text-3xl font-bold tracking-tight text-white">{openAlerts.length}</p>
        </div>
        <div className="glass-card group relative overflow-hidden p-5 animate-slide-up">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-amber-500 to-orange-400 opacity-60" />
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500">On watch</p>
            <AlertTriangle className="h-4 w-4 text-amber-400" />
          </div>
          <p className="mt-2 text-3xl font-bold tracking-tight text-white">{watchCount}</p>
        </div>
        <div className="glass-card group relative overflow-hidden p-5 animate-slide-up">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-emerald-500 to-teal-400 opacity-60" />
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Avg loss ratio</p>
            <LineChart className="h-4 w-4 text-emerald-400" />
          </div>
          <p className="mt-2 text-3xl font-bold tracking-tight text-white">{avgLossRatio ? `${(avgLossRatio * 100).toFixed(0)}%` : '—'}</p>
        </div>
      </div>

      {openAlerts.length > 0 && (
        <div className="glass-card p-6">
          <div className="mb-3 flex items-center gap-2">
            <BellRing className="h-4 w-4 text-red-400" />
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Open monitoring alerts</h3>
            <span className="ml-auto rounded-full bg-red-500/15 px-2 py-0.5 text-[11px] font-bold text-red-400">{openAlerts.length}</span>
          </div>
          <div className="grid gap-2 md:grid-cols-2">
            {openAlerts.map((a) => {
              const meta = SeverityMeta(a.severity);
              return (
                <div key={a.alert_id} className="rounded-xl bg-black/20 px-4 py-3 ring-1 ring-white/[0.04]">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-medium text-slate-200">{a.title}</p>
                    <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ring-1 ${meta.cls}`}>{a.severity}</span>
                  </div>
                  {a.message && <p className="mt-1 text-xs leading-relaxed text-slate-500">{a.message}</p>}
                  <p className="mt-1.5 text-[11px] text-slate-600">
                    <span className="font-mono">{a.policy_id}</span> · {fmtDateTime(a.created_at)}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="glass-card p-6">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">In-force policies</h3>
            <p className="mt-1 text-xs text-slate-500">Select a policy to manage monitoring items, loss development, and alerts</p>
          </div>
        </div>

        {loading ? (
          <div className="flex justify-center py-12">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
          </div>
        ) : policies.length === 0 ? (
          <EmptyState
            icon={Activity}
            title="No policies under monitoring"
            description="Bind an approved submission to seed monitoring with its UW memo conditions and policy term."
          />
        ) : (
          <div className="space-y-3">
            {policies.map((p) => {
              const isOpen = detail?.policyId === p.policy_id;
              return (
                <div key={p.policy_id} className="overflow-hidden rounded-xl border border-white/[0.06]">
                  <button
                    type="button"
                    onClick={() => openDetail(p.policy_id)}
                    className={`flex w-full flex-wrap items-center gap-4 bg-surface-overlay px-4 py-3 text-left transition hover:bg-white/[0.03] ${isOpen ? 'bg-white/[0.04]' : ''}`}
                  >
                    <ChevronDown className={`h-4 w-4 shrink-0 text-slate-500 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-medium text-white">{p.insured_name || 'Unnamed insured'}</p>
                        <Badge status={p.status} />
                      </div>
                      <p className="mt-0.5 text-xs text-slate-500">
                        <span className="font-mono text-slate-400">{p.policy_number || p.policy_id}</span>
                        {' · '}{p.line_of_business || '—'}
                        {' · expires in '}<span className={p.days_to_expiry <= 120 && p.days_to_expiry > 0 ? 'text-amber-400' : 'text-slate-400'}>{p.days_to_expiry > 0 ? `${p.days_to_expiry}d` : '—'}</span>
                      </p>
                    </div>
                    <div className="hidden w-44 shrink-0 sm:block"><LossRatioBar ratio={p.latest_loss_ratio} /></div>
                    <div className="flex shrink-0 items-center gap-3 text-xs">
                      <span className="inline-flex items-center gap-1 rounded-full bg-surface-overlay px-2 py-1 text-slate-300 ring-1 ring-white/[0.06]"><AlertTriangle className={`h-3 w-3 ${p.open_alert_count ? 'text-red-400' : 'text-slate-600'}`} /> {p.open_alert_count}</span>
                      <span className="inline-flex items-center gap-1 rounded-full bg-surface-overlay px-2 py-1 text-slate-300 ring-1 ring-white/[0.06]"><Clock className={`h-3 w-3 ${p.open_item_count ? 'text-amber-400' : 'text-slate-600'}`} /> {p.open_item_count} items</span>
                      <span className="hidden font-semibold text-slate-200 md:block">{fmtCurrency(p.premium)}</span>
                    </div>
                  </button>

                  {isOpen && (
                    <div className="border-t border-white/[0.06] bg-black/20 p-4">
                      {busy === 'detail' && !detail?.record ? (
                        <div className="flex justify-center py-8">
                          <div className="h-6 w-6 animate-spin rounded-full border-2 border-brand border-t-transparent" />
                        </div>
                      ) : detail?.record ? <PolicyDetail
                        record={detail.record}
                        busy={busy}
                        showAddItem={showAddItem}
                        setShowAddItem={setShowAddItem}
                        itemForm={itemForm}
                        setItemForm={setItemForm}
                        onAddItem={addItem}
                        onResolve={resolveItem}
                        showLossDev={showLossDev}
                        setShowLossDev={setShowLossDev}
                        lossForm={lossForm}
                        setLossForm={setLossForm}
                        onRecordLossDev={recordLossDev}
                      /> : null}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function PolicyDetail({
  record, busy, showAddItem, setShowAddItem, itemForm, setItemForm, onAddItem,
  onResolve, showLossDev, setShowLossDev, lossForm, setLossForm, onRecordLossDev,
}) {
  const openItems = record.items?.filter(openItem) || [];
  const clearedItems = record.items?.filter((i) => !openItem(i)) || [];
  const lossEntries = [...(record.loss_development || [])].reverse();

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-2 rounded-xl bg-surface-overlay p-3 text-xs sm:grid-cols-4">
        <div><span className="text-slate-500">Policy term</span><p className="mt-0.5 font-medium text-slate-200">{fmtDate(record.effective_date)} → {fmtDate(record.expiry_date)}</p></div>
        <div><span className="text-slate-500">Premium</span><p className="mt-0.5 font-medium text-slate-200">{fmtCurrency(record.premium)}</p></div>
        <div><span className="text-slate-500">TIV</span><p className="mt-0.5 font-medium text-slate-200">{fmtCurrency(record.tiv)}</p></div>
        <div><span className="text-slate-500">Bundle</span><p className="mt-0.5 font-mono font-medium text-slate-200">{record.bundle_id || '—'}</p></div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl bg-surface-overlay p-4">
          <div className="mb-3 flex items-center justify-between">
            <h4 className="flex items-center gap-2 text-sm font-semibold text-slate-200"><AlertTriangle className="h-4 w-4 text-amber-400" /> Monitoring items</h4>
            <button type="button" onClick={() => setShowAddItem((v) => !v)} className="inline-flex items-center gap-1 rounded-lg bg-violet-500/15 px-2.5 py-1 text-xs font-medium text-violet-300 ring-1 ring-inset ring-violet-500/25 transition hover:bg-violet-500/25">
              <Plus className="h-3 w-3" /> Add item
            </button>
          </div>

          {showAddItem && (
            <form onSubmit={onAddItem} className="mb-3 space-y-2 rounded-lg bg-black/20 p-3">
              <input className="input-field w-full text-sm" placeholder="Title (e.g. roof age verified by renewal)" value={itemForm.title} onChange={(e) => setItemForm((f) => ({ ...f, title: e.target.value }))} required />
              <textarea className="input-field w-full text-sm" rows={2} placeholder="Description / action required" value={itemForm.description} onChange={(e) => setItemForm((f) => ({ ...f, description: e.target.value }))} />
              <div className="grid grid-cols-2 gap-2">
                <select className="input-field w-full text-sm" value={itemForm.severity} onChange={(e) => setItemForm((f) => ({ ...f, severity: e.target.value }))}>
                  <option value="low">Low</option>
                  <option value="moderate">Moderate</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
                <select className="input-field w-full text-sm" value={itemForm.source} onChange={(e) => setItemForm((f) => ({ ...f, source: e.target.value }))}>
                  <option value="manual">Manual</option>
                  <option value="uw_memo">UW memo</option>
                  <option value="loss_development">Loss development</option>
                  <option value="expiry">Expiry</option>
                  <option value="renewal">Renewal</option>
                </select>
              </div>
              <input type="date" className="input-field w-full text-sm" value={itemForm.due_by} onChange={(e) => setItemForm((f) => ({ ...f, due_by: e.target.value }))} />
              <div className="flex gap-2">
                <button type="submit" className="btn-primary btn-sm text-xs">Add item</button>
                <button type="button" onClick={() => setShowAddItem(false)} className="btn-secondary btn-sm text-xs">Cancel</button>
              </div>
            </form>
          )}

          {openItems.length === 0 && clearedItems.length === 0 ? (
            <p className="text-xs text-slate-500">No monitoring items on this policy.</p>
          ) : (
            <ul className="space-y-2">
              {openItems.map((i) => (
                <li key={i.item_id} className="rounded-lg bg-black/20 p-3 ring-1 ring-white/[0.04]">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-slate-200">{i.title}</p>
                      {i.description && <p className="mt-0.5 text-xs leading-relaxed text-slate-500">{i.description}</p>}
                    </div>
                    <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ring-1 ${SeverityMeta(i.severity).cls}`}>{i.severity}</span>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-slate-500">
                    <span className="capitalize">{i.source.replace('_', ' ')}</span>
                    {i.due_by && <span className={`inline-flex items-center gap-1 ${i.due_by < new Date().toISOString().slice(0, 10) ? 'text-red-400' : ''}`}><Clock className="h-3 w-3" /> due {fmtDate(i.due_by)}</span>}
                    <span className="ml-auto flex gap-1.5">
                      <button type="button" disabled={busy === `item-${i.item_id}`} onClick={() => onResolve(i.item_id, 'cleared')} className="inline-flex items-center gap-1 rounded-lg bg-emerald-500/10 px-2 py-0.5 text-emerald-400 ring-1 ring-inset ring-emerald-500/25 hover:bg-emerald-500/20 disabled:opacity-50"><CheckCircle2 className="h-3 w-3" /> Cleared</button>
                      <button type="button" disabled={busy === `item-${i.item_id}`} onClick={() => onResolve(i.item_id, 'waived')} className="inline-flex items-center gap-1 rounded-lg bg-slate-500/10 px-2 py-0.5 text-slate-400 ring-1 ring-inset ring-slate-500/25 hover:bg-slate-500/20 disabled:opacity-50"><XCircle className="h-3 w-3" /> Waive</button>
                    </span>
                  </div>
                </li>
              ))}
              {clearedItems.map((i) => (
                <li key={i.item_id} className="rounded-lg bg-black/20 p-3 opacity-60 ring-1 ring-white/[0.04]">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm text-slate-300 line-through decoration-slate-600">{i.title}</p>
                    <Badge status={i.status} />
                  </div>
                  <p className="mt-1 text-[11px] text-slate-500">
                    {i.resolved_at ? `Resolved ${fmtDateTime(i.resolved_at)}` : ''}{i.resolved_by ? ` by ${i.resolved_by}` : ''}
                    {i.notes?.length ? ` · ${i.notes.join(' · ')}` : ''}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="space-y-4">
          <div className="rounded-xl bg-surface-overlay p-4">
            <div className="mb-3 flex items-center justify-between">
              <h4 className="flex items-center gap-2 text-sm font-semibold text-slate-200"><LineChart className="h-4 w-4 text-emerald-400" /> Loss development</h4>
              <button type="button" onClick={() => setShowLossDev((v) => !v)} className="inline-flex items-center gap-1 rounded-lg bg-emerald-500/15 px-2.5 py-1 text-xs font-medium text-emerald-300 ring-1 ring-inset ring-emerald-500/25 transition hover:bg-emerald-500/25">
                <Plus className="h-3 w-3" /> Record
              </button>
            </div>

            {showLossDev && (
              <form onSubmit={onRecordLossDev} className="mb-3 space-y-2 rounded-lg bg-black/20 p-3">
                <div className="grid grid-cols-2 gap-2">
                  <input type="number" className="input-field w-full text-sm" placeholder="Policy year" value={lossForm.policy_year} onChange={(e) => setLossForm((f) => ({ ...f, policy_year: e.target.value }))} />
                  <input type="number" step="0.01" className="input-field w-full text-sm" placeholder="Earned premium" value={lossForm.earned_premium} onChange={(e) => setLossForm((f) => ({ ...f, earned_premium: e.target.value }))} required />
                  <input type="number" step="0.01" className="input-field w-full text-sm" placeholder="Incurred losses" value={lossForm.incurred_losses} onChange={(e) => setLossForm((f) => ({ ...f, incurred_losses: e.target.value }))} required />
                  <input type="number" step="0.01" className="input-field w-full text-sm" placeholder="Paid losses" value={lossForm.paid_losses} onChange={(e) => setLossForm((f) => ({ ...f, paid_losses: e.target.value }))} />
                </div>
                <input type="number" className="input-field w-full text-sm" placeholder="Claim count" value={lossForm.claim_count} onChange={(e) => setLossForm((f) => ({ ...f, claim_count: e.target.value }))} />
                <div className="flex gap-2">
                  <button type="submit" className="btn-primary btn-sm text-xs">Record</button>
                  <button type="button" onClick={() => setShowLossDev(false)} className="btn-secondary btn-sm text-xs">Cancel</button>
                </div>
              </form>
            )}

            <LossRatioBar ratio={record.latest_loss_ratio} />

            {lossEntries.length === 0 ? (
              <p className="mt-3 text-xs text-slate-500">No loss development recorded yet.</p>
            ) : (
              <div className="mt-3 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/[0.06] text-left text-[10px] uppercase tracking-wider text-slate-500">
                      <th className="px-2 py-1.5">Year</th>
                      <th className="px-2 py-1.5">Earned</th>
                      <th className="px-2 py-1.5">Incurred</th>
                      <th className="px-2 py-1.5">Claims</th>
                      <th className="px-2 py-1.5">Ratio</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.04]">
                    {lossEntries.map((e) => (
                      <tr key={e.entry_id} className="hover:bg-white/[0.02]">
                        <td className="px-2 py-2 text-xs text-slate-300">{e.policy_year || fmtDate(e.recorded_at)}</td>
                        <td className="px-2 py-2 text-xs text-slate-400">{fmtCurrency(e.earned_premium)}</td>
                        <td className="px-2 py-2 text-xs text-slate-400">{fmtCurrency(e.incurred_losses)}</td>
                        <td className="px-2 py-2 text-xs text-slate-400">{e.claim_count}</td>
                        <td className={`px-2 py-2 text-xs font-semibold ${e.loss_ratio >= 0.9 ? 'text-red-400' : e.loss_ratio >= 0.7 ? 'text-amber-400' : 'text-slate-300'}`}>{(e.loss_ratio * 100).toFixed(0)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {record.alerts?.filter((a) => !a.resolved).length > 0 && (
            <div className="rounded-xl bg-surface-overlay p-4">
              <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-200"><BellRing className="h-4 w-4 text-red-400" /> Policy alerts</h4>
              <ul className="space-y-2">
                {record.alerts.filter((a) => !a.resolved).map((a) => (
                  <li key={a.alert_id} className="flex items-start justify-between gap-2 rounded-lg bg-black/20 px-3 py-2 ring-1 ring-white/[0.04]">
                    <div>
                      <p className="text-xs font-medium text-slate-200">{a.title}</p>
                      {a.message && <p className="mt-0.5 text-[11px] leading-relaxed text-slate-500">{a.message}</p>}
                    </div>
                    <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ring-1 ${SeverityMeta(a.severity).cls}`}>{a.severity}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
