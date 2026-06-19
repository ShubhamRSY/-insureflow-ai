import { useEffect, useMemo, useState } from 'react';
import {
  Cloud, FolderOpen, Database, FileText, CheckCircle2, Loader2, ChevronDown,
  Building2, PenLine, MessageSquare, Briefcase, Link2, Package, Inbox, ArrowLeftRight, Warehouse,
} from 'lucide-react';
import { endpoints } from '../lib/api';
import { buildSubmissionPayload, validatePackage, detectDocType } from '../lib/insuranceDocs';
import { groupSourcesByCategory } from '../lib/connectorBrands';
import ConnectorLogo from './ConnectorLogo';

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

export default function InsuranceSourceHub({ onSubmit, loading }) {
  const [sources, setSources] = useState([]);
  const [categoryId, setCategoryId] = useState('Document Storage');
  const [activeSource, setActiveSource] = useState(null);
  const [config, setConfig] = useState({});
  const [connected, setConnected] = useState(null);
  const [files, setFiles] = useState([]);
  const [pulling, setPulling] = useState(false);
  const [useLlm, setUseLlm] = useState(true);
  const [error, setError] = useState('');
  const [showManual, setShowManual] = useState(false);

  const sections = useMemo(() => groupSourcesByCategory(sources), [sources]);
  const activeSection = sections.find((s) => s.id === categoryId) || sections[0];
  const SectionIcon = activeSection ? (SECTION_ICONS[activeSection.icon] || FolderOpen) : FolderOpen;

  useEffect(() => {
    endpoints.insuranceSources().then((r) => setSources(r.sources || [])).catch(() => {});
  }, []);

  useEffect(() => {
    if (sections.length && !sections.find((s) => s.id === categoryId)) {
      setCategoryId(sections[0].id);
    }
  }, [sections, categoryId]);

  const pullSource = async (sourceId, cfg) => {
    setPulling(true);
    setError('');
    try {
      const result = await endpoints.pullInsuranceSource(sourceId, cfg);
      setConnected(result);
      const mapped = (result.documents || []).map((d, i) => ({
        ...d,
        id: `${d.filename}-${i}`,
        slot: detectDocType(d.filename, d.encoding === 'utf-8' ? d.content.slice(0, 4000) : ''),
      }));
      setFiles(mapped);
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
    setFiles([]);
    setConfig({});
    if (source.type === 'library') {
      await pullSource(source.id, {});
    }
  };

  const handleCategoryChange = (id) => {
    setCategoryId(id);
    setActiveSource(null);
    setConnected(null);
    setFiles([]);
    setConfig({});
    setError('');
  };

  const handlePull = () => {
    if (!activeSource) return;
    pullSource(activeSource.id, config);
  };

  const handleSubmit = async () => {
    const validation = validatePackage(files);
    if (validation) { setError(validation); return; }
    setError('');
    await onSubmit(buildSubmissionPayload(files, useLlm));
    setFiles([]);
    setConnected(null);
    setActiveSource(null);
  };

  return (
    <div className="glass-card overflow-hidden">
      <div className="border-b border-white/[0.06] px-5 py-4 sm:px-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <Link2 className="h-5 w-5 text-insurance" />
            <div>
              <h3 className="font-semibold">Connect input source</h3>
              <p className="text-xs text-slate-500">Pick a category, then choose your provider</p>
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
              <span className="font-semibold text-sm">Connected · {connected.connection_label}</span>
            </div>
            <p className="mt-1 text-xs text-slate-400">{connected.file_count} documents ready</p>
            <ul className="mt-3 max-h-40 space-y-1 overflow-y-auto rounded-lg border border-white/[0.06] bg-surface/40 p-2">
              {files.map((f) => (
                <li key={f.id} className="flex items-center gap-2 px-2 py-1.5 text-xs">
                  <FileText className="h-3.5 w-3.5 shrink-0 text-insurance" />
                  <span className="truncate text-slate-300">{f.filename}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {error && <p className="rounded-xl bg-red-500/10 px-4 py-2 text-sm text-red-300">{error}</p>}

        <div className="flex flex-wrap items-center justify-between gap-4 border-t border-white/[0.06] pt-4">
          <label className="flex items-center gap-2 text-sm text-slate-400">
            <input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} className="rounded" />
            LLM enhancement
          </label>
          <button type="button" onClick={handleSubmit} disabled={loading || !files.length} className="btn-primary">
            {loading ? 'Submitting…' : 'Run underwriting pipeline'}
          </button>
        </div>

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
              onChange={async (e) => {
                const { readFileForUpload, detectDocType } = await import('../lib/insuranceDocs');
                const incoming = await Promise.all(
                  Array.from(e.target.files || []).map(async (file) => {
                    const doc = await readFileForUpload(file);
                    return {
                      ...doc,
                      id: file.name,
                      slot: detectDocType(file.name, doc.encoding === 'utf-8' ? doc.content.slice(0, 4000) : ''),
                    };
                  }),
                );
                setFiles(incoming);
                setConnected({ connection_label: 'Manual upload', file_count: incoming.length });
              }}
            />
          </label>
        )}
      </div>
    </div>
  );
}
