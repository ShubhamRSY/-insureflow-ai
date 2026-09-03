import { Search, RefreshCw, ArrowUpDown } from 'lucide-react';
import { Badge, ScoreBadge, PriorityBadge, AssigneeAvatar, EmptyState } from '../components/ui';
import { STATUS_META, buildQueueRows } from '../lib/submissions';
import { useMemo, useState } from 'react';

const SORTS = {
  score_desc: { label: 'Score (high to low)', cmp: (a, b) => (b.score ?? -1) - (a.score ?? -1) },
  score_asc: { label: 'Score (low to high)', cmp: (a, b) => (a.score ?? 101) - (b.score ?? 101) },
  insured: { label: 'Insured name (A–Z)', cmp: (a, b) => a.insuredName.localeCompare(b.insuredName) },
  submission_id: { label: 'Submission ID', cmp: (a, b) => a.submissionId.localeCompare(b.submissionId) },
};

export default function QueuePage({ queueStats, insuranceJobs, onOpenJob, onRefresh }) {
  const [priority, setPriority] = useState('');
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [sortKey, setSortKey] = useState('score_desc');

  const items = queueStats?.queue || [];
  const rows = useMemo(() => buildQueueRows(items, insuranceJobs), [items, insuranceJobs]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    let out = rows;
    if (priority) out = out.filter((r) => r.priority === priority);
    if (statusFilter) out = out.filter((r) => r.statusMeta.status === statusFilter);
    if (q) out = out.filter((r) => r.insuredName.toLowerCase().includes(q) || r.submissionId.toLowerCase().includes(q) || r.lob.toLowerCase().includes(q));
    return [...out].sort(SORTS[sortKey].cmp);
  }, [rows, priority, statusFilter, query, sortKey]);

  const statusCounts = rows.reduce((acc, r) => {
    acc[r.statusMeta.status] = (acc[r.statusMeta.status] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="mx-auto max-w-6xl space-y-8 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Submissions <span className="text-slate-500">{items.length}</span></h1>
          <p className="mt-1 text-slate-400">Prioritized submissions with triage scores and pipeline progress</p>
        </div>
        <button type="button" onClick={onRefresh} className="btn-secondary btn-sm text-xs">
          <RefreshCw className="h-3.5 w-3.5" /> Refresh
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-4">
        <div className="glass-card p-4">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Total</p>
          <p className="mt-1 text-2xl font-bold">{items.length}</p>
        </div>
        <div className="glass-card p-4">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Hot</p>
          <p className="mt-1 text-2xl font-bold text-red-400">{items.filter((i) => i.priority === 'hot').length}</p>
        </div>
        <div className="glass-card p-4">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Warm</p>
          <p className="mt-1 text-2xl font-bold text-amber-400">{items.filter((i) => i.priority === 'warm').length}</p>
        </div>
        <div className="glass-card p-4">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Appetite Check Failed</p>
          <p className="mt-1 text-2xl font-bold text-slate-400">{statusCounts.appetite_check_failed || 0}</p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="flex gap-2">
          {['', 'hot', 'warm', 'cold', 'no_fit'].map((p) => (
            <button key={p} onClick={() => setPriority(p)} className={`rounded-xl px-3 py-1.5 text-xs transition ${priority === p ? 'bg-brand text-white' : 'bg-surface-overlay text-slate-400 hover:text-slate-200'}`}>
              {p ? p.replace('_', ' ') : 'All'}
            </button>
          ))}
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-xl border border-white/[0.08] bg-surface-overlay px-3 py-1.5 text-xs text-slate-300"
        >
          <option value="">All statuses</option>
          {Object.values(STATUS_META).map((s) => (
            <option key={s.status} value={s.status}>{s.label}</option>
          ))}
        </select>
        <div className="flex items-center gap-1.5 rounded-xl border border-white/[0.08] bg-surface-overlay px-3 py-1.5">
          <ArrowUpDown className="h-3.5 w-3.5 text-slate-500" />
          <select value={sortKey} onChange={(e) => setSortKey(e.target.value)} className="bg-transparent text-xs text-slate-300 focus:outline-none">
            {Object.entries(SORTS).map(([key, s]) => (
              <option key={key} value={key}>{s.label}</option>
            ))}
          </select>
        </div>
        <div className="relative ml-auto">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search insured, ID, or LOB…"
            className="w-56 rounded-xl border border-white/[0.08] bg-surface-overlay py-1.5 pl-8 pr-3 text-xs text-slate-300 placeholder:text-slate-600 focus:outline-none"
          />
        </div>
      </div>

      <div className="glass-card overflow-hidden">
        {filtered.length === 0 ? (
          <EmptyState icon={Search} title="No submissions match" description="Try clearing filters or search" />
        ) : (
          <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/[0.06] bg-surface-overlay text-left text-xs uppercase tracking-wider text-slate-500">
                <th className="px-6 py-3">Submission ID</th>
                <th className="px-6 py-3">Insured</th>
                <th className="px-6 py-3">Priority</th>
                <th className="px-6 py-3">Score</th>
                <th className="px-6 py-3">LoB</th>
                <th className="px-6 py-3">Agency</th>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3">Assignee</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {filtered.map((r) => (
                <tr key={r.bundleId} onClick={() => onOpenJob?.('insurance', r.bundleId, r.bundleId)} className="cursor-pointer transition hover:bg-white/[0.02]">
                  <td className="px-6 py-3.5 font-mono text-xs text-slate-400">{r.submissionId}</td>
                  <td className="px-6 py-3.5 text-slate-300">{r.insuredName || '—'}</td>
                  <td className="px-6 py-3.5"><PriorityBadge priority={r.priority} /></td>
                  <td className="px-6 py-3.5"><ScoreBadge value={r.score} direction="quality" /></td>
                  <td className="px-6 py-3.5 text-xs text-slate-400">{r.lob || '—'}</td>
                  <td className="px-6 py-3.5 text-xs text-slate-400">{r.agency || '—'}</td>
                  <td className="px-6 py-3.5"><Badge status={r.statusMeta.status} label={r.statusMeta.label} pulse={r.statusMeta.status === 'processing'} /></td>
                  <td className="px-6 py-3.5"><AssigneeAvatar name={r.assignee} /></td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </div>
    </div>
  );
}
