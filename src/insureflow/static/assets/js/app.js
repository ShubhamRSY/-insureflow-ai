import { auth, endpoints } from './api.js';
import {
  escapeHtml, formatCurrency, statusBadge, toast, icons,
  renderHealthHero, renderCheckList, renderJobDetail,
  extractInsuranceSummary, extractMortgageSummary,
  renderPipelineStages, renderCopeScores, renderQuoteBreakdown,
  renderProvenance, renderReconciliationSummary, renderMemo,
  renderLendingResult, renderEvalMetricCard,
} from './components.js';

const VIEWS = ['overview', 'system', 'insurance', 'mortgage', 'lending', 'portfolio', 'evaluations', 'ml', 'workflow', 'settings'];
const PROTECTED = new Set(['insurance', 'mortgage', 'lending', 'portfolio', 'evaluations', 'ml', 'workflow']);

const state = {
  route: 'overview',
  diagnostics: null,
  presets: null,
  overview: null,
  insuranceJobs: [],
  mortgageJobs: [],
  selectedJob: null,
  selectedVertical: null,
  pollTimer: null,
};

const titles = {
  overview: ['Overview', 'Platform activity and quick actions'],
  system: ['System Health', 'Environment diagnostics and configuration'],
  insurance: ['Commercial Insurance', 'P&C underwriting pipeline'],
  mortgage: ['Mortgage Underwriting', 'Residential & commercial loan packages'],
  lending: ['Consumer & Commercial Lending', 'Credit decisioning pipeline'],
  portfolio: ['Portfolio Concentration', 'Risk aggregate exposure'],
  evaluations: ['Evaluations & Quality', 'HITL scoring, drift detection, quality gates'],
  ml: ['ML Predictive Analytics', 'Loss prediction, fraud detection, premium optimization'],
  workflow: ['UW Sign-off Queue', 'Licensed underwriter review workflow'],
  settings: ['Account', 'Authentication and organization settings'],
};

function $(sel) { return document.querySelector(sel); }
function $$(sel) { return [...document.querySelectorAll(sel)]; }

function navigate(route) {
  if (PROTECTED.has(route) && !auth.isLoggedIn) {
    showLoginModal();
    return;
  }
  state.route = route;
  location.hash = `#/${route}`;
  $$('.nav-item').forEach(el => el.classList.toggle('active', el.dataset.route === route));
  $$('.view').forEach(el => el.classList.toggle('active', el.id === `view-${route}`));
  const [title, sub] = titles[route] || ['InsureFlow', ''];
  $('#pageTitle').textContent = title;
  $('#pageSubtitle').textContent = sub;
  loadView(route);
}

async function loadView(route) {
  try {
    switch (route) {
      case 'overview': await loadOverview(); break;
      case 'system': await loadSystem(); break;
      case 'insurance': await loadInsurance(); break;
      case 'mortgage': await loadMortgage(); break;
      case 'lending': await loadLending(); break;
      case 'portfolio': await loadPortfolio(); break;
      case 'evaluations': await loadEvaluations(); break;
      case 'ml': await loadML(); break;
      case 'workflow': await loadWorkflow(); break;
      case 'settings': renderSettings(); break;
    }
  } catch (e) {
    toast(e.message, 'error');
  }
}

function updateUserUI() {
  const chip = $('#userChip');
  if (!auth.isLoggedIn) {
    chip.innerHTML = `<button class="btn btn-primary btn-sm" id="loginBtn">Sign In</button>`;
    $('#loginBtn')?.addEventListener('click', showLoginModal);
    return;
  }
  const u = auth.user || {};
  const initials = (u.username || 'U').slice(0, 2).toUpperCase();
  chip.innerHTML = `
    <div class="user-chip">
      <div class="user-avatar">${escapeHtml(initials)}</div>
      <div>
        <div style="font-weight:600">${escapeHtml(u.username || '')}</div>
        <div style="font-size:0.7rem;color:var(--text-dim)">${escapeHtml(u.role || '')} · ${escapeHtml(u.org_id || '')}</div>
      </div>
    </div>
    <button class="btn btn-ghost btn-sm" id="logoutBtn">Logout</button>`;
  $('#logoutBtn')?.addEventListener('click', () => {
    auth.clear();
    updateUserUI();
    toast('Signed out', 'info');
    navigate('system');
  });
}

async function loadDiagnostics() {
  try {
    state.diagnostics = await endpoints.diagnostics();
  } catch {
    state.diagnostics = { overall: 'unknown', llm_mode: '' };
  }
  const pill = $('#sidebarHealthPill');
  if (pill) {
    const s = state.diagnostics.overall;
    pill.innerHTML = `<span class="dot ${escapeHtml(s)}"></span> ${escapeHtml(s)} · ${escapeHtml(state.diagnostics.llm_mode || '')}`;
  }
  return state.diagnostics;
}

async function loadOverview() {
  const [diag, overview] = await Promise.all([
    state.diagnostics ? Promise.resolve(state.diagnostics) : loadDiagnostics(),
    auth.isLoggedIn ? endpoints.overview() : Promise.resolve(null),
  ]);
  state.overview = overview;

  $('#overviewStats').innerHTML = overview ? `
    <div class="stat-card"><div class="stat-label">Insurance Jobs</div><div class="stat-value">${overview.insurance?.total || 0}</div><div class="stat-sub">${overview.insurance?.completed || 0} completed · ${overview.insurance?.processing || 0} running</div></div>
    <div class="stat-card"><div class="stat-label">Mortgage Jobs</div><div class="stat-value">${overview.mortgage?.total || 0}</div><div class="stat-sub">${overview.mortgage?.completed || 0} completed · ${overview.mortgage?.processing || 0} running</div></div>
    <div class="stat-card"><div class="stat-label">Lending Apps</div><div class="stat-value">${overview.lending?.total || 0}</div><div class="stat-sub">${overview.lending?.completed || 0} completed · ${overview.lending?.processing || 0} running</div></div>
    <div class="stat-card"><div class="stat-label">Pending UW Review</div><div class="stat-value">${overview.pending_reviews || 0}</div><div class="stat-sub">Requires licensed sign-off</div></div>
  ` : `
    <div class="stat-card" style="grid-column:1/-1"><div class="stat-label">Sign in required</div><div class="stat-value" style="font-size:1.1rem">Authenticate to view job metrics</div><div class="stat-sub"><button class="btn btn-primary btn-sm" onclick="document.getElementById('loginModal').classList.remove('hidden')">Sign In</button></div></div>`;

  const badge = $('#navBadgeWorkflow');
  if (badge) badge.textContent = overview?.pending_reviews || '';
  badge?.classList.toggle('hidden', !(overview?.pending_reviews > 0));

  if (!state.presets) state.presets = await endpoints.presets();
  const demos = [...(state.presets.insurance || []), ...(state.presets.mortgage || [])];
  $('#overviewDemos').innerHTML = demos.map(d => `
    <div class="demo-card" data-demo="${escapeHtml(d.id)}" data-vertical="${escapeHtml(d.vertical)}">
      <h4>${escapeHtml(d.name)}</h4>
      <p>${escapeHtml(d.description)}</p>
      <span class="tag">${escapeHtml(d.vertical)}</span>
    </div>`).join('');

  $$('#overviewDemos .demo-card').forEach(card => {
    card.addEventListener('click', () => runDemo(card.dataset.vertical, card.dataset.demo));
  });

  const jobs = overview?.recent_jobs || [];
  $('#overviewActivity').innerHTML = jobs.length ? `
    <div class="table-wrap"><table>
      <thead><tr><th>Job</th><th>Vertical</th><th>Status</th><th>Decision</th></tr></thead>
      <tbody>${jobs.slice(0, 10).map(j => `
        <tr data-job="${escapeHtml(j.job_id)}" data-vertical="${escapeHtml(j.vertical)}">
          <td class="mono">${escapeHtml(j.job_id)}</td>
          <td>${escapeHtml(j.vertical)}</td>
          <td>${statusBadge(j.status)}</td>
          <td>${j.decision ? statusBadge(j.decision) : '—'}</td>
        </tr>`).join('')}</tbody>
    </table></div>` : '<div class="empty-state"><p>No jobs yet — run a demo to get started</p></div>';

  $$('#overviewActivity tbody tr').forEach(row => {
    row.addEventListener('click', () => openJob(row.dataset.vertical, row.dataset.job));
  });
}

async function loadSystem() {
  const data = await loadDiagnostics();
  $('#systemHero').innerHTML = renderHealthHero(data);
  $('#systemChecks').innerHTML = renderCheckList(data.checks);
}

async function loadInsurance() {
  const [jobsResp, presets] = await Promise.all([
    endpoints.insuranceJobs(),
    state.presets ? Promise.resolve(state.presets) : endpoints.presets(),
  ]);
  state.presets = presets;
  state.insuranceJobs = jobsResp.jobs || [];

  $('#insuranceDemos').innerHTML = (presets.insurance || []).map(d => `
    <div class="demo-card" data-preset="${escapeHtml(d.id)}">
      <h4>${escapeHtml(d.name)}</h4>
      <p>${escapeHtml(d.description)}</p>
    </div>`).join('');
  $$('#insuranceDemos .demo-card').forEach(c => {
    c.addEventListener('click', () => runDemo('insurance', c.dataset.preset));
  });

  await renderJobTable('insurance', state.insuranceJobs, '#insuranceJobTable');
}

async function loadMortgage() {
  const [jobsResp, presets] = await Promise.all([
    endpoints.mortgageJobs(),
    state.presets ? Promise.resolve(state.presets) : endpoints.presets(),
  ]);
  state.presets = presets;
  state.mortgageJobs = jobsResp.jobs || [];

  $('#mortgageDemos').innerHTML = (presets.mortgage || []).map(d => `
    <div class="demo-card" data-preset="${escapeHtml(d.id)}">
      <h4>${escapeHtml(d.name)}</h4>
      <p>${escapeHtml(d.description)}</p>
      <span class="tag">${escapeHtml(d.product_line || 'mortgage')}</span>
    </div>`).join('');
  $$('#mortgageDemos .demo-card').forEach(c => {
    c.addEventListener('click', () => runDemo('mortgage', c.dataset.preset));
  });

  await renderJobTable('mortgage', state.mortgageJobs, '#mortgageJobTable');
}

async function loadLending() {
  try {
    const products = await endpoints.lendingProducts();
    const items = products.products || products || [];
    const arr = Array.isArray(items) ? items : [];
    $('#lendingProducts').innerHTML = arr.length
      ? arr.map(p => `
        <div class="demo-card">
          <h4>${escapeHtml(p.name || p.id || 'Product')}</h4>
          <p>${escapeHtml(p.description || p.category || '')}</p>
          <span class="tag">${escapeHtml(p.type || p.product_type || 'lending')}</span>
        </div>`).join('')
      : '<div class="empty-state"><p>No lending products configured</p></div>';
  } catch {
    $('#lendingProducts').innerHTML = '<div class="empty-state"><p>Lending module unavailable</p></div>';
  }

  $('#lendingContent').innerHTML = '<div class="empty-state"><p>Submit an application to view results here</p></div>';
}

async function loadPortfolio() {
  try {
    const data = await endpoints.portfolioSummary();
    const buckets = data.concentration_buckets || data.buckets || [];
    const totalExposure = data.total_exposure || 0;
    const topLines = data.top_lines || [];

    $('#portfolioStats').innerHTML = `
      <div class="stat-card"><div class="stat-label">Total Exposure</div><div class="stat-value">${formatCurrency(totalExposure)}</div></div>
      <div class="stat-card"><div class="stat-label">Active Policies</div><div class="stat-value">${data.active_policies || 0}</div></div>
      <div class="stat-card"><div class="stat-label">Buckets</div><div class="stat-value">${buckets.length}</div></div>
      <div class="stat-card"><div class="stat-label">Top Lines</div><div class="stat-value">${topLines.length}</div></div>`;

    $('#portfolioBuckets').innerHTML = buckets.length
      ? `<div class="table-wrap"><table>
          <thead><tr><th>Bucket</th><th>Exposure</th><th>Count</th><th>Avg Premium</th></tr></thead>
          <tbody>${buckets.map(b => `
            <tr>
              <td>${escapeHtml(b.bucket || b.name || '—')}</td>
              <td>${formatCurrency(b.exposure || b.total_exposure)}</td>
              <td>${b.count || b.policy_count || 0}</td>
              <td>${formatCurrency(b.avg_premium || b.average_premium)}</td>
            </tr>`).join('')}</tbody>
        </table></div>`
      : '<div class="empty-state"><p>No concentration data available</p></div>';

    $('#portfolioTopLines').innerHTML = topLines.length
      ? `<div class="table-wrap"><table>
          <thead><tr><th>Line</th><th>Exposure</th><th>Count</th></tr></thead>
          <tbody>${topLines.map(l => `
            <tr>
              <td>${escapeHtml(l.line || l.name || '—')}</td>
              <td>${formatCurrency(l.exposure || l.total_exposure)}</td>
              <td>${l.count || 0}</td>
            </tr>`).join('')}</tbody>
        </table></div>`
      : '';
  } catch (e) {
    $('#portfolioStats').innerHTML = '<div class="empty-state"><p>Portfolio data unavailable</p></div>';
    $('#portfolioBuckets').innerHTML = '';
    $('#portfolioTopLines').innerHTML = '';
  }
}

async function loadEvaluations() {
  const sections = [];

  try {
    const gates = await endpoints.qualityGates();
    const gateList = gates.gates || gates.results || [];
    sections.push(`<div class="eval-section"><h3>Quality Gates</h3>
      ${gateList.length ? `<div class="table-wrap"><table>
        <thead><tr><th>Gate</th><th>Status</th><th>Last Run</th><th>Details</th></tr></thead>
        <tbody>${gateList.map(g => `
          <tr>
            <td>${escapeHtml(g.name || g.gate_name || '—')}</td>
            <td>${statusBadge(g.status || g.result || '—')}</td>
            <td>${escapeHtml(g.last_run || g.timestamp || '—')}</td>
            <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis">${escapeHtml(g.details || g.message || '')}</td>
          </tr>`).join('')}</tbody>
      </table></div>`
      : '<div class="empty-state"><p>No quality gates configured</p></div>'}
    </div>`);
  } catch {
    sections.push('<div class="eval-section"><h3>Quality Gates</h3><div class="empty-state"><p>Unavailable</p></div></div>');
  }

  try {
    const hitl = await endpoints.hitlSummary();
    const reviews = hitl.reviews || hitl.results || [];
    sections.push(`<div class="eval-section"><h3>Human-in-the-Loop Reviews</h3>
      <div class="eval-metrics-row">
        ${renderEvalMetricCard('Total Reviews', hitl.total_reviews ?? reviews.length ?? 0)}
        ${renderEvalMetricCard('Avg Score', hitl.avg_score != null ? hitl.avg_score.toFixed(2) : '—')}
        ${renderEvalMetricCard('Approval Rate', hitl.approval_rate != null ? `${(hitl.approval_rate * 100).toFixed(0)}%` : '—')}
        ${renderEvalMetricCard('Pending', hitl.pending ?? '—')}
      </div>
      ${reviews.length ? `<div class="table-wrap"><table>
        <thead><tr><th>Review ID</th><th>Bundle</th><th>Score</th><th>Decision</th><th>Reviewer</th></tr></thead>
        <tbody>${reviews.slice(0, 20).map(r => `
          <tr>
            <td class="mono">${escapeHtml(r.review_id || r.id || '—')}</td>
            <td class="mono">${escapeHtml(r.bundle_id || '—')}</td>
            <td>${r.score != null ? r.score.toFixed(2) : '—'}</td>
            <td>${statusBadge(r.decision || r.outcome || '—')}</td>
            <td>${escapeHtml(r.reviewer || r.underwriter || '—')}</td>
          </tr>`).join('')}</tbody>
      </table></div>` : ''}
    </div>`);
  } catch {
    sections.push('<div class="eval-section"><h3>Human-in-the-Loop Reviews</h3><div class="empty-state"><p>Unavailable</p></div></div>');
  }

  try {
    const drift = await endpoints.drift();
    const metrics = drift.metrics || drift.results || [];
    sections.push(`<div class="eval-section"><h3>Drift Detection</h3>
      ${metrics.length ? `<div class="table-wrap"><table>
        <thead><tr><th>Metric</th><th>Current</th><th>Baseline</th><th>Drift</th><th>Status</th></tr></thead>
        <tbody>${metrics.map(m => `
          <tr>
            <td>${escapeHtml(m.metric || m.name || '—')}</td>
            <td>${m.current != null ? m.current.toFixed(3) : '—'}</td>
            <td>${m.baseline != null ? m.baseline.toFixed(3) : '—'}</td>
            <td>${m.drift != null ? m.drift.toFixed(3) : '—'}</td>
            <td>${statusBadge(m.status || (m.drift && Math.abs(m.drift) > 0.1 ? 'degraded' : 'ok'))}</td>
          </tr>`).join('')}</tbody>
      </table></div>`
      : '<div class="empty-state"><p>No drift data available</p></div>'}
    </div>`);
  } catch {
    sections.push('<div class="eval-section"><h3>Drift Detection</h3><div class="empty-state"><p>Unavailable</p></div></div>');
  }

  try {
    const trends = await endpoints.trends();
    const trendData = trends.trends || trends.results || [];
    sections.push(`<div class="eval-section"><h3>Performance Trends</h3>
      ${trendData.length ? `<div class="table-wrap"><table>
        <thead><tr><th>Metric</th><th>Value</th><th>Trend</th><th>Period</th></tr></thead>
        <tbody>${trendData.map(t => `
          <tr>
            <td>${escapeHtml(t.metric || t.name || '—')}</td>
            <td>${t.value != null ? (typeof t.value === 'number' ? t.value.toFixed(2) : t.value) : '—'}</td>
            <td>${t.trend ? (t.trend > 0 ? '&#9650;' : t.trend < 0 ? '&#9660;' : '&#8212;') : '—'}</td>
            <td>${escapeHtml(t.period || t.date || '—')}</td>
          </tr>`).join('')}</tbody>
      </table></div>`
      : '<div class="empty-state"><p>No trend data available</p></div>'}
    </div>`);
  } catch {
    sections.push('<div class="eval-section"><h3>Performance Trends</h3><div class="empty-state"><p>Unavailable</p></div></div>');
  }

  $('#evaluationsContent').innerHTML = sections.join('');
}

async function renderJobTable(vertical, jobIds, containerSel) {
  const container = $(containerSel);
  if (!jobIds.length) {
    container.innerHTML = '<div class="empty-state"><p>No jobs yet</p></div>';
    return;
  }

  const rows = await Promise.all(jobIds.slice().reverse().map(async (id) => {
    try {
      const job = vertical === 'insurance'
        ? await endpoints.insuranceJob(id)
        : await endpoints.mortgageJob(id);
      const s = vertical === 'insurance' ? extractInsuranceSummary(job) : extractMortgageSummary(job);
      return { id, job, s };
    } catch {
      return { id, job: { status: 'unknown' }, s: {} };
    }
  }));

  container.innerHTML = `
    <div class="table-wrap"><table>
      <thead><tr><th>Job ID</th><th>Status</th><th>Decision</th><th>${vertical === 'insurance' ? 'Premium' : 'Rate'}</th><th>Actions</th></tr></thead>
      <tbody>${rows.map(({ id, job, s }) => `
        <tr data-job="${escapeHtml(id)}" data-vertical="${vertical}">
          <td class="mono">${escapeHtml(id)}</td>
          <td>${statusBadge(job.status)}</td>
          <td>${s.decision ? statusBadge(s.decision) : '—'}</td>
          <td>${vertical === 'insurance' ? formatCurrency(s.premium) : (s.rate != null ? `${s.rate}%` : '—')}</td>
          <td><button class="btn btn-outline btn-sm" onclick="event.stopPropagation()">View</button></td>
        </tr>`).join('')}</tbody>
    </table></div>`;

  container.querySelectorAll('tbody tr').forEach(row => {
    row.addEventListener('click', () => openJob(row.dataset.vertical, row.dataset.job));
  });
}

async function openJob(vertical, jobId) {
  state.selectedVertical = vertical;
  state.selectedJob = jobId;
  const fetchJob = vertical === 'insurance' ? endpoints.insuranceJob : vertical === 'mortgage' ? endpoints.mortgageJob : endpoints.lendingResult;
  let job;
  try {
    job = await fetchJob(jobId);
  } catch (e) {
    toast(`Failed to load job: ${e.message}`, 'error');
    return;
  }

  $('#drawerTitle').textContent = jobId;
  $('#drawerBody').innerHTML = renderJobDetail(vertical, job);
  bindDrawerJsonToggle();
  $('#drawerOverlay').classList.add('open');

  clearInterval(state.pollTimer);
  if (job.status === 'processing') {
    state.pollTimer = setInterval(async () => {
      job = await fetchJob(jobId);
      $('#drawerBody').innerHTML = renderJobDetail(vertical, job);
      bindDrawerJsonToggle();
      if (job.status !== 'processing') {
        clearInterval(state.pollTimer);
        toast(`Job ${jobId} ${job.status}`, job.status === 'completed' ? 'success' : 'error');
        loadView(state.route);
      }
    }, 3000);
  }
}

function bindDrawerJsonToggle() {
  $('[data-toggle-json]')?.addEventListener('click', (e) => {
    e.target.nextElementSibling?.classList.toggle('open');
    e.target.textContent = e.target.nextElementSibling?.classList.contains('open') ? 'Hide raw JSON' : 'View raw JSON';
  });
}

function closeDrawer() {
  $('#drawerOverlay').classList.remove('open');
  clearInterval(state.pollTimer);
}

async function runDemo(vertical, presetId) {
  try {
    toast(`Starting ${presetId}…`, 'info');
    const res = vertical === 'insurance'
      ? await endpoints.runInsuranceDemo(presetId)
      : await endpoints.runMortgageDemo(presetId);
    toast(`Job queued: ${res.job_id}`, 'success');
    navigate(vertical);
    setTimeout(() => openJob(vertical, res.job_id), 500);
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function loadML() {
  let status;
  try {
    status = await endpoints.mlStatus();
  } catch {
    status = { models: [] };
  }

  const models = status.models || [];
  $('#mlModels').innerHTML = models.length ? `
    <div class="table-wrap"><table>
      <thead><tr><th>Model</th><th>Version</th><th>Status</th><th>Key Metric</th></tr></thead>
      <tbody>${models.map(m => {
        const metric = m.metrics?.val_r2 != null ? `R²: ${m.metrics.val_r2.toFixed(3)}`
          : m.metrics?.val_f1 != null ? `F1: ${m.metrics.val_f1.toFixed(3)}`
          : m.metrics?.val_accuracy != null ? `Acc: ${(m.metrics.val_accuracy * 100).toFixed(1)}%`
          : 'Trained';
        return `<tr>
          <td><strong>${escapeHtml(m.model_name || m.model_type)}</strong></td>
          <td class="mono">${escapeHtml(m.version || '—')}</td>
          <td>${statusBadge(m.status || (m.is_trained ? 'ready' : 'draft'))}</td>
          <td>${escapeHtml(metric)}</td>
        </tr>`;
      }).join('')}</tbody>
    </table></div>`
    : '<div class="empty-state"><p>No models trained yet — click "Train All" to bootstrap</p></div>';

  $('#mlQuickPredict').innerHTML = `
    <div class="eval-metrics-row">
      ${renderEvalMetricCard('Loss Prediction', models.find(m => m.model_type === 'loss_prediction')?.version || '—', 'Frequency × Severity')}
      ${renderEvalMetricCard('Fraud Detection', models.find(m => m.model_type === 'fraud_detection')?.version || '—', 'Isolation Forest + GBM')}
      ${renderEvalMetricCard('Premium Optimizer', models.find(m => m.model_type === 'premium_optimizer')?.version || '—', 'Elasticity + Margin')}
      ${renderEvalMetricCard('Churn Prediction', models.find(m => m.model_type === 'churn_prediction')?.version || '—', 'Non-Renewal Risk')}
      ${renderEvalMetricCard('Portfolio Risk', '1.0.0', 'Monte Carlo VaR')}
      ${renderEvalMetricCard('Behavioral Scoring', '1.0.0', 'Broker Quality')}
    </div>`;

  const history = status.history || [];
  $('#mlHistory').innerHTML = history.length
    ? `<div class="table-wrap"><table>
        <thead><tr><th>Model</th><th>Version</th><th>Trained At</th><th>Val R²/Acc</th></tr></thead>
        <tbody>${history.map(h => {
          const score = h.metrics?.val_r2 != null ? h.metrics.val_r2.toFixed(3)
            : h.metrics?.val_accuracy != null ? (h.metrics.val_accuracy * 100).toFixed(1) + '%'
            : '—';
          return `<tr>
            <td>${escapeHtml(h.model_type)}</td>
            <td class="mono">${escapeHtml(h.version)}</td>
            <td>${escapeHtml(h.trained_at?.slice(0, 19)?.replace('T', ' ') || '—')}</td>
            <td>${escapeHtml(score)}</td>
          </tr>`;
        }).join('')}</tbody>
      </table></div>`
    : '<div class="empty-state"><p>No training history yet</p></div>';
}

async function loadWorkflow() {
  const data = await endpoints.pendingWorkflow();
  const pending = data.pending || [];
  const el = $('#workflowList');

  if (!pending.length) {
    el.innerHTML = '<div class="empty-state"><p>No submissions awaiting licensed UW sign-off</p></div>';
    return;
  }

  el.innerHTML = pending.map(p => `
    <div class="workflow-card" data-bundle="${escapeHtml(p.bundle_id || p.bundleId || '')}">
      <div style="display:flex;justify-content:space-between;align-items:center">
        <strong class="mono">${escapeHtml(p.bundle_id || p.bundleId || 'unknown')}</strong>
        ${statusBadge(p.state || p.status || 'pending')}
      </div>
      <p style="font-size:0.82rem;color:var(--text-muted);margin-top:0.35rem">${escapeHtml(p.recommendation || p.decision || 'Awaiting review')}</p>
      <div class="workflow-actions">
        <button class="btn btn-primary btn-sm" data-action="approve">Approve</button>
        <button class="btn btn-secondary btn-sm" data-action="refer">Refer</button>
        <button class="btn btn-ghost btn-sm" data-action="decline">Decline</button>
      </div>
    </div>`).join('');

  el.querySelectorAll('.workflow-card').forEach(card => {
    const bundleId = card.dataset.bundle;
    card.querySelectorAll('[data-action]').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const action = btn.dataset.action;
        const license = prompt('License number (optional):') || '';
        const notes = prompt('Notes (optional):') || '';
        try {
          await endpoints.signOff(bundleId, { action, license_number: license, notes });
          toast(`Sign-off ${action} recorded`, 'success');
          loadWorkflow();
        } catch (err) {
          toast(err.message, 'error');
        }
      });
    });
  });
}

function renderSettings() {
  $('#settingsContent').innerHTML = auth.isLoggedIn ? `
    <div class="card"><div class="card-body">
      <div class="detail-grid">
        <div class="detail-item"><div class="label">Username</div><div class="value">${escapeHtml(auth.user?.username)}</div></div>
        <div class="detail-item"><div class="label">Role</div><div class="value">${escapeHtml(auth.user?.role)}</div></div>
        <div class="detail-item"><div class="label">Organization</div><div class="value">${escapeHtml(auth.user?.org_id)}</div></div>
      </div>
      <button class="btn btn-secondary" style="margin-top:1rem" id="settingsLogout">Sign Out</button>
    </div></div>` : `
    <div class="card"><div class="card-body">
      <p style="color:var(--text-muted);margin-bottom:1rem">Sign in to access underwriting pipelines, job history, and workflow queues.</p>
      <button class="btn btn-primary" id="settingsLogin">Sign In / Setup</button>
    </div></div>`;

  $('#settingsLogout')?.addEventListener('click', () => { auth.clear(); updateUserUI(); renderSettings(); });
  $('#settingsLogin')?.addEventListener('click', showLoginModal);
}

async function showLoginModal() {
  switchAuthTab('login');
  $('#loginModal').classList.remove('hidden');
}

function hideLoginModal() {
  $('#loginModal').classList.add('hidden');
}

async function handleLogin(e) {
  e.preventDefault();
  const username = $('#loginUsername').value.trim();
  const password = $('#loginPassword').value;
  try {
    const token = await endpoints.login(username, password);
    auth.token = token.access_token;
    const me = await endpoints.me();
    auth.user = me;
    hideLoginModal();
    updateUserUI();
    toast(`Welcome, ${me.username}`, 'success');
    navigate(state.route);
  } catch (err) {
    toast(err.message, 'error');
  }
}

async function handleSetup(e) {
  e.preventDefault();
  try {
    await endpoints.setup({
      username: $('#setupUsername').value.trim(),
      password: $('#setupPassword').value,
      full_name: $('#setupName').value.trim(),
      org_id: $('#setupOrg').value.trim() || 'default',
      role: 'admin',
    });
    toast('Admin account created — sign in now', 'success');
    switchAuthTab('login');
    $('#loginUsername').value = $('#setupUsername').value.trim();
  } catch (err) {
    toast(err.message, 'error');
  }
}

function switchAuthTab(tab) {
  $$('.modal-tabs button').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  $('#loginForm').classList.toggle('hidden', tab !== 'login');
  $('#setupForm').classList.toggle('hidden', tab !== 'setup');
}

async function submitInsuranceCustom(e) {
  e.preventDefault();
  const acord = $('#insAcord').value.trim();
  if (!acord) { toast('ACORD XML is required', 'error'); return; }
  try {
    const res = await endpoints.runInsurance({
      acord_xml: acord,
      loss_run: $('#insLossRun').value.trim() || undefined,
      schedule_of_values: $('#insSov').value.trim() || undefined,
      use_llm: $('#insUseLlm').checked,
    });
    toast(`Job ${res.job_id} started`, 'success');
    loadInsurance();
    openJob('insurance', res.job_id);
  } catch (err) {
    toast(err.message, 'error');
  }
}

async function submitMortgageCustom(e) {
  e.preventDefault();
  const docName = $('#mortDocName').value.trim();
  const docContent = $('#mortDocContent').value.trim();
  if (!docName || !docContent) { toast('Document name and content are required', 'error'); return; }
  try {
    const res = await endpoints.runMortgage({
      documents: [{ filename: docName, content: docContent }],
      product_line: $('#mortProduct').value,
      use_llm: $('#mortUseLlm').checked,
      per_borrower: $('#mortPerBorrower').checked,
    });
    toast(`Job ${res.job_id} started`, 'success');
    loadMortgage();
    openJob('mortgage', res.job_id);
  } catch (err) {
    toast(err.message, 'error');
  }
}

function init() {
  $$('.nav-item').forEach(el => el.addEventListener('click', () => navigate(el.dataset.route)));
  $('#refreshBtn')?.addEventListener('click', () => loadView(state.route));
  $('#drawerClose')?.addEventListener('click', closeDrawer);
  $('#drawerOverlay')?.addEventListener('click', (e) => { if (e.target.id === 'drawerOverlay') closeDrawer(); });
  $('#loginForm')?.addEventListener('submit', handleLogin);
  $('#setupForm')?.addEventListener('submit', handleSetup);
  $$('.modal-tabs button').forEach(b => b.addEventListener('click', () => switchAuthTab(b.dataset.tab)));
  $('#loginModalClose')?.addEventListener('click', hideLoginModal);
  $('#insuranceForm')?.addEventListener('submit', submitInsuranceCustom);
  $('#mortgageForm')?.addEventListener('submit', submitMortgageCustom);
  $('#mlTrainAllBtn')?.addEventListener('click', async () => {
    if (!auth.isLoggedIn) { showLoginModal(); return; }
    try {
      toast('Training all ML models…', 'info');
      const res = await endpoints.mlTrainAll();
      toast(`Trained ${res.trained} models`, 'success');
      loadML();
    } catch (e) {
      toast(e.message, 'error');
    }
  });
  $('#mobileMenuBtn')?.addEventListener('click', () => $('#sidebar').classList.toggle('open'));

  if (auth.isLoggedIn) {
    endpoints.me().then(me => { auth.user = me; updateUserUI(); }).catch(() => auth.clear());
  } else {
    updateUserUI();
  }

  loadDiagnostics();
  const hash = location.hash.replace('#/', '') || 'overview';
  navigate(VIEWS.includes(hash) ? hash : 'overview');

  setInterval(() => {
    if (state.route === 'system' || state.route === 'overview') loadDiagnostics();
  }, 60000);
}

window.switchAuthTab = switchAuthTab;

document.addEventListener('DOMContentLoaded', init);
