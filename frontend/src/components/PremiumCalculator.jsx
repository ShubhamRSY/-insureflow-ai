import { useState } from 'react';
import { fmtCurrency } from '../lib/api';
import { Hint, RatePanel, RateField } from './ui';

const HINTS = {
  face: 'Death benefit / face amount the premium is calculated on.',
  age: 'Attained age — for reference alongside the mortality rate pulled from the Actuarial Lookup above. Not used directly in this calculator\'s formula.',
  tobacco: 'Tobacco class — for reference. The base rate already reflects whatever class was used in the Actuarial Lookup above.',
  uwClass: 'Underwriting class multiplier applied on top of the base mortality rate. Better classes (super preferred, preferred) pay less than standard; substandard/table ratings pay more for added risk.',
  baseRate: 'Raw mortality rate per $1,000 of face, pulled from the Actuarial Mortality Lookup above (or a $0.726 default if no lookup has been run yet).',
  adjustedRate: 'Base rate × underwriting class multiplier — the rate actually charged per $1,000 of face.',
  annualPremium: 'Adjusted rate × face amount / 1,000 — the full-year cost of insurance before riders, flat extras, or policy fees.',
  monthlyPremium: 'Annual premium ÷ 12, for reference only — does not include any modal (monthly payment) loading a real billing schedule would apply.',
  backend: 'The premium build-up actually produced by the rating engine for this case, as opposed to the exploratory numbers above.',
};

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
      <p className="text-xs text-slate-500">
        Quick what-if premium estimate from a face amount, mortality rate, and UW class. Exploratory only — does not change the filed quote.
      </p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <RateField label="Face Amount" hint={HINTS.face}>
          <input type="number" value={faceAmount} onChange={e => setFaceAmount(Number(e.target.value))} className="input" />
        </RateField>
        <RateField label="Age" hint={HINTS.age}>
          <input type="number" value={age} onChange={e => setAge(Number(e.target.value))} className="input" />
        </RateField>
        <RateField label="Tobacco" hint={HINTS.tobacco}>
          <select value={tobacco} onChange={e => setTobacco(e.target.value)} className="input">
            <option value="nontobacco">Non-Tobacco</option>
            <option value="tobacco">Tobacco</option>
          </select>
        </RateField>
        <RateField label="UW Class" hint={HINTS.uwClass}>
          <select value={uwClass} onChange={e => setUwClass(e.target.value)} className="input">
            {Object.keys(classMultipliers).map(c => (
              <option key={c} value={c}>{c.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</option>
            ))}
          </select>
        </RateField>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <ResultCard label="Base Rate" value={`$${baseRate.toFixed(3)}/1000`} hint={HINTS.baseRate} />
        <ResultCard label="Adjusted Rate" value={`$${adjustedRate.toFixed(3)}/1000`} hint={HINTS.adjustedRate} highlight />
        <ResultCard label="Annual Premium" value={fmtCurrency(annualPremium)} hint={HINTS.annualPremium} highlight />
        <ResultCard label="Monthly Premium" value={fmtCurrency(monthlyPremium)} hint={HINTS.monthlyPremium} />
      </div>

      <RatePanel>
        <p className="mb-1 text-xs text-slate-500">Class Multiplier: {mult.toFixed(2)}x ({uwClass.replace(/_/g, ' ')})</p>
        <p className="text-xs text-slate-500">
          Rate = {baseRate.toFixed(3)} × {mult.toFixed(2)} = {adjustedRate.toFixed(3)} per $1,000
        </p>
        <p className="text-xs text-slate-500">
          Premium = ${faceAmount.toLocaleString()} × ${adjustedRate.toFixed(3)} / 1,000 = {fmtCurrency(annualPremium)}/yr
        </p>
      </RatePanel>

      {result && (
        <RatePanel>
          <Hint text={HINTS.backend}>
            <p className="hint-label mb-2 inline-block cursor-help text-xs text-slate-500">Backend Premium Build-up</p>
          </Hint>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
            {result.base_premium != null && <div><span className="text-slate-500">Base: </span><span className="text-slate-100">{fmtCurrency(result.base_premium)}</span></div>}
            {result.adjusted_premium != null && <div><span className="text-slate-500">Adjusted: </span><span className="text-slate-100">{fmtCurrency(result.adjusted_premium)}</span></div>}
            {result.rider_load != null && <div><span className="text-slate-500">Rider Load: </span><span className="text-slate-100">{fmtCurrency(result.rider_load)}</span></div>}
            {result.flat_extra != null && <div><span className="text-slate-500">Flat Extra: </span><span className="text-slate-100">{fmtCurrency(result.flat_extra)}</span></div>}
            {result.total_premium != null && <div><span className="text-slate-500">Total: </span><span className="font-medium text-slate-100">{fmtCurrency(result.total_premium)}</span></div>}
          </div>
        </RatePanel>
      )}
    </div>
  );
}

function ResultCard({ label, value, hint, highlight }) {
  return (
    <div className={`rounded-lg border px-3 py-2 ${highlight ? 'border-brand/40 bg-brand/10' : 'border-white/10 bg-surface-overlay/50'}`}>
      <Hint text={hint}>
        <p className={`text-xs text-slate-500 ${hint ? 'hint-label cursor-help' : ''}`}>{label}</p>
      </Hint>
      <p className={`text-sm font-medium ${highlight ? 'text-brand-light' : 'text-slate-100'}`}>{value}</p>
    </div>
  );
}
