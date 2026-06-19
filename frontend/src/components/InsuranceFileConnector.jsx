import { useCallback, useState } from 'react';
import { Upload, FileText, X, HelpCircle, FolderOpen } from 'lucide-react';
import {
  DOC_SLOTS,
  detectDocType,
  readFileForUpload,
  buildSubmissionPayload,
  validatePackage,
} from '../lib/insuranceDocs';

export default function InsuranceFileConnector({ onSubmit, loading }) {
  const [files, setFiles] = useState([]);
  const [dragOver, setDragOver] = useState(false);
  const [useLlm, setUseLlm] = useState(true);
  const [error, setError] = useState('');

  const ingestFiles = useCallback(async (fileList) => {
    setError('');
    const incoming = Array.from(fileList || []);
    if (!incoming.length) return;

    const parsed = await Promise.all(
      incoming.map(async (file) => {
        const doc = await readFileForUpload(file);
        const preview = doc.encoding === 'utf-8' ? doc.content.slice(0, 8000) : '';
        const slot = detectDocType(file.name, preview);
        return { ...doc, slot, size: file.size, id: `${file.name}-${file.size}-${Date.now()}` };
      }),
    );
    setFiles((prev) => {
      const merged = [...prev];
      for (const f of parsed) {
        if (f.slot === 'acord_xml') {
          const idx = merged.findIndex((x) => x.slot === 'acord_xml');
          if (idx >= 0) merged[idx] = f;
          else merged.unshift(f);
        } else {
          merged.push(f);
        }
      }
      return merged;
    });
  }, []);

  const removeFile = (id) => setFiles((prev) => prev.filter((f) => f.id !== id));

  const setSlot = (id, slot) => {
    setFiles((prev) => prev.map((f) => (f.id === id ? { ...f, slot } : f)));
  };

  const handleSubmit = async () => {
    const validation = validatePackage(files);
    if (validation) {
      setError(validation);
      return;
    }
    setError('');
    await onSubmit(buildSubmissionPayload(files, useLlm));
    setFiles([]);
  };

  const slotted = Object.keys(DOC_SLOTS).map((slotId) => ({
    ...DOC_SLOTS[slotId],
    file: files.find((f) => f.slot === slotId),
  }));

  return (
    <div className="glass-card overflow-hidden">
      <div className="border-b border-white/[0.06] px-6 py-4">
        <div className="flex items-center gap-2">
          <FolderOpen className="h-5 w-5 text-insurance" />
          <div>
            <h3 className="font-semibold">Submission Input Source</h3>
            <p className="text-xs text-slate-500">Upload the broker package — files are classified and sent to the pipeline</p>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* Drop zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => { e.preventDefault(); setDragOver(false); ingestFiles(e.dataTransfer.files); }}
          className={`relative rounded-2xl border-2 border-dashed p-10 text-center transition ${dragOver ? 'border-insurance bg-insurance/5' : 'border-white/10 bg-surface/50 hover:border-white/20'}`}
        >
          <Upload className="mx-auto h-10 w-10 text-slate-500" />
          <p className="mt-3 font-medium text-slate-200">Drop broker documents here</p>
          <p className="mt-1 text-sm text-slate-500">ACORD XML, loss runs, SOV, inspections, broker JSON, PDFs</p>
          <label className="btn-primary mt-5 cursor-pointer inline-flex">
            Browse files
            <input
              type="file"
              multiple
              accept=".xml,.json,.pdf,.txt,.md,.png,.jpg,.jpeg"
              className="hidden"
              onChange={(e) => ingestFiles(e.target.files)}
            />
          </label>
        </div>

        {/* Document slots */}
        <div className="grid gap-3 sm:grid-cols-2">
          {slotted.map((slot) => (
            <div
              key={slot.id}
              className={`rounded-xl border p-4 transition ${slot.file ? 'border-insurance/30 bg-insurance/5' : 'border-white/[0.06] bg-surface-overlay/50'}`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm font-semibold text-slate-200">
                      {slot.label}
                      {slot.required && <span className="text-red-400"> *</span>}
                    </span>
                    <span className="group relative">
                      <HelpCircle className="h-3.5 w-3.5 text-slate-600 cursor-help" />
                      <span className="pointer-events-none absolute bottom-full left-0 z-10 mb-2 hidden w-56 rounded-lg bg-surface-raised p-2 text-xs text-slate-400 shadow-lg ring-1 ring-white/10 group-hover:block">
                        {slot.hint}
                      </span>
                    </span>
                  </div>
                  {slot.file ? (
                    <div className="mt-2 flex items-center gap-2">
                      <FileText className="h-4 w-4 shrink-0 text-insurance" />
                      <span className="truncate text-xs text-slate-300">{slot.file.filename}</span>
                      <button type="button" onClick={() => removeFile(slot.file.id)} className="ml-auto text-slate-500 hover:text-red-400">
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ) : (
                    <p className="mt-1 text-xs text-slate-600">Not uploaded</p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* All files list with re-tag */}
        {files.length > 0 && (
          <div className="rounded-xl border border-white/[0.06] bg-surface/40">
            <div className="border-b border-white/[0.06] px-4 py-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Connected files ({files.length})
            </div>
            <ul className="divide-y divide-white/[0.04]">
              {files.map((f) => (
                <li key={f.id} className="flex flex-wrap items-center gap-3 px-4 py-2.5">
                  <FileText className="h-4 w-4 text-slate-500" />
                  <span className="min-w-0 flex-1 truncate text-sm text-slate-300">{f.filename}</span>
                  <select
                    value={f.slot}
                    onChange={(e) => setSlot(f.id, e.target.value)}
                    className="rounded-lg border border-white/10 bg-surface px-2 py-1 text-xs text-slate-300"
                  >
                    {Object.values(DOC_SLOTS).map((s) => (
                      <option key={s.id} value={s.id}>{s.label}</option>
                    ))}
                  </select>
                  <button type="button" onClick={() => removeFile(f.id)} className="text-slate-500 hover:text-red-400">
                    <X className="h-4 w-4" />
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {error && (
          <p className="rounded-xl bg-amber-500/10 px-4 py-2 text-sm text-amber-300">{error}</p>
        )}

        <div className="flex flex-wrap items-center justify-between gap-4 border-t border-white/[0.06] pt-4">
          <label className="flex items-center gap-2 text-sm text-slate-400">
            <input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} className="rounded" />
            Use LLM enhancement
          </label>
          <button type="button" onClick={handleSubmit} disabled={loading || !files.length} className="btn-primary">
            {loading ? 'Running pipeline…' : 'Submit package to underwriting'}
          </button>
        </div>
      </div>
    </div>
  );
}
