import { useEffect, useMemo, useState } from 'react';
import { Loader2, Upload, FileText, Play, Database, Cable, AlertTriangle, Trash2, ChevronRight } from 'lucide-react';
import { readFileForUpload, buildSubmissionPayload, scoreFileRelevance, validatePackageRelevance } from '../lib/insuranceDocs';
import { insuranceLineLabel } from '../lib/insuranceLines';
import { UI_HINTS } from '../lib/uiHints';
import { useStateContext } from '../lib/useStateContext';
import { endpoints } from '../lib/api';
import ConnectAndPull from './ConnectAndPull';
import CommercialLinePicker from './CommercialLinePicker';
import CompanyPicker from './CompanyPicker';
import { Hint, HintCheckbox } from './ui';
import { isCommercialSelectionComplete } from '../lib/commercialTaxonomy';

const HUB_WIDE_LINES = new Set(['life', 'health', 'general']);

function insuranceSampleMatches(sample, selection) {
  if (!selection) return false;
  const productId = String(selection.productId || '').toLowerCase();
  const checklist = String(selection.checklist_lob || '').toLowerCase();
  const line = String(selection.insurance_line || '').toLowerCase();
  const sampleProduct = String(sample.product_id || '').toLowerCase();
  const sampleLine = String(sample.insurance_line || sample.product_line || sample.product_type || '').toLowerCase();
  if (sampleProduct) {
    return Boolean(productId) && (sampleProduct === productId || sampleProduct === checklist);
  }
  if (!sampleLine || HUB_WIDE_LINES.has(sampleLine)) return false;
  return sampleLine === line || sampleLine === productId || sampleLine === checklist;
}

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

function FileDropZone({ onDrop, files, fileScores, onRemove, onRemoveAll }) {
  return (
    <div className="space-y-3">
      <label
        onDrop={onDrop}
        onDragOver={(e) => e.preventDefault()}
        className="flex w-full cursor-pointer flex-col items-center justify-center gap-1 rounded-xl border border-dashed border-white/[0.12] bg-surface/30 px-4 py-6 text-center transition hover:border-brand/40 hover:bg-brand/5">
        <Upload className="h-5 w-5 text-slate-500" />
        <span className="text-sm font-medium text-slate-200">Drop multiple files here or click to browse</span>
        <span className="text-xs text-slate-400">.pdf .xml .json .txt .md .xlsx .docx .eml — multi-select supported</span>
        <input type="file" multiple className="hidden" accept=".xml,.json,.pdf,.txt,.md,.csv,.xlsx,.xls,.docx,.doc,.eml,.html,.png,.jpg,.jpeg,.tiff,.tif,.bmp"
          onChange={(e) => { onDrop({ dataTransfer: { files: e.target.files } }); e.target.value = ''; }} />
      </label>

      {files.length > 0 && (
        <div className="rounded-lg border border-white/[0.06] bg-surface/40 p-2">
          <div className="mb-1.5 flex items-center justify-between px-1">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              Files · {files.length}
            </p>
            <button
              type="button"
              onClick={onRemoveAll}
              className="inline-flex items-center gap-1 text-[11px] font-medium text-red-400 hover:text-red-300"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Delete all files
            </button>
          </div>
          <div className="max-h-44 space-y-1 overflow-y-auto">
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
                  <button
                    type="button"
                    onClick={() => onRemove(i)}
                    className="shrink-0 rounded p-1 text-red-400 hover:bg-red-500/10"
                    title={`Delete ${f.filename}`}
                    aria-label={`Delete ${f.filename}`}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

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
  isHealthProductPicker = false,
  isGeneralProductPicker = false,
  guidedFlow = false,
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
  const [companyId, setCompanyId] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [guidedStep, setGuidedStep] = useState(1);
  const { selectedState } = useStateContext();

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
      } else if (isHealthProductPicker) {
        body.health_product_id = commercialSelection.checklist_lob || commercialSelection.productId;
        body.health_coverage_id = commercialSelection.coverageId || undefined;
      } else if (isGeneralProductPicker) {
        body.general_product_id = commercialSelection.checklist_lob || commercialSelection.productId;
        body.general_coverage_id = commercialSelection.coverageId || undefined;
      } else {
        body.commercial_product_id = commercialSelection.productId;
      }
    } else if (normalizedOptions.length > 0) {
      body[productField] = activeProduct;
    }
    if (vertical === 'insurance') {
      if (companyId) body.insurance_company_id = companyId;
      if (companyName) body.insurance_company_name = companyName;
    }
    return body;
  };

  useEffect(() => {
    if (productValue !== undefined) return;
    if (productDefault) setProduct(productDefault);
  }, [productDefault, productValue]);

  const allSamples = samples || presets?.insurance || [];
  const sampleList = useCommercialPicker
    ? allSamples.filter((s) => insuranceSampleMatches(s, commercialSelection))
    : (normalizedOptions.length > 0 && vertical === 'insurance'
      ? allSamples.filter((s) => (s.insurance_line || s.product_line || s.product_type) === activeProduct)
      : allSamples);

  const sampleIds = sampleList.map((s) => s.id).join('|');
  useEffect(() => {
    if (tab === 'sample' && !sampleIds) setTab('files');
    if (dataId && !sampleIds.split('|').includes(dataId)) setDataId('');
  }, [tab, sampleIds, dataId]);

  const visibleTabs = TABS.filter((t) => t.id !== 'sample' || sampleList.length > 0);

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
        const bad = new Set((gate.irrelevant || []).map((r) => r.filename));
        const kept = files.filter((f) => !bad.has(f.filename));
        if (!kept.length) {
          setError('All files look irrelevant — add underwriting documents');
          return;
        }
        setFiles(kept);
        setRunning(true);
        try {
          const body = applyLineFields(buildSubmissionPayload(kept, useLlm));
          if (includePurpose) body.purpose = purpose;
          body.require_documents = true;
          if (selectedState) body.state_code = selectedState;
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
      if (selectedState) body.state_code = selectedState;
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
    setRunning(true);
    try {
      await onRunDemo?.(vertical, dataId);
    } catch (e) {
      const msg = e.message || 'Sample run failed';
      if (/disabled in BANK_MODE|Sample data is disabled|Sign in to run sample/i.test(msg)) {
        setError('Sign in as a Rytera underwriter to run this sample pack. If you are already signed in, refresh and try again.');
      } else {
        setError(msg);
      }
    } finally {
      setRunning(false);
    }
  };

  const companySelected = companyId || companyName;
  const lineSelected = useCommercialPicker
    ? isCommercialSelectionComplete(commercialSelection)
    : !!activeProduct || (tab === 'sample' && !!dataId);

  const confirmationText = `${companyName || companyId || 'Any company'} · ${useCommercialPicker ? (commercialSelection?.insurance_line || commercialSelection?.productName || 'Any line') : (activeProduct || 'Any line')}`;

  if (guidedFlow) {
    return (
      <div className="space-y-5">
        <div className="flex items-center gap-3">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex items-center gap-2">
              <div className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold transition-colors ${
                guidedStep >= s ? 'bg-brand text-white' : 'bg-surface-overlay text-slate-500 ring-1 ring-white/10'
              }`}>{s}</div>
              <span className={`text-xs font-medium ${guidedStep >= s ? 'text-slate-200' : 'text-slate-400'}`}>
                {s === 1 ? 'Company' : s === 2 ? 'Source & Line' : 'Run'}
              </span>
              {s < 3 && <ChevronRight className="h-3 w-3 text-slate-500" />}
            </div>
          ))}
        </div>

        <div className={`rounded-xl border p-4 transition-colors ${guidedStep === 1 ? 'border-brand/30 bg-brand/5' : 'border-white/[0.06] bg-surface/30'}`}>
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">1. Select company / person</p>
            {companySelected && guidedStep > 1 && (
              <button type="button" onClick={() => setGuidedStep(1)} className="text-[11px] text-brand hover:underline">Edit</button>
            )}
          </div>
          {guidedStep === 1 ? (
            <>
              {vertical === 'insurance' && (
                <CompanyPicker
                  value={companyId}
                  name={companyName}
                  disabled={running}
                  onChange={(c) => { setCompanyId(c.id || ''); setCompanyName(c.name || ''); }}
                />
              )}
              <div className="mt-3 flex justify-end">
                <button type="button" onClick={() => setGuidedStep(2)}
                  className="btn-primary btn-sm text-xs">
                  Continue <ChevronRight className="h-3 w-3" />
                </button>
              </div>
            </>
          ) : (
            <p className="text-sm text-slate-300">{companyName || companyId || 'No company selected'}</p>
          )}
        </div>

        {guidedStep >= 2 && (
          <div className={`rounded-xl border p-4 transition-colors ${guidedStep === 2 ? 'border-brand/30 bg-brand/5' : 'border-white/[0.06] bg-surface/30'}`}>
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">2. Select source & line of business</p>
              {lineSelected && guidedStep > 2 && (
                <button type="button" onClick={() => setGuidedStep(2)} className="text-[11px] text-brand hover:underline">Edit</button>
              )}
            </div>
            {guidedStep === 2 ? (
              <div className="space-y-3">
                <div className="flex gap-1 rounded-lg bg-surface/60 p-0.5">
                  {visibleTabs.map((t) => (
                    <button key={t.id} type="button" onClick={() => { setTab(t.id); setError(''); setWarning(''); }}
                      className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                        tab === t.id ? 'bg-brand/15 text-brand ring-1 ring-brand/25' : 'text-slate-500 hover:text-slate-300'
                      }`}>
                      <span className="inline-flex items-center gap-1"><t.icon className="h-3 w-3" /> {t.label}</span>
                    </button>
                  ))}
                </div>

                {tab === 'files' && (
                  <FileDropZone onDrop={handleDrop} files={files} fileScores={fileScores} onRemove={removeFile} onRemoveAll={() => { setFiles([]); setWarning(''); }} />
                )}

                {tab === 'connect' && (
                  <ConnectAndPull
                    vertical={vertical}
                    insuranceLine={activeProduct || ''}
                    lifeProductId={isLifeProductPicker ? (commercialSelection?.checklist_lob || commercialSelection?.productId || '') : ''}
                    lifeCoverageId={isLifeProductPicker ? (commercialSelection?.coverageId || '') : ''}
                    healthProductId={isHealthProductPicker ? (commercialSelection?.checklist_lob || commercialSelection?.productId || '') : ''}
                    healthCoverageId={isHealthProductPicker ? (commercialSelection?.coverageId || '') : ''}
                    generalProductId={isGeneralProductPicker ? (commercialSelection?.checklist_lob || commercialSelection?.productId || '') : ''}
                    generalCoverageId={isGeneralProductPicker ? (commercialSelection?.coverageId || '') : ''}
                    commercialProductId={(!isLifeProductPicker && !isHealthProductPicker && !isGeneralProductPicker) ? (commercialSelection?.productId || '') : ''}
                    coverageId={commercialSelection?.coverageId || ''}
                    productName={commercialSelection?.productName || ''}
                    coverageName={commercialSelection?.coverageName || ''}
                    commercialCategoryId={commercialSelection?.categoryId || ''}
                    insuranceCompanyId={companyId}
                    insuranceCompanyName={companyName}
                    strictRelevance={strictRelevance}
                    onRunJob={onRunJob || (onSubmit ? (jobId) => onSubmit?.({ _jobId: jobId }) : undefined)}
                    onRunResult={onRunResult}
                  />
                )}

                {tab === 'sample' && (
                  <div className="space-y-3">
                    {sampleList.length === 0 ? (
                      <div className="rounded-xl border border-dashed border-white/[0.12] bg-surface/30 px-4 py-5 text-center">
                        <p className="text-sm font-medium text-slate-300">
                          {vertical === 'insurance' ? `No demo case for ${insuranceLineLabel(activeProduct)} yet — coming soon.` : 'No sample data sets available.'}
                        </p>
                        <p className="mt-1 text-xs text-slate-400">Upload files in the Files tab or connect a source above.</p>
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
                        {dataId && <p className="text-xs text-slate-400">{sampleList.find((s) => s.id === dataId)?.description}</p>}
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

                {useCommercialPicker ? (
                  <CommercialLinePicker
                    taxonomy={commercialTaxonomy}
                    value={commercialSelection}
                    onChange={onCommercialSelectionChange}
                    disabled={running}
                  />
                ) : normalizedOptions.length > 0 && (
                  <select value={activeProduct} onChange={(e) => pickProduct(e.target.value)}
                    className="input-field w-full text-xs" aria-label="Line of business">
                    {normalizedOptions.map((opt) => (
                      <option key={opt.id} value={opt.id}>{opt.label}</option>
                    ))}
                  </select>
                )}

                <div className="flex justify-end">
                  <button type="button" onClick={() => setGuidedStep(3)} disabled={!lineSelected}
                    className="btn-primary btn-sm text-xs disabled:opacity-40">
                    Continue <ChevronRight className="h-3 w-3" />
                  </button>
                </div>
              </div>
            ) : (
              <p className="text-sm text-slate-300">{confirmationText}</p>
            )}
          </div>
        )}

        {guidedStep >= 3 && (
          <div className={`rounded-xl border p-4 transition-colors ${guidedStep === 3 ? 'border-brand/30 bg-brand/5' : 'border-white/[0.06] bg-surface/30'}`}>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">3. Run pipeline</p>
            <p className="text-xs text-slate-300 mb-3">Pipeline will run as <span className="font-medium text-white">{confirmationText}</span></p>
            {files.length === 0 && tab !== 'sample' && (
              <div className="mb-3 flex items-center gap-2 rounded-lg bg-amber-500/10 border border-amber-500/20 px-3 py-2.5">
                <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400" />
                <p className="text-xs text-amber-200">No files attached. Go back to step 2 to upload files, connect a data source, or pick a sample dataset.</p>
              </div>
            )}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <HintCheckbox hint={UI_HINTS.llmExtraction} label="LLM extraction" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} />
              </div>
              <Hint text={UI_HINTS.runPipeline}>
                <button type="button" onClick={tab === 'sample' && dataId ? runSample : runFiles} disabled={running || (tab !== 'sample' && !files.length) || (tab === 'sample' && !dataId)}
                  className="btn-primary btn-sm text-xs disabled:opacity-40">
                  {running ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3 w-3" />}
                  {tab === 'sample' ? 'Run sample' : `Run pipeline${files.length ? ` (${files.length})` : ''}`}
                </button>
              </Hint>
            </div>
            {warning && <p className="mt-2 rounded-lg bg-amber-500/10 px-3 py-1.5 text-xs text-amber-200">{warning}</p>}
            {error && <p className="mt-2 rounded-lg bg-red-500/10 px-3 py-1.5 text-xs text-red-300">{error}</p>}
          </div>
        )}
      </div>
    );
  }

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <p className="text-sm font-semibold uppercase tracking-wider text-slate-400">Select files or data to run</p>
        <div className="flex rounded-lg bg-surface/60 p-0.5">
          {visibleTabs.map((t) => (
            <Hint key={t.id} text={t.hint}>
              <button type="button" onClick={() => { setTab(t.id); setError(''); setWarning(''); }}
                className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                  tab === t.id ? 'bg-brand/15 text-brand ring-1 ring-brand/25' : 'text-slate-500 hover:text-slate-300'
                }`}>
                <span className="inline-flex items-center gap-1"><t.icon className="h-3 w-3" /> {t.label}</span>
              </button>
            </Hint>
          ))}
        </div>
      </div>

      {vertical === 'insurance' && (
        <div className="mb-3">
          <CompanyPicker
            value={companyId}
            name={companyName}
            disabled={running}
            onChange={(c) => { setCompanyId(c.id || ''); setCompanyName(c.name || ''); }}
          />
        </div>
      )}

      {tab === 'files' && (
        <div className="space-y-3">
          <label
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            className="flex w-full cursor-pointer flex-col items-center justify-center gap-1 rounded-xl border border-dashed border-white/[0.12] bg-surface/30 px-4 py-6 text-center transition hover:border-brand/40 hover:bg-brand/5">
            <Upload className="h-5 w-5 text-slate-500" />
            <span className="text-sm font-medium text-slate-200">Drop multiple files here or click to browse</span>
            <span className="text-xs text-slate-400">.pdf .xml .json .txt .md .xlsx .docx .eml — multi-select supported</span>
            <input type="file" multiple className="hidden" accept=".xml,.json,.pdf,.txt,.md,.csv,.xlsx,.xls,.docx,.doc,.eml,.html,.png,.jpg,.jpeg,.tiff,.tif,.bmp"
              onChange={(e) => { addFiles(e.target.files); e.target.value = ''; }} />
          </label>

          {files.length > 0 && (
            <div className="rounded-lg border border-white/[0.06] bg-surface/40 p-2">
              <div className="mb-1.5 flex items-center justify-between px-1">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                  Files · {files.length}
                </p>
                <button
                  type="button"
                  onClick={() => { setFiles([]); setWarning(''); }}
                  className="inline-flex items-center gap-1 text-[11px] font-medium text-red-400 hover:text-red-300"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Delete all files
                </button>
              </div>
              <div className="max-h-44 space-y-1 overflow-y-auto">
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
                      <button
                        type="button"
                        onClick={() => removeFile(i)}
                        className="shrink-0 rounded p-1 text-red-400 hover:bg-red-500/10"
                        title={`Delete ${f.filename}`}
                        aria-label={`Delete ${f.filename}`}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  );
                })}
              </div>
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
                  <span className="hint-label cursor-help text-xs font-semibold uppercase tracking-wider text-slate-400">Line of business</span>
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
                  <button type="button" onClick={removeIrrelevantFiles} className="hint-label cursor-help text-xs text-amber-400/90 transition hover:text-amber-300">
                    Remove irrelevant
                  </button>
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
          healthProductId={isHealthProductPicker ? (commercialSelection?.checklist_lob || commercialSelection?.productId || '') : ''}
          healthCoverageId={isHealthProductPicker ? (commercialSelection?.coverageId || '') : ''}
          generalProductId={isGeneralProductPicker ? (commercialSelection?.checklist_lob || commercialSelection?.productId || '') : ''}
          generalCoverageId={isGeneralProductPicker ? (commercialSelection?.coverageId || '') : ''}
          commercialProductId={(!isLifeProductPicker && !isHealthProductPicker && !isGeneralProductPicker) ? (commercialSelection?.productId || '') : ''}
          coverageId={commercialSelection?.coverageId || ''}
          productName={commercialSelection?.productName || ''}
          coverageName={commercialSelection?.coverageName || ''}
          commercialCategoryId={commercialSelection?.categoryId || ''}
          insuranceCompanyId={companyId}
          insuranceCompanyName={companyName}
          strictRelevance={strictRelevance}
          onRunJob={onRunJob || (onSubmit ? (jobId) => onSubmit?.({ _jobId: jobId }) : undefined)}
          onRunResult={onRunResult}
        />
      )}

      {tab === 'sample' && (
        <div className="space-y-3">
          {sampleList.length === 0 ? (
            <div className="rounded-xl border border-dashed border-white/[0.12] bg-surface/30 px-4 py-5 text-center">
              <p className="text-sm font-medium text-slate-300">
                {vertical === 'insurance' ? `No demo case for ${insuranceLineLabel(activeProduct)} yet — coming soon.` : 'No sample data sets available.'}
              </p>
              <p className="mt-1 text-xs text-slate-400">Upload files in the Files tab or connect a source above.</p>
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
              {dataId && <p className="text-xs text-slate-400">{sampleList.find((s) => s.id === dataId)?.description}</p>}
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
