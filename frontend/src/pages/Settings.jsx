import { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import { auth, endpoints } from '../lib/api';

const ROLE_BADGE = {
  viewer: 'bg-slate-500/15 text-slate-300',
  underwriter: 'bg-blue-500/15 text-blue-300',
  licensed_uw: 'bg-purple-500/15 text-purple-300',
  admin: 'bg-amber-500/15 text-amber-300',
  cuo: 'bg-red-500/15 text-red-300',
};

export default function SettingsPage({ onLogin, onAuthReset }) {
  const { user } = useOutletContext() || {};
  const [roles, setRoles] = useState([]);

  useEffect(() => {
    endpoints.roles().then((d) => setRoles(d.roles || [])).catch(() => {});
  }, []);

  const handleReset = async () => {
    if (!window.confirm('Delete ALL login accounts on this server? You will need to run First-time Setup again.')) {
      return;
    }
    try {
      await endpoints.authReset();
      auth.wipeSession();
      onAuthReset?.();
      window.location.href = '/dashboard';
    } catch (e) {
      alert(e.message);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6 animate-fade-in">
      <h1 className="text-3xl font-bold tracking-tight">Settings</h1>

      {user ? (
        <div className="glass-card divide-y divide-white/[0.04]">
          {[
            ['Username', user.username],
            ['Role', <span key="role" className={`rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase ${ROLE_BADGE[user.role] || 'bg-slate-500/15 text-slate-300'}`}>{user.role}</span>],
            ['Organization', user.org_id],
          ].map(([label, val]) => (
            <div key={label} className="flex justify-between px-6 py-4">
              <span className="text-sm text-slate-400">{label}</span>
              <span className="text-sm font-medium">{val}</span>
            </div>
          ))}
        </div>
      ) : (
        <div className="glass-card p-6 text-center">
          <p className="text-slate-400">Not signed in</p>
          <button type="button" onClick={onLogin} className="btn-primary mt-4">Sign In</button>
        </div>
      )}

      {roles.length > 0 && (
        <div className="glass-card">
          <div className="border-b border-white/[0.04] px-6 py-4">
            <h2 className="font-semibold">Role-Based Access Control</h2>
            <p className="mt-0.5 text-sm text-slate-400">Each role inherits permissions from all lower levels</p>
          </div>
          <div className="divide-y divide-white/[0.04]">
            {roles.map((r) => (
              <div key={r.role} className="flex items-center gap-4 px-6 py-4">
                <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase ${ROLE_BADGE[r.role] || 'bg-slate-500/15 text-slate-300'}`}>{r.role.replace('_', ' ')}</span>
                <span className="text-xs text-slate-500">Lv.{r.level}</span>
                <span className="flex-1 text-sm text-slate-400">{r.description}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {user && (
        <button type="button" onClick={() => { auth.clear(); window.location.reload(); }} className="btn-secondary w-full">
          Sign Out
        </button>
      )}

      <div className="glass-card border-red-500/20 p-6">
        <h2 className="font-semibold text-red-300">Reset credentials</h2>
        <p className="mt-2 text-sm text-slate-400">
          Clears every account on this server instance so you can run First-time Setup again.
          Does not affect saved underwriting jobs.
        </p>
        <button type="button" onClick={handleReset} className="mt-4 w-full rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-2.5 text-sm font-semibold text-red-300 transition hover:bg-red-500/20">
          Clear all login accounts
        </button>
      </div>
    </div>
  );
}
