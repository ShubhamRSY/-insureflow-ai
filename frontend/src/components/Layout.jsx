import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, Shield, Home, Activity, ClipboardCheck, Settings, LogOut, RefreshCw, Menu, X,
  FileText, Users, BarChart3, BookOpen, Wallet, Layers, Link2, LineChart, Search, Database, FlaskConical,
  FileCheck, MessagesSquare, Radar, Briefcase, Building2, Calculator, ChevronDown, ChevronRight, Plus,
  ShieldCheck, Library,
} from 'lucide-react';
import { useState } from 'react';
import { auth } from '../lib/api';

const nav = [
  { to: '/', icon: LayoutDashboard, label: 'Overview' },
  { to: '/system', icon: Activity, label: 'System Health' },
  { section: 'Insurance' },
  {
    to: '/insurance',
    icon: Shield,
    label: 'Insurance',
    color: 'text-insurance',
    defaultOpen: true,
    scrollChildren: true,
    children: [
      { to: '/insurance', label: 'All 12 sections' },
      { to: '/insurance/sections/life', label: '1. Life', tag: 'Live' },
      { to: '/insurance/sections/health', label: '2. Health', tag: 'Catalog' },
      { to: '/insurance/sections/general', label: '3. General / Non-Life', tag: 'Catalog' },
      { to: '/insurance/sections/commercial', label: '4. Business / Commercial', tag: 'Live' },
      { to: '/insurance/sections/specialty', label: '5. Other / Specialty', tag: 'Catalog' },
      { to: '/insurance/sections/provider', label: '6. By Provider Type', tag: 'Catalog' },
      { to: '/insurance/sections/engineering', label: '7. Engineering', tag: 'Catalog' },
      { to: '/insurance/sections/aviation', label: '8. Aviation', tag: 'Catalog' },
      { to: '/insurance/sections/fidelity', label: '9. Fidelity & Burglary', tag: 'Catalog' },
      { to: '/insurance/sections/catastrophe', label: '10. Catastrophe', tag: 'Catalog' },
      { to: '/insurance/sections/niche-liability', label: '11. Niche Liability', tag: 'Catalog' },
      { to: '/insurance/sections/warranty-financial-emerging', label: '12. Warranty / Financial / Emerging', tag: 'Catalog' },
    ],
  },
  { section: 'Reference' },
  {
    to: '/reference',
    icon: Library,
    label: 'Reference notebooks',
    color: 'text-slate-300',
    defaultOpen: true,
    children: [
      { to: '/reference/commercial', label: 'Commercial insurance' },
    ],
  },
  { section: 'Mortgage & Lending' },
  { to: '/mortgage', icon: Home, label: 'Mortgage', color: 'text-mortgage' },
  { to: '/lending', icon: Wallet, label: 'Lending', color: 'text-lending' },
  { section: 'UW Operations' },
  { to: '/line-uw', icon: Briefcase, label: 'Line UW Desk', color: 'text-sky-400' },
  { to: '/staff-uw', icon: Building2, label: 'Staff UW Desk', color: 'text-violet-400' },
  { to: '/workflow', icon: ClipboardCheck, label: 'UW Sign-off', badge: true },
  { to: '/uw-workbench', icon: ShieldCheck, label: 'UW Workbench', color: 'text-teal-400' },
  { to: '/queue', icon: Search, label: 'Queue' },
  { section: 'Post-Decision' },
  { to: '/issuance', icon: FileCheck, label: 'Issuance', color: 'text-emerald-400' },
  { to: '/monitoring', icon: Radar, label: 'Policy Monitoring', color: 'text-violet-400' },
  { to: '/producer-comms', icon: MessagesSquare, label: 'Producer Comms', color: 'text-sky-400' },
  { section: 'Analytics' },
  { to: '/renewals', icon: FileText, label: 'Renewals' },
  { to: '/overrides', icon: LineChart, label: 'Override Analytics' },
  { to: '/business-kpis', icon: BarChart3, label: 'Business KPIs', color: 'text-brand' },
  { to: '/eval-trends', icon: Activity, label: 'Eval Trends' },
  { to: '/portfolio', icon: Layers, label: 'Portfolio' },
  { to: '/ratemaking', icon: Calculator, label: 'Ratemaking & Pricing', color: 'text-brand' },
  { to: '/authority', icon: Users, label: 'Authority Matrix' },
  { to: '/market', icon: BarChart3, label: 'Market Cycle' },
  { section: 'Governance' },
  { to: '/pilot', icon: FlaskConical, label: 'Pilot Lab', color: 'text-amber-400' },
  { to: '/registry', icon: BookOpen, label: 'Model Registry' },
  { to: '/integrations', icon: Link2, label: 'Integrations' },
  { to: '/webhooks', icon: Database, label: 'Webhooks' },
  { section: 'Account' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

const CRUMBS = [
  { prefix: '/reference/commercial', labels: ['Reference', 'Commercial insurance'] },
  { prefix: '/reference', labels: ['Reference', 'Notebooks'] },
  { prefix: '/insurance/sections', labels: ['Insurance', 'Section'] },
  { prefix: '/insurance/general', labels: ['Insurance', 'General / Non-Life'] },
  { prefix: '/insurance/health', labels: ['Insurance', 'Health Insurance'] },
  { prefix: '/insurance/life', labels: ['Insurance', 'Life Insurance'] },
  { prefix: '/insurance/commercial', labels: ['Insurance', 'Business & Commercial'] },
  { prefix: '/insurance/', labels: ['Insurance'] },
  { prefix: '/insurance', labels: ['Insurance'] },
  { prefix: '/line-uw', labels: ['UW Operations', 'Line UW Desk'] },
  { prefix: '/staff-uw', labels: ['UW Operations', 'Staff UW Desk'] },
  { prefix: '/uw-workbench', labels: ['UW Operations', 'UW Workbench'] },
  { prefix: '/mortgage', labels: ['Mortgage & Lending', 'Mortgage'] },
  { prefix: '/lending', labels: ['Mortgage & Lending', 'Lending'] },
  { prefix: '/workflow', labels: ['UW Operations', 'UW Sign-off'] },
  { prefix: '/queue', labels: ['UW Operations', 'Submission Queue'] },
  { prefix: '/issuance', labels: ['Post-Decision', 'Issuance'] },
  { prefix: '/monitoring', labels: ['Post-Decision', 'Policy Monitoring'] },
  { prefix: '/producer-comms', labels: ['Post-Decision', 'Producer Comms'] },
  { prefix: '/renewals', labels: ['Analytics', 'Renewals'] },
  { prefix: '/overrides', labels: ['Analytics', 'Override Analytics'] },
  { prefix: '/business-kpis', labels: ['Analytics', 'Business KPIs'] },
  { prefix: '/eval-trends', labels: ['Analytics', 'Eval Trends'] },
  { prefix: '/portfolio', labels: ['Analytics', 'Portfolio'] },
  { prefix: '/ratemaking', labels: ['Analytics', 'Ratemaking & Pricing'] },
  { prefix: '/authority', labels: ['Analytics', 'Authority Matrix'] },
  { prefix: '/market', labels: ['Analytics', 'Market Cycle'] },
  { prefix: '/pilot', labels: ['Governance', 'Pilot Lab'] },
  { prefix: '/registry', labels: ['Governance', 'Model Registry'] },
  { prefix: '/integrations', labels: ['Governance', 'Integrations'] },
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

export default function Layout({ health, pendingCount, onRefresh, onLogin, user, setUser }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [openGroups, setOpenGroups] = useState(() => {
    const init = {};
    nav.forEach((item) => { if (item.children && item.defaultOpen) init[item.to] = true; });
    return init;
  });
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const crumbs = crumbsFor(pathname);

  const logout = () => {
    auth.clear();
    setUser(null);
    navigate('/system');
  };

  const toggleGroup = (to) => setOpenGroups((g) => ({ ...g, [to]: !g[to] }));

  const renderNavItem = (item, i) => {
    if (item.section) {
      if (sidebarCollapsed) return null;
      return (
        <p key={i} className="px-3 pb-1 pt-4 text-[10px] font-bold uppercase tracking-widest text-slate-600">
          {item.section}
        </p>
      );
    }

    if (item.children) {
      const Icon = item.icon;
      const isOpen = !!openGroups[item.to];
      if (sidebarCollapsed) {
        return (
          <NavLink
            key={item.to}
            to={item.to}
            title={item.label}
            className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}
          >
            <Icon className={`h-[18px] w-[18px] mx-auto ${item.color || ''}`} />
          </NavLink>
        );
      }
      return (
        <div key={item.to}>
          <div className="flex items-center gap-0">
            <NavLink
              to={item.to}
              className={({ isActive }) => `nav-link flex-1 ${isActive ? 'nav-link-active' : ''}`}
            >
              <Icon className={`h-[18px] w-[18px] ${item.color || ''}`} />
              <span className="flex-1">{item.label}</span>
            </NavLink>
            <button
              type="button"
              onClick={() => toggleGroup(item.to)}
              className="mr-1 rounded-lg p-2 text-slate-500 transition hover:bg-white/[0.05] hover:text-slate-300"
              title={isOpen ? 'Collapse' : 'Expand'}
            >
              {isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </button>
          </div>
          {isOpen && (
            <div
              className={`ml-4 mt-0.5 border-l border-white/[0.07] pl-2 ${
                item.scrollChildren
                  ? 'max-h-[11.25rem] overflow-y-auto overscroll-contain pr-1 [scrollbar-width:thin] [scrollbar-color:rgba(148,163,184,0.45)_transparent]'
                  : ''
              }`}
            >
              {item.children.map((child) => {
                if (child.soon) {
                  return (
                    <div
                      key={child.label}
                      className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm text-slate-600"
                      title="Coming soon"
                    >
                      <Plus className="h-3.5 w-3.5 shrink-0 text-slate-600" />
                      <span className="flex-1">{child.label}</span>
                      <span className="rounded-full bg-slate-500/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-slate-500">
                        Soon
                      </span>
                    </div>
                  );
                }
                return (
                  <NavLink
                    key={child.to}
                    to={child.to}
                    end={child.to === '/insurance'}
                    className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}
                  >
                    <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${(child.to === '/insurance' ? pathname === '/insurance' : pathname.startsWith(child.to)) ? 'bg-brand' : 'bg-slate-600'}`} />
                    <span className="flex-1">{child.label}</span>
                    {child.tag && (
                      <span className={`rounded-full px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${
                        child.tag === 'Live'
                          ? 'bg-emerald-500/15 text-emerald-400'
                          : 'bg-amber-500/15 text-amber-400'
                      }`}>
                        {child.tag}
                      </span>
                    )}
                  </NavLink>
                );
              })}
            </div>
          )}
        </div>
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
        title={sidebarCollapsed ? item.label : undefined}
      >
        <Icon className={`h-[18px] w-[18px] ${sidebarCollapsed ? 'mx-auto' : ''} ${item.color || ''}`} />
        {!sidebarCollapsed && <span className="flex-1">{item.label}</span>}
        {!sidebarCollapsed && item.badge && pendingCount > 0 && (
          <span className="rounded-full bg-red-500/20 px-2 py-0.5 text-[10px] font-bold text-red-400">
            {pendingCount}
          </span>
        )}
      </NavLink>
    );
  };

  return (
    <div className="flex min-h-screen bg-surface bg-mesh">
      {/* Sidebar */}
      <aside className={`fixed inset-y-0 left-0 z-50 flex flex-col border-r border-white/[0.06] bg-surface-raised/95 backdrop-blur-xl transition-all duration-300 lg:translate-x-0 ${
        sidebarCollapsed ? 'w-[64px]' : 'w-[272px]'
      } ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex items-center gap-3 border-b border-white/[0.06] px-5 py-5">
          {sidebarCollapsed ? (
            <button type="button" className="mx-auto flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-brand to-indigo-600 shadow-glow" onClick={() => setSidebarCollapsed(false)}>
              <Shield className="h-5 w-5 text-white" />
            </button>
          ) : (
            <>
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-brand to-indigo-600 shadow-glow">
                <Shield className="h-5 w-5 text-white" />
              </div>
              <div>
                <h1 className="font-display text-base font-bold tracking-tight">Rytera</h1>
                <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-500">AI Underwriting</p>
              </div>
            </>
          )}
          {!sidebarCollapsed && (
            <button type="button" className="ml-auto lg:hidden" onClick={() => setMobileOpen(false)}>
              <X className="h-5 w-5 text-slate-400" />
            </button>
          )}
        </div>

        <nav className="flex-1 space-y-0.5 overflow-y-auto p-3">
          {nav.map(renderNavItem)}

          {!sidebarCollapsed && (
            <div className="mx-3 mt-1 flex items-center gap-2 rounded-xl border border-dashed border-white/[0.08] px-3 py-2 text-xs text-slate-600">
              <Plus className="h-3.5 w-3.5" />
              More underwriting lines
              <span className="ml-auto rounded-full bg-slate-500/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-slate-500">
                Soon
              </span>
            </div>
          )}
        </nav>

        {!sidebarCollapsed && (
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
        )}
      </aside>

      {mobileOpen && <div className="fixed inset-0 z-40 bg-black/60 lg:hidden" onClick={() => setMobileOpen(false)} />}

      {/* Main */}
      <div className={`flex min-w-0 flex-1 flex-col transition-all duration-300 ${sidebarCollapsed ? 'lg:ml-[64px]' : 'lg:ml-[272px]'}`}>
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-3 border-b border-white/[0.06] bg-surface/80 px-6 backdrop-blur-xl">
          <div className="flex min-w-0 items-center gap-3">
            <button type="button" className="rounded-lg p-2 lg:hidden" onClick={() => setMobileOpen(true)}>
              <Menu className="h-5 w-5" />
            </button>
            <button
              type="button"
              className="hidden rounded-lg p-2 text-slate-500 hover:bg-white/5 hover:text-slate-300 lg:block"
              onClick={() => setSidebarCollapsed((v) => !v)}
              title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              <Menu className="h-5 w-5" />
            </button>
            <nav className="hidden min-w-0 items-center gap-1.5 text-xs text-slate-500 md:flex" aria-label="Breadcrumb">
              {crumbs.map((c, i) => (
                <span key={`${c}-${i}`} className="flex items-center gap-1.5 whitespace-nowrap">
                  {i > 0 && <span className="text-slate-700">/</span>}
                  <span className={i === crumbs.length - 1 ? 'font-semibold text-slate-200' : ''}>{c}</span>
                </span>
              ))}
            </nav>
          </div>
          <button type="button" onClick={onRefresh} className="btn-secondary btn-sm shrink-0 text-xs">
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
