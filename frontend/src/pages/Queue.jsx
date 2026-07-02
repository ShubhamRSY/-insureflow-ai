import { Search, RefreshCw, Shield } from 'lucide-react';
import { Badge, DecisionBadge, EmptyState } from '../components/ui';
import { fmtCurrency } from '../lib/api';
import { useState } from 'react';

export default function QueuePage({ queueStats, onOpenJob, onRefresh }) {
  const [priority, setPriority] = useState('');

  const items = queueStats?.queue || [];
  const filtered = priority ? items.filter((i) => i.priority === priority) : items;

  return (
    <div className="mx-auto max-w-4xl space-y-8 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Submission Queue</h1>
          <p className="mt-1 text-slate-400">Prioritized submission queue with triage scores</p>
        </div>
        <button type="button" onClick={onRefresh} className="btn-secondary btn-sm text-xs">
          <RefreshCw className="h-3.5 w-3.5" /> Refresh
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="glass-card p-4">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Total</p>
          <p className="mt-1 text-2xl font-bold">{items.length}</p>
        </div>
        <div className="glass-card p-4">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Hot</p>
          <p className="mt-1 text-2xl font-bold text-red-400">{items.filter(i => i.priority === 'hot').length}</p>
        </div>
        <div className="glass-card p-4">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Warm</p>
          <p className="mt-1 text-2xl font-bold text-amber-400">{items.filter(i => i.priority === 'warm').length}</p>
        </div>
      </div>

      <div className="flex gap-2">
        {['', 'hot', 'warm', 'cold', 'no-fit'].map((p) => (
          <button key={p} onClick={() => setPriority(p)} className={`rounded-xl px-3 py-1.5 text-xs transition ${priority === p ? 'bg-brand text-white' : 'bg-surface-overlay text-slate-400 hover:text-slate-200'}`}>
            {p || 'All'}
          </button>
        ))}
      </div>

      <div className="glass-card overflow-hidden">
        {filtered.length === 0 ? (
          <EmptyState icon={Search} title="Queue empty" description="No submissions in the queue" />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/[0.06] bg-surface-overlay text-left text-xs uppercase tracking-wider text-slate-500">
                <th className="px-6 py-3">Bundle ID</th>
                <th className="px-6 py-3">Insured</th>
                <th className="px-6 py-3">Priority</th>
                <th className="px-6 py-3">Score</th>
                <th className="px-6 py-3">Premium</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {filtered.map((item) => (
                <tr key={item.bundle_id} onClick={() => onOpenJob?.('insurance', item.bundle_id, item.bundle_id)} className="cursor-pointer transition hover:bg-white/[0.02]">
                  <td className="px-6 py-3.5 font-mono text-xs text-slate-400">{item.bundle_id}</td>
                  <td className="px-6 py-3.5 text-slate-300">{item.insured_name || '—'}</td>
                  <td className="px-6 py-3.5"><Badge status={item.priority} /></td>
                  <td className="px-6 py-3.5">{item.triage_score != null ? item.triage_score.toFixed(1) : '—'}</td>
                  <td className="px-6 py-3.5 font-mono">{fmtCurrency(item.estimated_premium)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
