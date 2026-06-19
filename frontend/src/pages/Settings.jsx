import { useOutletContext } from 'react-router-dom';
import { auth, endpoints } from '../lib/api';

export default function SettingsPage({ onLogin, onAuthReset }) {
  const { user } = useOutletContext() || {};

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
    <div className="mx-auto max-w-md space-y-6 animate-fade-in">
      <h1 className="text-3xl font-bold tracking-tight">Settings</h1>

      {user ? (
        <>
          <div className="glass-card divide-y divide-white/[0.04]">
            {[
              ['Username', user.username],
              ['Role', user.role],
              ['Organization', user.org_id],
            ].map(([label, val]) => (
              <div key={label} className="flex justify-between px-6 py-4">
                <span className="text-sm text-slate-400">{label}</span>
                <span className="text-sm font-medium">{val}</span>
              </div>
            ))}
          </div>
          <button type="button" onClick={() => { auth.clear(); window.location.reload(); }} className="btn-secondary w-full">
            Sign Out
          </button>
        </>
      ) : (
        <div className="glass-card p-6 text-center">
          <p className="text-slate-400">Not signed in</p>
          <button type="button" onClick={onLogin} className="btn-primary mt-4">Sign In</button>
        </div>
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
