import { useRef, useState } from 'react';
import {
  FileUp, FolderOpen, FlaskConical, Cable, Loader2, Home, Building2, Upload, X, FileText, Wallet,
} from 'lucide-react';
import { readFileForUpload } from '../lib/insuranceDocs';
import { UI_HINTS } from '../lib/uiHints';
import ConnectAndPull from './ConnectAndPull';
import { HintCheckbox } from './ui';

const TABS = [
  { id: 'upload', label: 'Upload', icon: FileUp },
  { id: 'directory', label: 'Server path', icon: FolderOpen },
  { id: 'connect', label: 'Connect & pull', icon: Cable },
  { id: 'samples', label: 'Samples', icon: FlaskConical },
];

const ACCENTS = {
  mortgage: {
    tab: 'bg-mortgage/15 text-mortgage border border-b-0 border-mortgage/30 -mb-px',
    drop: 'border-mortgage bg-mortgage/10',
    dropIcon: 'text-mortgage',
    file: 'text-mortgage',
    chip: 'bg-mortgage/20 text-mortgage ring-1 ring-mortgage/30',
    boxIcon: 'bg-mortgage/15',
    badge: 'text-mortgage/80',
    hover: 'hover:border-mortgage/35 hover:bg-mortgage/5',
    action: 'text-mortgage',
    spinner: 'text-mortgage',
  },
  lending: {
    tab: 'bg-lending/15 text-lending border border-b-0 border-lending/30 -mb-px',
    drop: 'border-lending bg-lending/10',
    dropIcon: 'text-lending',
    file: 'text-lending',
    chip: 'bg-lending/20 text-lending ring-1 ring-lending/30',
    boxIcon: 'bg-lending/15',
    badge: 'text-lending/80',
    hover: 'hover:border-lending/35 hover:bg-lending/5',
    action: 'text-lending',
    spinner: 'text-lending',
  },
};

function formatBytes(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export default function PackageSourceHub({
  vertical = 'mortgage',
  samples = [],
  title = 'Loan package',
  subtitle = 'Load one package, then run underwriting.',
  productField = 'product_line',
  productOptions = [],
  productDefault = '',
  includePurpose = false,
  purposeOptions = [],
  purposeDefault = '',
  quickPaths = [],
  perBorrower = false,
  dropHint = 'Drop borrower package…',
  onSubmit,
  onRunDemo,
  onRunConnect,
  onRunResult,
  loading,
}) {
  const accent = ACCENTS[vertical] || ACCENTS.mortgage;
  const [sourceId, setSourceId] = useState('upload');
  const [fileList, setFileList] = useState([]);
  const [directory, setDirectory] = useState(quickPaths[0]?.path || '');
  const [product, setProduct] = useState(productDefault);
  const [purpose, setPurpose] = useState(purposeDefault);
  const [useLlm, setUseLlm] = useState(true);
  const [splitFolders, setSplitFolders] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const running = loading || busy;

  const addFiles = (incoming) => {
    const next = Array.from(incoming || []);
    if (!next.length) return;
    setFileList((prev) => {
      const names = new Set(prev.map((f) => `${f.name}:${f.size}`));
      const merged = [...prev];
      for (const f of next) {
        const key = `${f.name}:${f.size}`;
        if (!names.has(key)) {
          names.add(key);
          merged.push(f);
        }
      }
      return merged;
    });
    setError('');
  };

  const removeFile = (idx) => setFileList((prev) => prev.filter((_, i) => i !== idx));

  const runCustom = async () => {
    setError('');
    setBusy(true);
    try {
      const body = { [productField]: product };
      if (includePurpose) body.purpose = purpose;
      body.require_documents = true;
      if (productField === 'product_line') body.use_llm = useLlm;
      if (sourceId === 'directory') {
        const path = directory.trim();
        if (!path) throw new Error('Enter a server document directory');
        body.directory = path;
        if (perBorrower) body.per_borrower = splitFolders;
      } else if (sourceId === 'upload') {
        if (!fileList.length) throw new Error('Add at least one package file');
        body.documents = await Promise.all(fileList.map(readFileForUpload));
      } else {
        return;
      }
      await onSubmit(body);
      setFileList([]);
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="glass-card overflow-hidden">
      <div className="border-b border-white/[0.06] px-5 py-4">
        <h2 className="text-sm font-semibold text-slate-100">{title}</h2>
        <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>
      </div>

      {/* Source tabs — pick once, no title echo */}
      <div className="flex gap-1 border-b border-white/[0.06] px-3 pt-3">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const sel = sourceId === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => { setSourceId(tab.id); setError(''); }}
              className={`inline-flex items-center gap-1.5 rounded-t-lg px-3.5 py-2 text-xs font-semibold transition ${
                sel ? accent.tab : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      <div className="p-5 space-y-4">
        {error && (
          <div className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-300">{error}</div>
        )}

        {sourceId === 'upload' && (
          <div className="space-y-3">
            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                addFiles(e.dataTransfer.files);
              }}
              className={`rounded-xl border-2 border-dashed px-6 py-10 text-center transition ${
                dragOver ? accent.drop : 'border-white/10 bg-black/20 hover:border-white/20'
              }`}
            >
              <Upload className={`mx-auto h-8 w-8 ${dragOver ? accent.dropIcon : 'text-slate-500'}`} />
              <p className="mt-3 text-sm font-medium text-slate-200">{dropHint}</p>
              <p className="mt-1 text-xs text-slate-500">PDF, images, or text — full package</p>
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="btn-secondary btn-sm mt-4 text-xs"
              >
                Browse files
              </button>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.txt,.md,.xml,.json,.csv,.png,.jpg,.jpeg,.tiff,.tif,.bmp"
                className="hidden"
                onChange={(e) => {
                  addFiles(e.target.files);
                  e.target.value = '';
                }}
              />
            </div>

            {fileList.length > 0 && (
              <ul className="space-y-1.5">
                {fileList.map((f, i) => (
                  <li
                    key={`${f.name}-${f.size}-${i}`}
                    className="flex items-center gap-2 rounded-lg bg-white/[0.03] px-3 py-2 text-xs"
                  >
                    <FileText className={`h-3.5 w-3.5 shrink-0 ${accent.file}`} />
                    <span className="min-w-0 flex-1 truncate text-slate-200">{f.name}</span>
                    <span className="shrink-0 text-slate-500">{formatBytes(f.size)}</span>
                    <button
                      type="button"
                      onClick={() => removeFile(i)}
                      className="shrink-0 rounded p-0.5 text-slate-500 hover:bg-white/10 hover:text-slate-200"
                      aria-label={`Remove ${f.name}`}
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {sourceId === 'directory' && (
          <div className="space-y-3">
            <label className="block">
              <span className="mb-1.5 block text-xs font-medium text-slate-400">
                Path on the API host
              </span>
              <input
                className="input-field w-full font-mono text-xs"
                value={directory}
                onChange={(e) => setDirectory(e.target.value)}
                placeholder="simulated_documents/…"
              />
            </label>
            {quickPaths.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {quickPaths.map((q) => (
                  <button
                    key={q.path}
                    type="button"
                    onClick={() => setDirectory(q.path)}
                    className={`rounded-md px-2 py-1 text-[10px] transition ${
                      directory === q.path
                        ? accent.chip
                        : 'bg-white/[0.04] text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {q.label}
                  </button>
                ))}
              </div>
            )}
            {perBorrower && (
              <HintCheckbox
                hint={UI_HINTS.splitFolders}
                label="Split multi-borrower folders"
                labelClassName="flex items-center gap-2 text-xs text-slate-400"
                checked={splitFolders}
                onChange={(e) => setSplitFolders(e.target.checked)}
              />
            )}
          </div>
        )}

        {sourceId === 'connect' && (
          onRunConnect
            ? <ConnectAndPull vertical={vertical} onRunJob={onRunConnect} />
            : <ConnectAndPull vertical={vertical} onRunResult={onRunResult} />
        )}

        {sourceId === 'samples' && (
          <div className="space-y-2">
            {samples.length === 0 ? (
              <p className="py-6 text-center text-xs text-slate-500">No sample packages available.</p>
            ) : (
              samples.map((d) => {
                const isCommercial = String(d[productField] || '').includes('commercial');
                return (
                  <button
                    key={d.id}
                    type="button"
                    disabled={running}
                    onClick={() => onRunDemo?.(vertical, d.id)}
                    className={`flex w-full items-center gap-3 rounded-xl border border-white/[0.06] bg-black/20 px-3.5 py-3 text-left transition ${accent.hover} disabled:opacity-50`}
                  >
                    <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${accent.boxIcon}`}>
                      {vertical === 'lending'
                        ? <Wallet className={`h-4 w-4 ${accent.action}`} />
                        : isCommercial
                          ? <Building2 className={`h-4 w-4 ${accent.action}`} />
                          : <Home className={`h-4 w-4 ${accent.action}`} />}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-slate-200">{d.name}</p>
                      <p className="truncate text-xs text-slate-500">{d.description}</p>
                    </div>
                    <span className={`shrink-0 rounded-md bg-white/[0.04] px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${accent.badge}`}>
                      {vertical === 'lending'
                        ? String(d.product_type || 'business').replace(/_/g, ' ')
                        : isCommercial ? 'Commercial' : 'Residential'}
                    </span>
                    {running ? (
                      <Loader2 className={`h-4 w-4 shrink-0 animate-spin ${accent.action}`} />
                    ) : (
                      <span className={`shrink-0 text-[10px] font-semibold uppercase tracking-wide ${accent.action}`}>
                        Run
                      </span>
                    )}
                  </button>
                );
              })
            )}
          </div>
        )}

        {sourceId !== 'samples' && sourceId !== 'connect' && (
          <div className="flex flex-wrap items-center gap-3 border-t border-white/[0.06] pt-4">
            {productOptions.length > 0 && (
              <div className="inline-flex flex-wrap rounded-lg border border-white/[0.08] p-0.5">
                {productOptions.map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => setProduct(opt.id)}
                    className={`rounded-md px-2.5 py-1 text-[11px] font-medium transition ${
                      product === opt.id
                        ? 'bg-white/10 text-slate-100'
                        : 'text-slate-500 hover:text-slate-300'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            )}
            {includePurpose && purposeOptions.length > 0 && (
              <select
                value={purpose}
                onChange={(e) => setPurpose(e.target.value)}
                className="input-field w-auto text-xs"
                aria-label="Loan purpose"
              >
                {purposeOptions.map((opt) => (
                  <option key={opt.id} value={opt.id}>{opt.label}</option>
                ))}
              </select>
            )}
            <HintCheckbox
              hint={UI_HINTS.llmExtraction}
              label="LLM assist"
              labelClassName="flex items-center gap-1.5 text-[11px] text-slate-500"
              checked={useLlm}
              onChange={(e) => setUseLlm(e.target.checked)}
            />
            <button
              type="button"
              disabled={running || (sourceId === 'upload' && !fileList.length)}
              onClick={runCustom}
              className="btn-primary btn-sm ml-auto text-xs inline-flex items-center gap-1.5"
            >
              {running ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
              {running ? 'Running…' : 'Underwrite'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
