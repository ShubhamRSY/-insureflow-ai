import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Briefcase, FilePlus2, LifeBuoy, RefreshCw, Shield, Sparkles, ArrowRight,
} from 'lucide-react';
import { Badge, EmptyState, HintCheckbox } from '../components/ui';
import { endpoints } from '../lib/api';
import { UI_HINTS } from '../lib/uiHints';

const REQUEST_TYPES = [
  'quote', 'endorsement', 'certificate', 'cancellation', 'renewal', 'correspondence', 'policyholder_inquiry',
];

const ACTION_COLOR = {
  broaden: 'text-emerald-400 bg-emerald-500/10',
  narrow: 'text-amber-400 bg-amber-500/10',
  verify: 'text-sky-400 bg-sky-500/10',
  manuscript: 'text-violet-400 bg-violet-500/10',
};

export default function LineUnderwriting() {
  const [desks, setDesks] = useState(null);
  const [tickets, setTickets] = useState([]);
  const [assist, setAssist] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    applicant: '',
    occupancy: 'manufacturing warehouse',
    operations_description: 'Ships finished goods to regional distributors; property in transit weekly.',
    complex_submission: false,
  });
  const [ticketForm, setTicketForm] = useState({
    request_type: 'quote',
    subject: '',
    detail: '',
    requester: 'producer',
    requester_name: '',
    policy_number: '',
  });

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [d, s] = await Promise.all([
        endpoints.underwritingDesks(),
        endpoints.lineServiceTickets(),
      ]);
      setDesks(d);
      setTickets(s.tickets || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const runAssist = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      const res = await endpoints.lineCoverageAssist(form);
      setAssist(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const createTicket = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await endpoints.createLineServiceTicket(ticketForm);
      setTicketForm({ request_type: 'quote', subject: '', detail: '', requester: 'producer', requester_name: '', policy_number: '' });
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const completeTicket = async (id) => {
    try {
      await endpoints.updateLineServiceTicket(id, { status: 'completed', resolution_notes: 'Completed by line underwriter' });
      await load();
    } catch (err) {
      setError(err.message);
    }
  };

  const caps = desks?.desks?.line?.capabilities || [];

  return (
    <div className="mx-auto max-w-6xl space-y-8 animate-fade-in">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-widest text-sky-400">Line underwriter</p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight">Branch & regional desk</h1>
          <p className="mt-1 max-w-2xl text-slate-400">
            Implement the underwriting process, determine appropriate coverage, and service producers and policyholders.
          </p>
        </div>
        <div className="flex gap-2">
          <Link to="/insurance" className="btn-secondary btn-sm text-xs">
            Run submission <ArrowRight className="h-3.5 w-3.5" />
          </Link>
          <button type="button" onClick={load} className="btn-secondary btn-sm text-xs">
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>
      </div>

      {error && <div className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {caps.map((c) => (
          <div key={c.id} className="glass-card p-4">
            <Shield className="h-4 w-4 text-sky-400" />
            <h3 className="mt-2 text-sm font-semibold">{c.title}</h3>
            <p className="mt-1 text-xs text-slate-500">{c.description}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="glass-card p-6">
          <div className="mb-4 flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-brand-light" />
            <h2 className="font-semibold">Coverage assist</h2>
          </div>
          <p className="mb-4 text-xs text-slate-500">
            Broaden gaps (e.g. inland marine for transit) or narrow terms with higher deductibles instead of declining.
          </p>
          <form onSubmit={runAssist} className="space-y-3">
            <input className="input w-full" placeholder="Applicant" value={form.applicant} onChange={(e) => setForm({ ...form, applicant: e.target.value })} />
            <input className="input w-full" placeholder="Occupancy" value={form.occupancy} onChange={(e) => setForm({ ...form, occupancy: e.target.value })} />
            <textarea className="input min-h-[88px] w-full" placeholder="Operations / inspection narrative" value={form.operations_description} onChange={(e) => setForm({ ...form, operations_description: e.target.value })} />
            <HintCheckbox
              hint={UI_HINTS.complexSubmission}
              label="Complex / unique submission (manuscript)"
              labelClassName="flex items-center gap-2 text-xs text-slate-400"
              checked={form.complex_submission}
              onChange={(e) => setForm({ ...form, complex_submission: e.target.checked })}
            />
            <button type="submit" disabled={saving} className="btn-primary text-sm">{saving ? 'Working…' : 'Recommend coverage'}</button>
          </form>
          {assist && (
            <div className="mt-5 space-y-3 border-t border-white/[0.06] pt-4">
              <p className="text-sm text-slate-300">{assist.summary}</p>
              {(assist.recommendations || []).map((r) => (
                <div key={r.title} className="rounded-xl bg-surface-overlay px-3 py-3">
                  <div className="flex items-center gap-2">
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${ACTION_COLOR[r.action] || ''}`}>{r.action}</span>
                    <span className="text-sm font-medium">{r.title}</span>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">{r.rationale}</p>
                  {r.suggested_form && <p className="mt-1 text-[11px] text-slate-400">Form: {r.suggested_form}</p>}
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="glass-card p-6">
          <div className="mb-4 flex items-center gap-2">
            <LifeBuoy className="h-4 w-4 text-emerald-400" />
            <h2 className="font-semibold">Producer & policyholder service</h2>
          </div>
          <form onSubmit={createTicket} className="space-y-3">
            <div className="grid grid-cols-2 gap-2">
              <select className="input" value={ticketForm.request_type} onChange={(e) => setTicketForm({ ...ticketForm, request_type: e.target.value })}>
                {REQUEST_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
              <select className="input" value={ticketForm.requester} onChange={(e) => setTicketForm({ ...ticketForm, requester: e.target.value })}>
                <option value="producer">Producer</option>
                <option value="policyholder">Policyholder</option>
                <option value="internal">Internal</option>
              </select>
            </div>
            <input className="input w-full" placeholder="Subject" required value={ticketForm.subject} onChange={(e) => setTicketForm({ ...ticketForm, subject: e.target.value })} />
            <input className="input w-full" placeholder="Requester name" value={ticketForm.requester_name} onChange={(e) => setTicketForm({ ...ticketForm, requester_name: e.target.value })} />
            <input className="input w-full" placeholder="Policy number (optional)" value={ticketForm.policy_number} onChange={(e) => setTicketForm({ ...ticketForm, policy_number: e.target.value })} />
            <textarea className="input min-h-[64px] w-full" placeholder="Detail" value={ticketForm.detail} onChange={(e) => setTicketForm({ ...ticketForm, detail: e.target.value })} />
            <button type="submit" disabled={saving} className="btn-primary text-sm">
              <FilePlus2 className="h-3.5 w-3.5" /> Open ticket
            </button>
          </form>

          <div className="mt-5 space-y-2 border-t border-white/[0.06] pt-4">
            {tickets.length === 0 ? (
              <EmptyState icon={Briefcase} title="No open service work" description="Quotes, endorsements, certificates, and renewals appear here." />
            ) : tickets.map((t) => (
              <div key={t.ticket_id} className="flex items-start justify-between gap-3 rounded-xl bg-surface-overlay px-3 py-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge>{t.request_type}</Badge>
                    <Badge>{t.status}</Badge>
                    <span className="text-sm font-medium">{t.subject}</span>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">{t.requester}{t.requester_name ? ` · ${t.requester_name}` : ''}{t.policy_number ? ` · ${t.policy_number}` : ''}</p>
                </div>
                {t.status !== 'completed' && (
                  <button type="button" className="btn-secondary btn-sm text-[10px]" onClick={() => completeTicket(t.ticket_id)}>Complete</button>
                )}
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
