import { useEffect, useMemo, useState } from 'react';
import {
  Cloud, FolderOpen, Database, FileText, CheckCircle2, Loader2, ChevronDown,
  Building2, PenLine, MessageSquare, Briefcase, Link2, Package, Inbox,
  ArrowLeftRight, Warehouse, Mail, Check,
} from 'lucide-react';
import { endpoints } from '../lib/api';
import { detectDocType } from '../lib/insuranceDocs';
import { groupSourcesByCategory } from '../lib/connectorBrands';
import ConnectorLogo from './ConnectorLogo';
import DocumentAccumulator from './DocumentAccumulator';

const SECTION_ICONS = {
  package: Package,
  cloud: Cloud,
  inbox: Inbox,
  exchange: ArrowLeftRight,
  policy: Building2,
  agency: Briefcase,
  crm: Briefcase,
  data: Database,
  signature: PenLine,
  messaging: MessageSquare,
  warehouse: Warehouse,
};

function SourceCard({ src, isActive, onConnect }) {
  return (
    <button
      type="button"
      onClick={() => onConnect(src)}
      className={`flex w-full items-center gap-4 rounded-xl border px-4 py-3 text-left transition ${
        isActive
          ? 'border-brand/40 bg-brand/5 ring-1 ring-brand/20'
          : 'border-white/[0.06] bg-surface-overlay/30 hover:border-white/10 hover:bg-white/[0.02]'
      }`}
    >
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-white/[0.06] p-1">
        <ConnectorLogo sourceId={src.id} name={src.name} size={28} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="font-medium text-sm text-slate-100">{src.name}</p>
        <p className="truncate text-xs text-slate-500">{src.description}</p>
      </div>
      <span className="shrink-0 rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
        Ready
      </span>
    </button>
  );
}

function EmailPicker({ emails, selectedIds, onToggle, onSelectAll }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-slate-400">{emails.length} email(s) found</p>
        <button type="button" onClick={onSelectAll}
          className="text-xs text-brand hover:text-brand-light transition">
          {selectedIds.size === emails.length ? 'Deselect all' : 'Select all'}
        </button>
      </div>
      <div className="max-h-64 space-y-1 overflow-y-auto rounded-lg border border-white/[0.06] bg-surface/40 p-2">
        {emails.map((em) => {
          const checked = selectedIds.has(em.id);
          return (
            <button
              key={em.id}
              type="button"
              onClick={() => onToggle(em.id)}
              className={`flex w-full items-start gap-3 rounded-lg px-3 py-2.5 text-left transition ${
                checked
                  ? 'bg-brand/10 ring-1 ring-brand/20'
                  : 'hover:bg-white/[0.02]'
              }`}
            >
              <div className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border ${
                checked ? 'border-brand bg-brand text-white' : 'border-slate-600'
              }`}>
                {checked && <Check className="h-3 w-3" />}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm text-slate-200 truncate">{em.subject || '(no subject)'}</p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-[10px] text-slate-500 truncate">{em.from}</span>
                  {em.date && <span className="text-[10px] text-slate-600">·</span>}
                  <span className="text-[10px] text-slate-600">{em.date?.split(',')[0] || ''}</span>
                </div>
              </div>
              <span className="shrink-0 text-[10px] text-slate-500 mt-0.5">
                {em.attachment_count} doc{em.attachment_count !== 1 ? 's' : ''}
              </span>
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
  const [showManual, setShowManual] = useState(false);

  // Draft bundle state (persistent across source switches)
  const [bundleId, setBundleId] = useState(null);
  const [bundleDocs, setBundleDocs] = useState([]);
  const [bundleLoading, setBundleLoading] = useState(false);

  const sections = useMemo(() => groupSourcesByCategory(sources), [sources]);
  const activeSection = sections.find((s) => s.id === categoryId) || sections[0];
  const SectionIcon = activeSection ? (SECTION_ICONS[activeSection.icon] || FolderOpen) : FolderOpen;

  const isEmailSource = activeSource?.id === 'email-inbox';
  const hasEmails = emails.length > 0;
  const selectedCount = selectedEmailIds.size;

  // Rebuild file list from selected emails
  const rebuildFilesFromSelection = (emailList, ids) => {
    const selected = new Set(ids);
    const docs = [];
    for (const em of emailList) {
      if (selected.has(em.id)) {
        for (const d of (em.documents || [])) {
          docs.push({
            ...d,
            id: `${em.id}-${d.filename}`,
            email_subject: em.subject,
            slot: detectDocType(d.filename, d.encoding === 'utf-8' ? d.content.slice(0, 4000) : ''),
          });
        }
      }
    }
    return docs;
  };

  const loadSources = async () => {
    try {
      const r = await endpoints.insuranceSources();
      setSources(r.sources || []);
    } catch { /* noop */ }
  };

  useState(() => { loadSources(); }, []);

  // Ensure a draft bundle exists
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

  // Refresh bundle documents from server
  const refreshBundle = async (bid) => {
    if (!bid) return;
    try {
      const detail = await endpoints.getDraftBundle(bid);
      setBundleDocs(detail.documents || []);
    } catch { /* noop */ }
  };

  // Pull source and accumulate into draft bundle
  const pullSource = async (sourceId, cfg) => {
    setPulling(true);
    setError('');
    try {
      const bid = await ensureBundle();
      if (!bid) return;

      const pullCfg = { ...cfg, bundle_id: bid };
      const result = await endpoints.pullInsuranceSource(sourceId, pullCfg);

      setConnected(result);

      // If email source, show email picker for selection
      if (result.emails?.length) {
        setEmails(result.emails);
        const allIds = new Set(result.emails.map((e) => e.id));
        setSelectedEmailIds(allIds);
        // For emails, we accumulate the full set initially — user can then deselect
        // The pull already accumulated all docs into the bundle
      }

      // Refresh bundle doc list from server
      await refreshBundle(bid);
    } catch (e) {
      setError(e.message);
    } finally {
      setPulling(false);
    }
  };

  const handleConnect = async (source) => {
    setActiveSource(source);
    setError('');
    setConnected(null);
    setEmails([]);
    setSelectedEmailIds(new Set());
    setConfig({});
    if (source.type === 'library') {
      await pullSource(source.id, {});
    }
  };

  const handleCategoryChange = (id) => {
    setCategoryId(id);
    setActiveSource(null);
    setConnected(null);
    setEmails([]);
    setSelectedEmailIds(new Set());
    setConfig({});
    setError('');
    // NOTE: bundle state is NOT cleared — documents persist across source switches
  };

  // Email selection: re-pull with filtered email IDs into the bundle
  const handleToggleEmail = (emailId) => {
    setSelectedEmailIds((prev) => {
      const next = new Set(prev);
      if (next.has(emailId)) {
        next.delete(emailId);
      } else {
        next.add(emailId);
      }
      return next;
    });
  };

  const handleSelectAllEmails = () => {
    if (selectedEmailIds.size === emails.length) {
      setSelectedEmailIds(new Set());
    } else {
      setSelectedEmailIds(new Set(emails.map((e) => e.id)));
    }
  };

  // After email selection changes, re-filter: remove old email docs, add selected
  const handleEmailConfirm = async () => {
    if (!bundleId || !isEmailSource) return;
    setPulling(true);
    try {
      // Filter emails via API
      const selectedIds = Array.from(selectedEmailIds);
      if (selectedIds.length === 0) {
        // Remove all email docs from bundle
        const detail = await endpoints.getDraftBundle(bundleId);
        for (const doc of (detail.documents || [])) {
          if (doc.source_id === 'email-inbox') {
            await endpoints.removeDocFromDraft(bundleId, doc.doc_id).catch(() => {});
          }
        }
      } else {
        const result = await endpoints.filterEmails(selectedIds);
        // Remove old email docs, add new ones
        const detail = await endpoints.getDraftBundle(bundleId);
        for (const doc of (detail.documents || [])) {
          if (doc.source_id === 'email-inbox') {
            await endpoints.removeDocFromDraft(bundleId, doc.doc_id).catch(() => {});
          }
        }
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

  const handlePull = () => {
    if (!activeSource) return;
    pullSource(activeSource.id, config);
  };

  const handleRemoveDoc = async (bid, docId) => {
    try {
      await endpoints.removeDocFromDraft(bid, docId);
      await refreshBundle(bid);
    } catch (e) {
      setError(e.message);
    }
  };

  const handleClearAll = async (bid) => {
    try {
      await endpoints.deleteDraftBundle(bid);
      setBundleId(null);
      setBundleDocs([]);
      setConnected(null);
      setActiveSource(null);
      setEmails([]);
      setSelectedEmailIds(new Set());
    } catch (e) {
      setError(e.message);
    }
  };

  const handleRunPipeline = async (bid, llm) => {
    try {
      const result = await endpoints.runDraftBundle(bid, llm);
      // Reset state after successful run
      setBundleId(null);
      setBundleDocs([]);
      setConnected(null);
      setActiveSource(null);
      setEmails([]);
      setSelectedEmailIds(new Set());
      // Trigger parent refresh
      await onSubmit?.({ _jobId: result.job_id });
    } catch (e) {
      setError(e.message);
    }
  };

  const handleManualUpload = async (e) => {
    const { readFileForUpload, detectDocType: detect } = await import('../lib/insuranceDocs');
    const incoming = await Promise.all(
      Array.from(e.target.files || []).map(async (file) => {
        const doc = await readFileForUpload(file);
        return {
          filename: doc.filename,
          content: doc.content,
          encoding: doc.encoding,
        };
      }),
    );
    if (!incoming.length) return;

    const bid = await ensureBundle();
    if (!bid) return;

    try {
      await endpoints.addDocsToDraft(bid, incoming, 'manual-upload', 'Manual upload');
      await refreshBundle(bid);
      setConnected({ connection_label: 'Manual upload', file_count: incoming.length });
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="glass-card overflow-hidden">
      <div className="border-b border-white/[0.06] px-5 py-4 sm:px-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <Link2 className="h-5 w-5 text-insurance" />
            <div>
              <h3 className="font-semibold">Connect input source</h3>
              <p className="text-xs text-slate-500">Pull from one or more sources — documents accumulate until you run</p>
            </div>
          </div>
          <div className="min-w-[220px]">
            <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              Service category
            </label>
            <select
              className="input-field text-sm"
              value={categoryId}
              onChange={(e) => handleCategoryChange(e.target.value)}
            >
              {sections.map((s) => (
                <option key={s.id} value={s.id}>{s.title}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="space-y-6 p-5 sm:p-6">
        {activeSection && (
          <div className="flex items-start gap-3 rounded-xl bg-white/[0.02] px-4 py-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-insurance/10">
              <SectionIcon className="h-4 w-4 text-insurance" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-200">{activeSection.title}</p>
              <p className="text-xs text-slate-500">{activeSection.subtitle}</p>
            </div>
          </div>
        )}

        <div className="space-y-2">
          {(activeSection?.sources || []).map((src) => (
            <SourceCard
              key={src.id}
              src={src}
              isActive={activeSource?.id === src.id}
              onConnect={handleConnect}
            />
          ))}
        </div>

        {activeSource && activeSource.config_fields?.length > 0 && !connected && (
          <div className="rounded-xl border border-white/[0.08] bg-surface/40 p-4 space-y-3">
            <div className="flex items-center gap-3">
              <ConnectorLogo sourceId={activeSource.id} name={activeSource.name} size={32} />
              <p className="text-sm font-medium">Connect to {activeSource.name}</p>
            </div>
            {activeSource.config_fields.map((f) => (
              <div key={f.key}>
                <label className="mb-1 block text-xs text-slate-500">{f.label}</label>
                <input
                  className="input-field text-sm"
                  placeholder={f.placeholder}
                  value={config[f.key] || ''}
                  onChange={(e) => setConfig((c) => ({ ...c, [f.key]: e.target.value }))}
                />
              </div>
            ))}
            <button type="button" onClick={handlePull} disabled={pulling} className="btn-primary btn-sm">
              {pulling ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Connect & pull files'}
            </button>
          </div>
        )}

        {connected && (
          <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
            <div className="flex items-center gap-2 text-emerald-400">
              <CheckCircle2 className="h-5 w-5" />
              <span className="font-semibold text-sm">
                {connected.accumulated
                  ? `Added ${connected.accumulated.added} doc(s) to bundle`
                  : `Connected · ${connected.connection_label}`}
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-400">
              {connected.accumulated
                ? `${connected.accumulated.document_count} total document(s) in bundle`
                : `${connected.file_count} document${connected.file_count !== 1 ? 's' : ''} ready`}
              {isEmailSource && hasEmails && ` from ${selectedCount} email(s)`}
            </p>
          </div>
        )}

        {connected && isEmailSource && hasEmails && (
          <div className="space-y-3">
            <EmailPicker
              emails={emails}
              selectedIds={selectedEmailIds}
              onToggle={handleToggleEmail}
              onSelectAll={handleSelectAllEmails}
            />
            <button
              type="button"
              onClick={handleEmailConfirm}
              disabled={pulling}
              className="btn-primary btn-sm"
            >
              {pulling ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Update selection'}
            </button>
          </div>
        )}

        {/* Persistent document accumulator — survives source switches */}
        {bundleId && (
          <DocumentAccumulator
            bundleId={bundleId}
            documents={bundleDocs}
            onRemove={handleRemoveDoc}
            onRunPipeline={handleRunPipeline}
            onClearAll={handleClearAll}
            loading={loading}
            useLlm={useLlm}
            onToggleLlm={setUseLlm}
          />
        )}

        {error && <p className="rounded-xl bg-red-500/10 px-4 py-2 text-sm text-red-300">{error}</p>}

        {/* Legacy quick-run for single-source flow (no bundle) */}
        {!bundleId && (
          <div className="flex items-center justify-between border-t border-white/[0.06] pt-4">
            <label className="flex items-center gap-2 text-sm text-slate-400">
              <input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} className="rounded" />
              LLM enhancement
            </label>
            <button
              type="button"
              onClick={async () => {
                // Fallback: create bundle and run immediately
                const bid = await ensureBundle();
                if (bid && bundleDocs.length > 0) {
                  handleRunPipeline(bid, useLlm);
                }
              }}
              disabled={loading || !bundleDocs.length}
              className="btn-primary"
            >
              {loading ? 'Submitting…' : 'Run underwriting pipeline'}
            </button>
          </div>
        )}

        <button
          type="button"
          onClick={() => setShowManual((v) => !v)}
          className="flex items-center gap-1 text-xs text-slate-600 hover:text-slate-400"
        >
          <ChevronDown className={`h-3.5 w-3.5 transition ${showManual ? 'rotate-180' : ''}`} />
          Manual file upload
        </button>

        {showManual && (
          <label className="btn-secondary inline-flex cursor-pointer text-xs">
            Choose files
            <input
              type="file"
              multiple
              className="hidden"
              accept=".xml,.json,.pdf,.txt,.md"
              onChange={handleManualUpload}
            />
          </label>
        )}
      </div>
    </div>
  );
}
