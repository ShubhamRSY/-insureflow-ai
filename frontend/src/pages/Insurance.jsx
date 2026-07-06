import { useState, useEffect } from 'react';
import { Badge, DecisionBadge, EmptyState } from '../components/ui';
import { fmtCurrency, extractInsurance, endpoints } from '../lib/api';
import InsuranceSourceHub from '../components/InsuranceSourceHub';
import JourneyMiniStrip from '../components/JourneyMiniStrip';
import { Shield, Zap, Package, Target, ArrowRight, Building2 } from 'lucide-react';

const FLOW_STEPS = [
  { label: 'Intake', desc: 'Connect & pull broker package' },
  { label: 'Parse', desc: 'OCR, classify, extract fields' },
  { label: 'Verify', desc: 'Oracles, COPE, reconciliation' },
  { label: 'Score', desc: 'Multi-agent risk analysis' },
  { label: 'Price', desc: 'Indicated premium build-up' },
  { label: 'Decide', desc: 'UW memo & workflow' },
];

export default function InsurancePage({ presets, jobs, onRunDemo, onOpenJob, onSubmit }) {
  const [loading, setLoading] = useState(false);
  const [useV2, setUseV2] = useState(false);
  const [products, setProducts] = useState(null);
  const [calibration, setCalibration] = useState(null);
  const [ecosystemStatus, setEcosystemStatus] = useState(null);

  useEffect(() => {
    endpoints.ecosystemStatus().then(setEcosystemStatus).catch(() => {});
  }, []);

  const handleSubmit = async (payload) => {
    setLoading(true);
    try {
      if (useV2) {
        await endpoints.runInsuranceV2(payload);
      } else {
        await onSubmit(payload);
      }
    } finally {
      setLoading(false);
    }
  };

  const loadProducts = async () => {
    try { setProducts(await endpoints.insuranceProducts()); } catch (e) { alert(e.message); }
  };

  const loadCalibration = async () => {
    try { setCalibration(await endpoints.calibration()); } catch (e) { alert(e.message); }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-8 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Commercial Insurance</h1>
        <p className="mt-2 text-sm text-slate-400">
          Structured underwriting pipeline — every submission runs through parse, verify, score, price, and decide.
        </p>
      </div>

      {/* Pipeline flow narrative */}
      <div className="glass-card p-5">
        <p className="mb-4 text-xs font-semibold uppercase tracking-wider text-slate-500">Underwriting pipeline</p>
        <div className="flex flex-wrap items-center gap-2">
          {FLOW_STEPS.map((step, i) => (
            <div key={step.label} className="flex items-center gap-2">
              <div className="rounded-lg bg-surface-overlay px-3 py-2 ring-1 ring-white/[0.04]">
                <p className="text-xs font-semibold text-slate-200">{step.label}</p>
                <p className="text-[10px] text-slate-500">{step.desc}</p>
              </div>
              {i < FLOW_STEPS.length - 1 && <ArrowRight className="h-3.5 w-3.5 text-slate-600" />}
            </div>
          ))}
        </div>
        <p className="mt-3 text-xs text-slate-500">Open any job to see the full submission journey — COPE, provenance, checkpoints, and pricing breakdown.</p>
      </div>

      {ecosystemStatus && (
        <div className="flex flex-wrap gap-2">
          {(ecosystemStatus.feeds || []).map((f) => (
            <span key={f.name} className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-[10px] ring-1 ${f.mode === 'live' && f.reachable ? 'text-emerald-400 ring-emerald-500/30' : f.mode === 'degraded' ? 'text-amber-400 ring-amber-500/30' : 'text-slate-400 ring-white/10'}`}>
              <Building2 className="h-3 w-3" /> {f.name}: {f.mode}{f.reachable ? '' : ' (unreachable)'}
            </span>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between">
        <label className="flex items-center gap-2 text-xs text-slate-400">
          <input type="checkbox" checked={useV2} onChange={(e) => setUseV2(e.target.checked)} className="rounded" />
          <Zap className="h-3.5 w-3.5 text-amber-400" /> Pipeline v2 (appetite, oracles, portfolio, integration)
        </label>
        <div className="flex gap-2">
          <button type="button" onClick={loadProducts} className="btn-secondary text-xs"><Package className="h-3 w-3" /> Products</button>
          <button type="button" onClick={loadCalibration} className="btn-secondary text-xs"><Target className="h-3 w-3" /> Calibration</button>
        </div>
      </div>

      <InsuranceSourceHub onSubmit={handleSubmit} loading={loading} />

      {products && (
        <div className="glass-card p-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Insurance Products</h3>
            <button onClick={() => setProducts(null)} className="text-xs text-slate-500">Close</button>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {(products.products || products.rating_products || []).map((p, i) => (
              <div key={i} className="rounded-lg bg-surface-overlay p-3 ring-1 ring-white/[0.04]">
                <p className="text-sm font-medium text-slate-200">{p.name || p.product_name || p.product_code}</p>
                <p className="text-xs text-slate-500">{p.description || p.line_of_business || ''}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {calibration && (
        <div className="glass-card p-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Actuarial Calibration Loop</h3>
            <button onClick={() => setCalibration(null)} className="text-xs text-slate-500">Close</button>
          </div>
          <p className="mb-3 text-xs text-slate-500">{ecosystemStatus?.actuarial_loop?.recommended_action || 'Claims → actuarial feedback (simulated)'}</p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {Object.entries(calibration).filter(([k]) => !['bundle_id', 'org_id'].includes(k)).map(([key, val]) => (
              <div key={key} className="rounded-lg bg-surface-overlay p-3 ring-1 ring-white/[0.04]">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{key.replace(/_/g, ' ')}</p>
                <p className="mt-1 text-sm font-medium text-slate-300">{typeof val === 'number' ? val.toFixed(4) : String(val)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {(presets?.insurance || []).length > 0 && (
        <div className="space-y-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">One-click samples</p>
          <div className="flex flex-col gap-2">
            {(presets?.insurance || []).map((d) => (
              <button key={d.id} type="button" onClick={() => onRunDemo('insurance', d.id)}
                className="flex items-center justify-between rounded-xl border border-white/[0.06] bg-surface-overlay/30 px-4 py-3 text-left transition hover:border-brand/30">
                <span className="text-sm font-medium text-slate-200">{d.name}</span>
                <span className="text-xs text-slate-500">Run sample →</span>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="glass-card overflow-hidden">
        <div className="border-b border-white/[0.06] px-5 py-3">
          <h3 className="text-sm font-semibold">Recent jobs</h3>
          <p className="text-xs text-slate-500">Journey strip shows pipeline progress — click row for full detail</p>
        </div>
        {!jobs?.length ? (
          <EmptyState icon={Shield} title="No insurance jobs" description="Upload a broker package or run a demo" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06] bg-surface-overlay text-left text-xs uppercase tracking-wider text-slate-500">
                  <th className="px-6 py-3">Job</th>
                  <th className="px-6 py-3">Insured</th>
                  <th className="px-6 py-3">Journey</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Decision</th>
                  <th className="px-6 py-3">Premium</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {[...jobs].reverse().map(({ id, job }) => {
                  const s = extractInsurance(job);
                  return (
                    <tr key={id} onClick={() => onOpenJob('insurance', id)} className="cursor-pointer transition hover:bg-white/[0.02]">
                      <td className="px-6 py-3.5 font-mono text-xs text-slate-400">{id}</td>
                      <td className="px-6 py-3.5 text-slate-300">{s.insuredName || '—'}</td>
                      <td className="px-6 py-3.5"><JourneyMiniStrip job={job} /></td>
                      <td className="px-6 py-3.5"><Badge status={job?.status} pulse={job?.status === 'processing'} /></td>
                      <td className="px-6 py-3.5"><DecisionBadge decision={s.decision} jobStatus={job?.status} /></td>
                      <td className="px-6 py-3.5 font-medium">{fmtCurrency(s.premium)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
