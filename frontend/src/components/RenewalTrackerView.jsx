import { fmtCurrency } from '../lib/api';
import { Hint, RatePanel, RateStat, Badge } from './ui';

const HINTS = {
  policy: 'In-force policy number this renewal record tracks.',
  status: 'Current lifecycle state of the policy relative to renewal or conversion.',
  renewalType: 'How this policy renews — e.g. level term rolling to annual renewable term, or a term nearing its convertibility deadline.',
  faceAmount: 'Death benefit currently in force on this policy.',
  effective: 'Date the current policy term took effect.',
  expiration: 'Date the current policy term ends.',
  renewalDate: 'Date the next renewal term begins.',
  premiumGuaranteeEnd: 'Last date the current premium is contractually guaranteed — expect a re-rate at renewal after this.',
  daysToRenewal: 'Countdown to the renewal date — flagged when overdue or inside 30 days so it doesn\'t get missed.',
  conversion: 'Term policies typically carry a window to convert to permanent coverage without new medical underwriting — track this so eligible clients don\'t lose the option.',
  conversionWindowEnd: 'Once this date passes, converting without new underwriting is no longer possible.',
  daysRemaining: 'Days left in the conversion window.',
  conversionFace: 'Face amount that would carry over if the client converts.',
  conversionOptions: 'Permanent products this term policy is eligible to convert into.',
  renewalPremium: "Comparison of what the client pays now against what's quoted for the upcoming renewal term.",
  current: 'Annual premium currently being paid.',
  renewalQuoted: 'Annual premium quoted for the next term.',
  change: 'Percentage change between current and renewal premium — a large increase is common at the end of a level term period as the policy re-rates to attained age.',
};

export default function RenewalTrackerView({ data }) {
  const renewals = data?.renewals || [];
  const latest = renewals[0];

  if (!latest) {
    return <p className="text-sm text-slate-500">No renewal records for this case.</p>;
  }

  const daysRenewal = latest.renewal_date ? Math.ceil((new Date(latest.renewal_date) - new Date()) / 86400000) : null;
  const daysConversion = latest.conversion_window_end ? Math.ceil((new Date(latest.conversion_window_end) - new Date()) / 86400000) : null;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <RateStat label="Policy" value={latest.policy_number} hint={HINTS.policy} />
        <RateStat label="Status" value={<Badge status={latest.status} label={latest.status?.replace(/_/g, ' ')} />} hint={HINTS.status} />
        <RateStat label="Renewal Type" value={latest.renewal_type?.replace(/_/g, ' ')} hint={HINTS.renewalType} />
        <RateStat label="Face Amount" value={fmtCurrency(latest.face_amount)} hint={HINTS.faceAmount} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <RateStat label="Effective Date" value={latest.effective_date} hint={HINTS.effective} />
        <RateStat label="Expiration Date" value={latest.expiration_date} hint={HINTS.expiration} />
        <RateStat label="Renewal Date" value={latest.renewal_date} hint={HINTS.renewalDate} />
        <RateStat label="Premium Guarantee End" value={latest.premium_guarantee_end} hint={HINTS.premiumGuaranteeEnd} />
      </div>

      {daysRenewal !== null && (
        <Hint text={HINTS.daysToRenewal}>
          <div className={`cursor-help rounded-lg border px-3 py-2 ${daysRenewal <= 0 ? 'border-red-500/30 bg-red-500/10' : daysRenewal <= 30 ? 'border-amber-500/30 bg-amber-500/10' : 'border-white/10 bg-surface-overlay/50'}`}>
            <p className={`text-xs ${daysRenewal <= 0 ? 'text-red-400' : daysRenewal <= 30 ? 'text-amber-400' : 'text-slate-500'}`}>
              {daysRenewal <= 0 ? `Renewal overdue by ${Math.abs(daysRenewal)} days` : `${daysRenewal} days until renewal`}
            </p>
          </div>
        </Hint>
      )}

      {latest.conversion_eligible && (
        <div className="rounded-lg border border-sky-500/20 bg-sky-500/10 p-3">
          <Hint text={HINTS.conversion}>
            <p className="hint-label mb-1 inline-block cursor-help text-xs font-medium text-sky-400">Conversion Options</p>
          </Hint>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <RateStat label="Conversion Window Closes" value={latest.conversion_window_end} hint={HINTS.conversionWindowEnd} />
            <RateStat label="Days Remaining" value={daysConversion} hint={HINTS.daysRemaining} />
            <RateStat label="Conversion Face" value={fmtCurrency(latest.conversion_face_amount)} hint={HINTS.conversionFace} />
            <RateStat label="Options" value={latest.conversion_product_options?.join(', ')} hint={HINTS.conversionOptions} />
          </div>
        </div>
      )}

      {latest.renewal_premium_quoted && (
        <RatePanel>
          <Hint text={HINTS.renewalPremium}>
            <p className="hint-label mb-1 inline-block cursor-help text-xs text-slate-500">Renewal Premium</p>
          </Hint>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <RateStat label="Current" value={fmtCurrency(latest.current_annual_premium)} hint={HINTS.current} />
            <RateStat label="Renewal Quoted" value={fmtCurrency(latest.renewal_premium_quoted)} hint={HINTS.renewalQuoted} />
            <RateStat
              label="Change"
              value={latest.renewal_premium_change_pct != null ? `${latest.renewal_premium_change_pct > 0 ? '+' : ''}${latest.renewal_premium_change_pct.toFixed(1)}%` : null}
              hint={HINTS.change}
            />
          </div>
        </RatePanel>
      )}
    </div>
  );
}
