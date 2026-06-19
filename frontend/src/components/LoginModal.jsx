import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { endpoints, auth } from '../lib/api';
import PasswordInput from './PasswordInput';

export default function LoginModal({ open, onClose, onSuccess }) {
  const [tab, setTab] = useState('login');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [setupRequired, setSetupRequired] = useState(false);

  useEffect(() => {
    if (!open) return;
    endpoints.authStatus()
      .then((s) => {
        setSetupRequired(s.setup_required);
        setTab(s.setup_required ? 'setup' : 'login');
      })
      .catch(() => setTab('login'));
  }, [open]);

  if (!open) return null;

  const handleResetCredentials = async () => {
    if (!window.confirm('Delete ALL login accounts and browser session?')) return;
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      window.location.href = '/auth/reset';
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
      const org_id = String(fd.get('org_id') || 'default').trim() || 'default';
      const full_name = String(fd.get('full_name') || username).trim();

      await endpoints.setup({
        username,
        password,
        full_name,
        org_id,
        role: 'admin',
      });

      // Auto sign-in with the same credentials (avoids typo after setup)
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
        setTab('login');
        setError('An admin account already exists. Sign in instead.');
      } else {
        setError(msg);
      }
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
        <h2 className="text-2xl font-bold tracking-tight">Welcome back</h2>
        <p className="mt-1 text-sm text-slate-400">Sign in to run pipelines and view results</p>

        <div className="mt-6 flex gap-2">
          {setupRequired && (
            <button
              type="button"
              onClick={() => { setTab('setup'); setError(''); setSuccess(''); }}
              className={`flex-1 rounded-xl py-2 text-sm font-semibold transition ${tab === 'setup' ? 'bg-brand/15 text-brand-light ring-1 ring-brand/30' : 'text-slate-400 hover:bg-white/5'}`}
            >
              First-time Setup
            </button>
          )}
          <button
            type="button"
            onClick={() => { setTab('login'); setError(''); setSuccess(''); }}
            className={`${setupRequired ? 'flex-1' : 'w-full'} rounded-xl py-2 text-sm font-semibold transition ${tab === 'login' ? 'bg-brand/15 text-brand-light ring-1 ring-brand/30' : 'text-slate-400 hover:bg-white/5'}`}
          >
            Sign In
          </button>
        </div>

        {!setupRequired && tab === 'login' && (
          <p className="mt-3 text-xs text-slate-500">
            <button type="button" className="text-red-400 underline" onClick={handleResetCredentials}>
              Reset all sign-in data
            </button>
          </p>
        )}

        {error && <p className="mt-4 rounded-xl bg-red-500/10 px-3 py-2 text-sm text-red-400">{error}</p>}
        {success && <p className="mt-4 rounded-xl bg-emerald-500/10 px-3 py-2 text-sm text-emerald-400">{success}</p>}

        {tab === 'login' ? (
          <form onSubmit={handleLogin} className="mt-6 space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-400">Username</label>
              <input name="username" required className="input-field" autoComplete="username" />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-400">Password</label>
              <PasswordInput autoComplete="current-password" />
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full">{loading ? 'Signing in…' : 'Sign In'}</button>
          </form>
        ) : (
          <form onSubmit={handleSetup} className="mt-6 space-y-4">
            <input name="username" placeholder="Username" required className="input-field" autoComplete="username" />
            <input name="full_name" placeholder="Full name (optional)" className="input-field" />
            <input name="org_id" placeholder="Organization ID (default)" className="input-field" />
            <PasswordInput placeholder="Password" autoComplete="new-password" />
            <button type="submit" disabled={loading} className="btn-primary w-full">{loading ? 'Creating…' : 'Create Admin & Sign In'}</button>
          </form>
        )}
      </div>
    </div>
  );
}
