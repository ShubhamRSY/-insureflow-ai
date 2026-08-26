import { fmtCurrency } from '../lib/api';
import { Hint, RatePanel, RateStat, Badge } from './ui';

const HINTS = {
  status: 'Where this case stands in the handoff from underwriting decision to an in-force policy.',
  binderId: 'Temporary coverage reference issued while the formal policy is being prepared.',
  issued: 'Date the binder was issued.',
  issuedBy: 'Underwriter or system that issued the binder.',
  checklist: 'Everything that must be true before the policy can actually be issued — unchecked items will block issuance.',
  blocking: 'Specific open items currently preventing issuance. Resolve these before the policy can move forward.',
  binderDetails: 'Terms locked in on the binder — should match the underwriting decision exactly.',
};

export default function PolicyIssuanceView({ data }) {
  const result = data?.issuance;
  const binder = result?.binder;
  const checklist = result?.ready_checklist || {};
  const blocking = result?.blocking_items || [];

  if (!result) {
    return <p className="text-sm text-slate-500">Issuance data not yet available for this case.</p>;
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <RateStat label="Status" value={<Badge status={result.status} label={result.status?.replace(/_/g, ' ')} />} hint={HINTS.status} />
        {binder && <RateStat label="Binder ID" value={binder.binder_id} hint={HINTS.binderId} />}
        {binder && <RateStat label="Issued" value={binder.issued_at ? new Date(binder.issued_at).toLocaleDateString() : null} hint={HINTS.issued} />}
        {binder && <RateStat label="Issued By" value={binder.issued_by} hint={HINTS.issuedBy} />}
      </div>

      <div>
        <Hint text={HINTS.checklist}>
          <p className="hint-label mb-2 inline-block cursor-help text-xs text-slate-500">Issuance Readiness Checklist</p>
        </Hint>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5">
          {Object.entries(checklist).map(([key, met]) => (
            <div key={key} className={`flex items-center gap-2 rounded px-2 py-1 text-xs ${met ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>
              <span>{met ? '✓' : '✗'}</span>
              <span>{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
            </div>
          ))}
        </div>
      </div>

      {blocking.length > 0 && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-3">
          <Hint text={HINTS.blocking}>
            <p className="hint-label mb-1 inline-block cursor-help text-xs font-medium text-red-400">Blocking Items ({blocking.length})</p>
          </Hint>
          <ul className="space-y-0.5 text-xs text-red-400">
            {blocking.map((item, i) => <li key={i}>• {item}</li>)}
          </ul>
        </div>
      )}

      {binder?.policy_data && (
        <RatePanel>
          <Hint text={HINTS.binderDetails}>
            <p className="hint-label mb-2 inline-block cursor-help text-xs text-slate-500">Binder Details</p>
          </Hint>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
            <RateStat label="Face Amount" value={fmtCurrency(binder.policy_data.face_amount)} />
            <RateStat label="Annual Premium" value={fmtCurrency(binder.policy_data.annual_premium)} />
            <RateStat label="Monthly Premium" value={fmtCurrency(binder.policy_data.monthly_premium)} />
            <RateStat label="UW Class" value={binder.policy_data.underwriting_class} />
            <RateStat label="Policy Type" value={binder.policy_data.policy_type} />
            <RateStat label="State" value={binder.policy_data.state} />
          </div>
          {binder.policy_data.riders?.length > 0 && (
            <p className="mt-2 text-xs text-slate-500">Riders: {binder.policy_data.riders.join(', ')}</p>
          )}
        </RatePanel>
      )}
    </div>
  );
}
