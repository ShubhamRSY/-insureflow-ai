import { useEffect, useState } from 'react';
import { ChevronDown, ChevronRight, Eye, FileText, Loader2, User, Shield, AlertTriangle, ClipboardCheck, Clock, CheckCircle2 } from 'lucide-react';
import { displayText, safeLower } from '../lib/safe';
import { endpoints } from '../lib/api';
import { uwFinding, uwMemoText, uwReasons, premiumStepLabel } from '../lib/uwLanguage';
import { Hint } from './ui';

const FIELD_HINTS = {
  'Insured Name': 'The person or entity this policy would cover, as extracted from the application.',
  'Product': 'The insurance product line this submission was written for.',
  'Coverage': 'The specific coverage or plan variant selected within the product.',
  'Insurance Line': 'High-level line of business this submission is classified under — drives which rating tables and UW rules apply.',
  'Face Amount / TIV': 'Face amount (life) or Total Insured Value (property/casualty) — the maximum the policy would pay out.',
  'Base Premium': 'Premium before underwriting-class, band, or state adjustments are applied.',
  'Indicated Premium': "The AI's fully-loaded premium recommendation after every rating factor below is applied. Not a bound rate until an underwriter signs off.",
  'Primary State': 'Governing state for rate filing and regulatory rules on this policy.',
  'Broker': 'Producer of record who submitted this business.',
  'Policy Reference': 'Internal policy administration system reference number for this quote.',
  'Quote Valid Until': 'Date this indicated premium expires — reprice if binding after this date, since rates or risk may have moved.',
  'Issue State': 'State the policy will actually be issued in, if different from the primary rating state.',
  'Decision': 'The underwriting outcome the AI recommends — accept, conditional accept, refer for review, or decline.',
  'Risk Severity': "Overall severity bucket assigned from this file's findings — drives how much scrutiny the decision needs before sign-off.",
  'Suggested Premium Adjustment': 'Additional loading or credit the AI recommends on top of the indicated premium, based on findings not already priced in.',
  'Submission ID': 'Internal job identifier for this submission run — use it when searching logs or support tickets.',
  'Bundle ID': 'Identifier for the document bundle this submission was built from.',
  'Submitted': 'Timestamp the submission was received into the pipeline.',
  'Completed': 'Timestamp the pipeline finished processing and produced this memo.',
  'Processing Time': 'Wall-clock time the pipeline took from intake to a finished decision.',
  'Memo Generated': 'Timestamp this underwriting memo was generated.',
  'Approved By': 'Underwriter who signed off on this decision. "Pending" means no human sign-off has been recorded yet.',
  'Approved At': 'Timestamp of human sign-off.',
  'License #': "Signing underwriter's license number, recorded for audit and regulatory purposes.",
  'Loss Ratio': 'Incurred losses divided by earned premium for this risk\'s prior history — a core input to pricing adequacy.',
  'Basis': 'What the loss ratio and experience figures are measured against (e.g. per-exposure, per-payroll).',
  'Experience Mod': 'Multiplier applied for this risk\'s claim history relative to class average — above 1.0 means worse than average.',
};

function FieldLabel({ label }) {
  const hint = FIELD_HINTS[label];
  if (!hint) return <>{label}</>;
  return (
    <Hint text={hint}>
      <span className="hint-label cursor-help">{label}</span>
    </Hint>
  );
}

const BASIS_LABELS = {
  per_100_tiv: 'per $100 of insured value',
  payroll: 'per payroll',
  gross_sales: 'per gross sales',
  tiv: 'per insured value',
  expense_profit: 'expense & profit load',
  state: 'by state filing',
  schedule: 'property schedule',
  market: 'market conditions',
  deductible: 'deductible level',
  loss_ratio: 'claims history',
  tenure: 'years in business',
  uw_discretion: 'underwriter judgment',
};

function premiumBasisLabel(basis) {
  const b = String(basis || '').trim();
  if (!b) return '—';
  return BASIS_LABELS[b.toLowerCase()] || b.replace(/_/g, ' ');
}

const SEV_COLORS = {
  critical: 'bg-red-500/15 text-red-400 ring-red-500/30',
  high: 'bg-orange-500/15 text-orange-400 ring-orange-500/30',
  moderate: 'bg-amber-500/15 text-amber-400 ring-amber-500/30',
  low: 'bg-slate-500/15 text-slate-400 ring-slate-500/30',
};

const SEV_ORDER = { critical: 0, high: 1, moderate: 2, low: 3 };

const DECISION_COLORS = {
  accept: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400',
  conditional_accept: 'border-amber-500/40 bg-amber-500/10 text-amber-400',
  refer: 'border-sky-500/40 bg-sky-500/10 text-sky-400',
  decline: 'border-red-400/50 bg-red-500/15 text-red-300',
};

const DECISION_LABELS = {
  accept: 'Issue as Applied',
  conditional_accept: 'Issue with Amendments',
  refer: 'Refer for Review',
  decline: 'Decline',
};

const FINDING_CATEGORIES = {
  medical: ['health', 'medical', 'biometric', 'lab', 'mib', 'aps', 'vital', 'pharmacy', 'rx'],
  financial: ['financial', 'income', 'net_worth', 'insurable_interest', 'replacement', '1035', 'premium'],
  compliance: ['compliance', 'regulatory', 'sanctions', 'ofac', 'state', 'filing', 'license'],
  fraud: ['fraud', 'mice', 'moral_hazard', 'misrepresentation', 'material'],
  loss: ['loss', 'claims', 'loss_run', 'clue', 'ncci'],
};

function categorizeFinding(finding) {
  const title = safeLower(finding?.title, '');
  const desc = safeLower(finding?.description, '');
  const cat = safeLower(finding?.category, '');
  const combined = `${title} ${desc} ${cat}`;
  for (const [category, keywords] of Object.entries(FINDING_CATEGORIES)) {
    if (keywords.some((kw) => combined.includes(kw))) return category;
  }
  return 'other';
}

function fmtCurrency(v) {
  if (!v || v === 0) return '—';
  return `$${Math.round(v).toLocaleString()}`;
}

function fmtFactor(v) {
  if (v == null || v === '') return '—';
  const n = Number(v);
  if (isNaN(n)) return String(v);
  return n.toFixed(2);
}

function fmtPct(v) {
  if (v == null || v === '' || v === 0) return '0.0%';
  const n = Number(v);
  if (isNaN(n)) return String(v);
  return `${n.toFixed(1)}%`;
}

function fmtTimestamp(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
  } catch { return iso; }
}

export function Collapsible({ id, title, defaultOpen = false, children, badge }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div id={id} data-collapsed={!open} className="rounded-xl border border-white/[0.06] bg-surface/60">
      <button
        type="button"
        data-collapsible-toggle
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-4 py-3 text-left transition hover:bg-white/[0.02]"
      >
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{title}</span>
          {badge != null && (
            <span className="rounded-full bg-brand/15 px-1.5 py-0.5 text-[9px] font-bold text-brand">{badge}</span>
          )}
        </div>
        {open ? <ChevronDown className="h-4 w-4 text-slate-500" /> : <ChevronRight className="h-4 w-4 text-slate-500" />}
      </button>
      {open && <div className="border-t border-white/[0.04] px-4 pb-4 pt-3">{children}</div>}
    </div>
  );
}

const SEV_HINTS = {
  critical: 'Blocks binding until resolved — typically a missing verification, an unverifiable figure, or a hard compliance failure.',
  high: 'Materially affects the decision — resolve or explicitly waive before sign-off.',
  moderate: 'Worth reviewing but unlikely to change the outcome on its own.',
  low: 'Informational — noted for the file but does not require action.',
};

// Maps a finding to the page section where an underwriter would actually
// resolve it, instead of leaving the finding as an isolated line of text
// with no path to action. Section ids are anchored in InsuranceJobDetail.jsx
// (collapsed Technical Details sections) and further down this component.
const FINDING_RESOLVE_TARGETS = [
  { match: (f) => f.category === 'mib', id: 'section-mib-orders', label: 'Go to MIB Bureau Orders' },
  { match: (f) => f.category === 'sanctions', id: 'section-applicant-profile', label: 'Go to Applicant Profile' },
  { match: (f) => f.category === 'beneficiary_review', id: 'section-beneficiary-review', label: 'Go to Beneficiary Review' },
  { match: (f) => f.category === 'hallucination' || f.category === 'data_quality', id: 'section-documents', label: 'Go to source documents' },
];

function scrollToSection(id) {
  const el = document.getElementById(id);
  if (!el) return;
  // The target may be inside a collapsed <Collapsible> in a sibling
  // component — click its header to expand before scrolling into view.
  const toggle = el.querySelector('[data-collapsible-toggle]');
  if (toggle && el.getAttribute('data-collapsed') === 'true') toggle.click();
  el.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function FindingCard({ finding }) {
  const f = uwFinding(finding);
  const sev = safeLower(f?.severity, 'moderate');
  const resolveTarget = FINDING_RESOLVE_TARGETS.find((t) => t.match(finding || {}));
  return (
    <div className="flex items-start gap-2.5 rounded-lg border border-white/[0.04] bg-surface/40 p-3">
      <Hint text={SEV_HINTS[sev]}>
        <span className={`mt-0.5 inline-block shrink-0 cursor-help rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ring-1 ring-inset ${SEV_COLORS[sev] || SEV_COLORS.moderate}`}>
          {sev}
        </span>
      </Hint>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-slate-200">{displayText(f?.title, 'Finding')}</p>
        {f?.description && (
          <p className="mt-1 text-xs leading-relaxed text-slate-400">{displayText(f.description)}</p>
        )}
        {f?.field_path && (
          <Hint text="Underlying data field this finding traces back to — cross-reference against Provenance to see the source page.">
            <p className="hint-label mt-1 inline-block cursor-help font-mono text-[10px] text-slate-600">{f.field_path}</p>
          </Hint>
        )}
        {resolveTarget && (
          <button
            type="button"
            onClick={() => scrollToSection(resolveTarget.id)}
            className="mt-1.5 text-[11px] font-medium text-sky-400 hover:text-sky-300 hover:underline"
          >
            {resolveTarget.label} →
          </button>
        )}
      </div>
    </div>
  );
}

function SectionHeader({ icon: Icon, title, subtitle, accent = 'slate' }) {
  const accents = {
    slate: 'text-slate-400',
    rose: 'text-rose-400',
    sky: 'text-sky-400',
    amber: 'text-amber-400',
    emerald: 'text-emerald-400',
  };
  return (
    <div className="flex items-start gap-3">
      <div className={`mt-0.5 ${accents[accent] || accents.slate}`}>
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <h3 className="text-sm font-bold tracking-tight text-slate-100">{title}</h3>
        {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
      </div>
    </div>
  );
}

function InfoRow({ label, value }) {
  if (!value && value !== 0) return null;
  return (
    <div className="flex justify-between py-1.5 border-b border-white/[0.03] last:border-0">
      <span className="text-xs text-slate-500"><FieldLabel label={label} /></span>
      <span className="text-xs font-medium text-slate-200">{value}</span>
    </div>
  );
}

// ── Document transparency ─────────────────────────────────────────────────────

function DocumentPreviewModal({ doc, onClose }) {
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const bundleId = doc.bundleId;
    const docId = doc.id;
    if (!bundleId || !docId) {
      setLoading(false);
      setError('Full document preview is not available for this file.');
      return () => {};
    }
    endpoints
      .previewDraftDocument(bundleId, docId)
      .then((d) => { if (!cancelled) setPreview(d); })
      .catch((e) => { if (!cancelled) setError(e.message || 'Could not load preview.'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [doc]);

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-6" onClick={onClose}>
      <div
        className="max-h-[80vh] w-full max-w-2xl overflow-hidden rounded-2xl border border-white/[0.08] bg-surface-raised shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-slate-200">{doc.filename || 'Document'}</p>
            {doc.type && <p className="text-xs text-slate-500">{displayText(doc.type).replace(/_/g, ' ')}</p>}
          </div>
          <button type="button" onClick={onClose} className="rounded-lg px-2 py-1 text-xs text-slate-400 hover:bg-white/5 hover:text-white">Close</button>
        </div>
        <div className="max-h-[64vh] overflow-y-auto px-5 py-4">
          {loading && (
            <p className="flex items-center gap-2 text-sm text-slate-400"><Loader2 className="h-4 w-4 animate-spin" /> Loading preview…</p>
          )}
          {!loading && error && <p className="text-sm text-amber-300/90">{error}</p>}
          {!loading && !error && (
            <pre className="whitespace-pre-wrap break-words font-mono text-[11px] leading-relaxed text-slate-300">
              {typeof preview === 'string' ? preview : displayText(preview?.content || preview?.text || preview?.snippet, 'No readable content available — file is stored as binary (PDF/image).')}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}

function IngestedDocuments({ job }) {
  const results = job?.results || {};
  const docs = [
    ...(Array.isArray(job?.documents) ? job.documents : []),
    ...(Array.isArray(results.documents) ? results.documents : []),
  ].filter((d) => d && typeof d === 'object' && (d.filename || d.name || d.document_type || d.type));
  const list = [];
  const seen = new Set();
  for (const d of docs) {
    const key = `${d.document_id || d.submission_id || d.id || ''}|${d.filename || d.name || ''}`;
    if (seen.has(key)) continue;
    seen.add(key);
    list.push(d);
  }
  const [viewing, setViewing] = useState(null);

  if (!list.length) return null;

  const bundleId = results.bundle_id || job?.bundle_id;

  return (
    <div id="section-documents" className="rounded-xl border border-white/[0.06] bg-surface/60 p-5">
      <h2 className="text-base font-bold tracking-tight text-slate-100">Documents On File</h2>
      <p className="mb-3 mt-1 text-xs text-slate-500">
        {list.length} document{list.length > 1 ? 's' : ''} received and reviewed for this submission.
      </p>
      <ul className="divide-y divide-white/[0.04]">
        {list.map((d, i) => {
          const name = d.filename || d.name || `Document ${i + 1}`;
          const id = d.document_id || d.submission_id || d.id || '';
          return (
            <li key={`${id}-${i}`} className="flex items-center justify-between gap-3 py-2.5">
              <div className="flex min-w-0 items-center gap-2.5">
                <FileText className="h-4 w-4 shrink-0 text-slate-500" />
                <div className="min-w-0">
                  <p className="truncate text-sm text-slate-200">{name}</p>
                  {(d.document_type || d.type) && (
                    <p className="text-[11px] capitalize text-slate-500">{displayText(d.document_type || d.type).replace(/_/g, ' ')}</p>
                  )}
                </div>
              </div>
              <button
                type="button"
                onClick={() => setViewing({ ...d, id, bundleId })}
                className="btn-secondary btn-sm shrink-0 text-xs"
              >
                <Eye className="h-3.5 w-3.5" /> View
              </button>
            </li>
          );
        })}
      </ul>
      {viewing && <DocumentPreviewModal doc={viewing} onClose={() => setViewing(null)} />}
    </div>
  );
}

function cleanMemoText(text) {
  if (!text) return '';
  return uwMemoText(text).trim();
}

export default function MemoReportView({ job }) {
  const results = job?.results || {};
  const memoObj = results.memo && typeof results.memo === 'object' ? results.memo : {};
  const memoText = memoObj.summary || results.memo_text || '';
  const quote = results.quote_full || {};
  const worksheet = results.uw_worksheet || {};
  const namedInsured = results.named_insured || {};
  // Single normalized source for fields that also appear in the worksheet
  // below — top-of-page and worksheet must never disagree about the same case.
  const caseState = namedInsured.state_of_residence || (quote.metadata || {}).issue_state || results.primary_state || '';
  // When no real state was extracted, say so the same way the worksheet's
  // State Relativity row does ("filing default"), instead of a bare "—"
  // that reads as disagreeing with the worksheet lower on the page.
  const caseStateDisplay = caseState || ((quote.metadata || {}).state_of_filing
    ? `Not extracted (rating used ${(quote.metadata || {}).state_of_filing} filing default)`
    : '—');
  const caseCoverage = results.commercial_coverage_name || worksheet.coverage || (quote.metadata || {}).product || '';

  const decision = safeLower(results.ai_decision || results.outcome || memoObj.decision, 'refer');
  const insuredName = displayText(results.insured_name || memoObj.insured_name);

  const faceAmount = results.tiv || results.face_amount || memoObj.face_amount || (quote.indicated_terms || {}).limit || 0;
  const premium = (quote.indicated_terms || {}).premium || quote.adjusted_premium || worksheet.indicated_terms?.premium || 0;
  const basePremium = (quote.indicated_terms || {}).base_premium || worksheet.indicated_terms?.base_premium || 0;
  const uwClass = (quote.medical || {}).underwriting_class || worksheet.uw_class || '';
  const riskSeverity = safeLower(memoObj.overall_risk_severity, '');

  const buildup = worksheet.premium_buildup || [];
  const quoteComponents = (quote.metadata || {}).components || [];
  const premiumSteps = buildup.length > 0 ? buildup : quoteComponents;

  const allFindings = Array.isArray(memoObj.key_findings) ? memoObj.key_findings : [];
  // If the name came from a secondary document (not the application itself),
  // the backend raises a matching finding carrying the real confidence/source
  // — surface that as a badge next to the name instead of showing it as if
  // fully verified, and instead of the finding text being the only place
  // that says so.
  const insuredNameFinding = allFindings.find((f) => f?.category === 'data_quality' && (f?.title || '').startsWith('Insured name unverified'));
  const insuredNameBadge = insuredNameFinding
    ? `unverified — ${Math.round((insuredNameFinding.confidence ?? 0.5) * 100)}% confidence, from ${displayText(insuredNameFinding.source_document).replace('broker_', '').replace(/_/g, ' ') || 'a secondary document'}`
    : '';
  const sortedFindings = [...allFindings].sort((a, b) => {
    const sa = SEV_ORDER[safeLower(a?.severity, 'moderate')] ?? 2;
    const sb = SEV_ORDER[safeLower(b?.severity, 'moderate')] ?? 2;
    return sa - sb;
  });

  const counts = { critical: 0, high: 0, moderate: 0, low: 0 };
  allFindings.forEach((f) => {
    const s = safeLower(f?.severity, 'moderate');
    if (counts[s] != null) counts[s] += 1;
  });

  // Sourced from results.decision_thresholds (backend decision_thresholds.py) —
  // never hardcode these numbers, or the legend can drift from what the
  // decision engine actually uses.
  const thresholds = results.decision_thresholds || {};
  const referMinPct = thresholds.refer_min != null ? Math.round(thresholds.refer_min * 100) : null;
  const declineMinPct = thresholds.decline_min != null ? Math.round(thresholds.decline_min * 100) : null;
  const riskLegend = referMinPct != null && declineMinPct != null
    ? `0–${referMinPct - 1} accept range · ${referMinPct}–${declineMinPct - 1} refer · ${declineMinPct}+ decline`
    : '0 = lowest risk, 100 = highest risk';

  const riskPct = memoObj.overall_risk_score != null
    ? Math.round(Number(memoObj.overall_risk_score) * 100)
    : null;

  const conditions = memoObj.conditions || [];
  const recommendation = memoObj.recommendation || {};

  const memoLines = memoText.split('\n');
  const whatToDoIdx = memoLines.findIndex((l) => l.trim() === 'What to do next');
  const nextSteps = whatToDoIdx >= 0 ? uwMemoText(memoLines.slice(whatToDoIdx).join('\n')) : '';
  // Numbered "N. step text" lines as a clean array for list rendering, instead of a <pre> text block.
  const nextStepsList = nextSteps
    .split('\n')
    .map((l) => l.replace(/^\s*\d+\.\s*/, '').trim())
    .filter(Boolean)
    .filter((l) => l.toLowerCase() !== 'what to do next');

  // Rationale headline only (decision + one-liner) — the findings breakdown and next
  // steps it also contains are already shown, better-formatted, in their own sections
  // below ("Why This Decision" cards, "What To Do Next" list), so repeating the raw
  // text here would just be the same content twice.
  const rationaleWhyIdx = memoLines.findIndex((l) => l.trim() === 'Why this decision');
  const rationaleHeadline = uwMemoText(
    (rationaleWhyIdx >= 0 ? memoLines.slice(0, rationaleWhyIdx) : memoLines).join('\n'),
  ).trim();

  // Full Memo (below) must not just re-print the same findings/next-steps text
  // that's already rendered as structured cards/lists above — keep only the
  // headline + risk line + any line-specific notes (e.g. "Life class=..."),
  // dropping the "Why this decision" and "What to do next" sections.
  let memoAfterNextSteps = [];
  if (whatToDoIdx >= 0) {
    let i = whatToDoIdx + 1;
    while (i < memoLines.length && memoLines[i].trim() !== '') i += 1;
    memoAfterNextSteps = memoLines.slice(i + 1);
  }
  const memoRemainder = uwMemoText([...(rationaleWhyIdx >= 0 ? memoLines.slice(0, rationaleWhyIdx) : memoLines), ...memoAfterNextSteps].join('\n')).trim();

  // Human Review Required reasons are titles drawn from the same findings
  // already shown as full cards in "Why This Decision" above — don't repeat
  // the ones that are already there verbatim, only genuinely extra reasons.
  const findingTitles = new Set(sortedFindings.map((f) => (f?.title || '').trim().toLowerCase()));
  const extraReviewReasons = (memoObj.human_review_reasons || []).filter((r) => !findingTitles.has((r || '').trim().toLowerCase()));

  const medicalFindings = sortedFindings.filter((f) => categorizeFinding(f) === 'medical');
  const financialFindings = sortedFindings.filter((f) => categorizeFinding(f) === 'financial');
  const complianceFindings = sortedFindings.filter((f) => categorizeFinding(f) === 'compliance');
  const fraudFindings = sortedFindings.filter((f) => categorizeFinding(f) === 'fraud');
  const lossFindings = sortedFindings.filter((f) => categorizeFinding(f) === 'loss');
  const otherFindings = sortedFindings.filter((f) => {
    const c = categorizeFinding(f);
    return c !== 'medical' && c !== 'financial' && c !== 'compliance' && c !== 'fraud' && c !== 'loss';
  });

  const exposure = worksheet.exposure || {};
  const lossExp = worksheet.loss_experience || {};
  const indicatedTerms = worksheet.indicated_terms || {};

  return (
    <div className="space-y-5">
      {/* ── 1. Decision Hero ────────────────────────────────────────────── */}
      <div className={`rounded-2xl border p-5 ${DECISION_COLORS[decision] || DECISION_COLORS.refer}`}>
        <div className="flex items-start justify-between">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest opacity-70">Underwriting Decision</p>
            <p className="mt-1 text-3xl font-bold tracking-tight uppercase">{DECISION_LABELS[decision] || decision.replace('_', ' ')}</p>
            {insuredName && <p className="mt-1 text-base font-medium text-white">{insuredName}</p>}
          </div>
          <div className="text-right">
            {riskPct != null && (
              <div>
                <Hint text="Composite 0-100 score combining every finding's severity and confidence — higher means more reasons to slow down before binding." position="bottom">
                  <p className="hint-label inline-block cursor-help text-[10px] uppercase opacity-70">Risk Score</p>
                </Hint>
                <p className="text-3xl font-bold">{riskPct}<span className="text-sm font-normal opacity-60">/100</span></p>
                {riskSeverity && <p className="text-[10px] uppercase opacity-60">{riskSeverity} severity</p>}
                <p className="mt-1 text-[9px] uppercase tracking-wide opacity-50">{riskLegend}</p>
              </div>
            )}
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-6 border-t border-white/10 pt-4">
          <div>
            <Hint text="Death benefit (life) or Total Insured Value (P&C) being quoted." position="bottom">
              <p className="hint-label inline-block cursor-help text-[10px] uppercase opacity-70">Face Amount</p>
            </Hint>
            <p className="text-xl font-bold text-white">{fmtCurrency(faceAmount)}</p>
          </div>
          <div>
            <Hint text="AI-recommended premium before any underwriter override — see Premium Build-up below for how it was derived." position="bottom">
              <p className="hint-label inline-block cursor-help text-[10px] uppercase opacity-70">Indicated Premium</p>
            </Hint>
            <p className="text-xl font-bold text-white">{fmtCurrency(premium)}</p>
          </div>
          {uwClass && (
            <div>
              <Hint text="Underwriting class the case would be rated at if accepted as presented — drives the mortality/rate factor used in the premium build-up." position="bottom">
                <p className="hint-label inline-block cursor-help text-[10px] uppercase opacity-70">UW Class</p>
              </Hint>
              <p className="text-lg font-semibold capitalize">{uwClass.replace(/_/g, ' ')}</p>
            </div>
          )}
          {decision === 'refer' && (
            <div>
              <p className="text-[10px] uppercase opacity-70">Status</p>
              <p className="text-lg font-semibold">Underwriter review required</p>
            </div>
          )}
        </div>
      </div>

      {/* ── 2. Applicant Profile & Basic Details ────────────────────────── */}
      <div id="section-applicant-profile" className="rounded-2xl border border-white/[0.08] bg-surface/80 p-5">
        <SectionHeader icon={User} title="Applicant Profile & Basic Details" subtitle="Who are we insuring and what are they buying" accent="rose" />
        <div className="mt-4 grid gap-x-8 gap-y-0 sm:grid-cols-2">
          <div>
            <InfoRow
              label="Insured Name"
              value={
                insuredName
                  ? (insuredNameBadge ? <>{insuredName} <span className="text-amber-400">({insuredNameBadge})</span></> : insuredName)
                  : 'Name not extracted — see findings'
              }
            />
            <InfoRow label="Product" value={displayText(results.commercial_product_name || worksheet.product || results.insurance_line || '—').replace(/_/g, ' ')} />
            <InfoRow label="Coverage" value={displayText(caseCoverage || '—').replace(/_/g, ' ')} />
            <InfoRow label="Insurance Line" value={displayText(results.insurance_line || '—').replace(/_/g, ' ')} />
          </div>
          <div>
            <InfoRow label="Face Amount / TIV" value={fmtCurrency(faceAmount)} />
            <InfoRow label="Base Premium" value={fmtCurrency(basePremium)} />
            <InfoRow label="Indicated Premium" value={fmtCurrency(premium)} />
            <InfoRow label="Primary State" value={displayText(caseStateDisplay)} />
          </div>
        </div>
        {(results.broker_name || quote.policy_admin_reference || quote.quote_valid_until) && (
          <div className="mt-3 grid gap-x-8 gap-y-0 sm:grid-cols-2">
            <div>
              <InfoRow label="Broker" value={displayText(results.broker_name)} />
              {quote.policy_admin_reference && <InfoRow label="Policy Reference" value={quote.policy_admin_reference} />}
            </div>
            <div>
              {quote.quote_valid_until && <InfoRow label="Quote Valid Until" value={fmtTimestamp(quote.quote_valid_until)} />}
              {results.issue_state && <InfoRow label="Issue State" value={displayText(results.issue_state)} />}
            </div>
          </div>
        )}
      </div>

      {/* ── 3. Risk Evaluation & Medical Findings ───────────────────────── */}
      <div className="rounded-2xl border border-white/[0.08] bg-surface/80 p-5">
        <SectionHeader icon={Shield} title="Risk Evaluation & Medical Findings" subtitle="Biometric data, health summary, and medical history" accent="sky" />
        <div className="mt-4 space-y-3">
          {medicalFindings.length > 0 ? (
            medicalFindings.map((f, i) => <FindingCard key={f.finding_id || i} finding={f} />)
          ) : (
            <p className="text-xs text-slate-500 italic">No medical-specific findings identified. Refer to "Why This Decision" for all findings.</p>
          )}
        </div>
        {lossExp.known && (
          <div className="mt-4 rounded-lg border border-white/[0.04] bg-black/20 p-3">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Loss Experience</p>
            <div className="mt-2 flex gap-6">
              <div>
                <p className="text-xs text-slate-400"><FieldLabel label="Loss Ratio" /></p>
                <p className="text-sm font-semibold text-slate-200">{fmtPct(lossExp.loss_ratio * 100)}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400"><FieldLabel label="Basis" /></p>
                <p className="text-sm font-semibold text-slate-200">{lossExp.basis || '—'}</p>
              </div>
              {lossExp.experience_mod != null && (
                <div>
                  <p className="text-xs text-slate-400"><FieldLabel label="Experience Mod" /></p>
                  <p className="text-sm font-semibold text-slate-200">{fmtFactor(lossExp.experience_mod)}</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ── 4. Lifestyle, Financial & Behavioral Risk ───────────────────── */}
      {(financialFindings.length > 0 || complianceFindings.length > 0 || fraudFindings.length > 0) && (
        <div className="rounded-2xl border border-white/[0.08] bg-surface/80 p-5">
          <SectionHeader icon={AlertTriangle} title="Lifestyle, Financial & Behavioral Risk" subtitle="Financial underwriting, compliance, fraud detection, and moral hazard" accent="amber" />
          <div className="mt-4 space-y-4">
            {financialFindings.length > 0 && (
              <div>
                <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-amber-400/70">Financial Underwriting</p>
                <div className="space-y-2">
                  {financialFindings.map((f, i) => <FindingCard key={f.finding_id || i} finding={f} />)}
                </div>
              </div>
            )}
            {complianceFindings.length > 0 && (
              <div>
                <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-amber-400/70">Compliance & Regulatory</p>
                <div className="space-y-2">
                  {complianceFindings.map((f, i) => <FindingCard key={f.finding_id || i} finding={f} />)}
                </div>
              </div>
            )}
            {fraudFindings.length > 0 && (
              <div>
                <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-amber-400/70">Fraud & Moral Hazard</p>
                <div className="space-y-2">
                  {fraudFindings.map((f, i) => <FindingCard key={f.finding_id || i} finding={f} />)}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── 5. Why This Decision — all findings ─────────────────────────── */}
      {sortedFindings.length > 0 && (
        <div className="rounded-2xl border border-white/[0.08] bg-surface/80 p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-bold tracking-tight text-slate-100">Why This Decision</h2>
            <div className="flex gap-2">
              {Object.entries(counts).map(([sev, n]) => n > 0 && (
                <Hint key={sev} text={SEV_HINTS[sev]}>
                  <span className={`cursor-help rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ring-1 ring-inset ${SEV_COLORS[sev]}`}>
                    {n} {sev}
                  </span>
                </Hint>
              ))}
            </div>
          </div>
          <div className="max-h-[26rem] space-y-2 overflow-y-auto pr-1">
            {sortedFindings.map((f, i) => (
              <FindingCard key={f.finding_id || i} finding={f} />
            ))}
          </div>
        </div>
      )}

      {/* ── 6. Decision Justification ──────────────────────────────────── */}
      <div className="rounded-2xl border border-white/[0.08] bg-surface/80 p-5">
        <SectionHeader icon={ClipboardCheck} title="Decision Justification" subtitle="Why this risk classification was assigned" accent="emerald" />
        <div className="mt-4 space-y-3">
          <InfoRow label="Decision" value={DECISION_LABELS[decision] || decision.replace('_', ' ')} />
          {riskSeverity && <InfoRow label="Risk Severity" value={riskSeverity.toUpperCase()} />}
          {rationaleHeadline && (
            <div className="rounded-lg border border-white/[0.04] bg-black/20 p-3">
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Rationale</p>
              <p className="mt-1 text-xs leading-relaxed text-slate-300">{displayText(rationaleHeadline)}</p>
            </div>
          )}
          {recommendation.suggested_premium_modification && (
            <InfoRow label="Suggested Premium Adjustment" value={fmtPct(recommendation.suggested_premium_modification * 100)} />
          )}
          {memoObj.human_review_required && (
            <div className="rounded-lg border border-sky-500/20 bg-sky-500/5 p-3">
              <p className="text-[10px] font-bold uppercase tracking-wider text-sky-400">Human Review Required</p>
              {extraReviewReasons.length > 0 ? (
                <ul className="mt-1.5 space-y-1">
                  {uwReasons(extraReviewReasons).map((r, i) => (
                    <li key={i} className="flex gap-2 text-xs text-slate-300">
                      <span className="text-sky-400 shrink-0">•</span>{displayText(r)}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-1.5 text-xs text-slate-400">Driven by the findings above in "Why This Decision" — {memoObj.human_review_reasons?.length || 0} of them require licensed UW sign-off before bind.</p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── 7. Next Steps ──────────────────────────────────────────────── */}
      {nextStepsList.length > 0 && (
        <div className="rounded-xl border border-sky-500/20 bg-sky-500/5 p-4">
          <h4 className="mb-2 text-[10px] font-bold uppercase tracking-wider text-sky-400">What To Do Next</h4>
          <ol className="space-y-1.5">
            {nextStepsList.map((step, i) => (
              <li key={i} className="flex gap-2.5 text-[13px] leading-relaxed text-slate-300">
                <span className="shrink-0 font-semibold text-sky-400">{i + 1}.</span>
                <span>{displayText(step)}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* ── 8. Conditions ──────────────────────────────────────────────── */}
      {conditions.length > 0 && (
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
          <h4 className="mb-2 text-[10px] font-bold uppercase tracking-wider text-amber-400">Conditions</h4>
          <ul className="space-y-1.5">
            {conditions.map((c, i) => (
              <li key={i} className="flex gap-2 text-sm text-slate-300">
                <span className="text-amber-400 shrink-0">•</span>{displayText(c)}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── 9. Audit Trail & Sign-Off ──────────────────────────────────── */}
      <div className="rounded-2xl border border-white/[0.08] bg-surface/80 p-5">
        <SectionHeader icon={Clock} title="Audit Trail & Sign-Off" subtitle="Timestamps, agent traceability, and approval status" accent="slate" />
        <div className="mt-4 grid gap-x-8 gap-y-0 sm:grid-cols-2">
          <div>
            <InfoRow label="Submission ID" value={job?.id || '—'} />
            <InfoRow label="Bundle ID" value={displayText(results.bundle_id)} />
            <InfoRow label="Submitted" value={fmtTimestamp(job?.created_at)} />
            <InfoRow label="Completed" value={fmtTimestamp(job?.updated_at)} />
            {job?.created_at && job?.updated_at && (
              <InfoRow label="Processing Time" value={`${Math.round((new Date(job.updated_at) - new Date(job.created_at)) / 1000)}s`} />
            )}
          </div>
          <div>
            <InfoRow label="Memo Generated" value={fmtTimestamp(memoObj.generated_at)} />
            <InfoRow label="Underwriter of Record" value={displayText(results.assigned_to) || 'Unassigned'} />
            <InfoRow label="Approved By" value={displayText(memoObj.approved_by) || 'Pending'} />
            {memoObj.approved_at && <InfoRow label="Approved At" value={fmtTimestamp(memoObj.approved_at)} />}
            <InfoRow label="License #" value={displayText(memoObj.license_number) || '—'} />
          </div>
        </div>
        {memoObj.sign_off_notes && (
          <div className="mt-3 rounded-lg border border-white/[0.04] bg-black/20 p-3">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Sign-Off Notes</p>
            <p className="mt-1 text-xs leading-relaxed text-slate-300">{displayText(memoObj.sign_off_notes)}</p>
          </div>
        )}
      </div>

      {/* ── 10. Documents on file ──────────────────────────────────────── */}
      <IngestedDocuments job={job} />

      {/* ── 11. Full Memo ──────────────────────────────────────────────── */}
      {memoText ? (
        <Collapsible title="Full Memo" badge="text">
          <div className="rounded-lg border border-white/[0.04] bg-black/20 p-4">
            <pre className="whitespace-pre-wrap font-sans text-[13px] leading-relaxed text-slate-300">{memoRemainder || cleanMemoText(memoText)}</pre>
          </div>
        </Collapsible>
      ) : null}

      {/* ── 12. Premium Build-up ───────────────────────────────────────── */}
      {premiumSteps.length > 0 && (
        <Collapsible title="Premium Build-up" badge={`${premiumSteps.length} rating components`}>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[11px]">
              <thead>
                <tr className="border-b border-white/[0.06] text-slate-500">
                  <th className="py-1.5 pr-3 font-medium">
                    <Hint text="Individual rating factor applied when building this premium — e.g. mortality rate, underwriting class, state relativity.">
                      <span className="hint-label cursor-help">Rating component</span>
                    </Hint>
                  </th>
                  <th className="py-1.5 pr-3 font-medium">
                    <Hint text="What this factor is measured against — age/sex band, face amount, state, etc.">
                      <span className="hint-label cursor-help">Applied to</span>
                    </Hint>
                  </th>
                  <th className="py-1.5 pr-3 font-medium">
                    <Hint text="The multiplier or flat amount this component contributes to the rate.">
                      <span className="hint-label cursor-help">Factor</span>
                    </Hint>
                  </th>
                  <th className="py-1.5 font-medium">
                    <Hint text="How much this step moved the premium versus the running total. 0.0% means the factor is already baked into the rate above rather than layered on as a separate step.">
                      <span className="hint-label cursor-help">Adjustment</span>
                    </Hint>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.03]">
                {premiumSteps.map((row, i) => {
                  const modPct = row.modifier_pct;
                  const moved = modPct != null && Math.abs(modPct) >= 0.05;
                  return (
                  <tr key={row.step || row.name || i} className="text-slate-300">
                    <td className="py-1.5 pr-3">{premiumStepLabel(row.step || row.name)}</td>
                    <td className="py-1.5 pr-3 text-slate-500">{premiumBasisLabel(displayText(row.basis))}</td>
                    <td className="py-1.5 pr-3 font-mono">{fmtFactor(row.factor ?? row.amount)}</td>
                    <td className={`py-1.5 font-mono ${moved ? (modPct > 0 ? 'font-semibold text-amber-400' : 'font-semibold text-emerald-400') : ''}`}>{modPct != null ? fmtPct(modPct) : '—'}</td>
                  </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Collapsible>
      )}
    </div>
  );
}
