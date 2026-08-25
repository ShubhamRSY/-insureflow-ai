import { extractInsurance } from './api';
import { asList, displayText, safeLower } from './safe';

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

function isLifeStage(r) {
  return safeLower(r?.insurance_line || r?.product_line) === 'life';
}

function riskBand(score) {
  const s = Number(score) * 100;
  if (s >= 80) return 'high';
  if (s >= 50) return 'moderate';
  return 'low';
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
  const processing = job?.status === 'processing';
  const failed = job?.status === 'failed';

  // Build the full expected stage list for the current job so every phase is
  // always visible, even during early processing when the backend has only
  // emitted a few stages so far.
  const fullExpected = buildExpectedStageList(job);

  if (backendStages?.length) {
    const byId = Object.fromEntries(backendStages.map((s) => [s.id, normalizeBackendStage(s)]));
    // Merge: use backend data where available, fill the rest from expected
    const merged = fullExpected.map((exp) => byId[exp.id] || exp);
    if (!processing) return merged;
    // During processing, apply current_stage overrides
    return applyProcessingOverrides(merged, job?.progress?.current_stage);
  }

  if (processing) {
    return applyProcessingOverrides(fullExpected, job?.progress?.current_stage);
  }

  // Post-processing fallback: derive status from results
  const r = job?.results || {};
  const memo = r.memo || {};
  const recon = r.reconciliation || {};
  const discrepancies = asList(recon.discrepancies);
  const criticalDisc = discrepancies.filter((d) => safeLower(d?.severity) === 'critical');
  const appetiteDecline = r.appetite_filter_passed === false && !r.appetite_needs_uw_referral;
  const agentFindings = asList(memo.key_findings).filter((f) => f.category !== 'external_oracle');

  return fullExpected.map((s) => {
    switch (s.id) {
      case 'intake':
        return { ...s, detail: r.document_count != null ? `${r.document_count} document(s)` : 'Documents received', status: failed ? 'failed' : 'complete', findings: r.document_count ?? 0 };
      case 'triage':
        return { ...s, detail: r.triage_score != null ? `Score ${Number(r.triage_score).toFixed(0)} · ${r.triage_priority || 'normal'}` : 'Priority scoring', status: stageStatus(r.triage_score != null, r.triage_priority === 'low') };
      case 'appetite':
        return { ...s, detail: r.appetite_needs_uw_referral ? 'Referral required' : r.appetite_filter_passed === false ? (r.decline_reason || 'Outside appetite') : 'Within appetite', status: stageStatus(r.appetite_filter_passed !== false, r.appetite_needs_uw_referral, r.appetite_filter_passed === false), findings: r.appetite_filter_passed === false ? 1 : 0 };
      case 'parse':
        return { ...s, detail: (r.document_count || r.ocr_documents) ? `${r.document_count ?? r.ocr_documents} document(s) read` : 'Documents read & structured', status: appetiteDecline ? 'skipped' : stageStatus((r.document_count || 0) > 0 || !!memo.insured_name), findings: r.document_count ?? r.ocr_documents ?? 0 };
      case 'verify':
        return { ...s, detail: isLifeStage(r) ? 'Medical & bureau checks run' : (r.oracle_findings_count ?? 0) > 0 ? `${r.oracle_findings_count} external record(s) checked` : 'External records checked', status: appetiteDecline ? 'skipped' : stageStatus(r.oracle_findings_count != null, (r.oracle_findings_count || 0) > 0), findings: r.oracle_findings_count || 0 };
      case 'reconcile':
        return { ...s, detail: recon.match_rate != null ? `${Math.round(recon.match_rate * 100)}% match · ${discrepancies.length} conflict(s)` : `${r.reconciliation_discrepancies ?? 0} conflict(s)`, status: appetiteDecline ? 'skipped' : stageStatus(recon.overall_status === 'reconciled' || discrepancies.length === 0, discrepancies.length > 0, criticalDisc.length > 0), findings: discrepancies.length };
      case 'analyze':
        return { ...s, detail: memo.overall_risk_score != null ? `Overall risk: ${riskBand(memo.overall_risk_score)}` : `${agentFindings.length} underwriting item(s) noted`, status: appetiteDecline ? 'skipped' : stageStatus(!!memo.decision || agentFindings.length >= 0, agentFindings.length > 3), findings: agentFindings.length };
      case 'price':
        return { ...s, detail: r.quote?.adjusted_premium != null ? `Indicated ${formatCompact(r.quote.adjusted_premium)}` : 'Premium calculation', status: appetiteDecline ? 'skipped' : stageStatus(!!r.quote?.adjusted_premium || !!r.quote?.base_premium) };
      case 'decision':
        return { ...s, detail: (r.ai_decision || memo.decision || 'pending').toString().toUpperCase(), status: stageStatus(!!r.ai_decision || !!memo.decision, r.human_review_required, r.ai_decision === 'decline'), findings: (memo.human_review_reasons || []).length };
      default:
        return s;
    }
  });
}

/** Build the full expected stage list with default pending status. */
function buildExpectedStageList(job) {
  const r = job?.results || {};
  const memo = r.memo || {};
  return [
    { id: 'intake', label: 'Intake', detail: 'Receiving submission package', status: 'pending', findings: 0, duration: null },
    { id: 'triage', label: 'Triage', detail: 'Priority scoring', status: 'pending', findings: 0, duration: null },
    { id: 'appetite', label: 'Appetite', detail: 'Checking carrier appetite', status: 'pending', findings: 0, duration: null },
    { id: 'parse', label: 'Parsed', detail: 'Ingesting and parsing documents', status: 'pending', findings: 0, duration: null },
    { id: 'verify', label: 'Verified', detail: 'Running external oracle checks', status: 'pending', findings: 0, duration: null },
    { id: 'reconcile', label: 'Reconciled', detail: 'Reconciling cross-document fields', status: 'pending', findings: 0, duration: null },
    { id: 'analyze', label: 'Scored', detail: 'Running specialist agent analysis', status: 'pending', findings: 0, duration: null },
    { id: 'price', label: 'Priced', detail: 'Calculating indicated premium', status: 'pending', findings: 0, duration: null },
    { id: 'decision', label: 'Decision', detail: 'Final underwriting decision', status: 'pending', findings: 0, duration: null },
  ];
}

/** Mark stages as complete/active/pending based on current_stage during processing. */
function applyProcessingOverrides(stages, currentStage) {
  if (!currentStage) {
    // No current_stage yet — mark intake as active, rest pending
    return stages.map((s, i) => ({ ...s, status: i === 0 ? 'active' : 'pending', duration: null }));
  }
  const currentIdx = stages.findIndex((s) => s.id === currentStage);
  return stages.map((s, i) => ({
    ...s,
    duration: null,
    status: i < currentIdx ? 'complete' : i === currentIdx ? 'active' : 'pending',
  }));
}

export function buildMiniStripStages(job) {
  const full = buildPipelineStages(job);
  const pick = ['parse', 'verify', 'reconcile', 'analyze', 'price', 'decision'];
  const byId = Object.fromEntries(full.map((s) => [s.id, s]));
  return pick.map((id) => byId[id] || { id, label: id, status: 'pending', detail: '', findings: 0, duration: null });
}

const PROPERTY_FINDING_MARKERS = [
  'schedule of values', 'acord application', 'protection class', 'roof age',
  'year built', 'reinsurance treaty', 'tiv $', 'ncci', 'experience mod',
  'catastrophe', 'wildfire', 'flood zone', 'locations, coverages',
  'risk profile, locations', 'named insured, risk profile',
];

function isPropertyOnlyFinding(f) {
  const blob = `${displayText(f?.title)} ${displayText(f?.description)}`.toLowerCase();
  return PROPERTY_FINDING_MARKERS.some((m) => blob.includes(m));
}

function dedupeFindings(findings) {
  const seen = new Set();
  return asList(findings).filter((f) => {
    const key = `${safeLower(f?.title)}|${safeLower(f?.severity)}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export function buildAgentFindings(job) {
  const memo = job?.results?.memo || {};
  const line = safeLower(job?.results?.insurance_line || job?.results?.product_line);
  const isLife = line === 'life';
  const keep = (f) => f.category !== 'external_oracle' && !(isLife && isPropertyOnlyFinding(f));
  const sections = [
    ['risk_analyst_findings', 'Risk Analyst'],
    ['loss_run_findings', 'Loss Run'],
    ['compliance_findings', 'Compliance'],
    ['fraud_findings', 'Fraud Detection'],
  ];
  const built = sections
    .map(([key, label]) => ({
      key,
      label,
      findings: dedupeFindings(asList(memo[key]).filter(keep)),
    }))
    .filter((s) => s.findings.length > 0);
  // Only surface key_findings when agent buckets are empty (avoid duplicates).
  if (built.length === 0 && asList(memo.key_findings).length > 0) {
    return [{
      key: 'key_findings',
      label: 'Key Findings',
      findings: dedupeFindings(asList(memo.key_findings).filter(keep)),
    }];
  }
  return built;
}

export function buildProvenanceView(job) {
  const r = job?.results || {};
  const prov = r.provenance || {};
  const summary = r.provenance_summary || {};
  const nodes = (prov.nodes && typeof prov.nodes === 'object' && !Array.isArray(prov.nodes)) ? prov.nodes : {};
  const line = safeLower(r.insurance_line || r.product_line);
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
    isLife: line === 'life',
  };
}

export function buildCheckpoints(job) {
  return asList(job?.results?.human_checkpoints);
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
  const status = safeLower(job?.status);
  const recon = r.reconciliation || {};
  const discrepancies = asList(recon.discrepancies);
  const criticalDisc = discrepancies.filter((d) => safeLower(d?.severity) === 'critical');
  const memo = r.memo || {};
  const line = safeLower(r.insurance_line || r.product_line);
  const isLife = line === 'life';
  const checklist = r.document_checklist || {};

  // Don't flash a fake B/75 while the pipeline is still ingesting — wait until
  // triage/checklist/decision signals exist (or the job has finished).
  const hasSignals = Boolean(
    r.ai_decision
    || r.document_checklist
    || r.triage_score != null
    || r.appetite_filter_passed != null
    || (r.document_count != null && r.document_count > 0),
  );
  const stillRunning = status === 'processing' || status === 'pending' || status === 'queued';
  if (!hasSignals && (stillRunning || !status)) {
    return {
      score: null,
      grade: '—',
      gradeColor: 'text-slate-500',
      issues: ['Scoring after intake completes'],
      pending: true,
      lob: checklist.lob || line || null,
    };
  }

  let score = 100;
  const issues = [];

  if (!r.document_count && !r.ai_decision && !r.triage_score) {
    score -= 25;
    issues.push('No documents ingested');
  } else if (r.document_count != null && r.document_count < 2) {
    score -= 10;
    issues.push('Thin submission — only one document');
  }

  const completeness = checklist.completeness_pct;
  // document_checklist uses 0–1; package-checklist API uses 0–100
  const completenessFrac = completeness == null ? null : (completeness > 1 ? completeness / 100 : completeness);
  if (completenessFrac != null && completenessFrac < 0.5) {
    score -= 12;
    const miss = (checklist.missing_documents || checklist.missing || []).slice(0, 2).join(', ');
    const lobLabel = checklist.lob || line || 'package';
    issues.push(miss ? `Incomplete ${lobLabel} package: ${miss}` : `Incomplete ${lobLabel} package`);
  }

  if (r.appetite_needs_uw_referral) {
    score -= 10;
    issues.push('Appetite referral required');
  } else if (r.appetite_filter_passed === false) {
    score -= 35;
    issues.push('Outside appetite');
  }

  // Life packages rarely have ACORD field match — don't thrash the grade for that.
  if (!isLife && recon.match_rate != null && recon.match_rate < 0.8) {
    score -= Math.round((0.8 - recon.match_rate) * 40);
    issues.push(`Low field match rate (${Math.round(recon.match_rate * 100)}%)`);
  }

  if (criticalDisc.length) {
    score -= criticalDisc.length * 12;
    issues.push(`${criticalDisc.length} critical reconciliation conflict(s)`);
  } else if (discrepancies.length && !isLife) {
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

  return { score, grade, gradeColor, issues, pending: false, lob: checklist.lob || line || null };
}

export function buildVerificationSummary(job) {
  const r = job?.results || {};
  const memo = r.memo || {};
  const quoteFull = r.quote_full || {};
  const meta = quoteFull.metadata || {};
  const line = safeLower(r.insurance_line || r.product_line);
  const isLife = line === 'life';
  const oracleFindings = asList(memo.key_findings).filter((f) => f.category === 'external_oracle');
  const medical = meta.medical || {};

  return {
    oracleCount: isLife ? 0 : (r.oracle_findings_count ?? oracleFindings.length),
    oracleFindings: isLife ? [] : oracleFindings.slice(0, 4),
    copeGrade: isLife ? null : (meta.cope_grade || null),
    copeModPct: isLife ? null : (meta.cope_mod_pct ?? null),
    copeScore: isLife ? null : (meta.cope_score ?? null),
    marketPhase: meta.market_phase || null,
    marketModPct: meta.market_mod_pct ?? null,
    matchRate: r.reconciliation?.match_rate ?? null,
    reconStatus: r.reconciliation?.overall_status || null,
    isLife,
    lifeClass: medical.underwriting_class || null,
    tobacco: medical.tobacco ?? null,
    faceAmount: meta.face_amount || meta.tiv || null,
    filingId: meta.filing_id || null,
  };
}

export function buildPricingBreakdown(job) {
  const r = job?.results || {};
  const quote = r.quote || {};
  const quoteFull = r.quote_full || {};
  const meta = quoteFull.metadata || {};
  const base = quote.base_premium ?? quoteFull.base_premium ?? null;
  const adjusted = quote.adjusted_premium ?? quoteFull.adjusted_premium ?? null;
  const mods = asList(quoteFull.schedule_modifications);

  const premiumMods = mods
    .filter((m) => m.modifier_pct !== 0 || ['cope_schedule_rating', 'market_cycle_adjustment', 'loss_experience'].includes(m.name))
    .map((m) => ({
      key: m.name,
      label: humanModName(m.name),
      pct: Math.round((m.modifier_pct ?? 0) * 100) / 100,
      basis: m.basis || '',
    }));

  if (meta.deductible_credit) {
    const exists = premiumMods.some((m) => m.key === 'deductible_credit');
    if (!exists) {
      premiumMods.push({
        key: 'deductible_credit',
        label: 'Deductible credit',
        pct: Math.round(meta.deductible_credit * 100) / 100,
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
        pct: Math.round(meta.years_in_business_mod_pct * 100) / 100,
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
    discrepancies: asList(recon.discrepancies),
  };
}

export function getJourneyContext(job) {
  try {
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
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error('getJourneyContext failed', err);
    return {
      stages: [],
      miniStages: [],
      quality: { score: null, grade: '—', gradeColor: 'text-slate-500', issues: [], pending: true, lob: null },
      verification: { oracleCount: null, copeGrade: null, matchRate: null, isLife: false, lifeClass: null, tobacco: null, filingId: null },
      pricing: { base: null, adjusted: null, premiumMods: [] },
      reconciliation: { discrepancies: [], matchRate: null, matchedFields: 0, totalFields: 0, overallStatus: 'pending' },
      agentSections: [],
      provenance: { totalFields: 0, verifiedFields: 0, contradictedFields: 0, fields: [], isLife: false },
      checkpoints: [],
      bundleId: job?.results?.bundle_id || null,
      insuredName: '',
      processing: job?.status === 'processing',
      failed: job?.status === 'failed',
      currentStage: null,
    };
  }
}
