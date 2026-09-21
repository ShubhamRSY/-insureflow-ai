import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  Shield, Home, Settings, LogOut, RefreshCw, Menu, X,
  BarChart3, FileCheck, Briefcase, ShieldCheck, Library, Lock, Cable, AlertTriangle, LayoutDashboard,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { auth } from '../lib/api';
import { RAIL_GROUPS, deriveActiveGroupId } from '../lib/railNav';
import { displayText } from '../lib/safe';
import { useStateContext } from '../lib/useStateContext';
import BrandMark from './BrandMark';
import ThemeToggle from './ThemeToggle';
import StateSelector from './StateSelector';
import ErrorBoundary from './ErrorBoundary';
import OperatingModeBanner from './OperatingModeBanner';
import ToastContainer from './Toast';

const GROUP_ICONS = {
  home: LayoutDashboard,
  insurance: Shield,
  reference: Library,
  'mortgage-lending': Home,
  'uw-operations': Briefcase,
  'post-decision': FileCheck,
  analytics: BarChart3,
  governance: ShieldCheck,
  integrations: Cable,
  account: Settings,
};

const CRUMBS = [
  { prefix: '/reference/commercial', labels: [{ text: 'Reference', to: '/reference' }, 'Commercial insurance'] },
  { prefix: '/reference', labels: ['Reference', 'Notebooks'] },
  { prefix: '/insurance/sections', labels: [{ text: 'Insurance', to: '/insurance' }, 'Section'] },
  { prefix: '/insurance/general', labels: [{ text: 'Insurance', to: '/insurance' }, 'Personal Lines'] },
  { prefix: '/insurance/health', labels: [{ text: 'Insurance', to: '/insurance' }, 'Health Insurance'] },
  { prefix: '/insurance/life', labels: [{ text: 'Insurance', to: '/insurance' }, 'Life Insurance'] },
  { prefix: '/insurance/commercial', labels: [{ text: 'Insurance', to: '/insurance' }, 'Commercial Lines'] },
  { prefix: '/insurance/', labels: [{ text: 'Insurance', to: '/insurance' }] },
  { prefix: '/insurance', labels: ['Insurance'] },
  { prefix: '/line-uw', labels: ['UW Operations', 'Line UW Desk'] },
  { prefix: '/staff-uw', labels: ['UW Operations', 'Staff UW Desk'] },
  { prefix: '/uw-workbench', labels: ['UW Operations', 'UW Workbench'] },
  { prefix: '/uw-dashboard', labels: ['UW Operations', 'UW Dashboard'] },
  { prefix: '/prior-decisions', labels: ['UW Operations', 'Prior decisions'] },
  { prefix: '/mortgage', labels: ['Mortgage & Lending', 'Mortgage'] },
  { prefix: '/lending', labels: ['Mortgage & Lending', 'Lending'] },
  { prefix: '/workflow', labels: ['UW Operations', 'UW Sign-off'] },
  { prefix: '/queue', labels: ['UW Operations', 'Submission Queue'] },
  { prefix: '/issuance', labels: ['Post-Decision', 'Issuance'] },
  { prefix: '/monitoring', labels: ['Post-Decision', 'Policy Monitoring'] },
  { prefix: '/producer-comms', labels: ['Post-Decision', 'Producer Comms'] },
  { prefix: '/renewals', labels: ['Analytics', 'Renewals'] },
  { prefix: '/overrides', labels: ['Analytics', 'Override Analytics'] },
  { prefix: '/business-kpis', labels: ['Analytics', 'ROI & KPIs'] },
  { prefix: '/eval-trends', labels: ['Analytics', 'Eval Trends'] },
  { prefix: '/portfolio', labels: ['Analytics', 'Portfolio'] },
  { prefix: '/ratemaking', labels: ['Analytics', 'Ratemaking & Pricing'] },
  { prefix: '/authority', labels: ['Analytics', 'Authority Matrix'] },
  { prefix: '/market', labels: ['Analytics', 'Market Cycle'] },
  { prefix: '/pilot', labels: ['Governance', 'Pilot Lab'] },
  { prefix: '/registry', labels: ['Governance', 'Model Registry'] },
  { prefix: '/integrations', labels: ['Integrations'] },
  { prefix: '/webhooks', labels: ['Governance', 'Webhooks'] },
  { prefix: '/settings', labels: ['Account', 'Settings'] },
  { prefix: '/system', labels: ['System Health'] },
  { prefix: '/', labels: ['Overview'] },
];

function crumbsFor(pathname) {
  for (const c of CRUMBS) {
    if (c.prefix === '/' ? pathname === '/' : pathname.startsWith(c.prefix)) return c.labels;
  }
  return [];
}

export default function Layout({ health, pendingCount, onRefresh, onLogin, user, setUser, isLimited, welcomeMessage, onDismissWelcome }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { selectedState } = useStateContext();
  const crumbs = crumbsFor(pathname);

  const [activeGroupId, setActiveGroupId] = useState(() => deriveActiveGroupId(pathname));
  useEffect(() => {
    setActiveGroupId(deriveActiveGroupId(pathname));
  }, [pathname]);
  const activeGroup = RAIL_GROUPS.find((g) => g.id === activeGroupId) || RAIL_GROUPS[0];

  const logout = () => {
    auth.clear();
    setUser(null);
    navigate('/system');
  };

  return (
    <div className="flex min-h-screen bg-surface bg-mesh">
      {/* Sidebar */}
      <aside className={`fixed inset-y-0 left-0 z-50 flex lg:translate-x-0 ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex w-[60px] shrink-0 flex-col items-center border-r border-white/[0.06] bg-surface py-4">
          <button type="button" onClick={() => navigate('/')} aria-label="Rytera home" className="mb-4 h-8 w-8 rounded-lg">
            <BrandMark />
          </button>
          <nav className="flex flex-1 flex-col items-center gap-1 overflow-y-auto">
            {RAIL_GROUPS.map((group) => {
              const Icon = GROUP_ICONS[group.id];
              const isActive = group.id === activeGroupId;
              return (
                <button
                  key={group.id}
                  type="button"
                  title={group.label}
                  onClick={() => setActiveGroupId(group.id)}
                  className={`flex h-9 w-9 items-center justify-center rounded-lg transition ${
                    isActive ? 'bg-brand/[0.14] text-brand' : 'text-slate-500 hover:bg-white/[0.05] hover:text-slate-300'
                  }`}
                >
                  <Icon className="h-[17px] w-[17px]" />
                </button>
              );
            })}
          </nav>
        </div>

        <div className="flex w-[198px] shrink-0 flex-col border-r border-white/[0.06] bg-surface-raised">
          <div className="border-b border-white/[0.06] px-4 py-[19px]">
            <p className="font-display text-base font-semibold">{activeGroup.label}</p>
          </div>
          <div className="flex-1 space-y-0.5 overflow-y-auto p-2">
            {activeGroup.items.map((item) => {
              const isProtected = item.to !== '/' && item.to !== '/system' && !user;
              const isHubMatch = Boolean(item.hub && pathname.startsWith(item.hub));
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/' || item.to === '/insurance' || item.to === '/integrations'}
                  onClick={() => setMobileOpen(false)}
                  className={({ isActive }) => `nav-link ${isActive || isHubMatch ? 'nav-link-active' : ''}`}
                >
                  <span className="flex-1">{item.label}</span>
                  {item.tag && (
                    <span className={`rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide ${
                      item.tag === 'Live' ? 'text-verdigris' : 'text-slate-500'
                    }`}>
                      {item.tag}
                    </span>
                  )}
                  {item.badge && pendingCount > 0 && (
                    <span className="rounded-full bg-risk-red/20 px-2 py-0.5 text-[10px] font-bold text-risk-red">
                      {pendingCount}
                    </span>
                  )}
                  {isProtected && <Lock className="h-3 w-3 shrink-0 text-slate-600" />}
                </NavLink>
              );
            })}
          </div>
          <div className="border-t border-white/[0.06] p-3.5">
            {health && (
              <div className="mb-2.5 flex items-center gap-2 text-[11.5px] text-slate-400">
                <span className={`h-1.5 w-1.5 rounded-full ${health.overall === 'healthy' ? 'bg-verdigris' : health.overall === 'degraded' ? 'bg-risk-amber' : 'bg-risk-red'}`} />
                {displayText(health.overall)} · {displayText(health.llm_mode)}
              </div>
            )}
            {user ? (
              <div className="flex items-center gap-2">
                <div className="keep-white flex h-[26px] w-[26px] items-center justify-center rounded-full bg-brand text-[10.5px] font-bold text-surface">
                  {displayText(user.username)?.slice(0, 2).toUpperCase()}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[12.5px] font-medium">{displayText(user.username)}</p>
                  <p className="truncate text-[10px] text-slate-500">{displayText(user.role)}</p>
                </div>
                <button type="button" onClick={logout} className="rounded-lg p-1 text-slate-500 hover:bg-white/5 hover:text-slate-300">
                  <LogOut className="h-3.5 w-3.5" />
                </button>
              </div>
            ) : (
              <button type="button" onClick={onLogin} className="btn-primary w-full text-xs">Sign in</button>
            )}
          </div>
        </div>
      </aside>

      {mobileOpen && <div className="fixed inset-0 z-40 bg-black/60 lg:hidden" onClick={() => setMobileOpen(false)} />}

      {/* Main */}
      <div className="flex min-w-0 flex-1 flex-col lg:ml-[258px]">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-3 overflow-visible border-b border-white/[0.06] bg-surface/80 px-6 backdrop-blur-xl">
          <div className="flex min-w-0 items-center gap-3">
            <button type="button" className="rounded-lg p-2 lg:hidden" onClick={() => setMobileOpen(true)}>
              <Menu className="h-5 w-5" />
            </button>
            <nav className="hidden min-w-0 items-center gap-1.5 text-sm text-slate-400 md:flex" aria-label="Breadcrumb">
              <span className="flex items-center gap-1.5">
                <NavLink to="/" className="transition hover:text-slate-200">Dashboard</NavLink>
              </span>
              {crumbs.map((c, i) => {
                const isLast = i === crumbs.length - 1;
                const text = typeof c === 'object' ? c.text : c;
                const link = typeof c === 'object' ? c.to : null;
                return (
                  <span key={`${text}-${i}`} className="flex items-center gap-1.5 whitespace-nowrap">
                    <span className="text-slate-700">/</span>
                    {link && !isLast ? (
                      <NavLink to={link} className="transition hover:text-slate-200">{text}</NavLink>
                    ) : (
                      <span className={isLast ? 'font-semibold text-slate-200' : ''}>{text}</span>
                    )}
                  </span>
                );
              })}
            </nav>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <StateSelector compact />
            <ThemeToggle compact />
            <button type="button" onClick={onRefresh} className="btn-secondary btn-sm shrink-0 text-xs">
              <RefreshCw className="h-3.5 w-3.5" /> Refresh
            </button>
          </div>
        </header>

        <main className="flex-1 p-6 lg:p-8">
          {!selectedState && (
            <div className="fixed right-6 top-20 z-50 w-[380px] rounded-2xl border border-white/10 bg-surface-raised shadow-2xl shadow-black/40">
              <div className="flex items-center gap-3 border-b border-white/[0.08] px-5 py-4">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-red-500/15">
                  <AlertTriangle className="h-4.5 w-4.5 text-red-400" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-semibold text-white">Confirm your operating state</p>
                  <p className="text-xs text-slate-400">Required before running a pipeline</p>
                </div>
                <button type="button" onClick={() => {}} className="text-slate-500 hover:text-slate-300" title="Dismiss after selecting">
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="px-5 py-4 space-y-3">
                <p className="text-xs leading-relaxed text-slate-300">
                  Our servers are based in the USA. State selection affects compliance and data handling rules.
                  Choose your state before proceeding.
                </p>
                <StateSelector compact />
              </div>
            </div>
          )}
          {welcomeMessage && (
            <div className="mb-4 flex items-start gap-3 rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
              <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
              <span className="flex-1">{welcomeMessage}</span>
              <button type="button" onClick={onDismissWelcome} className="shrink-0 rounded-lg p-1 text-amber-400/60 hover:text-amber-200">
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          )}
          <OperatingModeBanner />
          <ErrorBoundary resetKey={pathname}>
            <Outlet context={{ user, onLogin }} />
          </ErrorBoundary>
        </main>

        <footer className="border-t border-white/[0.06] px-6 py-3 text-center text-xs text-slate-400">
          Rytera™ · <a href="https://ryterainc.com" className="text-slate-500 hover:text-slate-400">ryterainc.com</a>
          {' · '}Rytera is a trademark of Rytera, Inc. All rights reserved.
        </footer>
        <ToastContainer />
      </div>
    </div>
  );
}
