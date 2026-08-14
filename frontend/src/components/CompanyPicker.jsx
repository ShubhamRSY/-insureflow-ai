import { useEffect, useState } from 'react';
import { Building2, Plus } from 'lucide-react';
import { endpoints } from '../lib/api';
import { Hint } from './ui';
import { UI_HINTS } from '../lib/uiHints';

export default function CompanyPicker({ value = '', name = '', onChange, disabled = false }) {
  const [companies, setCompanies] = useState([]);
  const [adding, setAdding] = useState(false);
  const [newName, setNewName] = useState('');
  const [error, setError] = useState('');

  const load = async () => {
    try {
      const r = await endpoints.insuranceCompanies();
      setCompanies(r.companies || []);
    } catch {
      setCompanies([]);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const emit = (id, label) => {
    onChange?.({ id, name: label });
  };

  const handleSelect = (id) => {
    if (id === '__add__') {
      setAdding(true);
      setError('');
      return;
    }
    const match = companies.find((c) => c.id === id);
    emit(id, match?.name || '');
  };

  const handleAdd = async () => {
    const label = newName.trim();
    if (!label) {
      setError('Enter a company name');
      return;
    }
    setError('');
    try {
      const created = await endpoints.addInsuranceCompany({ name: label });
      await load();
      emit(created.id, created.name);
      setNewName('');
      setAdding(false);
    } catch (e) {
      emit('', label);
      setAdding(false);
      setError(e.message || 'Could not save to panel — using this name for the run');
    }
  };

  return (
    <div className="space-y-2 rounded-xl border border-white/[0.06] bg-surface/30 p-3">
      <Hint text={UI_HINTS.insuranceCompany}>
        <label htmlFor="insurance-company" className="hint-label mb-1 flex cursor-help items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
          <Building2 className="h-3.5 w-3.5" />
          Insurance company
        </label>
      </Hint>
      <select
        id="insurance-company"
        value={adding ? '__add__' : value}
        onChange={(e) => handleSelect(e.target.value)}
        disabled={disabled}
        className="input-field w-full text-xs"
        aria-label="Insurance company"
      >
        <option value="">Choose writing company…</option>
        {companies.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}{c.kind === 'demo' ? ' (demo book)' : ''}
          </option>
        ))}
        <option value="__add__">Add a company to this panel…</option>
      </select>
      {adding && (
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Appointed company name"
            className="input-field min-w-[12rem] flex-1 text-xs"
            aria-label="New insurance company name"
          />
          <button type="button" onClick={handleAdd} disabled={disabled} className="btn-secondary btn-sm text-[11px]">
            <Plus className="h-3 w-3" /> Add
          </button>
          <button type="button" onClick={() => { setAdding(false); setNewName(''); }} className="text-[11px] text-slate-500 hover:text-slate-300">
            Cancel
          </button>
        </div>
      )}
      {name && value ? (
        <p className="text-[10px] text-slate-500">This file will underwrite for <span className="font-medium text-slate-300">{name}</span>.</p>
      ) : (
        <p className="text-[10px] text-slate-600">Optional — pick whose paper this file is for. Your panel, not a market Rytera invented.</p>
      )}
      {error ? <p className="text-[10px] text-amber-400">{error}</p> : null}
    </div>
  );
}
