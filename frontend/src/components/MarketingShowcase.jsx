import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowRight, FileSearch, HeartPulse, Building2, Home, Wallet,
  ScrollText, ShieldCheck, Layers, Gauge, Sparkles, FileText,
} from 'lucide-react';

const SOLUTIONS = [
  {
    id: 'insurance',
    label: 'Insurance',
    blurb: 'Commercial P&C and personal lines — from broker package to bind-ready memo.',
    path: '/insurance',
    points: ['Loss run & SOV intake', 'COPE / life medical UW', 'Indicated premium & decision'],
  },
  {
    id: 'mortgage',
    label: 'Mortgage',
    blurb: 'Residential and commercial packages with income, collateral, and rate lock checks.',
    path: '/mortgage',
    points: ['W-2 / tax / credit pull', 'Appraisal abstraction', 'GSE / HMDA-aware scoring'],
  },
  {
    id: 'lending',
    label: 'Lending',
    blurb: 'Consumer and commercial credit with pricing, compliance, and adverse action.',
    path: '/lending',
    points: ['Application + bank data', 'Risk-based pricing', 'Decision vocab unified'],
  },
];

const AUTOMATIONS = [
  {
    id: 'loss-run',
    title: 'AI Loss Run Analysis',
    desc: 'Normalize carrier loss runs, flag large / unusual claims, and feed experience rating.',
    icon: FileSearch,
    vertical: 'insurance',
    path: '/insurance',
    demoHint: 'commercial',
  },
  {
    id: 'life-medical',
    title: 'AI Life Medical UW',
    desc: 'Paramed / APS-aware classing, tobacco, face amount, and filing-grade life rating.',
    icon: HeartPulse,
    vertical: 'insurance',
    path: '/insurance',
    demoHint: 'life',
  },
  {
    id: 'cope',
    title: 'AI COPE Property Rating',
    desc: 'Construction, occupancy, protection, and exposure schedule mods with evidence.',
    icon: Building2,
    vertical: 'insurance',
    path: '/insurance',
    demoHint: 'property',
  },
  {
    id: 'acord',
    title: 'AI ACORD Extraction',
    desc: 'Classify and extract ACORD / broker packages with provenance and reconciliation.',
    icon: ScrollText,
    vertical: 'insurance',
    path: '/insurance',
  },
  {
    id: 'memo',
    title: 'AI Underwriting Memo',
    desc: 'Generate a coherent UW memo — decision, summary, and conditions stay in sync.',
    icon: FileText,
    vertical: 'insurance',
    path: '/insurance',
  },
  {
    id: 'mortgage-pkg',
    title: 'AI Mortgage Package',
    desc: 'Abstract appraisals, income docs, and credit into a lender-ready risk view.',
    icon: Home,
    vertical: 'mortgage',
    path: '/mortgage',
  },
  {
    id: 'lending-decision',
    title: 'AI Credit Decision',
    desc: 'Score applications, price risk, and emit compliant adverse-action narratives.',
    icon: Wallet,
    vertical: 'lending',
    path: '/lending',
  },
  {
    id: 'triage',
    title: 'AI Appetite Triage',
    desc: 'LOB-aware package checklists and priority scoring before expensive processing.',
    icon: Gauge,
    vertical: 'insurance',
    path: '/queue',
  },
  {
    id: 'portfolio',
    title: 'AI Portfolio Guardrails',
    desc: 'Concentration, treaty fit, and authority checks before you bind exposure.',
    icon: Layers,
    vertical: 'insurance',
    path: '/portfolio',
  },
  {
    id: 'audit',
    title: 'AI Audit & Provenance',
    desc: 'Field-level trust, encrypted trails, and human checkpoints for examiners.',
    icon: ShieldCheck,
    vertical: 'insurance',
    path: '/system',
  },
];

const VERT_COLOR = {
  insurance: 'text-insurance',
  mortgage: 'text-mortgage',
  lending: 'text-lending',
};

function PipelineViz() {
  const steps = ['Ingest', 'Extract', 'Verify', 'Score', 'Price', 'Decide'];
  return (
    <div className="relative mt-10 w-full max-w-3xl" aria-hidden>
      <div className="absolute inset-x-8 top-1/2 h-px -translate-y-1/2 bg-gradient-to-r from-transparent via-brand/50 to-transparent" />
      <div className="relative flex justify-between gap-2">
        {steps.map((label, i) => (
          <div
            key={label}
            className="animate-float flex flex-col items-center"
            style={{ animationDelay: `${i * 0.12}s` }}
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-surface-raised ring-1 ring-brand/30 shadow-glow">
              <span className="font-display text-xs font-bold text-brand-light">{String(i + 1).padStart(2, '0')}</span>
            </div>
            <span className="mt-2 text-[10px] font-semibold uppercase tracking-wider text-slate-400">{label}</span>
          </div>
        ))}
      </div>
      <p className="mt-6 text-center text-xs text-slate-500">
        Live pipeline · hundreds of documents in parallel · every field cited
      </p>
    </div>
  );
}

export function HeroSection({ user, onLogin, onRunDemo, presets }) {
  const navigate = useNavigate();
  const firstDemo = presets?.insurance?.[0];

  const primary = () => {
    if (user) {
      if (firstDemo && onRunDemo) onRunDemo('insurance', firstDemo.id);
      else navigate('/insurance');
      return;
    }
    onLogin?.();
  };

  return (
    <section className="relative overflow-hidden rounded-none border-b border-white/[0.06] bg-hero-glow px-6 pb-16 pt-10 lg:px-12 lg:pb-20 lg:pt-14">
      <div className="pointer-events-none absolute -right-24 top-0 h-[420px] w-[420px] rounded-full bg-insurance/10 blur-3xl animate-pulse-soft" />
      <div className="pointer-events-none absolute -left-16 bottom-0 h-[280px] w-[280px] rounded-full bg-brand/15 blur-3xl" />

      <p className="font-display text-5xl font-bold tracking-tight text-white sm:text-6xl lg:text-7xl animate-fade-in">
        Rytera
      </p>
      <h2 className="mt-4 max-w-2xl font-display text-2xl font-semibold leading-snug tracking-tight text-slate-100 sm:text-3xl animate-slide-up">
        Automate document-heavy underwriting with AI
      </h2>
      <p className="mt-4 max-w-xl text-base leading-relaxed text-slate-400 animate-slide-up" style={{ animationDelay: '0.08s' }}>
        Turn insurance, mortgage, and lending packages into verified decisions — accurate, auditable, and under your control.
      </p>

      <div className="mt-8 flex flex-wrap items-center gap-3 animate-slide-up" style={{ animationDelay: '0.16s' }}>
        <button type="button" onClick={primary} className="btn-primary px-5 py-3 text-sm">
          {user ? 'Run a live demo' : 'Sign in to try it'}
          <ArrowRight className="h-4 w-4" />
        </button>
        <button type="button" onClick={() => navigate('/insurance')} className="btn-secondary px-5 py-3 text-sm">
          Explore insurance
        </button>
      </div>

      <div className="mt-8 flex flex-wrap gap-4 text-[11px] font-semibold uppercase tracking-widest text-slate-500 animate-fade-in" style={{ animationDelay: '0.24s' }}>
        <span className="ring-1 ring-white/10 rounded-md px-2.5 py-1">SOC-ready audit</span>
        <span className="ring-1 ring-white/10 rounded-md px-2.5 py-1">Encrypted at rest</span>
        <span className="ring-1 ring-white/10 rounded-md px-2.5 py-1">Human checkpoints</span>
      </div>

      <PipelineViz />
    </section>
  );
}

export function SolutionsSection() {
  const [active, setActive] = useState('insurance');
  const navigate = useNavigate();
  const sol = SOLUTIONS.find((s) => s.id === active) || SOLUTIONS[0];

  return (
    <section className="px-6 py-14 lg:px-12">
      <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-brand-light">Solutions</p>
      <h3 className="mt-2 font-display text-2xl font-semibold tracking-tight text-white sm:text-3xl">
        Tailored for your workflows
      </h3>
      <p className="mt-2 max-w-2xl text-sm text-slate-400">
        Specialized agents for every vertical — same platform, same audit trail.
      </p>

      <div className="mt-8 flex flex-wrap gap-2">
        {SOLUTIONS.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => setActive(s.id)}
            className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
              active === s.id
                ? 'bg-brand/20 text-brand-light ring-1 ring-brand/40'
                : 'bg-surface-overlay text-slate-400 ring-1 ring-white/[0.06] hover:text-slate-200'
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      <div className="mt-6 grid gap-8 lg:grid-cols-[1.2fr_1fr] lg:items-end">
        <div>
          <h4 className={`font-display text-xl font-semibold ${VERT_COLOR[sol.id] || 'text-white'}`}>{sol.label}</h4>
          <p className="mt-2 text-sm leading-relaxed text-slate-400">{sol.blurb}</p>
          <ul className="mt-4 space-y-2">
            {sol.points.map((p) => (
              <li key={p} className="flex items-start gap-2 text-sm text-slate-300">
                <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-brand-light" />
                {p}
              </li>
            ))}
          </ul>
          <button type="button" onClick={() => navigate(sol.path)} className="btn-primary mt-6 text-sm">
            Open {sol.label} <ArrowRight className="h-4 w-4" />
          </button>
        </div>
        <div className="relative overflow-hidden rounded-2xl bg-surface-overlay/80 p-6 ring-1 ring-white/[0.06]">
          <div className="absolute inset-0 bg-gradient-to-br from-brand/10 via-transparent to-insurance/10" />
          <p className="relative text-[10px] font-bold uppercase tracking-widest text-slate-500">Workflow snapshot</p>
          <ol className="relative mt-4 space-y-3">
            {['Pull package from broker / LOS', 'Extract & reconcile fields', 'Apply appetite + rating logic', 'Emit memo, quote, or decision'].map((step, i) => (
              <li key={step} className="flex items-center gap-3 text-sm text-slate-300">
                <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-surface-raised font-mono text-[10px] text-brand-light ring-1 ring-white/10">
                  {String(i + 1).padStart(2, '0')}
                </span>
                {step}
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}

export function AutomationsCatalog({ filterVertical }) {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [tab, setTab] = useState(filterVertical || 'all');

  const items = useMemo(() => {
    const q = query.trim().toLowerCase();
    return AUTOMATIONS.filter((a) => {
      if (tab !== 'all' && a.vertical !== tab) return false;
      if (!q) return true;
      return `${a.title} ${a.desc}`.toLowerCase().includes(q);
    });
  }, [query, tab]);

  return (
    <section className="border-t border-white/[0.06] bg-surface-raised/40 px-6 py-14 lg:px-12">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-brand-light">Free AI automations</p>
          <h3 className="mt-2 font-display text-2xl font-semibold tracking-tight text-white sm:text-3xl">
            Ready-to-run underwriting agents
          </h3>
          <p className="mt-2 max-w-xl text-sm text-slate-400">
            Pick an automation, point it at your package, and watch the full journey — no black box.
          </p>
        </div>
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search: loss run, life, mortgage…"
          className="input-field max-w-xs text-sm"
          aria-label="Search automations"
        />
      </div>

      <div className="mt-6 flex flex-wrap gap-2">
        {['all', 'insurance', 'mortgage', 'lending'].map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold capitalize transition ${
              tab === t ? 'bg-white/10 text-white' : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            {t === 'all' ? 'All' : t}
          </button>
        ))}
      </div>

      <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {items.map((a, i) => {
          const Icon = a.icon;
          return (
            <button
              key={a.id}
              type="button"
              onClick={() => navigate(a.path)}
              className="group relative overflow-hidden rounded-2xl bg-surface/60 p-5 text-left ring-1 ring-white/[0.06] transition hover:ring-brand/35 hover:shadow-glow animate-slide-up"
              style={{ animationDelay: `${Math.min(i, 8) * 0.04}s` }}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand/10 ring-1 ring-brand/20">
                  <Icon className="h-5 w-5 text-brand-light" />
                </div>
                <span className={`text-[10px] font-bold uppercase tracking-wider ${VERT_COLOR[a.vertical]}`}>
                  {a.vertical}
                </span>
              </div>
              <h4 className="mt-4 font-display text-base font-semibold text-white group-hover:text-brand-light transition">
                {a.title}
              </h4>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">{a.desc}</p>
              <span className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-brand-light opacity-0 transition group-hover:opacity-100">
                Launch <ArrowRight className="h-3 w-3" />
              </span>
            </button>
          );
        })}
        {!items.length && (
          <p className="col-span-full text-sm text-slate-500">No automations match that search.</p>
        )}
      </div>
    </section>
  );
}

export function PlatformStrip() {
  const pillars = [
    { title: 'Minutes, not weeks', body: 'Ingest, extract, verify, and decide in one visible pipeline.' },
    { title: 'Cited & controllable', body: 'Provenance on every field. Human checkpoints when risk rises.' },
    { title: 'LOB-native', body: 'Life medical, COPE property, mortgage packages — not one generic checklist.' },
  ];
  return (
    <section className="px-6 py-12 lg:px-12">
      <div className="grid gap-8 md:grid-cols-3">
        {pillars.map((p) => (
          <div key={p.title}>
            <h4 className="font-display text-lg font-semibold text-white">{p.title}</h4>
            <p className="mt-2 text-sm leading-relaxed text-slate-400">{p.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
