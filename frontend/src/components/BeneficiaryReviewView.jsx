import { Hint, RatePanel, RateStat, Badge } from './ui';

const HINTS = {
  status: 'Where this beneficiary designation stands in underwriting review.',
  insured: 'The life the beneficiary designation applies to.',
  primaryTotal: "Primary beneficiaries' share percentages should sum to 100% — anything else needs correction before issue.",
  contingentTotal: 'Contingent (backup) beneficiaries\' share percentages, paid only if no primary beneficiary survives the insured.',
  ownership: "Ownership type differs from the insured — relevant for insurable interest and estate/tax review.",
  flags: "Situations where the named beneficiary's relationship to the insured needs to be verified to confirm a valid insurable interest exists.",
  actions: 'Outstanding follow-ups before this beneficiary designation can be considered clean.',
};

export default function BeneficiaryReviewView({ data }) {
  const review = data?.beneficiary_review;
  if (!review) {
    return <p className="text-sm text-slate-500">No beneficiary review data for this case.</p>;
  }

  const beneficiaries = review.beneficiaries || [];
  const primary = beneficiaries.filter(b => b.beneficiary_type === 'primary');
  const contingent = beneficiaries.filter(b => b.beneficiary_type === 'contingent');

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <RateStat label="Status" value={<Badge status={review.status} label={review.status?.replace(/_/g, ' ')} />} hint={HINTS.status} />
        <RateStat label="Insured" value={review.insured_name} hint={HINTS.insured} />
        <RateStat label="Primary Total" value={`${review.primary_total_pct}%`} hint={HINTS.primaryTotal} />
        <RateStat label="Contingent Total" value={`${review.contingent_total_pct}%`} hint={HINTS.contingentTotal} />
      </div>

      {primary.length > 0 && (
        <div>
          <p className="mb-2 text-xs text-slate-500">Primary Beneficiaries</p>
          <div className="space-y-1.5">
            {primary.map((b, i) => (
              <BeneficiaryRow key={b.entry_id || i} beneficiary={b} />
            ))}
          </div>
        </div>
      )}

      {contingent.length > 0 && (
        <div>
          <p className="mb-2 text-xs text-slate-500">Contingent Beneficiaries</p>
          <div className="space-y-1.5">
            {contingent.map((b, i) => (
              <BeneficiaryRow key={b.entry_id || i} beneficiary={b} />
            ))}
          </div>
        </div>
      )}

      {review.insurable_interest_flags?.length > 0 && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-3">
          <Hint text={HINTS.flags}>
            <p className="hint-label mb-1 inline-block cursor-help text-xs font-medium text-red-400">Insurable Interest Flags</p>
          </Hint>
          <ul className="space-y-0.5 text-xs text-red-400">
            {review.insurable_interest_flags.map((flag, i) => <li key={i}>• {flag}</li>)}
          </ul>
        </div>
      )}

      {review.action_items?.length > 0 && (
        <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 p-3">
          <Hint text={HINTS.actions}>
            <p className="hint-label mb-1 inline-block cursor-help text-xs font-medium text-amber-400">Action Items</p>
          </Hint>
          <ul className="space-y-0.5 text-xs text-amber-400">
            {review.action_items.map((item, i) => <li key={i}>• {item}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

function BeneficiaryRow({ beneficiary: b }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-white/10 bg-surface-overlay/50 px-3 py-2 text-xs">
      <div className="flex items-center gap-3">
        <span className="font-medium text-slate-100">{b.name || 'Unnamed'}</span>
        <span className="text-slate-500">{b.relationship}</span>
        {b.ownership_type !== 'insured' && (
          <Hint text={HINTS.ownership}>
            <span className="hint-label cursor-help rounded bg-sky-500/15 px-1.5 py-0.5 text-sky-400">{b.ownership_type}</span>
          </Hint>
        )}
      </div>
      <div className="flex items-center gap-3">
        <span className="text-slate-100">{b.percentage}%</span>
        {b.trust_name && <span className="text-slate-500">Trust: {b.trust_name}</span>}
      </div>
    </div>
  );
}
