import { useEffect, useState } from 'react';
import { CheckCircle2, Loader2, PenLine } from 'lucide-react';
import { endpoints } from '../lib/api';
import { Hint } from './ui';
import { UI_HINTS } from '../lib/uiHints';

/** Licensed UW edits and validates premium / limit / deductible. */
export default function UwPolicyValidator({ bundleId, worksheet, validatedTerms, onValidated }) {
  const terms = worksheet?.indicated_terms || {};
  const [premium, setPremium] = useState('');
  const [limit, setLimit] = useState('');
  const [deductible, setDeductible] = useState('');
  const [notes, setNotes] = useState('');
  const [license, setLicense] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(validatedTerms?.validated_at || null);

  useEffect(() => {
    const v = validatedTerms || {};
    setPremium(String(v.indicated_premium ?? terms.premium ?? ''));
    setLimit(String(v.limit ?? terms.limit ?? ''));
    setDeductible(String(v.deductible ?? terms.deductible ?? ''));
    setSaved(v.validated_at || null);
  }, [worksheet, validatedTerms, terms.premium, terms.limit, terms.deductible]);

  if (!bundleId || !worksheet) return null;

  const handleValidate = async () => {
    setError('');
    setBusy(true);
    try {
      const res = await endpoints.validateUwTerms(bundleId, {
        indicated_premium: parseFloat(premium) || 0,
        limit: parseFloat(limit) || 0,
        deductible: parseFloat(deductible) || 0,
        notes,
        license_number: license,
      });
      setSaved(res.validated_terms?.validated_at || new Date().toISOString());
      onValidated?.(res.validated_terms);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-xl border border-brand/20 bg-brand/5 p-5">
      <div className="mb-3 flex items-center gap-2">
        <PenLine className="h-4 w-4 text-brand" />
        <p className="text-xs font-semibold uppercase tracking-wider text-brand-light">UW validator</p>
        {saved && (
          <span className="ml-auto inline-flex items-center gap-1 text-[10px] text-emerald-400">
            <CheckCircle2 className="h-3 w-3" /> Terms saved
          </span>
        )}
      </div>
      <p className="mb-4 text-[11px] text-slate-400">
        Review AI-indicated terms, edit as needed, and validate before sign-off. You remain the decision-maker.
      </p>
      <div className="grid gap-3 sm:grid-cols-3">
        <label className="block">
          <Hint text={UI_HINTS.uwValidatePremium}>
            <span className="hint-label mb-1 block cursor-help text-[10px] uppercase text-slate-500">Premium ($)</span>
          </Hint>
          <input type="number" className="input-field w-full text-sm" value={premium} onChange={(e) => setPremium(e.target.value)} />
        </label>
        <label className="block">
          <Hint text={UI_HINTS.uwValidateLimit}>
            <span className="hint-label mb-1 block cursor-help text-[10px] uppercase text-slate-500">Limit ($)</span>
          </Hint>
          <input type="number" className="input-field w-full text-sm" value={limit} onChange={(e) => setLimit(e.target.value)} />
        </label>
        <label className="block">
          <Hint text={UI_HINTS.uwValidateDeductible}>
            <span className="hint-label mb-1 block cursor-help text-[10px] uppercase text-slate-500">Deductible ($)</span>
          </Hint>
          <input type="number" className="input-field w-full text-sm" value={deductible} onChange={(e) => setDeductible(e.target.value)} />
        </label>
      </div>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <input className="input-field text-xs" placeholder="License #" value={license} onChange={(e) => setLicense(e.target.value)} />
        <input className="input-field text-xs" placeholder="Validation notes (optional)" value={notes} onChange={(e) => setNotes(e.target.value)} />
      </div>
      <div className="mt-4 flex justify-end">
        <button type="button" onClick={handleValidate} disabled={busy} className="btn-primary btn-sm text-xs disabled:opacity-50">
          {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
          Validate terms
        </button>
      </div>
      {error && <p className="mt-2 text-xs text-red-300">{error}</p>}
    </div>
  );
}
