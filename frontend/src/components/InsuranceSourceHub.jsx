import { useEffect, useMemo, useState } from 'react';
import {
  Cloud, FolderOpen, Database, FileText, CheckCircle2, Loader2,
  Building2, PenLine, MessageSquare, Briefcase, Link2, Package, Inbox,
  ArrowLeftRight, Warehouse, Mail, Check, Upload, X,
} from 'lucide-react';
import { endpoints } from '../lib/api';
import { detectDocType } from '../lib/insuranceDocs';
import { groupSourcesByCategory } from '../lib/connectorBrands';
import { UI_HINTS } from '../lib/uiHints';
import ConnectorLogo from './ConnectorLogo';
import { HintCheckbox } from './ui';

const SECTION_ICONS = {
  package: Package, cloud: Cloud, inbox: Inbox, exchange: ArrowLeftRight,
  policy: Building2, agency: Briefcase, crm: Briefcase, data: Database,
  signature: PenLine, messaging: MessageSquare, warehouse: Warehouse,
};

function EmailPicker({ emails, selectedIds, onToggle, onSelectAll }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs text-slate-400">{emails.length} email(s)</p>
        <button type="button" onClick={onSelectAll}
          className="text-xs text-brand hover:text-brand-light">
          {selectedIds.size === emails.length ? 'Deselect all' : 'Select all'}
        </button>
      </div>
      <div className="max-h-48 space-y-0.5 overflow-y-auto rounded-lg border border-white/[0.06] bg-surface/40 p-1.5">
        {emails.map((em) => {
          const checked = selectedIds.has(em.id);
          return (
            <button key={em.id} type="button" onClick={() => onToggle(em.id)}
              className={`flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left transition text-xs ${
                checked ? 'bg-brand/10 ring-1 ring-brand/20' : 'hover:bg-white/[0.02]'
              }`}>
              <div className={`flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded border ${
                checked ? 'border-brand bg-brand text-white' : 'border-slate-600'
              }`}>
                {checked && <Check className="h-2.5 w-2.5" />}
              </div>
              <span className="truncate text-slate-200 flex-1">{em.subject || '(no subject)'}</span>
              <span className="shrink-0 text-slate-500">{em.attachment_count}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default function InsuranceSourceHub({ onSubmit, loading }) {
  const [sources, setSources] = useState([]);
  const [categoryId, setCategoryId] = useState('Document Storage');
  const [activeSource, setActiveSource] = useState(null);
  const [config, setConfig] = useState({});
  const [connected, setConnected] = useState(null);
  const [emails, setEmails] = useState([]);
  const [selectedEmailIds, setSelectedEmailIds] = useState(new Set());
  const [pulling, setPulling] = useState(false);
  const [useLlm, setUseLlm] = useState(true);
  const [error, setError] = useState('');

  const [bundleId, setBundleId] = useState(null);
  const [bundleDocs, setBundleDocs] = useState([]);

  const sections = useMemo(() => groupSourcesByCategory(sources), [sources]);
  const activeSection = sections.find((s) => s.id === categoryId) || sections[0];
  const SectionIcon = activeSection ? (SECTION_ICONS[activeSection.icon] || FolderOpen) : FolderOpen;
  const isEmailSource = activeSource?.id === 'email-inbox';
  const hasEmails = emails.length > 0;

  const loadSources = async () => {
    try { const r = await endpoints.insuranceSources(); setSources(r.sources || []); }
    catch { /* noop */ }
  };

  useEffect(() => { loadSources(); }, []);

  const ensureBundle = async () => {
    if (bundleId) return bundleId;
    try {
      const result = await endpoints.createDraftBundle('New submission');
      setBundleId(result.bundle_id);
      return result.bundle_id;
    } catch (e) { setError(e.message); return null; }
  };

  const refreshBundle = async (bid) => {
    if (!bid) return;
    try { const detail = await endpoints.getDraftBundle(bid); setBundleDocs(detail.documents || []); }
    catch { /* noop */ }
  };

  const pullSource = async (sourceId, cfg) => {
    setPulling(true); setError('');
    try {
      const bid = await ensureBundle();
      if (!bid) return;
      const result = await endpoints.pullInsuranceSource(sourceId, { ...cfg, bundle_id: bid });
      setConnected(result);
      if (result.emails?.length) {
        setEmails(result.emails);
        setSelectedEmailIds(new Set(result.emails.map((e) => e.id)));
      }
      await refreshBundle(bid);
    } catch (e) { setError(e.message); }
    finally { setPulling(false); }
  };

  const handleConnect = async (source) => {
    setActiveSource(source); setError(''); setConnected(null); setEmails([]);
    setSelectedEmailIds(new Set()); setConfig({});
    if (source.type === 'library') await pullSource(source.id, {});
  };

  const handleEmailConfirm = async () => {
    if (!bundleId || !isEmailSource) return;
    setPulling(true);
    try {
      const selectedIds = Array.from(selectedEmailIds);
      const detail = await endpoints.getDraftBundle(bundleId);
      for (const doc of (detail.documents || [])) {
        if (doc.source_id === 'email-inbox')
          await endpoints.removeDocFromDraft(bundleId, doc.doc_id).catch(() => {});
      }
      if (selectedIds.length > 0) {
        const result = await endpoints.filterEmails(selectedIds);
        if (result.documents?.length)
          await endpoints.addDocsToDraft(bundleId, result.documents, 'email-inbox', connected?.connection_label || 'Email');
      }
      await refreshBundle(bundleId);
    } catch (e) { setError(e.message); }
    finally { setPulling(false); }
  };

  const handleRemoveDoc = async (bid, docId) => {
    try { await endpoints.removeDocFromDraft(bid, docId); await refreshBundle(bid); }
    catch (e) { setError(e.message); }
  };

  const handleClearAll = async (bid) => {
    try { await endpoints.deleteDraftBundle(bid); setBundleId(null); setBundleDocs([]); setConnected(null); setActiveSource(null); setEmails([]); setSelectedEmailIds(new Set()); }
    catch (e) { setError(e.message); }
  };

  const handleRunPipeline = async (bid, llm) => {
    try {
      const result = await endpoints.runDraftBundle(bid, llm);
      setBundleId(null); setBundleDocs([]); setConnected(null); setActiveSource(null);
      setEmails([]); setSelectedEmailIds(new Set());
      await onSubmit?.({ _jobId: result.job_id });
    } catch (e) { setError(e.message); }
  };

  const handleManualUpload = async (e) => {
    const { readFileForUpload } = await import('../lib/insuranceDocs');
    const incoming = await Promise.all(
      Array.from(e.target.files || []).map(async (file) => {
        const doc = await readFileForUpload(file);
        return { filename: doc.filename, content: doc.content, encoding: doc.encoding };
      }),
    );
    if (!incoming.length) return;
    const bid = await ensureBundle();
    if (!bid) return;
    try {
      await endpoints.addDocsToDraft(bid, incoming, 'manual-upload', 'Manual upload');
      await refreshBundle(bid);
      setConnected({ connection_label: 'Manual upload', file_count: incoming.length });
    } catch (err) { setError(err.message); }
  };

  const totalDocs = bundleDocs.length;

  return (
    <div className="rounded-xl border border-white/[0.06] bg-surface-overlay/40">
      {/* Header row */}
      <div className="flex items-center gap-3 border-b border-white/[0.06] px-4 py-2.5">
        <Link2 className="h-4 w-4 text-insurance shrink-0" />
        <span className="text-sm font-semibold text-slate-200">Input sources</span>
        <div className="ml-auto flex items-center gap-1">
          <select
            value={categoryId}
            onChange={(e) => { setCategoryId(e.target.value); setActiveSource(null); setConnected(null); setEmails([]); setSelectedEmailIds(new Set()); setConfig({}); setError(''); }}
            className="input-field w-40 text-[11px]"
            aria-label="Source category"
          >
            {sections.map((s) => (
              <option key={s.id} value={s.id}>{s.title}</option>
            ))}
          </select>
          {totalDocs > 0 && (
            <span className="shrink-0 rounded-full bg-brand/15 px-2 py-0.5 text-[10px] font-semibold text-brand">
              {totalDocs}
            </span>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="p-3 space-y-3">
        {/* Source grid */}
        <div className="flex flex-col gap-1.5">
          {(activeSection?.sources || []).map((src) => {
            const sel = activeSource?.id === src.id;
            return (
              <button key={src.id} type="button" onClick={() => handleConnect(src)}
                className={`flex items-center gap-2.5 rounded-lg border px-2.5 py-2 text-left transition ${
                  sel
                    ? 'border-brand/40 bg-brand/5 ring-1 ring-brand/20'
                    : 'border-white/[0.06] bg-surface/30 hover:border-white/10 hover:bg-white/[0.02]'
                }`}>
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-white/[0.06] p-0.5">
                  <ConnectorLogo sourceId={src.id} name={src.name} size={16} />
                </div>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-xs font-medium text-slate-200">{src.name}</span>
                  <span className="block truncate text-[10px] text-slate-500">{src.description}</span>
                </span>
              </button>
            );
          })}
        </div>

        {/* Config inline */}
        {activeSource && activeSource.config_fields?.length > 0 && !connected && (
          <div className="flex flex-wrap items-end gap-2 rounded-lg border border-white/[0.06] bg-surface/40 p-3">
            {activeSource.config_fields.map((f) => (
              <div key={f.key} className="min-w-0 flex-1 basis-40">
                <label className="mb-0.5 block text-[10px] text-slate-500">{f.label}</label>
                <input className="input-field text-xs w-full" placeholder={f.placeholder}
                  value={config[f.key] || ''}
                  onChange={(e) => setConfig((c) => ({ ...c, [f.key]: e.target.value }))} />
              </div>
            ))}
            <button type="button" onClick={() => pullSource(activeSource.id, config)}
              disabled={pulling} className="btn-primary btn-sm text-xs shrink-0">
              {pulling ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : 'Pull'}
            </button>
          </div>
        )}

        {/* Connected badge */}
        {connected && (
          <div className="flex items-center gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-3 py-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
            <span className="text-xs text-emerald-300 flex-1">
              {connected.accumulated
                ? `+${connected.accumulated.added} doc(s) · ${connected.accumulated.document_count} total`
                : `Connected · ${connected.connection_label}`}
            </span>
            {connected.file_count != null && (
              <span className="text-[10px] text-slate-500">{connected.file_count} file(s)</span>
            )}
            {isEmailSource && hasEmails && (
              <button type="button" onClick={handleEmailConfirm} disabled={pulling}
                className="text-[10px] text-brand hover:text-brand-light">
                {pulling ? <Loader2 className="h-3 w-3 animate-spin" /> : `Update (${selectedEmailIds.size})`}
              </button>
            )}
          </div>
        )}

        {/* Email picker */}
        {connected && isEmailSource && hasEmails && <EmailPicker emails={emails} selectedIds={selectedEmailIds} onToggle={(id) => setSelectedEmailIds((p) => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n; })} onSelectAll={() => setSelectedEmailIds((p) => p.size === emails.length ? new Set() : new Set(emails.map((e) => e.id)))} />}

        {/* Error */}
        {error && <p className="rounded-lg bg-red-500/10 px-3 py-1.5 text-xs text-red-300">{error}</p>}

        {/* Manual upload */}
        <label className="inline-flex cursor-pointer items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition">
          <Upload className="h-3.5 w-3.5" />
          Upload files
          <input type="file" multiple className="hidden" accept=".xml,.json,.pdf,.txt,.md" onChange={handleManualUpload} />
        </label>
      </div>

      {/* Document accumulator footer */}
      {bundleId && totalDocs > 0 && (
        <div className="border-t border-white/[0.06] px-3 py-2">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Package className="h-3.5 w-3.5 text-brand" />
              <span className="text-xs font-medium text-slate-300">{totalDocs} document{totalDocs !== 1 ? 's' : ''}</span>
              <span className="rounded-full bg-brand/15 px-1.5 py-0.5 text-[9px] font-semibold text-brand">Multi-source</span>
            </div>
            <div className="flex items-center gap-2">
              <HintCheckbox
                hint={UI_HINTS.llmExtraction}
                label="LLM"
                checked={useLlm}
                onChange={(e) => setUseLlm(e.target.checked)}
              />
              <button type="button" onClick={() => handleClearAll(bundleId)}
                className="text-[10px] text-red-400/70 hover:text-red-400">Clear</button>
            </div>
          </div>

          {/* Doc list compact */}
          <div className="mb-2 max-h-32 space-y-0.5 overflow-y-auto">
            {bundleDocs.map((doc) => (
              <div key={doc.doc_id} className="flex items-center gap-2 rounded-md bg-white/[0.02] px-2 py-1 group">
                <FileText className="h-3 w-3 shrink-0 text-insurance" />
                <span className="truncate text-[11px] text-slate-400 flex-1">{doc.filename}</span>
                <span className="text-[9px] text-slate-600 shrink-0">{doc.source_id}</span>
                <button type="button" onClick={() => handleRemoveDoc(bundleId, doc.doc_id)}
                  className="opacity-0 group-hover:opacity-100 text-slate-600 hover:text-red-400 transition">
                  <X className="h-3 w-3" />
                </button>
              </div>
            ))}
          </div>

          <button type="button" onClick={() => handleRunPipeline(bundleId, useLlm)}
            disabled={loading} className="btn-primary w-full text-xs py-2">
            {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : `Run pipeline (${totalDocs} docs)`}
          </button>
        </div>
      )}
    </div>
  );
}
