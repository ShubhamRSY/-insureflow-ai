const TOKEN_KEY = 'insureflow_token';
const USER_KEY = 'insureflow_user';

export const auth = {
  get token() { return localStorage.getItem(TOKEN_KEY); },
  set token(v) { v ? localStorage.setItem(TOKEN_KEY, v) : localStorage.removeItem(TOKEN_KEY); },
  get user() {
    try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null'); }
    catch { return null; }
  },
  set user(v) { v ? localStorage.setItem(USER_KEY, JSON.stringify(v)) : localStorage.removeItem(USER_KEY); },
  clear() { this.token = null; this.user = null; },
  wipeSession() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    try { sessionStorage.removeItem(TOKEN_KEY); sessionStorage.removeItem(USER_KEY); } catch { /* ignore */ }
  },
  get isLoggedIn() { return !!this.token; },
};

export class AuthError extends Error {
  constructor(message = 'Session expired') {
    super(message);
    this.name = 'AuthError';
    this.isAuth = true;
  }
}

export async function api(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  if (opts.body && !(opts.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(opts.body);
  }
  if (auth.token) headers.Authorization = `Bearer ${auth.token}`;

  const res = await fetch(path, { ...opts, headers });
  let data = null;
  const ct = res.headers.get('content-type') || '';
  if (ct.includes('application/json')) {
    try { data = await res.json(); } catch { /* empty */ }
  } else if (ct.includes('text/html')) {
    try { data = await res.text(); } catch { /* empty */ }
  }
  if (!res.ok) {
    const msg = data?.detail
      ? (typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail))
      : `HTTP ${res.status}`;
    if (res.status === 401) {
      auth.wipeSession();
      throw new AuthError(msg);
    }
    throw new Error(msg);
  }
  return data;
}

export const endpoints = {
  diagnostics: () => api('/system/diagnostics'),
  presets: () => api('/api/demo/presets'),
  overview: () => api('/api/dashboard/overview'),
  login: (username, password) => api('/auth/login', { method: 'POST', body: { username, password } }),
  authStatus: () => api('/auth/status'),
  authReset: () => api('/auth/reset', { method: 'POST' }).then((r) => { auth.wipeSession(); return r; }),
  setup: (body) => api('/auth/setup', { method: 'POST', body }),
  me: () => api('/auth/me'),
  register: (body) => api('/auth/register', { method: 'POST', body }),
  roles: () => api('/auth/roles'),
  insuranceJobs: () => api('/pipeline/jobs'),
  insuranceJob: (id) => api(`/pipeline/jobs/${id}`),
  downloadJob: (id) => api(`/pipeline/jobs/${id}/download`),
  deleteJob: (id) => api(`/pipeline/jobs/${id}`, { method: 'DELETE' }),
  retryJob: (id) => api(`/pipeline/jobs/${id}/retry`, { method: 'POST' }),
  runInsurance: (body) => api('/pipeline/run', { method: 'POST', body }),
  runInsuranceDemo: (preset) => api(`/api/demo/insurance/${preset}`, { method: 'POST' }),
  mortgageJobs: () => api('/mortgage/pipeline/jobs'),
  mortgageJob: (id) => api(`/mortgage/pipeline/jobs/${id}`),
  runMortgage: (body) => api('/mortgage/pipeline/run', { method: 'POST', body }),
  runMortgageDemo: (preset) => api(`/api/demo/mortgage/${preset}`, { method: 'POST' }),
  runLendingDemo: (preset) => api(`/api/demo/lending/${preset}`, { method: 'POST' }),
  pendingWorkflow: () => api('/pipeline/workflow/pending'),
  signOff: (bundleId, body) => api(`/pipeline/workflow/${bundleId}/sign-off`, { method: 'POST', body }),
  insuranceSources: (vertical = 'insurance') => api(`/api/insurance/sources?vertical=${vertical}`),
  pullInsuranceSource: (sourceId, body = {}, vertical = 'insurance') =>
    api(`/api/insurance/sources/${sourceId}/pull?vertical=${vertical}`, { method: 'POST', body }),
  filterEmails: (emailIds) => api('/api/insurance/sources/email-inbox/filter', { method: 'POST', body: { email_ids: emailIds } }),

  // Draft bundles (multi-source intake)
  draftBundles: () => api('/pipeline/bundles'),
  createDraftBundle: (name = '') => api('/pipeline/bundles', { method: 'POST', body: { name } }),
  getDraftBundle: (id) => api(`/pipeline/bundles/${id}`),
  addDocsToDraft: (id, documents, sourceId = '', connectionLabel = '') =>
    api(`/pipeline/bundles/${id}/documents`, { method: 'POST', body: { documents, source_id: sourceId, connection_label: connectionLabel } }),
  removeDocFromDraft: (bundleId, docId) =>
    api(`/pipeline/bundles/${bundleId}/documents/${docId}`, { method: 'DELETE' }),
  deleteDraftBundle: (id) => api(`/pipeline/bundles/${id}`, { method: 'DELETE' }),
  runDraftBundle: (id, useLlm = true, vertical = 'insurance') =>
    api(`/pipeline/bundles/${id}/run?use_llm=${useLlm}&vertical=${vertical}`, { method: 'POST' }),

  // New v2 pipeline
  runInsuranceV2: (body) => api('/pipeline/v2/run', { method: 'POST', body }),
  deepDive: (bundleId, include = []) =>
    api(`/pipeline/${bundleId}/deep-dive`, { method: 'POST', body: { include } }),

  // Broker status
  brokerStatus: (token) => api(`/broker/status/${token}`),
  createBrokerShare: (bundleId) => api(`/pipeline/jobs/${bundleId}/broker-share`, { method: 'POST' }),

  // Vision / photo analysis
  analyzePhotos: (body) => api('/pipeline/vision/analyze', { method: 'POST', body }),
  visionStatus: () => api('/pipeline/vision/status'),

  // Portfolio concentration
  portfolioSummary: () => api('/portfolio/summary'),

  // Core integration status
  integrationStatus: () => api('/integration/status'),
  connectSource: (sourceId, config = {}, vertical = 'insurance') =>
    api(`/api/connections/${sourceId}`, { method: 'POST', body: { config, vertical } }),
  disconnectSource: (sourceId) =>
    api(`/api/connections/${sourceId}`, { method: 'DELETE' }),
  pullConnectedSource: (sourceId, body) =>
    api(`/api/connections/${sourceId}/pull`, { method: 'POST', body }),

  // Insurance webhooks
  insuranceWebhooks: () => api('/webhooks/insurance'),
  registerInsuranceWebhook: (body) => api('/webhooks/insurance', { method: 'POST', body }),
  deleteWebhook: (id) => api(`/webhooks/${id}`, { method: 'DELETE' }),

  // Underwriting workspace
  submissionQueue: (priority, limit) => api(`/pipeline/queue?priority=${priority || ''}&limit=${limit || 50}`),
  copeAnalysis: (bundleId) => api(`/pipeline/cope/${bundleId}`),
  marketCycle: () => api('/underwriting/market'),
  setMarketCycle: (phase) => api(`/underwriting/market/set?phase=${phase}`, { method: 'POST' }),
  authorityMatrix: () => api('/underwriting/authority'),
  upsertAuthority: (body) => api('/underwriting/authority', { method: 'POST', body }),
  deleteAuthority: (username) => api(`/underwriting/authority/${encodeURIComponent(username)}`, { method: 'DELETE' }),
  renewalAnalysis: (bundleId) => api(`/pipeline/renewal/${bundleId}`, { method: 'POST' }),
  missingDocuments: (bundleId) => api(`/pipeline/documents/${bundleId}/missing`),
  requestBrokerDocs: (bundleId, documents, notes = '') =>
    api(`/pipeline/documents/${bundleId}/request`, { method: 'POST', body: { documents, notes } }),
  infoRequests: (bundleId) => api(`/pipeline/jobs/${bundleId}/info-requests`),
  relationshipNotes: (bundleId) => api(`/pipeline/jobs/${bundleId}/relationship-notes`),
  addRelationshipNote: (bundleId, body) =>
    api(`/pipeline/jobs/${bundleId}/relationship-notes`, { method: 'POST', body }),
  packageChecklist: (bundleId, lob = 'auto') =>
    api(`/pipeline/jobs/${bundleId}/package-checklist?lob=${lob}`),
  brokerRespond: (token, body) => api(`/broker/status/${token}/respond`, { method: 'POST', body }),
  ecosystemStatus: () => api('/pipeline/ecosystem/status'),
  ecosystemBundle: (bundleId) => api(`/pipeline/ecosystem/${bundleId}`),
  dispatchLossControl: (bundleId, notes = '') => api(`/pipeline/ecosystem/${bundleId}/loss-control/dispatch`, { method: 'POST', body: { notes } }),
  resolveCheckpoint: (bundleId, checkpointId, action) => api(`/pipeline/checkpoints/${bundleId}/${checkpointId}`, { method: 'POST', body: { action } }),

  // Pilot lab
  pilotSandboxStatus: () => api('/pilot/sandbox-status'),
  pilotPackages: () => api('/pilot/packages'),
  pilotRun: (body) => api('/pilot/packages/run', { method: 'POST', body }),
  pilotScanPii: (partner, submissionId) => api(`/pilot/packages/${partner}/${submissionId}/pii`),
  pilotRedact: (body) => api('/pilot/packages/redact', { method: 'POST', body }),
  pilotIngestEmail: (body) => api('/pilot/ingest/email', { method: 'POST', body }),
  pilotCalibrate: () => api('/pilot/calibrate', { method: 'POST' }),
  pilotCalibration: () => api('/pilot/calibration'),
  pilotSeed: () => api('/pilot/seed', { method: 'POST' }),
  pilotRecordHuman: (body) => api('/pilot/calibration/human', { method: 'POST', body }),

  // Premium audit
  premiumAudits: (status) => api(`/pipeline/audits${status ? `?status=${status}` : ''}`),
  createPremiumAudit: (bundleId, estimated_premium, opts = {}) => api(
    `/pipeline/audits/${bundleId}/create?estimated_premium=${estimated_premium}${opts.policy_number ? `&policy_number=${opts.policy_number}` : ''}${opts.policy_period_start ? `&policy_period_start=${opts.policy_period_start}` : ''}${opts.policy_period_end ? `&policy_period_end=${opts.policy_period_end}` : ''}`,
    { method: 'POST' }
  ),
  completePremiumAudit: (auditId, actual_premium, notes = '') => api(
    `/pipeline/audits/${auditId}/complete?actual_premium=${actual_premium}&notes=${encodeURIComponent(notes)}`,
    { method: 'POST' }
  ),
  recordAuditAdjustment: (auditId, amount, reason) => api(
    `/pipeline/audits/${auditId}/adjustment?amount=${amount}&reason=${encodeURIComponent(reason)}`,
    { method: 'POST' }
  ),
  materialAdjustments: () => api('/pipeline/audits/material-adjustments'),

  // Insurance audit trail & export
  auditTrail: (bundleId) => api(`/pipeline/audit/${bundleId}`),
  auditPackage: (bundleId) => api(`/pipeline/audit/${bundleId}/package`),
  workflowDetail: (bundleId) => api(`/pipeline/workflow/${bundleId}`),
  bindPolicy: (bundleId) => api(`/pipeline/workflow/${bundleId}/bind`, { method: 'POST' }),
  insuranceQuote: (jobId) => api(`/pipeline/jobs/${jobId}/quote`),
  insuranceReport: async (jobId) => {
    const headers = {};
    if (auth.token) headers.Authorization = `Bearer ${auth.token}`;
    const res = await fetch(`/pipeline/jobs/${jobId}/report`, { headers });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const blob = await res.blob();
    const cd = res.headers.get('content-disposition') || '';
    const ext = cd.includes('.pdf') ? 'pdf' : 'html';
    const name = (cd.match(/filename="?(.+?)"?$/) || [])[1] || `Rytera_Report.${ext}`;
    return { blob, filename: name };
  },
  // Insurance products & outcomes
  insuranceProducts: () => api('/pipeline/rating/products'),
  lossExperience: (body) => api('/pipeline/outcomes/loss-experience', { method: 'POST', body }),
  calibration: () => api('/pipeline/outcomes/calibration'),

  // Override analytics
  overrideAnalytics: () => api('/analytics/overrides'),
  overridePatterns: () => api('/analytics/overrides/patterns'),
  documentAnalytics: () => api('/analytics/documents'),
  agentPerformance: () => api('/analytics/agent-performance'),
  evalTrends: () => api('/evaluations/trends'),
  logExplorers: () => api('/observability/log-explorers'),

  // Mortgage audit & products
  mortgageAudit: (bundleId) => api(`/mortgage/audit/${bundleId}`),
  mortgageProducts: () => api('/mortgage/products'),
  mortgageWebhooks: () => api('/mortgage/webhooks'),
  registerMortgageWebhook: (body) => api('/mortgage/webhooks', { method: 'POST', body }),
  deleteMortgageWebhook: (id) => api(`/mortgage/webhooks/${id}`, { method: 'DELETE' }),

  // Lending
  lendingProducts: () => api('/lending/products'),
  runLending: (body) => api('/lending/pipeline/run', { method: 'POST', body }),
  lendingResult: (appId) => api(`/lending/pipeline/result/${appId}`),

  // Registry
  registryVersions: () => api('/registry/versions'),
  registryVersion: (entryId) => api(`/registry/versions/${entryId}`),
  createRegistryEntry: (body) => api('/registry/versions', { method: 'POST', body }),
  submitRegistryEntry: (entryId) => api(`/registry/versions/${entryId}/submit`, { method: 'POST' }),
  approveRegistryEntry: (entryId) => api(`/registry/versions/${entryId}/approve`, { method: 'POST' }),
  rejectRegistryEntry: (entryId) => api(`/registry/versions/${entryId}/reject`, { method: 'POST' }),
  registryDiff: (a, b) => api(`/registry/diff?a=${a}&b=${b}`),
  registryContexts: () => api('/registry/context'),
  registrySnapshot: () => api('/registry/snapshot', { method: 'POST' }),
  registrySnapshots: () => api('/registry/snapshots'),
  registryBootstrap: () => api('/registry/bootstrap', { method: 'POST' }),
  releaseChecklist: () => api('/releases/checklist'),
  releaseExperiments: (experimentClass) => api(`/releases/experiments${experimentClass ? `?experiment_class=${encodeURIComponent(experimentClass)}` : ''}`),
  startReleaseExperiment: (body) => api('/releases/experiments', { method: 'POST', body }),
  promoteExperiment: (runId, stage) => api(`/releases/experiments/${runId}/promote`, { method: 'POST', body: { stage } }),

  // Admin
  createUser: (body) => api('/auth/users', { method: 'POST', body }),
};

export function fmtCurrency(n) {
  if (n == null || isNaN(n)) return '—';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n);
}

export function extractInsurance(job) {
  if (!job || job.status === 'processing') {
    return { decision: null, premium: null, bundleId: null, memo: '', quote: {}, insuredName: '' };
  }
  if (job.status === 'failed') {
    return { decision: null, premium: null, bundleId: null, memo: job.error || '', quote: {}, insuredName: '' };
  }
  const r = job.results || {};
  const memo = r.memo || r.underwriting_memo || {};
  const quote = r.quote || {};
  const rawDecision = r.ai_decision || memo.decision || memo?.recommendation?.action || r.decision;
  const decision = rawDecision ? String(rawDecision).toLowerCase() : null;
  return {
    decision,
    premium: quote.adjusted_premium ?? quote.base_premium ?? null,
    bundleId: r.bundle_id,
    insuredName: r.insured_name || memo.insured_name || '',
    memo: memo.summary || memo.executive_summary || memo.narrative || '',
    memoData: memo,
    quote,
    workflowState: r.workflow_state,
  };
}

export function extractMortgage(job) {
  const r = job?.results || {};
  const s = r.summary || r.pipeline_summary || r;
  const rate = s?.rate_quote || r.rate_quote || {};
  const memo = r.memo || s.memo || {};
  return {
    decision: s?.decision || s?.recommendation || r.decision || memo.decision,
    rate: rate?.adjusted_rate ?? rate?.note_rate ?? rate?.interest_rate ?? null,
    payment: rate?.monthly_pi ?? rate?.monthly_payment ?? rate?.pitia ?? null,
    dti: s?.dti_ratio ?? memo.dti_ratio ?? rate?.dti,
    ltv: s?.ltv_ratio ?? memo.ltv_ratio,
    eligible: rate?.eligible,
    ineligibilityReasons: rate?.ineligibility_reasons || [],
    violations: s?.compliance_violations || r.compliance_violations || [],
    memo: memo.executive_summary || memo.underwriting_summary || s?.underwriting_summary || s?.narrative || '',
    borrower: s?.borrower || memo.borrower_name,
  };
}
