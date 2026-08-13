import { useEffect, useMemo, useState } from 'react';
import { Loader2, Upload, FileText, X, Play, Database, Cable, AlertTriangle } from 'lucide-react';
import { readFileForUpload, buildSubmissionPayload, scoreFileRelevance, validatePackageRelevance } from '../lib/insuranceDocs';
import { insuranceLineLabel } from '../lib/insuranceLines';
import { UI_HINTS } from '../lib/uiHints';
import { endpoints } from '../lib/api';
import ConnectAndPull from './ConnectAndPull';
import CommercialLinePicker from './CommercialLinePicker';
import { Hint, HintCheckbox } from './ui';
import { isCommercialSelectionComplete } from '../lib/commercialTaxonomy';

const TABS = [
  { id: 'files', label: 'Files', icon: Upload, hint: UI_HINTS.tabFiles },
  { id: 'connect', label: 'Connect & pull', icon: Cable, hint: UI_HINTS.tabConnect },
  { id: 'sample', label: 'Sample data', icon: Database, hint: UI_HINTS.tabSample },
];

const fmtSize = (bytes) => {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export default function RunSelector({
  presets,
  vertical = 'insurance',
  samples,
  onRunDemo,
  onSubmit,
  onRunJob,
  onRunResult,
  productField = 'product_line',
  productOptions = [],
  productDefault = '',
  productValue,
  onProductChange,
  commercialTaxonomy = null,
  commercialSelection,
  onCommercialSelectionChange,
  isLifeProductPicker = false,
  includePurpose = false,
  purposeOptions = [],
  purposeDefault = '',
}) {
  const [tab, setTab] = useState('files');
  const [files, setFiles] = useState([]);
  const [dataId, setDataId] = useState('');
  const [useLlm, setUseLlm] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState('');
  const [warning, setWarning] = useState('');
  const [product, setProduct] = useState(productDefault);
  const [purpose, setPurpose] = useState(purposeDefault);
  const [strictRelevance, setStrictRelevance] = useState(true);

  const useCommercialPicker = Array.isArray(commercialTaxonomy) && commercialTaxonomy.length > 0;

  const normalizedOptions = useMemo(
    () => (productOptions || []).map((opt) => ({
      id: opt.id || opt.value,
      label: opt.label || opt.id || opt.value,
    })).filter((opt) => opt.id),
    [productOptions],
  );

  const activeProduct = useCommercialPicker
    ? (commercialSelection?.insurance_line || '')
    : (productValue !== undefined ? productValue : product);

  const applyLineFields = (body) => {
    if (useCommercialPicker && commercialSelection) {
      if (!isCommercialSelectionComplete(commercialSelection)) {
        throw new Error('Select category, product, and coverage before running');
      }
      body[productField] = commercialSelection.insurance_line;
      body.commercial_product_name = commercialSelection.productName;
      body.commercial_coverage_name = commercialSelection.coverageName;
      body.commercial_coverage_id = commercialSelection.coverageId || undefined;
      body.commercial_category_id = commercialSelection.categoryId;
      if (isLifeProductPicker) {
        body.life_product_id = commercialSelection.checklist_lob || commercialSelection.productId;
        body.life_coverage_id = commercialSelection.coverageId || undefined;
      } else {
        body.commercial_product_id = commercialSelection.productId;
      }
      return body;
    }
    if (normalizedOptions.length > 0) body[productField] = activeProduct;
    return body;
  };

  useEffect(() => {
    if (productValue !== undefined) return;
    if (productDefault) setProduct(productDefault);
  }, [productDefault, productValue]);

  const allSamples = samples || presets?.insurance || [];
  const sampleList = normalizedOptions.length > 0 && vertical === 'insurance'
    ? allSamples.filter((s) => (s.insurance_line || s.product_line || s.product_type) === activeProduct)
    : allSamples;

  const setActiveProduct = (id) => {
    if (onProductChange) onProductChange(id);
    else setProduct(id);
  };

  const fileScores = useMemo(
    () => files.map((f) => ({ ...scoreFileRelevance(f), filename: f.filename })),
    [files],
  );

  const pickProduct = (id) => {
    setActiveProduct(id);
    if (vertical === 'insurance' && normalizedOptions.length > 0) {
      setDataId((prev) => {
        const match = allSamples.find((s) => s.id === prev && (s.insurance_line || s.product_line || s.product_type) === id);
        return match ? prev : '';
      });
    }
  };

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
    setError('');
    setWarning('');
  };

  const handleDrop = (e) => {
    e.preventDefault();
    addFiles(e.dataTransfer.files);
  };

  const removeFile = (index) => setFiles((prev) => prev.filter((_, i) => i !== index));

  const removeIrrelevantFiles = () => {
    setFiles((prev) => prev.filter((f) => scoreFileRelevance(f).relevant));
    setWarning('');
  };

  const runFiles = async () => {
    setError('');
    setWarning('');
    if (!files.length) {
      setError('Add at least one file to run');
      return;
    }

    const local = validatePackageRelevance(files);
    let gate = local;
    try {
      const docs = files.map((f) => ({ filename: f.filename, content: f.content, encoding: f.encoding }));
      const server = await endpoints.validateDocuments(docs, vertical, strictRelevance);
      gate = {
        can_run: server.can_run,
        irrelevant: server.irrelevant || [],
        warnings: server.warnings || [],
        message: server.message,
      };
    } catch {
      // Fall back to client heuristics if API unavailable
    }

    if (!gate.can_run) {
      setError(gate.message || 'No relevant documents to run');
      return;
    }
    if (gate.irrelevant?.length) {
      setWarning(gate.warnings?.[0] || gate.message || `${gate.irrelevant.length} file(s) look irrelevant`);
      if (strictRelevance) {
        // Keep only relevant files for the run
        const bad = new Set((gate.irrelevant || []).map((r) => r.filename));
        const kept = files.filter((f) => !bad.has(f.filename));
        if (!kept.length) {
          setError('All files look irrelevant — add underwriting documents');
          return;
        }
        setFiles(kept);
        // continue with kept
        setRunning(true);
        try {
          const body = applyLineFields(buildSubmissionPayload(kept, useLlm));
          if (includePurpose) body.purpose = purpose;
          body.require_documents = true;
          await onSubmit?.(body);
        } catch (e) {
          setError(e.message);
        } finally {
          setRunning(false);
        }
        return;
      }
    }

    setRunning(true);
    try {
      const body = applyLineFields(buildSubmissionPayload(files, useLlm));
      if (includePurpose) body.purpose = purpose;
      body.require_documents = true;
      await onSubmit?.(body);
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
    await onRunDemo?.(vertical, dataId);
  };

  return (
    <div className="glass-card p-5">
      <div className="mb-3 flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Select files or data to run</p>
        <div className="flex rounded-lg bg-surface/60 p-0.5">
          {TABS.map((t) => (
            <Hint key={t.id} text={t.hint}>
              <button type="button" onClick={() => { setTab(t.id); setError(''); setWarning(''); }}
                className={`rounded-md px-3 py-1 text-[11px] font-medium transition ${
                  tab === t.id ? 'bg-brand/15 text-brand ring-1 ring-brand/25' : 'text-slate-500 hover:text-slate-300'
                }`}>
                <span className="inline-flex items-center gap-1"><t.icon className="h-3 w-3" /> {t.label}</span>
              </button>
            </Hint>
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
            <span className="text-xs font-medium text-slate-300">Drop multiple files here or click to browse</span>
            <span className="text-[10px] text-slate-600">.pdf .xml .json .txt .md — multi-select supported</span>
            <input type="file" multiple className="hidden" accept=".xml,.json,.pdf,.txt,.md,.png,.jpg,.jpeg"
              onChange={(e) => { addFiles(e.target.files); e.target.value = ''; }} />
          </label>

          {files.length > 0 && (
            <div className="max-h-44 space-y-1 overflow-y-auto rounded-lg border border-white/[0.06] bg-surface/40 p-2">
              {files.map((f, i) => {
                const score = fileScores[i];
                const bad = score && !score.relevant;
                return (
                  <div key={`${f.filename}-${i}`} className={`group flex items-center gap-2 rounded-md px-2 py-1.5 transition hover:bg-white/[0.03] ${bad ? 'bg-amber-500/10' : ''}`}>
                    {bad ? <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-amber-400" /> : <FileText className="h-3.5 w-3.5 shrink-0 text-insurance" />}
                    <span className="min-w-0 flex-1 truncate text-[11px] text-slate-300" title={score?.reason || ''}>{f.filename}</span>
                    <span className={`shrink-0 text-[9px] ${bad ? 'text-amber-400' : 'text-slate-600'}`}>
                      {bad ? 'irrelevant' : (score?.doc_type || f.kind)}
                      {f.size ? ` · ${fmtSize(f.size)}` : ''}
                    </span>
                    <button type="button" onClick={() => removeFile(i)} className="shrink-0 text-slate-600 transition hover:text-red-400">
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                );
              })}
            </div>
          )}

          {useCommercialPicker ? (
            <CommercialLinePicker
              taxonomy={commercialTaxonomy}
              value={commercialSelection}
              onChange={onCommercialSelectionChange}
              disabled={running}
            />
          ) : normalizedOptions.length > 0 && (
            <div className="flex flex-wrap items-center gap-3">
              <label className="flex min-w-[240px] flex-1 items-center gap-2">
                <Hint text={UI_HINTS.lineOfBusiness}>
                  <span className="hint-label cursor-help text-[11px] font-semibold uppercase tracking-wider text-slate-500">Line of business</span>
                </Hint>
                <select
                  value={activeProduct}
                  onChange={(e) => pickProduct(e.target.value)}
                  className="input-field flex-1 text-xs"
                  aria-label="Line of business"
                >
                  {normalizedOptions.map((opt) => (
                    <option key={opt.id} value={opt.id}>{opt.label}</option>
                  ))}
                </select>
              </label>
              {includePurpose && purposeOptions.length > 0 && (
                <select value={purpose} onChange={(e) => setPurpose(e.target.value)} className="input-field w-auto text-xs" aria-label="Loan purpose">
                  {purposeOptions.map((opt) => <option key={opt.id || opt.value} value={opt.id || opt.value}>{opt.label}</option>)}
                </select>
              )}
            </div>
          )}

          <div className="flex flex-wrap items-center gap-3">
            <HintCheckbox
              hint={UI_HINTS.llmExtraction}
              label="LLM extraction"
              checked={useLlm}
              onChange={(e) => setUseLlm(e.target.checked)}
            />
            <HintCheckbox
              hint={UI_HINTS.blockIrrelevant}
              label="Block irrelevant files"
              checked={strictRelevance}
              onChange={(e) => setStrictRelevance(e.target.checked)}
            />
            <div className="ml-auto flex items-center gap-2">
              {fileScores.some((s) => !s.relevant) && (
                <Hint text={UI_HINTS.removeIrrelevant}>
                  <button type="button" onClick={removeIrrelevantFiles} className="hint-label cursor-help text-[10px] text-amber-400/90 transition hover:text-amber-300">
                    Remove irrelevant
                  </button>
                </Hint>
              )}
              {files.length > 0 && (
                <Hint text={UI_HINTS.clearFiles}>
                  <button type="button" onClick={() => { setFiles([]); setWarning(''); }} className="hint-label cursor-help text-[10px] text-red-400/70 transition hover:text-red-400">Clear</button>
                </Hint>
              )}
              <Hint text={UI_HINTS.runPipeline}>
                <button type="button" onClick={runFiles} disabled={running}
                  className="btn-primary btn-sm text-xs disabled:opacity-40">
                  {running ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3 w-3" />}
                  Run pipeline{files.length ? ` (${files.length})` : ''}
                </button>
              </Hint>
            </div>
          </div>
        </div>
      )}

      {tab === 'connect' && (
        <ConnectAndPull
          vertical={vertical}
          insuranceLine={activeProduct || ''}
          lifeProductId={isLifeProductPicker ? (commercialSelection?.checklist_lob || commercialSelection?.productId || '') : ''}
          lifeCoverageId={isLifeProductPicker ? (commercialSelection?.coverageId || '') : ''}
          commercialProductId={!isLifeProductPicker ? (commercialSelection?.productId || '') : ''}
          coverageId={commercialSelection?.coverageId || ''}
          productName={commercialSelection?.productName || ''}
          coverageName={commercialSelection?.coverageName || ''}
          commercialCategoryId={commercialSelection?.categoryId || ''}
          strictRelevance={strictRelevance}
          onRunJob={onRunJob || (onSubmit ? (jobId) => onSubmit?.({ _jobId: jobId }) : undefined)}
          onRunResult={onRunResult}
        />
      )}

      {tab === 'sample' && (
        <div className="space-y-3">
          {sampleList.length === 0 ? (
            <div className="rounded-xl border border-dashed border-white/[0.12] bg-surface/30 px-4 py-5 text-center">
              <p className="text-xs font-medium text-slate-400">
                {vertical === 'insurance' ? `No demo case for ${insuranceLineLabel(activeProduct)} yet — coming soon.` : 'No sample data sets available.'}
              </p>
              <p className="mt-1 text-[10px] text-slate-600">Upload files in the Files tab or connect a source above.</p>
            </div>
          ) : (
            <>
              <select value={dataId} onChange={(e) => setDataId(e.target.value)} className="input-field w-full text-xs">
                <option value="">Choose a sample data set…</option>
                {sampleList.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} — {insuranceLineLabel(s.insurance_line || s.product_line || s.product_type || 'commercial')}
                  </option>
                ))}
              </select>
              {dataId && <p className="text-[11px] text-slate-500">{sampleList.find((s) => s.id === dataId)?.description}</p>}
              <div className="flex justify-end">
                <Hint text={UI_HINTS.runSample}>
                  <button type="button" onClick={runSample} disabled={running || !dataId}
                    className="btn-primary btn-sm text-xs disabled:opacity-40">
                    {running ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3 w-3" />}
                    Run sample
                  </button>
                </Hint>
              </div>
            </>
          )}
        </div>
      )}

      {warning && <p className="mt-3 rounded-lg bg-amber-500/10 px-3 py-1.5 text-xs text-amber-200">{warning}</p>}
      {error && <p className="mt-3 rounded-lg bg-red-500/10 px-3 py-1.5 text-xs text-red-300">{error}</p>}
    </div>
  );
}
