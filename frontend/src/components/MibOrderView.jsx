import { Hint, RatePanel, RateStat, Badge } from './ui';

const HINTS = {
  orderId: 'Bureau order tracking ID — reference this when following up with MIB or the vendor.',
  status: 'Where the MIB (Medical Information Bureau) bureau check stands in its lifecycle.',
  priority: 'Processing priority requested from the bureau — higher priority typically shortens turnaround.',
  applicant: 'Name searched against the MIB database.',
  report: "Results returned once the bureau completes its search. Codes are non-diagnostic alerts, not a diagnosis — they only signal that another carrier reported something material.",
  codes: 'Number of MIB alert codes returned. A code flags that a prior carrier reported something material — follow-up (e.g. an APS) may be warranted.',
  discrepancies: "Places where this application's disclosures don't match what MIB has on file — resolve before binding.",
  noHit: 'Whether MIB has no record at all for this applicant. A no-hit is common and not itself a red flag.',
};

export default function MibOrderView({ data }) {
  const orders = data?.mib_orders || [];
  const latestOrder = orders[0];

  if (!latestOrder) {
    return <p className="text-sm text-slate-500">No MIB orders placed for this case.</p>;
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <RateStat label="Order ID" value={latestOrder.order_id} hint={HINTS.orderId} />
        <RateStat label="Status" value={<Badge status={latestOrder.status} label={latestOrder.status?.replace(/_/g, ' ')} />} hint={HINTS.status} />
        <RateStat label="Priority" value={latestOrder.priority} hint={HINTS.priority} />
        <RateStat label="Applicant" value={latestOrder.applicant_name} hint={HINTS.applicant} />
      </div>
      {latestOrder.report && (
        <RatePanel>
          <Hint text={HINTS.report}>
            <p className="hint-label mb-2 inline-block cursor-help text-xs text-slate-500">MIB Report</p>
          </Hint>
          <div className="grid grid-cols-3 gap-2 text-sm">
            <RateStat label="Codes Found" value={latestOrder.report.codes?.length || 0} hint={HINTS.codes} />
            <RateStat label="Discrepancies" value={latestOrder.report.discrepancies?.length || 0} hint={HINTS.discrepancies} />
            <RateStat label="No-Hit" value={latestOrder.report.no_hit ? 'Yes' : 'No'} hint={HINTS.noHit} />
          </div>
          {latestOrder.report.discrepancies?.length > 0 && (
            <div className="mt-2 space-y-1">
              {latestOrder.report.discrepancies.map((d, i) => (
                <div key={i} className="rounded border border-red-500/20 bg-red-500/10 px-2 py-1 text-xs text-red-400">
                  {d.description} — {d.reason}
                </div>
              ))}
            </div>
          )}
        </RatePanel>
      )}
    </div>
  );
}
