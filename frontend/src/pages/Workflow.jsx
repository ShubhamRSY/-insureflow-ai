import { useCallback, useEffect, useMemo, useState } from 'react';
import { Badge, EmptyState } from '../components/ui';
import { ClipboardCheck, Shield, Search, FileCheck, Loader2, Clock } from 'lucide-react';
import { endpoints, fmtCurrency } from '../lib/api';
import { toast } from '../lib/toast';
import { decisionLabel, uwReasons, ageInfo, AGE_STYLE } from '../lib/uwLanguage';
import { insuranceLineLabel } from '../lib/insuranceLines';

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

const STATE_BADGE = {
  pending_review: { status: 'pending', label: 'Pending review' },
  pending_co_sign: { status: 'refer', label: 'Needs co-sign' },
  approved: { status: 'approved', label: 'Approved' },
  quoted: { status: 'approved', label: 'Quoted' },
};

const EMPTY_FORM = { action: 'quote', license_number: '', notes: '', override_reason: '', override_reason_category: 'other', uw_confidence: 'medium' };

export default function WorkflowPage({ onRefresh, authorityData, onOpenJob }) {
  const [pending, setPending] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [showSignOff, setShowSignOff] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [workflowDetail, setWorkflowDetail] = useState(null);
  const [detailBundleId, setDetailBundleId] = useState(null);

  const load = useCallback(async () => {
    try {
      const res = await endpoints.uwWorkbench();
      setPending(res.pending || []);
      setError('');
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    const items = q
      ? pending.filter((p) => [p.bundle_id, p.insured_name, p.broker_name].some((v) => (v || '').toLowerCase().includes(q)))
      : pending;
    return [...items].sort((a, b) => new Date(a.created_at || 0) - new Date(b.created_at || 0));
  }, [pending, query]);

  const handleSignOff = async (bundleId) => {
    try {
      await endpoints.signOff(bundleId, form);
      setShowSignOff(null);
      setForm(EMPTY_FORM);
      await load();
      onRefresh?.();
    } catch (e) {
      toast.error(e.message);
    }
  };

  const handleBind = async (bundleId) => {
    try {
      await endpoints.bindPolicy(bundleId);
      await load();
      onRefresh?.();
    } catch (e) {
      toast.error(e.message);
    }
  };

  const getAuthorityLabel = (premium) => {
    if (!authorityData?.authorities || premium == null) return '';
    const tiers = authorityData.authorities;
    for (const t of tiers) {
      if (premium <= t.binding_authority.max_premium) return `${t.tier} (${t.display_name}, max $${(t.binding_authority.max_premium / 1000).toFixed(0)}K)`;
    }
    return 'Needs CUO approval';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        <Loader2 className="h-5 w-5 animate-spin" /> <span className="ml-2 text-sm">Loading sign-off queue…</span>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-8 animate-fade-in">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">UW Sign-off Queue</h1>
          <p className="mt-1 text-slate-400">Licensed underwriter review for insurance submissions</p>
        </div>
        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search insured, broker, bundle id…"
            className="input-field w-56 pl-8 text-xs"
          />
        </div>
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

      {error && <div className="rounded-xl bg-red-500/10 p-4 text-sm text-red-400 ring-1 ring-red-500/20">{error}</div>}

      <div className="glass-card p-6">
        {!visible.length ? (
          <EmptyState
            icon={ClipboardCheck}
            title="Queue empty"
            description={pending.length ? 'No submissions match your search.' : 'No submissions awaiting licensed UW sign-off'}
          />
        ) : (
          <div className="space-y-4">
            {visible.map((p) => {
              const id = p.bundle_id;
              const authLabel = getAuthorityLabel(p.premium);
              const isOpen = showSignOff === id;
              const sb = STATE_BADGE[p.state] || { status: p.state, label: p.state };
              const age = ageInfo(p.created_at);
              const reason = uwReasons(p.human_review_reasons || [])[0];
              return (
                <div key={id} className="rounded-xl border border-white/[0.06] bg-surface-overlay p-5">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-sm font-semibold">{id}</span>
                        <Badge status={sb.status} label={sb.label} />
                        {age && (
                          <span className={`inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] ring-1 ring-inset ${AGE_STYLE[age.level]}`}>
                            <Clock className="h-2.5 w-2.5" /> {age.label}
                          </span>
                        )}
                      </div>
                      <p className="mt-1 text-sm font-medium text-white">{p.insured_name || 'Submission'}</p>
                      <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-400">
                        {p.insurance_line && <span>{insuranceLineLabel(p.insurance_line)}</span>}
                        {p.broker_name && <span>Broker: {p.broker_name}</span>}
                        {authLabel && <span>{authLabel}</span>}
                      </div>
                    </div>
                    {p.premium != null && (
                      <span className="font-mono text-lg font-bold text-white">{fmtCurrency(p.premium)}</span>
                    )}
                  </div>

                  <p className="mt-2 text-sm text-slate-400">
                    {reason ? `Why: ${reason}` : p.ai_decision ? `AI recommendation: ${decisionLabel(p.ai_decision)}` : 'Awaiting review'}
                  </p>

                  <div className="mt-4 flex flex-wrap gap-2">
                    <button type="button" onClick={() => onOpenJob?.('insurance', id, id)} className="btn-secondary text-xs">View</button>
                    <button type="button" onClick={() => { setShowSignOff(id); setForm((f) => ({ ...f, action: 'quote' })); }} className="btn-primary btn-sm text-xs">Quote</button>
                    <button type="button" onClick={() => { setShowSignOff(id); setForm((f) => ({ ...f, action: 'no_quote' })); }} className="btn-danger">No quote</button>
                    <button type="button" onClick={() => { setShowSignOff(id); setForm((f) => ({ ...f, action: 'request_info' })); }} className="btn-secondary text-xs">Request info</button>
                    <button type="button" onClick={() => { setShowSignOff(id); setForm((f) => ({ ...f, action: 'refer' })); }} className="btn-secondary text-xs">Refer</button>
                    {(p.state === 'approved' || p.state === 'quoted') && (
                      <button type="button" onClick={() => handleBind(id)} className="btn-success"><FileCheck className="h-3 w-3 inline" /> Bind</button>
                    )}
                    <button type="button" onClick={async () => { setDetailBundleId(id); try { const d = await endpoints.workflowDetail(id); setWorkflowDetail(d); } catch (e) { toast.error(e.message); } }} className="btn-secondary text-xs"><Search className="h-3 w-3 inline" /> Detail</button>
                  </div>

                  {isOpen && (
                    <div className="mt-4 space-y-3 rounded-lg bg-black/20 p-4">
                      <div className="grid gap-3 sm:grid-cols-2">
                        <input
                          type="text" placeholder="License number" className="input-field w-full text-sm"
                          value={form.license_number} onChange={(e) => setForm((f) => ({ ...f, license_number: e.target.value }))}
                        />
                        <select
                          className="input-field w-full text-sm"
                          value={form.override_reason_category} onChange={(e) => setForm((f) => ({ ...f, override_reason_category: e.target.value }))}
                        >
                          <option value="">Reason category…</option>
                          {REASON_CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                        </select>
                        <select
                          className="input-field w-full text-sm"
                          value={form.uw_confidence} onChange={(e) => setForm((f) => ({ ...f, uw_confidence: e.target.value }))}
                        >
                          <option value="low">Low confidence</option>
                          <option value="medium">Medium confidence</option>
                          <option value="high">High confidence</option>
                        </select>
                        <input
                          type="text" placeholder="Override reason" className="input-field w-full text-sm"
                          value={form.override_reason} onChange={(e) => setForm((f) => ({ ...f, override_reason: e.target.value }))}
                        />
                      </div>
                      <textarea
                        placeholder={form.action === 'request_info' ? 'What do you need from the broker? (e.g. docs: loss run, SOV)' : form.action === 'no_quote' ? 'Why no quote?' : 'Notes…'}
                        className="input-field w-full text-sm" rows={2}
                        value={form.notes} onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                      />
                      <div className="flex gap-2">
                        <button type="button" onClick={() => handleSignOff(id)} className="btn-primary btn-sm text-xs">
                          Confirm {decisionLabel(form.action)}
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
                          <p className="font-medium text-slate-300">{(STATE_BADGE[workflowDetail.state]?.label) || workflowDetail.state || workflowDetail.status || '—'}</p>
                        </div>
                        <div className="rounded bg-surface-overlay p-2">
                          <span className="text-slate-500">Decision</span>
                          <p className="font-medium text-slate-300">{workflowDetail.decision ? decisionLabel(workflowDetail.decision) : '—'}</p>
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
                              <span className="ml-2 text-slate-500">{decisionLabel(so.action)} by {so.username || '—'}</span>
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
