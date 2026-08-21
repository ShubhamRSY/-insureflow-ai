import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  AlertCircle, ArrowRight, Shield, HeartPulse, Stethoscope, Umbrella, Briefcase, Leaf,
  Landmark, HardHat, Plane, Lock, CloudRain, Scale, ShieldCheck,
} from 'lucide-react';
import { endpoints } from '../lib/api';
import { getInsuranceSection, insuranceSectionAccent } from '../lib/insuranceSections';

const ICONS = {
  HeartPulse, Stethoscope, Umbrella, Briefcase, Leaf, Landmark,
  HardHat, Plane, Lock, CloudRain, Scale, ShieldCheck,
};

export default function InsuranceSegmentPage() {
  const { sectionId } = useParams();
  const navigate = useNavigate();
  const section = getInsuranceSection(sectionId);
  const [hubLines, setHubLines] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!section) return undefined;
    let cancelled = false;
    setHubLines(null);
    setError('');
    const load = async () => {
      try {
        if (section.hubKind === 'general') {
          const hub = await endpoints.generalInsuranceHub();
          if (!cancelled) setHubLines(hub.lines || []);
          return;
        }
        if (section.hubKind === 'commercial' || section.hubKind === 'mixed') {
          const hub = await endpoints.commercialInsuranceHub();
          if (!cancelled) setHubLines(hub.lines || []);
        }
      } catch (e) {
        if (!cancelled) setError(e.message || 'Failed to load section lines');
      }
    };
    load();
    return () => { cancelled = true; };
  }, [section]);

  const liveLines = useMemo(() => {
    if (!section || !hubLines) return [];
    let rows = hubLines;
    if (section.filterCategories?.length) {
      rows = rows.filter((ln) => section.filterCategories.includes(ln.category_id));
    }
    if (section.filterIds?.length) {
      rows = rows.filter((ln) => section.filterIds.includes(ln.id));
    }
    return rows;
  }, [section, hubLines]);

  const liveByCat = useMemo(() => {
    if (!hubLines) return {};
    const map = {};
    for (const ln of hubLines) {
      if (ln.status === 'live' && ln.category_id) map[ln.category_id] = true;
    }
    return map;
  }, [hubLines]);

  const sectionLive = useMemo(() => {
    if (!section) return false;
    if (section.hubKind && hubLines) {
      return hubLines.some((ln) => ln.status === 'live');
    }
    return section.status === 'live';
  }, [section, hubLines]);

  const sectionStatus = sectionLive ? 'live' : 'catalog';

  if (!section) {
    return (
      <div className="mx-auto max-w-3xl py-16 text-center">
        <AlertCircle className="mx-auto h-8 w-8 text-red-400" />
        <p className="mt-3 text-red-400">Unknown insurance section</p>
        <Link to="/insurance" className="mt-4 inline-block text-sm text-brand hover:underline">
          Back to all sections
        </Link>
      </div>
    );
  }

  const Icon = ICONS[section.icon] || Shield;
  const accent = insuranceSectionAccent(section.accent);

  return (
    <div className="mx-auto w-full max-w-[1600px] space-y-8 animate-fade-in pb-12">
      <div>
        <nav className="flex items-center gap-1.5 text-xs text-slate-500" aria-label="Breadcrumb">
          <Link to="/insurance" className="transition hover:text-slate-300">Insurance</Link>
          <span className="text-slate-700">/</span>
          <span className="font-semibold text-slate-200">{section.title}</span>
        </nav>
        <div className="mt-3 flex items-start gap-4">
          <div className={`flex h-12 w-12 items-center justify-center rounded-2xl ${accent.iconBg}`}>
            <Icon className="h-6 w-6" />
          </div>
          <div>
            <p className={`text-xs font-semibold uppercase tracking-wider ${accent.tag}`}>
              Section {String(section.n).padStart(2, '0')} of 12
            </p>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              <h1 className="text-3xl font-bold tracking-tight text-slate-100">{section.title}</h1>
              <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                sectionStatus === 'live'
                  ? 'bg-emerald-500/15 text-emerald-400'
                  : 'bg-amber-500/15 text-amber-400'
              }`}>
                {sectionStatus === 'live' ? 'Live' : 'Catalog'}
              </span>
            </div>
            <p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-400">{section.summary}</p>
          </div>
        </div>
      </div>

      <section>
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Products in this section</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {section.products.map((p) => (
            <button
              key={p.name}
              type="button"
              onClick={() => navigate(p.href || section.hub)}
              className="rounded-xl bg-surface-overlay p-4 text-left ring-1 ring-white/[0.04] transition hover:ring-white/20"
            >
              <div className="flex items-center justify-between gap-2">
                <p className="font-medium text-slate-200">{p.name}</p>
                {p.cat && liveByCat[p.cat] ? (
                  <span className="shrink-0 rounded-full bg-emerald-500/15 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-emerald-400">
                    Live
                  </span>
                ) : null}
              </div>
              {p.hint ? <p className="mt-1 text-xs leading-relaxed text-slate-500">{p.hint}</p> : null}
              <p className={`mt-3 inline-flex items-center gap-1 text-xs font-medium ${accent.tag}`}>
                Open <ArrowRight className="h-3.5 w-3.5" />
              </p>
            </button>
          ))}
        </div>
      </section>

      {error ? <p className="text-sm text-red-400">{error}</p> : null}

      {liveLines.length > 0 ? (
        <section>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
            Underwriting lines
          </h2>
          <p className="mt-1 text-xs text-slate-500">
            Existing checklists and UW for this section. Catalog leaves do not invent premium.
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {liveLines.map((line) => (
              <button
                key={line.id}
                type="button"
                onClick={() => {
                  const base = section.hubKind === 'general' ? '/insurance/general' : '/insurance/commercial';
                  navigate(`${base}/${line.slug}`);
                }}
                className="rounded-xl bg-surface-overlay p-4 text-left ring-1 ring-white/[0.04] transition hover:ring-white/20"
              >
                <p className="font-medium text-slate-200">{line.short_name || line.name}</p>
                <p className="mt-2 line-clamp-2 text-xs text-slate-500">{line.description}</p>
                <p className="mt-3 text-[11px] uppercase tracking-wide text-slate-600">
                  {line.document_count} documents · {line.status || 'catalog'}
                </p>
              </button>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
