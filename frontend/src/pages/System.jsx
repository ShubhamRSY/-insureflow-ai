import { Badge } from '../components/ui';

export default function SystemPage({ health }) {
  if (!health) {
    return (
      <div className="flex justify-center py-20">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
      </div>
    );
  }

  const pct = Math.round(((health.summary?.ok || 0) / (health.summary?.total || 1)) * 100);
  const ringColor = { healthy: 'border-emerald-400 text-emerald-400', degraded: 'border-amber-400 text-amber-400', missing: 'border-red-400 text-red-400', error: 'border-red-400 text-red-400' }[health.overall] || 'border-slate-500';

  return (
    <div className="mx-auto max-w-4xl space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">System Health</h1>
        <p className="mt-1 text-slate-400">Environment diagnostics — no secrets exposed</p>
      </div>

      <div className="glass-card flex flex-col items-center gap-6 p-8 sm:flex-row sm:items-start">
        <div className={`flex h-28 w-28 shrink-0 items-center justify-center rounded-full border-4 text-2xl font-bold ${ringColor}`}>
          {pct}%
        </div>
        <div className="flex-1 text-center sm:text-left">
          <h2 className="text-xl font-bold capitalize">{health.overall}</h2>
          <p className="mt-1 text-slate-400">LLM mode: <span className="font-semibold text-brand-light">{health.llm_mode}</span></p>
          <div className="mt-4 flex flex-wrap justify-center gap-2 sm:justify-start">
            <span className="rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-xs font-semibold text-emerald-400">{health.summary?.ok} OK</span>
            <span className="rounded-full bg-amber-500/15 px-2.5 py-0.5 text-xs font-semibold text-amber-400">{health.summary?.degraded} Degraded</span>
            <span className="rounded-full bg-red-500/15 px-2.5 py-0.5 text-xs font-semibold text-red-400">{health.summary?.missing} Missing</span>
          </div>
        </div>
      </div>

      <div className="glass-card divide-y divide-white/[0.04]">
        {(health.checks || []).map((c) => (
          <div key={c.component} className="flex items-start gap-4 px-5 py-4 transition hover:bg-white/[0.02]">
            <span className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${c.status === 'ok' ? 'bg-emerald-400' : c.status === 'degraded' ? 'bg-amber-400' : 'bg-red-400'}`} />
            <div className="min-w-0 flex-1">
              <p className="font-medium">{c.component}</p>
              <p className="mt-0.5 text-sm text-slate-400">{c.message}</p>
            </div>
            <Badge status={c.status} />
          </div>
        ))}
      </div>
    </div>
  );
}
