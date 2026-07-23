/** Shared UI components & formatters */

export function escapeHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function formatCurrency(n) {
  if (n == null || isNaN(n)) return '—';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n);
}

export function statusBadge(status) {
  const s = (status || 'unknown').toLowerCase();
  const pulse = s === 'processing' ? '<span class="pulse"></span>' : '';
  return `<span class="badge ${escapeHtml(s)}">${pulse}${escapeHtml(status || 'unknown')}</span>`;
}

export function overallLabel(o) {
  const map = { healthy: 'All Systems Operational', degraded: 'Degraded Performance', missing: 'Configuration Missing', error: 'System Error' };
  return map[o] || o;
}

export function toast(msg, type = 'info') {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4500);
}

export function extractInsuranceSummary(job) {
  const r = job?.results || {};
  const summary = r.summary || r.pipeline_summary || r;
  const memo = r.underwriting_memo || summary?.underwriting_memo || {};
  const quote = r.quote || summary?.quote || {};
  const decision = summary?.decision || summary?.recommendation
    || memo?.recommendation || memo?.decision
    || (summary?.underwriting_decision || {}).decision;
  return {
    bundleId: r.bundle_id || summary?.bundle_id || job?.bundle_id,
    decision,
    confidence: memo?.confidence || summary?.confidence,
    premium: quote?.adjusted_premium || quote?.indicated_premium || summary?.premium,
    memoText: typeof memo === 'string' ? memo : (memo?.executive_summary || memo?.narrative || memo?.summary || ''),
    quote,
    raw: job,
  };
}

export function extractMortgageSummary(job) {
  const r = job?.results || {};
  const summary = r.summary || r.pipeline_summary || r;
  const decision = summary?.decision || summary?.recommendation || r.decision;
  const rate = summary?.rate_quote || r.rate_quote || {};
  const violations = summary?.compliance_violations || r.compliance_violations || [];
  return {
    bundleId: r.bundle_id || summary?.bundle_id,
    decision,
    dti: summary?.dti_ratio || rate?.dti,
    ltv: summary?.ltv_ratio || rate?.ltv,
    rate: rate?.note_rate || rate?.interest_rate,
    payment: rate?.monthly_payment || rate?.pitia,
    violations: Array.isArray(violations) ? violations : [],
    memoText: summary?.underwriting_summary || summary?.narrative || '',
    raw: job,
  };
}

export function renderHealthHero(data) {
  const s = data.overall || 'unknown';
  const sum = data.summary || {};
  return `
    <div class="health-hero">
      <div class="health-ring ${escapeHtml(s)}">${Math.round((sum.ok || 0) / (sum.total || 1) * 100)}%</div>
      <div>
        <div style="font-size:1.35rem;font-weight:700;margin-bottom:0.25rem" class="${escapeHtml(s)}">${overallLabel(s)}</div>
        <div style="color:var(--text-muted);font-size:0.9rem;margin-bottom:0.75rem">
          LLM mode: <strong style="color:var(--accent)">${escapeHtml(data.llm_mode || 'unknown')}</strong>
        </div>
        <div style="display:flex;gap:0.5rem;flex-wrap:wrap">
          <span class="badge ok">${sum.ok || 0} OK</span>
          <span class="badge degraded">${sum.degraded || 0} Degraded</span>
          <span class="badge missing">${sum.missing || 0} Missing</span>
          ${sum.error ? `<span class="badge error">${sum.error} Error</span>` : ''}
        </div>
      </div>
    </div>`;
}

export function renderCheckList(checks) {
  if (!checks?.length) return '<div class="empty-state"><p>No diagnostics available</p></div>';
  return `<div class="check-list">${checks.map(c => `
    <div class="check-row">
      <span class="dot ${escapeHtml(c.status)}"></span>
      <div style="flex:1">
        <div class="check-title">${escapeHtml(c.component)}</div>
        <div class="check-msg">${escapeHtml(c.message)}</div>
        ${c.details && Object.keys(c.details).length ? `<div class="check-detail">${escapeHtml(JSON.stringify(c.details))}</div>` : ''}
      </div>
      <span class="badge ${escapeHtml(c.status)}">${escapeHtml(c.status)}</span>
    </div>`).join('')}</div>`;
}

export function renderJobDetail(vertical, job) {
  if (job.status === 'processing') {
    return `<div class="empty-state"><p>Job is still processing…</p><p style="margin-top:0.5rem;font-size:0.8rem">Auto-refreshing every 3s</p></div>`;
  }
  if (job.status === 'failed') {
    return `<div class="detail-section"><h4>Error</h4><div class="memo-box" style="color:var(--danger)">${escapeHtml(job.error || 'Unknown error')}</div></div>`;
  }

  if (vertical === 'insurance') {
    const s = extractInsuranceSummary(job);
    const r = job?.results || {};
    const stages = r.pipeline_stages || r.stages || {};
    const cope = r.cope_scores || r.cope;
    const provenance = r.provenance || r.field_provenance;
    const reconciliation = r.reconciliation || r.reconciliation_summary;
    return `
      <div class="detail-section">
        <h4>Underwriting Decision</h4>
        <div class="detail-grid">
          <div class="detail-item"><div class="label">Decision</div><div class="value">${statusBadge(s.decision)}</div></div>
          <div class="detail-item"><div class="label">Indicated Premium</div><div class="value">${formatCurrency(s.premium)}</div></div>
          <div class="detail-item"><div class="label">Bundle ID</div><div class="value mono">${escapeHtml(s.bundleId || '—')}</div></div>
          <div class="detail-item"><div class="label">Confidence</div><div class="value">${s.confidence != null ? `${Math.round(s.confidence * 100)}%` : '—'}</div></div>
        </div>
      </div>
      ${renderPipelineStages(stages)}
      ${renderCopeScores(cope)}
      ${renderQuoteBreakdown(s.quote)}
      ${renderReconciliationSummary(reconciliation)}
      ${renderProvenance(provenance)}
      ${s.memoText ? renderMemo(s.memoText) : ''}
      <span class="json-toggle" data-toggle-json>View raw JSON</span>
      <pre class="json-raw">${escapeHtml(JSON.stringify(job, null, 2))}</pre>`;
  }

  if (vertical === 'mortgage') {
    const s = extractMortgageSummary(job);
    const r = job?.results || {};
    const stages = r.pipeline_stages || r.stages || {};
    return `
      <div class="detail-section">
        <h4>Loan Decision</h4>
        <div class="detail-grid">
          <div class="detail-item"><div class="label">Decision</div><div class="value">${statusBadge(s.decision)}</div></div>
          <div class="detail-item"><div class="label">Note Rate</div><div class="value">${s.rate != null ? `${s.rate}%` : '—'}</div></div>
          <div class="detail-item"><div class="label">DTI</div><div class="value">${s.dti != null ? `${(s.dti * (s.dti <= 1 ? 100 : 1)).toFixed(1)}%` : '—'}</div></div>
          <div class="detail-item"><div class="label">Monthly PITIA</div><div class="value">${formatCurrency(s.payment)}</div></div>
        </div>
      </div>
      ${renderPipelineStages(stages)}
      ${renderComplianceViolations(s.violations)}
      ${s.memoText ? renderMemo(s.memoText, 'Underwriting Summary') : ''}
      <span class="json-toggle" data-toggle-json>View raw JSON</span>
      <pre class="json-raw">${escapeHtml(JSON.stringify(job, null, 2))}</pre>`;
  }

  if (vertical === 'lending') {
    return renderLendingResult(job?.results || job);
  }

  return `
    <span class="json-toggle" data-toggle-json>View raw JSON</span>
    <pre class="json-raw">${escapeHtml(JSON.stringify(job, null, 2))}</pre>`;
}

export const INSURANCE_STAGES = [
  'intake', 'ingestion', 'normalization', 'retrieval',
  'risk_scoring', 'underwriting', 'quote', 'reconciliation', 'reporting',
];

export const STAGE_LABELS = {
  intake: 'Intake', ingestion: 'Ingestion', normalization: 'Normalization',
  retrieval: 'Guideline Retrieval', risk_scoring: 'Risk Scoring',
  underwriting: 'Underwriting', quote: 'Quote Generation',
  reconciliation: 'Reconciliation', reporting: 'Reporting',
};

export function renderPipelineStages(stages) {
  if (!stages || !Object.keys(stages).length) {
    return '<div class="empty-state" style="padding:1rem"><p>No pipeline stage data</p></div>';
  }
  const ordered = INSURANCE_STAGES.filter(k => stages[k]);
  if (!ordered.length) {
    return '<div class="empty-state" style="padding:1rem"><p>No pipeline stage data</p></div>';
  }
  const completed = ordered.filter(k => stages[k]?.status === 'completed').length;
  const total = ordered.length;
  const pct = total ? Math.round((completed / total) * 100) : 0;
  return `
    <div class="pipeline-stages">
      <div class="pipeline-progress">
        <div class="pipeline-progress-bar" style="width:${pct}%"></div>
        <span class="pipeline-progress-label">${completed}/${total} stages</span>
      </div>
      <div class="stage-list">
        ${ordered.map((k, i) => {
          const st = stages[k];
          const status = st?.status || 'pending';
          const icon = status === 'completed' ? '&#10003;' : status === 'failed' ? '&#10007;' : status === 'skipped' ? '&#8212;' : (i + 1);
          const time = st?.elapsed_seconds != null ? ` ${st.elapsed_seconds.toFixed(1)}s` : '';
          const findings = st?.findings_count != null ? ` &middot; ${st.findings_count} findings` : '';
          return `<div class="stage-item ${status}">
            <div class="stage-marker">${icon}</div>
            <div class="stage-info">
              <div class="stage-name">${STAGE_LABELS[k] || k}<span class="stage-meta">${time}${findings}</span></div>
              ${st?.error ? `<div class="stage-error">${escapeHtml(st.error)}</div>` : ''}
            </div>
          </div>`;
        }).join('')}
      </div>
    </div>`;
}

export function renderCopeScores(cope) {
  if (!cope || typeof cope !== 'object') return '';
  const scores = cope.scores || cope;
  const keys = ['construction', 'occupancy', 'protection', 'exposure'];
  const vals = keys.map(k => scores[k]).filter(v => v != null);
  if (!vals.length) return '';
  const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
  return `
    <div class="cope-scores">
      <h4>COPE Scores</h4>
      <div class="cope-grid">
        ${keys.map(k => `
          <div class="cope-item">
            <div class="cope-value">${scores[k] != null ? scores[k].toFixed(1) : '—'}</div>
            <div class="cope-label">${k.charAt(0).toUpperCase() + k.slice(1)}</div>
            <div class="cope-bar"><div class="cope-bar-fill" style="width:${(scores[k] || 0) / 10 * 100}%"></div></div>
          </div>
        `).join('')}
        <div class="cope-item cope-avg">
          <div class="cope-value">${avg.toFixed(1)}</div>
          <div class="cope-label">Average</div>
          <div class="cope-bar"><div class="cope-bar-fill" style="width:${avg / 10 * 100}%"></div></div>
        </div>
      </div>
    </div>`;
}

export function renderQuoteBreakdown(quote) {
  if (!quote || typeof quote !== 'object') return '';
  const keys = [
    ['base_premium', 'Base Premium'],
    ['adjusted_premium', 'Adjusted Premium'],
    ['indicated_premium', 'Indicated Premium'],
    ['binding_premium', 'Binding Premium'],
  ];
  const fields = keys.filter(([k]) => quote[k] != null);
  if (!fields.length) return '';
  return `
    <div class="quote-breakdown">
      <h4>Quote Details</h4>
      <div class="detail-grid">
        ${fields.map(([k, label]) => `
          <div class="detail-item">
            <div class="label">${label}</div>
            <div class="value">${formatCurrency(quote[k])}</div>
          </div>
        `).join('')}
        ${quote.valid_until ? `
          <div class="detail-item">
            <div class="label">Valid Until</div>
            <div class="value">${escapeHtml(quote.valid_until)}</div>
          </div>
        ` : ''}
        ${quote.carrier ? `
          <div class="detail-item">
            <div class="label">Carrier</div>
            <div class="value">${escapeHtml(quote.carrier)}</div>
          </div>
        ` : ''}
        ${quote.product ? `
          <div class="detail-item">
            <div class="label">Product</div>
            <div class="value">${escapeHtml(quote.product)}</div>
          </div>
        ` : ''}
      </div>
    </div>`;
}

export function renderProvenance(provenance) {
  if (!provenance || typeof provenance !== 'object') return '';
  const fields = Object.entries(provenance);
  if (!fields.length) return '';
  return `
    <div class="provenance-section">
      <h4>Provenance</h4>
      <div class="provenance-grid">
        ${fields.map(([field, info]) => {
          const verified = info?.verified === true;
          const status = verified ? 'verified' : 'unverified';
          return `<div class="provenance-item ${status}">
            <span class="provenance-dot ${status}"></span>
            <span class="provenance-field">${escapeHtml(field)}</span>
            <span class="provenance-source">${escapeHtml(info?.source || '—')}</span>
          </div>`;
        }).join('')}
      </div>
    </div>`;
}

export function renderReconciliationSummary(recon) {
  if (!recon || typeof recon !== 'object') return '';
  const total = recon.total_fields ?? recon.fields_checked ?? 0;
  const verified = recon.verified ?? recon.fields_verified ?? 0;
  const discrepancies = recon.discrepancies ?? recon.discrepancy_count ?? 0;
  return `
    <div class="reconciliation-summary">
      <h4>Reconciliation</h4>
      <div class="detail-grid">
        <div class="detail-item"><div class="label">Fields Checked</div><div class="value">${total}</div></div>
        <div class="detail-item"><div class="label">Verified</div><div class="value" style="color:var(--success)">${verified}</div></div>
        <div class="detail-item"><div class="label">Discrepancies</div><div class="value" style="color:${discrepancies > 0 ? 'var(--danger)' : 'var(--success)'}">${discrepancies}</div></div>
      </div>
    </div>`;
}

export function renderMemo(text, title = 'Executive Summary') {
  if (!text) return '';
  return `<div class="detail-section"><h4>${escapeHtml(title)}</h4><div class="memo-box">${escapeHtml(text)}</div></div>`;
}

export function renderComplianceViolations(violations) {
  if (!violations?.length) return '';
  return `
    <div class="detail-section">
      <h4>Compliance Violations</h4>
      <ul class="violation-list">
        ${violations.map(v => {
          const msg = typeof v === 'string' ? v : v?.message || v?.description || JSON.stringify(v);
          const severity = typeof v === 'object' && v?.severity ? v.severity : '';
          return `<li class="${severity}"><span class="violation-severity">${escapeHtml(severity || 'info')}</span> ${escapeHtml(msg)}</li>`;
        }).join('')}
      </ul>
    </div>`;
}

export function renderLendingResult(result) {
  if (!result) return '<div class="empty-state"><p>No lending data available</p></div>';
  const decision = result.decision || result.recommendation || '—';
  const product = result.product || result.product_type || '—';
  return `
    <div class="detail-section">
      <h4>Lending Decision</h4>
      <div class="detail-grid">
        <div class="detail-item"><div class="label">Decision</div><div class="value">${statusBadge(decision)}</div></div>
        <div class="detail-item"><div class="label">Product</div><div class="value">${escapeHtml(product)}</div></div>
        <div class="detail-item"><div class="label">Application ID</div><div class="value mono">${escapeHtml(result.application_id || '—')}</div></div>
        <div class="detail-item"><div class="label">Confidence</div><div class="value">${result.confidence != null ? `${Math.round(result.confidence * 100)}%` : '—'}</div></div>
      </div>
    </div>
    ${result.narrative ? renderMemo(result.narrative, 'Narrative') : ''}
    <span class="json-toggle" data-toggle-json>View raw JSON</span>
    <pre class="json-raw">${escapeHtml(JSON.stringify(result, null, 2))}</pre>`;
}

export function renderEvalMetricCard(label, value, subtext = '') {
  return `
    <div class="eval-metric-card">
      <div class="eval-metric-value">${value}</div>
      <div class="eval-metric-label">${escapeHtml(label)}</div>
      ${subtext ? `<div class="eval-metric-sub">${escapeHtml(subtext)}</div>` : ''}
    </div>`;
}

export const icons = {
  overview: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
  system: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
  insurance: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/></svg>',
  mortgage: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
  lending: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg>',
  workflow: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="8.5" cy="7" r="4"/><polyline points="17 11 19 13 23 9"/></svg>',
  portfolio: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>',
  evaluations: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/></svg>',
  settings: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>',
};
