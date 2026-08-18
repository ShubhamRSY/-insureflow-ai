import { useEffect, useState } from 'react';
import { Cable, Check, CheckCircle2, Loader2, Play } from 'lucide-react';
import { endpoints } from '../lib/api';
import ConnectorLogo from './ConnectorLogo';
import PulledFilesBrowser from './PulledFilesBrowser';
import { groupSourcesByCategory } from '../lib/connectorBrands';
import { UI_HINTS } from '../lib/uiHints';
import { Hint, HintCheckbox } from './ui';

function KindBadge({ kind }) {
  if (kind === 'live') {
    return <span className="shrink-0 rounded-full bg-emerald-500/15 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-emerald-400">Live</span>;
  }
  if (kind === 'needs_config') {
    return <span className="shrink-0 rounded-full bg-amber-500/15 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-amber-400">Needs creds</span>;
  }
  if (kind === 'lab_demo') {
    return <span className="shrink-0 rounded-full bg-slate-500/15 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-slate-400">Lab sample</span>;
  }
  if (kind === 'catalog_stub') {
    return <span className="shrink-0 rounded-full bg-white/5 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-slate-500">Not contracted</span>;
  }
  return null;
}

/**
 * "Connect & pull" source hub shared across verticals (insurance, mortgage,
 * lending). Lists connectors + demo packages from the vertical-aware
 * /api/insurance/sources endpoint, accumulates pulled documents into a draft
 * bundle, and runs the bundle through that vertical's pipeline.
 *
 * onRunJob — async verticals (insurance, mortgage) that return a job_id
 * onRunResult — inline verticals (lending) that return the result directly
 */
export default function ConnectAndPull({
  vertical = 'insurance',
  onRunJob,
  onRunResult,
  insuranceLine = '',
  lifeProductId = '',
  lifeCoverageId = '',
  healthProductId = '',
  healthCoverageId = '',
  generalProductId = '',
  generalCoverageId = '',
  commercialProductId = '',
  coverageId = '',
  productName = '',
  coverageName = '',
  commercialCategoryId = '',
  insuranceCompanyId = '',
  insuranceCompanyName = '',
  strictRelevance = true,
}) {
  const [sources, setSources] = useState([]);
  const [sections, setSections] = useState([]);
  const [categoryId, setCategoryId] = useState('Document Storage');
  const [activeSource, setActiveSource] = useState(null);
  const [config, setConfig] = useState({});
  const [connected, setConnected] = useState(null);
  const [emails, setEmails] = useState([]);
  const [selectedEmailIds, setSelectedEmailIds] = useState(new Set());
  const [pulling, setPulling] = useState(false);
  const [bundleId, setBundleId] = useState(null);
  const [bundleDocs, setBundleDocs] = useState([]);
  const [bundleTree, setBundleTree] = useState([]);
  const [relevanceByName, setRelevanceByName] = useState({});
  const [useLlm, setUseLlm] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState('');
  const [warning, setWarning] = useState('');

  useEffect(() => {
    endpoints.insuranceSources(vertical)
      .then((r) => {
        const srcs = r.sources || [];
        setSources(srcs);
        setSections(groupSourcesByCategory(srcs));
      })
      .catch(() => {});
  }, [vertical]);

  const activeSection = sections.find((s) => s.id === categoryId) || sections[0];
  const isEmailSource = activeSource?.id === 'email-inbox';
  const needsConfig = (activeSource?.config_fields?.length || 0) > 0;

  const ensureBundle = async () => {
    if (bundleId) return bundleId;
    try {
      const result = await endpoints.createDraftBundle('New submission');
      setBundleId(result.bundle_id);
      return result.bundle_id;
    } catch (e) {
      setError(e.message);
      return null;
    }
  };

  const refreshBundle = async (bid) => {
    if (!bid) return;
    try {
      const detail = await endpoints.getDraftBundle(bid);
      const docs = detail.documents || [];
      setBundleDocs(docs);
      setBundleTree(detail.tree || []);
      if (docs.length) {
        const payload = docs.map((d) => ({
          filename: d.filename,
          content: d.content || '',
          encoding: d.encoding || 'utf-8',
        }));
        const rel = await endpoints.validateDocuments(payload, vertical, false).catch(() => null);
        if (rel?.documents) {
          const map = {};
          rel.documents.forEach((row) => { map[row.filename] = row; });
          setRelevanceByName(map);
          setWarning(rel.irrelevant_count ? (rel.warnings?.[0] || rel.message || '') : '');
        }
      } else {
        setRelevanceByName({});
        setWarning('');
      }
    } catch { /* noop */ }
  };

  const pullSource = async (sourceId, cfg = {}) => {
    setPulling(true);
    setError('');
    try {
      const bid = await ensureBundle();
      if (!bid) return;
      const result = await endpoints.pullInsuranceSource(sourceId, { ...cfg, bundle_id: bid }, vertical);
      setConnected(result);
      if (result.emails?.length) {
        setEmails(result.emails);
        setSelectedEmailIds(new Set(result.emails.map((e) => e.id)));
      }
      await refreshBundle(bid);
    } catch (e) {
      setError(e.message);
    } finally {
      setPulling(false);
    }
  };

  const pullAllInCategory = async () => {
    const list = activeSection?.sources || [];
    if (!list.length) return;
    setPulling(true);
    setError('');
    setWarning('');
    try {
      const bid = await ensureBundle();
      if (!bid) return;
      let pulled = 0;
      const failures = [];
      for (const src of list) {
        // Skip sources that need credentials the user hasn't filled
        if ((src.config_fields || []).length > 0) continue;
        if (src.kind === 'catalog_stub' || src.kind === 'needs_config') continue;
        try {
          await endpoints.pullInsuranceSource(src.id, { bundle_id: bid }, vertical);
          pulled += 1;
        } catch (e) {
          failures.push(`${src.name}: ${e.message}`);
        }
      }
      await refreshBundle(bid);
      if (!pulled && failures.length) setError(failures[0]);
      else if (failures.length) setWarning(`Pulled ${pulled} source(s); ${failures.length} skipped/failed`);
      else if (!pulled) setWarning('No zero-config sources in this category — open a source and pull, or fill connection fields');
      else setConnected({ accumulated: { added: pulled, document_count: pulled }, connection_label: `${pulled} sources` });
    } finally {
      setPulling(false);
    }
  };

  const handleEmailConfirm = async () => {
    if (!bundleId) return;
    setPulling(true);
    try {
      const selectedIds = Array.from(selectedEmailIds);
      const detail = await endpoints.getDraftBundle(bundleId);
      for (const doc of detail.documents || []) {
        if (doc.source_id === 'email-inbox') {
          await endpoints.removeDocFromDraft(bundleId, doc.doc_id).catch(() => {});
        }
      }
      if (selectedIds.length > 0) {
        const result = await endpoints.filterEmails(selectedIds);
        if (result.documents?.length) {
          await endpoints.addDocsToDraft(bundleId, result.documents, 'email-inbox', connected?.connection_label || 'Email');
        }
      }
      await refreshBundle(bundleId);
    } catch (e) {
      setError(e.message);
    } finally {
      setPulling(false);
    }
  };

  const handleRemoveDoc = async (bid, docId) => {
    try {
      await endpoints.removeDocFromDraft(bid, docId);
      await refreshBundle(bid);
    } catch (e) {
      setError(e.message);
    }
  };

  const handleClearAll = async () => {
    if (!bundleId) return;
    if (!window.confirm('Delete all pulled files from this package?')) return;
    try {
      await endpoints.deleteDraftBundle(bundleId);
      setBundleId(null);
      setBundleDocs([]);
      setBundleTree([]);
      setConnected(null);
      setEmails([]);
      setSelectedEmailIds(new Set());
      setRelevanceByName({});
      setWarning('');
    } catch (e) {
      setError(e.message);
    }
  };

  const removeIrrelevant = async () => {
    if (!bundleId) return;
    const bad = bundleDocs.filter((d) => relevanceByName[d.filename] && relevanceByName[d.filename].relevant === false);
    for (const doc of bad) {
      await endpoints.removeDocFromDraft(bundleId, doc.doc_id).catch(() => {});
    }
    await refreshBundle(bundleId);
  };

  const runBundle = async () => {
    setError('');
    setWarning('');
    if (!bundleId || !bundleDocs.length) {
      setError('Pull at least one document first');
      return;
    }
    const irrelevant = bundleDocs.filter((d) => relevanceByName[d.filename]?.relevant === false);
    if (strictRelevance && irrelevant.length && irrelevant.length === bundleDocs.length) {
      setError('All pulled files look irrelevant — remove them and pull underwriting documents');
      return;
    }
    setRunning(true);
    try {
      const result = await endpoints.runDraftBundle(bundleId, useLlm, vertical, {
        insurance_line: insuranceLine,
        life_product_id: lifeProductId,
        life_coverage_id: lifeCoverageId,
        health_product_id: healthProductId,
        health_coverage_id: healthCoverageId,
        general_product_id: generalProductId,
        general_coverage_id: generalCoverageId,
        commercial_product_id: commercialProductId,
        commercial_coverage_id: coverageId,
        commercial_product_name: productName,
        commercial_coverage_name: coverageName,
        commercial_category_id: commercialCategoryId,
        insurance_company_id: insuranceCompanyId,
        insurance_company_name: insuranceCompanyName,
        strict_relevance: strictRelevance,
      });
      if (result.relevance?.irrelevant_count) {
        setWarning(result.relevance.warnings?.[0] || result.relevance.message || '');
      }
      if (result.job_id) {
        await onRunJob?.(result.job_id, vertical);
      } else {
        await onRunResult?.(result, vertical);
      }
    } catch (e) {
      const detail = e?.data?.detail;
      const msg = typeof detail === 'object' ? (detail.message || JSON.stringify(detail)) : (e.message || String(e));
      setError(msg);
    } finally {
      setRunning(false);
    }
  };

  // Auto-select first section when loaded
  useEffect(() => {
    if (sections.length && !sections.find((s) => s.id === categoryId)) {
      setCategoryId(sections[0].id);
    }
  }, [sections, categoryId]);

  return (
    <div className="space-y-3">
      <p className="text-[11px] text-slate-500">
        <span className="font-semibold text-emerald-400">Live</span> = IMAP / S3 / SFTP / folder when credentials are set.
        {' '}<span className="font-semibold text-slate-400">Lab sample</span> = Pacific Coast-style demos.
        {' '}<span className="font-semibold text-slate-500">Not contracted</span> = SharePoint, Drive, IVANS — simulation only.
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <select value={categoryId}
          onChange={(e) => { setCategoryId(e.target.value); setActiveSource(null); setConnected(null); setEmails([]); setSelectedEmailIds(new Set()); setConfig({}); setError(''); }}
          className="input-field min-w-0 flex-1 text-xs" aria-label="Source category">
          {sections.map((s) => (
            <option key={s.id} value={s.id}>{s.title}</option>
          ))}
        </select>
        <button type="button" onClick={pullAllInCategory} disabled={pulling}
          className="btn-secondary btn-sm shrink-0 text-[10px] disabled:opacity-40" title="Pull every zero-config source in this category">
          {pulling ? <Loader2 className="h-3 w-3 animate-spin" /> : <Cable className="h-3 w-3" />}
          Pull all
        </button>
        {bundleDocs.length > 0 && (
          <span className="shrink-0 rounded-full bg-brand/15 px-2 py-0.5 text-[10px] font-semibold text-brand">{bundleDocs.length}</span>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        {(activeSection?.sources || []).map((src) => {
          const sel = activeSource?.id === src.id;
          return (
            <button key={src.id} type="button"
              onClick={() => { setActiveSource(src); setError(''); setConnected(null); setEmails([]); setSelectedEmailIds(new Set()); setConfig({}); }}
              className={`flex items-center gap-2.5 rounded-lg border px-2.5 py-2 text-left transition ${
                sel ? 'border-brand/40 bg-brand/5 ring-1 ring-brand/20' : 'border-white/[0.06] bg-surface/30 hover:border-white/10 hover:bg-white/[0.02]'
              }`}>
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-white/[0.06] p-0.5">
                <ConnectorLogo sourceId={src.id} name={src.name} size={16} />
              </div>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-xs font-medium text-slate-200">{src.name}</span>
                <span className="block truncate text-[10px] text-slate-500">{src.honesty || src.description}</span>
              </span>
              <KindBadge kind={src.kind} />
            </button>
          );
        })}
      </div>

      {activeSource && needsConfig && !connected && (
        <div className="space-y-2 rounded-lg border border-white/[0.06] bg-surface/40 p-3">
          {activeSource.kind === 'catalog_stub' && (
            <p className="text-[11px] text-amber-300">This is not a live {activeSource.name} connection. Pull uses a lab demo package until that vendor is contracted.</p>
          )}
          {activeSource.kind === 'needs_config' && (
            <p className="text-[11px] text-amber-300">{activeSource.honesty}</p>
          )}
          {activeSource.config_fields.map((f) => (
            <div key={f.key}>
              <label className="mb-0.5 block text-[10px] text-slate-500">{f.label}</label>
              <input className="input-field w-full text-xs" placeholder={f.placeholder}
                value={config[f.key] || ''}
                onChange={(e) => setConfig((c) => ({ ...c, [f.key]: e.target.value }))} />
            </div>
          ))}
          <button type="button" onClick={() => pullSource(activeSource.id, config)} disabled={pulling}
            className="btn-primary btn-sm w-full text-xs disabled:opacity-40">
            {pulling ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Cable className="h-3 w-3" />}
            Pull from {activeSource.name}
          </button>
        </div>
      )}

      {activeSource && !needsConfig && !connected && (
        <div className="space-y-2">
          {activeSource.kind === 'needs_config' && (
            <p className="text-[11px] text-amber-300">{activeSource.honesty}</p>
          )}
          {activeSource.kind === 'lab_demo' && (
            <p className="text-[11px] text-slate-400">Lab sample package — not a live broker feed.</p>
          )}
          <button type="button" onClick={() => pullSource(activeSource.id, {})} disabled={pulling || (activeSource.kind === 'needs_config' && !activeSource.pullable)}
            className="btn-primary btn-sm w-full text-xs disabled:opacity-40">
            {pulling ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Cable className="h-3 w-3" />}
            Pull from {activeSource.name}
          </button>
        </div>
      )}

      {connected && (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-3 py-2">
          <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
          <span className="flex-1 text-xs text-emerald-300">
            {connected.accumulated
              ? `+${connected.accumulated.added} doc(s) · ${connected.accumulated.document_count} total`
              : `Connected · ${connected.connection_label}`}
          </span>
          {isEmailSource && emails.length > 0 && (
            <button type="button" onClick={handleEmailConfirm} disabled={pulling}
              className="text-[10px] text-brand transition hover:text-brand-light">
              {pulling ? <Loader2 className="h-3 w-3 animate-spin" /> : `Attach (${selectedEmailIds.size})`}
            </button>
          )}
        </div>
      )}

      {connected && isEmailSource && emails.length > 0 && (
        <div className="max-h-40 space-y-0.5 overflow-y-auto rounded-lg border border-white/[0.06] bg-surface/40 p-1.5">
          {emails.map((em) => {
            const checked = selectedEmailIds.has(em.id);
            return (
              <button key={em.id} type="button"
                onClick={() => setSelectedEmailIds((p) => { const n = new Set(p); n.has(em.id) ? n.delete(em.id) : n.add(em.id); return n; })}
                className={`flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-left text-xs ${
                  checked ? 'bg-brand/10 ring-1 ring-brand/20' : 'hover:bg-white/[0.02]'
                }`}>
                <span className={`flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded border ${
                  checked ? 'border-brand bg-brand text-white' : 'border-slate-600'
                }`}>
                  {checked && <Check className="h-2.5 w-2.5" />}
                </span>
                <span className="min-w-0 flex-1 truncate text-slate-200">{em.subject || '(no subject)'}</span>
                <span className="shrink-0 text-slate-500">{em.attachment_count}</span>
              </button>
            );
          })}
        </div>
      )}

      {bundleDocs.length > 0 && (
        <div className="space-y-2">
          <PulledFilesBrowser
            bundleId={bundleId}
            documents={bundleDocs}
            tree={bundleTree}
            relevanceByName={relevanceByName}
            onRemove={handleRemoveDoc}
            onRemoveAll={handleClearAll}
            onRemoveIrrelevant={removeIrrelevant}
          />
          <div className="flex items-center justify-between">
            <HintCheckbox
              hint={UI_HINTS.llmExtraction}
              label="LLM extraction"
              checked={useLlm}
              onChange={(e) => setUseLlm(e.target.checked)}
            />
            <Hint text={UI_HINTS.runPipeline}>
              <button type="button" onClick={runBundle} disabled={running}
                className="btn-primary btn-sm text-xs disabled:opacity-40">
                {running ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3 w-3" />}
                Run pipeline ({bundleDocs.length})
              </button>
            </Hint>
          </div>
        </div>
      )}

      {warning && <p className="rounded-lg bg-amber-500/10 px-3 py-1.5 text-xs text-amber-200">{warning}</p>}
      {error && <p className="rounded-lg bg-red-500/10 px-3 py-1.5 text-xs text-red-300">{error}</p>}
    </div>
  );
}
