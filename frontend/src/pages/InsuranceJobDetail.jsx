import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, FileCheck, ExternalLink, FileText, RefreshCw, AlertTriangle, Trash2 } from 'lucide-react';
import { endpoints } from '../lib/api';
import { displayText } from '../lib/safe';
import MemoReportView, { Collapsible } from '../components/MemoReportView';
import SubmissionJourney from '../components/SubmissionJourney';
import UwWorksheetView from '../components/UwWorksheetView';
import UwPolicyValidator from '../components/UwPolicyValidator';
import RateProvenance from '../components/RateProvenance';

export default function InsuranceJobDetail({ onDeleted, onDeleteJob }) {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [validatedTerms, setValidatedTerms] = useState(null);

  const fetchJob = async () => {
    try {
      const data = await endpoints.insuranceJob(jobId);
      setJob(data);
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchJob(); }, [jobId]);
  useEffect(() => {
    if (job?.status !== 'processing') return;
    const iv = setInterval(fetchJob, 3000);
    return () => clearInterval(iv);
  }, [job?.status]);

  const processing = job?.status === 'processing';
  const bundleId = job?.results?.bundle_id;
  const insuredName = displayText(job?.results?.insured_name || job?.results?.memo?.insured_name);
  const submittedAt = job?.created_at
    ? new Date(job.created_at).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
    : null;
  const updatedAt = job?.updated_at
    ? new Date(job.updated_at).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
    : null;
  const completedAt = job?.status === 'completed' && job?.created_at && job?.updated_at
    ? updatedAt
    : null;
  const processingDuration = job?.status === 'completed' && job?.created_at && job?.updated_at
    ? Math.round((new Date(job.updated_at) - new Date(job.created_at)) / 1000)
    : null;

  useEffect(() => {
    if (!bundleId) return;
    setValidatedTerms(job?.results?.validated_terms || null);
  }, [bundleId, job?.results?.validated_terms]);

  const handleReport = async () => {
    try {
      const { blob, filename } = await endpoints.insuranceReport(jobId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = filename; a.click();
      URL.revokeObjectURL(url);
    } catch (e) { alert(e.message); }
  };

  const handleQuote = async () => {
    setQuoteLoading(true);
    try {
      const { blob, filename } = await endpoints.insuranceQuote(jobId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = filename; a.click();
      URL.revokeObjectURL(url);
    } catch (e) { alert(e.message || 'Quote not available'); }
    finally { setQuoteLoading(false); }
  };

  const handleBrokerShare = async () => {
    try {
      const r = await endpoints.createBrokerShare(bundleId);
      const link = `${window.location.origin}/dashboard/broker/status/${r.token}`;
      await navigator.clipboard?.writeText(link);
      alert(`Share link copied!\n${link}`);
    } catch (e) { alert(e.message); }
  };

  const handleDeleteJob = async () => {
    if (!window.confirm('Delete this submission? This cannot be undone.')) return;
    try {
      if (onDeleteJob) await onDeleteJob(jobId);
      else await endpoints.deleteJob(jobId);
      await onDeleted?.();
      navigate('/insurance');
    } catch (e) { alert(e.message || 'Could not delete submission'); }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-32">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
        <span className="ml-3 text-sm text-slate-400">Loading submission…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-16 text-center">
        <p className="text-red-400">{error}</p>
        <button onClick={() => navigate('/insurance')} className="mt-4 text-sm text-slate-400 hover:text-white">Back to Insurance</button>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="py-16 text-center">
        <p className="text-slate-400">Submission not found.</p>
        <button onClick={() => navigate('/insurance')} className="mt-4 text-sm text-slate-400 hover:text-white">Back to Insurance</button>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <div className="sticky top-0 z-10 border-b border-white/[0.06] bg-surface-raised/80 backdrop-blur-xl">
        <div className="flex items-center justify-between px-6 py-3">
          <div className="flex items-center gap-4">
            <button onClick={() => (window.history.length > 1 ? navigate(-1) : navigate('/insurance'))}
              className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs text-slate-400 hover:bg-white/5 hover:text-white transition">
              <ArrowLeft className="h-3.5 w-3.5" /> Back
            </button>
            <div className="h-4 w-px bg-white/[0.06]" />
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Insurance Submission</p>
              <p className="text-sm font-semibold">{insuredName || 'Unnamed applicant'}</p>
              <p className="font-mono text-[11px] text-slate-500">
                {jobId}{submittedAt ? ` · Submitted ${submittedAt}` : ''}
                {completedAt && processingDuration != null ? ` · Completed ${completedAt} (${processingDuration}s)` : ''}
                {updatedAt && !completedAt ? ` · Updated ${updatedAt}` : ''}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {processing && (
              <span className="flex items-center gap-1.5 text-xs text-slate-500">
                <RefreshCw className="h-3 w-3 animate-spin" /> Processing…
                {submittedAt && (
                  <span className="ml-1 text-slate-600">
                    ({Math.round((Date.now() - new Date(job.created_at).getTime()) / 1000)}s elapsed)
                  </span>
                )}
              </span>
            )}
            {bundleId && (
              <>
                <button onClick={handleQuote} disabled={quoteLoading} className="btn-secondary btn-sm text-xs">
                  {quoteLoading ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <FileCheck className="h-3.5 w-3.5" />} Quote PDF
                </button>
                <button onClick={handleReport} className="btn-secondary btn-sm text-xs">
                  <FileText className="h-3.5 w-3.5" /> Full Report
                </button>
                <button onClick={handleBrokerShare} className="btn-secondary btn-sm text-xs">
                  <ExternalLink className="h-3.5 w-3.5" /> Broker Share
                </button>
              </>
            )}
            <button type="button" onClick={handleDeleteJob} className="btn-secondary btn-sm text-xs text-red-400 hover:text-red-300">
              <Trash2 className="h-3.5 w-3.5" /> Delete
            </button>
          </div>
        </div>
      </div>

      {job?.archived && (
        <div className="border-b border-amber-500/20 bg-amber-500/10 px-6 py-2 text-sm text-amber-200">
          Archived from the landing-zone disk. Memo and decision are here.
        </div>
      )}

      {/* Content */}
      <div className="mx-auto max-w-4xl px-6 py-6">
        {!processing && !job?.results?.memo && !job?.results?.uw_worksheet && (
          <div className="mb-6 rounded-xl border border-amber-500/20 bg-amber-500/5 p-6 text-center">
            <AlertTriangle className="mx-auto mb-3 h-8 w-8 text-amber-400" />
            <p className="text-sm font-semibold text-amber-200">Pipeline has not run yet</p>
            <p className="mt-1 text-xs text-slate-400">Run the pipeline to extract data and generate the underwriting memo.</p>
            <button onClick={async () => {
              try { await endpoints.retryJob(jobId); fetchJob(); } catch (e) { alert(e.message || 'Could not start pipeline'); }
            }} className="mt-4 inline-flex items-center gap-2 rounded-xl bg-brand px-4 py-2 text-xs font-semibold text-white hover:bg-brand-light transition">
              <RefreshCw className="h-3.5 w-3.5" /> Run Pipeline
            </button>
          </div>
        )}

        {/* Primary: Memo Report */}
        {!processing && <MemoReportView job={job} />}

        {/* Technical Details — collapsed by default */}
        <div className="mt-8 space-y-4">
          <Collapsible title="Underwriting Worksheet" defaultOpen={false}>
            {job?.results?.uw_worksheet ? (
              <div className="space-y-3">
                <UwWorksheetView worksheet={job.results.uw_worksheet} validatedTerms={validatedTerms} />
                <UwPolicyValidator
                  bundleId={bundleId}
                  worksheet={job.results.uw_worksheet}
                  validatedTerms={validatedTerms}
                  onValidated={(v) => { setValidatedTerms(v); fetchJob(); }}
                />
              </div>
            ) : (
              <p className="text-xs text-slate-500">No worksheet available.</p>
            )}
          </Collapsible>

          <Collapsible title="Pipeline Journey" defaultOpen={false}>
            <SubmissionJourney job={job} />
          </Collapsible>

          {(job?.quote_result?.metadata || job?.results?.quote_full?.metadata) && (
            <Collapsible title="Rate Provenance" defaultOpen={false}>
              <RateProvenance metadata={job.quote_result?.metadata || job.results.quote_full.metadata} />
            </Collapsible>
          )}
        </div>
      </div>
    </div>
  );
}
