import { useState, useEffect, useCallback } from 'react';
import { Users, Shield, RefreshCw, Plus, Pencil, Trash2, X, Loader2, ShieldCheck } from 'lucide-react';
import { Badge, EmptyState } from '../components/ui';
import { endpoints, fmtCurrency } from '../lib/api';
import { useOutletContext } from 'react-router-dom';

const TIERS = [
  { value: 'junior', label: 'Junior UW', desc: 'Simple, small accounts (< $25K premium)' },
  { value: 'senior', label: 'Senior UW', desc: 'Complex/high-value (up to $500K)' },
  { value: 'cuo', label: 'Chief UW Officer', desc: 'Unlimited authority' },
  { value: 'mga', label: 'MGA', desc: 'Managing General Agent (delegated)' },
];

const TIER_DEFAULTS = {
  junior: { max_premium: 25000, max_tiv: 1000000, max_aggregate_exposure: 5000000, requires_co_sign: false, co_sign_threshold_premium: 0 },
  senior: { max_premium: 250000, max_tiv: 10000000, max_aggregate_exposure: 25000000, requires_co_sign: false, co_sign_threshold_premium: 150000 },
  cuo: { max_premium: 10000000, max_tiv: 500000000, max_aggregate_exposure: 500000000, requires_co_sign: false, co_sign_threshold_premium: 0 },
  mga: { max_premium: 100000, max_tiv: 5000000, max_aggregate_exposure: 20000000, requires_co_sign: false, co_sign_threshold_premium: 0 },
};

const tierConfig = {
  junior: { label: 'Junior UW', color: 'text-sky-400', ring: 'ring-sky-500/20', bg: 'bg-sky-500/10' },
  senior: { label: 'Senior UW', color: 'text-brand-light', ring: 'ring-brand/20', bg: 'bg-brand/10' },
  cuo: { label: 'Chief UW Officer', color: 'text-purple-400', ring: 'ring-purple-500/20', bg: 'bg-purple-500/10' },
  mga: { label: 'MGA', color: 'text-amber-400', ring: 'ring-amber-500/20', bg: 'bg-amber-500/10' },
};

const EMPTY_FORM = {
  username: '',
  display_name: '',
  tier: 'junior',
  license_number: '',
  max_premium: '',
  max_tiv: '',
  max_aggregate_exposure: '',
  requires_co_sign: false,
  co_sign_threshold_premium: '',
};

export default function AuthorityMatrix() {
  const { user } = useOutletContext() || {};
  const isAdmin = user?.role === 'admin';

  const [matrix, setMatrix] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await endpoints.authorityMatrix();
      setMatrix(data.authorities || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const openAdd = () => {
    setEditing(null);
    setForm({ ...EMPTY_FORM, ...TIER_DEFAULTS.junior });
    setModalOpen(true);
  };

  const openEdit = (a) => {
    setEditing(a);
    const ba = a.binding_authority || {};
    setForm({
      username: a.username,
      display_name: a.display_name,
      tier: a.tier,
      license_number: a.license_number || '',
      max_premium: ba.max_premium ?? '',
      max_tiv: ba.max_tiv ?? '',
      max_aggregate_exposure: ba.max_aggregate_exposure ?? '',
      requires_co_sign: !!ba.requires_co_sign,
      co_sign_threshold_premium: ba.co_sign_threshold_premium ?? '',
    });
    setModalOpen(true);
  };

  const onTierChange = (tier) => {
    const next = { ...form, tier };
    if (!editing) {
      const d = TIER_DEFAULTS[tier] || TIER_DEFAULTS.junior;
      next.max_premium = d.max_premium;
      next.max_tiv = d.max_tiv;
      next.max_aggregate_exposure = d.max_aggregate_exposure;
      next.requires_co_sign = d.requires_co_sign;
      next.co_sign_threshold_premium = d.co_sign_threshold_premium;
    }
    setForm(next);
  };

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      const body = {
        username: form.username.trim(),
        display_name: form.display_name.trim(),
        tier: form.tier,
        license_number: form.license_number.trim(),
        max_premium: Number(form.max_premium) || 0,
        max_tiv: Number(form.max_tiv) || 0,
        max_aggregate_exposure: Number(form.max_aggregate_exposure) || 0,
        requires_co_sign: !!form.requires_co_sign,
        co_sign_threshold_premium: Number(form.co_sign_threshold_premium) || 0,
      };
      await endpoints.upsertAuthority(body);
      setModalOpen(false);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const remove = async (a) => {
    if (!window.confirm(`Delete authority record for "${a.display_name}" (${a.username})?`)) return;
    setDeleting(a.username);
    setError('');
    try {
      await endpoints.deleteAuthority(a.username);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setDeleting('');
    }
  };

  return (
    <div className="mx-auto max-w-6xl space-y-8 animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-cyan-500/15">
            <Shield className="h-6 w-6 text-cyan-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Authority Matrix</h1>
            <p className="mt-1 text-slate-400">Delegation of authority and binding limits</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isAdmin && (
            <button type="button" onClick={openAdd} className="btn-primary btn-sm text-xs">
              <Plus className="h-3.5 w-3.5" /> Add Underwriter
            </button>
          )}
          <button type="button" onClick={load} className="btn-secondary btn-sm text-xs">
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>
      </div>

      {isAdmin && (
        <div className="rounded-xl border border-brand/20 bg-brand/5 px-4 py-3 text-xs text-brand-light">
          <ShieldCheck className="mr-1.5 inline h-3.5 w-3.5" />
          Admin mode — you can add, edit, and remove authority records. Changes apply immediately.
        </div>
      )}

      {error && (
        <div className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>
      )}

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
        </div>
      ) : matrix.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No authority records"
          description="Configure UW tiers in settings"
          action={isAdmin && (
            <button type="button" onClick={openAdd} className="btn-primary">
              <Plus className="h-4 w-4" /> Add Underwriter
            </button>
          )}
        />
      ) : (
        <>
          {/* Tier Overview Cards */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Object.entries(tierConfig).map(([key, cfg]) => {
              const uws = matrix.filter(a => a.tier === key);
              if (!uws.length) return null;
              return (
                <div key={key} className={`glass-card rounded-xl border ${cfg.ring} p-5`}>
                  <div className={`inline-flex rounded-lg ${cfg.bg} px-2.5 py-1 text-xs font-semibold ${cfg.color}`}>
                    {cfg.label}
                  </div>
                  <p className="mt-3 text-2xl font-bold">{uws.length}</p>
                  <p className="text-xs text-slate-500">underwriters</p>
                </div>
              );
            })}
          </div>

          {/* Detailed Table */}
          <div className="glass-card overflow-hidden">
            <div className="border-b border-white/[0.06] px-5 py-4">
              <h3 className="font-semibold">Binding Authority Details</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/[0.04] text-xs uppercase tracking-wider text-slate-500">
                    <th className="px-5 py-3 text-left">Name</th>
                    <th className="px-5 py-3 text-left">Username</th>
                    <th className="px-5 py-3 text-left">Tier</th>
                    <th className="px-5 py-3 text-right">Max Premium</th>
                    <th className="px-5 py-3 text-right">Max TIV</th>
                    <th className="px-5 py-3 text-right">Aggregate Cap</th>
                    <th className="px-5 py-3 text-center">Co-Sign</th>
                    <th className="px-5 py-3 text-left">License</th>
                    {isAdmin && <th className="px-5 py-3 text-right">Actions</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  {matrix.map((a) => {
                    const cfg = tierConfig[a.tier] || {};
                    const ba = a.binding_authority || {};
                    return (
                      <tr key={a.username} className="hover:bg-white/[0.02]">
                        <td className="px-5 py-3 font-medium text-white">{a.display_name}</td>
                        <td className="px-5 py-3 font-mono text-xs text-slate-400">{a.username}</td>
                        <td className="px-5 py-3">
                          <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset capitalize ${cfg.color} ${cfg.bg} ${cfg.ring}`}>
                            {a.tier}
                          </span>
                        </td>
                        <td className="px-5 py-3 text-right font-mono">{fmtCurrency(ba.max_premium)}</td>
                        <td className="px-5 py-3 text-right font-mono">{fmtCurrency(ba.max_tiv)}</td>
                        <td className="px-5 py-3 text-right font-mono text-slate-400">{fmtCurrency(ba.max_aggregate_exposure)}</td>
                        <td className="px-5 py-3 text-center">
                          {ba.requires_co_sign ? (
                            <Badge status="Yes" />
                          ) : ba.co_sign_threshold_premium ? (
                            <span className="text-xs text-amber-400">&gt;{fmtCurrency(ba.co_sign_threshold_premium)}</span>
                          ) : (
                            <span className="text-xs text-slate-500">No</span>
                          )}
                        </td>
                        <td className="px-5 py-3 text-xs text-slate-400">{a.license_number || '\u2014'}</td>
                        {isAdmin && (
                          <td className="px-5 py-3">
                            <div className="flex items-center justify-end gap-1.5">
                              <button type="button" onClick={() => openEdit(a)} className="rounded-lg p-1.5 text-slate-400 transition hover:bg-white/[0.06] hover:text-brand-light" title="Edit">
                                <Pencil className="h-3.5 w-3.5" />
                              </button>
                              <button type="button" onClick={() => remove(a)} disabled={deleting === a.username} className="rounded-lg p-1.5 text-slate-400 transition hover:bg-red-500/10 hover:text-red-400" title="Delete">
                                {deleting === a.username ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
                              </button>
                            </div>
                          </td>
                        )}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* Add / Edit Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm animate-fade-in">
          <div className="glass-card relative w-full max-w-lg p-7 animate-slide-up">
            <button type="button" onClick={() => setModalOpen(false)} className="absolute right-4 top-4 rounded-lg p-1 text-slate-500 hover:text-slate-300">
              <X className="h-5 w-5" />
            </button>

            <h2 className="text-xl font-bold tracking-tight">
              {editing ? 'Edit Underwriter' : 'Add Underwriter'}
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              {editing ? `Updating authority for ${editing.username}` : 'Delegation of authority and binding limits'}
            </p>

            <form onSubmit={submit} className="mt-5 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-400">Username</label>
                  <input
                    className="input-field"
                    value={form.username}
                    onChange={(e) => setForm({ ...form, username: e.target.value })}
                    placeholder="jdoe"
                    required
                    disabled={!!editing}
                    readOnly={!!editing}
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-400">Display name</label>
                  <input
                    className="input-field"
                    value={form.display_name}
                    onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                    placeholder="Jane Doe"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-400">Tier</label>
                  <select
                    className="input-field"
                    value={form.tier}
                    onChange={(e) => onTierChange(e.target.value)}
                  >
                    {TIERS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                  <p className="mt-1 text-[10px] text-slate-500">
                    {TIERS.find((t) => t.value === form.tier)?.desc}
                  </p>
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-400">License number</label>
                  <input
                    className="input-field"
                    value={form.license_number}
                    onChange={(e) => setForm({ ...form, license_number: e.target.value })}
                    placeholder="P&C-00000-TX"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-400">Max premium ($)</label>
                  <input
                    className="input-field"
                    type="number"
                    min="0"
                    value={form.max_premium}
                    onChange={(e) => setForm({ ...form, max_premium: e.target.value })}
                    required
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-400">Max TIV ($)</label>
                  <input
                    className="input-field"
                    type="number"
                    min="0"
                    value={form.max_tiv}
                    onChange={(e) => setForm({ ...form, max_tiv: e.target.value })}
                    required
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-400">Aggregate cap ($)</label>
                  <input
                    className="input-field"
                    type="number"
                    min="0"
                    value={form.max_aggregate_exposure}
                    onChange={(e) => setForm({ ...form, max_aggregate_exposure: e.target.value })}
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-400">Co-sign threshold ($)</label>
                  <input
                    className="input-field"
                    type="number"
                    min="0"
                    value={form.co_sign_threshold_premium}
                    onChange={(e) => setForm({ ...form, co_sign_threshold_premium: e.target.value })}
                    placeholder="Above this premium, co-sign required"
                  />
                </div>
                <div className="flex items-end pb-1">
                  <label className="flex cursor-pointer items-center gap-2 text-xs font-medium text-slate-400">
                    <input
                      type="checkbox"
                      className="h-4 w-4 accent-brand"
                      checked={form.requires_co_sign}
                      onChange={(e) => setForm({ ...form, requires_co_sign: e.target.checked })}
                    />
                    Always requires co-sign
                  </label>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 border-t border-white/[0.06] pt-4">
                <button type="button" onClick={() => setModalOpen(false)} className="btn-secondary btn-sm">
                  Cancel
                </button>
                <button type="submit" disabled={saving} className="btn-primary btn-sm disabled:opacity-40">
                  {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ShieldCheck className="h-3.5 w-3.5" />}
                  {editing ? 'Save Changes' : 'Add Underwriter'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
