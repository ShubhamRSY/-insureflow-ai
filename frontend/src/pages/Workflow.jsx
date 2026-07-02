import { useState } from 'react';
import { Badge, EmptyState } from '../components/ui';
import { ClipboardCheck, Shield, Search, FileCheck } from 'lucide-react';
import { endpoints } from '../lib/api';

const REASON_CATEGORIES = [
  { value: 'pricing', label: 'Pricing' },
  { value: 'coverage', label: 'Coverage' },
  { value: 'terms', label: 'Terms' },
  { value: 'appetite', label: 'Appetite' },
  { value: 'compliance', label: 'Compliance' },
  { value: 'data_quality', label: 'Data Quality' },
  { value: 'market_conditions', label: 'Market Conditions' },
  { value: 'client_relationship', label: 'Client Relationship' },
  { value: 'erroneous_ai', label: 'Erroneous AI' },
  { value: 'other', label: 'Other' },
];

export default function WorkflowPage({ pending, onRefresh, authorityData, onOpenJob }) {
  const [showSignOff, setShowSignOff] = useState(null);
  const [form, setForm] = useState({ action: 'approve', license_number: '', notes: '', override_reason: '', override_reason_category: 'other', uw_confidence: 'medium' });
  const [workflowDetail, setWorkflowDetail] = useState(null);
  const [detailBundleId, setDetailBundleId] = useState(null);

  const handleSignOff = async (bundleId) => {
    try {
      await endpoints.signOff(bundleId, form);
      setShowSignOff(null);
      setForm({ action: 'approve', license_number: '', notes: '', override_reason: '', override_reason_category: 'other', uw_confidence: 'medium' });
      onRefresh();
    } catch (e) {
      alert(e.message);
    }
  };

  const getAuthorityLabel = (premium) => {
    if (!authorityData?.authorities) return '';
    const tiers = authorityData.authorities;
    for (const t of tiers) {
      if (premium <= t.binding_authority.max_premium) return `${t.tier} (${t.display_name}, max $${(t.binding_authority.max_premium / 1000).toFixed(0)}K)`;
    }
    return 'Needs CUO approval';
  };

  return (
    <div className="mx-auto max-w-4xl space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">UW Sign-off Queue</h1>
        <p className="mt-1 text-slate-400">Licensed underwriter review for insurance submissions</p>
      </div>

      {authorityData?.authorities && (
        <div className="flex flex-wrap gap-2">
          {authorityData.authorities.map((a) => (
            <span key={a.username} className="inline-flex items-center gap-1.5 rounded-full bg-surface-overlay px-3 py-1 text-xs text-slate-300 ring-1 ring-white/[0.06]">
              <Shield className="h-3 w-3" />
              {a.display_name} — {a.tier} (${(a.binding_authority.max_premium / 1000).toFixed(0)}K)
            </span>
          ))}
        </div>
      )}

      <div className="glass-card p-6">
        {!pending?.length ? (
          <EmptyState icon={ClipboardCheck} title="Queue empty" description="No submissions awaiting licensed UW sign-off" />
        ) : (
          <div className="space-y-4">
            {pending.map((p) => {
              const id = typeof p === 'string' ? p : (p.bundle_id || p.bundleId || '');
              const premium = typeof p === 'string' ? 0 : (p.premium || p.estimated_premium || 0);
              const authLabel = getAuthorityLabel(premium);
              const isOpen = showSignOff === id;
              return (
                <div key={id} className="rounded-xl border border-white/[0.06] bg-surface-overlay p-5">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <span className="font-mono text-sm font-semibold">{id}</span>
                      {authLabel && <span className="ml-2 text-xs text-slate-500">({authLabel})</span>}
                    </div>
                    <Badge status={p.state || p.status || 'pending'} />
                  </div>
                  <p className="mt-2 text-sm text-slate-400">{p.recommendation || p.decision || 'Awaiting review'}</p>

                    <div className="mt-4 flex flex-wrap gap-2">
                      <button type="button" onClick={() => onOpenJob?.('insurance', id, id)} className="btn-secondary text-xs">View</button>
                      <button type="button" onClick={() => { setShowSignOff(id); setForm(f => ({ ...f, action: 'approve' })); }} className="btn-primary btn-sm text-xs">Approve</button>
                      <button type="button" onClick={() => { setShowSignOff(id); setForm(f => ({ ...f, action: 'refer' })); }} className="btn-secondary text-xs">Refer</button>
                      <button type="button" onClick={() => { setShowSignOff(id); setForm(f => ({ ...f, action: 'decline' })); }} className="rounded-xl px-3 py-1.5 text-xs text-red-400 ring-1 ring-red-500/30 hover:bg-red-500/10">Decline</button>
                      {p.state === 'approved' && (
                        <button type="button" onClick={async () => { await endpoints.bindPolicy(id).catch(e => alert(e.message)); onRefresh?.(); }} className="rounded-xl px-3 py-1.5 text-xs text-emerald-400 ring-1 ring-emerald-500/30 hover:bg-emerald-500/10"><FileCheck className="h-3 w-3 inline" /> Bind</button>
                      )}
                      <button type="button" onClick={async () => { setDetailBundleId(id); try { const d = await endpoints.workflowDetail(id); setWorkflowDetail(d); } catch (e) { alert(e.message); } }} className="btn-secondary text-xs"><Search className="h-3 w-3 inline" /> Detail</button>
                    </div>

                  {isOpen && (
                    <div className="mt-4 space-y-3 rounded-lg bg-black/20 p-4">
                      <div className="grid gap-3 sm:grid-cols-2">
                        <input
                          type="text" placeholder="License number" className="input-field w-full text-sm"
                          value={form.license_number} onChange={e => setForm(f => ({ ...f, license_number: e.target.value }))}
                        />
                        <select
                          className="input-field w-full text-sm"
                          value={form.override_reason_category} onChange={e => setForm(f => ({ ...f, override_reason_category: e.target.value }))}
                        >
                          <option value="">Reason category…</option>
                          {REASON_CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                        </select>
                        <select
                          className="input-field w-full text-sm"
                          value={form.uw_confidence} onChange={e => setForm(f => ({ ...f, uw_confidence: e.target.value }))}
                        >
                          <option value="low">Low confidence</option>
                          <option value="medium">Medium confidence</option>
                          <option value="high">High confidence</option>
                        </select>
                        <input
                          type="text" placeholder="Override reason" className="input-field w-full text-sm"
                          value={form.override_reason} onChange={e => setForm(f => ({ ...f, override_reason: e.target.value }))}
                        />
                      </div>
                      <textarea
                        placeholder="Notes…" className="input-field w-full text-sm" rows={2}
                        value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
                      />
                      <div className="flex gap-2">
                        <button type="button" onClick={() => handleSignOff(id)} className="btn-primary btn-sm text-xs">
                          Confirm {form.action}
                        </button>
                        <button type="button" onClick={() => setShowSignOff(null)} className="btn-secondary text-xs">Cancel</button>
                      </div>
                    </div>
                  )}

                  {workflowDetail && detailBundleId === id && (
                    <div className="mt-4 rounded-lg bg-black/20 p-3">
                      <div className="mb-2 flex items-center justify-between">
                        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Workflow State</p>
                        <button onClick={() => { setWorkflowDetail(null); setDetailBundleId(null); }} className="text-xs text-slate-500 hover:text-slate-300">Close</button>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div className="rounded bg-surface-overlay p-2">
                          <span className="text-slate-500">State</span>
                          <p className="font-medium text-slate-300">{workflowDetail.state || workflowDetail.status || '—'}</p>
                        </div>
                        <div className="rounded bg-surface-overlay p-2">
                          <span className="text-slate-500">Decision</span>
                          <p className="font-medium text-slate-300">{workflowDetail.decision || '—'}</p>
                        </div>
                        <div className="rounded bg-surface-overlay p-2">
                          <span className="text-slate-500">Sign-offs</span>
                          <p className="font-medium text-slate-300">{(workflowDetail.sign_offs || workflowDetail.signoffs || []).length}</p>
                        </div>
                        <div className="rounded bg-surface-overlay p-2">
                          <span className="text-slate-500">Created</span>
                          <p className="font-medium text-slate-300">{workflowDetail.created_at ? new Date(workflowDetail.created_at).toLocaleString() : '—'}</p>
                        </div>
                      </div>
                      {(workflowDetail.sign_offs || workflowDetail.signoffs || []).length > 0 && (
                        <div className="mt-2 space-y-1">
                          <p className="text-[10px] font-semibold uppercase text-slate-500">Sign-off History</p>
                          {(workflowDetail.sign_offs || workflowDetail.signoffs || []).map((so, i) => (
                            <div key={i} className="rounded bg-surface-overlay p-2 text-xs">
                              <span className="text-slate-400">{so.license_number || so.license || '—'}</span>
                              <span className="ml-2 text-slate-500">{so.action} by {so.username || '—'}</span>
                              {so.notes && <p className="text-slate-500">{so.notes}</p>}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
