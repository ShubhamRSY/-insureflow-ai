import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowRight, Building2, Users, HardHat, CreditCard, Scale, HeartPulse,
  FileText, ClipboardCheck, Shield,
} from 'lucide-react';
import { endpoints } from '../lib/api';
import RunSelector from '../components/RunSelector';

const LOB_ICONS = {
  property_bi: Building2,
  directors_officers: Users,
  workers_comp: HardHat,
  trade_credit: CreditCard,
  errors_omissions: Scale,
  key_person: HeartPulse,
};

export default function CommercialInsuranceHub({ presets, onRunDemo, onSubmit }) {
  const navigate = useNavigate();
  const [hub, setHub] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    endpoints.commercialInsuranceHub()
      .then((d) => { if (!cancelled) setHub(d); })
      .catch((e) => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, []);

  if (error) {
    return <p className="py-16 text-center text-red-400">{error}</p>;
  }
  if (!hub) {
    return (
      <div className="flex justify-center py-24">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-8 animate-fade-in pb-12">
      <div>
        <nav className="flex items-center gap-1.5 text-xs text-slate-500" aria-label="Breadcrumb">
          <Link to="/insurance" className="text-slate-600 transition hover:text-slate-300">Underwriting</Link>
          <span className="text-slate-700">/</span>
          <Link to="/insurance" className="text-slate-600 transition hover:text-slate-300">Insurance</Link>
          <span className="text-slate-700">/</span>
          <span className="font-semibold text-slate-200">Business & Commercial</span>
        </nav>
        <div className="mt-3 flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand/15 text-brand">
            <Shield className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-brand/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-brand-light">
                Block 1
              </span>
              <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-emerald-400">
                Live
              </span>
            </div>
            <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-100">{hub.title}</h1>
            <p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-400">{hub.summary}</p>
          </div>
        </div>
      </div>

      {/* Run / pull / connect */}
      <RunSelector
        presets={presets}
        vertical="insurance"
        productField="insurance_line"
        productOptions={(hub.lines || []).map((l) => ({ id: l.insurance_line, label: l.short_name }))}
        productDefault={(hub.lines || [])[0]?.insurance_line || ''}
        onRunDemo={onRunDemo}
        onSubmit={onSubmit}
      />

      {/* UW framing */}
      <section className="glass-card p-6">
        <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
          <ClipboardCheck className="h-4 w-4" /> What the commercial underwriter does
        </h2>
        <p className="mt-3 text-sm leading-relaxed text-slate-300">
          Decide whether to offer coverage, on what terms, and at what price — the risk evaluator
          between the applicant and the carrier&apos;s balance sheet.
        </p>
        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {(hub.uw_responsibilities || []).map((r) => (
            <div key={r.id} className="rounded-xl bg-black/20 p-4 ring-1 ring-white/[0.04]">
              <p className="text-sm font-medium text-slate-200">{r.title}</p>
              <p className="mt-1.5 text-xs leading-relaxed text-slate-500">{r.summary}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Base packet */}
      <section className="glass-card p-6">
        <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
          <FileText className="h-4 w-4" /> Base packet (almost every line)
        </h2>
        <ul className="mt-4 grid gap-2 sm:grid-cols-2">
          {(hub.base_packet || []).map((item) => (
            <li key={item} className="flex gap-2 text-sm text-slate-300">
              <span className="text-brand-light">•</span>
              {item}
            </li>
          ))}
        </ul>
      </section>

      {/* Lines */}
      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Lines of business</h2>
        <div className="grid gap-4 md:grid-cols-2">
          {(hub.lines || []).map((line) => {
            const Icon = LOB_ICONS[line.id] || FileText;
            return (
              <button
                key={line.id}
                type="button"
                onClick={() => navigate(`/insurance/commercial/${line.slug}`)}
                className="group rounded-2xl bg-surface-overlay p-5 text-left ring-1 ring-white/[0.04] transition hover:ring-brand/35"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand/10 text-brand-light">
                      <Icon className="h-5 w-5" />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-slate-100">{line.name}</h3>
                      <p className="text-xs text-slate-500">{line.document_count} required documents</p>
                    </div>
                  </div>
                  <ArrowRight className="mt-1 h-4 w-4 text-slate-600 transition group-hover:text-brand" />
                </div>
                <p className="mt-3 text-sm leading-relaxed text-slate-400">{line.description}</p>
                {(line.acord_forms || []).length > 0 && (
                  <p className="mt-3 text-xs text-slate-500">{line.acord_forms.join(' · ')}</p>
                )}
              </button>
            );
          })}
        </div>
      </section>
    </div>
  );
}
