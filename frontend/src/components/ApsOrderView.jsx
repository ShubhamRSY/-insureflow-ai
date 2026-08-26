import { useState } from 'react';

const STATUS_COLORS = {
  not_requested: 'bg-slate-700 text-slate-300',
  pending: 'bg-yellow-900/40 text-yellow-300',
  submitted_to_vendor: 'bg-blue-900/40 text-blue-300',
  vendor_processing: 'bg-blue-900/40 text-blue-300',
  received: 'bg-green-900/40 text-green-300',
  reviewed: 'bg-green-900/40 text-green-300',
  failed: 'bg-red-900/40 text-red-300',
};

export default function ApsOrderView({ data }) {
  const orders = data?.aps_orders || [];
  const latest = orders[0];

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wide">APS (Attending Physician Statement)</h3>
      {!latest ? (
        <p className="text-sm text-slate-400">No APS orders placed for this case.</p>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Info label="Order ID" value={latest.order_id} />
            <Info label="Status" value={<StatusBadge status={latest.status} />} />
            <Info label="Priority" value={latest.priority} />
            <Info label="HIPAA On File" value={latest.hipaa_authorization_on_file ? 'Yes' : 'No'} />
          </div>
          {latest.physician?.name && (
            <div className="rounded border border-slate-800 bg-slate-900/50 p-3">
              <p className="text-xs text-slate-400 mb-1">Physician</p>
              <p className="text-sm text-white">{latest.physician.name}</p>
              {latest.physician.specialty && <p className="text-xs text-slate-400">{latest.physician.specialty}</p>}
              {latest.physician.practice_name && <p className="text-xs text-slate-400">{latest.physician.practice_name}</p>}
            </div>
          )}
          {latest.estimated_completion && (
            <p className="text-xs text-slate-400">Estimated completion: {latest.estimated_completion}</p>
          )}
        </>
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
