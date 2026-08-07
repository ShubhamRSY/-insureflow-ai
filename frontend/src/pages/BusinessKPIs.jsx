import { useState, useEffect, useCallback } from 'react';
import { Gauge, RefreshCw, Play, CheckCircle2, AlertTriangle, Clock } from 'lucide-react';
import { EmptyState, Badge, StatCard } from '../components/ui';
import { endpoints } from '../lib/api';

const statusBadge = (s) => {
  if (s === 'production_ready') return 'ok';
  if (s === 'lab_partial') return 'pending';
  return 'failed';
};

const fmtValue = (kpi) => {
  if (!kpi || kpi.sample_size === 0) return '—';
  if (kpi.unit === 'seconds_avg') return `${kpi.value}s`;
  if (kpi.unit === 'rate' || kpi.unit === 'stp_rate' || kpi.unit === 'ratio') {
    return `${(Number(kpi.value) * 100).toFixed(1)}%`;
  }
  return String(kpi.value);
};

const KPI_META = [
  { key: 'cycle_time', title: 'Cycle time', hint: 'First-pass pipeline duration' },
  { key: 'override_rate', title: 'Override rate', hint: 'UW changes AI decision' },
  { key: 'bind_rate_after_accept', title: 'Bind rate after Accept', hint: 'Accepts that go in-force' },
  { key: 'loss_ratio', title: 'Loss ratio', hint: 'Claims ÷ earned premium' },
  { key: 'stp_vs_referred', title: 'STP vs referred', hint: 'Straight-through share' },
  { key: 'missing_doc_conflict_catch', title: 'Missing-doc / conflict catch', hint: 'Data-quality catches' },
];

export default function BusinessKPIsPage() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const r = await endpoints.businessKpis();
      setReport(r);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const bootstrap = async () => {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const r = await endpoints.bootstrapBusinessKpis();
      setReport(r);
      const boot = r.bootstrap || {};
      setMessage(
        `Bootstrapped ${boot.scenarios_passed ?? 0}/${boot.scenarios_run ?? 0} labeled scenarios. ${boot.note || ''}`,
      );
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-24">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
      </div>
    );
  }

  const kpis = report?.kpis || {};
  const overall = report?.overall || 'not_ready';

  return (
    <div className="mx-auto max-w-6xl space-y-8 animate-fade-in">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand/15">
            <Gauge className="h-6 w-6 text-brand" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Business KPIs</h1>
            <p className="mt-1 text-slate-400">
              Production scorecard — cycle time, override, bind, loss ratio, STP, catch rate
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={load} className="btn-secondary btn-sm text-xs">
            <RefreshCw className="h-3.5 w-3.5" /> Refresh
          </button>
          <button type="button" onClick={bootstrap} disabled={busy} className="btn-primary btn-sm text-xs">
            <Play className="h-3.5 w-3.5" />
            {busy ? 'Running scenarios…' : 'Bootstrap from labeled scenarios'}
          </button>
        </div>
      </div>

      {error && <div className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}
      {message && <div className="rounded-xl bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">{message}</div>}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Overall"
          value={overall.replace(/_/g, ' ')}
          sub={`${report?.production_ready_count ?? 0}/${report?.total_kpis ?? 6} production-ready`}
          accent="insurance"
        />
        <StatCard
          label="Measured"
          value={`${report?.measured_count ?? 0}/${report?.total_kpis ?? 6}`}
          sub="KPIs with sample size &gt; 0"
        />
        <StatCard
          label="Generated"
          value={report?.generated_at ? new Date(report.generated_at).toLocaleString() : '—'}
          sub={`org ${report?.org_id || '—'}`}
        />
        <StatCard
          label="Target bar"
          value="Pilot brief"
          sub="Override &lt;25% · p95 ≤15m · catch ≥90%"
          accent="success"
        />
      </div>

      {!report ? (
        <EmptyState icon={Gauge} title="No KPI report" description="Refresh or bootstrap labeled scenarios." />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {KPI_META.map(({ key, title, hint }) => {
            const kpi = kpis[key] || {};
            const ready = kpi.status === 'production_ready';
            return (
              <div key={key} className="glass-card p-5 space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-100">{title}</h3>
                    <p className="text-xs text-slate-500">{hint}</p>
                  </div>
                  <Badge status={statusBadge(kpi.status)} label={(kpi.status || 'not_measured').replace(/_/g, ' ')} />
                </div>
                <div className="flex items-end gap-3">
                  <p className="text-3xl font-bold tabular-nums text-white">{fmtValue(kpi)}</p>
                  {kpi.unit === 'seconds_avg' && kpi.p95_seconds != null && (
                    <p className="mb-1 text-xs text-slate-400">p95 {kpi.p95_seconds}s · n={kpi.sample_size}</p>
                  )}
                  {kpi.unit !== 'seconds_avg' && (
                    <p className="mb-1 text-xs text-slate-400">n={kpi.sample_size ?? 0}</p>
                  )}
                </div>
                <p className="text-sm text-slate-300">{kpi.what_to_say}</p>
                <div className="flex items-center gap-2 text-xs text-slate-500">
                  {ready ? (
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                  ) : kpi.sample_size > 0 ? (
                    <Clock className="h-3.5 w-3.5 text-amber-400" />
                  ) : (
                    <AlertTriangle className="h-3.5 w-3.5 text-slate-500" />
                  )}
                  <span>{kpi.target?.label || '—'}</span>
                  {kpi.pass ? <span className="text-emerald-400">· on target</span> : null}
                </div>
                {key === 'stp_vs_referred' && kpi.by_decision && (
                  <p className="text-xs text-slate-500">
                    Mix: STP {kpi.straight_through ?? 0} · refer {kpi.referred ?? 0} · decline {kpi.declined ?? 0}
                  </p>
                )}
                {key === 'cycle_time' && kpi.sample_size > 0 && (
                  <p className="text-xs text-slate-500">
                    min {kpi.min_seconds}s · p50 {kpi.p50_seconds}s · max {kpi.max_seconds}s
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}

      {report?.bootstrap?.note && (
        <div className="rounded-xl border border-slate-500/20 bg-surface-overlay/60 px-4 py-3 text-xs text-slate-400">
          {report.bootstrap.note}
        </div>
      )}
    </div>
  );
}
