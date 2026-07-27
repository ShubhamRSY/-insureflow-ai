import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, FileCheck, ExternalLink, FileText, RefreshCw } from 'lucide-react';
import { endpoints } from '../lib/api';
import SubmissionJourney from '../components/SubmissionJourney';
import InsuranceMemoView from '../components/InsuranceMemoView';

export default function InsuranceJobDetail() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [quote, setQuote] = useState(null);

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

  useEffect(() => {
    fetchJob();
  }, [jobId]);

  // Auto-refresh while processing
  useEffect(() => {
    if (job?.status !== 'processing') return;
    const iv = setInterval(fetchJob, 3000);
    return () => clearInterval(iv);
  }, [job?.status]);

  const processing = job?.status === 'processing';
  const bundleId = job?.results?.bundle_id;

  const handleReport = async () => {
    try {
      const { blob, filename } = await endpoints.insuranceReport(jobId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert(e.message);
    }
  };

  const handleQuote = async () => {
    try {
      const d = await endpoints.insuranceQuote(jobId);
      setQuote(d);
    } catch (e) {
      alert(e.message || 'Quote not available');
    }
  };

  const handleBrokerShare = async () => {
    try {
      const r = await endpoints.createBrokerShare(bundleId);
      navigator.clipboard?.writeText(`${window.location.origin}/dashboard/broker/status/${r.token}`);
      alert('Share link copied!');
    } catch (e) {
      alert(e.message);
    }
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
        <button onClick={() => navigate('/insurance')} className="mt-4 text-sm text-slate-400 hover:text-white">
          Back to Insurance
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <div className="sticky top-0 z-10 border-b border-white/[0.06] bg-surface-raised/80 backdrop-blur-xl">
        <div className="flex items-center justify-between px-6 py-3">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/insurance')}
              className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs text-slate-400 hover:bg-white/5 hover:text-white transition"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Back
            </button>
            <div className="h-4 w-px bg-white/[0.06]" />
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Insurance Submission</p>
              <p className="font-mono text-sm font-semibold">{jobId}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {processing && (
              <span className="flex items-center gap-1.5 text-xs text-slate-500">
                <RefreshCw className="h-3 w-3 animate-spin" />
                Processing…
              </span>
            )}
            {bundleId && (
              <>
                <button onClick={handleQuote} className="btn-secondary btn-sm text-xs">
                  <FileCheck className="h-3.5 w-3.5" /> Quote PDF
                </button>
                <button onClick={handleReport} className="btn-secondary btn-sm text-xs">
                  <FileText className="h-3.5 w-3.5" /> Full Report
                </button>
                <button onClick={handleBrokerShare} className="btn-secondary btn-sm text-xs">
                  <ExternalLink className="h-3.5 w-3.5" /> Broker Share
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="mx-auto max-w-7xl px-6 py-6">
        <SubmissionJourney job={job} />

        {!processing && (
          <div className="mt-6">
            <InsuranceMemoView job={job} />
          </div>
        )}

        {quote && (
          <div className="mt-6 rounded-xl bg-surface-overlay p-5 ring-1 ring-white/[0.04]">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Quote Document</p>
              <button onClick={() => setQuote(null)} className="text-xs text-slate-500 hover:text-slate-300">Close</button>
            </div>
            <div className="max-h-[600px] overflow-y-auto rounded-lg border border-white/[0.06]" dangerouslySetInnerHTML={{ __html: typeof quote === 'string' ? quote : '' }} />
          </div>
        )}
      </div>
    </div>
  );
}
