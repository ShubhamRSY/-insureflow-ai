import { RatePanel, RateStat, Badge } from './ui';

const HINTS = {
  orderId: 'Attending Physician Statement order tracking ID.',
  status: 'Where the APS request stands — from not yet requested through received/reviewed by underwriting.',
  priority: 'Requested turnaround priority with the medical records vendor.',
  hipaa: "Whether a signed HIPAA authorization is on file to legally request these records. Required before the physician's office can release anything.",
  physician: 'Attending physician the records are being requested from.',
  eta: "Vendor's estimated delivery date for the completed statement.",
};

export default function ApsOrderView({ data }) {
  const orders = data?.aps_orders || [];
  const latest = orders[0];

  if (!latest) {
    return <p className="text-sm text-slate-500">No APS orders placed for this case.</p>;
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <RateStat label="Order ID" value={latest.order_id} hint={HINTS.orderId} />
        <RateStat label="Status" value={<Badge status={latest.status} label={latest.status?.replace(/_/g, ' ')} />} hint={HINTS.status} />
        <RateStat label="Priority" value={latest.priority} hint={HINTS.priority} />
        <RateStat label="HIPAA On File" value={latest.hipaa_authorization_on_file ? 'Yes' : 'No'} hint={HINTS.hipaa} />
      </div>
      {latest.physician?.name && (
        <RatePanel>
          <RateStat label="Physician" value={latest.physician.name} hint={HINTS.physician} />
          {latest.physician.specialty && <p className="mt-1 text-xs text-slate-500">{latest.physician.specialty}</p>}
          {latest.physician.practice_name && <p className="text-xs text-slate-500">{latest.physician.practice_name}</p>}
        </RatePanel>
      )}
      {latest.estimated_completion && (
        <RateStat label="Estimated completion" value={latest.estimated_completion} hint={HINTS.eta} />
      )}
    </div>
  );
}
