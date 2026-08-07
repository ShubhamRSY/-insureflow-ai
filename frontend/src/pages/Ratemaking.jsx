import { useState, useEffect, useCallback } from 'react';
import { Calculator, RefreshCw, Layers, Scale, TrendingUp, Gavel, Landmark, Clock, AlertTriangle } from 'lucide-react';
import { StatCard, EmptyState, Badge } from '../components/ui';
import { endpoints, fmtCurrency } from '../lib/api';

const LINES = [
  'commercial_property', 'general_liability', 'workers_comp', 'business_owners_policy',
  'umbrella', 'personal_homeowners', 'personal_auto', 'life',
];

const METHODS = [
  { id: 'pure_premium', label: 'Pure premium', icon: Layers, color: 'text-brand' },
  { id: 'loss_ratio', label: 'Loss ratio', icon: TrendingUp, color: 'text-sky-400' },
  { id: 'judgment', label: 'Judgment', icon: Gavel, color: 'text-violet-400' },
];

export default function RatemakingPage() {
  const [line, setLine] = useState('commercial_property');
  const [study, setStudy] = useState(null);
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    incurred_losses: '10000000', exposure_units: '100000',
    lae: '1000000', acquisition: '1500000', general_admin: '800000', premium_taxes: '200000',
    contingency_pct: '5', profit_pct: '5', actual_loss_ratio: '0.60', permissible_loss_ratio: '0.65',
  });

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [o, s] = await Promise.all([endpoints.ratemaking(), endpoints.ratemakingRun({ line })]);
      setOverview(o);
      setStudy(s);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [line]);

  useEffect(() => { load(); }, [load]);

  const runForm = async () => {
    setError('');
    try {
      const nums = (k) => Number(form[k] || 0);
      const s = await endpoints.ratemakingRun({
        line,
        incurred_losses: nums('incurred_losses'),
        exposure_units: nums('exposure_units'),
        lae: nums('lae'), acquisition: nums('acquisition'),
        general_admin: nums('general_admin'), premium_taxes: nums('premium_taxes'),
        contingency_pct: nums('contingency_pct'), profit_pct: nums('profit_pct'),
        actual_loss_ratio: Number(form.actual_loss_ratio || 0.6),
        permissible_loss_ratio: Number(form.permissible_loss_ratio || 0.65),
      });
      setStudy(s);
    } catch (e) {
      setError(e.message);
    }
  };

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const pure = study?.pure_premium_result || {};

  return (
    <div className="mx-auto max-w-6xl space-y-8 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand/15">
            <Calculator className="h-6 w-6 text-brand" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Ratemaking &amp; Pricing</h1>
            <p className="mt-1 text-slate-400">Base-rate build-up, the three ratemaking methods, and statutory rate goals</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <select value={line} onChange={(e) => setLine(e.target.value)} className="input text-sm">
            {LINES.map((l) => <option key={l} value={l}>{l}</option>)}
          </select>
          <button type="button" onClick={load} className="btn-secondary btn-sm text-xs">
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>
      </div>

      {error && <div className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
        </div>
      ) : !study ? (
        <EmptyState icon={Calculator} title="No ratemaking data" description="Ratemaking output will appear once the study is generated" />
      ) : (
        <>
          {study.summary && (
            <div className="rounded-xl bg-brand/10 px-4 py-3 text-sm text-brand">{study.summary}</div>
          )}

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Pure Premium" value={fmtCurrency(pure.pure_premium)} sub="per exposure unit" accent="brand" />
            <StatCard label="Expense Loading" value={fmtCurrency(pure.expense_loading)} sub="acquisition · admin · taxes" accent="insurance" />
            <StatCard label="Base Rate" value={fmtCurrency(pure.base_rate)} sub="pure premium + expenses" accent="success" />
            <StatCard label="Gross Rate" value={fmtCurrency(pure.gross_rate)} sub={`+${pure.contingency_loading ?? 0} contingency +${pure.profit_loading ?? 0} profit`} accent="mortgage" />
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <div className="glass-card p-5">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
                <Layers className="h-4 w-4" /> The three methods
              </h3>
              <div className="space-y-3">
                {METHODS.map((m) => {
                  const Icon = m.icon;
                  const lr = study.loss_ratio_result || {};
                  const j = study.judgment_result || {};
                  const value = m.id === 'pure_premium' ? pure.base_rate : m.id === 'loss_ratio' ? lr.indicated_rate : j.judgment_rate;
                  const sub = m.id === 'loss_ratio' ? `${lr.rate_change_pct ?? 0 > 0 ? '+' : ''}${lr.rate_change_pct ?? 0}% change` : `${m.id} method`;
                  return (
                    <div key={m.id} className="flex items-center justify-between rounded-lg bg-surface-overlay px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Icon className={`h-4 w-4 ${m.color}`} />
                        <span className="text-sm text-slate-300">{m.label}</span>
                      </div>
                      <div className="text-right">
                        <span className="text-sm font-semibold text-white">{fmtCurrency(value)}</span>
                        <p className="text-xs text-slate-400">{sub}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="glass-card p-5">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
                <Scale className="h-4 w-4" /> Regulatory goals
              </h3>
              <div className="space-y-2">
                {(study.regulatory || []).map((r, i) => (
                  <div key={i} className="flex items-center justify-between gap-3 rounded-lg bg-surface-overlay px-4 py-2">
                    <div>
                      <p className="text-sm capitalize text-slate-200">{r.goal.replace(/_/g, ' ')}</p>
                      <p className="text-xs text-slate-400">{r.detail}</p>
                    </div>
                    <Badge status={r.status} />
                  </div>
                ))}
              </div>
            </div>

            <div className="glass-card p-5">
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">Rate characteristics</h3>
              <div className="space-y-2">
                {(study.characteristics || []).map((c, i) => (
                  <div key={i} className="flex items-center justify-between gap-3 rounded-lg bg-surface-overlay px-4 py-2">
                    <p className="text-sm capitalize text-slate-200">{c.characteristic.replace(/_/g, ' ')}</p>
                    <Badge status={c.status} />
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="glass-card p-5">
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">Build a rate (three-step process)</h3>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                <label className="text-xs text-slate-400">Incurred losses $
                  <input className="input mt-1" value={form.incurred_losses} onChange={set('incurred_losses')} />
                </label>
                <label className="text-xs text-slate-400">Exposure units
                  <input className="input mt-1" value={form.exposure_units} onChange={set('exposure_units')} />
                </label>
                <label className="text-xs text-slate-400">LAE $
                  <input className="input mt-1" value={form.lae} onChange={set('lae')} />
                </label>
                <label className="text-xs text-slate-400">Acquisition $
                  <input className="input mt-1" value={form.acquisition} onChange={set('acquisition')} />
                </label>
                <label className="text-xs text-slate-400">General admin $
                  <input className="input mt-1" value={form.general_admin} onChange={set('general_admin')} />
                </label>
                <label className="text-xs text-slate-400">Premium taxes $
                  <input className="input mt-1" value={form.premium_taxes} onChange={set('premium_taxes')} />
                </label>
                <label className="text-xs text-slate-400">Contingency %
                  <input className="input mt-1" value={form.contingency_pct} onChange={set('contingency_pct')} />
                </label>
                <label className="text-xs text-slate-400">Profit %
                  <input className="input mt-1" value={form.profit_pct} onChange={set('profit_pct')} />
                </label>
                <label className="text-xs text-slate-400">Actual loss ratio
                  <input className="input mt-1" value={form.actual_loss_ratio} onChange={set('actual_loss_ratio')} />
                </label>
                <label className="text-xs text-slate-400">Permissible loss ratio
                  <input className="input mt-1" value={form.permissible_loss_ratio} onChange={set('permissible_loss_ratio')} />
                </label>
              </div>
              <button type="button" onClick={runForm} className="btn-primary mt-4">
                <Calculator className="h-4 w-4" /> Recalculate rate
              </button>
            </div>

            <div className="glass-card p-5">
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">Per-line base rates</h3>
              <div className="max-h-80 space-y-2 overflow-y-auto">
                {(overview?.line_build_ups || []).map((b, i) => (
                  <div key={i} className="flex items-center justify-between rounded-lg bg-surface-overlay px-4 py-2">
                    <span className="text-sm text-slate-300">{b.line}</span>
                    <span className="text-xs text-slate-400">
                      pure {fmtCurrency(b.pure_premium)} · base {fmtCurrency(b.base_rate)} · gross {fmtCurrency(b.gross_rate)}
                    </span>
                  </div>
                ))}
              </div>
              <h3 className="mb-2 mt-5 text-sm font-semibold uppercase tracking-wider text-slate-400">Advisory organizations</h3>
              <div className="flex flex-wrap gap-2">
                {(overview?.advisory_organizations || []).map((org) => (
                  <span key={org} className="rounded-full bg-surface-overlay px-3 py-1 text-xs text-slate-300 ring-1 ring-inset ring-slate-500/20">{org}</span>
                ))}
              </div>
            </div>
          </div>

          <div className="glass-card p-5">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <h3 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
                <Landmark className="h-4 w-4" /> Loss reserve estimation
              </h3>
              <div className="flex flex-wrap gap-2">
                <span className="rounded-full bg-surface-overlay px-3 py-1 text-xs text-slate-300 ring-1 ring-inset ring-slate-500/20">
                  redundancy {overview?.reserve_analysis?.payout_pattern?.reserve_redundancy_pct ?? 0}%
                </span>
                <span className="rounded-full bg-surface-overlay px-3 py-1 text-xs text-slate-300 ring-1 ring-inset ring-slate-500/20">
                  rate lag ~{overview?.reserve_analysis?.filing_schedule?.total_lag_years ?? 0} yrs
                </span>
              </div>
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <div>
                <h4 className="mb-2 text-xs uppercase tracking-wider text-slate-400">Accident-year development (paid · reported · IBNR)</h4>
                <div className="overflow-x-auto rounded-lg ring-1 ring-inset ring-slate-500/20">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-surface-overlay text-left text-slate-400">
                        <th className="px-3 py-2 font-medium">Valuation</th>
                        <th className="px-3 py-2 text-right font-medium">Paid to date</th>
                        <th className="px-3 py-2 text-right font-medium">Reported unpaid</th>
                        <th className="px-3 py-2 text-right font-medium">IBNR</th>
                        <th className="px-3 py-2 text-right font-medium">Incurred est.</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(overview?.reserve_analysis?.payout_pattern?.valuations || []).map((v) => (
                        <tr key={v.valuation_year} className="border-t border-slate-500/10 text-slate-200">
                          <td className="px-3 py-1.5 text-slate-400">Year {v.valuation_year}</td>
                          <td className="px-3 py-1.5 text-right tabular-nums">{fmtCurrency(v.paid_to_date)}</td>
                          <td className="px-3 py-1.5 text-right tabular-nums">{fmtCurrency(v.reported_but_unpaid)}</td>
                          <td className="px-3 py-1.5 text-right tabular-nums">{fmtCurrency(v.ibnr)}</td>
                          <td className="px-3 py-1.5 text-right font-semibold tabular-nums">{fmtCurrency(v.incurred_estimate)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {(overview?.reserve_analysis?.payout_pattern?.reserve_redundancy_pct ?? 0) > 0 && (
                  <div className="mt-3 flex items-start gap-2 rounded-lg bg-amber-500/10 px-3 py-2 text-xs text-amber-300">
                    <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                    <span>
                      Estimated incurred at first valuation exceeded the matured estimate by ~
                      {overview.reserve_analysis.payout_pattern.reserve_redundancy_pct}% — rates based on the early
                      estimate would have been too high by about the same amount.
                    </span>
                  </div>
                )}
              </div>

              <div>
                <h4 className="mb-2 flex items-center gap-1 text-xs uppercase tracking-wider text-slate-400">
                  <Clock className="h-3.5 w-3.5" /> Rate filing schedule
                </h4>
                <ol className="relative ml-2 space-y-2 border-l border-slate-500/20 pl-4">
                  {(overview?.reserve_analysis?.filing_schedule?.stages || []).map((s, i) => (
                    <li key={i} className="relative">
                      <span className="absolute -left-[21px] top-1 h-2 w-2 rounded-full bg-brand/60" />
                      <p className="text-xs font-medium text-slate-200">{s.stage}</p>
                      <p className="text-[11px] text-slate-400">{s.date} — {s.description}</p>
                    </li>
                  ))}
                </ol>
                <h4 className="mb-2 mt-5 text-xs uppercase tracking-wider text-slate-400">Delays reducing rate responsiveness</h4>
                <ul className="space-y-1.5">
                  {(overview?.reserve_analysis?.data_delays || []).map((d, i) => (
                    <li key={i} className="flex items-start justify-between gap-3 rounded-lg bg-surface-overlay px-3 py-2 text-xs">
                      <div>
                        <p className="text-slate-200">{d.source}</p>
                        <p className="text-slate-400">{d.detail}</p>
                      </div>
                      <Badge status={d.severity === 'high' ? 'fail' : d.severity === 'moderate' ? 'flag' : 'pass'} />
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
