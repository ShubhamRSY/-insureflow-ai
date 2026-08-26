import { fmtCurrency } from '../lib/api';

const STATUS_COLORS = {
  pending: 'bg-yellow-900/40 text-yellow-300',
  in_review: 'bg-blue-900/40 text-blue-300',
  approved: 'bg-green-900/40 text-green-300',
  flagged: 'bg-red-900/40 text-red-300',
  rejected: 'bg-red-900/40 text-red-300',
  changes_requested: 'bg-yellow-900/40 text-yellow-300',
};

export default function BeneficiaryReviewView({ data }) {
  const review = data?.beneficiary_review;
  if (!review) {
    return (
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wide">Beneficiary Review</h3>
        <p className="text-sm text-slate-400">No beneficiary review data for this case.</p>
      </div>
    );
  }

  const beneficiaries = review.beneficiaries || [];
  const primary = beneficiaries.filter(b => b.beneficiary_type === 'primary');
  const contingent = beneficiaries.filter(b => b.beneficiary_type === 'contingent');

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wide">Beneficiary Review</h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Info label="Status" value={<StatusBadge status={review.status} />} />
        <Info label="Insured" value={review.insured_name} />
        <Info label="Primary Total" value={`${review.primary_total_pct}%`} />
        <Info label="Contingent Total" value={`${review.contingent_total_pct}%`} />
      </div>

      {primary.length > 0 && (
        <div>
          <p className="text-xs text-slate-400 mb-2">Primary Beneficiaries</p>
          <div className="space-y-1.5">
            {primary.map((b, i) => (
              <BeneficiaryRow key={b.entry_id || i} beneficiary={b} />
            ))}
          </div>
        </div>
      )}

      {contingent.length > 0 && (
        <div>
          <p className="text-xs text-slate-400 mb-2">Contingent Beneficiaries</p>
          <div className="space-y-1.5">
            {contingent.map((b, i) => (
              <BeneficiaryRow key={b.entry_id || i} beneficiary={b} />
            ))}
          </div>
        </div>
      )}

      {review.insurable_interest_flags?.length > 0 && (
        <div className="rounded border border-red-800/30 bg-red-900/10 p-3">
          <p className="text-xs text-red-400 font-medium mb-1">Insurable Interest Flags</p>
          <ul className="text-xs text-red-300 space-y-0.5">
            {review.insurable_interest_flags.map((flag, i) => <li key={i}>• {flag}</li>)}
          </ul>
        </div>
      )}

      {review.action_items?.length > 0 && (
        <div className="rounded border border-yellow-800/30 bg-yellow-900/10 p-3">
          <p className="text-xs text-yellow-400 font-medium mb-1">Action Items</p>
          <ul className="text-xs text-yellow-300 space-y-0.5">
            {review.action_items.map((item, i) => <li key={i}>• {item}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

function BeneficiaryRow({ beneficiary: b }) {
  return (
    <div className="flex items-center justify-between rounded border border-slate-800 bg-slate-900/50 px-3 py-2 text-xs">
      <div className="flex items-center gap-3">
        <span className="text-white font-medium">{b.name || 'Unnamed'}</span>
        <span className="text-slate-400">{b.relationship}</span>
        {b.ownership_type !== 'insured' && (
          <span className="rounded bg-blue-900/30 px-1.5 py-0.5 text-blue-300">{b.ownership_type}</span>
        )}
      </div>
      <div className="flex items-center gap-3">
        <span className="text-white">{b.percentage}%</span>
        {b.trust_name && <span className="text-slate-400">Trust: {b.trust_name}</span>}
      </div>
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
