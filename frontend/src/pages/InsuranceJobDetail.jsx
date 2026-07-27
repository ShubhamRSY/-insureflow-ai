import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, FileCheck, ExternalLink, FileText, RefreshCw, Camera, AlertTriangle } from 'lucide-react';
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

        {!processing && job.results?.visual_analysis && (
          <div className="mt-6 rounded-xl bg-surface-overlay p-5 ring-1 ring-white/[0.04]">
            <div className="flex items-center gap-2 mb-4">
              <Camera className="h-4 w-4 text-brand" />
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Visual Analysis</p>
              <span className={`ml-auto text-xs px-2 py-0.5 rounded-full ${
                job.results.visual_analysis.overall_visual_risk === 'critical' ? 'bg-red-500/20 text-red-400' :
                job.results.visual_analysis.overall_visual_risk === 'high' ? 'bg-orange-500/20 text-orange-400' :
                job.results.visual_analysis.overall_visual_risk === 'moderate' ? 'bg-yellow-500/20 text-yellow-400' :
                'bg-green-500/20 text-green-400'
              }`}>
                Risk: {job.results.visual_analysis.overall_visual_risk}
              </span>
            </div>
            <p className="text-xs text-slate-400 mb-3">{job.results.visual_analysis.processing_notes}</p>
            <div className="grid grid-cols-3 gap-3 mb-3">
              <div className="text-center rounded-lg bg-black/20 py-2">
                <p className="text-[10px] text-slate-500 uppercase">Photos</p>
                <p className="text-lg font-bold text-slate-200">{job.results.visual_analysis.analyzed_photos}/{job.results.visual_analysis.total_photos}</p>
              </div>
              <div className="text-center rounded-lg bg-black/20 py-2">
                <p className="text-[10px] text-slate-500 uppercase">Damage</p>
                <p className="text-lg font-bold text-slate-200">{job.results.visual_analysis.damage_count}</p>
              </div>
              <div className="text-center rounded-lg bg-black/20 py-2">
                <p className="text-[10px] text-slate-500 uppercase">Quality</p>
                <p className="text-lg font-bold text-slate-200">{job.results.visual_analysis.overall_quality}</p>
              </div>
            </div>
            {job.results.visual_analysis.risk_factors?.length > 0 && (
              <div className="mb-3">
                <p className="text-xs font-semibold text-slate-500 mb-1">Risk Factors</p>
                {job.results.visual_analysis.risk_factors.map((f, i) => (
                  <div key={i} className="flex items-start gap-1 text-xs text-orange-400/80">
                    <AlertTriangle className="h-3 w-3 mt-0.5 shrink-0" />
                    {f}
                  </div>
                ))}
              </div>
            )}
            {job.results.visual_analysis.recommendations?.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-slate-500 mb-1">Recommendations</p>
                {job.results.visual_analysis.recommendations.map((r, i) => (
                  <p key={i} className="text-xs text-slate-400">&bull; {r}</p>
                ))}
              </div>
            )}
          </div>
        )}

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
