import { extractInsurance } from './api';

const MOD_LABELS = {
  iso_base_loss_cost: 'ISO base loss cost',
  loss_cost_multiplier: 'Loss cost multiplier',
  territory_relativity: 'Territory relativity',
  cope_schedule_rating: 'COPE schedule rating',
  market_cycle_adjustment: 'Market cycle',
  deductible_credit: 'Deductible credit',
  loss_experience: 'Loss experience',
  years_in_business: 'Years in business',
  uw_schedule_modification: 'UW schedule mod',
};

function humanModName(name) {
  if (!name) return 'Modifier';
  if (MOD_LABELS[name]) return MOD_LABELS[name];
  if (name.startsWith('territory_relativity_')) {
    return `Territory (${name.replace('territory_relativity_', '')})`;
  }
  return name.replace(/_/g, ' ');
}

function stageStatus(done, warn, fail, skipped) {
  if (skipped) return 'skipped';
  if (fail) return 'failed';
  if (warn) return 'warning';
  if (done) return 'complete';
  return 'pending';
}

function formatDuration(ms) {
  if (ms == null) return null;
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function normalizeBackendStage(stage) {
  return {
    id: stage.id,
    label: stage.label,
    detail: stage.detail || '',
    status: stage.status || 'complete',
    findings: stage.findings ?? 0,
    duration: formatDuration(stage.duration_ms),
  };
}

export function buildPipelineStages(job) {
  const backendStages = job?.progress?.pipeline_stages || job?.results?.pipeline_stages;
  if (backendStages?.length) {
    return backendStages.map(normalizeBackendStage);
  }

  const processing = job?.status === 'processing';
  const failed = job?.status === 'failed';
  const r = job?.results || {};
  const memo = r.memo || {};
  const recon = r.reconciliation || {};
  const discrepancies = recon.discrepancies || [];
  const criticalDisc = discrepancies.filter((d) => (d.severity || '').toLowerCase() === 'critical');
  const appetiteDecline = r.appetite_filter_passed === false && !r.appetite_needs_uw_referral;
  const agentFindings = (memo.key_findings || []).filter((f) => f.category !== 'external_oracle');

  const stages = [
    {
      id: 'intake',
      label: 'Intake',
      detail: r.document_count != null ? `${r.document_count} document(s)` : 'Documents received',
      status: processing ? 'active' : failed ? 'failed' : 'complete',
      findings: r.document_count ?? 0,
    },
    {
      id: 'triage',
      label: 'Triage',
      detail: r.triage_score != null
        ? `Score ${Number(r.triage_score).toFixed(0)} · ${r.triage_priority || 'normal'}`
        : 'Priority scoring',
      status: processing
        ? 'pending'
        : stageStatus(r.triage_score != null, r.triage_priority === 'low'),
      findings: 0,
    },
    {
      id: 'appetite',
      label: 'Appetite',
      detail: r.appetite_filter_passed === false
        ? (r.decline_reason || 'Outside appetite')
        : r.appetite_needs_uw_referral
          ? 'Referral required'
          : 'Within appetite',
      status: processing
        ? 'pending'
        : stageStatus(
            r.appetite_filter_passed !== false,
            r.appetite_needs_uw_referral,
            r.appetite_filter_passed === false,
          ),
      findings: r.appetite_filter_passed === false ? 1 : 0,
    },
    {
      id: 'parse',
      label: 'Parsed',
      detail: r.ocr_documents
        ? `${r.ocr_documents} OCR · structured extract`
        : 'Structured + unstructured parse',
      status: processing
        ? 'pending'
        : appetiteDecline
          ? 'skipped'
          : stageStatus((r.document_count || 0) > 0 || !!memo.insured_name),
      findings: r.ocr_documents || 0,
    },
    {
      id: 'verify',
      label: 'Verified',
      detail: `${r.oracle_findings_count ?? 0} oracle check(s)`,
      status: processing
        ? 'pending'
        : appetiteDecline
          ? 'skipped'
          : stageStatus(r.oracle_findings_count != null, (r.oracle_findings_count || 0) > 0),
      findings: r.oracle_findings_count || 0,
    },
    {
      id: 'reconcile',
      label: 'Reconciled',
      detail: recon.match_rate != null
        ? `${Math.round(recon.match_rate * 100)}% match · ${discrepancies.length} conflict(s)`
        : `${r.reconciliation_discrepancies ?? 0} conflict(s)`,
      status: processing
        ? 'pending'
        : appetiteDecline
          ? 'skipped'
          : stageStatus(
              recon.overall_status === 'reconciled' || discrepancies.length === 0,
              discrepancies.length > 0,
              criticalDisc.length > 0,
            ),
      findings: discrepancies.length,
    },
    {
      id: 'analyze',
      label: 'Scored',
      detail: memo.overall_risk_score != null
        ? `Risk ${Math.round(Number(memo.overall_risk_score) * 100)}/100`
        : `${agentFindings.length} agent finding(s)`,
      status: processing
        ? 'pending'
        : appetiteDecline
          ? 'skipped'
          : stageStatus(!!memo.decision || agentFindings.length >= 0, agentFindings.length > 3),
      findings: agentFindings.length,
    },
    {
      id: 'price',
      label: 'Priced',
      detail: r.quote?.adjusted_premium != null
        ? `Indicated ${formatCompact(r.quote.adjusted_premium)}`
        : 'Premium calculation',
      status: processing
        ? 'pending'
        : appetiteDecline
          ? 'skipped'
          : stageStatus(!!r.quote?.adjusted_premium || !!r.quote?.base_premium),
      findings: 0,
    },
    {
      id: 'decision',
      label: 'Decision',
      detail: (r.ai_decision || memo.decision || 'pending').toString().toUpperCase(),
      status: processing
        ? 'pending'
        : stageStatus(!!r.ai_decision || !!memo.decision, r.human_review_required, r.ai_decision === 'decline'),
      findings: (memo.human_review_reasons || []).length,
    },
  ];

  if (processing) {
    const current = job?.progress?.current_stage;
    if (current) {
      return stages.map((s) => ({
        ...s,
        duration: null,
        status: s.id === current ? 'active' : stages.findIndex((x) => x.id === s.id) < stages.findIndex((x) => x.id === current) ? 'complete' : 'pending',
      }));
    }
    stages[0].status = 'active';
  }

  return stages.map((s) => ({ ...s, duration: null }));
}

export function buildMiniStripStages(job) {
  const full = buildPipelineStages(job);
  const pick = ['parse', 'verify', 'reconcile', 'analyze', 'price', 'decision'];
  const byId = Object.fromEntries(full.map((s) => [s.id, s]));
  return pick.map((id) => byId[id] || { id, label: id, status: 'pending', detail: '', findings: 0, duration: null });
}

export function buildAgentFindings(job) {
  const memo = job?.results?.memo || {};
  const sections = [
    ['risk_analyst_findings', 'Risk Analyst'],
    ['loss_run_findings', 'Loss Run'],
    ['compliance_findings', 'Compliance'],
    ['fraud_findings', 'Fraud Detection'],
    ['key_findings', 'Key Findings'],
  ];
  return sections
    .map(([key, label]) => ({
      key,
      label,
      findings: (memo[key] || []).filter((f) => f.category !== 'external_oracle'),
    }))
    .filter((s) => s.findings.length > 0);
}

export function buildProvenanceView(job) {
  const r = job?.results || {};
  const prov = r.provenance || {};
  const summary = r.provenance_summary || {};
  const nodes = prov.nodes || {};
  const fields = Object.entries(nodes).slice(0, 8).map(([field, nodeList]) => {
    const node = (nodeList || [])[0] || {};
    const source = node.source || {};
    return {
      field,
      value: node.value,
      source: source.source_name || source.source_type || 'unknown',
      trust: source.trust_level || 'unverified',
      status: node.verification_status || 'unverified',
      confidence: node.confidence,
    };
  });
  return {
    totalFields: summary.total_fields ?? prov.record_count ?? Object.keys(nodes).length,
    verifiedFields: summary.verified_fields ?? 0,
    contradictedFields: summary.contradicted_fields ?? 0,
    fields,
  };
}

export function buildCheckpoints(job) {
  return job?.results?.human_checkpoints || [];
}

function formatCompact(n) {
  if (n == null || Number.isNaN(n)) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(n);
}

export function buildSubmissionQuality(job) {
  const r = job?.results || {};
  const recon = r.reconciliation || {};
  const discrepancies = recon.discrepancies || [];
  const criticalDisc = discrepancies.filter((d) => (d.severity || '').toLowerCase() === 'critical');
  const memo = r.memo || {};

  let score = 100;
  const issues = [];

  if (!r.document_count) {
    score -= 25;
    issues.push('No documents ingested');
  } else if (r.document_count < 2) {
    score -= 10;
    issues.push('Thin submission — only one document');
  }

  if (r.appetite_filter_passed === false) {
    score -= 35;
    issues.push('Outside appetite');
  } else if (r.appetite_needs_uw_referral) {
    score -= 10;
    issues.push('Appetite referral required');
  }

  if (recon.match_rate != null && recon.match_rate < 0.8) {
    score -= Math.round((0.8 - recon.match_rate) * 40);
    issues.push(`Low field match rate (${Math.round(recon.match_rate * 100)}%)`);
  }

  if (criticalDisc.length) {
    score -= criticalDisc.length * 12;
    issues.push(`${criticalDisc.length} critical reconciliation conflict(s)`);
  } else if (discrepancies.length) {
    score -= Math.min(discrepancies.length * 4, 16);
    issues.push(`${discrepancies.length} field conflict(s) to review`);
  }

  if (r.triage_score != null && r.triage_score < 45) {
    score -= 8;
    issues.push('Low triage priority');
  }

  if (memo.human_review_required) {
    score -= 6;
    issues.push('Human review required');
  }

  score = Math.max(0, Math.min(100, Math.round(score)));

  let grade = 'A';
  let gradeColor = 'text-emerald-400';
  if (score < 90) { grade = 'B'; gradeColor = 'text-sky-400'; }
  if (score < 75) { grade = 'C'; gradeColor = 'text-amber-400'; }
  if (score < 60) { grade = 'D'; gradeColor = 'text-orange-400'; }
  if (score < 45) { grade = 'F'; gradeColor = 'text-red-400'; }

  return { score, grade, gradeColor, issues };
}

export function buildVerificationSummary(job) {
  const r = job?.results || {};
  const memo = r.memo || {};
  const quoteFull = r.quote_full || {};
  const meta = quoteFull.metadata || {};
  const oracleFindings = (memo.key_findings || []).filter((f) => f.category === 'external_oracle');

  return {
    oracleCount: r.oracle_findings_count ?? oracleFindings.length,
    oracleFindings: oracleFindings.slice(0, 4),
    copeGrade: meta.cope_grade || null,
    copeModPct: meta.cope_mod_pct ?? null,
    copeScore: meta.cope_score ?? null,
    marketPhase: meta.market_phase || null,
    marketModPct: meta.market_mod_pct ?? null,
    matchRate: r.reconciliation?.match_rate ?? null,
    reconStatus: r.reconciliation?.overall_status || null,
  };
}

export function buildPricingBreakdown(job) {
  const r = job?.results || {};
  const quote = r.quote || {};
  const quoteFull = r.quote_full || {};
  const meta = quoteFull.metadata || {};
  const base = quote.base_premium ?? quoteFull.base_premium ?? null;
  const adjusted = quote.adjusted_premium ?? quoteFull.adjusted_premium ?? null;
  const mods = quoteFull.schedule_modifications || [];

  const premiumMods = mods
    .filter((m) => m.modifier_pct !== 0 || ['cope_schedule_rating', 'market_cycle_adjustment', 'loss_experience'].includes(m.name))
    .map((m) => ({
      key: m.name,
      label: humanModName(m.name),
      pct: m.modifier_pct ?? 0,
      basis: m.basis || '',
    }));

  if (meta.deductible_credit) {
    const exists = premiumMods.some((m) => m.key === 'deductible_credit');
    if (!exists) {
      premiumMods.push({
        key: 'deductible_credit',
        label: 'Deductible credit',
        pct: meta.deductible_credit,
        basis: 'deductible',
      });
    }
  }

  if (meta.years_in_business_mod_pct) {
    const exists = premiumMods.some((m) => m.key === 'years_in_business');
    if (!exists) {
      premiumMods.push({
        key: 'years_in_business',
        label: 'Years in business',
        pct: meta.years_in_business_mod_pct,
        basis: 'tenure',
      });
    }
  }

  return { base, adjusted, premiumMods, ratePer100: quoteFull.rate_per_100_tiv ?? null };
}

export function buildReconciliationView(job) {
  const recon = job?.results?.reconciliation || {};
  return {
    matchRate: recon.match_rate ?? null,
    matchedFields: recon.matched_fields ?? 0,
    totalFields: recon.total_fields ?? 0,
    overallStatus: recon.overall_status || 'pending',
    discrepancies: recon.discrepancies || [],
  };
}

export function getJourneyContext(job) {
  const s = extractInsurance(job);
  return {
    stages: buildPipelineStages(job),
    miniStages: buildMiniStripStages(job),
    quality: buildSubmissionQuality(job),
    verification: buildVerificationSummary(job),
    pricing: buildPricingBreakdown(job),
    reconciliation: buildReconciliationView(job),
    agentSections: buildAgentFindings(job),
    provenance: buildProvenanceView(job),
    checkpoints: buildCheckpoints(job),
    bundleId: s.bundleId,
    insuredName: s.insuredName,
    processing: job?.status === 'processing',
    failed: job?.status === 'failed',
    currentStage: job?.progress?.current_stage || null,
  };
}
