import { useState, useEffect, useCallback } from 'react';
import { Database, RefreshCw, Plus, Trash2 } from 'lucide-react';
import { EmptyState, Badge } from '../components/ui';
import { endpoints } from '../lib/api';

export default function WebhooksPage() {
  const [webhooks, setWebhooks] = useState([]);
  const [mortgageWebhooks, setMortgageWebhooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [vertical, setVertical] = useState('insurance');
  const [form, setForm] = useState({ url: '', events: 'mortgage.completed' });

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [ins, mort] = await Promise.all([
        endpoints.insuranceWebhooks().catch(() => ({ subscriptions: [] })),
        endpoints.mortgageWebhooks().catch(() => ({ subscriptions: [] })),
      ]);
      setWebhooks(ins.subscriptions || []);
      setMortgageWebhooks(mort.subscriptions || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleRegister = async (e) => {
    e.preventDefault();
    try {
      const body = { url: form.url, events: [form.events] };
      if (vertical === 'insurance') {
        await endpoints.registerInsuranceWebhook(body);
      } else {
        await endpoints.registerMortgageWebhook(body);
      }
      setShowForm(false);
      setForm({ url: '', events: 'mortgage.completed' });
      await load();
    } catch (e) {
      alert(e.message);
    }
  };

  const handleDelete = async (id, vert) => {
    try {
      if (vert === 'insurance') {
        await endpoints.deleteWebhook(id);
      } else {
        await endpoints.deleteMortgageWebhook(id);
      }
      await load();
    } catch (e) {
      alert(e.message);
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-8 animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-sky-500/15">
            <Database className="h-6 w-6 text-sky-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Webhooks</h1>
            <p className="mt-1 text-slate-400">HMAC-signed event subscriptions for insurance and mortgage</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={() => { setShowForm(true); setVertical('insurance'); }} className="btn-primary btn-sm text-xs"><Plus className="h-3.5 w-3.5" /> Insurance</button>
          <button type="button" onClick={() => { setShowForm(true); setVertical('mortgage'); }} className="btn-primary btn-sm text-xs"><Plus className="h-3.5 w-3.5" /> Mortgage</button>
          <button type="button" onClick={load} className="btn-secondary btn-sm text-xs"><RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /></button>
        </div>
      </div>

      {error && <div className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}

      {showForm && (
        <div className="glass-card p-6">
          <h3 className="mb-4 font-semibold">Register Webhook ({vertical})</h3>
          <form onSubmit={handleRegister} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-400">Callback URL</label>
              <input className="input-field w-full text-sm" value={form.url} onChange={e => setForm(f => ({ ...f, url: e.target.value }))} required placeholder="https://example.com/webhook" />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-400">Event</label>
              <select className="input-field w-full text-sm" value={form.events} onChange={e => setForm(f => ({ ...f, events: e.target.value }))}>
                <option value="mortgage.completed">mortgage.completed</option>
                <option value="mortgage.failed">mortgage.failed</option>
                <option value="insurance.completed">insurance.completed</option>
                <option value="insurance.signoff">insurance.signoff</option>
              </select>
            </div>
            <div className="flex gap-2">
              <button type="submit" className="btn-primary btn-sm">Register</button>
              <button type="button" onClick={() => setShowForm(false)} className="btn-secondary btn-sm">Cancel</button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
        </div>
      ) : (
        <>
          {webhooks.length > 0 && (
            <div className="glass-card overflow-hidden">
              <div className="border-b border-white/[0.06] px-5 py-3">
                <h3 className="text-sm font-semibold">Insurance Webhooks</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/[0.06] bg-surface-overlay text-left text-xs uppercase tracking-wider text-slate-500">
                      <th className="px-6 py-3">ID</th>
                      <th className="px-6 py-3">URL</th>
                      <th className="px-6 py-3">Events</th>
                      <th className="px-6 py-3">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.04]">
                    {webhooks.map((w) => (
                      <tr key={w.id || w.subscription_id} className="hover:bg-white/[0.02]">
                        <td className="px-6 py-3.5 font-mono text-xs text-slate-400">{w.id || w.subscription_id}</td>
                        <td className="px-6 py-3.5 text-xs text-slate-300">{w.url}</td>
                        <td className="px-6 py-3.5">{w.events?.map((e) => <Badge key={e} status={e} />)}</td>
                        <td className="px-6 py-3.5">
                          <button onClick={() => handleDelete(w.id || w.subscription_id, 'insurance')} className="rounded-lg p-1.5 text-red-400 hover:bg-red-500/10"><Trash2 className="h-4 w-4" /></button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {mortgageWebhooks.length > 0 && (
            <div className="glass-card overflow-hidden">
              <div className="border-b border-white/[0.06] px-5 py-3">
                <h3 className="text-sm font-semibold">Mortgage Webhooks</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/[0.06] bg-surface-overlay text-left text-xs uppercase tracking-wider text-slate-500">
                      <th className="px-6 py-3">ID</th>
                      <th className="px-6 py-3">URL</th>
                      <th className="px-6 py-3">Events</th>
                      <th className="px-6 py-3">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.04]">
                    {mortgageWebhooks.map((w) => (
                      <tr key={w.id || w.subscription_id} className="hover:bg-white/[0.02]">
                        <td className="px-6 py-3.5 font-mono text-xs text-slate-400">{w.id || w.subscription_id}</td>
                        <td className="px-6 py-3.5 text-xs text-slate-300">{w.url}</td>
                        <td className="px-6 py-3.5">{w.events?.map((e) => <Badge key={e} status={e} />)}</td>
                        <td className="px-6 py-3.5">
                          <button onClick={() => handleDelete(w.id || w.subscription_id, 'mortgage')} className="rounded-lg p-1.5 text-red-400 hover:bg-red-500/10"><Trash2 className="h-4 w-4" /></button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {webhooks.length === 0 && mortgageWebhooks.length === 0 && (
            <EmptyState icon={Database} title="No webhooks" description="Register a webhook to receive event notifications" />
          )}
        </>
      )}
    </div>
  );
}
