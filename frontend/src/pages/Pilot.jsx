import { useCallback, useEffect, useState } from 'react';
import { FlaskConical, RefreshCw, Play, ShieldAlert, CheckCircle2, AlertTriangle } from 'lucide-react';
import { Badge, EmptyState, StatCard } from '../components/ui';
import { endpoints } from '../lib/api';

const statusColor = (s) => {
  if (s === 'ready' || s === 'sandbox_ready') return 'ok';
  if (s === 'simulated') return 'pending';
  if (s === 'degraded' || s === 'missing') return 'failed';
  return s;
};

export default function PilotPage() {
  const [readiness, setReadiness] = useState(null);
  const [packages, setPackages] = useState([]);
  const [calibration, setCalibration] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [r, p, c] = await Promise.all([
        endpoints.pilotSandboxStatus(),
        endpoints.pilotPackages(),
        endpoints.pilotCalibration().catch(() => null),
      ]);
      setReadiness(r);
      setPackages(p.packages || []);
      setCalibration(c);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const seed = async () => {
    setBusy('seed');
    setError('');
    setMessage('');
    try {
      const res = await endpoints.pilotSeed();
      setMessage(`Seeded ${res.seeded} demo packages`);
      await load();
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy('');
    }
  };

  const runOne = async (partner, submission_id) => {
    setBusy(`${partner}/${submission_id}`);
    setError('');
    setMessage('');
    try {
      const res = await endpoints.pilotRun({ partner, submission_id });
      setMessage(`Started ${submission_id} → job ${res.job_id}`);
      await load();
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy('');
    }
  };

  const calibrate = async () => {
    setBusy('calibrate');
    setError('');
    setMessage('');
    try {
      const res = await endpoints.pilotCalibrate();
      setCalibration(res.summary);
      setMessage(`Calibrated ${res.ran} packages (${res.blocked_pii} blocked by PII)`);
      await load();
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy('');
    }
  };

  const redactOne = async (partner, submission_id) => {
    setBusy(`redact:${partner}/${submission_id}`);
    setError('');
    setMessage('');
    try {
      const res = await endpoints.pilotRedact({ partner, submission_id, inplace: true });
      const after = res.after || {};
      setMessage(
        `Redacted ${submission_id}: blocking ${res.before?.blocking_count ?? '?'}→${after.blocking_count ?? '?'} (${(res.files_changed || []).length} files)`,
      );
      await load();
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy('');
    }
  };

  const ingestEmail = async () => {
    setBusy('ingest-email');
    setError('');
    setMessage('');
    try {
      const res = await endpoints.pilotIngestEmail({ partner: 'email', limit: 10, unread_only: true, auto_redact: true });
      setMessage(`Ingested ${res.count} package(s) from IMAP (${res.emails_found ?? 0} emails scanned)`);
      await load();
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy('');
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-24">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
      </div>
    );
  }

  const overall = readiness?.overall || 'not_ready';
  const matchPct = calibration?.match_rate != null ? `${Math.round(calibration.match_rate * 100)}%` : '—';

  return (
    <div className="mx-auto max-w-6xl space-y-8 animate-fade-in">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-500/15">
            <FlaskConical className="h-6 w-6 text-amber-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Pilot Lab</h1>
            <p className="mt-1 text-slate-400">Sandbox readiness, redacted packages, shadow underwriting</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={load} className="btn-secondary btn-sm text-xs">
            <RefreshCw className="h-3.5 w-3.5" /> Refresh
          </button>
          <button type="button" onClick={seed} disabled={!!busy} className="btn-secondary btn-sm text-xs">
            Seed demos
          </button>
          <button type="button" onClick={ingestEmail} disabled={!!busy} className="btn-secondary btn-sm text-xs">
            {busy === 'ingest-email' ? 'Pulling…' : 'Ingest email'}
          </button>
          <button type="button" onClick={calibrate} disabled={!!busy} className="btn-primary btn-sm text-xs">
            {busy === 'calibrate' ? 'Running…' : 'Calibrate all'}
          </button>
        </div>
      </div>

      {error && <div className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}
      {message && <div className="rounded-xl bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">{message}</div>}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Readiness" value={overall.replace(/_/g, ' ')} sub={readiness?.shadow_mode ? 'Shadow mode ON' : 'Shadow mode OFF'} accent="insurance" />
        <StatCard label="Required feeds" value={`${readiness?.required_ready ?? 0}/${readiness?.required_total ?? 0}`} sub="CLUE / A-PLUS / Guidewire / Redis" />
        <StatCard label="Packages" value={String(packages.length)} sub="Under pilot_packages/" />
        <StatCard label="Match rate" value={matchPct} sub={`n=${calibration?.labeled_sample_size ?? 0} labeled`} accent="success" />
      </div>

      {readiness?.shadow_mode && (
        <div className="flex items-start gap-3 rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
          <p>Bind is disabled while shadow mode is on. Configure live Guidewire and set <code className="text-amber-200">PILOT_SHADOW_MODE=false</code> to enable production bind.</p>
        </div>
      )}

      <section className="glass-card p-5 space-y-3">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Free outreach (mailto)</h3>
        <p className="text-sm text-slate-400">
          Opens your mail client with a draft — no paid tools. Full templates live in{' '}
          <code className="text-slate-300">docs/THIS_WEEK_OUTREACH.md</code>.
        </p>
        <div className="flex flex-wrap gap-2">
          <a
            className="btn-secondary btn-sm text-xs"
            href={`mailto:?subject=${encodeURIComponent('30-day shadow UW pilot — redacted commercial submissions')}&body=${encodeURIComponent(
              `Hi [First name],

I'm with Rytera (ryterainc.com). We run multi-agent commercial underwriting with licensed UW sign-off.

Looking for a 30-day shadow pilot: 20–50 redacted packages + one UW 2–4 hrs/week. Bind stays off.

Open to 15 minutes this week?

Best,
[Your name]`,
            )}`}
          >
            Pilot carrier / MGA
          </a>
          <a
            className="btn-secondary btn-sm text-xs"
            href={`mailto:?subject=${encodeURIComponent('Sandbox API access — Rytera commercial UW (CLUE)')}&body=${encodeURIComponent(
              `Hello,

Rytera (ryterainc.com) needs sandbox / UAT CLUE Commercial access for a shadow underwriting pilot.

Please advise sandbox URL, auth, test FEINs, rate limits, and commercial contact.

Thank you,
[Your name]`,
            )}`}
          >
            LexisNexis CLUE
          </a>
          <a
            className="btn-secondary btn-sm text-xs"
            href={`mailto:?subject=${encodeURIComponent('Sandbox API access — A-PLUS for Rytera commercial UW pilot')}&body=${encodeURIComponent(
              `Hello,

Requesting sandbox credentials for A-PLUS property loss history for Rytera's multi-agent underwriting platform.

Please send sandbox URL, API key process, and sample request/response docs.

Thank you,
[Your name]`,
            )}`}
          >
            Verisk A-PLUS
          </a>
        </div>
      </section>

      <section className="glass-card overflow-hidden">
        <div className="border-b border-white/[0.06] px-5 py-3">
          <h3 className="text-sm font-semibold">Integration feeds</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/[0.06] bg-surface-overlay text-left text-xs uppercase tracking-wider text-slate-500">
                <th className="px-6 py-3">Feed</th>
                <th className="px-6 py-3">Category</th>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3">Next action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {(readiness?.feeds || []).map((f) => (
                <tr key={f.name} className="hover:bg-white/[0.02]">
                  <td className="px-6 py-3.5 text-slate-200">{f.name}{f.required_for_pilot ? ' *' : ''}</td>
                  <td className="px-6 py-3.5 text-xs text-slate-400">{f.category}</td>
                  <td className="px-6 py-3.5"><Badge status={statusColor(f.status)} /></td>
                  <td className="px-6 py-3.5 text-xs text-slate-400">{f.next_action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="glass-card overflow-hidden">
        <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-3">
          <h3 className="text-sm font-semibold">Pilot packages</h3>
          <p className="text-xs text-slate-500">Drop redacted files under pilot_packages/&lt;partner&gt;/&lt;id&gt;/</p>
        </div>
        {packages.length === 0 ? (
          <EmptyState
            icon={FlaskConical}
            title="No pilot packages"
            description="Seed demo scenarios or drop partner redacted submissions into pilot_packages/"
            action={<button type="button" className="btn-primary btn-sm" onClick={seed}>Seed demos</button>}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06] bg-surface-overlay text-left text-xs uppercase tracking-wider text-slate-500">
                  <th className="px-6 py-3">Partner</th>
                  <th className="px-6 py-3">Submission</th>
                  <th className="px-6 py-3">Insured</th>
                  <th className="px-6 py-3">Docs</th>
                  <th className="px-6 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {packages.map((p) => (
                  <tr key={`${p.partner}/${p.submission_id}`} className="hover:bg-white/[0.02]">
                    <td className="px-6 py-3.5 text-slate-300">{p.partner}</td>
                    <td className="px-6 py-3.5 text-slate-200">{p.submission_id}</td>
                    <td className="px-6 py-3.5 text-slate-400">{p.insured_name}</td>
                    <td className="px-6 py-3.5 text-xs text-slate-500">
                      {p.has_acord ? 'ACORD ' : ''}
                      {p.has_loss_run ? 'Loss ' : ''}
                      {p.has_sov ? 'SOV ' : ''}
                      {p.inspection_count ? `Insp×${p.inspection_count}` : ''}
                    </td>
                    <td className="px-6 py-3.5 text-right">
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          className="btn-secondary btn-sm text-xs"
                          disabled={!!busy}
                          onClick={() => redactOne(p.partner, p.submission_id)}
                        >
                          {busy === `redact:${p.partner}/${p.submission_id}` ? '…' : 'Redact'}
                        </button>
                        <button
                          type="button"
                          className="btn-secondary btn-sm text-xs"
                          disabled={!!busy}
                          onClick={() => runOne(p.partner, p.submission_id)}
                        >
                          <Play className="h-3.5 w-3.5" />
                          {busy === `${p.partner}/${p.submission_id}` ? '…' : 'Run'}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {calibration && calibration.sample_size > 0 && (
        <section className="glass-card p-5">
          <h3 className="text-sm font-semibold">Calibration</h3>
          <div className="mt-3 flex flex-wrap gap-4 text-sm text-slate-300">
            <span className="inline-flex items-center gap-1.5"><CheckCircle2 className="h-4 w-4 text-emerald-400" /> Match {matchPct}</span>
            <span>Overrides {calibration.override_rate != null ? `${Math.round(calibration.override_rate * 100)}%` : '—'}</span>
            <span>By decision: {Object.entries(calibration.by_decision || {}).map(([k, v]) => `${k}:${v}`).join(' · ')}</span>
          </div>
          {(calibration.mismatches || []).length > 0 && (
            <div className="mt-4 space-y-1">
              <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-amber-400">
                <AlertTriangle className="h-3.5 w-3.5" /> Mismatches
              </p>
              {calibration.mismatches.slice(0, 8).map((m) => (
                <p key={`${m.partner}-${m.submission_id}`} className="text-xs text-slate-400">
                  {m.submission_id}: ai={m.ai} expected={m.expected}
                </p>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
