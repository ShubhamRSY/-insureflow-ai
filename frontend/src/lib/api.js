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
  insuranceJobs: () => api('/pipeline/jobs'),
  insuranceJob: (id) => api(`/pipeline/jobs/${id}`),
  runInsurance: (body) => api('/pipeline/run', { method: 'POST', body }),
  runInsuranceDemo: (preset) => api(`/api/demo/insurance/${preset}`, { method: 'POST' }),
  mortgageJobs: () => api('/mortgage/pipeline/jobs'),
  mortgageJob: (id) => api(`/mortgage/pipeline/jobs/${id}`),
  runMortgage: (body) => api('/mortgage/pipeline/run', { method: 'POST', body }),
  runMortgageDemo: (preset) => api(`/api/demo/mortgage/${preset}`, { method: 'POST' }),
  pendingWorkflow: () => api('/pipeline/workflow/pending'),
  signOff: (bundleId, body) => api(`/pipeline/workflow/${bundleId}/sign-off`, { method: 'POST', body }),
  insuranceSources: () => api('/api/insurance/sources'),
  pullInsuranceSource: (sourceId, body = {}) => api(`/api/insurance/sources/${sourceId}/pull`, { method: 'POST', body }),
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
