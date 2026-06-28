import { useState, useEffect, useCallback } from 'react';
import { TrendingUp, TrendingDown, AlertTriangle, RefreshCw, Shield } from 'lucide-react';
import { StatCard, Badge, EmptyState } from '../components/ui';
import { endpoints } from '../lib/api';

const PHASES = [
  { value: 'hard', label: 'Hard Market', desc: 'Rates rising, capacity tight' },
  { value: 'soft', label: 'Soft Market', desc: 'Rates declining, capacity abundant' },
  { value: 'transitioning_hard', label: 'Transitioning → Hard', desc: 'Market firming up' },
  { value: 'transitioning_soft', label: 'Transitioning → Soft', desc: 'Market softening' },
];

export default function MarketAdmin() {
  const [cycle, setCycle] = useState(null);
  const [loading, setLoading] = useState(true);
  const [setting, setSetting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await endpoints.marketCycle();
      setCycle(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const setPhase = async (phase) => {
    setSetting(true);
    setError('');
    setSuccess('');
    try {
      await endpoints.setMarketCycle(phase);
      setSuccess(`Market phase set to ${PHASES.find(p => p.value === phase)?.label || phase}`);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setSetting(false);
    }
  };

  const phaseColor = cycle?.phase === 'hard' ? 'text-red-400' : cycle?.phase === 'soft' ? 'text-green-400' : 'text-amber-400';
  const direction = cycle?.phase === 'hard' ? 'up' : cycle?.phase === 'soft' ? 'down' : 'stable';

  return (
    <div className="mx-auto max-w-4xl space-y-8 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Market Cycle Admin</h1>
          <p className="mt-1 text-slate-400">Configure insurance market cycle phase and rate adjustments</p>
        </div>
        <button type="button" onClick={load} className="btn-secondary btn-sm text-xs">
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {error && (
        <div className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>
      )}
      {success && (
        <div className="rounded-xl bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">{success}</div>
      )}

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
        </div>
      ) : !cycle ? (
        <EmptyState icon={TrendingUp} title="No market data" description="Market cycle data unavailable" />
      ) : (
        <>
          {/* Current Status Banner */}
          <div className={`glass-card rounded-2xl border p-6 ${cycle.phase === 'hard' ? 'border-red-500/20' : cycle.phase === 'soft' ? 'border-green-500/20' : 'border-amber-500/20'}`}>
            <div className="flex items-center gap-4">
              <div className={`flex h-14 w-14 items-center justify-center rounded-2xl ${direction === 'up' ? 'bg-red-500/15' : direction === 'down' ? 'bg-green-500/15' : 'bg-amber-500/15'}`}>
                {direction === 'up' ? <TrendingUp className={`h-7 w-7 ${phaseColor}`} /> :
                 direction === 'down' ? <TrendingDown className={`h-7 w-7 ${phaseColor}`} /> :
                 <AlertTriangle className="h-7 w-7 text-amber-400" />}
              </div>
              <div>
                <div className={`text-2xl font-bold capitalize ${phaseColor}`}>{cycle.phase} market</div>
                <p className="mt-1 text-sm text-slate-400">{cycle.description}</p>
              </div>
            </div>
          </div>

          {/* Rate Impact Cards */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Property" value={cycle.property_mod} accent="insurance" />
            <StatCard label="Liability" value={cycle.liability_mod} accent="brand" />
            <StatCard label="Workers Comp" value={cycle.workers_comp_mod} sub={cycle.nuclear_verdict_trend === 'rising' ? 'Nuclear verdicts rising' : ''} accent="success" />
            <StatCard label="Auto" value={cycle.auto_mod} accent="mortgage" />
          </div>

          {/* Market Metrics */}
          <div className="glass-card p-6">
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">Market Metrics</h3>
            <div className="grid grid-cols-2 gap-6 md:grid-cols-4">
              {[
                { label: 'Appetite Tightness', value: cycle.appetite_tightness },
                { label: 'Reinsurance Cost', value: cycle.reinsurance_cost_mod },
                { label: 'Industry Loss Ratio', value: cycle.industry_loss_ratio },
                { label: 'Nuclear Verdicts', value: cycle.nuclear_verdict_trend, cap: true },
              ].map((m) => (
                <div key={m.label}>
                  <p className="text-xs font-medium uppercase tracking-wider text-slate-500">{m.label}</p>
                  <p className={`mt-1 text-xl font-bold ${m.cap ? 'capitalize' : ''} ${m.value === 'rising' ? 'text-red-400' : 'text-white'}`}>
                    {m.value}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Phase Selector */}
          <div className="glass-card p-6">
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">Set Market Phase</h3>
            <p className="mb-4 text-sm text-slate-500">Changing the cycle affects pricing, appetite thresholds, and TIV limits across all submissions.</p>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {PHASES.map((p) => (
                <button
                  key={p.value}
                  type="button"
                  disabled={setting || cycle.phase === p.value}
                  onClick={() => setPhase(p.value)}
                  className={`glass-card w-full rounded-xl border p-4 text-left transition hover:border-brand/30 disabled:opacity-50 disabled:cursor-not-allowed ${cycle.phase === p.value ? 'border-brand/40 ring-1 ring-brand/20' : ''}`}
                >
                  <div className="text-sm font-semibold text-white">{p.label}</div>
                  <p className="mt-1 text-xs text-slate-400">{p.desc}</p>
                  {cycle.phase === p.value && (
                    <span className="mt-2 inline-block text-xs font-semibold text-brand-light">Active</span>
                  )}
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
