import { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import { auth, endpoints } from '../lib/api';

const ROLE_BADGE = {
  viewer: 'bg-slate-500/15 text-slate-300',
  underwriter: 'bg-blue-500/15 text-blue-300',
  staff_uw: 'bg-violet-500/15 text-violet-300',
  licensed_uw: 'bg-purple-500/15 text-purple-300',
  admin: 'bg-amber-500/15 text-amber-300',
  cuo: 'bg-red-500/15 text-red-300',
};

export default function SettingsPage({ onLogin, onAuthReset }) {
  const { user } = useOutletContext() || {};
  const [roles, setRoles] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [companyName, setCompanyName] = useState('');
  const [companyError, setCompanyError] = useState('');

  useEffect(() => {
    endpoints.roles().then((d) => setRoles(d.roles || [])).catch(() => {});
    endpoints.insuranceCompanies().then((d) => setCompanies(d.companies || [])).catch(() => {});
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
        <div className="glass-card">
          <div className="border-b border-white/[0.04] px-6 py-4">
            <h2 className="font-semibold">Insurance company panel</h2>
            <p className="mt-0.5 text-sm text-slate-400">
              Choose whose paper a file is for. These are your appointed companies — not live appointments Rytera claims.
            </p>
          </div>
          <div className="divide-y divide-white/[0.04]">
            {companies.map((c) => (
              <div key={c.id} className="flex items-center justify-between gap-3 px-6 py-3">
                <div>
                  <p className="text-sm font-medium text-slate-200">{c.name}</p>
                  <p className="text-[11px] text-slate-500">{c.kind === 'demo' ? 'Demo book' : 'Appointed panel'}{c.naic ? ` · NAIC ${c.naic}` : ''}</p>
                </div>
              </div>
            ))}
            {!companies.length && <p className="px-6 py-4 text-sm text-slate-500">No companies loaded.</p>}
          </div>
          <form
            className="flex flex-wrap gap-2 border-t border-white/[0.04] px-6 py-4"
            onSubmit={async (e) => {
              e.preventDefault();
              setCompanyError('');
              try {
                const created = await endpoints.addInsuranceCompany({ name: companyName });
                setCompanies((prev) => [...prev.filter((c) => c.id !== created.id), created]);
                setCompanyName('');
              } catch (err) {
                setCompanyError(err.message || 'Could not add company');
              }
            }}
          >
            <input
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="Add appointed company"
              className="input-field min-w-[12rem] flex-1 text-sm"
            />
            <button type="submit" className="btn-secondary btn-sm text-sm" disabled={!companyName.trim()}>Add</button>
            {companyError ? <p className="w-full text-xs text-amber-400">{companyError}</p> : null}
          </form>
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
