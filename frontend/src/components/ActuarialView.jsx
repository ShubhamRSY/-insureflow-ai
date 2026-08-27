import { useState } from 'react';
import { fmtCurrency } from '../lib/api';
import { Hint, RatePanel, RateStat, RateField } from './ui';

const TABLES = [
  { value: 'cso_2017', label: 'CSO 2017' },
  { value: 'atb_99', label: 'ATB 99' },
  { value: 'cso_2001', label: 'CSO 2001' },
  { value: 'cso_1980', label: 'CSO 1980' },
];
const TOBACCO_OPTIONS = [
  { value: 'nontobacco', label: 'Non-Tobacco' },
  { value: 'preferred_nontobacco', label: 'Preferred Non-Tobacco' },
  { value: 'tobacco', label: 'Tobacco' },
];

const HINTS = {
  age: 'Attained age used to look up the mortality rate for this life. Changing it re-runs the lookup instantly — it does not affect the filed quote.',
  face: 'Death benefit / face amount the mortality cost is calculated against.',
  tobacco: 'Tobacco class affects the mortality rate materially — tobacco users are charged a materially higher rate than non-tobacco.',
  gender: 'Sex is a rated factor in mortality tables — female mortality is generally lower than male at the same age.',
  table: 'The mortality table / basis this lookup is priced from. Carriers file specific tables per product and state — confirm this matches the rate filing before relying on the result.',
  mortalityRate: 'Expected deaths per 1,000 lives at this age, sex, tobacco class, and table — the raw input to the mortality cost calculation.',
  annualCost: 'Mortality rate × face amount / 1,000 — the pure cost of insurance for one year, before UW class, fees, or policy loads.',
  monthlyCost: 'Annual mortality cost divided by 12 — for reference only, does not reflect any modal (payment frequency) loading the filed rate may apply.',
  costPerDollar: 'Mortality cost expressed per $1 of face amount — useful for comparing risk across different face amounts.',
  comparison: 'The same age/sex/tobacco inputs re-priced against every mortality table on file, so you can see how much the table selection itself moves the cost.',
  spread: 'Percentage difference between the cheapest and most expensive table shown below — a wide spread means table selection materially changes the price.',
};

export default function ActuarialView({ data }) {
  // Seed inputs from this case's own extracted data instead of an unrelated
  // generic default — the underwriter can still override any field to run
  // a what-if from that real baseline.
  const meta = data?.quote_full?.metadata || {};
  const caseFactors = meta.personal_factors || {};
  const caseMedical = meta.medical || {};
  const [age, setAge] = useState(() => caseFactors.age || 40);
  const [face, setFace] = useState(() => meta.face_amount || meta.tiv || 500000);
  const [tobacco, setTobacco] = useState(() => (caseMedical.tobacco ? 'tobacco' : 'nontobacco'));
  const [gender, setGender] = useState(() => (caseFactors.sex === 'female' ? 'female' : 'male'));
  const [table, setTable] = useState('cso_2017');

  const result = data?.actuarial;
  const cost = result?.mortality_cost;
  const comparison = result?.comparison;

  return (
    <div className="space-y-4">
      <p className="text-xs text-slate-500">
        Reprice this life against any mortality table to sanity-check the filed rate. Inputs here are exploratory only — they don't change the quote.
      </p>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <RateField label="Age" hint={HINTS.age}>
          <input type="number" value={age} onChange={e => setAge(Number(e.target.value))} className="input" />
        </RateField>
        <RateField label="Face Amount" hint={HINTS.face}>
          <input type="number" value={face} onChange={e => setFace(Number(e.target.value))} className="input" />
        </RateField>
        <RateField label="Tobacco" hint={HINTS.tobacco}>
          <select value={tobacco} onChange={e => setTobacco(e.target.value)} className="input">
            {TOBACCO_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </RateField>
        <RateField label="Gender" hint={HINTS.gender}>
          <select value={gender} onChange={e => setGender(e.target.value)} className="input">
            <option value="male">Male</option>
            <option value="female">Female</option>
          </select>
        </RateField>
        <RateField label="Table" hint={HINTS.table}>
          <select value={table} onChange={e => setTable(e.target.value)} className="input">
            {TABLES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </RateField>
      </div>

      {cost && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Stat label="Mortality Rate" value={`${cost.mortality_rate_per_1000}/1000`} hint={HINTS.mortalityRate} />
          <Stat label="Annual Cost" value={fmtCurrency(cost.expected_annual_cost)} hint={HINTS.annualCost} />
          <Stat label="Monthly Cost" value={fmtCurrency(cost.expected_monthly_cost)} hint={HINTS.monthlyCost} />
          <Stat label="Cost per $1" value={`$${cost.cost_per_dollar.toFixed(6)}`} hint={HINTS.costPerDollar} />
        </div>
      )}

      {comparison && (
        <div className="mt-3">
          <Hint text={HINTS.comparison}>
            <p className="hint-label mb-2 inline-block cursor-help text-xs text-slate-500">Cross-Table Comparison</p>
          </Hint>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="text-xs text-slate-500">
                <th className="py-1 text-left">Table</th>
                <th className="py-1 text-right">Rate/1000</th>
                <th className="py-1 text-right">Annual Cost</th>
              </tr></thead>
              <tbody>
                {Object.entries(comparison.rates_per_1000 || {}).map(([t, rate]) => (
                  <tr key={t} className="border-t border-white/[0.06]">
                    <td className="py-1 text-slate-300">{t}</td>
                    <td className="py-1 text-right text-slate-300">{rate?.toFixed(3)}</td>
                    <td className="py-1 text-right text-slate-300">{fmtCurrency(comparison.annual_costs?.[t])}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Hint text={HINTS.spread}>
            <p className="hint-label mt-1 inline-block cursor-help text-xs text-slate-500">Spread: {comparison.spread_pct?.toFixed(1)}%</p>
          </Hint>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, hint }) {
  return (
    <RatePanel>
      <Hint text={hint}>
        <p className={`text-xs text-slate-500 ${hint ? 'hint-label cursor-help' : ''}`}>{label}</p>
      </Hint>
      <p className="text-sm font-medium text-slate-100">{value}</p>
    </RatePanel>
  );
}
