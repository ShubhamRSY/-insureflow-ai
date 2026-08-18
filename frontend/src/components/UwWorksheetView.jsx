import { fmtCurrency } from '../lib/api';
import { asList, displayText, fmtFixed } from '../lib/safe';

/** UW-facing rate worksheet — no internal eval scores. */
export default function UwWorksheetView({ worksheet, validatedTerms }) {
  if (!worksheet) return null;

  const terms = worksheet.indicated_terms || {};
  const exposure = worksheet.exposure || {};
  const validated = validatedTerms || {};
  const premium = validated.indicated_premium ?? terms.uw_validated_premium ?? terms.premium;
  const limit = validated.limit ?? terms.uw_validated_limit ?? terms.limit;
  const deductible = validated.deductible ?? terms.uw_validated_deductible ?? terms.deductible;

  return (
    <div className="rounded-xl bg-surface-overlay p-5 ring-1 ring-white/[0.04]">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Underwriting worksheet</p>
          <p className="mt-1 text-sm font-medium text-slate-100">
            {displayText(worksheet.product)}
            {worksheet.coverage ? ` · ${displayText(worksheet.coverage)}` : ''}
          </p>
          <p className="mt-0.5 text-[11px] text-slate-500">{displayText(worksheet.rating_method).replace(/_/g, ' ')}</p>
        </div>
        {validated.validated_at && (
          <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-400">
            UW validated
          </span>
        )}
      </div>

      <div className="mb-4 grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg bg-black/20 px-3 py-2">
          <p className="text-[10px] uppercase text-slate-500">Indicated premium</p>
          <p className="text-lg font-semibold text-slate-100">{fmtCurrency(premium)}</p>
        </div>
        <div className="rounded-lg bg-black/20 px-3 py-2">
          <p className="text-[10px] uppercase text-slate-500">Policy limit</p>
          <p className="text-lg font-semibold text-slate-100">{fmtCurrency(limit)}</p>
        </div>
        <div className="rounded-lg bg-black/20 px-3 py-2">
          <p className="text-[10px] uppercase text-slate-500">Deductible</p>
          <p className="text-lg font-semibold text-slate-100">{fmtCurrency(deductible)}</p>
        </div>
      </div>

      <div className="mb-4 grid gap-3 sm:grid-cols-2 text-xs">
        <div>
          <p className="font-medium text-slate-400">Exposure ({exposure.label || 'TIV'})</p>
          <p className="text-slate-200">{fmtCurrency(exposure.value)}</p>
        </div>
        <div>
          <p className="font-medium text-slate-400">Rate per $100 exposure</p>
          <p className="text-slate-200">${fmtFixed(terms.rate_per_100_exposure, 4) || '0.0000'}</p>
        </div>
        {worksheet.loss_experience && (
          <>
            <div>
              <p className="font-medium text-slate-400">Loss ratio (incurred / earned premium)</p>
              <p className="text-slate-200">
                {worksheet.loss_experience.known === false
                  ? 'Unknown — no earned/written premium'
                  : `${fmtFixed((worksheet.loss_experience.loss_ratio || 0) * 100, 1) || '0.0'}%`}
              </p>
            </div>
            <div>
              <p className="font-medium text-slate-400">Credibility (Z)</p>
              <p className="text-slate-200">{worksheet.loss_experience.credibility_z ?? '—'}</p>
            </div>
          </>
        )}
      </div>

      {(asList(worksheet.premium_buildup).length > 0) && (
        <div>
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Premium buildup</p>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[11px]">
              <thead>
                <tr className="border-b border-white/[0.06] text-slate-500">
                  <th className="py-1.5 pr-2 font-medium">Step</th>
                  <th className="py-1.5 pr-2 font-medium">Basis</th>
                  <th className="py-1.5 pr-2 font-medium">Factor</th>
                  <th className="py-1.5 font-medium">Mod %</th>
                </tr>
              </thead>
              <tbody>
                {asList(worksheet.premium_buildup).map((row, i) => (
                  <tr key={row.step || i} className="border-b border-white/[0.03] text-slate-300">
                    <td className="py-1.5 pr-2">{displayText(row.step)}</td>
                    <td className="py-1.5 pr-2 text-slate-500">{displayText(row.basis)}</td>
                    <td className="py-1.5 pr-2">{displayText(row.factor)}</td>
                    <td className="py-1.5">{fmtFixed(row.modifier_pct, 1) ? `${fmtFixed(row.modifier_pct, 1)}%` : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {worksheet.uw_focus && (
        <p className="mt-4 text-[11px] leading-relaxed text-slate-500">
          <span className="font-medium text-slate-400">UW focus: </span>
          {displayText(worksheet.uw_focus)}
        </p>
      )}
    </div>
  );
}
