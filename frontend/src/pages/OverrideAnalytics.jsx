import { useState, useEffect, useCallback } from 'react';
import { LineChart, RefreshCw } from 'lucide-react';
import { EmptyState, Badge } from '../components/ui';
import { endpoints } from '../lib/api';

export default function OverrideAnalyticsPage() {
  const [overrides, setOverrides] = useState([]);
  const [patterns, setPatterns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [o, p] = await Promise.all([
        endpoints.overrideAnalytics().catch(() => ({ overrides: [] })),
        endpoints.overridePatterns().catch(() => ({ patterns: [] })),
      ]);
      setOverrides(o.overrides || []);
      setPatterns(p.patterns || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="mx-auto max-w-6xl space-y-8 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Override Analytics</h1>
          <p className="mt-1 text-slate-400">Structured override capture and pattern detection</p>
        </div>
        <button type="button" onClick={load} className="btn-secondary btn-sm text-xs">
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {error && <div className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}

      {patterns.length > 0 && (
        <div className="glass-card p-5">
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">Detected Patterns</h3>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {patterns.map((p, i) => (
              <div key={i} className="rounded-xl bg-surface-overlay p-4 ring-1 ring-white/[0.04]">
                <p className="text-sm font-medium text-slate-200">{p.pattern_name || p.pattern}</p>
                <p className="mt-1 text-xs text-slate-400">{p.description}</p>
                <p className="mt-2 text-xs text-slate-500">Frequency: {p.frequency || p.count || 'N/A'}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
        </div>
      ) : overrides.length === 0 ? (
        <EmptyState icon={LineChart} title="No overrides recorded" description="Override analytics will populate as UW decisions are captured" />
      ) : (
        <div className="glass-card overflow-hidden">
          <div className="border-b border-white/[0.06] px-5 py-3">
            <h3 className="text-sm font-semibold">Override History</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06] bg-surface-overlay text-left text-xs uppercase tracking-wider text-slate-500">
                  <th className="px-6 py-3">Bundle ID</th>
                  <th className="px-6 py-3">Category</th>
                  <th className="px-6 py-3">Reason</th>
                  <th className="px-6 py-3">Decision</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {overrides.map((o, i) => (
                  <tr key={i} className="hover:bg-white/[0.02]">
                    <td className="px-6 py-3.5 font-mono text-xs text-slate-400">{o.bundle_id}</td>
                    <td className="px-6 py-3.5"><Badge status={o.category || o.override_reason_category} /></td>
                    <td className="px-6 py-3.5 text-slate-400">{o.override_reason || '—'}</td>
                    <td className="px-6 py-3.5"><Badge status={o.action || o.decision} /></td>
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
