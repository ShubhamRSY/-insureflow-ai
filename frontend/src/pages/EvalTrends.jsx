import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Legend,
} from 'recharts';
import { Activity, RefreshCw, Search } from 'lucide-react';
import { EmptyState } from '../components/ui';
import { endpoints } from '../lib/api';

function fmtDay(ts) {
  if (!ts) return '';
  try { return new Date(ts).toISOString().slice(0, 10); } catch { return ts; }
}

export default function EvalTrendsPage() {
  const [data, setData] = useState(null);
  const [explorers, setExplorers] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [trends, logs] = await Promise.all([
        endpoints.evalTrends().catch(() => null),
        endpoints.logExplorers().catch(() => null),
      ]);
      setData(trends);
      setExplorers(logs);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const precisionSeries = useMemo(() => {
    const rows = data?.series?.precision || [];
    const recall = data?.series?.recall || [];
    const byTs = {};
    rows.forEach((r) => { byTs[r.ts] = { day: fmtDay(r.ts), precision: r.value }; });
    recall.forEach((r) => {
      byTs[r.ts] = { ...(byTs[r.ts] || { day: fmtDay(r.ts) }), recall: r.value };
    });
    return Object.values(byTs).sort((a, b) => (a.day || '').localeCompare(b.day || ''));
  }, [data]);

  const halluSeries = useMemo(
    () => (data?.series?.hallucination_rate || []).map((r) => ({ day: fmtDay(r.ts), hallucination: r.value })),
    [data],
  );

  const ragSeries = useMemo(
    () => (data?.series?.ragas_quality_score || []).map((r) => ({ day: fmtDay(r.ts), rag: r.value })),
    [data],
  );

  const agentBars = useMemo(() => {
    const agents = data?.agent_snapshot?.agents || {};
    return Object.entries(agents).map(([name, s]) => ({
      agent: name.replace(/_agent$/, ''),
      error_rate: Number(s.error_rate || 0),
      latency_ms: Number(s.avg_duration_ms || 0),
      findings: Number(s.findings || 0),
    }));
  }, [data]);

  const toSeries = useCallback(
    (key, valueKey = 'value') => (data?.series?.[key] || []).map((r) => ({ day: fmtDay(r.ts), [valueKey]: r.value })),
    [data],
  );

  const benchmarkTtft = useMemo(() => toSeries('time_to_first_token_s', 'ttft'), [toSeries]);
  const benchmarkE2e = useMemo(() => toSeries('e2e_response_time_s', 'e2e'), [toSeries]);
  const benchmarkSpeed = useMemo(() => toSeries('output_speed_tokens_per_s', 'speed'), [toSeries]);
  const benchmarkReasoning = useMemo(() => toSeries('average_reasoning_tokens', 'reasoning'), [toSeries]);

  const latestBench = useMemo(() => {
    const last = (arr) => arr[arr.length - 1];
    return {
      ttft: last(benchmarkTtft)?.ttft,
      e2e: last(benchmarkE2e)?.e2e,
      speed: last(benchmarkSpeed)?.speed,
      reasoning: last(benchmarkReasoning)?.reasoning,
    };
  }, [benchmarkTtft, benchmarkE2e, benchmarkSpeed, benchmarkReasoning]);

  const hasBenchmark = benchmarkTtft.length > 0 || benchmarkE2e.length > 0;

  return (
    <div className="mx-auto max-w-6xl space-y-8 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Eval & Agent Trends</h1>
          <p className="mt-1 text-slate-400">
            Automated log analysis + eval metric trends (CloudWatch Insights + LangSmith explorers)
          </p>
        </div>
        <button type="button" onClick={load} className="btn-secondary btn-sm text-xs">
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {error && <div className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}

      {loading && !data ? (
        <div className="flex justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
        </div>
      ) : !data || data.points === 0 ? (
        <EmptyState icon={Activity} title="No trend points yet" description="Nightly eval / scorer appends trend history automatically" />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="glass-card p-4">
              <p className="text-xs uppercase tracking-wider text-slate-500">Trend points</p>
              <p className="mt-1 text-2xl font-semibold text-slate-100">{data.points}</p>
            </div>
            <div className="glass-card p-4">
              <p className="text-xs uppercase tracking-wider text-slate-500">Avg agent error rate</p>
              <p className="mt-1 text-2xl font-semibold text-slate-100">
                {((data.agent_snapshot?.avg_error_rate || 0) * 100).toFixed(2)}%
              </p>
            </div>
            <div className="glass-card p-4">
              <p className="text-xs uppercase tracking-wider text-slate-500">Avg agent latency</p>
              <p className="mt-1 text-2xl font-semibold text-slate-100">
                {data.agent_snapshot?.avg_latency_ms != null ? `${data.agent_snapshot.avg_latency_ms} ms` : '—'}
              </p>
            </div>
          </div>

          <div className="glass-card p-5">
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">Precision / Recall trend</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={precisionSeries}>
                  <CartesianGrid stroke="rgba(255,255,255,0.06)" />
                  <XAxis dataKey="day" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <YAxis domain={[0.7, 1]} tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155' }} />
                  <Legend />
                  <Line type="monotone" dataKey="precision" stroke="#34d399" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="recall" stroke="#60a5fa" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="glass-card p-5">
              <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">Hallucination rate</h3>
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={halluSeries}>
                    <CartesianGrid stroke="rgba(255,255,255,0.06)" />
                    <XAxis dataKey="day" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                    <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
                    <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155' }} />
                    <Line type="monotone" dataKey="hallucination" stroke="#f87171" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div className="glass-card p-5">
              <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">RAG quality score</h3>
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={ragSeries}>
                    <CartesianGrid stroke="rgba(255,255,255,0.06)" />
                    <XAxis dataKey="day" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                    <YAxis domain={[0.6, 1]} tick={{ fill: '#94a3b8', fontSize: 11 }} />
                    <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155' }} />
                    <Line type="monotone" dataKey="rag" stroke="#a78bfa" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <div className="glass-card p-5">
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">Agent latency (log analysis)</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={agentBars}>
                  <CartesianGrid stroke="rgba(255,255,255,0.06)" />
                  <XAxis dataKey="agent" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155' }} />
                  <Bar dataKey="latency_ms" fill="#38bdf8" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {hasBenchmark && (
            <>
              <div className="glass-card p-5">
                <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
                  Performance &amp; price benchmark (Artificial Analysis)
                </h3>
                <div className="grid gap-4 sm:grid-cols-4">
                  <div className="rounded-xl bg-surface-overlay p-4">
                    <p className="text-xs uppercase tracking-wider text-slate-500">TTFT (avg, s)</p>
                    <p className="mt-1 text-2xl font-semibold text-slate-100">
                      {latestBench.ttft != null ? `${latestBench.ttft.toFixed(2)}` : '—'}
                    </p>
                  </div>
                  <div className="rounded-xl bg-surface-overlay p-4">
                    <p className="text-xs uppercase tracking-wider text-slate-500">E2E response (avg, s)</p>
                    <p className="mt-1 text-2xl font-semibold text-slate-100">
                      {latestBench.e2e != null ? `${latestBench.e2e.toFixed(2)}` : '—'}
                    </p>
                  </div>
                  <div className="rounded-xl bg-surface-overlay p-4">
                    <p className="text-xs uppercase tracking-wider text-slate-500">Output speed (tok/s)</p>
                    <p className="mt-1 text-2xl font-semibold text-slate-100">
                      {latestBench.speed != null ? `${latestBench.speed.toFixed(1)}` : '—'}
                    </p>
                  </div>
                  <div className="rounded-xl bg-surface-overlay p-4">
                    <p className="text-xs uppercase tracking-wider text-slate-500">Reasoning tokens (avg)</p>
                    <p className="mt-1 text-2xl font-semibold text-slate-100">
                      {latestBench.reasoning != null ? latestBench.reasoning.toLocaleString() : '—'}
                    </p>
                  </div>
                </div>
                <div className="mt-4 grid gap-4 lg:grid-cols-2">
                  <div className="h-56">
                    <p className="mb-2 text-xs text-slate-400">TTFT vs E2E response time (s)</p>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={benchmarkTtft.map((r, i) => ({ ...r, e2e: benchmarkE2e[i]?.e2e }))}>
                        <CartesianGrid stroke="rgba(255,255,255,0.06)" />
                        <XAxis dataKey="day" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                        <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} />
                        <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155' }} />
                        <Legend />
                        <Line type="monotone" dataKey="ttft" stroke="#34d399" strokeWidth={2} dot={false} />
                        <Line type="monotone" dataKey="e2e" stroke="#fbbf24" strokeWidth={2} dot={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="h-56">
                    <p className="mb-2 text-xs text-slate-400">Output speed (tok/s) vs reasoning tokens</p>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={benchmarkSpeed.map((r, i) => ({ ...r, reasoning: benchmarkReasoning[i]?.reasoning }))}>
                        <CartesianGrid stroke="rgba(255,255,255,0.06)" />
                        <XAxis dataKey="day" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                        <YAxis yAxisId="left" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                        <YAxis yAxisId="right" orientation="right" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                        <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155' }} />
                        <Legend />
                        <Line yAxisId="left" type="monotone" dataKey="speed" stroke="#60a5fa" strokeWidth={2} dot={false} />
                        <Line yAxisId="right" type="monotone" dataKey="reasoning" stroke="#a78bfa" strokeWidth={2} dot={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            </>
          )}
        </>
      )}

      {explorers && (
        <div className="glass-card p-5">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
            <Search className="h-4 w-4" /> Log explorers
          </h3>
          <p className="mb-4 text-sm text-slate-400">{explorers.automation}</p>
          <div className="grid gap-3 sm:grid-cols-2">
            {(explorers.explorers || []).map((ex) => (
              <a
                key={ex.name}
                href={ex.url}
                target="_blank"
                rel="noreferrer"
                className="rounded-xl bg-surface-overlay p-4 ring-1 ring-white/[0.04] transition hover:ring-white/10"
              >
                <p className="text-sm font-medium text-slate-200">{ex.name}</p>
                <p className="mt-1 text-xs text-slate-400">{ex.role}</p>
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
