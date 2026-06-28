import { useState, useEffect, useCallback } from 'react';
import { Users, Shield, RefreshCw } from 'lucide-react';
import { Badge, EmptyState } from '../components/ui';
import { endpoints, fmtCurrency } from '../lib/api';

export default function AuthorityMatrix() {
  const [matrix, setMatrix] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await endpoints.authorityMatrix();
      setMatrix(data.authorities || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const tierConfig = {
    junior: { label: 'Junior UW', color: 'text-sky-400', ring: 'ring-sky-500/20', bg: 'bg-sky-500/10' },
    senior: { label: 'Senior UW', color: 'text-brand-light', ring: 'ring-brand/20', bg: 'bg-brand/10' },
    cuo: { label: 'Chief UW Officer', color: 'text-purple-400', ring: 'ring-purple-500/20', bg: 'bg-purple-500/10' },
    mga: { label: 'MGA', color: 'text-amber-400', ring: 'ring-amber-500/20', bg: 'bg-amber-500/10' },
  };

  return (
    <div className="mx-auto max-w-6xl space-y-8 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Authority Matrix</h1>
          <p className="mt-1 text-slate-400">Delegation of authority and binding limits</p>
        </div>
        <button type="button" onClick={load} className="btn-secondary btn-sm text-xs">
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {error && (
        <div className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>
      )}

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
        </div>
      ) : matrix.length === 0 ? (
        <EmptyState icon={Users} title="No authority records" description="Configure UW tiers in settings" />
      ) : (
        <>
          {/* Tier Overview Cards */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Object.entries(tierConfig).map(([key, cfg]) => {
              const uws = matrix.filter(a => a.tier === key);
              if (!uws.length) return null;
              return (
                <div key={key} className={`glass-card rounded-xl border ${cfg.ring} p-5`}>
                  <div className={`inline-flex rounded-lg ${cfg.bg} px-2.5 py-1 text-xs font-semibold ${cfg.color}`}>
                    {cfg.label}
                  </div>
                  <p className="mt-3 text-2xl font-bold">{uws.length}</p>
                  <p className="text-xs text-slate-500">underwriters</p>
                </div>
              );
            })}
          </div>

          {/* Detailed Table */}
          <div className="glass-card overflow-hidden">
            <div className="border-b border-white/[0.06] px-5 py-4">
              <h3 className="font-semibold">Binding Authority Details</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/[0.04] text-xs uppercase tracking-wider text-slate-500">
                    <th className="px-5 py-3 text-left">Name</th>
                    <th className="px-5 py-3 text-left">Username</th>
                    <th className="px-5 py-3 text-left">Tier</th>
                    <th className="px-5 py-3 text-right">Max Premium</th>
                    <th className="px-5 py-3 text-right">Max TIV</th>
                    <th className="px-5 py-3 text-right">Aggregate Cap</th>
                    <th className="px-5 py-3 text-center">Co-Sign</th>
                    <th className="px-5 py-3 text-left">License</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  {matrix.map((a) => {
                    const cfg = tierConfig[a.tier] || {};
                    const ba = a.binding_authority || {};
                    return (
                      <tr key={a.username} className="hover:bg-white/[0.02]">
                        <td className="px-5 py-3 font-medium text-white">{a.display_name}</td>
                        <td className="px-5 py-3 font-mono text-xs text-slate-400">{a.username}</td>
                        <td className="px-5 py-3">
                          <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset capitalize ${cfg.color} ${cfg.bg} ${cfg.ring}`}>
                            {a.tier}
                          </span>
                        </td>
                        <td className="px-5 py-3 text-right font-mono">{fmtCurrency(ba.max_premium)}</td>
                        <td className="px-5 py-3 text-right font-mono">{fmtCurrency(ba.max_tiv)}</td>
                        <td className="px-5 py-3 text-right font-mono text-slate-400">{fmtCurrency(ba.max_aggregate_exposure)}</td>
                        <td className="px-5 py-3 text-center">
                          {ba.requires_co_sign ? (
                            <Badge status="Yes" />
                          ) : ba.co_sign_threshold_premium ? (
                            <span className="text-xs text-amber-400">&gt;{fmtCurrency(ba.co_sign_threshold_premium)}</span>
                          ) : (
                            <span className="text-xs text-slate-500">No</span>
                          )}
                        </td>
                        <td className="px-5 py-3 text-xs text-slate-400">{a.license_number || '\u2014'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
