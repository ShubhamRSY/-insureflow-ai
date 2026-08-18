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

  const pick = (code) => {
    setSelectedState(code);
    setOpen(false);
    setSearch('');
  };

  if (compact) {
    return (
      <div ref={ref} className="relative inline-block">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-surface-overlay px-2.5 py-1 text-sm font-medium text-slate-200 transition-colors hover:border-emerald-500/50"
          aria-expanded={open}
          aria-haspopup="listbox"
        >
          <span className="flex h-5 w-5 items-center justify-center rounded bg-emerald-500/20 text-xs font-bold text-emerald-400">
            {selectedState || 'US'}
          </span>
          <span className="hidden sm:inline">{selectedObj?.name || 'All States'}</span>
          <svg className={`h-3 w-3 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
        </button>
        {open && (
          <div className="absolute right-0 top-full z-[80] mt-1 w-72 overflow-hidden rounded-xl border border-white/15 bg-surface-raised shadow-xl">
            <div className="border-b border-white/10 p-2">
              <input
                type="text"
                placeholder="Search states..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="input py-1.5"
                autoFocus
                aria-label="Search states"
              />
            </div>
            <div className="max-h-72 overflow-y-auto" role="listbox">
              <button
                type="button"
                onClick={() => pick('')}
                className={`flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors hover:bg-white/[0.05] ${!selectedState ? 'bg-emerald-500/10 font-medium text-emerald-500' : 'text-slate-200'}`}
              >
                <span className="flex h-5 w-5 items-center justify-center rounded bg-surface-overlay text-[10px] font-bold text-slate-400">ALL</span>
                All States
              </button>
              {filtered.map(s => (
                <button
                  type="button"
                  key={s.code}
                  onClick={() => pick(s.code)}
                  className={`flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors hover:bg-white/[0.05] ${selectedState === s.code ? 'bg-emerald-500/10 font-medium text-emerald-500' : 'text-slate-200'}`}
                >
                  <span className="flex h-5 w-5 items-center justify-center rounded bg-surface-overlay text-[10px] font-bold text-slate-400">{s.code}</span>
                  {s.name}
                </button>
              ))}
              {filtered.length === 0 && (
                <p className="px-3 py-4 text-center text-sm text-slate-500">No states match “{search}”</p>
              )}
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="glass-card p-6">
      <h3 className="mb-4 text-lg font-semibold text-slate-100">Select Operating State</h3>
      <p className="mb-4 text-sm text-slate-400">
        Choose a state to enforce only that jurisdiction&apos;s insurance laws. Like AWS regions, but for state regulatory compliance.
      </p>
      <div className="grid max-h-96 grid-cols-2 gap-2 overflow-y-auto sm:grid-cols-3 md:grid-cols-4">
        <button
          type="button"
          onClick={() => setSelectedState('')}
          className={`rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${!selectedState ? 'border-emerald-500/50 bg-emerald-500/20 text-emerald-500' : 'border-white/10 bg-surface-overlay text-slate-300 hover:border-white/20'}`}
        >
          All States
        </button>
        {US_STATES.map(s => (
          <button
            type="button"
            key={s.code}
            onClick={() => setSelectedState(s.code)}
            className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-left text-sm font-medium transition-colors ${selectedState === s.code ? 'border-emerald-500/50 bg-emerald-500/20 text-emerald-500' : 'border-white/10 bg-surface-overlay text-slate-300 hover:border-white/20'}`}
          >
            <span className="text-xs font-bold text-slate-500">{s.code}</span>
            {s.name}
          </button>
        ))}
      </div>
    </div>
  );
}
