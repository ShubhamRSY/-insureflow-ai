import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, FileCheck, ExternalLink, FileText, RefreshCw, Camera, AlertTriangle, MessageSquare } from 'lucide-react';
import { endpoints } from '../lib/api';
import { insuranceLineLabel } from '../lib/insuranceLines';
import SubmissionJourney from '../components/SubmissionJourney';
import InsuranceMemoView from '../components/InsuranceMemoView';
import UwWorksheetView from '../components/UwWorksheetView';
import UwPolicyValidator from '../components/UwPolicyValidator';
import BindReadinessPanel from '../components/BindReadinessPanel';

export default function InsuranceJobDetail() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [notes, setNotes] = useState([]);
  const [noteText, setNoteText] = useState('');
  const [checklist, setChecklist] = useState(null);
  const [infoRequests, setInfoRequests] = useState([]);
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
  const insuredName = job?.results?.insured_name || job?.results?.memo?.insured_name || '';

  useEffect(() => {
    if (!bundleId) return;
    const lob = job?.results?.insurance_line || job?.results?.product_line || '';
    endpoints.relationshipNotes(bundleId).then((r) => setNotes(r.notes || [])).catch(() => {});
    endpoints.packageChecklist(bundleId, lob).then(setChecklist).catch(() => {});
    endpoints.infoRequests(bundleId).then((r) => setInfoRequests(r.requests || [])).catch(() => {});
    setValidatedTerms(job?.results?.validated_terms || null);
  }, [bundleId, job?.results?.insurance_line, job?.results?.product_line, job?.results?.validated_terms]);

  const handleAddNote = async () => {
    if (!bundleId || !noteText.trim()) return;
    try {
      const n = await endpoints.addRelationshipNote(bundleId, { text: noteText, role: 'uw' });
      setNotes((prev) => [...prev, n]);
      setNoteText('');
    } catch (e) {
      alert(e.message);
    }
  };

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
    setQuoteLoading(true);
    try {
      const { blob, filename } = await endpoints.insuranceQuote(jobId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert(e.message || 'Quote not available');
    } finally {
      setQuoteLoading(false);
    }
  };

  const handleBrokerShare = async () => {
    try {
      const r = await endpoints.createBrokerShare(bundleId);
      const link = `${window.location.origin}/dashboard/broker/status/${r.token}`;
      await navigator.clipboard?.writeText(link);
      alert(`Share link copied!\n${link}`);
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
              {insuredName && <p className="text-xs text-slate-400">{insuredName}</p>}
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
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="mx-auto max-w-7xl px-6 py-6">
        {job?.results?.uw_worksheet && (
          <div className="mb-6 space-y-4">
            <UwWorksheetView worksheet={job.results.uw_worksheet} validatedTerms={validatedTerms} />
            <UwPolicyValidator
              bundleId={bundleId}
              worksheet={job.results.uw_worksheet}
              validatedTerms={validatedTerms}
              onValidated={(v) => {
                setValidatedTerms(v);
                fetchJob();
              }}
            />
          </div>
        )}
        {bundleId && job?.results && (
          <div className="mb-6">
            <BindReadinessPanel bundleId={bundleId} onChanged={fetchJob} />
          </div>
        )}

        <SubmissionJourney job={job} />

        {bundleId && (
          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl bg-surface-overlay p-5 ring-1 ring-white/[0.04]">
              <div className="mb-3 flex items-center gap-2">
                <MessageSquare className="h-4 w-4 text-brand" />
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Relationship notes</p>
              </div>
              <div className="mb-3 max-h-40 space-y-2 overflow-y-auto">
                {!notes.length && <p className="text-xs text-slate-500">No broker/carrier notes yet.</p>}
                {notes.map((n) => (
                  <div key={n.note_id} className="rounded-lg bg-black/20 px-3 py-2 text-xs">
                    <p className="text-slate-300">{n.text}</p>
                    <p className="mt-1 text-[10px] text-slate-600">{n.role} · {n.author} · {n.created_at ? new Date(n.created_at).toLocaleString() : ''}</p>
                  </div>
                ))}
              </div>
              <div className="flex gap-2">
                <input className="input-field flex-1 text-xs" placeholder="Add UW / broker context…" value={noteText} onChange={(e) => setNoteText(e.target.value)} />
                <button type="button" onClick={handleAddNote} className="btn-secondary btn-sm text-xs">Add</button>
              </div>
            </div>

            <div className="rounded-xl bg-surface-overlay p-5 ring-1 ring-white/[0.04]">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
                Package checklist {checklist?.lob ? `(${insuranceLineLabel(checklist.lob)})` : ''}
              </p>
              {checklist ? (
                <>
                  <p className="mb-2 text-sm text-slate-300">{checklist.completeness_pct}% complete</p>
                  <p className="text-[10px] uppercase text-slate-500 mb-1">Missing</p>
                  <ul className="mb-3 space-y-1 text-xs text-amber-300/90">
                    {(checklist.missing || []).length ? checklist.missing.map((m) => <li key={m}>• {m}</li>) : <li className="text-slate-500">None</li>}
                  </ul>
                  <p className="text-[10px] uppercase text-slate-500 mb-1">Info requests</p>
                  <ul className="space-y-1 text-xs text-slate-400">
                    {!infoRequests.length && <li>None yet</li>}
                    {infoRequests.map((r) => (
                      <li key={r.request_id}>{r.status}: {(r.documents || []).join(', ')}</li>
                    ))}
                  </ul>
                </>
              ) : (
                <p className="text-xs text-slate-500">Checklist unavailable for this job.</p>
              )}
            </div>
          </div>
        )}

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
      </div>
    </div>
  );
}
