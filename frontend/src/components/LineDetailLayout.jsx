import { useState } from 'react';
import { ClipboardCheck, FileText, Shield } from 'lucide-react';
import { PageBack, Tabs } from './ui';
import RunSelector from './RunSelector';

// Tailwind's class scanner needs literal strings, not `bg-${accent}-500/15` —
// so every accent this app uses gets a fixed entry here rather than being
// built dynamically.
const ACCENT_STYLES = {
  teal: { chip: 'bg-teal-500/15 text-teal-400', label: 'text-teal-400', bullet: 'text-teal-400' },
  rose: { chip: 'bg-rose-500/15 text-rose-400', label: 'text-rose-400', bullet: 'text-rose-400' },
  brand: { chip: 'bg-brand/15 text-brand', label: 'text-brand', bullet: 'text-brand-light' },
  sky: { chip: 'bg-sky-500/15 text-sky-400', label: 'text-sky-400', bullet: 'text-sky-400' },
};

const SECTION_TABS = [
  { id: 'documents', label: 'Document Pack', icon: FileText },
  { id: 'base_packet', label: 'Base Packet', icon: Shield },
  { id: 'uw_focus', label: 'Underwriter Focus', icon: ClipboardCheck },
  { id: 'checklist', label: 'Checklist', icon: ClipboardCheck },
];

// Shared layout for every insurance line's detail page (health/life/
// commercial/general). Previously each line's page hand-duplicated the same
// four reference sections stacked one after another, forcing a long scroll —
// this puts them behind tabs instead, written once here rather than four
// times. Start Submission stays always-visible below the tabs: it's the
// actual action the page exists for, not reference material to browse.
export default function LineDetailLayout({
  line,
  eyebrowLabel,
  accent = 'brand',
  icon: Icon,
  backTo,
  backLabel,
  presets,
  lineTaxonomy,
  selection,
  onSelectionChange,
  onRunDemo,
  onSubmit,
  extraRunSelectorProps = {},
  snippetField = 'checklist_lob',
}) {
  const [activeTab, setActiveTab] = useState(SECTION_TABS[0].id);
  const styles = ACCENT_STYLES[accent] || ACCENT_STYLES.brand;
  const missingTemplate = line.checklist_template?.missing || line.documents || [];

  return (
    <div className="mx-auto max-w-6xl space-y-8 animate-fade-in pb-12">
      <div>
        {backTo && (
          <div className="mb-3">
            <PageBack to={backTo} label={backLabel} />
          </div>
        )}
        <div className="flex items-start gap-4">
          <div className={`flex h-12 w-12 items-center justify-center rounded-2xl ${styles.chip}`}>
            <Icon className="h-6 w-6" />
          </div>
          <div>
            <p className={`text-xs font-semibold uppercase tracking-wider ${styles.label}`}>{eyebrowLabel}</p>
            <h1 className="text-3xl font-bold tracking-tight text-slate-100">{line.name}</h1>
            <p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-400">{line.description}</p>
            {(line.acord_forms || []).length > 0 && (
              <p className="mt-2 text-xs text-slate-500">{line.acord_forms.join(' · ')}</p>
            )}
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <Tabs tabs={SECTION_TABS} active={activeTab} onChange={setActiveTab} />

        <section className="glass-card p-6">
          {activeTab === 'documents' && (
            <>
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
            </>
          )}

          {activeTab === 'base_packet' && (
            <>
              <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
                <Shield className="h-4 w-4" /> Base packet (keep ready)
              </h2>
              {(line.base_packet || []).length > 0 ? (
                <ul className="mt-4 space-y-2">
                  {line.base_packet.map((item) => (
                    <li key={item} className="flex gap-2 text-sm text-slate-300">
                      <span className={styles.bullet}>•</span>
                      {item}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-3 text-sm text-slate-500">No base packet items for this line.</p>
              )}
            </>
          )}

          {activeTab === 'uw_focus' && (
            <>
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
            </>
          )}

          {activeTab === 'checklist' && (
            <>
              <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Checklist template</h2>
              <p className="mt-2 text-xs text-slate-500">
                Empty package → all items missing until documents are classified.
              </p>
              <p className="mt-3 text-2xl font-semibold text-slate-100">
                0 / {missingTemplate.length || (line.documents || []).length}
              </p>
              <p className="text-xs text-slate-500">present / required for this line</p>
            </>
          )}
        </section>
      </div>

      <section className="glass-card p-6">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          Start submission — {line.short_name}
        </h2>
        <p className="mt-2 mb-4 text-sm text-slate-400">
          Select the coverage, then upload the package. Only that coverage runs — checklist, rating, and UW
          stay scoped to <code className="text-brand-light">{line[snippetField]}</code>
          {selection?.coverageName ? <> · <code className="text-brand-light">{selection.coverageName}</code></> : null}.
        </p>
        {selection && (
          <RunSelector
            presets={presets}
            vertical="insurance"
            productField="insurance_line"
            commercialTaxonomy={lineTaxonomy}
            commercialSelection={selection}
            onCommercialSelectionChange={onSelectionChange}
            onRunDemo={onRunDemo}
            onSubmit={async (body) => {
              await onSubmit?.({
                ...body,
                insurance_line: line.insurance_line,
                product_line: line.insurance_line,
              });
            }}
            {...extraRunSelectorProps}
          />
        )}
      </section>
    </div>
  );
}
