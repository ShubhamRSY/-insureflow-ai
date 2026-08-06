import { useState, useEffect, useCallback } from 'react';
import { useOutletContext } from 'react-router-dom';
import { MessagesSquare, RefreshCw, CheckCircle2, Clock, Send, Shield, User } from 'lucide-react';
import { Badge, EmptyState } from '../components/ui';
import { endpoints } from '../lib/api';

function fmtDateTime(value) {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' });
}

const KIND_META = {
  uw_decision: { label: 'UW decision', icon: Shield, cls: 'text-sky-400 bg-sky-500/15' },
  bind: { label: 'Coverage in force', icon: CheckCircle2, cls: 'text-emerald-400 bg-emerald-500/15' },
};

function NotificationCard({ n, onAcknowledge, busy }) {
  const meta = KIND_META[n.kind] || { label: n.kind || 'communication', icon: Send, cls: 'text-slate-400 bg-white/5' };
  const Icon = meta.icon;
  return (
    <div className="glass-card p-5 animate-slide-up">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${meta.cls}`}>
            <Icon className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-semibold text-white">{meta.label}</p>
              <Badge status={n.status} />
            </div>
            <p className="text-xs text-slate-500">
              <span className="font-mono text-slate-400">{n.bundle_id}</span>
              {' · '}{n.producer_name ? `to ${n.producer_name}` : 'to producer'}{' · '}{fmtDateTime(n.created_at)}
            </p>
          </div>
        </div>
        {n.status === 'sent' && (
          <button
            type="button"
            disabled={busy === n.notification_id}
            onClick={() => onAcknowledge(n)}
            className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-400 ring-1 ring-inset ring-emerald-500/25 transition hover:bg-emerald-500/20 disabled:opacity-60"
          >
            <CheckCircle2 className={`h-3.5 w-3.5 ${busy === n.notification_id ? 'animate-pulse' : ''}`} />
            Acknowledge
          </button>
        )}
      </div>

      <p className="mt-3 rounded-xl bg-black/20 px-4 py-3 text-sm leading-relaxed text-slate-300">{n.message}</p>

      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-slate-500">
        <span className="inline-flex items-center gap-1"><Send className="h-3 w-3" /> decision: <span className="capitalize text-slate-300">{n.decision}</span></span>
        <span className="inline-flex items-center gap-1"><User className="h-3 w-3" /> producer: <span className="text-slate-300">{n.producer_name || '—'}</span></span>
        {n.status === 'acknowledged' ? (
          <span className="inline-flex items-center gap-1"><CheckCircle2 className="h-3 w-3 text-emerald-400" /> acknowledged by <span className="text-slate-300">{n.acknowledged_by}</span> at {fmtDateTime(n.acknowledged_at)}</span>
        ) : (
          <span className="inline-flex items-center gap-1"><Clock className="h-3 w-3" /> awaiting broker acknowledgement</span>
        )}
        <span className="ml-auto font-mono text-slate-600">{n.notification_id}</span>
      </div>
    </div>
  );
}

export default function ProducerCommsPage() {
  const { user } = useOutletContext() || {};
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  const [filter, setFilter] = useState('all');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await endpoints.producerNotifications();
      setNotifications(data.notifications || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const acknowledge = async (n) => {
    setBusy(n.notification_id);
    try {
      await endpoints.acknowledgeNotification(n.bundle_id, n.notification_id, user?.username || 'broker');
      await load();
    } catch (e) {
      alert(e.message);
    } finally {
      setBusy('');
    }
  };

  const counts = {
    all: notifications.length,
    sent: notifications.filter((n) => n.status === 'sent').length,
    acknowledged: notifications.filter((n) => n.status === 'acknowledged').length,
  };
  const visible = filter === 'all' ? notifications : notifications.filter((n) => n.status === filter);

  return (
    <div className="mx-auto max-w-5xl space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-sky-500/15">
            <MessagesSquare className="h-6 w-6 text-sky-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Producer Comms</h1>
            <p className="mt-1 text-sm text-slate-400">
              Every underwriting decision communicated to the producer — approvals, declinations, info requests, referrals, and binds.
            </p>
          </div>
        </div>
        <button type="button" onClick={load} className="btn-secondary btn-sm text-xs"><RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh</button>
      </div>

      {error && <div className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="glass-card group relative overflow-hidden p-5 animate-slide-up">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-sky-500 to-cyan-400 opacity-60" />
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Total communications</p>
            <Send className="h-4 w-4 text-sky-400" />
          </div>
          <p className="mt-2 text-3xl font-bold tracking-tight text-white">{counts.all}</p>
        </div>
        <div className="glass-card group relative overflow-hidden p-5 animate-slide-up">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-emerald-500 to-teal-400 opacity-60" />
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Acknowledged</p>
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          </div>
          <p className="mt-2 text-3xl font-bold tracking-tight text-white">{counts.acknowledged}</p>
        </div>
        <div className="glass-card group relative overflow-hidden p-5 animate-slide-up">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-amber-500 to-orange-400 opacity-60" />
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Awaiting ack</p>
            <Clock className="h-4 w-4 text-amber-400" />
          </div>
          <p className="mt-2 text-3xl font-bold tracking-tight text-white">{counts.sent}</p>
        </div>
      </div>

      <div className="glass-card p-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Communication log</h3>
            <p className="mt-1 text-xs text-slate-500">Durable audit of producer-facing decisions, including acknowledgement back from the broker</p>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {[['all', 'All', counts.all], ['sent', 'Awaiting ack', counts.sent], ['acknowledged', 'Acknowledged', counts.acknowledged]].map(([k, label, count]) => (
              <button
                key={k}
                type="button"
                onClick={() => setFilter(k)}
                className={`rounded-full px-3 py-1 text-xs font-medium ring-1 transition ${filter === k ? 'bg-sky-500/15 text-sky-300 ring-sky-500/30' : 'bg-surface-overlay text-slate-400 ring-white/[0.06] hover:text-slate-200'}`}
              >
                {label} <span className="ml-0.5 opacity-60">{count}</span>
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="flex justify-center py-12">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
          </div>
        ) : visible.length === 0 ? (
          <EmptyState
            icon={MessagesSquare}
            title="No producer communications yet"
            description="Sign off a submission or bind coverage and the decision message to the producer will appear here."
          />
        ) : (
          <div className="space-y-4">
            {visible.map((n) => <NotificationCard key={n.notification_id} n={n} onAcknowledge={acknowledge} busy={busy} />)}
          </div>
        )}
      </div>
    </div>
  );
}
