import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, Shield, Home, Activity, ClipboardCheck, Settings, LogOut, RefreshCw, Menu, X,
  FileText, Users, BarChart3, BookOpen, Wallet, Layers, Link2, LineChart, Search, Database,
} from 'lucide-react';
import { useState } from 'react';
import { auth, endpoints } from '../lib/api';
import { Badge } from './ui';

const nav = [
  { to: '/', icon: LayoutDashboard, label: 'Overview' },
  { to: '/system', icon: Activity, label: 'System Health' },
  { section: 'Underwriting' },
  { to: '/insurance', icon: Shield, label: 'Insurance', color: 'text-insurance' },
  { to: '/mortgage', icon: Home, label: 'Mortgage', color: 'text-mortgage' },
  { to: '/lending', icon: Wallet, label: 'Lending', color: 'text-emerald-400' },
  { to: '/workflow', icon: ClipboardCheck, label: 'UW Sign-off', badge: true },
  { to: '/queue', icon: Search, label: 'Queue' },
  { section: 'Analytics' },
  { to: '/renewals', icon: FileText, label: 'Renewals' },
  { to: '/overrides', icon: LineChart, label: 'Override Analytics' },
  { to: '/eval-trends', icon: Activity, label: 'Eval Trends' },
  { to: '/portfolio', icon: Layers, label: 'Portfolio' },
  { to: '/authority', icon: Users, label: 'Authority Matrix' },
  { to: '/market', icon: BarChart3, label: 'Market Cycle' },
  { section: 'Governance' },
  { to: '/registry', icon: BookOpen, label: 'Model Registry' },
  { to: '/integrations', icon: Link2, label: 'Integrations' },
  { to: '/webhooks', icon: Database, label: 'Webhooks' },
  { section: 'Account' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

export default function Layout({ health, pendingCount, onRefresh, onLogin, user, setUser }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();

  const logout = () => {
    auth.clear();
    setUser(null);
    navigate('/system');
  };

  return (
    <div className="flex min-h-screen bg-surface bg-mesh">
      {/* Sidebar */}
      <aside className={`fixed inset-y-0 left-0 z-50 flex w-[272px] flex-col border-r border-white/[0.06] bg-surface-raised/95 backdrop-blur-xl transition-transform lg:translate-x-0 ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex items-center gap-3 border-b border-white/[0.06] px-5 py-5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-brand to-indigo-600 shadow-glow">
            <Shield className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold tracking-tight">Rytera</h1>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">AI Underwriting</p>
          </div>
          <button type="button" className="ml-auto lg:hidden" onClick={() => setMobileOpen(false)}>
            <X className="h-5 w-5 text-slate-400" />
          </button>
        </div>

        <nav className="flex-1 space-y-0.5 overflow-y-auto p-3">
          {nav.map((item, i) => {
            if (item.section) {
              return (
                <p key={i} className="px-3 pb-1 pt-4 text-[10px] font-bold uppercase tracking-widest text-slate-600">
                  {item.section}
                </p>
              );
            }
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}
              >
                <Icon className={`h-[18px] w-[18px] ${item.color || ''}`} />
                <span className="flex-1">{item.label}</span>
                {item.badge && pendingCount > 0 && (
                  <span className="rounded-full bg-red-500/20 px-2 py-0.5 text-[10px] font-bold text-red-400">
                    {pendingCount}
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>

        <div className="border-t border-white/[0.06] p-4">
          {health && (
            <div className="mb-3 flex items-center gap-2 rounded-xl bg-surface-overlay px-3 py-2 text-xs text-slate-400">
              <span className={`h-2 w-2 rounded-full ${health.overall === 'healthy' ? 'bg-emerald-400' : health.overall === 'degraded' ? 'bg-amber-400' : 'bg-red-400'}`} />
              {health.overall} · {health.llm_mode}
            </div>
          )}
          {user ? (
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-brand to-indigo-500 text-xs font-bold">
                {user.username?.slice(0, 2).toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{user.username}</p>
                <p className="truncate text-[10px] text-slate-500">{user.role} · {user.org_id}</p>
              </div>
              <button type="button" onClick={logout} className="rounded-lg p-1.5 text-slate-500 hover:bg-white/5 hover:text-slate-300">
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <button type="button" onClick={onLogin} className="btn-primary w-full text-sm">Sign In</button>
          )}
        </div>
      </aside>

      {mobileOpen && <div className="fixed inset-0 z-40 bg-black/60 lg:hidden" onClick={() => setMobileOpen(false)} />}

      {/* Main */}
      <div className="flex min-w-0 flex-1 flex-col lg:ml-[272px]">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-white/[0.06] bg-surface/80 px-6 backdrop-blur-xl">
          <div className="flex items-center gap-3">
            <button type="button" className="rounded-lg p-2 lg:hidden" onClick={() => setMobileOpen(true)}>
              <Menu className="h-5 w-5" />
            </button>
          </div>
          <button type="button" onClick={onRefresh} className="btn-secondary btn-sm text-xs">
            <RefreshCw className="h-3.5 w-3.5" /> Refresh
          </button>
        </header>

        <main className="flex-1 p-6 lg:p-8">
          <Outlet context={{ user, onLogin }} />
        </main>

        <footer className="border-t border-white/[0.06] px-6 py-3 text-center text-[10px] text-slate-600">
          Rytera™ · <a href="https://rytera.ai" className="text-slate-500 hover:text-slate-400">rytera.ai</a>
          {' · '}Rytera is a trademark of Rytera, Inc. All rights reserved.
        </footer>
      </div>
    </div>
  );
}
