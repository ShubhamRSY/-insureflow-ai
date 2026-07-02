import { useState, useEffect, useCallback } from 'react';
import { Layers, RefreshCw, Globe, Building2 } from 'lucide-react';
import { StatCard, EmptyState } from '../components/ui';
import { endpoints, fmtCurrency } from '../lib/api';

export default function PortfolioPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const d = await endpoints.portfolioSummary();
      setData(d);
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
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-violet-500/15">
            <Layers className="h-6 w-6 text-violet-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Portfolio</h1>
            <p className="mt-1 text-slate-400">Portfolio concentration analysis and reinsurance treaty tracking</p>
          </div>
        </div>
        <button type="button" onClick={load} className="btn-secondary btn-sm text-xs">
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {error && <div className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
        </div>
      ) : !data ? (
        <EmptyState icon={Layers} title="No portfolio data" description="Portfolio data will appear once policies are bound" />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <StatCard label="Total Policies" value={data.total_policies || 0} accent="brand" />
            <StatCard label="Total Premium" value={fmtCurrency(data.total_premium)} accent="insurance" />
            <StatCard label="Geo Concentration" value={data.geo_concentration?.score || '—'} accent={data.geo_concentration?.score > 70 ? 'success' : 'brand'} />
          </div>

          {data.geo_concentration?.details?.length > 0 && (
            <div className="glass-card p-5">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
                <Globe className="h-4 w-4" /> Geographic Distribution
              </h3>
              <div className="space-y-2">
                {data.geo_concentration.details.map((g, i) => (
                  <div key={i} className="flex items-center justify-between rounded-lg bg-surface-overlay px-4 py-2">
                    <span className="text-sm text-slate-300">{g.state || g.region}</span>
                    <span className="text-xs text-slate-400">{g.count} policies · {g.percentage?.toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {data.industry_concentration?.details?.length > 0 && (
            <div className="glass-card p-5">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
                <Building2 className="h-4 w-4" /> Industry Distribution
              </h3>
              <div className="space-y-2">
                {data.industry_concentration.details.map((ind, i) => (
                  <div key={i} className="flex items-center justify-between rounded-lg bg-surface-overlay px-4 py-2">
                    <span className="text-sm text-slate-300">{ind.industry}</span>
                    <span className="text-xs text-slate-400">{ind.count} policies · {ind.percentage?.toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
