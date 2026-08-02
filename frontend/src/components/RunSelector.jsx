import { useState } from 'react';
import { Loader2, Upload, FileText, X, Play, Database, Cable } from 'lucide-react';
import { readFileForUpload, buildSubmissionPayload } from '../lib/insuranceDocs';
import ConnectAndPull from './ConnectAndPull';

const TABS = [
  { id: 'files', label: 'Files', icon: Upload },
  { id: 'connect', label: 'Connect & pull', icon: Cable },
  { id: 'sample', label: 'Sample data', icon: Database },
];

const fmtSize = (bytes) => {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export default function RunSelector({ presets, onRunDemo, onSubmit }) {
  const [tab, setTab] = useState('files');
  const [files, setFiles] = useState([]);
  const [dataId, setDataId] = useState('');
  const [useLlm, setUseLlm] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState('');

  const samples = presets?.insurance || [];

  const addFiles = async (list) => {
    const arr = Array.from(list || []);
    if (!arr.length) return;
    const incoming = await Promise.all(
      arr.map(async (file) => {
        const doc = await readFileForUpload(file);
        return { ...doc, size: file.size, kind: (file.name.split('.').pop() || '').toUpperCase() };
      }),
    );
    setFiles((prev) => [...prev, ...incoming]);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    addFiles(e.dataTransfer.files);
  };

  const removeFile = (index) => setFiles((prev) => prev.filter((_, i) => i !== index));

  const runFiles = async () => {
    setError('');
    if (!files.length) {
      setError('Add at least one file to run');
      return;
    }
    setRunning(true);
    try {
      await onSubmit?.(buildSubmissionPayload(files, useLlm));
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  };

  const runSample = async () => {
    setError('');
    if (!dataId) {
      setError('Pick a sample data set first');
      return;
    }
    await onRunDemo?.('insurance', dataId);
  };

  return (
    <div className="glass-card p-5">
      <div className="mb-3 flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Select files or data to run</p>
        <div className="flex rounded-lg bg-surface/60 p-0.5">
          {TABS.map((t) => (
            <button key={t.id} type="button" onClick={() => { setTab(t.id); setError(''); }}
              className={`rounded-md px-3 py-1 text-[11px] font-medium transition ${
                tab === t.id ? 'bg-brand/15 text-brand ring-1 ring-brand/25' : 'text-slate-500 hover:text-slate-300'
              }`}>
              <span className="inline-flex items-center gap-1"><t.icon className="h-3 w-3" /> {t.label}</span>
            </button>
          ))}
        </div>
      </div>

      {tab === 'files' && (
        <div className="space-y-3">
          <label
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            className="flex w-full cursor-pointer flex-col items-center justify-center gap-1 rounded-xl border border-dashed border-white/[0.12] bg-surface/30 px-4 py-6 text-center transition hover:border-brand/40 hover:bg-brand/5">
            <Upload className="h-5 w-5 text-slate-500" />
            <span className="text-xs font-medium text-slate-300">Drop files here or click to browse</span>
            <span className="text-[10px] text-slate-600">.pdf .xml .json .txt .md</span>
            <input type="file" multiple className="hidden" accept=".xml,.json,.pdf,.txt,.md"
              onChange={(e) => { addFiles(e.target.files); e.target.value = ''; }} />
          </label>

          {files.length > 0 && (
            <div className="max-h-40 space-y-1 overflow-y-auto rounded-lg border border-white/[0.06] bg-surface/40 p-2">
              {files.map((f, i) => (
                <div key={`${f.filename}-${i}`} className="group flex items-center gap-2 rounded-md px-2 py-1.5 transition hover:bg-white/[0.03]">
                  <FileText className="h-3.5 w-3.5 shrink-0 text-insurance" />
                  <span className="min-w-0 flex-1 truncate text-[11px] text-slate-300">{f.filename}</span>
                  <span className="shrink-0 text-[9px] text-slate-600">{f.kind}{f.size ? ` · ${fmtSize(f.size)}` : ''}</span>
                  <button type="button" onClick={() => removeFile(i)} className="shrink-0 text-slate-600 transition hover:text-red-400">
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="flex flex-wrap items-center gap-2">
            <label className="flex items-center gap-1.5 text-[10px] text-slate-500">
              <input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} className="rounded" />
              LLM extraction
            </label>
            <div className="ml-auto flex items-center gap-2">
              {files.length > 0 && (
                <button type="button" onClick={() => setFiles([])} className="text-[10px] text-red-400/70 transition hover:text-red-400">Clear</button>
              )}
              <button type="button" onClick={runFiles} disabled={running}
                className="btn-primary btn-sm text-xs disabled:opacity-40">
                {running ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3 w-3" />}
                Run pipeline{files.length ? ` (${files.length})` : ''}
              </button>
            </div>
          </div>
        </div>
      )}

      {tab === 'connect' && (
        <ConnectAndPull vertical="insurance" onRunJob={(jobId) => onSubmit?.({ _jobId: jobId })} />
      )}

      {tab === 'sample' && (
        <div className="space-y-3">
          <select value={dataId} onChange={(e) => setDataId(e.target.value)} className="input-field w-full text-xs">
            <option value="">Choose a sample data set…</option>
            {samples.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} — {(s.insurance_line || 'commercial').replace(/_/g, ' ')}
              </option>
            ))}
          </select>
          {dataId && <p className="text-[11px] text-slate-500">{samples.find((s) => s.id === dataId)?.description}</p>}
          <div className="flex justify-end">
            <button type="button" onClick={runSample} disabled={running || !dataId}
              className="btn-primary btn-sm text-xs disabled:opacity-40">
              {running ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3 w-3" />}
              Run sample
            </button>
          </div>
        </div>
      )}

      {error && <p className="mt-3 rounded-lg bg-red-500/10 px-3 py-1.5 text-xs text-red-300">{error}</p>}
    </div>
  );
}
