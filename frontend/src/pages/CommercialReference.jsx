import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  BookOpen,
  ChevronDown,
  ChevronRight,
  ClipboardList,
  FileText,
  Layers,
  Search,
  Shield,
} from 'lucide-react';
import { endpoints } from '../lib/api';

function GuideSection({ title, icon: Icon, open, onToggle, children, badge }) {
  return (
    <div className="overflow-hidden rounded-xl border border-white/[0.06] bg-surface-overlay/80">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left hover:bg-white/[0.02]"
      >
        <span className="flex min-w-0 items-center gap-2">
          {Icon && <Icon className="h-4 w-4 shrink-0 text-slate-500" />}
          <span className="text-sm font-semibold text-slate-200">{title}</span>
          {badge != null && (
            <span className="rounded-full bg-white/[0.06] px-2 py-0.5 text-[10px] font-medium text-slate-500">{badge}</span>
          )}
        </span>
        {open ? <ChevronDown className="h-4 w-4 shrink-0 text-slate-600" /> : <ChevronRight className="h-4 w-4 shrink-0 text-slate-600" />}
      </button>
      {open && <div className="border-t border-white/[0.04] px-4 py-4">{children}</div>}
    </div>
  );
}

export default function CommercialReference() {
  const [hub, setHub] = useState(null);
  const [error, setError] = useState('');
  const [selectedLine, setSelectedLine] = useState('');
  const [taxonomyQuery, setTaxonomyQuery] = useState('');
  const [openSections, setOpenSections] = useState({
    lines: true,
    pack: true,
    taxonomy: true,
    base: false,
    uw: false,
  });
  const [openCats, setOpenCats] = useState({});

  useEffect(() => {
    let cancelled = false;
    endpoints.commercialInsuranceHub()
      .then((d) => {
        if (cancelled) return;
        setHub(d);
        const lines = d.lines || d.live_lines || [];
        setSelectedLine(lines[0]?.insurance_line || '');
        const initial = {};
        (d.taxonomy || []).forEach((c) => { initial[c.id] = false; });
        setOpenCats(initial);
      })
      .catch((e) => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, []);

  const productByLine = useMemo(() => {
    const map = new Map();
    (hub?.taxonomy || []).forEach((cat) => {
      (cat.products || []).forEach((p) => map.set(p.insurance_line, { ...p, categoryName: cat.name }));
    });
    return map;
  }, [hub]);

  const selectedProduct = productByLine.get(selectedLine);
  const liveProductOptions = useMemo(() => {
    return (hub?.lines || []).map((l) => ({ id: l.insurance_line, label: l.name }));
  }, [hub]);

  const filteredTaxonomy = useMemo(() => {
    const q = taxonomyQuery.trim().toLowerCase();
    if (!q) return hub?.taxonomy || [];
    return (hub?.taxonomy || [])
      .map((cat) => ({
        ...cat,
        products: (cat.products || []).filter(
          (p) => p.name.toLowerCase().includes(q) || p.insurance_line.toLowerCase().includes(q),
        ),
      }))
      .filter((cat) => cat.products.length > 0 || cat.name.toLowerCase().includes(q));
  }, [hub, taxonomyQuery]);

  const toggleSection = (key) => setOpenSections((s) => ({ ...s, [key]: !s[key] }));

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

  const stats = hub.stats || {};
  const packDocs = selectedProduct?.all_documents || [];

  return (
    <div className="mx-auto max-w-3xl animate-fade-in space-y-6 pb-12">
      <div>
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand/15 text-brand">
            <BookOpen className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">Commercial insurance notebook</h1>
            <p className="mt-1 text-sm text-slate-400">
              Product taxonomy, required documents, and UW reference — separate from the submission workbench.
            </p>
            <Link to="/insurance/commercial" className="mt-2 inline-flex items-center gap-1 text-xs text-brand hover:underline">
              ← Back to submissions
            </Link>
          </div>
        </div>
      </div>

      <GuideSection
        title="Live lines"
        icon={Layers}
        open={openSections.lines}
        onToggle={() => toggleSection('lines')}
        badge={liveProductOptions.length}
      >
        <ul className="space-y-1">
          {liveProductOptions.map((opt) => {
            const active = selectedLine === opt.id;
            return (
              <li key={opt.id}>
                <button
                  type="button"
                  onClick={() => setSelectedLine(opt.id)}
                  className={`w-full rounded-lg px-3 py-2 text-left text-sm transition ${
                    active
                      ? 'bg-brand/15 font-medium text-brand-light ring-1 ring-brand/25'
                      : 'text-slate-400 hover:bg-white/[0.03] hover:text-slate-200'
                  }`}
                >
                  {opt.label}
                </button>
              </li>
            );
          })}
        </ul>
      </GuideSection>

      {selectedProduct && (
        <GuideSection
          title="Document pack"
          icon={ClipboardList}
          open={openSections.pack}
          onToggle={() => toggleSection('pack')}
          badge={packDocs.length || selectedProduct.document_count}
        >
          <p className="text-sm text-slate-400">
            Required for <span className="text-slate-200">{selectedProduct.name}</span>
          </p>
          <ol className="mt-3 space-y-2 text-sm text-slate-400">
            {(packDocs.length ? packDocs : ['No document list loaded']).map((doc, i) => (
              <li key={doc} className="flex gap-2">
                <span className="w-5 shrink-0 text-right text-slate-600">{i + 1}.</span>
                <span>{doc}</span>
              </li>
            ))}
          </ol>
          {selectedProduct.slug && (
            <Link
              to={`/insurance/commercial/${selectedProduct.slug}`}
              className="mt-4 inline-flex items-center gap-1 text-sm text-brand hover:underline"
            >
              Full line detail <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          )}
        </GuideSection>
      )}

      <GuideSection
        title="Product lines"
        icon={Search}
        open={openSections.taxonomy}
        onToggle={() => toggleSection('taxonomy')}
        badge={stats.product_count}
      >
        <input
          type="search"
          value={taxonomyQuery}
          onChange={(e) => setTaxonomyQuery(e.target.value)}
          placeholder="Search products…"
          className="input-field mb-3 text-sm"
        />
        <div className="space-y-2">
          {filteredTaxonomy.map((cat) => {
            const catOpen = !!openCats[cat.id];
            return (
              <div key={cat.id} className="rounded-lg bg-black/20 ring-1 ring-white/[0.04]">
                <button
                  type="button"
                  onClick={() => setOpenCats((s) => ({ ...s, [cat.id]: !s[cat.id] }))}
                  className="flex w-full items-center justify-between px-3 py-2.5 text-left hover:bg-white/[0.02]"
                >
                  <span className="text-sm font-medium text-slate-200">{cat.name}</span>
                  <span className="text-xs text-slate-500">{cat.products?.length || 0} products</span>
                </button>
                {catOpen && (
                  <ul className="space-y-0.5 border-t border-white/[0.04] px-3 py-2">
                    {(cat.products || []).map((product) => (
                      <li key={product.id}>
                        <button
                          type="button"
                          onClick={() => setSelectedLine(product.insurance_line)}
                          className={`flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm ${
                            selectedLine === product.insurance_line
                              ? 'bg-brand/10 text-brand-light'
                              : 'text-slate-400 hover:text-slate-200'
                          }`}
                        >
                          <span className="min-w-0 flex-1">{product.short_name || product.name}</span>
                          <span className="text-[10px] uppercase text-emerald-400">live</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            );
          })}
        </div>
      </GuideSection>

      <GuideSection
        title="Base submission packet"
        icon={FileText}
        open={openSections.base}
        onToggle={() => toggleSection('base')}
      >
        <ul className="space-y-2 text-sm text-slate-400">
          {(hub.base_packet || []).map((item) => (
            <li key={item} className="flex gap-2">
              <span className="text-brand-light/70">•</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </GuideSection>

      <GuideSection
        title="UW responsibilities"
        icon={Shield}
        open={openSections.uw}
        onToggle={() => toggleSection('uw')}
      >
        <ul className="space-y-3">
          {(hub.uw_responsibilities || []).map((r) => (
            <li key={r.id}>
              <p className="text-sm font-medium text-slate-200">{r.title}</p>
              <p className="mt-0.5 text-xs leading-relaxed text-slate-500">{r.summary}</p>
            </li>
          ))}
        </ul>
      </GuideSection>
    </div>
  );
}
