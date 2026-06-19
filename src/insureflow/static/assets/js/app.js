import { auth, endpoints } from './api.js';
import {
  escapeHtml, formatCurrency, statusBadge, toast, icons,
  renderHealthHero, renderCheckList, renderJobDetail,
  extractInsuranceSummary, extractMortgageSummary,
} from './components.js';

const VIEWS = ['overview', 'system', 'insurance', 'mortgage', 'workflow', 'settings'];
const PROTECTED = new Set(['insurance', 'mortgage', 'workflow']);

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
  state.diagnostics = await endpoints.diagnostics();
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
    <div class="stat-card"><div class="stat-label">Pending UW Review</div><div class="stat-value">${overview.pending_reviews || 0}</div><div class="stat-sub">Requires licensed sign-off</div></div>
    <div class="stat-card"><div class="stat-label">System Health</div><div class="stat-value" style="font-size:1.25rem;color:var(--accent)">${escapeHtml(diag.overall)}</div><div class="stat-sub">LLM: ${escapeHtml(diag.llm_mode || 'unknown')}</div></div>
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
      <thead><tr><th>Job ID</th><th>Status</th><th>Decision</th><th>${vertical === 'insurance' ? 'Premium' : 'Rate'}</th><th></th></tr></thead>
      <tbody>${rows.map(({ id, job, s }) => `
        <tr data-job="${escapeHtml(id)}" data-vertical="${vertical}">
          <td class="mono">${escapeHtml(id)}</td>
          <td>${statusBadge(job.status)}</td>
          <td>${s.decision ? statusBadge(s.decision) : '—'}</td>
          <td>${vertical === 'insurance' ? formatCurrency(s.premium) : (s.rate != null ? `${s.rate}%` : '—')}</td>
          <td><button class="btn btn-ghost btn-sm">View</button></td>
        </tr>`).join('')}</tbody>
    </table></div>`;

  container.querySelectorAll('tbody tr').forEach(row => {
    row.addEventListener('click', () => openJob(row.dataset.vertical, row.dataset.job));
  });
}

async function openJob(vertical, jobId) {
  state.selectedVertical = vertical;
  state.selectedJob = jobId;
  const fetchJob = vertical === 'insurance' ? endpoints.insuranceJob : endpoints.mortgageJob;
  let job = await fetchJob(jobId);

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
  if (!auth.isLoggedIn) { showLoginModal(); return; }
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

function showLoginModal() {
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
  const directory = $('#mortDirectory').value.trim();
  if (!directory) { toast('Directory path is required', 'error'); return; }
  try {
    const res = await endpoints.runMortgage({
      directory,
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

document.addEventListener('DOMContentLoaded', init);
