import { useState, useEffect, useCallback } from 'react';
import { FileText, TrendingUp, TrendingDown, AlertTriangle, RefreshCw, Search } from 'lucide-react';
import { StatCard, Badge, EmptyState } from '../components/ui';
import { endpoints, fmtCurrency } from '../lib/api';

export default function RenewalDashboard() {
  const [renewals, setRenewals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await endpoints.premiumAudits();
      setRenewals(data.audits || []);
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
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
