import { useState, useEffect, useCallback } from 'react';
import { Link2, RefreshCw, CheckCircle, XCircle } from 'lucide-react';
import { EmptyState } from '../components/ui';
import { endpoints } from '../lib/api';

export default function IntegrationsPage() {
  const [status, setStatus] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const d = await endpoints.integrationStatus();
      setStatus(d.adapters || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="mx-auto max-w-4xl space-y-8 animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-cyan-500/15">
            <Link2 className="h-6 w-6 text-cyan-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Integrations</h1>
            <p className="mt-1 text-slate-400">System adapter health and status</p>
          </div>
        </div>
        <button type="button" onClick={load} className="btn-secondary btn-sm text-xs">
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {error && <div className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
        </div>
      ) : status.length === 0 ? (
        <EmptyState icon={Link2} title="No integrations" description="Integration adapters will appear once configured" />
      ) : (
        <div className="glass-card overflow-hidden">
          <div className="border-b border-white/[0.06] px-5 py-3">
            <h3 className="text-sm font-semibold">Adapter Status</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06] bg-surface-overlay text-left text-xs uppercase tracking-wider text-slate-500">
                  <th className="px-6 py-3">Adapter</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Version</th>
                  <th className="px-6 py-3">Last Check</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {status.map((a, i) => (
                  <tr key={i} className="hover:bg-white/[0.02]">
                    <td className="px-6 py-3.5 text-slate-300">{a.name || a.adapter}</td>
                    <td className="px-6 py-3.5">
                      {a.status === 'ok' || a.healthy ? (
                        <span className="inline-flex items-center gap-1 text-xs text-emerald-400"><CheckCircle className="h-3 w-3" /> Connected</span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs text-red-400"><XCircle className="h-3 w-3" /> Disconnected</span>
                      )}
                    </td>
                    <td className="px-6 py-3.5 text-xs text-slate-400">{a.version || '—'}</td>
                    <td className="px-6 py-3.5 text-xs text-slate-400">{a.last_check || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
