import { useState } from 'react';
import {
  FileUp, FolderOpen, FlaskConical, Link2, Loader2, CheckCircle2, Home, Building2,
} from 'lucide-react';
import { readFileForUpload } from '../lib/insuranceDocs';

const SOURCES = [
  {
    id: 'upload',
    name: 'Upload files',
    desc: 'Browser drop — W-2, 1003, credit, appraisal…',
    icon: FileUp,
  },
  {
    id: 'directory',
    name: 'Server directory',
    desc: 'Ops / sandbox path on the API host',
    icon: FolderOpen,
  },
  {
    id: 'samples',
    name: 'Sample packages',
    desc: 'Built-in demos for walkthroughs',
    icon: FlaskConical,
  },
];

export default function MortgageSourceHub({ presets, onSubmit, onRunDemo, loading }) {
  const [sourceId, setSourceId] = useState('upload');
  const [files, setFiles] = useState([]);
  const [directory, setDirectory] = useState('simulated_documents/home_mortgage/johnson_marcus_imani');
  const [productLine, setProductLine] = useState('residential_mortgage');
  const [useLlm, setUseLlm] = useState(true);
  const [perBorrower, setPerBorrower] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const active = SOURCES.find((s) => s.id === sourceId) || SOURCES[0];
  const samples = presets?.mortgage || [];

  const runCustom = async () => {
    setError('');
    setBusy(true);
    try {
      const body = {
        product_line: productLine,
        use_llm: useLlm,
        per_borrower: false,
      };
      if (sourceId === 'directory') {
        const path = directory.trim();
        if (!path) throw new Error('Enter a server document directory');
        body.directory = path;
        body.per_borrower = perBorrower;
      } else if (sourceId === 'upload') {
        if (!files.length) throw new Error('Choose at least one loan package file');
        body.documents = await Promise.all([...files].map(readFileForUpload));
      } else {
        return;
      }
      await onSubmit(body);
      setFiles([]);
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setBusy(false);
    }
  };

  const running = loading || busy;

  return (
    <div className="rounded-xl border border-white/[0.06] bg-surface-overlay/40 overflow-hidden">
      <div className="flex items-center gap-2 border-b border-white/[0.06] px-4 py-2.5">
        <Link2 className="h-4 w-4 text-mortgage shrink-0" />
        <span className="text-sm font-semibold text-slate-200">Input sources</span>
        <span className="text-[10px] text-slate-500 ml-1">one package → one underwriting run</span>
      </div>

      <div className="grid lg:grid-cols-[13rem_1fr]">
        {/* Left rail */}
        <div className="border-b lg:border-b-0 lg:border-r border-white/[0.06] p-2 space-y-1 bg-black/10">
          {SOURCES.map((src) => {
            const Icon = src.icon;
            const sel = src.id === sourceId;
            return (
              <button
                key={src.id}
                type="button"
                onClick={() => { setSourceId(src.id); setError(''); }}
                className={`flex w-full items-start gap-2.5 rounded-lg px-2.5 py-2.5 text-left transition ${
                  sel
                    ? 'bg-mortgage/15 ring-1 ring-mortgage/30 text-slate-100'
                    : 'text-slate-400 hover:bg-white/[0.03] hover:text-slate-200'
                }`}
              >
                <Icon className={`h-4 w-4 mt-0.5 shrink-0 ${sel ? 'text-mortgage' : ''}`} />
                <span>
                  <span className="block text-xs font-semibold">{src.name}</span>
                  <span className="block text-[10px] text-slate-500 leading-snug mt-0.5">{src.desc}</span>
                </span>
              </button>
            );
          })}
        </div>

        {/* Detail panel */}
        <div className="p-4 space-y-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-200">{active.name}</h3>
            <p className="mt-0.5 text-xs text-slate-500">{active.desc}</p>
          </div>

          {error && (
            <div className="rounded-lg bg-red-500/10 px-3 py-2 text-xs text-red-300">{error}</div>
          )}

          {sourceId === 'upload' && (
            <div className="space-y-3">
              <label className="block">
                <span className="mb-1.5 flex items-center gap-2 text-xs font-medium text-slate-400">
                  <FileUp className="h-3.5 w-3.5" /> Loan package files
                </span>
                <input
                  type="file"
                  multiple
                  accept=".pdf,.txt,.md,.xml,.json,.csv,.png,.jpg,.jpeg,.tiff,.tif,.bmp"
                  className="input-field w-full text-sm"
                  onChange={(e) => setFiles(e.target.files || [])}
                />
              </label>
              <p className="text-xs text-slate-500">
                {files.length
                  ? `${files.length} file(s) ready`
                  : 'Select the full package (income, credit, property, UW docs).'}
              </p>
            </div>
          )}

          {sourceId === 'directory' && (
            <div className="space-y-3">
              <label className="block">
                <span className="mb-1.5 flex items-center gap-2 text-xs font-medium text-slate-400">
                  <FolderOpen className="h-3.5 w-3.5" /> Path on API host
                </span>
                <input
                  className="input-field w-full font-mono text-xs"
                  value={directory}
                  onChange={(e) => setDirectory(e.target.value)}
                  placeholder="simulated_documents/home_mortgage/johnson_marcus_imani"
                />
              </label>
              <label className="flex items-center gap-2 text-xs text-slate-400">
                <input type="checkbox" checked={perBorrower} onChange={(e) => setPerBorrower(e.target.checked)} className="rounded" />
                Per borrower (split folder packages)
              </label>
            </div>
          )}

          {sourceId === 'samples' && (
            <div className="space-y-2">
              {samples.length === 0 ? (
                <p className="text-xs text-slate-500">No sample packages available.</p>
              ) : (
                samples.map((d) => {
                  const isCommercial = String(d.product_line || '').includes('commercial');
                  return (
                    <button
                      key={d.id}
                      type="button"
                      disabled={running}
                      onClick={() => onRunDemo('mortgage', d.id)}
                      className="flex w-full items-center gap-3 rounded-lg border border-white/[0.06] bg-surface/40 px-3 py-2.5 text-left transition hover:border-mortgage/30 hover:bg-mortgage/5"
                    >
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-mortgage/15">
                        {isCommercial ? <Building2 className="h-4 w-4 text-mortgage" /> : <Home className="h-4 w-4 text-mortgage" />}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-semibold text-slate-200 truncate">{d.name}</p>
                        <p className="text-[10px] text-slate-500 truncate">{d.description}</p>
                      </div>
                      <span className="shrink-0 rounded bg-white/[0.04] px-1.5 py-0.5 text-[10px] text-slate-400">
                        {d.product_line || 'demo'}
                      </span>
                    </button>
                  );
                })
              )}
              <p className="text-[10px] text-slate-500 pt-1">
                Samples seed a package already on the server — use Upload for real borrower files.
              </p>
            </div>
          )}

          {sourceId !== 'samples' && (
            <div className="flex flex-wrap items-end gap-3 border-t border-white/[0.06] pt-3">
              <div className="min-w-[10rem]">
                <label className="mb-1 block text-[10px] font-medium text-slate-500">Product line</label>
                <select
                  className="input-field text-xs w-full"
                  value={productLine}
                  onChange={(e) => setProductLine(e.target.value)}
                >
                  <option value="residential_mortgage">Residential Mortgage</option>
                  <option value="commercial_mortgage">Commercial Mortgage</option>
                </select>
              </div>
              <label className="flex items-center gap-2 text-xs text-slate-400 pb-2">
                <input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} className="rounded" />
                Use LLM
              </label>
              <button
                type="button"
                disabled={running}
                onClick={runCustom}
                className="btn-primary btn-sm text-xs ml-auto inline-flex items-center gap-1.5"
              >
                {running ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
                {running ? 'Running…' : 'Run pipeline'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
