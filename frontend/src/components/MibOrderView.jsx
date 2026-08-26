import { useState } from 'react';
import { fmtCurrency } from '../lib/api';

const STATUS_COLORS = {
  pending: 'bg-yellow-900/40 text-yellow-300',
  submitted: 'bg-blue-900/40 text-blue-300',
  processing: 'bg-blue-900/40 text-blue-300',
  completed: 'bg-green-900/40 text-green-300',
  failed: 'bg-red-900/40 text-red-300',
};

export default function MibOrderView({ data }) {
  const orders = data?.mib_orders || [];
  const latestOrder = orders[0];

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wide">MIB Bureau Orders</h3>
      {!latestOrder ? (
        <p className="text-sm text-slate-400">No MIB orders placed for this case.</p>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Info label="Order ID" value={latestOrder.order_id} />
            <Info label="Status" value={<StatusBadge status={latestOrder.status} />} />
            <Info label="Priority" value={latestOrder.priority} />
            <Info label="Applicant" value={latestOrder.applicant_name} />
          </div>
          {latestOrder.report && (
            <div className="mt-3 rounded border border-slate-800 bg-slate-900/50 p-3">
              <p className="text-xs text-slate-400 mb-2">MIB Report</p>
              <div className="grid grid-cols-3 gap-2 text-sm">
                <span className="text-slate-400">Codes Found: <span className="text-white">{latestOrder.report.codes?.length || 0}</span></span>
                <span className="text-slate-400">Discrepancies: <span className="text-white">{latestOrder.report.discrepancies?.length || 0}</span></span>
                <span className="text-slate-400">No-Hit: <span className="text-white">{latestOrder.report.no_hit ? 'Yes' : 'No'}</span></span>
              </div>
              {latestOrder.report.discrepancies?.length > 0 && (
                <div className="mt-2 space-y-1">
                  {latestOrder.report.discrepancies.map((d, i) => (
                    <div key={i} className="text-xs rounded bg-red-900/20 border border-red-800/30 px-2 py-1 text-red-300">
                      {d.description} — {d.reason}
                    </div>
                  ))}
                </div>
              )}
            </div>
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
      {status}
    </span>
  );
}
