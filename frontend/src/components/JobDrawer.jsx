import { X, FileCheck, ExternalLink, FileText } from 'lucide-react';
import { Badge } from './ui';
import { extractMortgage, endpoints, fmtCurrency } from '../lib/api';
import InsuranceMemoView from './InsuranceMemoView';
import SubmissionJourney from './SubmissionJourney';

export default function JobDrawer({ job, vertical, jobId, onClose }) {
  if (!jobId) return null;

  const processing = job?.status === 'processing';
  const failed = job?.status === 'failed';
  const isInsurance = vertical === 'insurance';
  const wide = isInsurance || vertical === 'mortgage' || vertical === 'lending';

  const bundleId = job?.results?.bundle_id;

  let content;
  if (failed) {
    content = (
      <div className="rounded-xl bg-red-500/10 p-4 text-sm text-red-300">{job.error || 'Unknown error'}</div>
    );
  } else if (isInsurance) {
    content = (
      <>
        <SubmissionJourney job={job} />
        {processing && (
          <div className="mt-6 flex flex-col items-center py-6 text-center">
            <div className="mb-3 h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
            <p className="text-sm text-slate-300">Running underwriting pipeline…</p>
            <p className="mt-1 text-xs text-slate-500">Results will appear automatically</p>
          </div>
        )}
        {!processing && (
          <>
            <div className="my-6 border-t border-white/[0.06]" />
            <InsuranceMemoView job={job} />
        {bundleId && (
          <div className="mt-4 flex flex-wrap gap-2">
            <button type="button" onClick={async () => {
              try {
                const { blob, filename } = await endpoints.insuranceQuote(jobId);
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                a.click();
                URL.revokeObjectURL(url);
              } catch (e) { alert(e.message || 'Quote not available'); }
            }} className="btn-secondary btn-sm text-xs"><FileCheck className="h-3.5 w-3.5" /> Quote PDF</button>
            <button type="button" onClick={async () => {
              try {
                const { blob, filename } = await endpoints.insuranceReport(jobId);
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                a.click();
                URL.revokeObjectURL(url);
              } catch (e) { alert(e.message || 'Report not available'); }
            }} className="btn-secondary btn-sm text-xs"><FileText className="h-3.5 w-3.5" /> Full Report</button>
            <button type="button" onClick={async () => {
              try {
                const r = await endpoints.createBrokerShare(bundleId);
                const link = `${window.location.origin}/dashboard/broker/status/${r.token}`;
                await navigator.clipboard?.writeText(link);
                alert(`Share link copied!\n${link}`);
              } catch (e) { alert(e.message); }
            }} className="btn-secondary btn-sm text-xs"><ExternalLink className="h-3.5 w-3.5" /> Broker Share</button>
          </div>
        )}
          </>
        )}
      </>
    );
  } else if (processing) {
    content = (
      <div className="flex flex-col items-center py-12 text-center">
        <div className="mb-4 h-10 w-10 animate-spin rounded-full border-2 border-brand border-t-transparent" />
        <p className="text-slate-300">Processing submission…</p>
        <p className="mt-1 text-sm text-slate-500">Results will appear automatically</p>
      </div>
    );
  } else {
    const s = extractMortgage(job);
    const denied = String(s.decision || '').toLowerCase() === 'deny';
    const sevColor = (sev) =>
      ({ critical: 'text-red-400', high: 'text-red-300', moderate: 'text-amber-400', low: 'text-emerald-400' }[String(sev || 'moderate').toLowerCase()] || 'text-slate-400');
    const sevBar = (sev) =>
      ({ critical: 'bg-red-500', high: 'bg-red-400', moderate: 'bg-amber-400', low: 'bg-emerald-400' }[String(sev || 'moderate').toLowerCase()] || 'bg-slate-500');
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
        {s.productLine && (
          <p className="mt-3 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            {s.productLine.replace(/_/g, ' ')} package
          </p>
        )}
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
        {s.findings?.length > 0 && (
          <div className="mt-4">
            <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">Key Findings</p>
            <div className="space-y-2">
              {s.findings.map((f, i) => {
                const title = typeof f === 'string' ? f : (f.title || 'Finding');
                const desc = typeof f === 'string' ? '' : (f.description || '');
                const sev = typeof f === 'string' ? 'moderate' : f.severity;
                return (
                  <div key={i} className="flex gap-3 rounded-xl bg-surface-overlay p-3 ring-1 ring-white/[0.04]">
                    <span className={`mt-0.5 h-8 w-1 shrink-0 rounded-full ${sevBar(sev)}`} />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-slate-200">{title}</p>
                      {desc && <p className="mt-0.5 text-xs text-slate-400">{desc}</p>}
                      <p className={`mt-1 text-[10px] font-bold uppercase tracking-wider ${sevColor(sev)}`}>{String(sev || 'moderate').toUpperCase()}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
        {s.violations?.length > 0 && (
          <div className="mt-4 rounded-xl bg-red-500/5 p-3 ring-1 ring-red-500/20">
            <p className="text-[10px] font-bold uppercase tracking-wider text-red-400">Compliance Violations</p>
            <ul className="mt-2 space-y-1 text-xs text-red-200/80">
              {s.violations.map((v, i) => {
                const msg = typeof v === 'string' ? v : (v.message || v.description || v.rule_id || JSON.stringify(v));
                const sev = typeof v === 'string' ? '' : v.severity;
                return <li key={i} className="flex items-start gap-2"><span>{msg}</span>{sev && <span className={`ml-auto shrink-0 text-[9px] font-bold uppercase ${sevColor(sev)}`}>{sev}</span>}</li>;
              })}
            </ul>
          </div>
        )}
        {s.conditions?.length > 0 && (
          <div className="mt-4 rounded-xl bg-surface-overlay p-3 ring-1 ring-white/[0.04]">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Conditions</p>
            <ul className="mt-2 space-y-1 text-xs text-slate-300">
              {s.conditions.map((c, i) => <li key={i}>{c}</li>)}
            </ul>
          </div>
        )}
        {s.bundleId && (
          <div className="mt-4 flex flex-wrap gap-2">
            <button type="button" onClick={async () => {
              try {
                const { blob, filename } = await endpoints.insuranceReport(jobId);
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                a.click();
                URL.revokeObjectURL(url);
              } catch (e) { alert(e.message || 'Report not available'); }
            }} className="btn-secondary btn-sm text-xs"><FileText className="h-3.5 w-3.5" /> Full Report</button>
          </div>
        )}
      </>
    );
  }

  return (
    <>
      <div className="fixed inset-0 z-[80] bg-black/50 backdrop-blur-sm animate-fade-in" onClick={onClose} />
      <div className={`fixed inset-y-0 right-0 z-[90] flex flex-col border-l border-white/[0.06] bg-surface-raised shadow-2xl animate-slide-up ${wide ? 'w-full max-w-2xl' : 'w-full max-w-md'}`}>
        <div className="flex items-center justify-between border-b border-white/[0.06] px-6 py-4">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
              {isInsurance ? 'Submission Journey' : 'Job Detail'}
            </p>
            <p className="font-mono text-sm font-semibold">{jobId}</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg p-2 hover:bg-white/5">
            <X className="h-5 w-5 text-slate-400" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-6">
          {!isInsurance && <div className="mb-4"><Badge status={job?.status} pulse={processing} /></div>}
          {isInsurance && processing && (
            <div className="mb-4"><Badge status={job?.status} pulse /></div>
          )}
          {content}
        </div>
      </div>
    </>
  );
}
