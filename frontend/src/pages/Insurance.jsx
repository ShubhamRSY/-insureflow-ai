import { Link, useNavigate } from 'react-router-dom';
import {
  Shield, ArrowRight, HeartPulse, Stethoscope, Umbrella, Briefcase, Leaf,
  Landmark, HardHat, Plane, Lock, CloudRain, Scale, ShieldCheck,
} from 'lucide-react';
import { insuranceLineLabel } from '../lib/insuranceLines';
import { INSURANCE_SECTIONS, insuranceSectionAccent } from '../lib/insuranceSections';

const ICONS = {
  HeartPulse, Stethoscope, Umbrella, Briefcase, Leaf, Landmark,
  HardHat, Plane, Lock, CloudRain, Scale, ShieldCheck,
};

export default function InsurancePage({ jobs, onRefresh }) {
  const navigate = useNavigate();
  const recent = (jobs || []).slice(0, 8);

  return (
    <div className="mx-auto max-w-6xl space-y-8 animate-fade-in pb-12">
      <div>
        <nav className="flex items-center gap-1.5 text-xs text-slate-500" aria-label="Breadcrumb">
          <span className="text-slate-600">Insurance</span>
          <span className="text-slate-700">/</span>
          <span className="font-semibold text-slate-200">All sections</span>
        </nav>
        <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-insurance/15 text-insurance">
              <Shield className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-slate-100">Insurance</h1>
              <p className="mt-1 max-w-2xl text-sm text-slate-400">
                Twelve sections — life, health, general, commercial, specialty, provider type,
                engineering, aviation, fidelity, catastrophe, niche liability, and warranty / financial / emerging.
                Named insureds and PII are stripped before any LLM API call on every section.
              </p>
            </div>
          </div>
          <button type="button" onClick={() => onRefresh?.()} className="btn-secondary btn-sm text-sm">
            Refresh jobs
          </button>
        </div>
      </div>

      <section>
        <div className="flex items-end justify-between gap-3">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">12 sections</h2>
          <p className="text-xs text-slate-500">{INSURANCE_SECTIONS.length} families · pick a section to underwrite</p>
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {INSURANCE_SECTIONS.map((section) => {
            const Icon = ICONS[section.icon] || Shield;
            const accent = insuranceSectionAccent(section.accent);
            return (
              <Link
                key={section.id}
                to={`/insurance/sections/${section.id}`}
                className={`group glass-card block p-5 transition hover:ring-1 ${accent.ring}`}
              >
                <div className="flex items-start gap-3">
                  <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${accent.iconBg}`}>
                    <Icon className="h-5 w-5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`text-[11px] font-bold tabular-nums ${accent.num}`}>{String(section.n).padStart(2, '0')}</span>
                      <h3 className="text-base font-semibold text-slate-100">{section.title}</h3>
                      <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                        section.status === 'live'
                          ? 'bg-emerald-500/15 text-emerald-400'
                          : 'bg-amber-500/15 text-amber-400'
                      }`}>
                        {section.status === 'live' ? 'Live' : 'Catalog'}
                      </span>
                    </div>
                    <p className="mt-1.5 text-xs leading-relaxed text-slate-400">{section.summary}</p>
                  </div>
                </div>
                <ul className="mt-4 space-y-1 border-t border-white/[0.04] pt-3">
                  {section.products.slice(0, 6).map((p) => (
                    <li key={p.name} className="flex gap-2 text-xs text-slate-300">
                      <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-slate-600" />
                      <span>
                        <span className="font-medium text-slate-200">{p.name}</span>
                        {p.hint ? <span className="text-slate-500"> — {p.hint}</span> : null}
                      </span>
                    </li>
                  ))}
                  {section.products.length > 6 ? (
                    <li className="pl-3 text-[11px] text-slate-500">+{section.products.length - 6} more</li>
                  ) : null}
                </ul>
                <p className={`mt-4 inline-flex items-center gap-1 text-sm font-medium ${accent.tag} group-hover:gap-2`}>
                  Open section <ArrowRight className="h-4 w-4" />
                </p>
              </Link>
            );
          })}
        </div>
      </section>

      <section className="glass-card overflow-hidden">
        <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-4">
          <h3 className="text-sm font-semibold text-slate-200">Recent insurance jobs</h3>
          <Link to="/insurance/sections/commercial" className="text-xs text-brand hover:underline">
            Start a submission →
          </Link>
        </div>
        {!recent.length ? (
          <p className="px-5 py-8 text-sm text-slate-500">No jobs yet. Open a section and run a package.</p>
        ) : (
          <div className="divide-y divide-white/[0.04]">
            {recent.map((j) => {
              const results = j.job?.results || j.results || {};
              const company = results.insurance_company_name || j.insurance_company_name;
              const line = results.insurance_line || results.product_line || j.insurance_line || j.product_line || 'commercial';
              return (
              <button
                key={j.id}
                type="button"
                onClick={() => navigate(`/insurance/${j.id}`)}
                className="flex w-full items-center justify-between gap-3 px-5 py-3 text-left hover:bg-white/[0.02]"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-200">{j.name || results.insured_name || j.insured_name || j.id}</p>
                  <p className="text-xs text-slate-500">
                    {company ? `${company} · ` : ''}
                    {insuranceLineLabel(line)}
                  </p>
                </div>
                <span className="shrink-0 text-xs capitalize text-slate-400">{j.job?.status || j.status || '—'}</span>
              </button>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
