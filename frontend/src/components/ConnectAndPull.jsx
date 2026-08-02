import { useEffect, useState } from 'react';
import { Cable, Check, CheckCircle2, FileText, Loader2, Play, X } from 'lucide-react';
import { endpoints } from '../lib/api';
import ConnectorLogo from './ConnectorLogo';
import { groupSourcesByCategory } from '../lib/connectorBrands';

/**
 * "Connect & pull" source hub shared across verticals (insurance, mortgage,
 * lending). Lists connectors + demo packages from the vertical-aware
 * /api/insurance/sources endpoint, accumulates pulled documents into a draft
 * bundle, and runs the bundle through that vertical's pipeline.
 *
 * onRunJob — async verticals (insurance, mortgage) that return a job_id
 * onRunResult — inline verticals (lending) that return the result directly
 */
export default function ConnectAndPull({ vertical = 'insurance', onRunJob, onRunResult }) {
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
  const [useLlm, setUseLlm] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState('');

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
      setBundleDocs(detail.documents || []);
    } catch { /* noop */ }
  };

  const pullSource = async (sourceId, cfg) => {
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

  const runBundle = async () => {
    setError('');
    if (!bundleId || !bundleDocs.length) {
      setError('Pull at least one document first');
      return;
    }
    setRunning(true);
    try {
      const result = await endpoints.runDraftBundle(bundleId, useLlm, vertical);
      if (result.job_id) {
        await onRunJob?.(result.job_id, vertical);
      } else {
        await onRunResult?.(result, vertical);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <select value={categoryId}
          onChange={(e) => { setCategoryId(e.target.value); setActiveSource(null); setConnected(null); setEmails([]); setSelectedEmailIds(new Set()); setConfig({}); setError(''); }}
          className="input-field w-full text-xs" aria-label="Source category">
          {sections.map((s) => (
            <option key={s.id} value={s.id}>{s.title}</option>
          ))}
        </select>
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
                <span className="block truncate text-[10px] text-slate-500">{src.description}</span>
              </span>
            </button>
          );
        })}
      </div>

      {activeSource && activeSource.config_fields?.length > 0 && !connected && (
        <div className="space-y-2 rounded-lg border border-white/[0.06] bg-surface/40 p-3">
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
        <div className="rounded-lg border border-white/[0.06] bg-surface/40 p-2">
          <p className="mb-1 px-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Pulled documents</p>
          <div className="max-h-32 space-y-0.5 overflow-y-auto">
            {bundleDocs.map((doc) => (
              <div key={doc.doc_id} className="group flex items-center gap-2 rounded-md px-2 py-1">
                <FileText className="h-3 w-3 shrink-0 text-insurance" />
                <span className="min-w-0 flex-1 truncate text-[11px] text-slate-300">{doc.filename}</span>
                <span className="shrink-0 text-[9px] text-slate-600">{doc.source_id}</span>
                <button type="button" onClick={() => handleRemoveDoc(bundleId, doc.doc_id)}
                  className="shrink-0 text-slate-600 transition hover:text-red-400">
                  <X className="h-3 w-3" />
                </button>
              </div>
            ))}
          </div>
          <div className="mt-2 flex items-center justify-between">
            <label className="flex items-center gap-1.5 text-[10px] text-slate-500">
              <input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} className="rounded" />
              LLM extraction
            </label>
            <button type="button" onClick={runBundle} disabled={running}
              className="btn-primary btn-sm text-xs disabled:opacity-40">
              {running ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3 w-3" />}
              Run pipeline ({bundleDocs.length})
            </button>
          </div>
        </div>
      )}

      {error && <p className="rounded-lg bg-red-500/10 px-3 py-1.5 text-xs text-red-300">{error}</p>}
    </div>
  );
}
