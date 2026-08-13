import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  Building2, Users, HardHat, CreditCard, Scale, HeartPulse,
  FileText, ClipboardCheck, Shield, AlertCircle,
} from 'lucide-react';
import { endpoints } from '../lib/api';
import { defaultCommercialSelection } from '../lib/commercialTaxonomy';
import RunSelector from '../components/RunSelector';

const LOB_ICONS = {
  property_bi: Building2,
  directors_officers: Users,
  workers_comp: HardHat,
  trade_credit: CreditCard,
  errors_omissions: Scale,
  key_person: HeartPulse,
};

export default function CommercialLinePage({ presets, onRunDemo, onSubmit }) {
  const { lobSlug } = useParams();
  const [line, setLine] = useState(null);
  const [error, setError] = useState('');
  const [selection, setSelection] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLine(null);
    setError('');
    setSelection(null);
    endpoints.commercialInsuranceLine(lobSlug)
      .then((d) => { if (!cancelled) setLine(d); })
      .catch((e) => { if (!cancelled) setError(e.message || 'Line not found'); });
    return () => { cancelled = true; };
  }, [lobSlug]);

  const lineTaxonomy = useMemo(() => {
    if (!line) return [];
    return [{
      id: line.category_id || 'commercial',
      name: line.short_name || line.name,
      products: [{
        id: line.id,
        name: line.name,
        slug: line.slug,
        insurance_line: line.insurance_line,
        checklist_lob: line.checklist_lob,
        coverages: line.coverages || [],
      }],
    }];
  }, [line]);

  useEffect(() => {
    if (!lineTaxonomy.length) return;
    setSelection(defaultCommercialSelection(lineTaxonomy));
  }, [lineTaxonomy]);

  if (error) {
    return (
      <div className="mx-auto max-w-3xl py-16 text-center">
        <AlertCircle className="mx-auto h-8 w-8 text-red-400" />
        <p className="mt-3 text-red-400">{error}</p>
        <Link to="/insurance/commercial" className="mt-4 inline-block text-sm text-brand hover:underline">
          Back to commercial hub
        </Link>
      </div>
    );
  }

  if (!line) {
    return (
      <div className="flex justify-center py-24">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
      </div>
    );
  }

  const Icon = LOB_ICONS[line.id] || FileText;
  const missingTemplate = line.checklist_template?.missing || line.documents || [];

  return (
    <div className="mx-auto max-w-6xl space-y-8 animate-fade-in pb-12">
      <div>
        <nav className="flex items-center gap-1.5 text-xs text-slate-500" aria-label="Breadcrumb">
          <Link to="/insurance" className="text-slate-600 transition hover:text-slate-300">Insurance</Link>
          <span className="text-slate-700">/</span>
          <Link to="/insurance" className="text-slate-600 transition hover:text-slate-300">Commercial Hub</Link>
          <span className="text-slate-700">/</span>
          <Link to="/insurance/commercial" className="text-slate-600 transition hover:text-slate-300">Business & Commercial</Link>
          <span className="text-slate-700">/</span>
          <span className="font-semibold text-slate-200">{line.name}</span>
        </nav>
        <div className="mt-3 flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand/15 text-brand">
            <Icon className="h-6 w-6" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-brand">Business / Commercial</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-100">{line.name}</h1>
            <p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-400">{line.description}</p>
            {(line.acord_forms || []).length > 0 && (
              <p className="mt-2 text-xs text-slate-500">{line.acord_forms.join(' · ')}</p>
            )}
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        <div className="space-y-6 lg:col-span-3">
          <section className="glass-card p-6">
            <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
              <FileText className="h-4 w-4" /> Document pack
            </h2>
            <p className="mt-2 text-xs text-slate-500">
              Line-specific submission requirements. Missing items drive triage / broker requests.
            </p>
            <ol className="mt-4 space-y-2">
              {(line.documents || []).map((doc, i) => (
                <li key={doc} className="flex gap-3 text-sm text-slate-300">
                  <span className="w-6 shrink-0 text-right text-xs text-slate-600">{i + 1}.</span>
                  <span>{doc}</span>
                </li>
              ))}
            </ol>
          </section>

          <section className="glass-card p-6">
            <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
              <Shield className="h-4 w-4" /> Base packet (keep ready)
            </h2>
            <ul className="mt-4 space-y-2">
              {(line.base_packet || []).map((item) => (
                <li key={item} className="flex gap-2 text-sm text-slate-300">
                  <span className="text-brand-light">•</span>
                  {item}
                </li>
              ))}
            </ul>
          </section>
        </div>

        <div className="space-y-6 lg:col-span-2">
          <section className="glass-card p-6">
            <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
              <ClipboardCheck className="h-4 w-4" /> Underwriter focus
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-slate-300">{line.uw_focus}</p>
            <p className="mt-4 rounded-xl bg-black/25 p-3 text-xs italic leading-relaxed text-slate-400">
              “{line.uw_question}”
            </p>
            <div className="mt-5 space-y-3">
              {(line.uw_responsibilities || []).map((r) => (
                <div key={r.id}>
                  <p className="text-sm font-medium text-slate-200">{r.title}</p>
                  <p className="mt-0.5 text-xs text-slate-500">{r.summary}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="glass-card p-6">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
              Checklist template
            </h2>
            <p className="mt-2 text-xs text-slate-500">
              Empty package → all items missing until documents are classified.
            </p>
            <p className="mt-3 text-2xl font-semibold text-slate-100">
              0 / {missingTemplate.length || (line.documents || []).length}
            </p>
            <p className="text-xs text-slate-500">present / required for this line</p>
          </section>
        </div>
      </div>

      <section className="glass-card p-6">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          Start submission — {line.short_name}
        </h2>
        <p className="mt-2 mb-4 text-sm text-slate-400">
          Select the coverage, then upload the package. Only that coverage runs — checklist, rating, and UW
          stay scoped to <code className="text-brand-light">{line.insurance_line}</code>
          {selection?.coverageName ? <> · <code className="text-brand-light">{selection.coverageName}</code></> : null}.
        </p>
        {selection && (
          <RunSelector
            presets={presets}
            vertical="insurance"
            productField="insurance_line"
            commercialTaxonomy={lineTaxonomy}
            commercialSelection={selection}
            onCommercialSelectionChange={setSelection}
            onRunDemo={onRunDemo}
            onSubmit={async (body) => {
              await onSubmit?.({
                ...body,
                insurance_line: line.insurance_line,
                product_line: line.insurance_line,
              });
            }}
          />
        )}
      </section>
    </div>
  );
}
