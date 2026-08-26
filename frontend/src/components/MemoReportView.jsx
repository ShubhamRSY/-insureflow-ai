import { useEffect, useState } from 'react';
import { ChevronDown, ChevronRight, Eye, FileText, Loader2, User, Shield, AlertTriangle, ClipboardCheck, Clock, CheckCircle2 } from 'lucide-react';
import { displayText, safeLower } from '../lib/safe';
import { endpoints } from '../lib/api';
import { uwFinding, uwMemoText, premiumStepLabel } from '../lib/uwLanguage';

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
  decline: 'border-red-800 bg-red-950/60 text-red-200',
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

export function Collapsible({ title, defaultOpen = false, children, badge }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-xl border border-white/[0.06] bg-surface/60">
      <button
        type="button"
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

function FindingCard({ finding }) {
  const f = uwFinding(finding);
  const sev = safeLower(f?.severity, 'moderate');
  return (
    <div className="flex items-start gap-2.5 rounded-lg border border-white/[0.04] bg-surface/40 p-3">
      <span className={`mt-0.5 shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ring-1 ring-inset ${SEV_COLORS[sev] || SEV_COLORS.moderate}`}>
        {sev}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-slate-200">{displayText(f?.title, 'Finding')}</p>
        {f?.description && (
          <p className="mt-1 text-xs leading-relaxed text-slate-400">{displayText(f.description)}</p>
        )}
        {f?.field_path && (
          <p className="mt-1 font-mono text-[10px] text-slate-600">{f.field_path}</p>
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
      <span className="text-xs text-slate-500">{label}</span>
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
    <div className="rounded-xl border border-white/[0.06] bg-surface/60 p-5">
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

  const riskPct = memoObj.overall_risk_score != null
    ? Math.round(Number(memoObj.overall_risk_score) * 100)
    : null;

  const conditions = memoObj.conditions || [];
  const recommendation = memoObj.recommendation || {};
  const agentResults = memoObj.agent_results || {};

  const memoLines = memoText.split('\n');
  const whatToDoIdx = memoLines.findIndex((l) => l.trim() === 'What to do next');
  const nextSteps = whatToDoIdx >= 0 ? uwMemoText(memoLines.slice(whatToDoIdx).join('\n')) : '';

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
      <div className={`rounded-2xl border-2 p-5 ${DECISION_COLORS[decision] || DECISION_COLORS.refer}`}>
        <div className="flex items-start justify-between">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest opacity-70">Underwriting Decision</p>
            <p className="mt-1 text-3xl font-bold tracking-tight uppercase">{DECISION_LABELS[decision] || decision.replace('_', ' ')}</p>
            {insuredName && <p className="mt-1 text-base font-medium text-white">{insuredName}</p>}
          </div>
          <div className="text-right">
            {riskPct != null && (
              <div>
                <p className="text-[10px] uppercase opacity-70">Risk Score</p>
                <p className="text-3xl font-bold">{riskPct}<span className="text-sm font-normal opacity-60">/100</span></p>
                {riskSeverity && <p className="text-[10px] uppercase opacity-60">{riskSeverity} severity</p>}
              </div>
            )}
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-6 border-t border-white/10 pt-4">
          <div>
            <p className="text-[10px] uppercase opacity-70">Face Amount</p>
            <p className="text-xl font-bold text-white">{fmtCurrency(faceAmount)}</p>
          </div>
          <div>
            <p className="text-[10px] uppercase opacity-70">Indicated Premium</p>
            <p className="text-xl font-bold text-white">{fmtCurrency(premium)}</p>
          </div>
          {uwClass && (
            <div>
              <p className="text-[10px] uppercase opacity-70">UW Class</p>
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
      <div className="rounded-2xl border border-white/[0.08] bg-surface/80 p-5">
        <SectionHeader icon={User} title="Applicant Profile & Basic Details" subtitle="Who are we insuring and what are they buying" accent="rose" />
        <div className="mt-4 grid gap-x-8 gap-y-0 sm:grid-cols-2">
          <div>
            <InfoRow label="Insured Name" value={insuredName || '—'} />
            <InfoRow label="Product" value={displayText(results.commercial_product_name || worksheet.product || results.insurance_line || '—').replace(/_/g, ' ')} />
            <InfoRow label="Coverage" value={displayText(results.commercial_coverage_name || worksheet.coverage || '—').replace(/_/g, ' ')} />
            <InfoRow label="Insurance Line" value={displayText(results.insurance_line || '—').replace(/_/g, ' ')} />
          </div>
          <div>
            <InfoRow label="Face Amount / TIV" value={fmtCurrency(faceAmount)} />
            <InfoRow label="Base Premium" value={fmtCurrency(basePremium)} />
            <InfoRow label="Indicated Premium" value={fmtCurrency(premium)} />
            <InfoRow label="Primary State" value={displayText(results.primary_state || '—')} />
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
                <p className="text-xs text-slate-400">Loss Ratio</p>
                <p className="text-sm font-semibold text-slate-200">{fmtPct(lossExp.loss_ratio * 100)}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Basis</p>
                <p className="text-sm font-semibold text-slate-200">{lossExp.basis || '—'}</p>
              </div>
              {lossExp.experience_mod != null && (
                <div>
                  <p className="text-xs text-slate-400">Experience Mod</p>
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
                <span key={sev} className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ring-1 ring-inset ${SEV_COLORS[sev]}`}>
                  {n} {sev}
                </span>
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
          {recommendation.rationale && (
            <div className="rounded-lg border border-white/[0.04] bg-black/20 p-3">
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Rationale</p>
              <p className="mt-1 text-xs leading-relaxed text-slate-300">{displayText(recommendation.rationale)}</p>
            </div>
          )}
          {recommendation.suggested_premium_modification && (
            <InfoRow label="Suggested Premium Adjustment" value={fmtPct(recommendation.suggested_premium_modification * 100)} />
          )}
          {memoObj.human_review_required && (
            <div className="rounded-lg border border-sky-500/20 bg-sky-500/5 p-3">
              <p className="text-[10px] font-bold uppercase tracking-wider text-sky-400">Human Review Required</p>
              {memoObj.human_review_reasons?.length > 0 && (
                <ul className="mt-1.5 space-y-1">
                  {memoObj.human_review_reasons.map((r, i) => (
                    <li key={i} className="flex gap-2 text-xs text-slate-300">
                      <span className="text-sky-400 shrink-0">•</span>{displayText(r)}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── 7. Next Steps ──────────────────────────────────────────────── */}
      {nextSteps && (
        <div className="rounded-xl border border-sky-500/20 bg-sky-500/5 p-4">
          <h4 className="mb-2 text-[10px] font-bold uppercase tracking-wider text-sky-400">What To Do Next</h4>
          <pre className="whitespace-pre-wrap font-sans text-[13px] leading-relaxed text-slate-300">{nextSteps}</pre>
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
        {Object.keys(agentResults).length > 0 && (
          <div className="mt-4">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-2">Agent Execution Trace</p>
            <div className="space-y-1.5">
              {Object.entries(agentResults).map(([name, result]) => (
                <div key={name} className="flex items-center gap-2 text-xs">
                  <CheckCircle2 className="h-3 w-3 text-emerald-500/60 shrink-0" />
                  <span className="font-medium text-slate-300">{name}</span>
                  {result?.status && (
                    <span className={`rounded-full px-1.5 py-0.5 text-[9px] font-bold uppercase ${
                      result.status === 'completed' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-slate-500/10 text-slate-400'
                    }`}>
                      {result.status}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── 10. Documents on file ──────────────────────────────────────── */}
      <IngestedDocuments job={job} />

      {/* ── 11. Full Memo ──────────────────────────────────────────────── */}
      {memoText ? (
        <Collapsible title="Full Memo" badge="text">
          <div className="rounded-lg border border-white/[0.04] bg-black/20 p-4">
            <pre className="whitespace-pre-wrap font-sans text-[13px] leading-relaxed text-slate-300">{cleanMemoText(memoText)}</pre>
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
                  <th className="py-1.5 pr-3 font-medium">Rating component</th>
                  <th className="py-1.5 pr-3 font-medium">Applied to</th>
                  <th className="py-1.5 pr-3 font-medium">Factor</th>
                  <th className="py-1.5 font-medium">Adjustment</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.03]">
                {premiumSteps.map((row, i) => (
                  <tr key={row.step || row.name || i} className="text-slate-300">
                    <td className="py-1.5 pr-3">{premiumStepLabel(row.step || row.name)}</td>
                    <td className="py-1.5 pr-3 text-slate-500">{premiumBasisLabel(displayText(row.basis))}</td>
                    <td className="py-1.5 pr-3 font-mono">{fmtFactor(row.factor || row.amount)}</td>
                    <td className="py-1.5 font-mono">{row.modifier_pct != null ? fmtPct(row.modifier_pct) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Collapsible>
      )}
    </div>
  );
}
