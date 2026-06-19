import { X } from 'lucide-react';
import { Badge } from './ui';
import { extractMortgage } from '../lib/api';
import InsuranceMemoView from './InsuranceMemoView';
import { fmtCurrency } from '../lib/api';

export default function JobDrawer({ job, vertical, jobId, onClose }) {
  if (!jobId) return null;

  const processing = job?.status === 'processing';
  const failed = job?.status === 'failed';
  const isInsurance = vertical === 'insurance';
  const wide = isInsurance && !processing && !failed;

  let content;
  if (processing) {
    content = (
      <div className="flex flex-col items-center py-12 text-center">
        <div className="mb-4 h-10 w-10 animate-spin rounded-full border-2 border-brand border-t-transparent" />
        <p className="text-slate-300">Processing submission…</p>
        <p className="mt-1 text-sm text-slate-500">Auto-refreshing every 3 seconds</p>
      </div>
    );
  } else if (failed) {
    content = (
      <div className="rounded-xl bg-red-500/10 p-4 text-sm text-red-300">{job.error || 'Unknown error'}</div>
    );
  } else if (isInsurance) {
    content = <InsuranceMemoView job={job} />;
  } else {
    const s = extractMortgage(job);
    const denied = String(s.decision || '').toLowerCase() === 'deny';
    content = (
      <>
        <div className="grid grid-cols-2 gap-3">
          {[
            ['Decision', <Badge status={s.decision} />],
            ['Rate', s.rate != null ? `${s.rate}%` : denied ? 'N/A (denied)' : '—'],
            ['Monthly P&I', fmtCurrency(s.payment)],
            ['DTI', s.dti != null ? `${Number(s.dti).toFixed(1)}%` : '—'],
            ['LTV', s.ltv != null ? `${Number(s.ltv).toFixed(1)}%` : '—'],
            ['Borrower', s.borrower || '—'],
          ].map(([label, val]) => (
            <div key={label} className="rounded-xl bg-surface-overlay p-3 ring-1 ring-white/[0.04]">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{label}</p>
              <div className="mt-1 text-sm font-semibold">{val}</div>
            </div>
          ))}
        </div>
        {s.ineligibilityReasons?.length > 0 && (
          <div className="mt-4 rounded-xl bg-amber-500/10 p-3 ring-1 ring-amber-500/20">
            <p className="text-[10px] font-bold uppercase tracking-wider text-amber-400">Ineligibility</p>
            <ul className="mt-2 space-y-1 text-xs text-amber-200/90">
              {s.ineligibilityReasons.map((r) => (
                <li key={r}>{typeof r === 'string' ? r : r.reason || JSON.stringify(r)}</li>
              ))}
            </ul>
          </div>
        )}
        {s.memo && (
          <div className="mt-4 rounded-xl bg-surface-overlay p-3 ring-1 ring-white/[0.04]">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Summary</p>
            <p className="mt-1 text-sm text-slate-300">{s.memo}</p>
          </div>
        )}
      </>
    );
  }

  return (
    <>
      <div className="fixed inset-0 z-[80] bg-black/50 backdrop-blur-sm animate-fade-in" onClick={onClose} />
      <div className={`fixed inset-y-0 right-0 z-[90] flex flex-col border-l border-white/[0.06] bg-surface-raised shadow-2xl animate-slide-up ${wide ? 'w-full max-w-xl' : 'w-full max-w-md'}`}>
        <div className="flex items-center justify-between border-b border-white/[0.06] px-6 py-4">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
              {isInsurance ? 'Underwriting Memo' : 'Job Detail'}
            </p>
            <p className="font-mono text-sm font-semibold">{jobId}</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg p-2 hover:bg-white/5">
            <X className="h-5 w-5 text-slate-400" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-6">
          {!isInsurance && <div className="mb-4"><Badge status={job?.status} pulse={processing} /></div>}
          {content}
        </div>
      </div>
    </>
  );
}
