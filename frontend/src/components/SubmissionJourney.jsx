import { useEffect, useState } from 'react';
import {
  CheckCircle2, Circle, AlertTriangle, XCircle, MinusCircle,
  Shield, GitCompare, DollarSign, ClipboardCheck, Loader2,
  Users, FileText, BarChart3, Layers, Send, Truck, Building2,
  ChevronDown, ChevronRight, Clock,
} from 'lucide-react';
import { fmtCurrency, endpoints } from '../lib/api';
import { getJourneyContext } from '../lib/pipelineJourney';

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
        className="flex w-full items-center justify-between px-4 py-3 text-left"
      >
        <h4 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
          {Icon && <Icon className="h-3.5 w-3.5" />}
          {title}
        </h4>
        {open ? <ChevronDown className="h-4 w-4 text-slate-600" /> : <ChevronRight className="h-4 w-4 text-slate-600" />}
      </button>
      {open && <div className="border-t border-white/[0.04] px-4 pb-4 pt-3">{children}</div>}
    </section>
  );
}

function PipelineTimeline({ stages, processing, currentStage }) {
  return (
    <div className="relative">
      <div className="absolute left-[11px] top-3 bottom-3 w-px bg-white/[0.06]" />
      <div className="space-y-1">
        {stages.map((stage) => {
          const status = processing && currentStage === stage.id ? 'active' : stage.status;
          const { Icon, cls } = STATUS_ICON[status] || STATUS_ICON.pending;
          return (
            <div key={stage.id} className="relative flex gap-3 rounded-lg px-1 py-2">
              <div className={`relative z-10 mt-0.5 shrink-0 ${cls}`}>
                <Icon className="h-[22px] w-[22px]" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium text-slate-200">{stage.label}</p>
                  <div className="flex items-center gap-2">
                    {stage.duration && (
                      <span className="flex items-center gap-0.5 text-[10px] text-slate-600">
                        <Clock className="h-2.5 w-2.5" />{stage.duration}
                      </span>
                    )}
                    {stage.findings > 0 && stage.status !== 'skipped' && (
                      <span className="shrink-0 rounded-full bg-white/[0.06] px-2 py-0.5 text-[10px] text-slate-400">
                        {stage.findings}
                      </span>
                    )}
                  </div>
                </div>
                <p className="text-xs text-slate-500">{stage.detail}</p>
              </div>
            </div>
          );
        })}
      </div>
      {processing && (
        <p className="mt-2 pl-8 text-xs text-brand-light/80">Live — {currentStage ? `Running ${currentStage}` : 'pipeline in progress'}</p>
      )}
    </div>
  );
}

function SubmissionQuality({ quality, docQuality, onRequestDocs, requesting }) {
  return (
    <div className="rounded-xl bg-surface-overlay p-4 ring-1 ring-white/[0.04]">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Submission Quality</p>
          <p className="mt-1 text-sm text-slate-300">Completeness, appetite fit, and data trust</p>
        </div>
        <div className="text-right">
          <p className={`text-3xl font-bold ${quality.gradeColor}`}>{quality.grade}</p>
          <p className="text-xs text-slate-500">{quality.score}/100</p>
        </div>
      </div>
      {docQuality && (
        <div className="mt-3 border-t border-white/[0.04] pt-3">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400">Document completeness</span>
            <span className="text-slate-300">{(docQuality.completeness_pct * 100).toFixed(0)}%</span>
          </div>
          <div className="mt-2 h-1.5 rounded-full bg-black/30">
            <div className="h-1.5 rounded-full bg-brand" style={{ width: `${docQuality.completeness_pct * 100}%` }} />
          </div>
          {docQuality.missing_documents?.length > 0 && (
            <ul className="mt-2 space-y-1">
              {docQuality.missing_documents.map((d) => (
                <li key={d} className="text-xs text-red-400/90">Missing: {d}</li>
              ))}
            </ul>
          )}
          {docQuality.missing_documents?.length > 0 && onRequestDocs && (
            <button type="button" onClick={onRequestDocs} disabled={requesting} className="btn-secondary btn-sm mt-3 text-xs">
              <Send className="h-3 w-3" /> {requesting ? 'Sending…' : 'Request from broker'}
            </button>
          )}
        </div>
      )}
      {quality.issues.length > 0 && (
        <ul className="mt-3 space-y-1 border-t border-white/[0.04] pt-3">
          {quality.issues.map((issue) => (
            <li key={issue} className="flex items-start gap-2 text-xs text-slate-400">
              <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0 text-amber-500/80" />
              {issue}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function CopeDeepDive({ cope }) {
  if (!cope) return <p className="text-xs text-slate-500">COPE analysis loads after property data is parsed.</p>;
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {[
        ['Construction', cope.construction],
        ['Occupancy', cope.occupancy],
        ['Protection', cope.protection],
        ['Exposure', cope.exposure],
      ].map(([label, data]) => (
        <div key={label} className="rounded-lg bg-black/20 p-3">
          <p className="text-[10px] uppercase text-slate-500">{label}</p>
          <p className="mt-1 text-sm font-medium capitalize text-slate-200">
            {data?.class || data?.types?.join(', ') || data?.raw || '—'}
          </p>
          {data?.mod_pct != null && (
            <p className={`text-xs ${data.mod_pct > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
              {data.mod_pct > 0 ? '+' : ''}{data.mod_pct}% schedule mod
            </p>
          )}
        </div>
      ))}
      <div className="sm:col-span-2 rounded-lg bg-brand/10 px-3 py-2 text-xs text-slate-300">
        Grade: <strong className="uppercase">{cope.cope_score?.risk_grade || '—'}</strong>
        {' · '}Schedule mod: {cope.cope_score?.schedule_mod_pct > 0 ? '+' : ''}{cope.cope_score?.schedule_mod_pct ?? 0}%
        {' · '}Score: {cope.cope_score?.total_score?.toFixed(3) ?? '—'}
      </div>
    </div>
  );
}

function AgentFindingsPanel({ sections }) {
  if (!sections.length) return <p className="text-xs text-slate-500">No agent findings yet.</p>;
  return (
    <div className="space-y-3">
      {sections.map((section) => (
        <div key={section.key}>
          <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">{section.label}</p>
          <div className="space-y-1.5">
            {section.findings.slice(0, 3).map((f, i) => {
              const sev = (f.severity || 'moderate').toLowerCase();
              return (
                <div key={f.finding_id || i} className="rounded-lg bg-black/20 p-2.5 text-xs">
                  <div className="flex items-center gap-2">
                    <span className={`rounded px-1.5 py-0.5 text-[10px] uppercase ring-1 ring-inset ${SEV_CLS[sev] || SEV_CLS.moderate}`}>{sev}</span>
                    <span className="font-medium text-slate-300">{f.title}</span>
                  </div>
                  {f.description && <p className="mt-1 text-slate-500">{f.description}</p>}
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
  if (!provenance.totalFields) return <p className="text-xs text-slate-500">Provenance map available after parse.</p>;
  return (
    <div>
      <div className="mb-3 flex gap-4 text-xs text-slate-400">
        <span>{provenance.totalFields} fields tracked</span>
        <span className="text-emerald-400">{provenance.verifiedFields} verified</span>
        {provenance.contradictedFields > 0 && (
          <span className="text-red-400">{provenance.contradictedFields} contradicted</span>
        )}
      </div>
      <div className="space-y-1.5">
        {provenance.fields.map((f) => (
          <div key={f.field} className="grid grid-cols-4 gap-2 rounded-lg bg-black/20 p-2 text-[11px]">
            <span className="font-medium text-slate-300">{f.field}</span>
            <span className="truncate font-mono text-slate-400">{String(f.value ?? '—')}</span>
            <span className="truncate text-slate-500">{f.source}</span>
            <span className="capitalize text-slate-500">{f.trust}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function HumanCheckpoints({ checkpoints, bundleId, onResolve }) {
  if (!checkpoints.length) return <p className="text-xs text-emerald-400/90">No pending human checkpoints.</p>;
  return (
    <div className="space-y-2">
      {checkpoints.map((cp) => (
        <div key={cp.id} className="rounded-lg bg-amber-500/10 p-3 ring-1 ring-amber-500/20">
          <p className="text-sm font-medium text-amber-200">{cp.label}</p>
          <p className="mt-1 text-xs text-amber-200/70">{cp.reason}</p>
          {cp.status === 'pending' && onResolve && (
            <div className="mt-2 flex gap-2">
              <button type="button" onClick={() => onResolve(cp.id, 'approve')} className="btn-secondary btn-sm text-xs">Approve</button>
              <button type="button" onClick={() => onResolve(cp.id, 'reject')} className="btn-secondary btn-sm text-xs text-red-300">Reject</button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function AuditTrailInline({ audit }) {
  const entries = audit?.audit_trail?.entries || [];
  if (!entries.length) return <p className="text-xs text-slate-500">Audit trail populates as the pipeline runs.</p>;
  return (
    <div className="max-h-48 space-y-1 overflow-y-auto">
      {entries.slice(-8).reverse().map((e, i) => (
        <div key={e.entry_id || i} className="flex gap-2 rounded-lg bg-black/20 p-2 text-xs">
          <FileText className="mt-0.5 h-3 w-3 shrink-0 text-slate-500" />
          <div>
            <p className="font-medium text-slate-300">{e.event?.replace(/_/g, ' ')}</p>
            <p className="text-slate-500">{e.message}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

function EnterpriseOpsPanel({ ecosystem, onDispatchLC }) {
  if (!ecosystem) return null;
      const feeds = ecosystem.oracle_feeds?.feeds || ecosystem.oracle_feeds || [];
  return (
    <div className="space-y-3 text-xs">
      <div>
        <p className="mb-1 font-semibold uppercase tracking-wider text-slate-500">External data feeds</p>
        <div className="flex flex-wrap gap-2">
          {feeds.map((f) => (
            <span key={f.name} className={`rounded-full px-2 py-0.5 ring-1 ${f.mode === 'live' && f.reachable ? 'text-emerald-400 ring-emerald-500/30' : 'text-slate-400 ring-white/10'}`}>
              {f.name}: {f.mode}
            </span>
          ))}
        </div>
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        <div className="rounded-lg bg-black/20 p-2">
          <p className="text-[10px] uppercase text-slate-500">Claims ops</p>
          <p className="text-slate-300">{ecosystem.claims?.closed_claims ?? 0} closed · ${(ecosystem.claims?.total_incurred ?? 0).toLocaleString()} incurred</p>
        </div>
        <div className="rounded-lg bg-black/20 p-2">
          <p className="text-[10px] uppercase text-slate-500">Actuarial filing</p>
          <p className="text-slate-300">{ecosystem.actuarial?.filing_status?.replace(/_/g, ' ')}</p>
        </div>
        <div className="rounded-lg bg-black/20 p-2">
          <p className="text-[10px] uppercase text-slate-500">Agency / CRM</p>
          <p className="text-slate-300">{ecosystem.agency?.agency_name || 'Broker portal link'}</p>
        </div>
        <div className="rounded-lg bg-black/20 p-2">
          <p className="text-[10px] uppercase text-slate-500">Actuarial loop</p>
          <p className="text-slate-300">{ecosystem.actuarial_loop?.recommended_action}</p>
        </div>
      </div>
      {onDispatchLC && (
        <button type="button" onClick={onDispatchLC} className="btn-secondary btn-sm text-xs">
          <Truck className="h-3 w-3" /> Dispatch loss control inspection
        </button>
      )}
    </div>
  );
}

function VerificationCard({ verification }) {
  const hasData = verification.oracleCount != null || verification.copeGrade || verification.matchRate != null;
  if (!hasData) return <p className="text-xs text-slate-500">Verification checks run after document parse completes.</p>;
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <div><p className="text-[10px] uppercase text-slate-500">Oracles</p><p className="mt-1 text-sm font-semibold">{verification.oracleCount ?? 0}</p></div>
      <div><p className="text-[10px] uppercase text-slate-500">COPE</p><p className="mt-1 text-sm font-semibold capitalize">{verification.copeGrade?.replace(/_/g, ' ') || '—'}</p></div>
      <div><p className="text-[10px] uppercase text-slate-500">Reconciliation</p><p className="mt-1 text-sm font-semibold capitalize">{verification.reconStatus || '—'}</p></div>
      <div><p className="text-[10px] uppercase text-slate-500">Market</p><p className="mt-1 text-sm font-semibold capitalize">{verification.marketPhase?.replace(/_/g, ' ') || '—'}</p></div>
    </div>
  );
}

function ReconciliationPanel({ reconciliation }) {
  const { discrepancies, matchRate, matchedFields, totalFields, overallStatus } = reconciliation;
  if (!discrepancies.length && matchRate == null) {
    return <p className="text-xs text-slate-500">Reconciliation data not available.</p>;
  }
  return (
    <div>
      <div className="mb-2 flex gap-3 text-[10px] text-slate-500">
        {matchRate != null && <span>{Math.round(matchRate * 100)}% match</span>}
        {totalFields > 0 && <span>{matchedFields}/{totalFields} fields</span>}
        <span className="capitalize">{overallStatus}</span>
      </div>
      {discrepancies.length === 0 ? (
        <p className="text-xs text-emerald-400/90">No cross-document conflicts.</p>
      ) : (
        <div className="space-y-2">
          {discrepancies.slice(0, 6).map((d) => (
            <div key={`${d.field_path}-${d.source_a}`} className="rounded-lg bg-black/20 p-3">
              <p className="text-xs font-medium text-slate-300">{d.field_path}</p>
              <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                <div><p className="text-[10px] text-slate-500">{d.source_a || 'Source A'}</p><p className="font-mono">{String(d.structured_value ?? '—')}</p></div>
                <div><p className="text-[10px] text-slate-500">{d.source_b || 'Source B'}</p><p className="font-mono">{String(d.unstructured_value ?? '—')}</p></div>
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
    return <p className="text-xs text-slate-500">Premium calculated after risk scoring.</p>;
  }
  return (
    <div className="divide-y divide-white/[0.04] rounded-lg ring-1 ring-white/[0.04]">
      <div className="flex justify-between px-3 py-2 text-sm"><span className="text-slate-400">Base</span><span>{fmtCurrency(pricing.base)}</span></div>
      {pricing.premiumMods.map((mod) => (
        <div key={mod.key} className="flex justify-between px-3 py-1.5 text-xs">
          <span className="text-slate-500">{mod.label}</span>
          <span>{mod.pct > 0 ? '+' : ''}{mod.pct}%</span>
        </div>
      ))}
      <div className="flex justify-between bg-brand/5 px-3 py-2"><span className="font-medium">Indicated</span><span className="font-bold">{fmtCurrency(pricing.adjusted)}</span></div>
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
  const [checkpoints, setCheckpoints] = useState(ctx.checkpoints);

  useEffect(() => {
    setCheckpoints(ctx.checkpoints);
  }, [job]);

  useEffect(() => {
    if (!ctx.bundleId) return;
    let cancelled = false;
    const load = async () => {
      const tasks = [
        endpoints.copeAnalysis(ctx.bundleId).then((d) => { if (!cancelled) setCope(d); }).catch(() => {}),
        endpoints.missingDocuments(ctx.bundleId).then((d) => { if (!cancelled) setDocQuality(d); }).catch(() => {}),
        endpoints.auditTrail(ctx.bundleId).then((d) => { if (!cancelled) setAudit(d); }).catch(() => {}),
        endpoints.ecosystemBundle(ctx.bundleId).then((d) => { if (!cancelled) setEcosystem(d); }).catch(() => {}),
      ];
      await Promise.all(tasks);
    };
    load();
    return () => { cancelled = true; };
  }, [ctx.bundleId]);

  if (ctx.failed) return null;

  const handleRequestDocs = async () => {
    if (!ctx.bundleId || !docQuality?.missing_documents?.length) return;
    setRequesting(true);
    try {
      await endpoints.requestBrokerDocs(ctx.bundleId, docQuality.missing_documents);
      alert('Document request sent to broker');
    } catch (e) {
      alert(e.message);
    } finally {
      setRequesting(false);
    }
  };

  const handleResolveCheckpoint = async (checkpointId, action) => {
    try {
      await endpoints.resolveCheckpoint(ctx.bundleId, checkpointId, action);
      setCheckpoints((prev) => prev.map((c) => (c.id === checkpointId ? { ...c, status: action === 'approve' ? 'approved' : 'rejected' } : c)));
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

  return (
    <div className="space-y-4">
      <div>
        <p className="text-[10px] font-bold uppercase tracking-widest text-brand-light/80">Submission Journey</p>
        {ctx.insuredName && <p className="mt-0.5 text-sm text-slate-400">{ctx.insuredName}</p>}
      </div>

      <SubmissionQuality
        quality={ctx.quality}
        docQuality={docQuality}
        onRequestDocs={ctx.bundleId ? handleRequestDocs : null}
        requesting={requesting}
      />

      <Section title="Pipeline" icon={ClipboardCheck}>
        <PipelineTimeline stages={ctx.stages} processing={ctx.processing} currentStage={ctx.currentStage} />
      </Section>

      <Section title="Human Checkpoints" icon={Users} defaultOpen={checkpoints.length > 0}>
        <HumanCheckpoints checkpoints={checkpoints} bundleId={ctx.bundleId} onResolve={ctx.bundleId ? handleResolveCheckpoint : null} />
      </Section>

      {!ctx.processing && (
        <>
          <Section title="Verification & Oracles" icon={Shield}>
            <VerificationCard verification={ctx.verification} />
          </Section>

          <Section title="COPE Deep Dive" icon={BarChart3}>
            <CopeDeepDive cope={cope} />
          </Section>

          <Section title="Agent Findings" icon={Users}>
            <AgentFindingsPanel sections={ctx.agentSections} />
          </Section>

          <Section title="Provenance" icon={Layers}>
            <ProvenancePanel provenance={ctx.provenance} />
          </Section>

          <Section title="Reconciliation" icon={GitCompare}>
            <ReconciliationPanel reconciliation={ctx.reconciliation} />
          </Section>

          <Section title="Pricing" icon={DollarSign}>
            <PricingBreakdown pricing={ctx.pricing} />
          </Section>

          <Section title="Audit Trail" icon={FileText} defaultOpen={false}>
            <AuditTrailInline audit={audit} />
          </Section>

          <Section title="Enterprise Ecosystem" icon={Building2} defaultOpen={false}>
            <EnterpriseOpsPanel ecosystem={ecosystem} onDispatchLC={ctx.bundleId ? handleDispatchLC : null} />
          </Section>
        </>
      )}
    </div>
  );
}
