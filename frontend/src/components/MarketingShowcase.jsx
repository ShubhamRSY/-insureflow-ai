import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { gsap, SplitText, useGSAP, withMotion } from '../lib/motion';
import {
  ArrowRight, FileSearch, HeartPulse, Building2, Home, Wallet,
  ScrollText, ShieldCheck, Layers, Gauge, Check, FileText, Briefcase,
  ClipboardCheck, BadgeCheck, FolderOpen, Route, Repeat, TrendingUp, HandCoins,
} from 'lucide-react';
import { endpoints } from '../lib/api';

const UW_RESPONSIBILITY_ICONS = {
  risk_assessment: Gauge,
  pricing: HandCoins,
  terms: ClipboardCheck,
  decision: BadgeCheck,
  portfolio: Layers,
  monitoring: Repeat,
};

const SOLUTIONS = [
  {
    id: 'insurance',
    label: 'Insurance',
    blurb: 'All insurance lines — life, health, personal, commercial, specialty — from broker package to bind-ready memo.',
    path: '/insurance',
    points: ['Loss run & SOV intake', 'Financials & floor-plan review', 'COPE / life medical UW', 'Indicated premium & decision'],
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
    title: 'Loss Run Analysis',
    desc: 'Normalize carrier loss runs, flag large / unusual claims, and feed experience rating.',
    icon: FileSearch,
    vertical: 'insurance',
    path: '/insurance',
    demoHint: 'commercial',
  },
  {
    id: 'life-medical',
    title: 'Life Medical UW',
    desc: 'Paramed / APS-aware classing, tobacco, face amount, and filing-grade life rating.',
    icon: HeartPulse,
    vertical: 'insurance',
    path: '/insurance',
    demoHint: 'life',
  },
  {
    id: 'cope',
    title: 'COPE Property Rating',
    desc: 'Construction, occupancy, protection, and exposure schedule mods with evidence.',
    icon: Building2,
    vertical: 'insurance',
    path: '/insurance',
    demoHint: 'property',
  },
  {
    id: 'acord',
    title: 'ACORD Extraction',
    desc: 'Classify ACORD 125/126/130/140 packages and extract every field with provenance.',
    icon: ScrollText,
    vertical: 'insurance',
    path: '/insurance',
  },
  {
    id: 'financial',
    title: 'Financial Statement Review',
    desc: 'Parse balance sheets, income statements, and tax returns into a 16-line financial-condition read.',
    icon: Wallet,
    vertical: 'insurance',
    path: '/insurance',
  },
  {
    id: 'floor-plan',
    title: 'Floor Plan & Schematic Review',
    desc: 'Extract area, stories, fire compartments, exits, and sprinkler protection from drawings.',
    icon: Building2,
    vertical: 'insurance',
    path: '/insurance',
  },
  {
    id: 'oracles',
    title: 'Oracle Verification',
    desc: 'Cross-check CLUE, NCCI, credit bureau, OSHA, and public-record feeds before you bind.',
    icon: Gauge,
    vertical: 'insurance',
    path: '/insurance',
  },
  {
    id: 'memo',
    title: 'Underwriting Memo',
    desc: 'Generate a coherent UW memo — decision, summary, and conditions stay in sync.',
    icon: FileText,
    vertical: 'insurance',
    path: '/insurance',
  },
  {
    id: 'mortgage-pkg',
    title: 'Mortgage Package',
    desc: 'Abstract appraisals, income docs, and credit into a lender-ready risk view.',
    icon: Home,
    vertical: 'mortgage',
    path: '/mortgage',
  },
  {
    id: 'lending-decision',
    title: 'Credit Decision',
    desc: 'Score applications, price risk, and emit compliant adverse-action narratives.',
    icon: Wallet,
    vertical: 'lending',
    path: '/lending',
  },
  {
    id: 'triage',
    title: 'Appetite Triage',
    desc: 'LOB-aware package checklists and priority scoring before expensive processing.',
    icon: Gauge,
    vertical: 'insurance',
    path: '/queue',
  },
  {
    id: 'portfolio',
    title: 'Portfolio Guardrails',
    desc: 'Concentration, treaty fit, and authority checks before you bind exposure.',
    icon: Layers,
    vertical: 'insurance',
    path: '/portfolio',
  },
  {
    id: 'audit',
    title: 'Audit & Provenance',
    desc: 'Field-level trust, encrypted trails, and human checkpoints for examiners.',
    icon: ShieldCheck,
    vertical: 'insurance',
    path: '/system',
  },
  {
    id: 'line-uw',
    title: 'Line UW Desk',
    desc: 'Coverage assist, producer & policyholder service — branch underwriting process.',
    icon: Briefcase,
    vertical: 'insurance',
    path: '/line-uw',
  },
  {
    id: 'staff-uw',
    title: 'Staff UW Desk',
    desc: 'Guides, rating plans, market research, UW audits, and line UW training.',
    icon: Building2,
    vertical: 'insurance',
    path: '/staff-uw',
  },
];

// Section headings marked data-kinetic rise in word by word as they scroll
// into view. Cards stay put: one orchestrated moment (the hero) is enough.
function useScrollReveal(scope, dependencies = []) {
  useGSAP(() => withMotion(() => {
    scope.current.querySelectorAll('[data-kinetic]').forEach((el) => {
      const split = SplitText.create(el, { type: 'words', mask: 'words' });
      gsap.from(split.words, {
        yPercent: 110, duration: 0.8, ease: 'power4.out', stagger: 0.05,
        onComplete: () => split.revert(), // masks clip descenders; restore plain text
        scrollTrigger: { trigger: el, start: 'top 85%', once: true },
      });
    });
  }), { scope, dependencies, revertOnUpdate: true });
}

function Container({ className = '', children }) {
  return <div className={`mx-auto w-full max-w-7xl px-6 lg:px-8 ${className}`}>{children}</div>;
}

function PipelineViz() {
  const steps = ['Ingest', 'Extract', 'Verify', 'Score', 'Price', 'Decide'];
  return (
    <div className="relative mt-10 w-full max-w-3xl" aria-hidden>
      <div data-pipe-line className="absolute inset-x-8 top-5 h-px origin-left bg-brand/40" />
      <div className="relative flex justify-between gap-2">
        {steps.map((label, i) => (
          <div key={label} className="flex flex-col items-center">
            <div data-pipe-step className="flex h-10 w-10 items-center justify-center rounded-full bg-surface-raised ring-1 ring-brand/40">
              <span className="font-display text-xs font-bold text-brand-light">{String(i + 1).padStart(2, '0')}</span>
            </div>
            <span className="mt-2 text-xs font-medium text-slate-400">{label}</span>
          </div>
        ))}
      </div>
      <p data-hero-fade className="mt-6 text-center text-xs text-slate-500">
        Hundreds of documents run in parallel, from intake to decision.
      </p>
    </div>
  );
}

export function HeroSection({ user, onLogin, onRunDemo, presets }) {
  const navigate = useNavigate();
  const firstDemo = presets?.insurance?.[0];
  const scope = useRef(null);

  useGSAP(() => withMotion(() => {
    const q = gsap.utils.selector(scope);
    const brand = SplitText.create(q('[data-hero-brand]'), { type: 'chars', mask: 'chars' });
    const head = SplitText.create(q('[data-hero-head]'), { type: 'words', mask: 'words' });
    // Give the masks room below the baseline so descenders aren't clipped mid-animation.
    gsap.set([...brand.masks, ...head.masks], { paddingBottom: '0.2em', marginBottom: '-0.2em' });
    // Masks clip descenders (the "y"), so restore plain text once the intro lands.
    gsap.timeline({ defaults: { ease: 'power4.out' }, onComplete: () => { brand.revert(); head.revert(); } })
      .from(brand.chars, { yPercent: 120, rotate: 6, duration: 1.1, stagger: 0.05 })
      .from(head.words, { yPercent: 110, duration: 0.8, stagger: 0.04 }, '-=0.7')
      .from(q('[data-hero-fade]'), { y: 16, autoAlpha: 0, duration: 0.6, stagger: 0.08, ease: 'power3.out' }, '-=0.5')
      .from(q('[data-pipe-line]'), { scaleX: 0, duration: 1, ease: 'power2.inOut' }, '-=0.6')
      .from(q('[data-pipe-step]'), { scale: 0.4, autoAlpha: 0, duration: 0.5, stagger: 0.08, ease: 'back.out(2)' }, '<0.1');
  }), { scope });

  const primary = () => {
    if (user) {
      if (firstDemo && onRunDemo) onRunDemo('insurance', firstDemo.id);
      else navigate('/insurance');
      return;
    }
    onLogin?.();
  };

  return (
    <section ref={scope} className="relative overflow-hidden border-b border-white/[0.06] bg-hero-glow pb-16 pt-12 lg:pb-20 lg:pt-16">
      <Container>
        <p data-hero-brand className="font-display text-5xl font-bold tracking-tight text-white sm:text-6xl lg:text-7xl">
          Rytera
        </p>
        <h2 data-hero-head className="mt-4 max-w-2xl font-display text-2xl font-semibold leading-snug tracking-tight text-slate-100 sm:text-3xl">
          Automate document-heavy underwriting with AI
        </h2>
        <p data-hero-fade className="mt-4 max-w-xl text-base leading-relaxed text-slate-400">
          Turn insurance, mortgage, and lending packages into verified decisions — for line underwriters on the branch desk and staff underwriters at the home office.
        </p>

        <div data-hero-fade className="mt-8 flex flex-wrap items-center gap-3">
          <button type="button" onClick={primary} className="btn-primary px-5 py-3 text-sm">
            {user ? 'Run a live demo' : 'Sign in to try it'}
            <ArrowRight className="h-4 w-4" />
          </button>
          <button type="button" onClick={() => navigate('/insurance')} className="btn-secondary px-5 py-3 text-sm">
            Explore insurance
          </button>
        </div>

        <p data-hero-fade className="mt-6 flex max-w-xl items-start gap-2 text-sm text-slate-500">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-verdigris" />
          Every field cites its source, risky files stop for a human, and every record is encrypted at rest.
        </p>

        <PipelineViz />
      </Container>
    </section>
  );
}

export function SolutionsSection() {
  const [active, setActive] = useState('insurance');
  const navigate = useNavigate();
  const sol = SOLUTIONS.find((s) => s.id === active) || SOLUTIONS[0];
  const scope = useRef(null);
  const panel = useRef(null);
  useScrollReveal(scope);

  // Crossfade the detail column when the tab changes.
  useGSAP(() => withMotion(() => {
    gsap.from(panel.current.children, { y: 12, autoAlpha: 0, duration: 0.45, ease: 'power2.out', stagger: 0.05 });
  }), { dependencies: [active], scope: panel });

  return (
    <section ref={scope} className="py-14 lg:py-20">
      <Container>
        <h3 data-kinetic className="font-display text-2xl font-semibold tracking-tight text-white sm:text-3xl">
          Three kinds of underwriting, one pipeline
        </h3>
        <p className="mt-2 max-w-2xl text-sm text-slate-400">
          Insurance, mortgage, and lending packages share the same extraction, checks, and audit trail.
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

        <div className="mt-8 grid gap-8 lg:grid-cols-[1.2fr_1fr] lg:items-center">
          <div ref={panel}>
            <h4 className="font-display text-xl font-semibold text-white">{sol.label}</h4>
            <p className="mt-2 text-sm leading-relaxed text-slate-400">{sol.blurb}</p>
            <ul className="mt-4 space-y-2">
              {sol.points.map((p) => (
                <li key={p} className="flex items-start gap-2 text-sm text-slate-300">
                  <Check className="mt-0.5 h-4 w-4 shrink-0 text-verdigris" />
                  {p}
                </li>
              ))}
            </ul>
            <button type="button" onClick={() => navigate(sol.path)} className="btn-primary mt-6 text-sm">
              Open {sol.label} <ArrowRight className="h-4 w-4" />
            </button>
          </div>
          <div className="rounded-2xl bg-surface-overlay/60 p-6 ring-1 ring-white/[0.06]">
            <p className="text-sm font-medium text-slate-300">How a package moves through</p>
            <ol className="mt-4 space-y-3">
              {['Pull package from broker / LOS', 'Extract & reconcile fields', 'Apply appetite + rating logic', 'Emit memo, quote, or decision'].map((step, i) => (
                <li key={step} className="flex items-center gap-3 text-sm text-slate-300">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full font-display text-sm font-semibold text-brand-light ring-1 ring-brand/40">
                    {i + 1}
                  </span>
                  {step}
                </li>
              ))}
            </ol>
          </div>
        </div>
      </Container>
    </section>
  );
}

export function UnderwriterPlaybook() {
  const navigate = useNavigate();
  const [hub, setHub] = useState(null);
  const scope = useRef(null);
  useScrollReveal(scope, [hub]);

  useEffect(() => {
    let cancelled = false;
    endpoints.commercialInsuranceHub()
      .then((d) => { if (!cancelled) setHub(d); })
      .catch(() => { /* non-critical marketing content */ });
    return () => { cancelled = true; };
  }, []);

  const LOB_ICONS = {
    property_bi: Building2,
    directors_officers: Briefcase,
    workers_comp: HeartPulse,
    trade_credit: FileSearch,
    errors_omissions: ScrollText,
    key_person: BadgeCheck,
  };

  return (
    <section ref={scope} className="border-t border-white/[0.06] py-14 lg:py-20">
      <Container>
        <h3 data-kinetic className="font-display text-2xl font-semibold tracking-tight text-white sm:text-3xl">
          What the commercial underwriter does
        </h3>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-400">
          {hub?.summary || 'Decide whether to offer coverage, on what terms, and at what price — the risk evaluator between the applicant and the carrier\u2019s balance sheet.'}
        </p>

        {(hub?.uw_responsibilities || []).length > 0 && (
          <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {hub.uw_responsibilities.map((r) => {
              const Icon = UW_RESPONSIBILITY_ICONS[r.id] || Gauge;
              return (
                <div key={r.id} className="rounded-2xl bg-surface/60 p-5 ring-1 ring-white/[0.06]">
                  <Icon className="h-5 w-5 text-brand-light" />
                  <h4 className="mt-3 font-display text-base font-semibold text-white">{r.title}</h4>
                  <p className="mt-1.5 text-sm leading-relaxed text-slate-400">{r.summary}</p>
                </div>
              );
            })}
          </div>
        )}

        {(hub?.base_packet || []).length > 0 && (
          <div className="mt-8 rounded-2xl bg-surface-overlay/60 p-6 ring-1 ring-white/[0.06]">
            <p className="flex items-center gap-2 text-sm font-medium text-slate-300">
              <FolderOpen className="h-4 w-4 text-brand-light" /> Documents almost every line asks for
            </p>
            <ul className="mt-4 grid gap-2 sm:grid-cols-2">
              {hub.base_packet.map((item) => (
                <li key={item} className="flex gap-2 text-sm text-slate-300">
                  <span className="text-brand-light">•</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}

        {(hub?.lines || []).length > 0 && (
          <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {hub.lines.map((line) => {
              const Icon = LOB_ICONS[line.id] || FileText;
              return (
                <div key={line.id} className="rounded-2xl bg-surface/60 p-5 ring-1 ring-white/[0.06]">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand/10 text-brand-light">
                      <Icon className="h-5 w-5" />
                    </div>
                    <div>
                      <h4 className="font-display text-base font-semibold text-white">{line.name}</h4>
                      <p className="text-xs text-slate-500">{line.document_count} required documents</p>
                    </div>
                  </div>
                  <p className="mt-3 text-sm leading-relaxed text-slate-400">{line.description}</p>
                  {(line.acord_forms || []).length > 0 && (
                    <p className="mt-3 text-xs text-slate-500">{line.acord_forms.join(' · ')}</p>
                  )}
                </div>
              );
            })}
          </div>
        )}

        <div className="mt-8 flex flex-wrap items-center gap-3">
          <button type="button" onClick={() => navigate('/insurance/commercial')} className="btn-primary text-sm">
            Run a commercial submission <ArrowRight className="h-4 w-4" />
          </button>
          <button type="button" onClick={() => navigate('/insurance')} className="btn-secondary text-sm">
            Insurance overview
          </button>
        </div>
      </Container>
    </section>
  );
}

export function AutomationsCatalog({ filterVertical }) {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [tab, setTab] = useState(filterVertical || 'all');
  const scope = useRef(null);
  useScrollReveal(scope);

  const items = useMemo(() => {
    const q = query.trim().toLowerCase();
    return AUTOMATIONS.filter((a) => {
      if (tab !== 'all' && a.vertical !== tab) return false;
      if (!q) return true;
      return `${a.title} ${a.desc}`.toLowerCase().includes(q);
    });
  }, [query, tab]);

  return (
    <section ref={scope} className="border-t border-white/[0.06] bg-surface-raised/40 py-14 lg:py-20">
      <Container>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h3 data-kinetic className="font-display text-2xl font-semibold tracking-tight text-white sm:text-3xl">
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
            placeholder="Search: loss run, floor plan, financials…"
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

        <ul className="mt-6 grid gap-x-10 sm:grid-cols-2">
          {items.map((a) => {
            const Icon = a.icon;
            return (
              <li key={a.id} className="border-t border-white/[0.06]">
                <button
                  type="button"
                  onClick={() => navigate(a.path)}
                  className="group flex w-full items-start gap-4 py-4 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/50"
                >
                  <Icon className="mt-0.5 h-5 w-5 shrink-0 text-brand-light" />
                  <span className="min-w-0 flex-1">
                    <span className="flex items-baseline justify-between gap-3">
                      <span className="font-display text-base font-semibold text-white transition group-hover:text-brand-light">{a.title}</span>
                      <span className="shrink-0 text-xs capitalize text-slate-500">{a.vertical}</span>
                    </span>
                    <span className="mt-1 block text-sm leading-relaxed text-slate-400">{a.desc}</span>
                  </span>
                  <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-slate-600 transition group-hover:translate-x-0.5 group-hover:text-brand-light" />
                </button>
              </li>
            );
          })}
          {!items.length && (
            <li className="col-span-full border-t border-white/[0.06] py-4 text-sm text-slate-500">
              No automations match that search. Try a document type, like "loss run".
            </li>
          )}
        </ul>
      </Container>
    </section>
  );
}

export function PlatformStrip() {
  const pillars = [
    { title: 'Minutes, not weeks', body: 'Ingest, extract, verify, and decide in one visible pipeline.' },
    { title: 'Cited and controllable', body: 'Every field links to its source. Files stop for a human when risk rises.' },
    { title: 'Built per line of business', body: 'Life medical, COPE property, and mortgage packages each get their own checklist.' },
  ];
  const scope = useRef(null);
  useScrollReveal(scope);
  return (
    <section ref={scope} className="border-t border-white/[0.06] py-14 lg:py-20">
      <Container>
        <div className="grid gap-8 md:grid-cols-3">
          {pillars.map((p) => (
            <div key={p.title} className="border-l-2 border-brand/50 pl-5">
              <h4 className="font-display text-lg font-semibold text-white">{p.title}</h4>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">{p.body}</p>
            </div>
          ))}
        </div>
      </Container>
    </section>
  );
}
