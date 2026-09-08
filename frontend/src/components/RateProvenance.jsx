import { useState } from 'react';
import { asList, displayText } from '../lib/safe';

const RATE_TYPE_LABELS = {
  loss_cost: 'Filed Loss Cost',
  lcm: 'Loss Cost Multiplier',
  state_relativity: 'State Relativity',
  minimum_premium: 'Minimum Premium',
  base_rate: 'Filed Base Rate',
  manual_rate: 'Manual Rate',
};

const RATE_TYPE_COLORS = {
  loss_cost: 'bg-emerald-500/10 border-emerald-500/25 text-emerald-200',
  lcm: 'bg-sky-500/10 border-sky-500/25 text-sky-200',
  state_relativity: 'bg-amber-500/10 border-amber-500/25 text-amber-200',
  minimum_premium: 'bg-red-500/10 border-red-500/25 text-red-200',
  base_rate: 'bg-violet-500/10 border-violet-500/25 text-violet-200',
  manual_rate: 'bg-indigo-500/10 border-indigo-500/25 text-indigo-200',
};

export default function RateProvenance({ metadata, className = '', defaultExpanded = false }) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  if (!metadata) return null;

  const rateSources = asList(metadata.rate_sources);
  const isFiledRate = metadata._is_filed_rate !== false;
  const rateBookPosture = metadata._rate_book_posture_audit || metadata.rate_book_posture || 'unknown';
  const filedPremium = Number(metadata._filed_premium || metadata.loss_cost || 0) || 0;
  const adjustedPremium = Number(metadata._adjusted_premium || metadata.adjusted_premium || 0) || 0;
  const aiMod = metadata._ai_mod_pct || 0;
  const rateBookId = metadata.rate_book_id || '';
  const rateBookGate = metadata.rate_book_gate || '';

  if (rateSources.length === 0 && !isFiledRate) return null;

  return (
    <div
      className={`rounded-xl border ${
        isFiledRate
          ? 'border-emerald-500/25 bg-emerald-500/5'
          : 'border-amber-500/25 bg-amber-500/5'
      } ${className}`}
    >
      <div className="flex items-center justify-between border-b border-white/[0.06] px-4 py-3">
        <div className="flex flex-wrap items-center gap-2">
          {isFiledRate ? (
            <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-emerald-300">
              Filed Rate
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full border border-amber-500/30 bg-amber-500/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-amber-300">
              Indication Only
            </span>
          )}
          <span className="text-sm font-medium text-slate-200">Rate source provenance</span>
        </div>
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-slate-400 hover:text-slate-200"
        >
          {expanded ? 'Collapse' : 'Expand'} sources
        </button>
      </div>

      <div className="grid grid-cols-2 gap-4 px-4 py-3 md:grid-cols-4">
        <div>
          <div className="mb-0.5 text-[10px] uppercase tracking-wider text-slate-500">Filed premium</div>
          <div className="text-sm font-semibold text-slate-100">${filedPremium.toLocaleString()}</div>
        </div>
        <div>
          <div className="mb-0.5 text-[10px] uppercase tracking-wider text-slate-500">Adjusted premium</div>
          <div className="text-sm font-semibold text-slate-100">${adjustedPremium.toLocaleString()}</div>
        </div>
        {aiMod !== 0 && (
          <div>
            <div className="mb-0.5 text-[10px] uppercase tracking-wider text-slate-500">AI suggested mod</div>
            <div className={`text-sm font-semibold ${aiMod < 0 ? 'text-emerald-300' : 'text-red-300'}`}>
              {aiMod > 0 ? '+' : ''}
              {aiMod}% <span className="text-[10px] font-normal text-slate-500">(advisory)</span>
            </div>
          </div>
        )}
        <div>
          <div className="mb-0.5 text-[10px] uppercase tracking-wider text-slate-500">Rate book</div>
          <div className="text-sm font-medium text-slate-200">{rateBookPosture}</div>
          {rateBookId ? <div className="text-[10px] text-slate-500">{rateBookId}</div> : null}
        </div>
      </div>

      {rateBookGate && (
        <div
          className={`border-t px-4 py-2 text-xs ${
            rateBookGate === 'ok'
              ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-200'
              : 'border-red-500/20 bg-red-500/10 text-red-200'
          }`}
        >
          {rateBookGate === 'ok'
            ? 'Rate book gate: OK — filed rate book loaded'
            : `Rate book gate: ${rateBookGate}`}
        </div>
      )}

      {expanded && rateSources.length > 0 && (
        <div className="space-y-2 px-4 pb-3">
          <div className="mb-1 mt-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            Filed rate sources
          </div>
          {rateSources.map((source, i) => (
            <div
              key={i}
              className={`flex flex-wrap items-start gap-2 rounded-lg border p-2 text-xs ${
                RATE_TYPE_COLORS[source.rate_type] || 'border-white/10 bg-white/[0.03] text-slate-300'
              }`}
            >
              <span className="font-medium">{displayText(RATE_TYPE_LABELS[source.rate_type] || source.rate_type)}</span>
              <span className="font-mono font-semibold">{displayText(source.value)}</span>
              {source.filing_id && <span className="text-slate-400">({displayText(source.filing_id)})</span>}
              {source.carrier && <span className="text-slate-400">Carrier: {displayText(source.carrier)}</span>}
              {source.effective_date && <span className="text-slate-400">Eff: {source.effective_date}</span>}
              {source.version && <span className="text-slate-400">v{source.version}</span>}
              {source.state && <span className="text-slate-400">{source.state}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
