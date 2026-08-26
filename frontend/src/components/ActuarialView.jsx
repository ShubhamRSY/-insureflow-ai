import { useState } from 'react';
import { fmtCurrency } from '../lib/api';

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

export default function ActuarialView({ data }) {
  const [age, setAge] = useState(40);
  const [face, setFace] = useState(500000);
  const [tobacco, setTobacco] = useState('nontobacco');
  const [gender, setGender] = useState('male');
  const [table, setTable] = useState('cso_2017');

  const result = data?.actuarial;
  const cost = result?.mortality_cost;
  const comparison = result?.comparison;

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wide">Actuarial Mortality Lookup</h3>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <label className="block text-xs text-slate-400">
          Age
          <input type="number" value={age} onChange={e => setAge(Number(e.target.value))}
            className="mt-1 w-full rounded border border-slate-700 bg-slate-800 px-2 py-1.5 text-sm text-white" />
        </label>
        <label className="block text-xs text-slate-400">
          Face Amount
          <input type="number" value={face} onChange={e => setFace(Number(e.target.value))}
            className="mt-1 w-full rounded border border-slate-700 bg-slate-800 px-2 py-1.5 text-sm text-white" />
        </label>
        <label className="block text-xs text-slate-400">
          Tobacco
          <select value={tobacco} onChange={e => setTobacco(e.target.value)}
            className="mt-1 w-full rounded border border-slate-700 bg-slate-800 px-2 py-1.5 text-sm text-white">
            {TOBACCO_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </label>
        <label className="block text-xs text-slate-400">
          Gender
          <select value={gender} onChange={e => setGender(e.target.value)}
            className="mt-1 w-full rounded border border-slate-700 bg-slate-800 px-2 py-1.5 text-sm text-white">
            <option value="male">Male</option>
            <option value="female">Female</option>
          </select>
        </label>
        <label className="block text-xs text-slate-400">
          Table
          <select value={table} onChange={e => setTable(e.target.value)}
            className="mt-1 w-full rounded border border-slate-700 bg-slate-800 px-2 py-1.5 text-sm text-white">
            {TABLES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </label>
      </div>

      {cost && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Stat label="Mortality Rate" value={`${cost.mortality_rate_per_1000}/1000`} />
          <Stat label="Annual Cost" value={fmtCurrency(cost.expected_annual_cost)} />
          <Stat label="Monthly Cost" value={fmtCurrency(cost.expected_monthly_cost)} />
          <Stat label="Cost per $1" value={`$${cost.cost_per_dollar.toFixed(6)}`} />
        </div>
      )}

      {comparison && (
        <div className="mt-3">
          <p className="text-xs text-slate-400 mb-2">Cross-Table Comparison</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="text-slate-400 text-xs">
                <th className="text-left py-1">Table</th>
                <th className="text-right py-1">Rate/1000</th>
                <th className="text-right py-1">Annual Cost</th>
              </tr></thead>
              <tbody>
                {Object.entries(comparison.rates_per_1000 || {}).map(([t, rate]) => (
                  <tr key={t} className="border-t border-slate-800">
                    <td className="py-1 text-slate-300">{t}</td>
                    <td className="py-1 text-right text-slate-300">{rate?.toFixed(3)}</td>
                    <td className="py-1 text-right text-slate-300">{fmtCurrency(comparison.annual_costs?.[t])}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-slate-500 mt-1">Spread: {comparison.spread_pct?.toFixed(1)}%</p>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="rounded border border-slate-800 bg-slate-900/50 px-3 py-2">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="text-sm font-medium text-white">{value}</p>
    </div>
  );
}
