import { useState, useRef, useEffect } from 'react';
import { useStateContext, US_STATES } from '../lib/useStateContext';

export default function StateSelector({ compact = false }) {
  const { selectedState, setSelectedState } = useStateContext();
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const ref = useRef(null);

  useEffect(() => {
    function handleClick(e) { if (ref.current && !ref.current.contains(e.target)) setOpen(false); }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const filtered = US_STATES.filter(s =>
    s.name.toLowerCase().includes(search.toLowerCase()) ||
    s.code.toLowerCase().includes(search.toLowerCase())
  );

  const selectedObj = US_STATES.find(s => s.code === selectedState);

  if (compact) {
    return (
      <div ref={ref} className="relative inline-block">
        <button
          onClick={() => setOpen(!open)}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 hover:border-emerald-500/50 text-sm font-medium transition-colors"
        >
          <span className="w-5 h-5 rounded bg-emerald-500/20 text-emerald-400 text-xs font-bold flex items-center justify-center">
            {selectedState || 'US'}
          </span>
          <span className="text-white/70 hidden sm:inline">{selectedObj?.name || 'All States'}</span>
          <svg className={`w-3 h-3 text-white/40 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
        </button>
        {open && (
          <div className="absolute right-0 top-full mt-1 z-50 w-64 bg-gray-900 border border-white/10 rounded-xl shadow-2xl overflow-hidden">
            <div className="p-2 border-b border-white/5">
              <input
                type="text"
                placeholder="Search states..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="w-full px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-white/30 focus:outline-none focus:border-emerald-500/50"
                autoFocus
              />
            </div>
            <div className="max-h-64 overflow-y-auto">
              <button
                onClick={() => { setSelectedState(''); setOpen(false); setSearch(''); }}
                className={`w-full px-3 py-2 text-left text-sm flex items-center gap-2 hover:bg-white/5 transition-colors ${!selectedState ? 'bg-emerald-500/10 text-emerald-400' : 'text-white/70'}`}
              >
                <span className="w-5 h-5 rounded bg-white/10 text-white/50 text-xs font-bold flex items-center justify-center">ALL</span>
                All States
              </button>
              {filtered.map(s => (
                <button
                  key={s.code}
                  onClick={() => { setSelectedState(s.code); setOpen(false); setSearch(''); }}
                  className={`w-full px-3 py-2 text-left text-sm flex items-center gap-2 hover:bg-white/5 transition-colors ${selectedState === s.code ? 'bg-emerald-500/10 text-emerald-400' : 'text-white/70'}`}
                >
                  <span className="w-5 h-5 rounded bg-white/10 text-white/50 text-xs font-bold flex items-center justify-center">{s.code}</span>
                  {s.name}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="glass-card p-6">
      <h3 className="text-lg font-semibold text-white mb-4">Select Operating State</h3>
      <p className="text-sm text-white/50 mb-4">
        Choose a state to enforce only that jurisdiction's insurance laws. Like AWS regions, but for state regulatory compliance.
      </p>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 max-h-96 overflow-y-auto">
        <button
          onClick={() => setSelectedState('')}
          className={`px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${!selectedState ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-400' : 'bg-white/5 border-white/10 text-white/60 hover:border-white/20'}`}
        >
          All States
        </button>
        {US_STATES.map(s => (
          <button
            key={s.code}
            onClick={() => setSelectedState(s.code)}
            className={`px-3 py-2 rounded-lg text-sm font-medium border transition-colors text-left flex items-center gap-2 ${selectedState === s.code ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-400' : 'bg-white/5 border-white/10 text-white/60 hover:border-white/20'}`}
          >
            <span className="text-xs font-bold opacity-50">{s.code}</span>
            {s.name}
          </button>
        ))}
      </div>
    </div>
  );
}
