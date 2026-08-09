import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, ChevronDown, ChevronRight, FileText, Shield } from 'lucide-react';
import { endpoints } from '../lib/api';
import { insuranceLineLabel } from '../lib/insuranceLines';
import RunSelector from '../components/RunSelector';

export default function CommercialInsuranceHub({ presets, onRunDemo, onSubmit, jobs }) {
  const navigate = useNavigate();
  const [hub, setHub] = useState(null);
  const [error, setError] = useState('');
  const [openCats, setOpenCats] = useState({});

  useEffect(() => {
    let cancelled = false;
    endpoints.commercialInsuranceHub()
      .then((d) => {
        if (cancelled) return;
        setHub(d);
        const initial = {};
        (d.taxonomy || []).forEach((c, i) => { initial[c.id] = i === 0; });
        setOpenCats(initial);
      })
      .catch((e) => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, []);

  const liveProductOptions = useMemo(() => {
    const live = hub?.live_lines || (hub?.lines || []).filter((l) => l.status === 'live');
    return live.map((l) => ({ id: l.insurance_line, label: l.name }));
  }, [hub]);

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

  const runs = (jobs || []).slice(0, 8);
  const stats = hub.stats || {};

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
              <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-emerald-400">
                Live
              </span>
              <span className="text-[11px] text-slate-500">
                {stats.product_count || 0} products · {stats.live_count || 0} live UW paths · {stats.category_count || 8} categories
              </span>
            </div>
            <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-100">{hub.title}</h1>
            <p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-400">{hub.summary}</p>
          </div>
        </div>
      </div>

      <RunSelector
        presets={presets}
        vertical="insurance"
        productField="insurance_line"
        productOptions={liveProductOptions.length ? liveProductOptions : (hub.lines || []).slice(0, 9).map((l) => ({ id: l.insurance_line, label: l.name }))}
        productDefault={liveProductOptions[0]?.id || (hub.lines || [])[0]?.insurance_line || ''}
        onRunDemo={onRunDemo}
        onSubmit={onSubmit}
      />

      {/* Full UW taxonomy */}
      <section className="space-y-3">
        <div className="flex items-end justify-between gap-3">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Underwriting taxonomy</h2>
          <p className="text-[11px] text-slate-500">Categories → products → coverages · document packs on every product</p>
        </div>
        <div className="space-y-2">
          {(hub.taxonomy || []).map((cat) => {
            const open = !!openCats[cat.id];
            return (
              <div key={cat.id} className="overflow-hidden rounded-2xl bg-surface-overlay ring-1 ring-white/[0.04]">
                <button
                  type="button"
                  onClick={() => setOpenCats((s) => ({ ...s, [cat.id]: !s[cat.id] }))}
                  className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-white/[0.02]"
                >
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-slate-100">{cat.name}</p>
                    <p className="truncate text-xs text-slate-500">{cat.summary}</p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <span className="rounded-full bg-white/[0.06] px-2 py-0.5 text-[10px] font-medium text-slate-400">
                      {cat.product_count} products
                      {cat.live_count ? ` · ${cat.live_count} live` : ''}
                    </span>
                    {open ? <ChevronDown className="h-4 w-4 text-slate-500" /> : <ChevronRight className="h-4 w-4 text-slate-500" />}
                  </div>
                </button>
                {open && (
                  <div className="space-y-2 border-t border-white/[0.04] px-4 py-3">
                    {(cat.products || []).map((product) => {
                      const demos = (presets?.insurance || []).filter((p) => p.insurance_line === product.insurance_line);
                      return (
                        <div key={product.id} className="rounded-xl bg-black/20 px-3 py-3 ring-1 ring-white/[0.04]">
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <div className="flex flex-wrap items-center gap-2">
                                <p className="text-sm font-medium text-slate-200">{product.name}</p>
                                <span className={`rounded-full px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${
                                  product.status === 'live'
                                    ? 'bg-emerald-500/15 text-emerald-400'
                                    : 'bg-slate-500/15 text-slate-400'
                                }`}>
                                  {product.status}
                                </span>
                              </div>
                              <p className="mt-0.5 text-[11px] text-slate-500">
                                {product.document_count} required documents
                                {demos.length ? ` · ${demos.length} demo${demos.length > 1 ? 's' : ''}` : ''}
                              </p>
                            </div>
                            {demos[0] && (
                              <button
                                type="button"
                                onClick={() => onRunDemo('insurance', demos[0].id)}
                                className="btn-primary btn-sm shrink-0 text-xs"
                              >
                                Run demo
                              </button>
                            )}
                          </div>
                          {(product.coverages || []).length > 0 && (
                            <ul className="mt-2 space-y-2 border-l border-white/[0.06] pl-3">
                              {product.coverages.map((cov) => (
                                <li key={cov.id || cov.name}>
                                  <p className="text-[11px] text-slate-400">{cov.name || cov}</p>
                                  {Array.isArray(cov.documents) && cov.documents.length > 0 && (
                                    <ul className="mt-1 space-y-0.5 pl-2">
                                      {cov.documents.map((doc) => (
                                        <li key={doc} className="text-xs text-slate-500">{doc}</li>
                                      ))}
                                    </ul>
                                  )}
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* Runs & reports */}
      <section className="glass-card overflow-hidden">
        <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-4">
          <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
            <FileText className="h-4 w-4" /> Runs & reports
          </h2>
          <Link to="/insurance" className="text-xs text-brand hover:underline">All insurance jobs →</Link>
        </div>
        {!runs.length ? (
          <p className="px-5 py-8 text-sm text-slate-500">
            No submissions yet. Pick a live line above, add files or a sample, and run — the memo, quote, and report land here.
          </p>
        ) : (
          <div className="divide-y divide-white/[0.04]">
            {runs.map(({ id, job }) => (
              <button
                key={id}
                type="button"
                onClick={() => navigate(`/insurance/${id}`)}
                className="flex w-full items-center justify-between gap-3 px-5 py-3 text-left hover:bg-white/[0.02]"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-200">
                    {job?.name || job?.results?.insured_name || id}
                  </p>
                  <p className="text-xs text-slate-500">
                    {insuranceLineLabel(job?.results?.insurance_line || job?.results?.product_line || '') || 'Commercial'}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs capitalize text-slate-400">{job?.status || '—'}</span>
                  <ArrowRight className="h-3.5 w-3.5 text-slate-600" />
                </div>
              </button>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
