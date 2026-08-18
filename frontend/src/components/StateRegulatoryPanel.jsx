import { useState, useEffect } from 'react';
import { useStateContext } from '../lib/useStateContext';

const LINE_LABELS = {
  auto: { label: 'Auto', color: 'bg-blue-500' },
  property: { label: 'Property', color: 'bg-amber-500' },
  liability: { label: 'Liability', color: 'bg-red-500' },
  workers_comp: { label: "Workers' Comp", color: 'bg-purple-500' },
  life: { label: 'Life', color: 'bg-emerald-500' },
  health: { label: 'Health', color: 'bg-cyan-500' },
  cyber: { label: 'Cyber', color: 'bg-pink-500' },
  marine: { label: 'Marine', color: 'bg-indigo-500' },
  financial: { label: 'Financial', color: 'bg-orange-500' },
  specialty: { label: 'Specialty', color: 'bg-violet-500' },
  package: { label: 'Package', color: 'bg-teal-500' },
  flood: { label: 'Flood', color: 'bg-sky-500' },
};

const FLAG_SEVERITY = {
  critical: { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/30' },
  error: { bg: 'bg-orange-500/20', text: 'text-orange-400', border: 'border-orange-500/30' },
  warning: { bg: 'bg-amber-500/20', text: 'text-amber-400', border: 'border-amber-500/30' },
  info: { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/30' },
};

export default function StateRegulatoryPanel() {
  const { selectedState, selectedStateObj } = useStateContext();
  const [detail, setDetail] = useState(null);
  const [compliance, setCompliance] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeLine, setActiveLine] = useState('general');

  useEffect(() => {
    if (!selectedState) { setDetail(null); setCompliance(null); return; }
    setLoading(true);
    Promise.all([
      fetch(`/api/regulatory/state-detail?state=${selectedState}`).then(r => r.json()),
      fetch(`/api/regulatory/state-compliance-all?state=${selectedState}`).then(r => r.json()),
    ]).then(([d, c]) => { setDetail(d); setCompliance(c); setLoading(false); })
      .catch(() => setLoading(false));
  }, [selectedState]);

  if (!selectedState) return null;

  if (loading) return (
    <div className="glass-card p-6 animate-pulse">
      <div className="h-6 bg-white/5 rounded w-48 mb-4" />
      <div className="space-y-2">{[1,2,3].map(i => <div key={i} className="h-4 bg-white/5 rounded" />)}</div>
    </div>
  );

  if (!detail) return null;

  const gen = detail.general_rule;
  const lineRules = detail.line_rules || {};
  const complianceLines = compliance?.lines || {};

  const currentLineData = activeLine === 'general'
    ? gen
    : lineRules[activeLine] || {};
  const currentFlags = activeLine === 'general'
    ? (complianceLines.general?.flags || [])
    : (complianceLines[activeLine]?.flags || []);

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/20 flex items-center justify-center">
              <span className="text-xl font-bold text-emerald-400">{selectedState}</span>
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">{selectedStateObj?.name}</h2>
              <p className="text-sm text-white/40">Insurance Regulatory Rules — {detail.lines_available.length} lines</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatCard label="Tort Model" value={gen.tort_model?.replace(/_/g, ' ') || 'N/A'} />
          <StatCard label="Rate Filing" value={gen.rate_filing?.replace(/_/g, ' ') || 'N/A'} />
          <StatCard label="Claims Pay" value={gen.claims_prompt_pay_days ? `${gen.claims_prompt_pay_days} days` : 'N/A'} />
          <StatCard label="SL Tax" value={gen.surplus_lines_tax_rate ? `${(gen.surplus_lines_tax_rate * 100).toFixed(1)}%` : 'N/A'} />
        </div>
      </div>

      <div className="glass-card p-2">
        <div className="flex gap-1 flex-wrap">
          <button
            onClick={() => setActiveLine('general')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${activeLine === 'general' ? 'bg-white/10 text-white' : 'text-white/40 hover:text-white/60'}`}
          >
            General
          </button>
          {Object.keys(lineRules).map(line => {
            const meta = LINE_LABELS[line] || { label: line, color: 'bg-gray-500' };
            return (
              <button
                key={line}
                onClick={() => setActiveLine(line)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 ${activeLine === line ? 'bg-white/10 text-white' : 'text-white/40 hover:text-white/60'}`}
              >
                <span className={`w-2 h-2 rounded-full ${meta.color}`} />
                {meta.label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="glass-card p-6">
        <h3 className="text-lg font-semibold text-white mb-4">
          {activeLine === 'general' ? 'General Rules' : `${LINE_LABELS[activeLine]?.label || activeLine} Rules`}
        </h3>
        <div className="space-y-3">
          {Object.entries(currentLineData).filter(([k]) => !['state_code', 'state_name', 'line_of_business', 'data'].includes(k) && currentLineData[k] !== null && currentLineData[k] !== '' && currentLineData[k] !== false).map(([key, val]) => (
            <div key={key} className="flex items-start gap-3 py-2 border-b border-white/5 last:border-0">
              <span className="text-xs font-mono text-emerald-400/70 min-w-[160px] pt-0.5">{key.replace(/_/g, ' ')}</span>
              <span className="text-sm text-white/80">
                {typeof val === 'boolean' ? (val ? 'Yes' : 'No') : Array.isArray(val) ? val.join(', ') : String(val)}
              </span>
            </div>
          ))}
          {currentLineData.data && typeof currentLineData.data === 'object' && Object.entries(currentLineData.data).filter(([,v]) => v !== null && v !== '' && v !== false).map(([key, val]) => (
            <div key={`data-${key}`} className="flex items-start gap-3 py-2 border-b border-white/5 last:border-0">
              <span className="text-xs font-mono text-blue-400/70 min-w-[160px] pt-0.5">{key.replace(/_/g, ' ')}</span>
              <span className="text-sm text-white/80">
                {typeof val === 'boolean' ? (val ? 'Yes' : 'No') : Array.isArray(val) ? val.join(', ') : typeof val === 'object' ? JSON.stringify(val) : String(val)}
              </span>
            </div>
          ))}
        </div>
      </div>

      {currentFlags.length > 0 && (
        <div className="glass-card p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Compliance Flags ({currentFlags.length})</h3>
          <div className="space-y-2">
            {currentFlags.map((flag, i) => {
              const sev = FLAG_SEVERITY[flag.severity] || FLAG_SEVERITY.info;
              return (
                <div key={i} className={`flex items-start gap-3 p-3 rounded-lg border ${sev.bg} ${sev.border}`}>
                  <span className={`text-xs font-bold uppercase px-1.5 py-0.5 rounded ${sev.bg} ${sev.text}`}>{flag.severity}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-white/90">{flag.message}</p>
                    {flag.action_required && <p className="text-xs text-white/40 mt-1">Action: {flag.action_required}</p>}
                  </div>
                  <span className="text-xs text-white/30">{flag.rule_category}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value }) {
  return (
    <div className="bg-white/5 rounded-lg p-3">
      <p className="text-xs text-white/40 mb-1">{label}</p>
      <p className="text-sm font-semibold text-white capitalize">{value}</p>
    </div>
  );
}
