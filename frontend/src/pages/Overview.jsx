import { useNavigate, useOutletContext } from 'react-router-dom';
import { useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { Zap, ArrowRight, TrendingUp, TrendingDown, AlertTriangle, FlaskConical, Lock, Mail, Eye, Shield, FileText, CheckCircle } from 'lucide-react';
import { StatCard, DemoCard, Badge, EmptyState } from '../components/ui';
import JourneyMiniStrip from '../components/JourneyMiniStrip';
import {
  HeroSection,
  SolutionsSection,
  AutomationsCatalog,
  PlatformStrip,
  UnderwriterPlaybook,
} from '../components/MarketingShowcase';

export default function Overview({ overview, health, presets, onRunDemo, onOpenJob, onLogin, marketCycle, queueStats, insuranceJobs, isLimited, remaining, trackView }) {
  const { user } = useOutletContext() || {};
  const navigate = useNavigate();

  useEffect(() => {
    if (trackView) trackView();
  }, [trackView]);

  const chartData = overview ? [
    { name: 'Insurance', completed: overview.insurance?.completed || 0, processing: overview.insurance?.processing || 0, failed: overview.insurance?.failed || 0 },
    { name: 'Mortgage', completed: overview.mortgage?.completed || 0, processing: overview.mortgage?.processing || 0, failed: overview.mortgage?.failed || 0 },
  ] : [];

  const demos = [...(presets?.insurance || []), ...(presets?.mortgage || []), ...(presets?.lending || [])];

  const marketPhase = marketCycle?.phase || null;
  const MarketIcon = marketPhase === 'hard' ? TrendingUp : marketPhase === 'soft' ? TrendingDown : null;
  const marketColor = marketPhase === 'hard' ? 'text-red-400' : marketPhase === 'soft' ? 'text-green-400' : 'text-slate-400';

  return (
    <div className="animate-fade-in">
      {/* Full-bleed marketing surface inside the app shell */}
      <div className="-mx-6 -mt-6 overflow-hidden lg:-mx-8 lg:-mt-8">
        <HeroSection user={user} onLogin={onLogin} onRunDemo={onRunDemo} presets={presets} />
        <SolutionsSection />
        <UnderwriterPlaybook />
        <AutomationsCatalog />
        <PlatformStrip />
      </div>

      <div className="mx-auto mt-4 max-w-7xl space-y-8 px-6 pb-4 lg:px-8">
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
                Queue: {queueStats.hot_need_review} hot, {queueStats.warm_could_proceed} warm, {queueStats.no_fit_discard ?? queueStats.no_fit} no-fit
              </div>
            )}
          </div>
        )}

        {user && (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            <button
              type="button"
              onClick={() => navigate('/business-kpis')}
              className="group flex items-center justify-between rounded-2xl border border-emerald-500/20 bg-gradient-to-r from-emerald-500/10 to-transparent px-5 py-4 text-left transition hover:border-emerald-500/40"
            >
              <div>
                <p className="font-semibold text-emerald-100">ROI &amp; KPIs</p>
                <p className="text-sm text-slate-400">ROI% = (Net Profit / Cost of Investment) × 100</p>
              </div>
              <ArrowRight className="h-4 w-4 text-emerald-400 transition group-hover:translate-x-0.5" />
            </button>
            <button
              type="button"
              onClick={() => navigate('/line-uw')}
              className="group flex items-center justify-between rounded-2xl border border-sky-500/20 bg-gradient-to-r from-sky-500/10 to-transparent px-5 py-4 text-left transition hover:border-sky-500/40"
            >
              <div>
                <p className="font-semibold text-sky-100">Line UW Desk</p>
                <p className="text-sm text-slate-400">Coverage assist · producer &amp; policyholder service</p>
              </div>
              <ArrowRight className="h-4 w-4 text-sky-400 transition group-hover:translate-x-0.5" />
            </button>
            <button
              type="button"
              onClick={() => navigate('/staff-uw')}
              className="group flex items-center justify-between rounded-2xl border border-violet-500/20 bg-gradient-to-r from-violet-500/10 to-transparent px-5 py-4 text-left transition hover:border-violet-500/40"
            >
              <div>
                <p className="font-semibold text-violet-100">Staff UW Desk</p>
                <p className="text-sm text-slate-400">Guides · rating plans · audits · training</p>
              </div>
              <ArrowRight className="h-4 w-4 text-violet-400 transition group-hover:translate-x-0.5" />
            </button>
          </div>
        )}

        {!user && (
          <div className="rounded-2xl border border-amber-500/20 bg-gradient-to-br from-amber-500/5 via-surface-overlay/50 to-surface-overlay/50 p-8 ring-1 ring-white/[0.06]">
            <div className="flex items-start gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-amber-500/10 ring-1 ring-amber-500/20">
                <Eye className="h-6 w-6 text-amber-400" />
              </div>
              <div className="flex-1">
                <h3 className="font-display text-lg font-semibold text-white">Preview Mode</h3>
                <p className="mt-1 text-sm text-slate-400">
                  You're viewing the platform overview. Sign in to run live demos, view job results, and access all 40+ pages.
                </p>
                <div className="mt-4 grid gap-3 sm:grid-cols-3">
                  <div className="flex items-center gap-2 rounded-lg bg-surface/60 px-3 py-2 ring-1 ring-white/[0.06]">
                    <Shield className="h-4 w-4 text-insurance" />
                    <span className="text-xs text-slate-300">View platform features</span>
                  </div>
                  <div className="flex items-center gap-2 rounded-lg bg-surface/60 px-3 py-2 ring-1 ring-white/[0.06]">
                    <FileText className="h-4 w-4 text-brand-light" />
                    <span className="text-xs text-slate-300">Explore solutions</span>
                  </div>
                  <div className="flex items-center gap-2 rounded-lg bg-surface/60 px-3 py-2 ring-1 ring-white/[0.06]">
                    <CheckCircle className="h-4 w-4 text-emerald-400" />
                    <span className="text-xs text-slate-300">See what's included</span>
                  </div>
                </div>
                <div className="mt-5 flex flex-wrap items-center gap-3">
                  <button type="button" onClick={onLogin} className="btn-primary px-5 py-2.5 text-sm">
                    Sign in for full access
                    <ArrowRight className="h-4 w-4" />
                  </button>
                  <a
                    href="mailto:shubham@ryterainc.com?subject=Rytera%20%E2%80%94%20Full%20Access%20Request"
                    className="inline-flex items-center gap-1.5 rounded-lg bg-amber-500/15 px-4 py-2.5 text-sm font-medium text-amber-200 ring-1 ring-amber-500/25 transition hover:bg-amber-500/25"
                  >
                    <Mail className="h-4 w-4" />
                    Contact us
                  </a>
                </div>
              </div>
            </div>
          </div>
        )}

        {user && (
          <button
            type="button"
            onClick={() => navigate('/pilot')}
            className="group flex w-full items-center justify-between rounded-2xl border border-amber-500/20 bg-gradient-to-r from-amber-500/10 to-transparent px-5 py-4 text-left transition hover:border-amber-500/40"
          >
            <div className="flex items-center gap-3">
              <FlaskConical className="h-5 w-5 text-amber-400" />
              <div>
                <p className="font-semibold text-amber-100">Pilot Lab</p>
                <p className="text-sm text-slate-400">Sandbox readiness · packages · ready-mode bind · calibration</p>
              </div>
            </div>
            <ArrowRight className="h-4 w-4 text-amber-400 transition group-hover:translate-x-0.5" />
          </button>
        )}

        {user && overview ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard label="Insurance Jobs" value={overview.insurance?.total || 0} sub={`${overview.insurance?.completed || 0} completed`} accent="insurance" />
            <StatCard label="Mortgage Jobs" value={overview.mortgage?.total || 0} sub={`${overview.mortgage?.completed || 0} completed`} accent="mortgage" />
            <StatCard label="Pending UW" value={overview.pending_reviews || 0} sub="Licensed sign-off queue" accent="brand" />
            <StatCard label="System" value={health?.overall || '—'} sub={`LLM: ${health?.llm_mode || 'unknown'}`} accent="success" />
          </div>
        ) : !user ? (
          <div className="rounded-2xl bg-surface-overlay/50 p-6 ring-1 ring-white/[0.06]">
            <div className="flex items-center gap-3">
              <Lock className="h-5 w-5 text-amber-400" />
              <div>
                <p className="font-semibold text-slate-200">Sign in to access the full dashboard</p>
                <p className="text-sm text-slate-400">Run live demos, view job metrics, and explore all 40+ pages</p>
              </div>
            </div>
          </div>
        ) : null}

        {user && chartData.some((d) => d.completed + d.processing + d.failed > 0) && (
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
              <h3 className="font-display font-semibold">{user ? 'Quick Demos' : 'What You Can Do'}</h3>
            </div>
            {user ? (
              <div className="grid gap-3 sm:grid-cols-2">
                {demos.map((d) => (
                  <DemoCard
                    key={d.id}
                    name={d.name}
                    description={d.description}
                    tag={d.vertical}
                    tagColor={d.vertical === 'insurance' ? 'insurance' : d.vertical === 'lending' ? 'lending' : 'mortgage'}
                    onClick={() => onRunDemo(d.vertical, d.id)}
                  />
                ))}
              </div>
            ) : (
              <div className="space-y-3">
                {[
                  { icon: Shield, label: 'Run insurance submissions', desc: 'ACORD, loss runs, SOVs, financials — full pipeline' },
                  { icon: FileText, label: 'Generate UW memos', desc: 'AI-written decisions with source citations' },
                  { icon: CheckCircle, label: 'Verify & validate', desc: 'Cross-document reconciliation, conflict detection' },
                ].map((item) => (
                  <div key={item.label} className="flex items-center gap-3 rounded-xl bg-surface/60 px-4 py-3 ring-1 ring-white/[0.06]">
                    <item.icon className="h-5 w-5 shrink-0 text-brand-light" />
                    <div>
                      <p className="text-sm font-medium text-slate-200">{item.label}</p>
                      <p className="text-xs text-slate-500">{item.desc}</p>
                    </div>
                    <Lock className="ml-auto h-3.5 w-3.5 shrink-0 text-slate-600" />
                  </div>
                ))}
                <p className="text-xs text-slate-500">
                  <Lock className="mr-1 inline h-3 w-3" />
                  Sign in or contact us to unlock these features
                </p>
              </div>
            )}
          </div>

          <div className="glass-card">
            <div className="border-b border-white/[0.06] px-5 py-4">
              <h3 className="font-display font-semibold">{user ? 'Recent Activity' : 'Platform Overview'}</h3>
            </div>
            <div className="divide-y divide-white/[0.04]">
              {user ? (
                <>
                  {(overview?.recent_jobs || []).slice(0, 8).map((j) => {
                    const fullJob = insuranceJobs?.find(({ id }) => id === j.job_id)?.job;
                    return (
                      <button
                        key={j.job_id}
                        type="button"
                        onClick={() => onOpenJob(j.vertical, j.job_id)}
                        className="flex w-full items-center gap-3 px-5 py-3 text-left transition hover:bg-white/[0.02]"
                      >
                        <Badge status={j.status} pulse={j.status === 'processing'} />
                        <span className="flex-1 truncate font-mono text-xs text-slate-400">{j.job_id}</span>
                        {j.vertical === 'insurance' && fullJob && (
                          <JourneyMiniStrip job={fullJob} compact />
                        )}
                        <span className="text-xs capitalize text-slate-500">{j.vertical}</span>
                        <ArrowRight className="h-3.5 w-3.5 text-slate-600" />
                      </button>
                    );
                  })}
                  {(!overview?.recent_jobs?.length) && (
                    <EmptyState title="No jobs yet" description="Run a demo to see activity here" />
                  )}
                </>
              ) : (
                <div className="p-5 space-y-3">
                  {[
                    '14-stage pipeline: ingest → extract → verify → decide',
                    'Multi-format: PDF, Excel, XML, scanned docs, emails',
                    'Verbatim source attribution on every field',
                    'Human-in-the-loop checkpoints at every risk level',
                    'WORM audit trail with SHA-256 hash chains',
                  ].map((line) => (
                    <div key={line} className="flex items-start gap-2 text-sm text-slate-400">
                      <CheckCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-500/70" />
                      {line}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
