import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Badge, EmptyState, StatCard } from '../components/ui';
import { endpoints, fmtCurrency, AuthError } from '../lib/api';
import { uwReasons } from '../lib/uwLanguage';
import { insuranceLineLabel } from '../lib/insuranceLines';
import {
  ShieldCheck, Inbox, FileCheck, History, Search, Loader2, Layers, AlertTriangle, GitCompare, UserCheck, CircleCheck, HandCoins,
} from 'lucide-react';

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
  approved: { status: 'approved', label: 'Approved — ready to bind' },
  quoted: { status: 'approved', label: 'Quoted — ready to bind' },
  declined: { status: 'decline', label: 'Declined' },
  no_quote: { status: 'decline', label: 'No quote' },
  bound: { status: 'bound', label: 'Bound' },
  expired: { status: 'closed', label: 'Expired' },
  archived: { status: 'closed', label: 'Archived memo' },
};

const EMPTY_FORM = {
  action: 'quote',
  license_number: '',
  notes: '',
  override_reason: '',
  override_reason_category: 'other',
  uw_confidence: 'medium',
  uw_indicated_premium: '',
  uw_limit: '',
  uw_deductible: '',
};

function formatError(e) {
  let msg = e?.message || String(e);
  try {
    const parsed = JSON.parse(msg);
    if (parsed.message) {
      const extra = parsed.open_conditions?.length
        ? `\n\nOpen conditions:\n${parsed.open_conditions.map((c) => `  · ${c}`).join('\n')}`
        : parsed.open_checkpoints?.length
          ? `\n\nOpen checkpoints:\n${parsed.open_checkpoints.map((c) => `  · ${c.label || c.id || ''}`).join('\n')}`
          : parsed.hint
            ? `\n\n${parsed.hint}`
            : '';
      msg = parsed.message + extra;
    }
  } catch { /* keep raw */ }
  return msg;
}

function checkpointLabel(name) {
  return {
    oracle_review: 'Oracle review',
    reconciliation_review: 'Reconciliation',
    uw_signoff: 'UW sign-off',
    external_validation: 'External validation',
  }[name] || name?.replace(/_/g, ' ');
}

export default function UWWorkbench({ onOpenJob, authorityData, onRefresh }) {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState('inbox');
  const [signingId, setSigningId] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [busy, setBusy] = useState(null);

  const load = useCallback(async () => {
    try {
      const res = await endpoints.uwWorkbench();
      setData(res);
      setError(null);
    } catch (e) {
      if (e instanceof AuthError) throw e;
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const afterMutate = async () => {
    setBusy(null);
    setSigningId(null);
    setForm(EMPTY_FORM);
    await load();
    onRefresh?.();
  };

  const handleSignOff = async (bundleId) => {
    setBusy(bundleId);
    try {
      const body = { ...form };
      if (body.uw_indicated_premium !== '') body.uw_indicated_premium = parseFloat(body.uw_indicated_premium);
      else delete body.uw_indicated_premium;
      if (body.uw_limit !== '') body.uw_limit = parseFloat(body.uw_limit);
      else delete body.uw_limit;
      if (body.uw_deductible !== '') body.uw_deductible = parseFloat(body.uw_deductible);
      else delete body.uw_deductible;
      await endpoints.signOff(bundleId, body);
      await afterMutate();
    } catch (e) {
      setBusy(null);
      alert(formatError(e));
    }
  };

  const handleBind = async (bundleId) => {
    if (!window.confirm(`Bind policy for ${bundleId}?`)) return;
    setBusy(bundleId);
    try {
      await endpoints.bindPolicy(bundleId);
      await afterMutate();
    } catch (e) {
      setBusy(null);
      alert(formatError(e));
    }
  };

  const handleResolveCheckpoint = async (bundleId, checkpointId) => {
    setBusy(`cp:${bundleId}:${checkpointId}`);
    try {
      await endpoints.resolveCheckpoint(bundleId, checkpointId, 'approve');
      await afterMutate();
    } catch (e) {
      setBusy(null);
      alert(formatError(e));
    }
  };

  const getAuthorityLabel = (premium) => {
    if (!authorityData?.authorities || premium == null) return '';
    for (const t of authorityData.authorities) {
      if (premium <= t.binding_authority.max_premium) {
        return `${t.tier} · ${t.display_name}`;
      }
    }
    return 'CUO approval required';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        <Loader2 className="h-5 w-5 animate-spin" /> <span className="ml-2 text-sm">Loading workbench…</span>
      </div>
    );
  }

  const totals = data?.totals || {};
  const lists = { inbox: data?.pending || [], bind: data?.approved || [], done: data?.done || [] };
  const cards = lists[tab] || [];
  const pendingCount = totals.pending || 0;
  const bindCount = totals.approved || 0;
  const coSignCount = totals.co_sign || 0;

  return (
    <div className="mx-auto max-w-6xl space-y-8 animate-fade-in">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">UW Workbench</h1>
          <p className="mt-1 text-slate-400">Every case, every decision, one desk — with sign-off, co-sign, and bind. Old memos survive Redis in Prior decisions.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => navigate('/prior-decisions')} className="btn-secondary btn-sm text-xs">
            <History className="h-3.5 w-3.5" /> Prior decisions
          </button>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-surface-overlay px-3 py-1 text-xs text-slate-300 ring-1 ring-white/[0.06]">
            <UserCheck className="h-3 w-3" /> Desk routing: {coSignCount > 0 ? `${coSignCount} need co-sign` : 'within authority'}
          </span>
          {authorityData?.authorities?.map((a) => (
            <span key={a.username} className="inline-flex items-center gap-1.5 rounded-full bg-surface-overlay px-3 py-1 text-xs text-slate-300 ring-1 ring-white/[0.06]">
              <ShieldCheck className="h-3 w-3 text-teal-400" /> {a.display_name} · {a.tier}
            </span>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Awaiting UW" value={pendingCount} sub="review or co-sign" accent="brand" />
        <StatCard label="Ready to bind" value={bindCount} sub="quoted / approved" accent="success" />
        <StatCard label="Need co-sign" value={coSignCount} sub="above binding authority" accent="mortgage" />
        <StatCard label="Decided" value={totals.done || 0} sub="bound · no quote · declined" accent="insurance" />
      </div>

      <div className="flex flex-wrap gap-2">
        {[
          { key: 'inbox', label: 'Inbox', icon: Inbox, count: pendingCount },
          { key: 'bind', label: 'Ready to bind', icon: FileCheck, count: bindCount },
          { key: 'done', label: 'History', icon: History, count: totals.done || 0 },
        ].map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium ring-1 transition ${
              tab === t.key
                ? 'bg-brand/15 text-brand ring-brand/30'
                : 'bg-surface-overlay text-slate-400 ring-white/[0.06] hover:text-slate-200'
            }`}
          >
            <t.icon className="h-4 w-4" /> {t.label}
            <span className="rounded-full bg-black/30 px-1.5 py-0.5 text-xs tabular-nums">{t.count}</span>
          </button>
        ))}
      </div>

      {error && <div className="rounded-xl bg-red-500/10 p-4 text-sm text-red-400 ring-1 ring-red-500/20">{error}</div>}

      <div className="glass-card p-6">
        {!cards.length ? (
          <EmptyState
            icon={tab === 'inbox' ? Inbox : tab === 'bind' ? FileCheck : History}
            title={tab === 'inbox' ? 'Inbox clear' : tab === 'bind' ? 'Nothing to bind' : 'No history yet'}
            description={
              tab === 'inbox'
                ? 'All submissions are being handled. New pipeline runs land here for UW sign-off.'
                : tab === 'bind'
                  ? 'No approved submissions waiting to bind.'
                  : 'Decided cases will appear here.'
            }
          />
        ) : (
          <div className="space-y-4">
            {cards.map((c) => {
              const sb = STATE_BADGE[c.state] || { status: c.state, label: c.state };
              const authLabel = getAuthorityLabel(c.premium);
              const open = c.human_review_required || (c.checkpoints || []).some((cp) => cp.status === 'pending');
              const openChecks = (c.checkpoints || []).filter((cp) => cp.status === 'pending').length;
              const line = insuranceLineLabel(c.insurance_line);
              const coSign = c.state === 'pending_co_sign';
              const isOpen = signingId === c.bundle_id;
              return (
                <div key={c.bundle_id} className="rounded-xl border border-white/[0.06] bg-surface-overlay p-5">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-sm font-semibold">{c.bundle_id}</span>
                        <Badge status={sb.status} label={sb.label} />
                        {coSign && <span className="inline-flex items-center gap-1 text-xs text-violet-400"><GitCompare className="h-3 w-3" /> Co-sign required</span>}
                      </div>
                      <p className="mt-1 text-sm font-medium text-white">{c.insured_name || 'Submission'}</p>
                      <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-400">
                        {line && <span>{line}</span>}
                        {c.broker_name && <span>Broker: {c.broker_name}</span>}
                        {c.assigned_to && <span className="inline-flex items-center gap-1"><UserCheck className="h-3 w-3" /> {c.assigned_to}</span>}
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-1.5">
                      {c.premium != null && (
                        <span className="font-mono text-lg font-bold text-white">{fmtCurrency(c.premium)}</span>
                      )}
                      {authLabel && <span className="text-xs text-slate-500">{authLabel}</span>}
                      {c.updated_at && (
                        <span className="text-xs text-slate-500">{new Date(c.updated_at).toLocaleString()}</span>
                      )}
                    </div>
                  </div>

                  <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                    <div className="rounded-lg bg-black/20 p-2.5">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">AI decision</p>
                      <p className="mt-0.5 text-sm font-medium text-slate-200 capitalize">{c.ai_decision || '—'}</p>
                    </div>
                    <div className="rounded-lg bg-black/20 p-2.5">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Risk</p>
                      <p className="mt-0.5 text-sm font-medium text-slate-200">
                        {c.severity ? <span className="capitalize">{c.severity}</span> : '—'}
                        {c.risk_score != null && <span className="ml-1 text-slate-400 tabular-nums">({c.risk_score}%)</span>}
                      </p>
                    </div>
                    <div className="rounded-lg bg-black/20 p-2.5">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Open conditions</p>
                      <p className="mt-0.5 text-sm font-medium text-slate-200 tabular-nums">{(c.conditions || []).length}</p>
                    </div>
                    <div className="rounded-lg bg-black/20 p-2.5">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Checkpoints</p>
                      <p className="mt-0.5 text-sm font-medium text-slate-200 tabular-nums">
                        {openChecks > 0 ? `${openChecks} open` : 'cleared'}
                      </p>
                    </div>
                  </div>

                  {(c.checkpoints || []).length > 0 && (
                    <div className="mt-3 flex flex-wrap items-center gap-1.5">
                      <Layers className="h-3 w-3 text-slate-500" />
                      {(c.checkpoints || []).map((cp) => (
                        <span
                          key={`${cp.id || cp.name}-${cp.status}`}
                          className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] ring-1 ring-inset ${
                            cp.status === 'pending'
                              ? 'bg-amber-500/10 text-amber-400 ring-amber-500/20'
                              : cp.status === 'approved' || cp.status === 'cleared'
                                ? 'bg-emerald-500/10 text-emerald-400 ring-emerald-500/20'
                                : cp.status === 'waived'
                                  ? 'bg-slate-500/10 text-slate-400 ring-slate-500/20'
                                  : 'bg-sky-500/10 text-sky-400 ring-sky-500/20'
                          }`}
                        >
                          {cp.status === 'pending'
                            ? <AlertTriangle className="h-2.5 w-2.5" />
                            : (cp.status === 'approved' || cp.status === 'cleared')
                              ? <CircleCheck className="h-2.5 w-2.5" />
                              : null}
                          {checkpointLabel(cp.id || cp.name)} · {cp.status}
                          {cp.status === 'pending' && (
                            <button
                              type="button"
                              disabled={busy === `cp:${c.bundle_id}:${cp.id}`}
                              onClick={() => handleResolveCheckpoint(c.bundle_id, cp.id)}
                              className="ml-1 rounded-full bg-brand/20 px-1.5 py-px text-[10px] font-semibold text-brand hover:bg-brand/30"
                            >
                              {busy === `cp:${c.bundle_id}:${cp.id}` ? '…' : 'Approve'}
                            </button>
                          )}
                        </span>
                      ))}
                    </div>
                  )}

                  {(c.human_review_reasons || []).length > 0 && (
                    <ul className="mt-3 space-y-1">
                      {uwReasons((c.human_review_reasons || []).map((r) => (typeof r === 'string' ? r : r.reason || JSON.stringify(r)))).map((r, i) => (
                        <li key={i} className="text-xs text-amber-400/90">· {r}</li>
                      ))}
                    </ul>
                  )}

                  {(c.sign_offs || []).length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {(c.sign_offs || []).map((so, i) => (
                        <span key={i} className="inline-flex items-center gap-1 rounded-full bg-black/20 px-2 py-0.5 text-[10px] text-slate-400 ring-1 ring-white/[0.06]">
                          <ShieldCheck className="h-2.5 w-2.5" /> {so.action} by {so.username || so.license_number || 'UW'}
                        </span>
                      ))}
                    </div>
                  )}

                      {c.archived && (
                        <p className="mt-2 text-[11px] text-slate-500">
                          Archived memo · {c.source_docs_retained === false ? 'source file is in the PAS, not here' : 'open to view decision'}
                        </p>
                      )}

                  <div className="mt-4 flex flex-wrap gap-2">
                    <button type="button" onClick={() => onOpenJob?.('insurance', c.bundle_id, c.bundle_id)} className="btn-secondary text-xs"><Search className="h-3 w-3 inline" /> View</button>

                    {(c.state === 'approved' || c.state === 'quoted') && (
                      <button
                        type="button"
                        disabled={busy === c.bundle_id}
                        onClick={() => handleBind(c.bundle_id)}
                        className="rounded-xl px-3 py-1.5 text-xs text-emerald-400 ring-1 ring-emerald-500/30 hover:bg-emerald-500/10"
                      >
                        <HandCoins className="h-3 w-3 inline" /> {busy === c.bundle_id ? 'Binding…' : 'Bind policy'}
                      </button>
                    )}

                    {c.state === 'pending_review' && !open && (
                      <button
                        type="button"
                        onClick={() => {
                          setSigningId(c.bundle_id);
                          setForm((f) => ({
                            ...f,
                            action: 'quote',
                            uw_indicated_premium: c.premium != null ? String(c.premium) : '',
                          }));
                        }}
                        className="btn-primary btn-sm text-xs"
                      >
                        Quote
                      </button>
                    )}
                    {c.state === 'pending_review' && (
                      <>
                        <button type="button" onClick={() => { setSigningId(c.bundle_id); setForm((f) => ({ ...f, action: 'no_quote' })); }} className="rounded-xl px-3 py-1.5 text-xs text-red-400 ring-1 ring-red-500/30 hover:bg-red-500/10">No quote</button>
                        <button type="button" onClick={() => { setSigningId(c.bundle_id); setForm((f) => ({ ...f, action: 'refer' })); }} className="btn-secondary text-xs">Refer</button>
                        <button type="button" onClick={() => { setSigningId(c.bundle_id); setForm((f) => ({ ...f, action: 'request_info' })); }} className="btn-secondary text-xs">Request info</button>
                      </>
                    )}
                    {c.state === 'pending_co_sign' && (
                      <button
                        type="button"
                        onClick={() => { setSigningId(c.bundle_id); setForm((f) => ({ ...f, action: 'approve' })); }}
                        className="btn-primary btn-sm text-xs"
                      >
                        Co-sign
                      </button>
                    )}
                  </div>

                  {isOpen && (
                    <div className="mt-4 space-y-3 rounded-lg bg-black/20 p-4 ring-1 ring-white/[0.06]">
                      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                        {form.action === 'quote' ? 'Quote' : form.action === 'no_quote' ? 'No quote' : form.action === 'approve' ? 'Approve / sign' : form.action} — {c.bundle_id}
                      </p>
                      <div className="grid gap-3 sm:grid-cols-2">
                        <input
                          type="text" placeholder="License number" className="input-field w-full text-sm"
                          value={form.license_number} onChange={(e) => setForm((f) => ({ ...f, license_number: e.target.value }))}
                        />
                        <select
                          className="input-field w-full text-sm"
                          value={form.override_reason_category}
                          onChange={(e) => setForm((f) => ({ ...f, override_reason_category: e.target.value }))}
                        >
                          <option value="">Reason category…</option>
                          {REASON_CATEGORIES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                        </select>
                        <select
                          className="input-field w-full text-sm"
                          value={form.uw_confidence}
                          onChange={(e) => setForm((f) => ({ ...f, uw_confidence: e.target.value }))}
                        >
                          <option value="low">Low confidence</option>
                          <option value="medium">Medium confidence</option>
                          <option value="high">High confidence</option>
                        </select>
                        <input
                          type="text" placeholder="Override reason (required to override AI)" className="input-field w-full text-sm"
                          value={form.override_reason} onChange={(e) => setForm((f) => ({ ...f, override_reason: e.target.value }))}
                        />
                        <input
                          type="number" placeholder="UW indicated premium" className="input-field w-full text-sm"
                          value={form.uw_indicated_premium} onChange={(e) => setForm((f) => ({ ...f, uw_indicated_premium: e.target.value }))}
                        />
                        <input
                          type="number" placeholder="UW limit" className="input-field w-full text-sm"
                          value={form.uw_limit} onChange={(e) => setForm((f) => ({ ...f, uw_limit: e.target.value }))}
                        />
                        <input
                          type="number" placeholder="UW deductible" className="input-field w-full text-sm"
                          value={form.uw_deductible} onChange={(e) => setForm((f) => ({ ...f, uw_deductible: e.target.value }))}
                        />
                      </div>
                      <textarea
                        placeholder={form.action === 'request_info' ? 'What do you need from the broker? (e.g. loss runs, SOV)' : form.action === 'no_quote' ? 'Why no quote? (appetite, risk, incomplete package…)' : 'Notes…'}
                        className="input-field w-full text-sm" rows={2}
                        value={form.notes} onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                      />
                      <div className="flex gap-2">
                        <button type="button" disabled={busy === c.bundle_id} onClick={() => handleSignOff(c.bundle_id)} className="btn-primary btn-sm text-xs">
                          {busy === c.bundle_id ? 'Submitting…' : `Confirm ${form.action === 'no_quote' ? 'no quote' : form.action}`}
                        </button>
                        <button type="button" onClick={() => setSigningId(null)} className="btn-secondary text-xs">Cancel</button>
                      </div>
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
