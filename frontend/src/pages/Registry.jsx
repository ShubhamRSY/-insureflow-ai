import { useState, useEffect, useCallback } from 'react';
import { BookOpen, RefreshCw, Plus, CheckCircle, XCircle, Send, Camera, GitCompare, Globe, Upload, ListChecks, FlaskConical } from 'lucide-react';
import { Badge, EmptyState } from '../components/ui';
import { endpoints } from '../lib/api';

export default function RegistryPage() {
  const [entries, setEntries] = useState([]);
  const [snapshots, setSnapshots] = useState([]);
  const [checklist, setChecklist] = useState(null);
  const [experiments, setExperiments] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', version: '', model_type: '', description: '' });
  const [diffData, setDiffData] = useState(null);
  const [diffA, setDiffA] = useState('');
  const [diffB, setDiffB] = useState('');
  const [contextData, setContextData] = useState(null);
  const [bootstrapping, setBootstrapping] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [v, s, cl, ex] = await Promise.all([
        endpoints.registryVersions().catch(() => ({ entries: [] })),
        endpoints.registrySnapshots().catch(() => ({ snapshots: [] })),
        endpoints.releaseChecklist().catch(() => null),
        endpoints.releaseExperiments().catch(() => null),
      ]);
      setEntries(v.entries || []);
      setSnapshots(s.snapshots || []);
      setChecklist(cl);
      setExperiments(ex);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await endpoints.createRegistryEntry(form);
      setShowForm(false);
      setForm({ name: '', version: '', model_type: '', description: '' });
      await load();
    } catch (e) {
      alert(e.message);
    }
  };

  const handleAction = async (id, action) => {
    try {
      if (action === 'submit') await endpoints.submitRegistryEntry(id);
      else if (action === 'approve') await endpoints.approveRegistryEntry(id);
      else if (action === 'reject') await endpoints.rejectRegistryEntry(id);
      await load();
    } catch (e) {
      alert(e.message);
    }
  };

  const handleSnapshot = async () => {
    try {
      await endpoints.registrySnapshot();
      await load();
    } catch (e) {
      alert(e.message);
    }
  };

  const statusColor = (s) => {
    if (s === 'approved') return 'ok';
    if (s === 'submitted') return 'processing';
    if (s === 'rejected') return 'error';
    return 'pending';
  };

  return (
    <div className="mx-auto max-w-6xl space-y-8 animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-500/15">
            <BookOpen className="h-6 w-6 text-amber-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Model Registry</h1>
            <p className="mt-1 text-slate-400">Registry + MLflow-style experiments + 11-step agent release checklist</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={handleSnapshot} className="btn-secondary btn-sm text-xs"><Camera className="h-3.5 w-3.5" /> Snapshot</button>
          <button type="button" onClick={() => { setDiffData(null); setDiffA(''); setDiffB(''); }} className="btn-secondary btn-sm text-xs"><GitCompare className="h-3.5 w-3.5" /> Diff</button>
          <button type="button" onClick={async () => { try { const d = await endpoints.registryContexts(); setContextData(d); } catch (e) { alert(e.message); } }} className="btn-secondary btn-sm text-xs"><Globe className="h-3.5 w-3.5" /> Contexts</button>
          <button type="button" onClick={async () => { setBootstrapping(true); try { await endpoints.registryBootstrap(); await load(); } catch (e) { alert(e.message); } finally { setBootstrapping(false); } }} disabled={bootstrapping} className="btn-secondary btn-sm text-xs"><Upload className={`h-3.5 w-3.5 ${bootstrapping ? 'animate-spin' : ''}`} /> Bootstrap</button>
          <button type="button" onClick={() => setShowForm(true)} className="btn-primary btn-sm text-xs"><Plus className="h-3.5 w-3.5" /> New Entry</button>
          <button type="button" onClick={load} className="btn-secondary btn-sm text-xs"><RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /></button>
        </div>
      </div>

      {error && <div className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}

      {checklist && (
        <div className="glass-card p-5">
          <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
            <ListChecks className="h-4 w-4" /> Agent release checklist
          </h3>
          <p className="mb-4 text-sm text-slate-400">{checklist.summary}</p>
          <ol className="space-y-2">
            {(checklist.checklist?.steps || []).map((s) => (
              <li key={s.id} className="rounded-lg bg-surface-overlay px-3 py-2 text-sm ring-1 ring-white/[0.04]">
                <span className="font-medium text-slate-200">{s.step}. {s.title}</span>
                <span className="ml-2 text-xs text-slate-500">({s.owner})</span>
                <p className="mt-1 text-xs text-slate-400">{s.detail}</p>
              </li>
            ))}
          </ol>
        </div>
      )}

      {experiments && (
        <div className="glass-card p-5">
          <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
            <FlaskConical className="h-4 w-4" /> Experiments (MLflow-compatible)
          </h3>
          <p className="mb-3 text-xs text-slate-500">
            Experiment: {experiments.experiment_name}
            {experiments.mlflow_tracking_uri ? ` · MLflow URI set` : ' · local store (set MLFLOW_TRACKING_URI for MLflow)'}
            {' · '}{experiments.summary?.total_runs || 0} runs
          </p>
          <div className="mb-3 flex flex-wrap gap-2">
            {Object.entries(experiments.summary?.by_class || {}).map(([k, v]) => (
              <span key={k} className="rounded-lg bg-surface-overlay px-2.5 py-1 text-xs text-slate-400 ring-1 ring-white/[0.06]">
                {k}: {v}
              </span>
            ))}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06] text-left text-xs uppercase tracking-wider text-slate-500">
                  <th className="px-3 py-2">Name</th>
                  <th className="px-3 py-2">Class</th>
                  <th className="px-3 py-2">Stage</th>
                  <th className="px-3 py-2">Key metrics</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {(experiments.runs || []).slice().reverse().map((r) => (
                  <tr key={r.run_id}>
                    <td className="px-3 py-2 text-slate-300">{r.name}</td>
                    <td className="px-3 py-2 text-slate-400">{r.experiment_class}</td>
                    <td className="px-3 py-2"><Badge status={r.stage || 'pending'} /></td>
                    <td className="px-3 py-2 font-mono text-xs text-slate-500">
                      {Object.entries(r.metrics || {}).slice(0, 3).map(([k, v]) => `${k}=${v}`).join(' · ') || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {diffData && (
        <div className="glass-card p-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400"><GitCompare className="mr-2 inline h-4 w-4" /> Diff Viewer</h3>
            <button onClick={() => setDiffData(null)} className="text-xs text-slate-500 hover:text-slate-300">Close</button>
          </div>
          <div className="mb-3 flex items-end gap-3">
            <div className="flex-1">
              <label className="mb-1 block text-xs text-slate-500">Version A</label>
              <select className="input-field w-full text-sm" value={diffA} onChange={e => setDiffA(e.target.value)}>
                <option value="">Select…</option>
                {entries.map(e => <option key={e.entry_id} value={e.entry_id}>{e.name} v{e.version}</option>)}
              </select>
            </div>
            <div className="flex-1">
              <label className="mb-1 block text-xs text-slate-500">Version B</label>
              <select className="input-field w-full text-sm" value={diffB} onChange={e => setDiffB(e.target.value)}>
                <option value="">Select…</option>
                {entries.map(e => <option key={e.entry_id} value={e.entry_id}>{e.name} v{e.version}</option>)}
              </select>
            </div>
            <button type="button" onClick={async () => { try { const d = await endpoints.registryDiff(diffA, diffB); setDiffData(d); } catch (e) { alert(e.message); } }} disabled={!diffA || !diffB} className="btn-primary btn-sm text-xs">Compare</button>
          </div>
          <pre className="max-h-80 overflow-y-auto rounded-lg bg-black/20 p-3 text-xs text-slate-400">{JSON.stringify(diffData, null, 2)}</pre>
        </div>
      )}

      {contextData && (
        <div className="glass-card p-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400"><Globe className="mr-2 inline h-4 w-4" /> Registry Contexts</h3>
            <button onClick={() => setContextData(null)} className="text-xs text-slate-500 hover:text-slate-300">Close</button>
          </div>
          <pre className="max-h-80 overflow-y-auto rounded-lg bg-black/20 p-3 text-xs text-slate-400">{JSON.stringify(contextData, null, 2)}</pre>
        </div>
      )}

      {showForm && (
        <div className="glass-card p-6">
          <h3 className="mb-4 font-semibold">Create Registry Entry</h3>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Name</label>
                <input className="input-field w-full text-sm" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Version</label>
                <input className="input-field w-full text-sm" value={form.version} onChange={e => setForm(f => ({ ...f, version: e.target.value }))} required />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Type</label>
                <select className="input-field w-full text-sm" value={form.model_type} onChange={e => setForm(f => ({ ...f, model_type: e.target.value }))}>
                  <option value="">Select…</option>
                  <option value="rating_engine">Rating Engine</option>
                  <option value="risk_model">Risk Model</option>
                  <option value="guideline">Guideline</option>
                  <option value="pricing_model">Pricing Model</option>
                </select>
              </div>
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-400">Description</label>
              <textarea className="input-field w-full text-sm" rows={3} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
            </div>
            <div className="flex gap-2">
              <button type="submit" className="btn-primary btn-sm">Create</button>
              <button type="button" onClick={() => setShowForm(false)} className="btn-secondary btn-sm">Cancel</button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
        </div>
      ) : entries.length === 0 ? (
        <EmptyState icon={BookOpen} title="No registry entries" description="Create your first model or guideline entry" />
      ) : (
        <div className="glass-card overflow-hidden">
          <div className="border-b border-white/[0.06] px-5 py-3">
            <h3 className="text-sm font-semibold">Registry Entries</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06] bg-surface-overlay text-left text-xs uppercase tracking-wider text-slate-500">
                  <th className="px-6 py-3">Name</th>
                  <th className="px-6 py-3">Version</th>
                  <th className="px-6 py-3">Type</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {entries.map((e) => (
                  <tr key={e.entry_id} className="hover:bg-white/[0.02]">
                    <td className="px-6 py-3.5 text-slate-300">{e.name}</td>
                    <td className="px-6 py-3.5 font-mono text-xs text-slate-400">{e.version}</td>
                    <td className="px-6 py-3.5 text-slate-400">{e.model_type}</td>
                    <td className="px-6 py-3.5"><Badge status={statusColor(e.status)} /></td>
                    <td className="px-6 py-3.5">
                      <div className="flex gap-1">
                        {e.status === 'draft' && (
                          <button onClick={() => handleAction(e.entry_id, 'submit')} className="rounded-lg bg-black/30 px-2 py-1 text-xs text-slate-400 hover:text-slate-200" title="Submit for review"><Send className="h-3 w-3 inline" /> Submit</button>
                        )}
                        {e.status === 'submitted' && (
                          <>
                            <button onClick={() => handleAction(e.entry_id, 'approve')} className="rounded-lg bg-emerald-500/20 px-2 py-1 text-xs text-emerald-400 hover:bg-emerald-500/30" title="Approve"><CheckCircle className="h-3 w-3 inline" /> Approve</button>
                            <button onClick={() => handleAction(e.entry_id, 'reject')} className="rounded-lg bg-red-500/20 px-2 py-1 text-xs text-red-400 hover:bg-red-500/30" title="Reject"><XCircle className="h-3 w-3 inline" /> Reject</button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {snapshots.length > 0 && (
        <div className="glass-card p-5">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">Snapshots</h3>
          <div className="flex flex-wrap gap-2">
            {snapshots.map((s) => (
              <span key={s.snapshot_id} className="rounded-lg bg-surface-overlay px-3 py-1.5 text-xs text-slate-400 ring-1 ring-white/[0.06]">
                {s.snapshot_id} — {new Date(s.created_at).toLocaleDateString()}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
