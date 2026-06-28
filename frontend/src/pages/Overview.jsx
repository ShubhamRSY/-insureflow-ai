import { useOutletContext } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Zap, ArrowRight, TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react';
import { StatCard, DemoCard, VerticalExplainer, Badge, EmptyState } from '../components/ui';
import { endpoints } from '../lib/api';

export default function Overview({ overview, health, presets, onRunDemo, onOpenJob, onLogin, marketCycle, queueStats }) {
  const { user } = useOutletContext() || {};

  const chartData = overview ? [
    { name: 'Insurance', completed: overview.insurance?.completed || 0, processing: overview.insurance?.processing || 0, failed: overview.insurance?.failed || 0 },
    { name: 'Mortgage', completed: overview.mortgage?.completed || 0, processing: overview.mortgage?.processing || 0, failed: overview.mortgage?.failed || 0 },
  ] : [];

  const demos = [...(presets?.insurance || []), ...(presets?.mortgage || [])];

  const marketPhase = marketCycle?.phase || null;
  const MarketIcon = marketPhase === 'hard' ? TrendingUp : marketPhase === 'soft' ? TrendingDown : null;
  const marketColor = marketPhase === 'hard' ? 'text-red-400' : marketPhase === 'soft' ? 'text-green-400' : 'text-slate-400';

  return (
    <div className="mx-auto max-w-6xl space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="mt-1 text-slate-400">Autonomous underwriting for insurance carriers and mortgage lenders</p>
      </div>

      {/* Market cycle + Queue stats banner */}
      {(marketCycle || queueStats) && (
        <div className="flex flex-wrap gap-3">
          {marketCycle && (
            <div className={`inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-xs font-medium ring-1 ${marketColor} ring-current/30 bg-surface-overlay`}>
              {MarketIcon && <MarketIcon className="h-3.5 w-3.5" />}
              Market: {marketPhase?.toUpperCase()} — Property {marketCycle.property_mod}, Liability {marketCycle.liability_mod}
              {marketCycle.nuclear_verdict_trend === 'rising' && <AlertTriangle className="ml-1 h-3 w-3 text-red-400" />}
            </div>
          )}
          {queueStats && (
            <div className="inline-flex items-center gap-2 rounded-full bg-surface-overlay px-4 py-1.5 text-xs text-slate-300 ring-1 ring-white/[0.06]">
              Queue: {queueStats.hot_need_review} hot, {queueStats.warm_could_proceed} warm, {queueStats.no_fit_discard} no-fit
            </div>
          )}
        </div>
      )}

      <VerticalExplainer />

      {user && overview ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard label="Insurance Jobs" value={overview.insurance?.total || 0} sub={`${overview.insurance?.completed || 0} completed`} accent="insurance" />
          <StatCard label="Mortgage Jobs" value={overview.mortgage?.total || 0} sub={`${overview.mortgage?.completed || 0} completed`} accent="mortgage" />
          <StatCard label="Pending UW" value={overview.pending_reviews || 0} sub="Licensed sign-off queue" accent="brand" />
          <StatCard label="System" value={health?.overall || '—'} sub={`LLM: ${health?.llm_mode || 'unknown'}`} accent="success" />
        </div>
      ) : (
        <div className="glass-card p-8 text-center">
          <p className="text-slate-300">Sign in to view job metrics and run demos</p>
          <button type="button" onClick={onLogin} className="btn-primary mt-4">Sign In</button>
        </div>
      )}

      {user && chartData.some(d => d.completed + d.processing + d.failed > 0) && (
        <div className="glass-card p-6">
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">Jobs by Vertical</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData} barGap={4}>
              <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 12 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: '#121826', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 12 }} />
              <Bar dataKey="completed" stackId="a" fill="#34d399" radius={[0, 0, 0, 0]} />
              <Bar dataKey="processing" stackId="a" fill="#fbbf24" />
              <Bar dataKey="failed" stackId="a" fill="#f87171" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <div>
          <div className="mb-4 flex items-center gap-2">
            <Zap className="h-4 w-4 text-brand-light" />
            <h3 className="font-semibold">Quick Demos</h3>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {demos.map((d) => (
              <DemoCard
                key={d.id}
                name={d.name}
                description={d.description}
                tag={d.vertical}
                tagColor={d.vertical === 'insurance' ? 'insurance' : 'mortgage'}
                onClick={() => onRunDemo(d.vertical, d.id)}
              />
            ))}
          </div>
        </div>

        <div className="glass-card">
          <div className="border-b border-white/[0.06] px-5 py-4">
            <h3 className="font-semibold">Recent Activity</h3>
          </div>
          <div className="divide-y divide-white/[0.04]">
            {(overview?.recent_jobs || []).slice(0, 8).map((j) => (
              <button
                key={j.job_id}
                type="button"
                onClick={() => onOpenJob(j.vertical, j.job_id)}
                className="flex w-full items-center gap-3 px-5 py-3 text-left transition hover:bg-white/[0.02]"
              >
                <Badge status={j.status} pulse={j.status === 'processing'} />
                <span className="flex-1 truncate font-mono text-xs text-slate-400">{j.job_id}</span>
                <span className="text-xs capitalize text-slate-500">{j.vertical}</span>
                <ArrowRight className="h-3.5 w-3.5 text-slate-600" />
              </button>
            ))}
            {(!overview?.recent_jobs?.length) && (
              <EmptyState title="No jobs yet" description="Run a demo to see activity here" />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
