/** InsureFlow API client */

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
  get isLoggedIn() { return !!this.token; },
};

export async function api(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  if (opts.body && !(opts.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(opts.body);
  }
  if (auth.token) headers['Authorization'] = `Bearer ${auth.token}`;

  const res = await fetch(path, { ...opts, headers });
  let data = null;
  const ct = res.headers.get('content-type') || '';
  if (ct.includes('application/json')) {
    try { data = await res.json(); } catch { data = null; }
  } else if (res.status !== 204) {
    data = await res.text();
  }

  if (!res.ok) {
    const msg = (data && data.detail) ? (typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)) : `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return data;
}

export const endpoints = {
  diagnostics: () => api('/system/diagnostics'),
  presets: () => api('/api/demo/presets'),
  overview: () => api('/api/dashboard/overview'),
  login: (username, password) => api('/auth/login', { method: 'POST', body: { username, password } }),
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
  mortgageProducts: () => api('/mortgage/products'),

  pendingWorkflow: () => api('/pipeline/workflow/pending'),
  workflow: (bundleId) => api(`/pipeline/workflow/${bundleId}`),
  signOff: (bundleId, body) => api(`/pipeline/workflow/${bundleId}/sign-off`, { method: 'POST', body }),
  bind: (bundleId, body) => api(`/pipeline/workflow/${bundleId}/bind`, { method: 'POST', body }),
  audit: (bundleId) => api(`/pipeline/audit/${bundleId}`),
  ratingProducts: () => api('/pipeline/rating/products'),
};
