import { fmtCurrency } from '../lib/api';

const STATUS_COLORS = {
  not_ready: 'bg-slate-700 text-slate-300',
  pending_uw_approval: 'bg-yellow-900/40 text-yellow-300',
  binder_issued: 'bg-blue-900/40 text-blue-300',
  policy_requested: 'bg-blue-900/40 text-blue-300',
  policy_issued: 'bg-green-900/40 text-green-300',
  policy_delivered: 'bg-green-900/40 text-green-300',
  failed: 'bg-red-900/40 text-red-300',
};

export default function PolicyIssuanceView({ data }) {
  const result = data?.issuance;
  const binder = result?.binder;
  const checklist = result?.ready_checklist || {};
  const blocking = result?.blocking_items || [];

  if (!result) {
    return (
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wide">Policy Issuance</h3>
        <p className="text-sm text-slate-400">Issuance data not yet available for this case.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wide">Policy Issuance Handoff</h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Info label="Status" value={<StatusBadge status={result.status} />} />
        {binder && <Info label="Binder ID" value={binder.binder_id} />}
        {binder && <Info label="Issued" value={new Date(binder.issued_at).toLocaleDateString()} />}
        {binder && <Info label="Issued By" value={binder.issued_by} />}
      </div>

      <div>
        <p className="text-xs text-slate-400 mb-2">Issuance Readiness Checklist</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5">
          {Object.entries(checklist).map(([key, met]) => (
            <div key={key} className={`flex items-center gap-2 text-xs px-2 py-1 rounded ${met ? 'bg-green-900/20 text-green-300' : 'bg-red-900/20 text-red-300'}`}>
              <span>{met ? '✓' : '✗'}</span>
              <span>{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
            </div>
          ))}
        </div>
      </div>

      {blocking.length > 0 && (
        <div className="rounded border border-red-800/30 bg-red-900/10 p-3">
          <p className="text-xs text-red-400 font-medium mb-1">Blocking Items ({blocking.length})</p>
          <ul className="text-xs text-red-300 space-y-0.5">
            {blocking.map((item, i) => <li key={i}>• {item}</li>)}
          </ul>
        </div>
      )}

      {binder?.policy_data && (
        <div className="rounded border border-slate-800 bg-slate-900/50 p-3">
          <p className="text-xs text-slate-400 mb-2">Binder Details</p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
            <Info label="Face Amount" value={fmtCurrency(binder.policy_data.face_amount)} />
            <Info label="Annual Premium" value={fmtCurrency(binder.policy_data.annual_premium)} />
            <Info label="Monthly Premium" value={fmtCurrency(binder.policy_data.monthly_premium)} />
            <Info label="UW Class" value={binder.policy_data.underwriting_class} />
            <Info label="Policy Type" value={binder.policy_data.policy_type} />
            <Info label="State" value={binder.policy_data.state} />
          </div>
          {binder.policy_data.riders?.length > 0 && (
            <p className="text-xs text-slate-400 mt-2">Riders: {binder.policy_data.riders.join(', ')}</p>
          )}
        </div>
      )}
    </div>
  );
}

function Info({ label, value }) {
  return (
    <div className="text-xs">
      <span className="text-slate-400">{label}: </span>
      <span className="text-white">{value}</span>
    </div>
  );
}

function StatusBadge({ status }) {
  return (
    <span className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${STATUS_COLORS[status] || 'bg-slate-700 text-slate-300'}`}>
      {status?.replace(/_/g, ' ')}
    </span>
  );
}
