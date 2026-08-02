import { useState, useEffect, useCallback } from 'react';
import { Link2, RefreshCw, CheckCircle2, XCircle, Cable, Loader2, Unplug, ArrowUpRight } from 'lucide-react';
import { EmptyState } from '../components/ui';
import { endpoints } from '../lib/api';
import ConnectorLogo from '../components/ConnectorLogo';
import { groupSourcesByCategory } from '../lib/connectorBrands';

export default function IntegrationsPage() {
  const [adapters, setAdapters] = useState([]);
  const [systems, setSystems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [connectingId, setConnectingId] = useState(null);
  const [config, setConfig] = useState({});
  const [activeId, setActiveId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const d = await endpoints.integrationStatus();
      setAdapters(d.adapters || []);
      setSystems(d.systems || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const sections = groupSourcesByCategory(adapters.map((a) => ({ ...a, status: a.connected ? 'connected' : 'ready' })));

  const connect = async (src) => {
    setError('');
    setConnectingId(src.id);
    try {
      await endpoints.connectSource(src.id, config[src.id] || {});
      setActiveId(null);
      setConfig((c) => ({ ...c, [src.id]: {} }));
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setConnectingId(null);
    }
  };

  const disconnect = async (src) => {
    setError('');
    setConnectingId(src.id);
    try {
      await endpoints.disconnectSource(src.id);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setConnectingId(null);
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-8 animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-cyan-500/15">
            <Link2 className="h-6 w-6 text-cyan-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Integrations</h1>
            <p className="mt-1 text-slate-400">
              Connect to document sources — then pull them from Insurance, Mortgage &amp; Lending
            </p>
          </div>
        </div>
        <button type="button" onClick={load} className="btn-secondary btn-sm text-xs">
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {error && <div className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}

      <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 px-4 py-3 text-xs text-cyan-300">
        Connecting a service here registers it for the <span className="font-semibold">Connect &amp; pull</span> tab in
        Insurance, Mortgage, and Lending — pull documents from it in any vertical.
      </div>

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
        </div>
      ) : adapters.length === 0 ? (
        <EmptyState icon={Link2} title="No connectors" description="Source connectors will appear here" />
      ) : (
        <div className="space-y-6">
          {sections.map((section) => (
            <div key={section.id} className="glass-card overflow-hidden">
              <div className="border-b border-white/[0.06] px-5 py-3">
                <h3 className="text-sm font-semibold">{section.title}</h3>
                <p className="mt-0.5 text-[11px] text-slate-500">
                  {section.sources.filter((s) => s.connected).length} of {section.sources.length} connected
                </p>
              </div>
              <div className="divide-y divide-white/[0.04]">
                {section.sources.map((src) => {
                  const isActive = activeId === src.id;
                  const cfg = config[src.id] || {};
                  return (
                    <div key={src.id} className={`px-5 py-4 transition ${isActive ? 'bg-brand/[0.03]' : 'hover:bg-white/[0.02]'}`}>
                      <div className="flex items-center gap-3">
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white/[0.06] p-1">
                          <ConnectorLogo sourceId={src.id} name={src.name} size={20} />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium text-slate-200">{src.name}</p>
                          <p className="truncate text-xs text-slate-500">{src.description}</p>
                        </div>
                        {src.connected ? (
                          <div className="flex shrink-0 items-center gap-2">
                            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-[10px] font-semibold text-emerald-400">
                              <CheckCircle2 className="h-3 w-3" /> Connected
                            </span>
                            <button type="button" onClick={() => disconnect(src)} disabled={connectingId === src.id}
                              className="rounded-lg border border-white/[0.08] px-2 py-1 text-[10px] text-slate-400 transition hover:border-red-400/30 hover:text-red-300">
                              {connectingId === src.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <Unplug className="h-3 w-3" />}
                            </button>
                          </div>
                        ) : (
                          <button type="button" onClick={() => { setActiveId(isActive ? null : src.id); setError(''); }}
                            className="btn-primary btn-sm shrink-0 text-xs">
                            <Cable className="h-3 w-3" /> Connect
                          </button>
                        )}
                      </div>

                      {src.connected && src.connection_label && (
                        <p className="mt-1.5 pl-12 text-[11px] text-emerald-400/80">↳ {src.connection_label}</p>
                      )}

                      {isActive && !src.connected && (
                        <div className="mt-3 space-y-2 rounded-lg border border-white/[0.06] bg-surface/40 p-3 pl-12">
                          {(src.config_fields || []).length === 0 ? (
                            <p className="text-[11px] text-slate-500">No configuration needed — connects with defaults.</p>
                          ) : (
                            (src.config_fields || []).map((f) => (
                              <div key={f.key}>
                                <label className="mb-0.5 block text-[10px] text-slate-500">{f.label}</label>
                                <input className="input-field w-full text-xs" placeholder={f.placeholder}
                                  value={cfg[f.key] || ''}
                                  onChange={(e) => setConfig((c) => ({ ...c, [src.id]: { ...c[src.id], [f.key]: e.target.value } }))} />
                              </div>
                            ))
                          )}
                          <button type="button" onClick={() => connect(src)} disabled={connectingId === src.id}
                            className="btn-primary btn-sm w-full text-xs disabled:opacity-40">
                            {connectingId === src.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Cable className="h-3 w-3" />}
                            Connect to {src.name}
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}

          {/* Pull destinations */}
          <div className="glass-card overflow-hidden">
            <div className="border-b border-white/[0.06] px-5 py-3">
              <h3 className="text-sm font-semibold">Pull connected sources</h3>
            </div>
            <div className="grid gap-3 p-5 sm:grid-cols-3">
              {[
                ['/insurance', 'Insurance', 'Commercial / personal lines submissions'],
                ['/mortgage', 'Mortgage', 'Residential & commercial loan packages'],
                ['/lending', 'Lending', 'Business & consumer loan applications'],
              ].map(([href, label, sub]) => (
                <a key={href} href={href}
                  className="group flex items-center justify-between rounded-xl border border-white/[0.06] bg-surface-overlay/40 px-4 py-3 transition hover:border-brand/35">
                  <span>
                    <span className="block text-sm font-medium text-slate-200">{label}</span>
                    <span className="block text-xs text-slate-500">{sub}</span>
                  </span>
                  <ArrowUpRight className="h-4 w-4 text-slate-500 transition group-hover:text-brand" />
                </a>
              ))}
            </div>
          </div>

          {systems.length > 0 && (
            <div className="glass-card overflow-hidden">
              <div className="border-b border-white/[0.06] px-5 py-3">
                <h3 className="text-sm font-semibold">Core Systems</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/[0.06] bg-surface-overlay text-left text-xs uppercase tracking-wider text-slate-500">
                      <th className="px-6 py-3">System</th>
                      <th className="px-6 py-3">Mode</th>
                      <th className="px-6 py-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.04]">
                    {systems.map((a, i) => (
                      <tr key={i} className="hover:bg-white/[0.02]">
                        <td className="px-6 py-3.5 text-slate-300">{a.name}</td>
                        <td className="px-6 py-3.5 text-xs text-slate-400">{a.mode || '—'}</td>
                        <td className="px-6 py-3.5">
                          {a.configured || a.healthy ? (
                            <span className="inline-flex items-center gap-1 text-xs text-emerald-400"><CheckCircle2 className="h-3 w-3" /> Connected</span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-xs text-slate-500"><XCircle className="h-3 w-3" /> Not configured</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
