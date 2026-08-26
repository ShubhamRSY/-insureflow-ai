import { fmtCurrency } from '../lib/api';

const STATUS_COLORS = {
  active: 'bg-green-900/40 text-green-300',
  renewal_due: 'bg-yellow-900/40 text-yellow-300',
  renewal_overdue: 'bg-red-900/40 text-red-300',
  convertible: 'bg-blue-900/40 text-blue-300',
  conversion_window_open: 'bg-blue-900/40 text-blue-300',
  conversion_window_closed: 'bg-slate-700 text-slate-300',
  lapsed: 'bg-red-900/40 text-red-300',
};

export default function RenewalTrackerView({ data }) {
  const renewals = data?.renewals || [];
  const latest = renewals[0];

  if (!latest) {
    return (
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wide">Renewal & Convertibility Tracking</h3>
        <p className="text-sm text-slate-400">No renewal records for this case.</p>
      </div>
    );
  }

  const daysRenewal = latest.renewal_date ? Math.ceil((new Date(latest.renewal_date) - new Date()) / 86400000) : null;
  const daysConversion = latest.conversion_window_end ? Math.ceil((new Date(latest.conversion_window_end) - new Date()) / 86400000) : null;

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wide">Renewal & Convertibility Tracking</h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Info label="Policy" value={latest.policy_number || 'N/A'} />
        <Info label="Status" value={<StatusBadge status={latest.status} />} />
        <Info label="Renewal Type" value={latest.renewal_type?.replace(/_/g, ' ')} />
        <Info label="Face Amount" value={fmtCurrency(latest.face_amount)} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Info label="Effective Date" value={latest.effective_date} />
        <Info label="Expiration Date" value={latest.expiration_date} />
        <Info label="Renewal Date" value={latest.renewal_date} />
        <Info label="Premium Guarantee End" value={latest.premium_guarantee_end} />
      </div>

      {daysRenewal !== null && (
        <div className={`rounded border px-3 py-2 ${daysRenewal <= 0 ? 'border-red-800/50 bg-red-900/20' : daysRenewal <= 30 ? 'border-yellow-800/50 bg-yellow-900/20' : 'border-slate-800 bg-slate-900/50'}`}>
          <p className={`text-xs ${daysRenewal <= 0 ? 'text-red-400' : daysRenewal <= 30 ? 'text-yellow-400' : 'text-slate-400'}`}>
            {daysRenewal <= 0 ? `Renewal overdue by ${Math.abs(daysRenewal)} days` : `${daysRenewal} days until renewal`}
          </p>
        </div>
      )}

      {latest.conversion_eligible && (
        <div className="rounded border border-blue-800/50 bg-blue-900/20 p-3">
          <p className="text-xs text-blue-400 font-medium mb-1">Conversion Options</p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <Info label="Conversion Window Closes" value={latest.conversion_window_end} />
            <Info label="Days Remaining" value={daysConversion} />
            <Info label="Conversion Face" value={fmtCurrency(latest.conversion_face_amount)} />
            <Info label="Options" value={latest.conversion_product_options?.join(', ') || 'N/A'} />
          </div>
        </div>
      )}

      {latest.renewal_premium_quoted && (
        <div className="rounded border border-slate-800 bg-slate-900/50 p-3">
          <p className="text-xs text-slate-400 mb-1">Renewal Premium</p>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <Info label="Current" value={fmtCurrency(latest.current_annual_premium)} />
            <Info label="Renewal Quoted" value={fmtCurrency(latest.renewal_premium_quoted)} />
            <Info label="Change" value={latest.renewal_premium_change_pct != null ? `${latest.renewal_premium_change_pct > 0 ? '+' : ''}${latest.renewal_premium_change_pct.toFixed(1)}%` : 'N/A'} />
          </div>
        </div>
      )}
    </div>
  );
}

function Info({ label, value }) {
  return (
    <div className="text-xs">
      <span className="text-slate-400">{label}: </span>
      <span className="text-white">{value || 'N/A'}</span>
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
