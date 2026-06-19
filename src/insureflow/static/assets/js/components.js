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
      ${s.memoText ? `<div class="detail-section"><h4>Executive Summary</h4><div class="memo-box">${escapeHtml(s.memoText)}</div></div>` : ''}
      ${s.quote && Object.keys(s.quote).length ? `<div class="detail-section"><h4>Rating Quote</h4><div class="memo-box">${escapeHtml(JSON.stringify(s.quote, null, 2))}</div></div>` : ''}
      <span class="json-toggle" data-toggle-json>View raw JSON</span>
      <pre class="json-raw">${escapeHtml(JSON.stringify(job, null, 2))}</pre>`;
  }

  const s = extractMortgageSummary(job);
  const violHtml = s.violations.length
    ? `<ul class="violation-list">${s.violations.map(v => `<li>${escapeHtml(typeof v === 'string' ? v : v.message || JSON.stringify(v))}</li>`).join('')}</ul>`
    : '<p style="color:var(--text-dim);font-size:0.85rem">No compliance violations</p>';

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
    <div class="detail-section"><h4>Compliance</h4>${violHtml}</div>
    ${s.memoText ? `<div class="detail-section"><h4>Underwriting Summary</h4><div class="memo-box">${escapeHtml(s.memoText)}</div></div>` : ''}
    <span class="json-toggle" data-toggle-json>View raw JSON</span>
    <pre class="json-raw">${escapeHtml(JSON.stringify(job, null, 2))}</pre>`;
}

export const icons = {
  overview: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
  system: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
  insurance: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/></svg>',
  mortgage: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
  workflow: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="8.5" cy="7" r="4"/><polyline points="17 11 19 13 23 9"/></svg>',
  settings: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>',
};
