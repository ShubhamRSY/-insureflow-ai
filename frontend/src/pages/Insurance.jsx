import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Shield, Building2, ArrowRight, FileText, Briefcase, Users,
  HardHat, CreditCard, Scale, HeartPulse, Layers, Plus,
} from 'lucide-react';
import { endpoints } from '../lib/api';
import { insuranceLineLabel } from '../lib/insuranceLines';

const LOB_ICONS = {
  property_bi: Building2,
  directors_officers: Users,
  workers_comp: HardHat,
  trade_credit: CreditCard,
  errors_omissions: Scale,
  key_person: HeartPulse,
};

export default function InsurancePage({ jobs, onRefresh }) {
  const navigate = useNavigate();
  const [hub, setHub] = useState(null);
  const [error, setError] = useState('');
  const recent = (jobs || []).slice(0, 6);

  useEffect(() => {
    let cancelled = false;
    endpoints.commercialInsuranceHub()
      .then((d) => { if (!cancelled) setHub(d); })
      .catch((e) => { if (!cancelled) setError(e.message || 'Failed to load commercial hub'); });
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="mx-auto max-w-6xl space-y-8 animate-fade-in pb-12">
      <div>
        <nav className="flex items-center gap-1.5 text-xs text-slate-500" aria-label="Breadcrumb">
          <span className="text-slate-600">Insurance</span>
          <span className="text-slate-700">/</span>
          <span className="font-semibold text-slate-200">Commercial Hub</span>
        </nav>
        <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-insurance/15 text-insurance">
              <Shield className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-slate-100">Insurance</h1>
              <p className="mt-1 max-w-2xl text-sm text-slate-400">
                Business / Commercial is live — more segments ship one at a time.
              </p>
            </div>
          </div>
          <button type="button" onClick={() => onRefresh?.()} className="btn-secondary btn-sm text-sm">
            Refresh jobs
          </button>
        </div>
      </div>

      {/* Segment cards */}
      <section>
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Segments</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          <Link
            to="/insurance/commercial"
            className="group glass-card block p-6 transition hover:ring-1 hover:ring-brand/40"
          >
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand/15 text-brand">
                <Briefcase className="h-5 w-5" />
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-emerald-400">Live</p>
                <h2 className="text-xl font-semibold text-slate-100">Business / Commercial</h2>
              </div>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-slate-400">
              Property & BI, D&O, Workers&apos; Comp, Trade Credit, E&O, and Key Person — with full
              submission checklists and commercial UW workflow.
            </p>
            <p className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-brand group-hover:gap-2">
              Open commercial hub <ArrowRight className="h-4 w-4" />
            </p>
          </Link>

          <div className="glass-card p-6 opacity-70">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-500/15 text-slate-400">
                <Layers className="h-5 w-5" />
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Next</p>
                <h2 className="text-xl font-semibold text-slate-300">Personal Lines</h2>
              </div>
            </div>
            <p className="mt-3 text-sm text-slate-500">
              Homeowners, personal auto, and life — coming after commercial is complete.
            </p>
          </div>

          <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-white/[0.1] p-6 text-center opacity-70">
            <Plus className="h-6 w-6 text-slate-600" />
            <p className="mt-2 text-sm font-medium text-slate-400">Next segment</p>
            <p className="mt-1 text-xs text-slate-500">More insurance segments arrive one at a time.</p>
          </div>
        </div>
      </section>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {/* Commercial preview */}
      {hub && (
        <section className="space-y-4">
          <div className="flex items-end justify-between gap-3">
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Commercial lines</h3>
              <p className="mt-1 text-sm text-slate-400">{hub.summary}</p>
            </div>
            <Link to="/insurance/commercial" className="text-sm text-brand hover:underline">View all</Link>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {(hub.lines || []).map((line) => {
              const Icon = LOB_ICONS[line.id] || FileText;
              return (
                <button
                  key={line.id}
                  type="button"
                  onClick={() => navigate(`/insurance/commercial/${line.slug}`)}
                  className="rounded-xl bg-surface-overlay p-4 text-left ring-1 ring-white/[0.04] transition hover:ring-brand/30"
                >
                  <div className="flex items-center gap-2">
                    <Icon className="h-4 w-4 text-brand-light" />
                    <p className="font-medium text-slate-200">{line.short_name}</p>
                  </div>
                  <p className="mt-2 line-clamp-2 text-xs text-slate-500">{line.description}</p>
                  <p className="mt-3 text-[11px] uppercase tracking-wide text-slate-600">
                    {line.document_count} documents in pack
                  </p>
                </button>
              );
            })}
          </div>
        </section>
      )}

      {/* Recent jobs */}
      <section className="glass-card overflow-hidden">
        <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-4">
          <h3 className="text-sm font-semibold text-slate-200">Recent insurance jobs</h3>
          <Link to="/insurance/commercial" className="text-xs text-brand hover:underline">
            Start commercial submission →
          </Link>
        </div>
        {!recent.length ? (
          <p className="px-5 py-8 text-sm text-slate-500">No jobs yet. Open a commercial line and run a package.</p>
        ) : (
          <div className="divide-y divide-white/[0.04]">
            {recent.map((j) => (
              <button
                key={j.id}
                type="button"
                onClick={() => navigate(`/insurance/${j.id}`)}
                className="flex w-full items-center justify-between gap-3 px-5 py-3 text-left hover:bg-white/[0.02]"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-200">{j.name || j.insured_name || j.id}</p>
                  <p className="text-xs text-slate-500">{insuranceLineLabel(j.insurance_line || j.product_line || 'commercial')}</p>
                </div>
                <span className="shrink-0 text-xs capitalize text-slate-400">{j.status || '—'}</span>
              </button>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
