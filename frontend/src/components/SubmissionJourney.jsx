import { useEffect, useState } from 'react';
import {
  CheckCircle2, Circle, AlertTriangle, XCircle, MinusCircle,
  Shield, GitCompare, DollarSign, ClipboardCheck, Loader2,
  Users, FileText, BarChart3, Layers, Send, Truck, Building2,
  ChevronDown, ChevronRight,
} from 'lucide-react';
import { fmtCurrency, endpoints } from '../lib/api';
import { getJourneyContext } from '../lib/pipelineJourney';
import { insuranceLineLabel } from '../lib/insuranceLines';
import SimilarPriors from './SimilarPriors';
import { asList, displayText, fmtFixed, safeLower } from '../lib/safe';

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

function PipelineTimeline({ stages, processing, currentStage, expandedStage, onToggleStage }) {
  const list = asList(stages);
  return (
    <div className="space-y-2">
      <div className="overflow-x-auto">
        <div className="flex items-stretch gap-1.5 min-w-max">
          {list.map((stage, i) => {
            const status = processing && currentStage === stage.id ? 'active' : stage.status;
            const { Icon, cls } = STATUS_ICON[status] || STATUS_ICON.pending;
            const activeCls = status === 'active' || status === 'complete' ? 'border-brand/20 bg-brand/5' : status === 'failed' ? 'border-red-500/20 bg-red-500/5' : 'border-white/[0.04] bg-surface/30';
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
        return (
          <div className="rounded-lg border border-brand/20 bg-brand/5 p-4 mt-1">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-semibold text-slate-200">{displayText(stage.label)}</h4>
              <button type="button" onClick={() => onToggleStage(null)} className="text-xs text-slate-500 hover:text-slate-300">Close</button>
            </div>
            <p className="text-sm text-slate-400">{displayText(stage.detail, 'No additional details')}</p>
            {stage.findings > 0 && (
              <p className="mt-1 text-xs text-slate-500">{stage.findings} finding{stage.findings > 1 ? 's' : ''} identified</p>
            )}
            {stage.duration && (
              <p className="mt-1 text-xs text-slate-500">Completed in {stage.duration}</p>
            )}
          </div>
        );
      })()}
      {processing && (
        <p className="pipeline-live mt-2 text-sm font-semibold text-brand-light">Live — {currentStage ? `Running ${currentStage}` : 'pipeline in progress'}</p>
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

function groupStagesByPhase(stages = []) {
  return PHASE_DEFS.map((phase) => ({
    label: phase.label,
    stages: asList(stages).filter((s) => phase.ids.includes(s.id)),
  })).filter((phase) => phase.stages.length > 0);
}

function PhaseStrip({ phases, processing, currentStage, expandedStage, onToggleStage }) {
  return (
    <div className="space-y-3">
      {phases.map((phase) => (
        <div key={phase.label}>
          <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">{phase.label}</p>
          <PipelineTimeline stages={phase.stages} processing={processing} currentStage={currentStage} expandedStage={expandedStage} onToggleStage={onToggleStage} />
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

function AgentFindingsPanel({ sections }) {
  const list = asList(sections);
  if (!list.length) return <p className="text-sm text-slate-400">No agent findings yet.</p>;
  return (
    <div className="space-y-3">
      {list.map((section) => (
        <div key={section.key}>
          <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-slate-400">{section.label}</p>
          <div className="space-y-1.5">
            {asList(section.findings).slice(0, 3).map((f, i) => {
              const sev = safeLower(f?.severity, 'moderate');
              return (
                <div key={f.finding_id || i} className="rounded-lg bg-black/20 p-2.5 text-sm">
                  <div className="flex items-center gap-2">
                    <span className={`rounded px-1.5 py-0.5 text-[11px] uppercase ring-1 ring-inset ${SEV_CLS[sev] || SEV_CLS.moderate}`}>{sev}</span>
                    <span className="font-medium text-slate-300">{displayText(f.title)}</span>
                  </div>
                  {f.description && <p className="mt-1 text-slate-500">{displayText(f.description)}</p>}
                </div>
              );
            })}
          </div>
        </div>
      ))}
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
          <div key={f.field} className="grid grid-cols-4 gap-2 rounded-lg bg-black/20 p-2 text-sm">
            <span className="font-medium text-slate-300">{displayText(f.field)}</span>
            <span className="truncate font-mono text-slate-400">{displayText(f.value, '—')}</span>
            <span className="truncate text-slate-500">{displayText(f.source)}</span>
            <span className="capitalize text-slate-500">{displayText(f.trust)}</span>
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
        <PhaseStrip phases={groupStagesByPhase(ctx.stages)} processing={ctx.processing} currentStage={ctx.currentStage} expandedStage={expandedStage} onToggleStage={(id) => setExpandedStage((prev) => prev === id ? null : id)} />
      </Section>

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
