import { useCallback, useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { endpoints, fmtCurrency, AuthError } from '../lib/api';
import { insuranceLineLabel } from '../lib/insuranceLines';
import { Badge, EmptyState, StatCard } from '../components/ui';
import {
  FileCheck, Clock, CheckCircle2,
  ArrowRight, Search, RefreshCw, Zap, Bell, BarChart3,
  Loader2, Sparkles, Flame, Briefcase,
} from 'lucide-react';

const QUICK_ACTIONS = [
  { key: 'w', label: 'Open Workbench', color: 'bg-brand hover:bg-brand-light', icon: Briefcase, to: '/uw-workbench' },
  { key: 'Enter', label: 'Open submission', color: 'bg-sky-600 hover:bg-sky-500', icon: FileCheck, openJob: true },
];

// Decorative severity dot for the illustrative Activity Hotspots list only —
// a plain unlabeled dot has no Badge equivalent, so this stays local.
const SEVERITY_DOT = {
  urgent: 'bg-red-400',
  critical: 'bg-orange-400',
  warning: 'bg-amber-400',
  info: 'bg-sky-400',
};

// Maps this file's 4-tier severity onto Badge's existing color keys instead
// of adding near-duplicate ones — urgent and critical must stay visually
// distinct (matches SEVERITY_DOT above), so urgent borrows Badge's `critical`
// (red) and this file's own `critical` borrows Badge's `high` (orange).
const SEVERITY_BADGE = { urgent: 'critical', critical: 'high', warning: 'moderate', info: 'low' };

function timeAgo(dateStr) {
  if (!dateStr) return '';
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function SubmissionRow({ job, onSelect, isSelected, index }) {
  const results = job.results || {};
  const memo = results.memo || {};
  const quote = results.quote || {};
  const insured = results.insured_name || memo.insured_name || 'Unknown';
  const line = results.insurance_line || results.product_line || quote.insurance_line || '';
  const state = results.state || memo.state || '';
  const risk = memo.overall_risk_score;
  const severity = memo.overall_risk_severity;
  const premium = quote.adjusted_premium || quote.estimated_premium;
  const decision = results.ai_decision || memo.decision || '';
  const status = job.status || 'processing';

  return (
    <button
      type="button"
      onClick={() => onSelect(job)}
      className={`w-full text-left p-3 rounded-lg border transition-all duration-150 group ${
        isSelected
          ? 'bg-brand/10 border-brand/40 ring-1 ring-brand/20'
          : 'bg-slate-800/30 border-slate-700/30 hover:bg-slate-700/30 hover:border-slate-600/50'
      }`}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-medium text-white text-sm truncate">{insured}</span>
            {state && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-700 text-slate-300 font-mono">
                {state}
              </span>
            )}
            {line && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-700/50 text-slate-400">
                {insuranceLineLabel(line)}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 mt-1">
            {risk != null && (
              <span className={`text-xs font-medium ${
                risk >= 7 ? 'text-risk-red' : risk >= 4 ? 'text-risk-amber' : 'text-verdigris'
              }`}>
                Risk {risk}/10
              </span>
            )}
            {premium && (
              <span className="text-xs text-slate-400">{fmtCurrency(premium)}</span>
            )}
            {decision && (
              <span className="text-xs text-slate-500 capitalize">{decision.replace(/_/g, ' ')}</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {status === 'processing' && (
            <Loader2 size={14} className="text-sky-400 animate-spin" />
          )}
          <ArrowRight size={14} className="text-slate-600 group-hover:text-slate-400 transition-colors" />
        </div>
      </div>
    </button>
  );
}

function AlertRow({ alert, onReview }) {
  return (
    <div className="p-3 rounded-lg border border-slate-700/40 bg-slate-800/30 flex items-start gap-3">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-white">{alert.title}</span>
          <Badge status={SEVERITY_BADGE[alert.severity] || 'low'} label={alert.severity} />
        </div>
        <div className="text-xs text-slate-400 mt-0.5 line-clamp-2">{alert.description}</div>
        <div className="flex items-center gap-2 mt-1.5">
          {alert.line_of_business && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-black/20 text-slate-400">{insuranceLineLabel(alert.line_of_business)}</span>
          )}
          {alert.requires_action && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-black/20 font-medium text-slate-300">Action required</span>
          )}
          <span className="text-[10px] text-slate-500">{timeAgo(alert.detected_at)}</span>
        </div>
      </div>
      {!alert.reviewed && (
        <button
          type="button"
          onClick={() => onReview(alert.alert_id)}
          className="text-[10px] px-2 py-1 rounded bg-black/20 hover:bg-black/30 shrink-0 text-slate-300"
        >
          Dismiss
        </button>
      )}
    </div>
  );
}

export default function UWDashboard({ onOpenJob }) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [inbox, setInbox] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [selectedJob, setSelectedJob] = useState(null);
  const [selectedIdx, setSelectedIdx] = useState(-1);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterLine, setFilterLine] = useState('');
  const [filterState, setFilterState] = useState('');
  const [showShortcuts, setShowShortcuts] = useState(false);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    try {
      const [inboxRes, alertsRes] = await Promise.allSettled([
        endpoints.workflowInbox(),
        endpoints.healthComplianceAllStates?.() ?? Promise.resolve({ states: {} }),
      ]);

      if (inboxRes.status === 'fulfilled') {
        const items = (inboxRes.value?.cases || inboxRes.value || []).map((c) => ({
          ...c,
          _results: c.results || c.memo || {},
        }));
        setInbox(items);
      }

      try {
        const state = 'CT';
        const res = await fetch(`/api/law-tracker/alerts?limit=20`, {
          headers: { Authorization: `Bearer ${localStorage.getItem('insureflow_token')}` },
        });
        if (res.ok) {
          const data = await res.json();
          setAlerts(data.alerts || []);
        }
      } catch { /* alerts optional */ }

      setMetrics({
        total: inboxRes.status === 'fulfilled' ? (inboxRes.value?.cases || inboxRes.value || []).length : 0,
        pending: inboxRes.status === 'fulfilled' ? (inboxRes.value?.cases || inboxRes.value || []).filter((c) => !c.final_decision).length : 0,
      });
    } catch (e) {
      if (e instanceof AuthError) return;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadDashboard(); }, [loadDashboard]);

  const filteredInbox = useMemo(() => {
    let items = inbox;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      items = items.filter((j) => {
        const r = j._results || j.results || {};
        const name = (r.insured_name || r.memo?.insured_name || '').toLowerCase();
        return name.includes(q) || (r.state || '').toLowerCase().includes(q);
      });
    }
    if (filterLine) {
      items = items.filter((j) => {
        const r = j._results || j.results || {};
        return (r.insurance_line || r.product_line || '').toLowerCase() === filterLine.toLowerCase();
      });
    }
    if (filterState) {
      items = items.filter((j) => {
        const r = j._results || j.results || {};
        return (r.state || '').toUpperCase() === filterState.toUpperCase();
      });
    }
    return items;
  }, [inbox, searchQuery, filterLine, filterState]);

  useEffect(() => {
    const handler = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

      if (e.key === '/' || e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        document.getElementById('uw-search')?.focus();
      }
      if (e.key === 'Escape') {
        setSelectedJob(null);
        setSelectedIdx(-1);
        setSearchQuery('');
      }
      if (e.key === 'ArrowDown' && filteredInbox.length > 0) {
        e.preventDefault();
        const next = Math.min(selectedIdx + 1, filteredInbox.length - 1);
        setSelectedIdx(next);
        setSelectedJob(filteredInbox[next]);
      }
      if (e.key === 'ArrowUp' && filteredInbox.length > 0) {
        e.preventDefault();
        const prev = Math.max(selectedIdx - 1, 0);
        setSelectedIdx(prev);
        setSelectedJob(filteredInbox[prev]);
      }
      if (e.key === 'Enter' && selectedJob) {
        const id = selectedJob.id || selectedJob.job_id;
        if (id) navigate(`/insurance/${id}`);
      }
      if (e.key === 'w' || e.key === 'W') {
        navigate('/uw-workbench');
      }
      if (e.key === '?') {
        setShowShortcuts((s) => !s);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [filteredInbox, selectedIdx, selectedJob, navigate]);

  const pendingJobs = filteredInbox.filter((j) => !j.final_decision);
  const recentJobs = filteredInbox.filter((j) => j.final_decision).slice(0, 10);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 size={24} className="text-brand animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
            <Sparkles size={22} className="text-brand" />
            UW Dashboard
          </h1>
          <p className="text-sm text-slate-400 mt-0.5">
            {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setShowShortcuts((s) => !s)}
            className="p-2 rounded-lg bg-slate-800/50 border border-slate-700/50 text-slate-400 hover:text-white transition-colors"
            title="Keyboard shortcuts (?)"
          >
            <span className="text-xs font-mono px-1">?</span>
          </button>
          <button
            type="button"
            onClick={loadDashboard}
            className="p-2 rounded-lg bg-slate-800/50 border border-slate-700/50 text-slate-400 hover:text-white transition-colors"
          >
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      {/* Keyboard shortcuts panel */}
      {showShortcuts && (
        <div className="glass-card p-4">
          <h3 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
            <Zap size={14} className="text-brand" /> Keyboard Shortcuts
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            {[
              ['/', 'Search'],
              ['\u2191\u2193', 'Navigate'],
              ['Enter', 'Open submission'],
              ['W', 'Open Workbench'],
              ['Esc', 'Clear selection'],
            ].map(([key, desc]) => (
              <div key={key} className="flex items-center gap-2">
                <kbd className="px-1.5 py-0.5 rounded bg-slate-700 text-slate-300 font-mono text-[10px]">{key}</kbd>
                <span className="text-slate-400">{desc}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Pending review" value={pendingJobs.length} valueClassName="text-sky-400" />
        <StatCard label="Decided today" value={recentJobs.length} valueClassName="text-emerald-400" />
        <StatCard label="Active alerts" value={alerts.filter((a) => !a.reviewed).length} valueClassName="text-amber-400" />
        <StatCard label="Total submissions" value={metrics?.total || inbox.length} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Inbox — left 2/3 */}
        <div className="lg:col-span-2 space-y-4">
          {/* Search + filters */}
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                id="uw-search"
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search submissions... ( / )"
                className="w-full pl-9 pr-3 py-2 rounded-lg bg-slate-800/50 border border-slate-700/50 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand/50 focus:ring-1 focus:ring-brand/20"
              />
            </div>
            <select
              value={filterLine}
              onChange={(e) => setFilterLine(e.target.value)}
              className="px-3 py-2 rounded-lg bg-slate-800/50 border border-slate-700/50 text-sm text-slate-300 focus:outline-none"
            >
              <option value="">All lines</option>
              <option value="property">Property</option>
              <option value="liability">Liability</option>
              <option value="auto">Auto</option>
              <option value="workers_comp">Workers Comp</option>
              <option value="life">Life</option>
              <option value="health">Health</option>
              <option value="cyber">Cyber</option>
            </select>
          </div>

          {/* Pending inbox */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-sm font-medium text-slate-300 flex items-center gap-2">
                <Flame size={14} className="text-orange-400" />
                Needs Review ({pendingJobs.length})
              </h2>
            </div>
            {pendingJobs.length === 0 ? (
              <EmptyState icon={CheckCircle2} title="All caught up" description="No submissions pending review." />
            ) : (
              <div className="space-y-1.5">
                {pendingJobs.map((job, i) => (
                  <SubmissionRow
                    key={job.id || i}
                    job={job}
                    index={i}
                    isSelected={selectedIdx === i}
                    onSelect={(j) => { setSelectedJob(j); setSelectedIdx(i); }}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Recent decisions */}
          {recentJobs.length > 0 && (
            <div>
              <h2 className="text-sm font-medium text-slate-300 mb-2 flex items-center gap-2">
                <Clock size={14} className="text-slate-400" />
                Recent Decisions ({recentJobs.length})
              </h2>
              <div className="space-y-1.5">
                {recentJobs.map((job, i) => (
                  <SubmissionRow
                    key={job.id || `r-${i}`}
                    job={job}
                    index={i + pendingJobs.length}
                    isSelected={false}
                    onSelect={(j) => {
                      const id = j.id || j.job_id;
                      if (id) navigate(`/insurance/${id}`);
                    }}
                  />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right sidebar — alerts + quick actions */}
        <div className="space-y-4">
          {/* Triage actions — decisions happen on Workbench, not here */}
          {selectedJob && (
            <div className="glass-card p-4">
              <h3 className="text-sm font-medium text-white mb-2 flex items-center gap-2">
                <Zap size={14} className="text-brand" />
                Next step
              </h3>
              <p className="mb-3 text-xs text-slate-400">
                Approve / decline / refer / quote live on the UW Workbench — this dashboard is triage only.
              </p>
              <div className="grid grid-cols-1 gap-2">
                {QUICK_ACTIONS.map(({ key, label, color, icon: Icon, to, openJob }) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => {
                      if (to) {
                        navigate(to);
                        return;
                      }
                      if (openJob) {
                        const id = selectedJob.id || selectedJob.job_id;
                        if (id) navigate(`/insurance/${id}`);
                      }
                    }}
                    className={`${color} text-white text-sm py-2 px-3 rounded-lg flex items-center justify-center gap-2 transition-all`}
                  >
                    <Icon size={14} />
                    {label}
                    <kbd className="text-[10px] opacity-60 ml-1">{key}</kbd>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Regulatory alerts */}
          <div className="glass-card p-4">
            <h3 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
              <Bell size={14} className="text-amber-400" />
              Regulatory Alerts
              {alerts.filter((a) => !a.reviewed).length > 0 && (
                <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300">
                  {alerts.filter((a) => !a.reviewed).length} new
                </span>
              )}
            </h3>
            {alerts.length === 0 ? (
              <EmptyState title="No alerts" />
            ) : (
              <div className="space-y-2 max-h-80 overflow-y-auto">
                {alerts.slice(0, 8).map((alert) => (
                  <AlertRow
                    key={alert.alert_id}
                    alert={alert}
                    onReview={(id) => setAlerts((prev) => prev.map((a) => a.alert_id === id ? { ...a, reviewed: true } : a))}
                  />
                ))}
              </div>
            )}
            {alerts.length > 8 && (
              <button
                type="button"
                onClick={() => navigate('/regulatory-review')}
                className="w-full mt-2 text-xs text-slate-400 hover:text-white py-1"
              >
                View all alerts
              </button>
            )}
          </div>

          {/* Hot states — illustrative only until portfolio feed is wired */}
          <div className="glass-card p-4">
            <h3 className="text-sm font-medium text-white mb-1 flex items-center gap-2">
              <BarChart3 size={14} className="text-sky-400" />
              Activity Hotspots
              <span className="ml-auto rounded-full bg-amber-500/15 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider text-amber-300">
                Demo
              </span>
            </h3>
            <p className="mb-3 text-[11px] text-slate-500">Illustrative examples — not live portfolio concentration.</p>
            <div className="space-y-2">
              {[
                { state: 'FL', reason: 'Hurricane season', severity: 'critical' },
                { state: 'CA', reason: 'Rate filing deadline', severity: 'warning' },
                { state: 'NY', reason: 'DFS enforcement', severity: 'warning' },
                { state: 'TX', reason: 'TDI bulletins', severity: 'info' },
              ].map((h) => (
                <div key={h.state} className="flex items-center gap-2 text-xs">
                  <span className={`w-2 h-2 rounded-full ${SEVERITY_DOT[h.severity] || SEVERITY_DOT.info}`} />
                  <span className="font-mono text-white w-6">{h.state}</span>
                  <span className="text-slate-400">{h.reason}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
