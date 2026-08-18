import { useState, useEffect, useCallback } from 'react';
import {
  ShieldCheck, RefreshCw, CheckCircle2, XCircle, Clock, FileText,
  AlertTriangle, Leaf, ChevronDown, ExternalLink,
} from 'lucide-react';
import { Badge, EmptyState } from '../components/ui';
import StateRegulatoryPanel from '../components/StateRegulatoryPanel';
import { api } from '../lib/api';

function fmtDate(value) {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function fmtDateTime(value) {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' });
}

function freshnessColor(score) {
  if (score >= 90) return 'text-emerald-400';
  if (score >= 70) return 'text-amber-400';
  if (score >= 50) return 'text-orange-400';
  return 'text-red-400';
}

function freshnessBarColor(score) {
  if (score >= 90) return 'bg-emerald-500';
  if (score >= 70) return 'bg-amber-500';
  if (score >= 50) return 'bg-orange-500';
  return 'bg-red-500';
}

function stateBadge(state) {
  return { detected: 'pending', reviewed: 'processing', approved: 'approved', rejected: 'error', superseded: 'superseded' }[state] || state;
}

export default function RegulatoryReview() {
  const [pending, setPending] = useState([]);
  const [health, setHealth] = useState(null);
  const [changelog, setChangelog] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  const [expandedRow, setExpandedRow] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [p, h, c] = await Promise.all([
        api('/api/regulatory/review/pending').catch(() => ({ changes: [] })),
        api('/api/regulatory/health').catch(() => null),
        api('/api/regulatory/changelog').catch(() => ({ entries: [] })),
      ]);
      setPending(p.changes || []);
      setHealth(h);
      setChangelog(c.entries || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const reviewChange = async (changelogId, approved) => {
    setBusy(changelogId);
    try {
      await api(`/api/regulatory/review/${changelogId}?approved=${approved}`, { method: 'POST' });
      await load();
    } catch (e) {
      alert(e.message);
    } finally {
      setBusy('');
    }
  };

  const overallScore = health?.overall_freshness ?? null;
  const lobHealth = health?.by_line_of_business || {};

  return (
    <div className="mx-auto max-w-7xl space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-500/15">
            <ShieldCheck className="h-6 w-6 text-emerald-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Regulatory Review</h1>
            <p className="mt-1 text-sm text-slate-400">
              Compliance officer dashboard — review pending rule changes, approve or reject, and monitor rule-file freshness.
            </p>
          </div>
        </div>
        <button type="button" onClick={load} className="btn-secondary btn-sm text-xs">
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {error && <div className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}

      <StateRegulatoryPanel />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div className="glass-card group relative overflow-hidden p-5 animate-slide-up">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-emerald-500 to-teal-400 opacity-60" />
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Pending changes</p>
            <AlertTriangle className="h-4 w-4 text-amber-400" />
          </div>
          <p className="mt-2 text-3xl font-bold tracking-tight text-white">{pending.length}</p>
        </div>
        <div className="glass-card group relative overflow-hidden p-5 animate-slide-up">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-sky-500 to-cyan-400 opacity-60" />
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Overall freshness</p>
            <Leaf className="h-4 w-4 text-sky-400" />
          </div>
          {overallScore != null ? (
            <p className={`mt-2 text-3xl font-bold tracking-tight ${freshnessColor(overallScore)}`}>{overallScore.toFixed(1)}%</p>
          ) : (
            <p className="mt-2 text-3xl font-bold tracking-tight text-slate-600">—</p>
          )}
        </div>
        <div className="glass-card group relative overflow-hidden p-5 animate-slide-up">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-violet-500 to-fuchsia-400 opacity-60" />
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Recent changelog</p>
            <FileText className="h-4 w-4 text-violet-400" />
          </div>
          <p className="mt-2 text-3xl font-bold tracking-tight text-white">{changelog.length}</p>
        </div>
      </div>

      {overallScore != null && (
        <div className="glass-card p-6">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h3 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
                <Leaf className="h-4 w-4 text-emerald-400" /> Overall rule freshness
              </h3>
              <p className="mt-1 text-xs text-slate-500">Composite score across all rule files and lines of business</p>
            </div>
            <span className={`text-2xl font-bold ${freshnessColor(overallScore)}`}>{overallScore.toFixed(1)}%</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
            <div
              className={`h-full rounded-full transition-all duration-500 ${freshnessBarColor(overallScore)}`}
              style={{ width: `${Math.min(100, Math.max(0, overallScore))}%` }}
            />
          </div>
        </div>
      )}

      {Object.keys(lobHealth).length > 0 && (
        <div className="glass-card p-6">
          <div className="mb-4">
            <h3 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
              <ShieldCheck className="h-4 w-4 text-sky-400" /> Freshness by line of business
            </h3>
            <p className="mt-1 text-xs text-slate-500">Per-LOB breakdown of how current each rule file is</p>
          </div>
          <div className="space-y-3">
            {Object.entries(lobHealth)
              .sort((a, b) => (b[1].score ?? b[1]) - (a[1].score ?? a[1]))
              .map(([lob, data]) => {
                const score = typeof data === 'object' ? (data.score ?? 0) : (data ?? 0);
                const label = typeof data === 'object' && data.label ? data.label : lob;
                return (
                  <div key={lob}>
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-medium text-slate-300">{label}</span>
                      <span className={`font-semibold ${freshnessColor(score)}`}>{typeof score === 'number' ? score.toFixed(1) : score}%</span>
                    </div>
                    <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-white/10">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${freshnessBarColor(score)}`}
                        style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
                      />
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      <div className="glass-card p-6">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h3 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
              <AlertTriangle className="h-4 w-4 text-amber-400" /> Pending regulatory changes
            </h3>
            <p className="mt-1 text-xs text-slate-500">Detected rule-file diffs awaiting compliance officer approval</p>
          </div>
          {pending.length > 0 && (
            <span className="rounded-full bg-amber-500/15 px-2.5 py-1 text-xs font-semibold text-amber-400 ring-1 ring-amber-500/20">
              {pending.length} pending
            </span>
          )}
        </div>

        {loading ? (
          <div className="flex justify-center py-12">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
          </div>
        ) : pending.length === 0 ? (
          <EmptyState
            icon={CheckCircle2}
            title="No pending changes"
            description="All regulatory rule files are current. New changes will appear here when detected."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06] text-left text-[10px] uppercase tracking-wider text-slate-500">
                  <th className="px-3 py-2">State</th>
                  <th className="px-3 py-2">Line</th>
                  <th className="px-3 py-2">Rule key</th>
                  <th className="px-3 py-2">Old value</th>
                  <th className="px-3 py-2">New value</th>
                  <th className="px-3 py-2">Source</th>
                  <th className="px-3 py-2">Detected</th>
                  <th className="px-3 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {pending.map((change) => {
                  const id = change.changelog_id || change.id || '';
                  const isOpen = expandedRow === id;
                  return (
                    <tr key={id} className="align-top hover:bg-white/[0.02]">
                      <td className="px-3 py-2.5">
                        <Badge status={stateBadge(change.state)} />
                      </td>
                      <td className="whitespace-nowrap px-3 py-2.5 text-xs text-slate-300">
                        {change.line_of_business || change.lob || '—'}
                      </td>
                      <td className="px-3 py-2.5">
                        <button
                          type="button"
                          onClick={() => setExpandedRow(isOpen ? null : id)}
                          className="inline-flex items-center gap-1 text-xs font-medium text-sky-400 hover:text-sky-300"
                        >
                          <span className="font-mono">{change.rule_key || change.key || '—'}</span>
                          <ChevronDown className={`h-3 w-3 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                        </button>
                      </td>
                      <td className="max-w-[180px] truncate px-3 py-2.5 font-mono text-xs text-slate-500" title={JSON.stringify(change.old_value)}>
                        {change.old_value != null ? (typeof change.old_value === 'string' ? change.old_value : JSON.stringify(change.old_value)) : '—'}
                      </td>
                      <td className="max-w-[180px] truncate px-3 py-2.5 font-mono text-xs text-emerald-400/80" title={JSON.stringify(change.new_value)}>
                        {change.new_value != null ? (typeof change.new_value === 'string' ? change.new_value : JSON.stringify(change.new_value)) : '—'}
                      </td>
                      <td className="whitespace-nowrap px-3 py-2.5 text-xs text-slate-400">
                        {change.source ? (
                          <span className="inline-flex items-center gap-1">
                            <ExternalLink className="h-3 w-3" /> {change.source}
                          </span>
                        ) : '—'}
                      </td>
                      <td className="whitespace-nowrap px-3 py-2.5 text-xs text-slate-500">
                        <span className="inline-flex items-center gap-1"><Clock className="h-3 w-3" /> {fmtDate(change.detected_at || change.created_at)}</span>
                      </td>
                      <td className="px-3 py-2.5 text-right">
                        <div className="flex justify-end gap-1.5">
                          <button
                            type="button"
                            disabled={busy === id}
                            onClick={() => reviewChange(id, true)}
                            className="inline-flex items-center gap-1 rounded-lg bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-400 ring-1 ring-inset ring-emerald-500/25 transition hover:bg-emerald-500/20 disabled:opacity-50"
                          >
                            <CheckCircle2 className="h-3 w-3" /> Approve
                          </button>
                          <button
                            type="button"
                            disabled={busy === id}
                            onClick={() => reviewChange(id, false)}
                            className="inline-flex items-center gap-1 rounded-lg bg-red-500/10 px-2.5 py-1 text-xs font-medium text-red-400 ring-1 ring-inset ring-red-500/25 transition hover:bg-red-500/20 disabled:opacity-50"
                          >
                            <XCircle className="h-3 w-3" /> Reject
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {changelog.length > 0 && (
        <div className="glass-card p-6">
          <div className="mb-4">
            <h3 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
              <FileText className="h-4 w-4 text-violet-400" /> Recent changelog
            </h3>
            <p className="mt-1 text-xs text-slate-500">History of detected and reviewed regulatory changes</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06] text-left text-[10px] uppercase tracking-wider text-slate-500">
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Line</th>
                  <th className="px-3 py-2">Rule key</th>
                  <th className="px-3 py-2">Change</th>
                  <th className="px-3 py-2">Reviewed</th>
                  <th className="px-3 py-2">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {changelog.map((entry) => {
                  const eid = entry.changelog_id || entry.id || '';
                  return (
                    <tr key={eid} className="hover:bg-white/[0.02]">
                      <td className="px-3 py-2.5">
                        <Badge status={stateBadge(entry.state || entry.status)} />
                      </td>
                      <td className="whitespace-nowrap px-3 py-2.5 text-xs text-slate-300">
                        {entry.line_of_business || entry.lob || '—'}
                      </td>
                      <td className="px-3 py-2.5 font-mono text-xs text-slate-300">
                        {entry.rule_key || entry.key || '—'}
                      </td>
                      <td className="max-w-[200px] truncate px-3 py-2.5 text-xs text-slate-400">
                        {entry.old_value != null && entry.new_value != null
                          ? <span className="font-mono">{String(entry.old_value)} → <span className="text-emerald-400/80">{String(entry.new_value)}</span></span>
                          : entry.summary || entry.description || '—'}
                      </td>
                      <td className="whitespace-nowrap px-3 py-2.5 text-xs text-slate-500">
                        {entry.reviewed_by || '—'}
                      </td>
                      <td className="whitespace-nowrap px-3 py-2.5 text-xs text-slate-500">
                        {fmtDateTime(entry.reviewed_at || entry.created_at)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
