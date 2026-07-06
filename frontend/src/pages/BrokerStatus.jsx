import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Shield, Clock, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';
import { api } from '../lib/api';

const STATUS_META = {
  processing: { icon: Clock, color: 'text-amber-400', bg: 'bg-amber-500/10', label: 'Processing' },
  completed: { icon: CheckCircle, color: 'text-emerald-400', bg: 'bg-emerald-500/10', label: 'Completed' },
  declined: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-500/10', label: 'Declined' },
  failed: { icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-500/10', label: 'Failed' },
  unknown: { icon: Clock, color: 'text-slate-400', bg: 'bg-slate-500/10', label: 'Unknown' },
};

const DECISION_UI = {
  accept: { label: 'Accepted', class: 'text-emerald-400' },
  refer: { label: 'Referred to UW', class: 'text-amber-400' },
  decline: { label: 'Declined', class: 'text-red-400' },
};

export default function BrokerStatus() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [polling, setPolling] = useState(true);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await api(`/broker/status/${token}`);
      setData(res);
      if (res.status !== 'processing') setPolling(false);
    } catch (e) {
      setError(e.message || 'Failed to load submission status');
      setPolling(false);
    }
  }, [token]);

  useEffect(() => {
    fetchStatus();
    if (!polling) return;
    const iv = setInterval(fetchStatus, 5000);
    return () => clearInterval(iv);
  }, [fetchStatus, polling]);

  if (error) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="glass-card max-w-md p-8 text-center">
          <AlertTriangle className="mx-auto h-12 w-12 text-red-400" />
          <h2 className="mt-4 text-lg font-semibold text-slate-200">Status Unavailable</h2>
          <p className="mt-2 text-sm text-slate-400">{error}</p>
          <p className="mt-4 text-xs text-slate-500">This link may have expired or the submission was not found.</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <Clock className="mx-auto h-8 w-8 animate-spin text-brand-light" />
          <p className="mt-4 text-sm text-slate-400">Loading submission status...</p>
        </div>
      </div>
    );
  }

  const meta = STATUS_META[data.status] || STATUS_META.unknown;
  const StatusIcon = meta.icon;
  const decision = DECISION_UI[data.decision] || null;

  return (
    <div className="mx-auto max-w-2xl py-12 animate-fade-in">
      <div className="glass-card overflow-hidden">
        <div className="border-b border-white/[0.06] bg-surface-overlay/50 px-6 py-5">
          <div className="flex items-center gap-3">
            <Shield className="h-6 w-6 text-brand-light" />
            <div>
              <h1 className="text-lg font-semibold text-slate-100">Submission Status</h1>
              <p className="text-xs text-slate-500">Shared by your carrier via Rytera</p>
            </div>
          </div>
        </div>

        <div className="space-y-6 p-6">
          {/* Status banner */}
          <div className={`flex items-center gap-4 rounded-xl ${meta.bg} p-5 ring-1 ring-white/[0.04]`}>
            <StatusIcon className={`h-8 w-8 ${meta.color}`} />
            <div>
              <p className={`text-lg font-semibold ${meta.color}`}>{meta.label}</p>
              {data.broker_name && (
                <p className="text-sm text-slate-400">Submission for {data.broker_name}</p>
              )}
            </div>
          </div>

          {/* Details grid */}
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-xl bg-surface-overlay p-4 ring-1 ring-white/[0.04]">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Bundle ID</p>
              <p className="mt-1 font-mono text-xs text-slate-300">{data.bundle_id || '—'}</p>
            </div>
            <div className="rounded-xl bg-surface-overlay p-4 ring-1 ring-white/[0.04]">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Status</p>
              <p className="mt-1 text-sm font-medium text-slate-300 capitalize">{data.status}</p>
            </div>
            {decision && (
              <div className="rounded-xl bg-surface-overlay p-4 ring-1 ring-white/[0.04]">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Decision</p>
                <p className={`mt-1 text-sm font-semibold ${decision.class}`}>{decision.label}</p>
              </div>
            )}
            {data.workflow_state && (
              <div className="rounded-xl bg-surface-overlay p-4 ring-1 ring-white/[0.04]">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Workflow</p>
                <p className="mt-1 text-sm font-medium text-slate-300 capitalize">{data.workflow_state}</p>
              </div>
            )}
          </div>

          {/* Timeline */}
          <div>
            <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Progress</p>
            <div className="space-y-3">
              {[
                { label: 'Submission Received', done: true },
                { label: 'Appetite & Eligibility Check', done: data.status !== 'unknown' },
                { label: 'Document Processing & Analysis', done: data.status === 'completed' || data.status === 'declined' },
                { label: 'External Data Verification', done: data.status === 'completed' || data.status === 'declined' },
                { label: 'Underwriting Decision', done: data.status === 'completed' || data.status === 'declined' || data.status === 'failed' },
                { label: 'UW Review & Sign-Off', done: data.workflow_state === 'approved' || data.workflow_state === 'bound' || data.workflow_state === 'declined' },
              ].map((step, i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${
                    step.done ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-700/50 text-slate-500'
                  }`}>
                    {step.done ? (
                      <CheckCircle className="h-3.5 w-3.5" />
                    ) : (
                      <div className="h-2 w-2 rounded-full bg-slate-600" />
                    )}
                  </div>
                  <span className={`text-sm ${step.done ? 'text-slate-300' : 'text-slate-500'}`}>
                    {step.label}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Footer */}
          <p className="border-t border-white/[0.04] pt-4 text-center text-[10px] text-slate-600">
            Powered by Rytera — Real-time submission tracking
          </p>
        </div>
      </div>
    </div>
  );
}
