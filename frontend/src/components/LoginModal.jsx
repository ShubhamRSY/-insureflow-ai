import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { endpoints, auth } from '../lib/api';
import PasswordInput from './PasswordInput';

export default function LoginModal({ open, onClose, onSuccess }) {
  const [mode, setMode] = useState('login');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [setupRequired, setSetupRequired] = useState(false);
  const [ssoEnabled, setSsoEnabled] = useState(false);
  const [ssoRequired, setSsoRequired] = useState(false);
  const [allowRegister, setAllowRegister] = useState(true);

  useEffect(() => {
    if (!open) return;
    endpoints.authStatus()
      .then((s) => {
        setSetupRequired(s.setup_required);
        setMode(s.setup_required ? 'setup' : 'login');
        setSsoEnabled(Boolean(s.sso?.enabled));
        setSsoRequired(Boolean(s.sso_required));
        setAllowRegister(s.allow_open_registration !== false && !s.sso_required);
        setError('');
        setSuccess('');
      })
      .catch(() => setMode('login'));
  }, [open]);

  if (!open) return null;

  const handleSso = async () => {
    setLoading(true);
    setError('');
    try {
      const r = await endpoints.ssoLogin();
      if (!r.authorize_url) throw new Error('SSO is not configured');
      window.location.assign(r.authorize_url);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      const fd = new FormData(e.target);
      const username = String(fd.get('username') || '').trim();
      const password = String(fd.get('password') || '');
      const token = await endpoints.login(username, password);
      auth.token = token.access_token;
      const me = await endpoints.me();
      auth.user = me;
      onSuccess(me);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSetup = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      const fd = new FormData(e.target);
      const username = String(fd.get('username') || '').trim();
      const password = String(fd.get('password') || '');
      const email = String(fd.get('email') || '').trim();
      const full_name = String(fd.get('full_name') || username).trim();
      const company_name = String(fd.get('company_name') || 'Default Organization').trim() || 'Default Organization';

      await endpoints.setup({ username, password, full_name, email, company_name, role: 'admin' });

      const token = await endpoints.login(username, password);
      auth.token = token.access_token;
      const me = await endpoints.me();
      auth.user = me;
      onSuccess(me);
      onClose();
    } catch (err) {
      const msg = err.message || 'Setup failed';
      if (msg.toLowerCase().includes('already exists')) {
        setSetupRequired(false);
        setMode('login');
        setError('An admin account already exists. Sign in instead.');
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      const fd = new FormData(e.target);
      const username = String(fd.get('username') || '').trim();
      const password = String(fd.get('password') || '');
      const role = String(fd.get('role') || 'viewer');

      await endpoints.register({ username, password, role });

      setSuccess(`Account created! Sign in as "${username}".`);
      setTimeout(() => setMode('login'), 1200);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm animate-fade-in">
      <div className="glass-card relative w-full max-w-md p-8 animate-slide-up">
        <button type="button" onClick={onClose} className="absolute right-4 top-4 rounded-lg p-1 text-slate-500 hover:text-slate-300">
          <X className="h-5 w-5" />
        </button>

        {mode === 'setup' ? (
          <>
            <h2 className="text-2xl font-bold tracking-tight">First-time Setup</h2>
            <p className="mt-1 text-sm text-slate-400">Create the admin account to get started</p>
            {error && <p className="mt-4 rounded-xl bg-red-500/10 px-3 py-2 text-sm text-red-400">{error}</p>}
            <form onSubmit={handleSetup} className="mt-6 space-y-4">
              <input name="username" placeholder="Username" required className="input-field" autoComplete="username" />
              <input name="email" type="email" placeholder="Email address" required className="input-field" autoComplete="email" />
              <input name="full_name" placeholder="Full name (optional)" className="input-field" />
              <input name="company_name" placeholder="Company / Organization" className="input-field" defaultValue="Default Organization" />
              <PasswordInput placeholder="Password" autoComplete="new-password" />
              <button type="submit" disabled={loading} className="btn-primary w-full">{loading ? 'Creating…' : 'Create Admin & Sign In'}</button>
            </form>
            <div className="mt-4 border-t border-slate-700 pt-4">
              <p className="text-xs text-slate-500 mb-2">Stuck? Clear old data and start fresh:</p>
              <button
                type="button"
                onClick={async () => {
                  try {
                    await endpoints.clearStaleSession();
                    localStorage.clear();
                    sessionStorage.clear();
                    setError('');
                    setSuccess('Cleared. Fill in the form above to create your admin.');
                  } catch (err) {
                    setError(err.message || 'Could not clear — accounts may already exist. Try logging in.');
                  }
                }}
                className="w-full rounded-xl border border-slate-600 px-3 py-2 text-xs text-slate-400 hover:border-red-500 hover:text-red-400 transition-colors"
              >
                Clear old login data
              </button>
            </div>
          </>
        ) : mode === 'register' ? (
          <>
            <h2 className="text-2xl font-bold tracking-tight">Create Account</h2>
            <p className="mt-1 text-sm text-slate-400">Sign up as an underwriter or viewer</p>
            <form onSubmit={handleRegister} className="mt-6 space-y-4">
              <input name="username" placeholder="Username" required className="input-field" autoComplete="username" />
              <PasswordInput placeholder="Password" autoComplete="new-password" />
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Role</label>
                <select name="role" className="input-field">
                  <option value="viewer">Viewer (read-only)</option>
                  <option value="underwriter">Underwriter (run pipelines)</option>
                </select>
              </div>
              <button type="submit" disabled={loading} className="btn-primary w-full">{loading ? 'Creating…' : 'Create Account'}</button>
            </form>
            <p className="mt-4 text-center text-xs text-slate-500">
              Already have an account?{' '}
              <button type="button" onClick={() => { setMode('login'); setError(''); setSuccess(''); }} className="text-brand-light underline">Sign In</button>
            </p>
          </>
        ) : (
          <>
            <h2 className="text-2xl font-bold tracking-tight">Welcome back</h2>
            <p className="mt-1 text-sm text-slate-400">
              {ssoRequired ? 'Sign in with your organization identity provider' : 'Sign in to run pipelines and view results'}
            </p>

            {error && <p className="mt-4 rounded-xl bg-red-500/10 px-3 py-2 text-sm text-red-400">{error}</p>}
            {success && <p className="mt-4 rounded-xl bg-emerald-500/10 px-3 py-2 text-sm text-emerald-400">{success}</p>}

            {ssoEnabled && (
              <button type="button" disabled={loading} onClick={handleSso} className="btn-primary mt-6 w-full">
                {loading ? 'Redirecting…' : 'Sign in with SSO'}
              </button>
            )}

            {!ssoRequired && (
            <form onSubmit={handleLogin} className="mt-6 space-y-4">
              {ssoEnabled && <p className="text-center text-xs text-slate-500">or use a local account</p>}
              <div>
                <label htmlFor="login-username" className="mb-1.5 block text-xs font-medium text-slate-400">Username or email</label>
                <input
                  id="login-username"
                  name="username"
                  type="text"
                  required
                  placeholder="Username or email"
                  className="input-field"
                  autoComplete="username"
                />
              </div>
              <div>
                <label htmlFor="login-password" className="mb-1.5 block text-xs font-medium text-slate-400">Password</label>
                <PasswordInput id="login-password" autoComplete="current-password" placeholder="" />
              </div>
              <button type="submit" disabled={loading} className="btn-primary w-full">{loading ? 'Signing in…' : 'Sign In'}</button>
            </form>
            )}

            {allowRegister && (
            <p className="mt-4 text-center text-xs text-slate-500">
              No account?{' '}
              <button type="button" onClick={() => { setMode('register'); setError(''); setSuccess(''); }} className="text-brand-light underline">Create one</button>
            </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
