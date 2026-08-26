import { useState } from 'react';
import { fmtCurrency } from '../lib/api';

export default function PremiumCalculator({ data }) {
  const [faceAmount, setFaceAmount] = useState(500000);
  const [age, setAge] = useState(40);
  const [tobacco, setTobacco] = useState('nontobacco');
  const [uwClass, setUwClass] = useState('standard');

  const result = data?.premium_calc;
  const mortality = data?.actuarial?.mortality_cost;

  const baseRate = mortality?.mortality_rate_per_1000 || 0.726;
  const classMultipliers = {
    super_preferred: 0.60,
    preferred: 0.75,
    standard_plus: 0.88,
    standard: 1.0,
    table_a: 1.25,
    table_b: 1.50,
    table_c: 1.80,
    substandard: 2.20,
  };
  const mult = classMultipliers[uwClass] || 1.0;
  const adjustedRate = baseRate * mult;
  const annualPremium = (faceAmount * adjustedRate) / 1000;
  const monthlyPremium = annualPremium / 12;

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wide">Premium Calculator</h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <label className="block text-xs text-slate-400">
          Face Amount
          <input type="number" value={faceAmount} onChange={e => setFaceAmount(Number(e.target.value))}
            className="mt-1 w-full rounded border border-slate-700 bg-slate-800 px-2 py-1.5 text-sm text-white" />
        </label>
        <label className="block text-xs text-slate-400">
          Age
          <input type="number" value={age} onChange={e => setAge(Number(e.target.value))}
            className="mt-1 w-full rounded border border-slate-700 bg-slate-800 px-2 py-1.5 text-sm text-white" />
        </label>
        <label className="block text-xs text-slate-400">
          Tobacco
          <select value={tobacco} onChange={e => setTobacco(e.target.value)}
            className="mt-1 w-full rounded border border-slate-700 bg-slate-800 px-2 py-1.5 text-sm text-white">
            <option value="nontobacco">Non-Tobacco</option>
            <option value="tobacco">Tobacco</option>
          </select>
        </label>
        <label className="block text-xs text-slate-400">
          UW Class
          <select value={uwClass} onChange={e => setUwClass(e.target.value)}
            className="mt-1 w-full rounded border border-slate-700 bg-slate-800 px-2 py-1.5 text-sm text-white">
            {Object.keys(classMultipliers).map(c => (
              <option key={c} value={c}>{c.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</option>
            ))}
          </select>
        </label>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <ResultCard label="Base Rate" value={`$${baseRate.toFixed(3)}/1000`} />
        <ResultCard label="Adjusted Rate" value={`$${adjustedRate.toFixed(3)}/1000`} highlight />
        <ResultCard label="Annual Premium" value={fmtCurrency(annualPremium)} highlight />
        <ResultCard label="Monthly Premium" value={fmtCurrency(monthlyPremium)} />
      </div>

      <div className="rounded border border-slate-800 bg-slate-900/50 p-3">
        <p className="text-xs text-slate-400 mb-1">Class Multiplier: {mult.toFixed(2)}x ({uwClass.replace(/_/g, ' ')})</p>
        <p className="text-xs text-slate-400">
          Rate = {baseRate.toFixed(3)} × {mult.toFixed(2)} = {adjustedRate.toFixed(3)} per $1,000
        </p>
        <p className="text-xs text-slate-400">
          Premium = ${faceAmount.toLocaleString()} × ${adjustedRate.toFixed(3)} / 1,000 = {fmtCurrency(annualPremium)}/yr
        </p>
      </div>

      {result && (
        <div className="rounded border border-slate-800 bg-slate-900/50 p-3">
          <p className="text-xs text-slate-400 mb-2">Backend Premium Build-up</p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
            {result.base_premium != null && <div><span className="text-slate-400">Base: </span><span className="text-white">{fmtCurrency(result.base_premium)}</span></div>}
            {result.adjusted_premium != null && <div><span className="text-slate-400">Adjusted: </span><span className="text-white">{fmtCurrency(result.adjusted_premium)}</span></div>}
            {result.rider_load != null && <div><span className="text-slate-400">Rider Load: </span><span className="text-white">{fmtCurrency(result.rider_load)}</span></div>}
            {result.flat_extra != null && <div><span className="text-slate-400">Flat Extra: </span><span className="text-white">{fmtCurrency(result.flat_extra)}</span></div>}
            {result.total_premium != null && <div><span className="text-slate-400">Total: </span><span className="text-white font-medium">{fmtCurrency(result.total_premium)}</span></div>}
          </div>
        </div>
      )}
    </div>
  );
}

function ResultCard({ label, value, highlight }) {
  return (
    <div className={`rounded border px-3 py-2 ${highlight ? 'border-blue-700/50 bg-blue-900/20' : 'border-slate-800 bg-slate-900/50'}`}>
      <p className="text-xs text-slate-400">{label}</p>
      <p className={`text-sm font-medium ${highlight ? 'text-blue-300' : 'text-white'}`}>{value}</p>
    </div>
  );
}
