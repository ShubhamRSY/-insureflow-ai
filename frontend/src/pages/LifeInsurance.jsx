import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { HeartPulse, Shield, Landmark, TrendingUp, Wallet, Coins } from 'lucide-react';
import { endpoints } from '../lib/api';
import { getInsuranceSection } from '../lib/insuranceSections';
import { commercialSelectionLabel, defaultCommercialSelection } from '../lib/commercialTaxonomy';
import RunSelector from '../components/RunSelector';
import SubmissionJobsList from '../components/SubmissionJobsList';

const LIFE_PRODUCTS = [
  { name: 'Level Term Life', hint: 'Pure protection for a fixed period (10, 20, 30 yr)', href: '/insurance/life/level-term', icon: Shield, accent: 'rose' },
  { name: 'Whole Life', hint: 'Lifelong coverage with a guaranteed cash-value component', href: '/insurance/life/traditional-whole-life', icon: Shield, accent: 'rose' },
  { name: 'Endowment Plans', hint: 'Hybrid: life cover + forced maturity savings — high premiums, strict financial UW', href: '/insurance/life/full-with-profit-endowment', icon: Landmark, accent: 'amber' },
  { name: 'ULIPs (Unit-Linked)', hint: 'Market-linked: mortality charge + equity/debt fund investment', href: '/insurance/life/regular-premium-ulip', icon: TrendingUp, accent: 'emerald' },
  { name: 'Money-Back Policies', hint: 'Periodic survival payouts during the term — persistency-focused UW', href: '/insurance/life/traditional-money-back', icon: Wallet, accent: 'sky' },
  { name: 'Annuities & Pension', hint: 'Income after retirement — longevity risk, not mortality risk', href: '/insurance/life/immediate-annuity', icon: Coins, accent: 'violet' },
];

export default function LifeInsuranceHub({ presets, onRunDemo, onSubmit, jobs, onDeleteJob, onDeleteAllJobs }) {
  const [hub, setHub] = useState(null);
  const [error, setError] = useState('');
  const [selection, setSelection] = useState(null);

  useEffect(() => {
    let cancelled = false;
    endpoints.lifeInsuranceHub()
      .then((d) => {
        if (cancelled) return;
        setHub(d);
        setSelection(defaultCommercialSelection(d.taxonomy || []));
      })
      .catch((e) => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, []);

  if (error) {
    return <p className="py-16 text-center text-red-400">{error}</p>;
  }
  if (!hub || !selection) {
    return (
      <div className="flex justify-center py-24">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
      </div>
    );
  }

  const selectionLabel = commercialSelectionLabel(selection);

  return (
    <div className="mx-auto w-full max-w-[1600px] animate-fade-in space-y-6 pb-12">
      <div>
        <nav className="flex items-center gap-1.5 text-xs text-slate-500" aria-label="Breadcrumb">
          <Link to="/insurance" className="transition hover:text-slate-300">Insurance</Link>
          <span className="text-slate-700">/</span>
          <span className="font-semibold text-slate-200">Life Insurance</span>
        </nav>
        <div className="mt-3 flex items-start gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-rose-500/15 text-rose-400">
            <HeartPulse className="h-5 w-5" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight text-slate-100">{hub.title}</h1>
              <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-emerald-400">
                Live
              </span>
            </div>
            <p className="mt-1 max-w-2xl text-sm text-slate-400">{hub.summary}</p>
          </div>
        </div>
      </div>

      {/* Product Families */}
      <section>
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          Product families
        </h2>
        <div className="mt-3 max-h-[260px] space-y-2 overflow-y-auto pr-1">
          {LIFE_PRODUCTS.map((p) => {
            const Icon = p.icon;
            return (
              <Link
                key={p.name}
                to={p.href}
                className="group flex items-center gap-3 rounded-xl border border-white/[0.06] bg-surface-overlay/40 px-4 py-3 transition hover:border-rose-400/25 hover:bg-white/[0.03]"
              >
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-rose-500/15 text-rose-400">
                  <Icon className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-slate-200">{p.name}</p>
                  <p className="mt-0.5 text-xs text-slate-500">{p.hint}</p>
                </div>
                <span className="shrink-0 text-xs text-slate-500 group-hover:text-rose-400 transition">→</span>
              </Link>
            );
          })}
        </div>
      </section>

      <section className="glass-card">
        <div className="border-b border-white/[0.06] px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-100">New submission</h2>
          <p className="mt-0.5 text-sm text-slate-400">
            Choose category → product → coverage, then upload the life package. Medical / financial UW and rating follow automatically.
          </p>
        </div>
        <div className="p-5">
          <RunSelector
            presets={presets}
            vertical="insurance"
            productField="insurance_line"
            commercialTaxonomy={hub.taxonomy}
            commercialSelection={selection}
            onCommercialSelectionChange={setSelection}
            isLifeProductPicker
            onRunDemo={onRunDemo}
            onSubmit={onSubmit}
          />
        </div>
      </section>

      <SubmissionJobsList
        jobs={jobs}
        fallbackLine="Life"
        emptyHint={
          <>
            Upload files above for{' '}
            <span className="text-slate-300">{selectionLabel || 'a life product'}</span>
            {' '}to start.
          </>
        }
        onDeleteJob={onDeleteJob}
        onDeleteAll={onDeleteAllJobs}
      />
    </div>
  );
}
