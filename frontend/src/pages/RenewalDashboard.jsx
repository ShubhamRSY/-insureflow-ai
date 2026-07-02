import { useState, useEffect, useCallback } from 'react';
import { FileText, TrendingUp, TrendingDown, AlertTriangle, RefreshCw, Search, Plus, CheckCircle } from 'lucide-react';
import { StatCard, Badge, EmptyState } from '../components/ui';
import { endpoints, fmtCurrency } from '../lib/api';

export default function RenewalDashboard() {
  const [renewals, setRenewals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [showComplete, setShowComplete] = useState(null);
  const [createForm, setCreateForm] = useState({ bundle_id: '', estimated_premium: '', policy_number: '' });
  const [completeForm, setCompleteForm] = useState({ actual_premium: '', notes: '' });
  const [materialAdjustments, setMaterialAdjustments] = useState([]);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [data, mat] = await Promise.all([
        endpoints.premiumAudits(),
        endpoints.materialAdjustments().catch(() => ({ adjustments: [] })),
      ]);
      setRenewals(data.audits || []);
      setMaterialAdjustments(mat.adjustments || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const statusColor = (s) => {
    if (s === 'completed') return 'ok';
    if (s === 'in_progress') return 'processing';
    if (s === 'disputed') return 'error';
    return 'pending';
  };

  const deltaColor = (pct) => {
    if (pct > 15) return 'text-red-400';
    if (pct < -15) return 'text-emerald-400';
    return 'text-slate-400';
  };

  return (
    <div className="mx-auto max-w-6xl space-y-8 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Renewal Dashboard</h1>
          <p className="mt-1 text-slate-400">Pre-renewal analysis and premium audit tracking</p>
        </div>
        <button type="button" onClick={load} className="btn-secondary btn-sm text-xs">
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {error && (
        <div className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Total Audits" value={renewals.length} sub="All time" accent="brand" />
        <StatCard
          label="Pending"
          value={renewals.filter(r => r.status === 'pending').length}
          sub="Awaiting review"
          accent="insurance"
        />
        <StatCard
          label="Completed"
          value={renewals.filter(r => r.status === 'completed').length}
          sub="Reconciled"
          accent="success"
        />
      </div>

      <div className="flex justify-end">
        <button type="button" onClick={() => setShowCreate(true)} className="btn-primary btn-sm text-xs"><Plus className="h-3.5 w-3.5" /> Create Audit</button>
      </div>

      {showCreate && (
        <div className="glass-card p-6">
          <h3 className="mb-4 font-semibold">Create Premium Audit</h3>
          <form onSubmit={async (e) => {
            e.preventDefault();
            try {
              await endpoints.createPremiumAudit(createForm.bundle_id, Number(createForm.estimated_premium), { policy_number: createForm.policy_number });
              setShowCreate(false);
              setCreateForm({ bundle_id: '', estimated_premium: '', policy_number: '' });
              await load();
            } catch (e) { alert(e.message); }
          }} className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Bundle ID</label>
                <input className="input-field w-full text-sm" value={createForm.bundle_id} onChange={e => setCreateForm(f => ({ ...f, bundle_id: e.target.value }))} required />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Estimated Premium</label>
                <input type="number" className="input-field w-full text-sm" value={createForm.estimated_premium} onChange={e => setCreateForm(f => ({ ...f, estimated_premium: e.target.value }))} required />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Policy Number</label>
                <input className="input-field w-full text-sm" value={createForm.policy_number} onChange={e => setCreateForm(f => ({ ...f, policy_number: e.target.value }))} />
              </div>
            </div>
            <div className="flex gap-2">
              <button type="submit" className="btn-primary btn-sm">Create</button>
              <button type="button" onClick={() => setShowCreate(false)} className="btn-secondary btn-sm">Cancel</button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
        </div>
      ) : renewals.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No audits yet"
          description="Premium audits will appear here when policies reach their end-of-period"
        />
      ) : (
        <div className="glass-card overflow-hidden">
          <div className="border-b border-white/[0.06] px-5 py-4">
            <h3 className="font-semibold">Premium Audit History</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.04] text-xs uppercase tracking-wider text-slate-500">
                  <th className="px-5 py-3 text-left">Bundle ID</th>
                  <th className="px-5 py-3 text-left">Policy</th>
                  <th className="px-5 py-3 text-right">Estimated</th>
                  <th className="px-5 py-3 text-right">Actual</th>
                  <th className="px-5 py-3 text-right">Delta</th>
                  <th className="px-5 py-3 text-center">Status</th>
                  <th className="px-5 py-3 text-right">Adjustments</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {renewals.map((a) => {
                  const deltaPct = a.estimated_premium > 0
                    ? ((a.premium_delta || 0) / a.estimated_premium) * 100
                    : 0;
                  return (
                    <tr key={a.audit_id} className="hover:bg-white/[0.02]">
                      <td className="px-5 py-3 font-mono text-xs text-slate-300">{a.bundle_id}</td>
                      <td className="px-5 py-3 text-slate-400">{a.policy_number || '\u2014'}</td>
                      <td className="px-5 py-3 text-right font-mono">{fmtCurrency(a.estimated_premium)}</td>
                      <td className="px-5 py-3 text-right font-mono">{fmtCurrency(a.actual_premium)}</td>
                      <td className={`px-5 py-3 text-right font-mono ${deltaColor(deltaPct)}`}>
                        {deltaPct >= 0 ? '+' : ''}{deltaPct.toFixed(1)}%
                      </td>
                      <td className="px-5 py-3 text-center">
                        <Badge status={statusColor(a.status)} />
                      </td>
                      <td className="px-5 py-3 text-right font-mono text-slate-400">
                        {a.adjustments?.length || 0}
                      </td>
                      <td className="px-5 py-3 text-center">
                        {a.status === 'in_progress' && (
                          <button onClick={() => setShowComplete(a.audit_id)} className="rounded-lg bg-emerald-500/20 px-2 py-1 text-xs text-emerald-400 hover:bg-emerald-500/30"><CheckCircle className="h-3 w-3 inline" /> Complete</button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {showComplete && (
        <div className="glass-card p-6">
          <h3 className="mb-4 font-semibold">Complete Audit</h3>
          <form onSubmit={async (e) => {
            e.preventDefault();
            try {
              await endpoints.completePremiumAudit(showComplete, Number(completeForm.actual_premium), completeForm.notes);
              setShowComplete(null);
              setCompleteForm({ actual_premium: '', notes: '' });
              await load();
            } catch (e) { alert(e.message); }
          }} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Actual Premium</label>
                <input type="number" className="input-field w-full text-sm" value={completeForm.actual_premium} onChange={e => setCompleteForm(f => ({ ...f, actual_premium: e.target.value }))} required />
              </div>
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-400">Notes</label>
              <textarea className="input-field w-full text-sm" rows={2} value={completeForm.notes} onChange={e => setCompleteForm(f => ({ ...f, notes: e.target.value }))} />
            </div>
            <div className="flex gap-2">
              <button type="submit" className="btn-primary btn-sm">Complete</button>
              <button type="button" onClick={() => setShowComplete(null)} className="btn-secondary btn-sm">Cancel</button>
            </div>
          </form>
        </div>
      )}

      {materialAdjustments.length > 0 && (
        <div className="glass-card p-5">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
            <AlertTriangle className="h-4 w-4 text-amber-400" /> Material Adjustments Pending Review
          </h3>
          <div className="space-y-2">
            {materialAdjustments.map((adj, i) => (
              <div key={i} className="flex items-center justify-between rounded-lg bg-surface-overlay px-4 py-2">
                <span className="text-xs text-slate-300">{adj.audit_id} — {adj.reason}</span>
                <span className="font-mono text-xs text-amber-400">{adj.amount > 0 ? '+' : ''}{fmtCurrency(adj.amount)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
