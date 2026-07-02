import { useState } from 'react';
import { Badge, DecisionBadge, EmptyState } from '../components/ui';
import { fmtCurrency, extractInsurance, endpoints } from '../lib/api';
import InsuranceSourceHub from '../components/InsuranceSourceHub';
import { Shield, BarChart3, FileSearch, Link, Zap, Package, TrendingDown, Target } from 'lucide-react';

export default function InsurancePage({ presets, jobs, onRunDemo, onOpenJob, onSubmit }) {
  const [loading, setLoading] = useState(false);
  const [copeData, setCopeData] = useState(null);
  const [missingDocs, setMissingDocs] = useState(null);
  const [focusedJob, setFocusedJob] = useState(null);
  const [useV2, setUseV2] = useState(false);
  const [products, setProducts] = useState(null);
  const [lossData, setLossData] = useState(null);
  const [calibration, setCalibration] = useState(null);

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

  const loadCope = async (bundleId) => {
    try {
      const data = await endpoints.copeAnalysis(bundleId);
      setCopeData(data);
      setFocusedJob(bundleId);
    } catch (e) {
      alert('COPE analysis: ' + e.message);
    }
  };

  const loadMissingDocs = async (bundleId) => {
    try {
      const data = await endpoints.missingDocuments(bundleId);
      setMissingDocs(data);
      setFocusedJob(bundleId);
    } catch (e) {
      alert('Missing docs: ' + e.message);
    }
  };

  const loadProducts = async () => {
    try {
      const data = await endpoints.insuranceProducts();
      setProducts(data);
    } catch (e) {
      alert('Products: ' + e.message);
    }
  };

  const loadLossExp = async (bundleId) => {
    try {
      const data = await endpoints.lossExperience({ bundle_id: bundleId });
      setLossData(data);
    } catch (e) {
      alert('Loss experience: ' + e.message);
    }
  };

  const loadCalibration = async () => {
    try {
      const data = await endpoints.calibration();
      setCalibration(data);
    } catch (e) {
      alert('Calibration: ' + e.message);
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-10 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Commercial Insurance</h1>
        <p className="mt-2 text-sm text-slate-400">
          Connect a document source, pull the broker package, and run underwriting.
        </p>
      </div>

      <div className="flex items-center justify-between">
        <label className="flex items-center gap-2 text-xs text-slate-400">
          <input type="checkbox" checked={useV2} onChange={e => setUseV2(e.target.checked)} className="rounded" />
          <Zap className="h-3.5 w-3.5 text-amber-400" /> Pipeline v2 (appetite filter, oracles, portfolio, integration, auto broker share)
        </label>
        <div className="flex gap-2">
          <button type="button" onClick={loadProducts} className="btn-secondary text-xs"><Package className="h-3 w-3" /> Products</button>
          <button type="button" onClick={loadCalibration} className="btn-secondary text-xs"><Target className="h-3 w-3" /> Calibration</button>
        </div>
      </div>
      <InsuranceSourceHub onSubmit={handleSubmit} loading={loading} />

      {/* COPE Analysis Panel */}
      {copeData && (
        <div className="glass-card p-5">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
              <BarChart3 className="mr-2 inline h-4 w-4" />
              COPE Risk Analysis — {focusedJob}
            </h3>
            <button onClick={() => setCopeData(null)} className="text-xs text-slate-500 hover:text-slate-300">Close</button>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-lg bg-black/20 p-3">
              <span className="text-xs text-slate-500">Construction</span>
              <p className="mt-1 text-sm font-medium capitalize">{copeData.construction?.class || copeData.construction?.raw || '—'}</p>
              <span className={`text-xs ${copeData.construction?.mod_pct > 0 ? 'text-red-400' : 'text-green-400'}`}>
                {copeData.construction?.mod_pct > 0 ? '+' : ''}{copeData.construction?.mod_pct}%
              </span>
            </div>
            <div className="rounded-lg bg-black/20 p-3">
              <span className="text-xs text-slate-500">Occupancy</span>
              <p className="mt-1 text-sm font-medium capitalize">{copeData.occupancy?.class || copeData.occupancy?.raw || '—'}</p>
              <span className={`text-xs ${copeData.occupancy?.mod_pct > 0 ? 'text-red-400' : 'text-green-400'}`}>
                {copeData.occupancy?.mod_pct > 0 ? '+' : ''}{copeData.occupancy?.mod_pct}%
              </span>
            </div>
            <div className="rounded-lg bg-black/20 p-3">
              <span className="text-xs text-slate-500">Protection</span>
              <p className="mt-1 text-sm font-medium">ISO Class {copeData.protection?.class || '—'}</p>
              <span className={`text-xs ${copeData.protection?.mod_pct > 0 ? 'text-red-400' : 'text-green-400'}`}>
                {copeData.protection?.mod_pct > 0 ? '+' : ''}{copeData.protection?.mod_pct}%
              </span>
            </div>
            <div className="rounded-lg bg-black/20 p-3">
              <span className="text-xs text-slate-500">Exposure</span>
              <p className="mt-1 text-sm font-medium">{copeData.exposure?.types?.join(', ') || 'None'}</p>
              <span className={`text-xs ${copeData.exposure?.mod_pct > 0 ? 'text-red-400' : 'text-green-400'}`}>
                {copeData.exposure?.mod_pct > 0 ? '+' : ''}{copeData.exposure?.mod_pct}%
              </span>
            </div>
          </div>
          <div className="mt-3 flex items-center gap-3 rounded-lg bg-brand/10 px-4 py-2">
            <span className="text-xs text-slate-400">Risk Grade: <strong className={`${copeData.cope_score?.risk_grade === 'preferred' ? 'text-green-400' : copeData.cope_score?.risk_grade === 'non_standard' ? 'text-red-400' : 'text-yellow-400'}`}>{copeData.cope_score?.risk_grade?.toUpperCase()}</strong></span>
            <span className="text-xs text-slate-400">Schedule Mod: <strong>{copeData.cope_score?.schedule_mod_pct > 0 ? '+' : ''}{copeData.cope_score?.schedule_mod_pct}%</strong></span>
            <span className="text-xs text-slate-400">Score: {copeData.cope_score?.total_score?.toFixed(3)}</span>
          </div>
        </div>
      )}

      {/* Missing Documents Panel */}
      {missingDocs && (
        <div className="glass-card p-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
              <FileSearch className="mr-2 inline h-4 w-4" />
              Missing Documents — {focusedJob}
            </h3>
            <button onClick={() => setMissingDocs(null)} className="text-xs text-slate-500 hover:text-slate-300">Close</button>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Complete: {(missingDocs.completeness_pct * 100).toFixed(0)}%</span>
            <div className="h-2 flex-1 rounded-full bg-black/30">
              <div className="h-2 rounded-full bg-brand" style={{ width: `${missingDocs.completeness_pct * 100}%` }} />
            </div>
          </div>
          {missingDocs.missing_documents?.length > 0 && (
            <ul className="mt-3 space-y-1">
              {missingDocs.missing_documents.map((d, i) => (
                <li key={i} className="flex items-center gap-2 text-xs text-red-400">
                  <span className="h-1.5 w-1.5 rounded-full bg-red-400" />
                  {d}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {products && (
        <div className="glass-card p-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400"><Package className="mr-2 inline h-4 w-4" /> Insurance Products</h3>
            <button onClick={() => setProducts(null)} className="text-xs text-slate-500 hover:text-slate-300">Close</button>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {(products.products || products.rating_products || []).map((p, i) => (
              <div key={i} className="rounded-lg bg-surface-overlay p-3 ring-1 ring-white/[0.04]">
                <p className="text-sm font-medium text-slate-200">{p.name || p.product_name || p.product_code}</p>
                <p className="text-xs text-slate-500">{p.description || p.line_of_business || ''}</p>
                <p className="mt-1 text-xs text-slate-400">Min: {fmtCurrency(p.min_premium)} &middot; Max: {fmtCurrency(p.max_premium)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {calibration && (
        <div className="glass-card p-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400"><Target className="mr-2 inline h-4 w-4" /> Calibration</h3>
            <button onClick={() => setCalibration(null)} className="text-xs text-slate-500 hover:text-slate-300">Close</button>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {Object.entries(calibration).filter(([k]) => k !== 'bundle_id' && k !== 'org_id').map(([key, val]) => (
              <div key={key} className="rounded-lg bg-surface-overlay p-3 ring-1 ring-white/[0.04]">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{key.replace(/_/g, ' ')}</p>
                <p className="mt-1 text-sm font-medium text-slate-300">{typeof val === 'number' ? val.toFixed(4) : String(val)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {lossData && (
        <div className="glass-card p-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400"><TrendingDown className="mr-2 inline h-4 w-4" /> Loss Experience</h3>
            <button onClick={() => setLossData(null)} className="text-xs text-slate-500 hover:text-slate-300">Close</button>
          </div>
          <pre className="max-h-60 overflow-y-auto text-xs text-slate-400">{JSON.stringify(lossData, null, 2)}</pre>
        </div>
      )}

      {(presets?.insurance || []).length > 0 && (
        <div className="space-y-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">One-click samples</p>
          <div className="flex flex-col gap-2">
            {(presets?.insurance || []).map((d) => (
              <button
                key={d.id}
                type="button"
                onClick={() => onRunDemo('insurance', d.id)}
                className="flex items-center justify-between rounded-xl border border-white/[0.06] bg-surface-overlay/30 px-4 py-3 text-left transition hover:border-brand/30 hover:bg-white/[0.02]"
              >
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
        </div>
        {!jobs?.length ? (
          <EmptyState icon={Shield} title="No insurance jobs" description="Upload a broker package or run the Pacific Coast demo" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06] bg-surface-overlay text-left text-xs uppercase tracking-wider text-slate-500">
                  <th className="px-6 py-3">Job ID</th>
                  <th className="px-6 py-3">Insured</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Decision</th>
                  <th className="px-6 py-3">Premium</th>
                  <th className="px-6 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {[...jobs].reverse().map(({ id, job }) => {
                  const s = extractInsurance(job);
                  const r = job?.results || {};
                  const triageScore = r.triage_score;
                  return (
                    <tr key={id} onClick={() => onOpenJob('insurance', id)} className="cursor-pointer transition hover:bg-white/[0.02]">
                      <td className="px-6 py-3.5 font-mono text-xs text-slate-400">{id}</td>
                      <td className="px-6 py-3.5 text-slate-300">
                        {s.insuredName || '—'}
                        {triageScore != null && <span className="ml-2 text-xs text-slate-500">({triageScore})</span>}
                      </td>
                      <td className="px-6 py-3.5"><Badge status={job?.status} pulse={job?.status === 'processing'} /></td>
                      <td className="px-6 py-3.5"><DecisionBadge decision={s.decision} jobStatus={job?.status} /></td>
                      <td className="px-6 py-3.5 font-medium">{fmtCurrency(s.premium)}</td>
                      <td className="px-6 py-3.5">
                        <div className="flex gap-1" onClick={e => e.stopPropagation()}>
                          {s.bundleId && (
                            <>
                              <button onClick={() => loadCope(s.bundleId)} className="rounded-lg bg-black/30 px-2 py-1 text-xs text-slate-400 hover:text-slate-200" title="COPE Risk Analysis">COPE</button>
                              <button onClick={() => loadMissingDocs(s.bundleId)} className="rounded-lg bg-black/30 px-2 py-1 text-xs text-slate-400 hover:text-slate-200" title="Missing Documents">Docs</button>
                              <button onClick={() => loadLossExp(s.bundleId)} className="rounded-lg bg-black/30 px-2 py-1 text-xs text-slate-400 hover:text-slate-200" title="Loss Experience">Loss</button>
                              <button onClick={async () => { try { const r = await endpoints.createBrokerShare(s.bundleId); navigator.clipboard?.writeText(`${window.location.origin}/dashboard/broker/status/${r.token}`); alert('Share link copied!'); } catch (e) { alert(e.message); } }} className="rounded-lg bg-black/30 px-2 py-1 text-xs text-slate-400 hover:text-slate-200" title="Create broker share link"><Link className="h-3 w-3 inline" /> Share</button>
                            </>
                          )}
                        </div>
                      </td>
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
