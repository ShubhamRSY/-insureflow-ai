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
  loss_cost: 'bg-green-50 border-green-200 text-green-800',
  lcm: 'bg-blue-50 border-blue-200 text-blue-800',
  state_relativity: 'bg-amber-50 border-amber-200 text-amber-800',
  minimum_premium: 'bg-red-50 border-red-200 text-red-800',
  base_rate: 'bg-purple-50 border-purple-200 text-purple-800',
  manual_rate: 'bg-indigo-50 border-indigo-200 text-indigo-800',
};

export default function RateProvenance({ metadata, className = '' }) {
  const [expanded, setExpanded] = useState(false);

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
    <div className={`rounded-lg border ${isFiledRate ? 'border-green-200 bg-green-50/30' : 'border-amber-200 bg-amber-50/30'} ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <div className="flex items-center gap-2">
          {isFiledRate ? (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 border border-green-200">
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
              Filed Rate
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800 border border-amber-200">
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" /></svg>
              Indication Only
            </span>
          )}
          <span className="text-sm font-medium text-gray-700">Rate Source Provenance</span>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1"
        >
          {expanded ? 'Collapse' : 'Expand'} sources
          <svg className={`w-3 h-3 transition-transform ${expanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
        </button>
      </div>

      {/* Summary */}
      <div className="px-4 py-3 grid grid-cols-2 md:grid-cols-4 gap-4">
        <div>
          <div className="text-xs text-gray-500 mb-0.5">Filed Premium</div>
          <div className="text-sm font-semibold text-gray-900">${filedPremium.toLocaleString()}</div>
        </div>
        <div>
          <div className="text-xs text-gray-500 mb-0.5">Adjusted Premium</div>
          <div className="text-sm font-semibold text-gray-900">${adjustedPremium.toLocaleString()}</div>
        </div>
        {aiMod !== 0 && (
          <div>
            <div className="text-xs text-gray-500 mb-0.5">AI Suggested Mod</div>
            <div className={`text-sm font-semibold ${aiMod < 0 ? 'text-green-700' : 'text-red-700'}`}>
              {aiMod > 0 ? '+' : ''}{aiMod}% <span className="text-xs font-normal text-gray-500">(advisory)</span>
            </div>
          </div>
        )}
        <div>
          <div className="text-xs text-gray-500 mb-0.5">Rate Book</div>
          <div className="text-sm font-medium text-gray-700">{rateBookPosture}</div>
          <div className="text-xs text-gray-400">{rateBookId}</div>
        </div>
      </div>

      {/* Gate status */}
      {rateBookGate && (
        <div className={`px-4 py-2 text-xs border-t ${
          rateBookGate === 'ok'
            ? 'bg-green-50 border-green-100 text-green-700'
            : 'bg-red-50 border-red-100 text-red-700'
        }`}>
          {rateBookGate === 'ok' ? 'Rate book gate: OK — filed rate book loaded' : `Rate book gate: ${rateBookGate}`}
        </div>
      )}

      {/* Expanded source details */}
      {expanded && rateSources.length > 0 && (
        <div className="px-4 pb-3 space-y-2">
          <div className="text-xs font-medium text-gray-500 uppercase tracking-wide mt-2 mb-1">Filed Rate Sources</div>
          {rateSources.map((source, i) => (
            <div
              key={i}
              className={`flex flex-wrap items-start gap-2 p-2 rounded border text-xs ${
                RATE_TYPE_COLORS[source.rate_type] || 'bg-gray-50 border-gray-200 text-gray-700'
              }`}
            >
              <span className="font-medium">{displayText(RATE_TYPE_LABELS[source.rate_type] || source.rate_type)}</span>
              <span className="font-mono font-semibold">{displayText(source.value)}</span>
              {source.filing_id && <span className="text-gray-500">({displayText(source.filing_id)})</span>}
              {source.carrier && <span className="text-gray-500">Carrier: {displayText(source.carrier)}</span>}
              {source.effective_date && <span className="text-gray-500">Eff: {source.effective_date}</span>}
              {source.version && <span className="text-gray-500">v{source.version}</span>}
              {source.state && <span className="text-gray-500">{source.state}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
