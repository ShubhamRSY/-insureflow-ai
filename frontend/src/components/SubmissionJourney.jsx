import { useEffect, useState } from 'react';
import {
  CheckCircle2, Circle, AlertTriangle, XCircle, MinusCircle,
  Shield, GitCompare, DollarSign, ClipboardCheck, Loader2,
  Users, FileText, BarChart3, Layers, Send, Truck, Building2,
  ChevronDown, ChevronRight,
} from 'lucide-react';
import { fmtCurrency, endpoints } from '../lib/api';
import { uwReasons } from '../lib/uwLanguage';
import { getJourneyContext } from '../lib/pipelineJourney';
import { insuranceLineLabel } from '../lib/insuranceLines';
import SimilarPriors from './SimilarPriors';
import { asList, displayText, fmtFixed, safeLower } from '../lib/safe';

function fmtTimestamp(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleTimeString();
}

const STATUS_ICON = {
  complete: { Icon: CheckCircle2, cls: 'text-emerald-400' },
  warning: { Icon: AlertTriangle, cls: 'text-amber-400' },
  failed: { Icon: XCircle, cls: 'text-red-400' },
  skipped: { Icon: MinusCircle, cls: 'text-slate-500' },
  pending: { Icon: Circle, cls: 'text-slate-600' },
  active: { Icon: Loader2, cls: 'text-brand-light animate-spin' },
};

const SEV_CLS = {
  critical: 'text-red-400 bg-red-500/10 ring-red-500/20',
  error: 'text-red-400 bg-red-500/10 ring-red-500/20',
  warning: 'text-amber-400 bg-amber-500/10 ring-amber-500/20',
  high: 'text-orange-400 bg-orange-500/10 ring-orange-500/20',
  moderate: 'text-amber-400 bg-amber-500/10 ring-amber-500/20',
  info: 'text-sky-400 bg-sky-500/10 ring-sky-500/20',
  low: 'text-slate-400 bg-slate-500/10 ring-slate-500/20',
};

function Section({ title, icon: Icon, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className="rounded-xl ring-1 ring-white/[0.04] bg-surface-overlay/40">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-4 py-3.5 text-left"
      >
        <h4 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
          {Icon && <Icon className="h-4 w-4" />}
          {title}
        </h4>
        {open ? <ChevronDown className="h-4 w-4 text-slate-500" /> : <ChevronRight className="h-4 w-4 text-slate-500" />}
      </button>
      {open && <div className="border-t border-white/[0.04] px-4 pb-4 pt-3">{children}</div>}
    </section>
  );
}

function DocPreviewModal({ doc, onClose }) {
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('content');

  useEffect(() => {
    let cancelled = false;
    if (!doc.bundleId || !doc.id) {
      setLoading(false);
      setError('Full document preview is not available for this file.');
      return () => {};
    }
    // Try draft bundle first, then fall back to completed pipeline audit
    endpoints
      .previewDraftDocument(doc.bundleId, doc.id)
      .then((d) => { if (!cancelled) setPreview(d); })
      .catch(() => {
        // Fall back to pipeline audit document endpoint
        endpoints.pipelineDocument(doc.bundleId, doc.id)
          .then((d) => { if (!cancelled) setPreview(d); })
          .catch((e) => { if (!cancelled) setError(e.message || 'Could not load preview.'); });
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [doc]);

  const extractedFields = preview?.extracted_fields || {};
  const hasExtraction = Object.keys(extractedFields).length > 0;
  const tabs = hasExtraction ? ['content', 'extraction'] : ['content'];

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-6" onClick={onClose}>
      <div
        className="max-h-[80vh] w-full max-w-2xl overflow-hidden rounded-2xl border border-white/[0.08] bg-surface-raised shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-3">
          <p className="min-w-0 truncate text-sm font-semibold text-slate-200">{doc.filename || doc.name || 'Document'}</p>
          <div className="flex items-center gap-2">
            {tabs.length > 1 && (
              <div className="flex rounded-lg bg-black/20 p-0.5">
                {tabs.map((tab) => (
                  <button
                    key={tab}
                    type="button"
                    onClick={() => setActiveTab(tab)}
                    className={`rounded-md px-2.5 py-1 text-xs font-medium transition ${activeTab === tab ? 'bg-brand text-white' : 'text-slate-400 hover:text-slate-200'}`}
                  >
                    {tab === 'content' ? 'Document' : 'Extracted Data'}
                  </button>
                ))}
              </div>
            )}
            <button type="button" onClick={onClose} className="rounded-lg px-2 py-1 text-xs text-slate-400 hover:bg-white/5 hover:text-white">Close</button>
          </div>
        </div>
        <div className="max-h-[64vh] overflow-y-auto px-5 py-4">
          {loading && (
            <p className="flex items-center gap-2 text-sm text-slate-400"><Loader2 className="h-4 w-4 animate-spin" /> Loading preview…</p>
          )}
          {!loading && error && <p className="text-sm text-amber-300/90">{error}</p>}
          {!loading && !error && activeTab === 'content' && (
            <pre className="whitespace-pre-wrap break-words font-mono text-[11px] leading-relaxed text-slate-300">
              {typeof preview === 'string' ? preview : displayText(preview?.content || preview?.text || preview?.snippet, 'No readable content available — file is stored as binary (PDF/image).')}
            </pre>
          )}
          {!loading && !error && activeTab === 'extraction' && hasExtraction && (
            <div className="space-y-3">
              {Object.entries(extractedFields).map(([fieldName, fields]) => (
                <div key={fieldName} className="rounded-lg bg-black/20 p-3">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">{fieldName.replace(/_/g, ' ')}</p>
                  <div className="mt-1.5 space-y-1">
                    {(Array.isArray(fields) ? fields : [fields]).map((f, i) => (
                      <div key={i} className="flex items-center gap-2 text-sm">
                        <span className="font-mono text-slate-300">{typeof f === 'string' ? f : f?.value || String(f)}</span>
                        {f?.confidence != null && (
                          <span className={`text-[10px] ${f.confidence >= 0.8 ? 'text-emerald-400' : f.confidence >= 0.5 ? 'text-amber-400' : 'text-red-400'}`}>
                            {Math.round(f.confidence * 100)}%
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
              {preview?.field_confidence && Object.keys(preview.field_confidence).length > 0 && (
                <div className="rounded-lg bg-brand/10 p-3">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Field Confidence Summary</p>
                  <div className="mt-1.5 grid grid-cols-2 gap-1">
                    {Object.entries(preview.field_confidence).slice(0, 12).map(([field, conf]) => (
                      <div key={field} className="flex items-center justify-between text-xs">
                        <span className="text-slate-400 truncate">{field.replace(/_/g, ' ')}</span>
                        <span className={`font-mono ${conf >= 0.8 ? 'text-emerald-400' : conf >= 0.5 ? 'text-amber-400' : 'text-red-400'}`}>
                          {Math.round(conf * 100)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function PipelineTimeline({ stages, processing, currentStage, expandedStage, onToggleStage, job }) {
  const list = asList(stages);
  const r = job?.results || {};
  const memo = r.memo || {};
  const [viewingDoc, setViewingDoc] = useState(null);
  const bundleId = r.bundle_id || job?.bundle_id || '';
  const jobDocs = asList(job?.documents || r.documents || []).map((d) => ({
    id: d.document_id || d.doc_id || d.id,
    filename: d.filename || d.name,
  }));
  const [bundleDocs, setBundleDocs] = useState([]);
  const docsForIntake = jobDocs.length > 0 ? jobDocs : bundleDocs;

  // Older jobs don't carry a documents list — pull it from the draft bundle
  // or the pipeline audit endpoint the first time the Intake stage is expanded.
  useEffect(() => {
    if (expandedStage !== 'intake' || docsForIntake.length > 0 || !bundleId) return undefined;
    let cancelled = false;
    // Try draft bundle first (pre-pipeline), then fall back to pipeline audit (post-pipeline)
    endpoints.getDraftBundle(bundleId)
      .then((b) => {
        if (cancelled) return;
        const draftDocs = asList(b?.documents).map((d) => ({ id: d.doc_id, filename: d.filename }));
        if (draftDocs.length > 0) {
          setBundleDocs(draftDocs);
        } else {
          // Fall back to pipeline audit documents
          endpoints.pipelineDocuments(bundleId)
            .then((pd) => {
              if (cancelled) return;
              setBundleDocs(asList(pd?.documents).map((d) => ({ id: d.doc_id, filename: d.filename })));
            })
            .catch(() => {});
        }
      })
      .catch(() => {
        // Draft bundle not found — try pipeline audit
        endpoints.pipelineDocuments(bundleId)
          .then((pd) => {
            if (cancelled) return;
            setBundleDocs(asList(pd?.documents).map((d) => ({ id: d.doc_id, filename: d.filename })));
          })
          .catch(() => {});
      });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expandedStage]);

  function getStageDetail(stageId) {
    const docs = docsForIntake;
    const filenames = docs.map((d) => d.filename || d.name || '').filter(Boolean);
    switch (stageId) {
      case 'intake':
        return {
          title: 'Intake — Documents Received',
          lines: [
            `${r.document_count ?? filenames.length ?? 0} document(s) received`,
            r.ocr_documents ? `${r.ocr_documents} document(s) read (OCR)` : null,
            `Bundle: ${r.bundle_id || '—'}`,
          ].filter(Boolean),
          docs,
        };
      case 'triage':
        return {
          title: 'Triage — Priority Scoring',
          lines: [
            `Priority score: ${r.triage_score != null ? `${Number(r.triage_score).toFixed(0)}/100` : '—'}`,
            `Priority level: ${r.triage_priority || '—'}`,
            r.document_checklist?.lob ? `Line of business: ${r.document_checklist.lob}` : null,
            r.document_checklist?.completeness_pct != null ? `Package completeness: ${Math.round(r.document_checklist.completeness_pct > 1 ? r.document_checklist.completeness_pct : r.document_checklist.completeness_pct * 100)}%` : null,
            (r.document_checklist?.missing_documents || []).length > 0 ? `Still outstanding from broker: ${(r.document_checklist.missing_documents || []).join(', ')}` : null,
          ].filter(Boolean),
        };
      case 'appetite':
        return {
          title: 'Appetite Filter',
          lines: [
            `Result: ${r.appetite_filter_passed === false ? 'Outside appetite' : r.appetite_needs_uw_referral ? 'Referral required' : 'Within appetite'}`,
            r.appetite_reason ? `Reason: ${r.appetite_reason}` : null,
          ].filter(Boolean),
        };
      case 'parse':
        return {
          title: 'Document Parsing',
          lines: [
            `${r.document_count ?? 0} document(s) reviewed`,
            r.ocr_documents ? `${r.ocr_documents} read via OCR` : null,
            memo.insured_name ? `Insured: ${memo.insured_name}` : null,
          ].filter(Boolean),
        };
      case 'verify':
        return {
          title: 'Verification & External Records',
          lines: [
            `${r.oracle_findings_count ?? 0} external record check(s) run`,
            r.ofac_cleared != null ? `OFAC / sanctions: ${r.ofac_cleared ? 'Cleared' : 'Flagged'}` : null,
            memo.insured_name ? `Insured identity: ${memo.insured_name}` : null,
            r.life_bureau_findings ? `Bureau findings: ${r.life_bureau_findings}` : null,
          ].filter(Boolean),
        };
      case 'reconcile':
        return {
          title: 'Cross-Document Reconciliation',
          lines: [
            r.reconciliation?.match_rate != null ? `Field match rate: ${Math.round(r.reconciliation.match_rate * 100)}%` : null,
            `${r.reconciliation_discrepancies ?? 0} conflicting value(s) across documents`,
            r.reconciliation?.overall_status ? `Status: ${r.reconciliation.overall_status}` : null,
          ].filter(Boolean),
        };
      case 'analyze':
        return {
          title: 'Risk Analysis & Scoring',
          lines: [
            memo.overall_risk_score != null ? `Risk score: ${Math.round(Number(memo.overall_risk_score) * 100)}/100` : null,
            memo.overall_risk_severity ? `Severity: ${memo.overall_risk_severity}` : null,
            `${(memo.key_findings || []).length} finding(s) on file`,
            memo.decision ? `Decision: ${memo.decision}` : null,
          ].filter(Boolean),
        };
      case 'price':
        return {
          title: 'Pricing',
          lines: [
            r.quote?.adjusted_premium != null ? `Indicated premium: $${Math.round(r.quote.adjusted_premium).toLocaleString()}` : null,
            r.quote?.base_premium != null ? `Base premium: $${Math.round(r.quote.base_premium).toLocaleString()}` : null,
            r.insurance_line ? `Line: ${r.insurance_line}` : null,
          ].filter(Boolean),
        };
      case 'decision':
        return {
          title: 'Final Decision',
          lines: [
            `Decision: ${(r.ai_decision || memo.decision || 'pending').toString().toUpperCase()}`,
            memo.human_review_required ? 'Underwriter review required before bind' : null,
            ...uwReasons(memo.human_review_reasons).slice(0, 5).map((rr) => rr),
          ].filter(Boolean),
        };
      default:
        return { title: stageId, lines: [stage.detail || 'No details available'] };
    }
  }
  return (
    <div className="space-y-2">
      <div>
        <div className="flex flex-wrap items-stretch gap-1.5">
          {list.map((stage, i) => {
            const status = processing && currentStage === stage.id ? 'active' : stage.status;
            const { Icon, cls } = STATUS_ICON[status] || STATUS_ICON.pending;
            const activeCls = status === 'active' ? 'border-brand/40 bg-brand/10 pipeline-stage-active' : status === 'complete' ? 'border-brand/20 bg-brand/5' : status === 'failed' ? 'border-red-500/20 bg-red-500/5' : 'border-white/[0.04] bg-surface/30';
            const isExpanded = expandedStage === stage.id;
            return (
              <div key={stage.id} className="flex items-stretch gap-0">
                <button
                  type="button"
                  onClick={() => onToggleStage(stage.id)}
                  className={`flex flex-col items-center gap-1.5 rounded-lg border px-3 py-2 min-w-[110px] text-left transition-all hover:border-brand/30 hover:bg-brand/5 cursor-pointer ${activeCls} ${isExpanded ? 'ring-1 ring-brand/40' : ''}`}
                >
                  <Icon className={`h-4 w-4 ${cls}`} />
                  <span className="text-sm font-semibold text-slate-200 text-center leading-tight">{displayText(stage.label)}</span>
                  <span className="text-[11px] text-slate-400 text-center leading-tight">{displayText(stage.detail)}</span>
                  {stage.findings > 0 && (
                    <span className="text-[10px] text-slate-500">{stage.findings} finding{stage.findings > 1 ? 's' : ''}</span>
                  )}
                </button>
                {i < list.length - 1 && (
                  <div className="flex items-center px-0.5">
                    <div className="h-px w-2 bg-white/[0.08]" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
      {/* Expanded stage details */}
      {expandedStage && (() => {
        const stage = list.find((s) => s.id === expandedStage);
        if (!stage) return null;
        const detail = getStageDetail(expandedStage);
        const bundleId = r.bundle_id || job?.bundle_id;
        return (
          <div className="rounded-lg border border-brand/20 bg-brand/5 p-4 mt-1">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-semibold text-slate-200">{detail.title}</h4>
              <button type="button" onClick={() => onToggleStage(null)} className="text-xs text-slate-500 hover:text-slate-300">Close</button>
            </div>
            <div className="space-y-1.5">
              {detail.lines.map((line, i) => (
                <div key={i} className="flex items-start gap-2 text-sm">
                  <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-brand/60" />
                  <span className="text-slate-300">{line}</span>
                </div>
              ))}
            </div>
            {asList(detail.docs).length > 0 && (
              <div className="mt-3 border-t border-white/[0.06] pt-3">
                <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">Documents on file</p>
                <ul className="divide-y divide-white/[0.04]">
                  {asList(detail.docs).map((d, i) => {
                    const name = d.filename || d.name || `Document ${i + 1}`;
                    const id = d.document_id || d.submission_id || d.id || '';
                    return (
                      <li key={`${id}-${i}`} className="flex items-center justify-between gap-3 py-2">
                        <span className="min-w-0 truncate text-sm text-slate-300"><FileText className="mr-2 inline h-3.5 w-3.5 text-slate-500" />{name}</span>
                        <button
                          type="button"
                          className="btn-secondary btn-sm shrink-0 text-xs"
                          onClick={() => setViewingDoc({ ...d, id, bundleId })}
                        >
                          View
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}
            {stage.findings > 0 && (
              <p className="mt-3 text-xs text-slate-500 border-t border-white/[0.04] pt-2">{stage.findings} finding{stage.findings > 1 ? 's' : ''} identified in this stage</p>
            )}
            {stage.duration && (
              <p className="mt-1 text-xs text-slate-500">Completed in {stage.duration}</p>
            )}
          </div>
        );
      })()}
      {viewingDoc && <DocPreviewModal doc={viewingDoc} onClose={() => setViewingDoc(null)} />}
      {processing && (
        <div className="mt-2 flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-light opacity-75" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-brand-light" />
          </span>
          <p className="pipeline-live text-sm font-semibold text-brand-light">
            {currentStage ? `Processing — ${currentStage.replace(/_/g, ' ')}` : 'Pipeline in progress…'}
          </p>
        </div>
      )}
    </div>
  );
}

// Group backend stages into three user-facing phases (funnel). Everything still
// appears — deferred analyses are rendered as "skipped" chips inside their phase.
const PHASE_DEFS = [
  { label: '1 · Triage', ids: ['intake', 'triage', 'appetite'] },
  { label: '2 · Risk & Price', ids: ['parse', 'vision', 'verify', 'reconcile', 'analyze', 'portfolio', 'reinsurance', 'price'] },
  { label: '3 · Decision', ids: ['decision', 'integrate', 'integration'] },
];

function groupStagesByPhase(stages = [], processing = false) {
  return PHASE_DEFS.map((phase) => ({
    label: phase.label,
    stages: asList(stages).filter((s) => phase.ids.includes(s.id)),
  })).filter((phase) => phase.stages.length > 0 || processing);
}

function PhaseStrip({ phases, processing, currentStage, expandedStage, onToggleStage, job }) {
  return (
    <div className="space-y-3">
      {phases.map((phase) => (
        <div key={phase.label}>
          <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">{phase.label}</p>
          <PipelineTimeline stages={phase.stages} processing={processing} currentStage={currentStage} expandedStage={expandedStage} onToggleStage={onToggleStage} job={job} />
        </div>
      ))}
    </div>
  );
}

function completenessDisplayPct(raw) {
  if (raw == null || Number.isNaN(Number(raw))) return null;
  const n = Number(raw);
  return n > 1 ? Math.round(n) : Math.round(n * 100);
}

function SubmissionQuality({ quality, docQuality, onRequestDocs, requesting, brokerRequest, brokerEmail, setBrokerEmail }) {
  const [showScoreDetail, setShowScoreDetail] = useState(false);
  const missing = asList(docQuality?.missing_documents || docQuality?.missing);
  const present = asList(docQuality?.present_documents || docQuality?.present);
  const pct = completenessDisplayPct(docQuality?.completeness_pct);
  const lob = docQuality?.lob || quality?.lob;
  const pending = quality?.pending || quality.score == null;
  const shareLink = brokerRequest?.broker_status_url
    || (brokerRequest?.broker_share_token
      ? `${typeof window !== 'undefined' ? window.location.origin : ''}/dashboard/broker/status/${brokerRequest.broker_share_token}`
      : '');
  const issues = asList(quality?.issues);
  return (
    <div className="rounded-xl bg-surface-overlay p-4 ring-1 ring-white/[0.04]">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Submission Quality</p>
          <p className="mt-1 text-base text-slate-300">
            {pending
              ? 'Waiting for intake & triage before scoring'
              : `${lob ? `${insuranceLineLabel(lob)} package · ` : ''}Completeness, appetite fit, and data trust`}
          </p>
          {!pending && (
            <p className="mt-0.5 text-[11px] text-slate-500">
              Measures data quality of the documents received (legibility, extraction confidence, appetite fit) — independent of how many required documents are present. See Document Completeness below for what's missing.
            </p>
          )}
        </div>
        <div className="text-right relative">
          {pending ? (
            <>
              <p className="text-3xl font-bold text-slate-500">—</p>
              <p className="text-sm text-slate-500">Scoring…</p>
            </>
          ) : (
            <>
              <button
                type="button"
                onClick={() => setShowScoreDetail(!showScoreDetail)}
                className="text-right group cursor-pointer"
              >
                <p className={`text-3xl font-bold ${quality.gradeColor} transition group-hover:opacity-80`}>{quality.grade}</p>
                <p className="text-sm text-slate-400 group-hover:text-slate-300 transition">{quality.score}/100</p>
              </button>
              {showScoreDetail && (
                <div className="absolute right-0 top-full z-50 mt-2 w-72 rounded-xl border border-white/[0.1] bg-surface-overlay p-4 shadow-xl">
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Score Breakdown</p>
                  <div className="space-y-1.5">
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-400">Base score</span>
                      <span className="text-slate-200">100</span>
                    </div>
                    {issues.map((issue, i) => (
                      <div key={i} className="flex justify-between text-sm">
                        <span className="text-amber-400/80 truncate max-w-[200px]">{issue}</span>
                        <span className="text-red-400 shrink-0">−</span>
                      </div>
                    ))}
                    <div className="border-t border-white/[0.06] pt-1.5 flex justify-between text-sm font-semibold">
                      <span className="text-slate-300">Final</span>
                      <span className={quality.gradeColor}>{quality.score}/100</span>
                    </div>
                  </div>
                  <button type="button" onClick={() => setShowScoreDetail(false)} className="mt-2 text-xs text-slate-500 hover:text-slate-300">Close</button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
      {!pending && docQuality && (
        <div className="mt-3 border-t border-white/[0.04] pt-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-400">{lob ? `${insuranceLineLabel(lob)} checklist` : 'Document completeness'}</span>
            <span className="text-slate-300">{pct != null ? `${pct}%` : '—'}</span>
          </div>
          <div className="mt-2 h-1.5 rounded-full bg-black/30">
            <div className="h-1.5 rounded-full bg-brand" style={{ width: `${pct ?? 0}%` }} />
          </div>
          {present.length > 0 && (
            <ul className="mt-2 space-y-1">
              {present.map((d, i) => (
                <li key={`p-${displayText(d) || i}`} className="text-sm text-emerald-400/90">Present: {displayText(d)}</li>
              ))}
            </ul>
          )}
          {missing.length > 0 && (
            <ul className="mt-2 space-y-1">
              {missing.map((d, i) => (
                <li key={`m-${displayText(d) || i}`} className="text-sm text-red-400/90">Missing: {displayText(d)}</li>
              ))}
            </ul>
          )}
          {missing.length > 0 && onRequestDocs && (
            <div className="mt-3 space-y-2 rounded-lg bg-black/20 p-3 ring-1 ring-white/[0.06]">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Request from broker</p>
              <p className="text-sm text-slate-400">
                Creates a status link the broker can open (no login). Optionally enter their email to send / draft the request.
              </p>
              <input
                type="email"
                className="input-field w-full text-sm"
                placeholder="Broker email (optional)"
                value={brokerEmail || ''}
                onChange={(e) => setBrokerEmail?.(e.target.value)}
              />
              <button type="button" onClick={onRequestDocs} disabled={requesting} className="btn-secondary btn-sm text-sm">
                <Send className="h-3.5 w-3.5" /> {requesting ? 'Sending…' : 'Send document request'}
              </button>
            </div>
          )}
          {brokerRequest && (
            <div className="mt-3 space-y-2 rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3 text-sm text-slate-300">
              <p className="font-medium text-emerald-300">{brokerRequest.message || 'Document request created'}</p>
              {(brokerRequest.requested_documents || []).length > 0 && (
                <p className="text-slate-400">Asked for: {(brokerRequest.requested_documents || []).join(', ')}</p>
              )}
              {shareLink && (
                <div className="flex flex-wrap items-center gap-2">
                  <a href={shareLink} target="_blank" rel="noreferrer" className="text-brand-light underline break-all">{shareLink}</a>
                  <button
                    type="button"
                    className="btn-secondary btn-sm text-xs"
                    onClick={() => navigator.clipboard?.writeText(shareLink)}
                  >
                    Copy link
                  </button>
                </div>
              )}
              {brokerRequest.email?.mailto && (
                <a href={brokerRequest.email.mailto} className="inline-flex text-sky-300 underline">
                  Open in email client (mailto)
                </a>
              )}
              {brokerRequest.email?.sent === false && brokerRequest.email?.reason && (
                <p className="text-xs text-amber-200/90">{brokerRequest.email.reason}</p>
              )}
              {brokerRequest.email?.sent === true && (
                <p className="text-xs text-emerald-300">Email delivered via SMTP to {brokerRequest.email.to}</p>
              )}
            </div>
          )}
        </div>
      )}
      {!pending && asList(quality.issues).length > 0 && (
        <ul className="mt-3 space-y-1 border-t border-white/[0.04] pt-3">
          {asList(quality.issues).map((issue) => (
            <li key={displayText(issue)} className="flex items-start gap-2 text-sm text-slate-400">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500/80" />
              {displayText(issue)}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function CopeDeepDive({ cope }) {
  if (!cope) return <p className="text-sm text-slate-400">COPE analysis loads after property data is parsed.</p>;
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {[
        ['Construction', cope.construction],
        ['Occupancy', cope.occupancy],
        ['Protection', cope.protection],
        ['Exposure', cope.exposure],
      ].map(([label, data]) => (
        <div key={label} className="rounded-lg bg-black/20 p-3">
          <p className="text-xs uppercase text-slate-400">{label}</p>
          <p className="mt-1 text-sm font-medium capitalize text-slate-200">
            {displayText(data?.class) || asList(data?.types).join(', ') || displayText(data?.raw, '—')}
          </p>
          {data?.mod_pct != null && (
            <p className={`text-xs ${data.mod_pct > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
              {data.mod_pct > 0 ? '+' : ''}{data.mod_pct}% schedule mod
            </p>
          )}
        </div>
      ))}
      <div className="sm:col-span-2 rounded-lg bg-brand/10 px-3 py-2 text-sm text-slate-300">
        Grade: <strong className="uppercase">{displayText(cope.cope_score?.risk_grade, '—')}</strong>
        {' · '}Schedule mod: {cope.cope_score?.schedule_mod_pct > 0 ? '+' : ''}{cope.cope_score?.schedule_mod_pct ?? 0}%
        {' · '}Score: {fmtFixed(cope.cope_score?.total_score, 3) || '—'}
      </div>
    </div>
  );
}

function LifeMedicalPanel({ job }) {
  const quote = job?.results?.quote_full || job?.results?.quote || {};
  const meta = quote.metadata || quote || {};
  const medical = meta.medical || quote.medical || {};
  const memo = job?.results?.memo || {};
  const face = meta.face_amount || meta.tiv || quote.tiv || 0;
  const decision = (job?.results?.ai_decision || memo.decision || '').toString().replace(/_/g, ' ');
  const conditions = asList(meta.conditions || memo.conditions);
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div className="rounded-lg bg-black/20 p-3">
        <p className="text-xs uppercase text-slate-400">UW Class</p>
        <p className="mt-1 text-sm font-medium capitalize text-slate-200">{displayText(medical.underwriting_class, '—')}</p>
      </div>
      <div className="rounded-lg bg-black/20 p-3">
        <p className="text-xs uppercase text-slate-400">Tobacco</p>
        <p className="mt-1 text-sm font-medium text-slate-200">{medical.tobacco ? 'Yes' : medical.tobacco === false ? 'No' : '—'}</p>
      </div>
      <div className="rounded-lg bg-black/20 p-3">
        <p className="text-xs uppercase text-slate-400">Face Amount</p>
        <p className="mt-1 text-sm font-medium text-slate-200">{face ? `$${Number(face).toLocaleString()}` : '—'}</p>
      </div>
      <div className="rounded-lg bg-black/20 p-3">
        <p className="text-xs uppercase text-slate-400">Decision</p>
        <p className="mt-1 text-sm font-medium uppercase text-slate-200">{decision || '—'}</p>
      </div>
      <div className="rounded-lg bg-black/20 p-3">
        <p className="text-xs uppercase text-slate-400">Rate Filing</p>
        <p className="mt-1 text-sm font-medium text-slate-200">{displayText(meta.filing_id || quote.filing_id, '—')}</p>
      </div>
      <div className="rounded-lg bg-black/20 p-3">
        <p className="text-xs uppercase text-slate-400">Indicated Premium</p>
        <p className="mt-1 text-sm font-medium text-slate-200">{fmtCurrency(quote.adjusted_premium ?? meta.adjusted_premium)}</p>
      </div>
      {memo.executive_summary && (
        <div className="sm:col-span-2 rounded-lg bg-brand/10 px-3 py-2 text-sm text-slate-300">
          {displayText(memo.executive_summary)}
        </div>
      )}
      {conditions.length > 0 && (
        <div className="sm:col-span-2 rounded-lg bg-amber-500/10 px-3 py-2 text-sm text-amber-200">
          {conditions.map((c, i) => <div key={i}>• {displayText(c)}</div>)}
        </div>
      )}
    </div>
  );
}

// Shows which agent raised how many findings, at what severity — a useful
// audit-trail view the severity-sorted "Why This Decision" list doesn't
// give. Deliberately does NOT re-print finding title/description text here;
// that's the exact same data already shown as full cards in "Why This
// Decision" above, and duplicating it verbatim in a second section was the
// bug being fixed.
function AgentFindingsPanel({ sections }) {
  const list = asList(sections);
  if (!list.length) return <p className="text-sm text-slate-400">No agent findings yet.</p>;
  return (
    <div className="space-y-2">
      <p className="text-xs text-slate-500">Which agent raised what — see "Why This Decision" above for the full finding text.</p>
      {list.map((section) => {
        const findings = asList(section.findings);
        const counts = { critical: 0, high: 0, moderate: 0, low: 0 };
        findings.forEach((f) => { const s = safeLower(f?.severity, 'moderate'); if (counts[s] != null) counts[s] += 1; });
        return (
          <div key={section.key} className="rounded-lg bg-black/20 p-2.5 text-sm">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                {section.success === false
                  ? <AlertTriangle className="h-3 w-3 text-amber-500/70 shrink-0" />
                  : <CheckCircle2 className="h-3 w-3 text-emerald-500/60 shrink-0" />}
                <span className="font-medium text-slate-300">{section.label}</span>
              </div>
              <div className="flex gap-1.5">
                {Object.entries(counts).map(([sev, n]) => n > 0 && (
                  <span key={sev} className={`rounded px-1.5 py-0.5 text-[10px] uppercase ring-1 ring-inset ${SEV_CLS[sev] || SEV_CLS.moderate}`}>{n} {sev}</span>
                ))}
                {findings.length === 0 && <span className="text-xs text-slate-500">clean</span>}
              </div>
            </div>
            {(section.processingTimeMs != null || section.processedAt) && (
              <div className="mt-1 flex gap-3 pl-5 text-[9px] uppercase tracking-wide text-slate-600">
                {section.processedAt && <span>{fmtTimestamp(section.processedAt)}</span>}
                {section.processingTimeMs != null && <span>{Math.round(section.processingTimeMs)}ms</span>}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function ProvenancePanel({ provenance }) {
  if (!provenance.totalFields) {
    return (
      <p className="text-sm text-slate-400">
        {provenance.isLife
          ? 'Life packages often lack ACORD field provenance — medical UW class and application fields appear after extract.'
          : 'No cross-document fields were reconciled yet (common when structured ACORD data is missing).'}
      </p>
    );
  }
  return (
    <div>
      <div className="mb-3 flex gap-4 text-sm text-slate-400">
        <span>{provenance.totalFields} fields tracked</span>
        <span className="text-emerald-400">{provenance.verifiedFields} verified</span>
        {provenance.contradictedFields > 0 && (
          <span className="text-red-400">{provenance.contradictedFields} contradicted</span>
        )}
      </div>
      <div className="space-y-1.5">
        {provenance.fields.map((f) => (
          <div key={f.field} className={f.conflicts?.length ? 'rounded-lg border border-red-500/20 bg-red-500/5 p-2' : 'rounded-lg bg-black/20 p-2'}>
            <div className="grid grid-cols-4 gap-2 text-sm">
              <span className="font-medium text-slate-300">{displayText(f.field)}</span>
              <span className="truncate font-mono text-slate-400">{displayText(f.value, '—')}</span>
              <span className="truncate text-slate-500">{displayText(f.source)}</span>
              <span className="capitalize text-slate-500">{displayText(f.trust)}</span>
            </div>
            {f.conflicts?.length > 0 && (
              <div className="mt-1.5 border-t border-red-500/20 pt-1.5 text-xs text-red-300">
                <p className="font-semibold uppercase tracking-wide">Conflicts with:</p>
                {f.conflicts.map((c, i) => (
                  <p key={i}>'{displayText(c.value)}' from {displayText(c.source)}</p>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function HumanCheckpoints({ checkpoints, bundleId, onResolve }) {
  const list = asList(checkpoints);
  if (!list.length) return <p className="text-sm text-emerald-400/90">No pending human checkpoints.</p>;
  return (
    <div className="space-y-2">
      {list.map((cp) => (
        <div key={cp.id} className="rounded-lg bg-amber-500/10 p-3 ring-1 ring-amber-500/20">
          <p className="text-sm font-medium text-amber-200">{displayText(cp.label)}</p>
          <p className="mt-1 text-sm text-amber-200/70">{displayText(cp.reason)}</p>
          {cp.status === 'pending' && onResolve && (
            <div className="mt-2 flex gap-2">
              <button type="button" onClick={() => onResolve(cp.id, 'approve')} className="btn-secondary btn-sm text-sm">Approve</button>
              <button type="button" onClick={() => onResolve(cp.id, 'reject')} className="btn-secondary btn-sm text-xs text-red-300">Reject</button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function PipelineStory({ story, decision, riskScore, humanReviewRequired }) {
  const [expanded, setExpanded] = useState(false);
  if (!story || story.length === 0) return <p className="text-sm text-slate-400">Pipeline story loads after processing completes.</p>;
  function fmtMs(ms) {
    if (ms == null || ms <= 0) return '';
    return ms < 1000 ? `${Math.round(ms)}ms` : `${(ms / 1000).toFixed(1)}s`;
  }
  const displayStory = expanded ? story : story.filter((s) => s.status !== 'skipped').slice(0, 6);
  return (
    <div className="space-y-2">
      {decision && (
        <div className={`rounded-lg px-3 py-2 text-sm ring-1 ${
          decision === 'accept' ? 'bg-emerald-500/10 ring-emerald-500/20 text-emerald-200'
          : decision === 'decline' ? 'bg-red-500/10 ring-red-500/20 text-red-200'
          : 'bg-amber-500/10 ring-amber-500/20 text-amber-200'
        }`}>
          <span className="font-semibold uppercase">{decision.replace(/_/g, ' ')}</span>
          {riskScore != null && <span className="ml-2 text-xs opacity-70">· Risk {Math.round(riskScore * 100)}/100</span>}
          {humanReviewRequired && <span className="ml-2 text-xs opacity-70">· Underwriter review required</span>}
        </div>
      )}
      <div className="space-y-1.5">
        {displayStory.map((step, i) => (
          <div key={step.stage || i} className="flex items-start gap-2.5 rounded-lg bg-black/20 p-2.5">
            <span className={`mt-0.5 h-2 w-2 shrink-0 rounded-full ${
              step.status === 'complete' ? 'bg-emerald-400'
              : step.status === 'warning' ? 'bg-amber-400'
              : step.status === 'failed' ? 'bg-red-400'
              : step.status === 'skipped' ? 'bg-slate-500'
              : 'bg-brand'
            }`} />
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold text-slate-300">{step.title}</p>
              <p className="text-xs text-slate-400">{step.narrative}</p>
              {step.findings > 0 && (
                <p className="text-[10px] text-slate-500 mt-0.5">{step.findings} finding{step.findings !== 1 ? 's' : ''}</p>
              )}
            </div>
            {step.duration_ms != null && step.duration_ms > 0 && (
              <span className="shrink-0 text-[10px] text-slate-500">{fmtMs(step.duration_ms)}</span>
            )}
          </div>
        ))}
      </div>
      {story.length > 6 && (
        <button type="button" onClick={() => setExpanded(!expanded)} className="text-xs text-brand-light hover:underline">
          {expanded ? 'Show fewer steps' : `Show all ${story.length} steps`}
        </button>
      )}
    </div>
  );
}

function AuditTrailInline({ audit }) {
  const entries = asList(audit?.audit_trail?.entries);
  if (!entries.length) return <p className="text-sm text-slate-400">Audit trail populates as the pipeline runs.</p>;
  return (
    <div className="max-h-48 space-y-1 overflow-y-auto">
      {entries.slice(-8).reverse().map((e, i) => (
        <div key={e.entry_id || i} className="flex gap-2 rounded-lg bg-black/20 p-2 text-sm">
          <FileText className="mt-0.5 h-3 w-3 shrink-0 text-slate-500" />
          <div>
            <p className="font-medium text-slate-300">{displayText(e.event).replace(/_/g, ' ')}</p>
            <p className="text-slate-500">{displayText(e.message)}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

function EnterpriseOpsPanel({ ecosystem, onDispatchLC }) {
  if (!ecosystem) return null;
      const feeds = asList(ecosystem.oracle_feeds?.feeds || ecosystem.oracle_feeds);
  return (
    <div className="space-y-3 text-sm">
      <div>
        <p className="mb-1 font-semibold uppercase tracking-wider text-slate-500">External data feeds</p>
        <div className="flex flex-wrap gap-2">
          {feeds.map((f) => {
            const isLive = f.mode === 'live' && f.reachable;
            const label = isLive ? 'live' : (f.configured === false ? 'not configured' : f.mode);
            return (
              <span key={f.name} title={isLive ? undefined : `Set the API key for ${f.name} — code-ready is not live ${f.name}`} className={`rounded-full px-2 py-0.5 ring-1 cursor-default ${isLive ? 'text-emerald-400 ring-emerald-500/30' : 'text-slate-400 ring-white/10'}`}>
                {f.name}: {label}
              </span>
            );
          })}
        </div>
        {feeds.some((f) => !(f.mode === 'live' && f.reachable)) && (
          <p className="mt-2 text-[11px] text-amber-300/90">Simulated / not configured is not live CLUE (or A-PLUS / NCCI). The pipeline fail-closes when those keys are required.</p>
        )}
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        <div className="rounded-lg bg-black/20 p-2">
          <p className="text-xs uppercase text-slate-400">Claims ops</p>
          <p className="text-slate-300">{ecosystem.claims?.closed_claims ?? 0} closed · ${(ecosystem.claims?.total_incurred ?? 0).toLocaleString()} incurred</p>
        </div>
        <div className="rounded-lg bg-black/20 p-2">
          <p className="text-xs uppercase text-slate-400">Actuarial filing</p>
          <p className="text-slate-300">{ecosystem.actuarial?.filing_status?.replace(/_/g, ' ')}</p>
        </div>
        <div className="rounded-lg bg-black/20 p-2">
          <p className="text-xs uppercase text-slate-400">Agency / CRM</p>
          <p className="text-slate-300">{ecosystem.agency?.agency_name || 'Broker portal link'}</p>
        </div>
        <div className="rounded-lg bg-black/20 p-2">
          <p className="text-xs uppercase text-slate-400">Actuarial loop</p>
          <p className="text-slate-300">{displayText(ecosystem.actuarial_loop?.recommended_action)}</p>
        </div>
      </div>
      {onDispatchLC && (
        <button type="button" onClick={onDispatchLC} className="btn-secondary btn-sm text-sm">
          <Truck className="h-3 w-3" /> Dispatch loss control inspection
        </button>
      )}
    </div>
  );
}

function VerificationCard({ verification }) {
  const hasData = verification.oracleCount != null || verification.copeGrade || verification.matchRate != null || verification.isLife || verification.lifeClass;
  if (!hasData) return <p className="text-sm text-slate-400">Verification checks run after document parse completes.</p>;
  if (verification.isLife) {
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div><p className="text-xs uppercase text-slate-400">Path</p><p className="mt-1 text-sm font-semibold">Life medical</p></div>
        <div><p className="text-xs uppercase text-slate-400">UW Class</p><p className="mt-1 text-sm font-semibold capitalize">{displayText(verification.lifeClass, '—')}</p></div>
        <div><p className="text-xs uppercase text-slate-400">Tobacco</p><p className="mt-1 text-sm font-semibold">{verification.tobacco ? 'Yes' : 'No'}</p></div>
        <div><p className="text-xs uppercase text-slate-400">Filing</p><p className="mt-1 text-sm font-semibold">{displayText(verification.filingId, '—')}</p></div>
      </div>
    );
  }
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <div><p className="text-xs uppercase text-slate-400">Oracles</p><p className="mt-1 text-sm font-semibold">{verification.oracleCount ?? 0}</p></div>
      <div><p className="text-xs uppercase text-slate-400">COPE</p><p className="mt-1 text-sm font-semibold capitalize">{verification.copeGrade?.replace(/_/g, ' ') || '—'}</p></div>
      <div><p className="text-xs uppercase text-slate-400">Reconciliation</p><p className="mt-1 text-sm font-semibold capitalize">{verification.reconStatus || '—'}</p></div>
      <div><p className="text-xs uppercase text-slate-400">Market</p><p className="mt-1 text-sm font-semibold capitalize">{verification.marketPhase?.replace(/_/g, ' ') || '—'}</p></div>
    </div>
  );
}

function ReconciliationPanel({ reconciliation }) {
  const { matchRate, matchedFields, totalFields, overallStatus } = reconciliation || {};
  const discrepancies = asList(reconciliation?.discrepancies);
  if (!discrepancies.length && matchRate == null) {
    return <p className="text-sm text-slate-400">Reconciliation data not available.</p>;
  }
  return (
    <div>
      <div className="mb-2 flex gap-3 text-xs text-slate-400">
        {matchRate != null && <span>{Math.round(matchRate * 100)}% match</span>}
        {totalFields > 0 && <span>{matchedFields}/{totalFields} fields</span>}
        <span className="capitalize">{overallStatus}</span>
      </div>
      {discrepancies.length === 0 ? (
        <p className="text-sm text-emerald-400/90">No cross-document conflicts.</p>
      ) : (
        <div className="space-y-2">
          {discrepancies.slice(0, 6).map((d) => (
            <div key={`${d.field_path}-${d.source_a}`} className="rounded-lg bg-black/20 p-3">
              <p className="text-sm font-medium text-slate-300">{d.field_path}</p>
              <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
                <div><p className="text-xs text-slate-400">{d.source_a || 'Source A'}</p><p className="font-mono">{String(d.structured_value ?? '—')}</p></div>
                <div><p className="text-xs text-slate-400">{d.source_b || 'Source B'}</p><p className="font-mono">{String(d.unstructured_value ?? '—')}</p></div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function PricingBreakdown({ pricing }) {
  if (pricing.base == null && pricing.adjusted == null) {
    return <p className="text-sm text-slate-400">Premium calculated after risk scoring.</p>;
  }
  return (
    <div className="divide-y divide-white/[0.04] rounded-lg ring-1 ring-white/[0.04]">
      <div className="flex justify-between px-3 py-2 text-sm"><span className="text-slate-400">Base</span><span>{fmtCurrency(pricing.base)}</span></div>
      {asList(pricing.premiumMods).map((mod) => (
        <div key={mod.key} className="flex justify-between px-3 py-1.5 text-sm">
          <span className="text-slate-500">{mod.label}</span>
          <span>{mod.pct > 0 ? '+' : ''}{mod.pct}%</span>
        </div>
      ))}
      <div className="flex justify-between bg-brand/5 px-3 py-2"><span className="font-medium">Indicated</span><span className="font-bold">{fmtCurrency(pricing.adjusted)}</span></div>
    </div>
  );
}

const DEEP_DIVE_LABELS = {
  oracles: 'External oracles (CLUE · NCCI · CAT)',
  portfolio: 'Portfolio concentration',
  reinsurance: 'Reinsurance treaty fit',
  fraud_ml: 'ML fraud score',
  premium_ml: 'ML premium estimate',
  churn_ml: 'ML retention / churn',
};

function DeepDivePanel({ available, bundleId }) {
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const run = async () => {
    if (!bundleId || running) return;
    setRunning(true);
    setError(null);
    try {
      const res = await endpoints.deepDive(bundleId, available);
      setResults(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-3">
      {available.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {available.map((k) => (
            <span key={k} className="rounded-full bg-black/20 px-2 py-0.5 text-xs text-slate-400 ring-1 ring-white/10">
              {DEEP_DIVE_LABELS[k] || k}
            </span>
          ))}
        </div>
      )}
      <button type="button" onClick={run} disabled={running || !bundleId} className="btn-secondary btn-sm text-sm">
        {running ? <Loader2 className="h-3 w-3 animate-spin" /> : <BarChart3 className="h-3 w-3" />}
        {running ? 'Running…' : 'Run deep dive'}
      </button>
      {error && <p className="text-sm text-red-400">{error}</p>}
      {results?.findings && (
        <div className="grid gap-2">
          {Object.entries(results.findings).map(([key, value]) => {
            const findings = Array.isArray(value) ? value : value?.findings || [];
            const title = DEEP_DIVE_LABELS[key] || key;
            return (
              <div key={key} className="rounded-lg bg-black/20 p-2.5">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">{title}</p>
                {findings.length === 0 ? (
                  <p className="mt-1 text-xs text-emerald-400/90">No findings.</p>
                ) : (
                  <ul className="mt-1 space-y-1">
                    {findings.slice(0, 5).map((f, i) => (
                      <li key={f.finding_id || i} className="text-xs text-slate-400">
                        <span className={`rounded px-1.5 py-0.5 text-[11px] uppercase ring-1 ring-inset ${SEV_CLS[safeLower(f?.severity, 'moderate')] || SEV_CLS.moderate}`}>
                          {displayText(f.severity, 'info')}
                        </span>{' '}
                        {displayText(f.title || f.reason, JSON.stringify(f))}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function SubmissionJourney({ job }) {
  const ctx = getJourneyContext(job);
  const [cope, setCope] = useState(null);
  const [docQuality, setDocQuality] = useState(null);
  const [audit, setAudit] = useState(null);
  const [ecosystem, setEcosystem] = useState(null);
  const [pipelineStory, setPipelineStory] = useState(null);
  const [requesting, setRequesting] = useState(false);
  const [brokerEmail, setBrokerEmail] = useState('');
  const [brokerRequest, setBrokerRequest] = useState(null);
  const [checkpoints, setCheckpoints] = useState(ctx.checkpoints);
  const [expandedStage, setExpandedStage] = useState(null);

  useEffect(() => {
    setCheckpoints(ctx.checkpoints);
  }, [job]);

  useEffect(() => {
    if (!ctx.bundleId) return;
    let cancelled = false;
    const fromResults = job?.results?.document_checklist;
    if (fromResults && !cancelled) {
      setDocQuality(fromResults);
    }
    const isLife = safeLower(job?.results?.insurance_line || job?.results?.product_line) === 'life';
    const load = async () => {
      const tasks = [
        endpoints.missingDocuments(ctx.bundleId).then((d) => { if (!cancelled && d) setDocQuality(d); }).catch(() => {}),
        endpoints.auditTrail(ctx.bundleId).then((d) => { if (!cancelled) setAudit(d); }).catch(() => {}),
        endpoints.ecosystemBundle(ctx.bundleId).then((d) => { if (!cancelled) setEcosystem(d); }).catch(() => {}),
        endpoints.pipelineStory(ctx.bundleId).then((d) => { if (!cancelled) setPipelineStory(d); }).catch(() => {}),
      ];
      if (!isLife) {
        tasks.push(endpoints.copeAnalysis(ctx.bundleId).then((d) => { if (!cancelled) setCope(d); }).catch(() => {}));
      }
      await Promise.all(tasks);
    };
    load();
    return () => { cancelled = true; };
  }, [ctx.bundleId, job?.results?.insurance_line, job?.results?.product_line]);

  if (ctx.failed) return null;

  const isLifeLine = safeLower(job?.results?.insurance_line || job?.results?.product_line) === 'life';

  const handleRequestDocs = async () => {
    const missingList = asList(docQuality?.missing_documents || docQuality?.missing);
    if (!ctx.bundleId || !missingList.length) return;
    setRequesting(true);
    try {
      const res = await endpoints.requestBrokerDocs(ctx.bundleId, missingList, '', {
        broker_email: brokerEmail.trim(),
      });
      setBrokerRequest(res);
    } catch (e) {
      alert(e.message);
    } finally {
      setRequesting(false);
    }
  };

  const handleResolveCheckpoint = async (checkpointId, action) => {
    try {
      await endpoints.resolveCheckpoint(ctx.bundleId, checkpointId, action);
      setCheckpoints((prev) => asList(prev).map((c) => (c.id === checkpointId ? { ...c, status: action === 'approve' ? 'approved' : 'rejected' } : c)));
    } catch (e) {
      alert(e.message);
    }
  };

  const handleDispatchLC = async () => {
    try {
      const r = await endpoints.dispatchLossControl(ctx.bundleId, 'Requested from submission journey');
      alert(`Loss control scheduled: ${r.dispatch_id}`);
    } catch (e) {
      alert(e.message);
    }
  };

  const deepDiveAvailable = (job?.results?.deep_dive_available || []).filter(
    (k) => !isLifeLine || !['oracles', 'portfolio', 'reinsurance'].includes(k),
  );

  return (
    <div className="space-y-4">
      <div>
        <p className="text-xs font-bold uppercase tracking-widest text-brand-light/80">
          {isLifeLine ? 'Life Submission Journey' : 'Submission Journey'}
        </p>
        {displayText(ctx.insuredName) && <p className="mt-0.5 text-base text-slate-300">{displayText(ctx.insuredName)}</p>}
      </div>

      <SubmissionQuality
        quality={ctx.quality}
        docQuality={docQuality}
        onRequestDocs={ctx.bundleId ? handleRequestDocs : null}
        requesting={requesting}
        brokerRequest={brokerRequest}
        brokerEmail={brokerEmail}
        setBrokerEmail={setBrokerEmail}
      />

      <Section title="Pipeline" icon={ClipboardCheck}>
        <PhaseStrip phases={groupStagesByPhase(ctx.stages, ctx.processing)} processing={ctx.processing} currentStage={ctx.currentStage} expandedStage={expandedStage} onToggleStage={(id) => setExpandedStage((prev) => prev === id ? null : id)} job={job} />
      </Section>

      {!ctx.processing && pipelineStory?.story && (
        <Section title="What Happened — Plain English" icon={FileText} defaultOpen={true}>
          <PipelineStory
            story={pipelineStory.story}
            decision={pipelineStory.decision}
            riskScore={pipelineStory.risk_score}
            humanReviewRequired={pipelineStory.human_review_required}
          />
        </Section>
      )}

      <Section title="Human Checkpoints" icon={Users} defaultOpen={asList(checkpoints).length > 0}>
        <HumanCheckpoints checkpoints={checkpoints} bundleId={ctx.bundleId} onResolve={ctx.bundleId ? handleResolveCheckpoint : null} />
      </Section>

      {!ctx.processing && (
        <>
          <Section title={isLifeLine ? 'Life Verification' : 'Verification & Oracles'} icon={Shield}>
            <VerificationCard verification={ctx.verification} />
          </Section>

          {isLifeLine ? (
            <Section title="Life Medical UW" icon={BarChart3}>
              <LifeMedicalPanel job={job} />
            </Section>
          ) : (
            <Section title="COPE Deep Dive" icon={BarChart3}>
              <CopeDeepDive cope={cope} />
            </Section>
          )}

          <Section title="Agent Findings" icon={Users}>
            <AgentFindingsPanel sections={ctx.agentSections} />
          </Section>

          <Section title="Provenance" icon={Layers}>
            <ProvenancePanel provenance={ctx.provenance} />
          </Section>

          {!isLifeLine && (
            <Section title="Reconciliation" icon={GitCompare}>
              <ReconciliationPanel reconciliation={ctx.reconciliation} />
            </Section>
          )}

          <Section title="Pricing" icon={DollarSign}>
            <PricingBreakdown pricing={ctx.pricing} />
          </Section>

          {ctx.bundleId && deepDiveAvailable.length > 0 && (
            <Section title="Deep Dive" icon={BarChart3} defaultOpen={false}>
              <DeepDivePanel available={deepDiveAvailable} bundleId={ctx.bundleId} />
            </Section>
          )}

          <Section title="Audit Trail" icon={FileText} defaultOpen={false}>
            <AuditTrailInline audit={audit} />
          </Section>

          <Section title="Similar prior files" icon={GitCompare} defaultOpen={false}>
            <SimilarPriors bundleId={ctx.bundleId} />
          </Section>

          {!isLifeLine && (
            <Section title="Enterprise Ecosystem" icon={Building2} defaultOpen={false}>
              <EnterpriseOpsPanel ecosystem={ecosystem} onDispatchLC={ctx.bundleId ? handleDispatchLC : null} />
            </Section>
          )}
        </>
      )}
    </div>
  );
}
