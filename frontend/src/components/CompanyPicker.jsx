import { useEffect, useState } from 'react';
import { Building2, Plus, Trash2 } from 'lucide-react';
import { endpoints } from '../lib/api';
import { Hint } from './ui';
import { UI_HINTS } from '../lib/uiHints';

// Letters/digits/spaces and the punctuation real carrier names use.
// \p{L}/\p{N} (not \w) so unicode names like "Zürich AG" pass.
const NAME_OK = /^(?:[\p{L}\p{N}]|[ .,'&()/-])+$/u;
const HAS_LETTER = /\p{L}/u;

export function validateCompanyName(raw) {
  const clean = (raw || '').replace(/\s+/g, ' ').trim();
  if (!clean) return { ok: false, error: 'Enter a company name' };
  if (clean.length > 80) return { ok: false, error: 'Keep the name under 80 characters' };
  if (!NAME_OK.test(clean)) return { ok: false, error: 'Letters, numbers, spaces and . , \' & ( ) - / only — no @ ; : # or other symbols' };
  if (!HAS_LETTER.test(clean)) return { ok: false, error: 'Name must contain at least one letter' };
  return { ok: true, clean };
}

export default function CompanyPicker({ value = '', name = '', onChange, disabled = false }) {
  const [companies, setCompanies] = useState([]);
  const [adding, setAdding] = useState(false);
  const [newName, setNewName] = useState('');
  const [error, setError] = useState('');
  const [confirmRemoveId, setConfirmRemoveId] = useState('');

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
    setConfirmRemoveId('');
    if (id === '__add__') {
      setAdding(true);
      setError('');
      return;
    }
    const match = companies.find((c) => c.id === id);
    emit(id, match?.name || '');
  };

  const validation = adding ? validateCompanyName(newName) : null;

  const handleAdd = async () => {
    const v = validateCompanyName(newName);
    if (!v.ok) {
      setError(v.error);
      return;
    }
    setError('');
    try {
      const created = await endpoints.addInsuranceCompany({ name: v.clean });
      await load();
      emit(created.id, created.name);
      setNewName('');
      setAdding(false);
    } catch (e) {
      emit('', v.clean);
      setAdding(false);
      setError(e.message || 'Could not save to panel — using this name for the run');
    }
  };

  const selected = companies.find((c) => c.id === value);

  const handleRemove = async () => {
    if (confirmRemoveId !== value) {
      setConfirmRemoveId(value);
      return;
    }
    try {
      await endpoints.removeInsuranceCompany(value);
    } catch {
      /* panel entry may already be gone — clear locally regardless */
    }
    setConfirmRemoveId('');
    await load();
    emit('', '');
  };

  const inputInvalid = adding && newName.trim() !== '' && !validation.ok;

  return (
    <div className="space-y-2 rounded-xl border border-white/[0.06] bg-surface/30 p-3">
      <Hint text={UI_HINTS.insuranceCompany}>
        <label htmlFor="insurance-company" className="hint-label mb-1 flex cursor-help items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-300">
          <Building2 className="h-3.5 w-3.5" />
          Insurance company
        </label>
      </Hint>
      <select
        id="insurance-company"
        value={adding ? '__add__' : value}
        onChange={(e) => handleSelect(e.target.value)}
        disabled={disabled}
        className="input-field w-full text-sm"
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
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleAdd(); }}
              placeholder="Appointed company name"
              maxLength={90}
              aria-invalid={inputInvalid}
              className={`input-field min-w-[12rem] flex-1 text-xs ${inputInvalid ? 'border-amber-500/60' : ''}`}
              aria-label="New insurance company name"
            />
            <button type="button" onClick={handleAdd} disabled={disabled || inputInvalid} className="btn-secondary btn-sm text-[11px]">
              <Plus className="h-3 w-3" /> Add
            </button>
            <button type="button" onClick={() => { setAdding(false); setNewName(''); setError(''); }} className="text-[11px] text-slate-500 hover:text-slate-300">
              Cancel
            </button>
          </div>
          {inputInvalid ? (
            <p className="text-[10px] font-medium text-red-400">{validation.error}</p>
          ) : (
            <p className="text-[10px] text-red-400">Letters, numbers, spaces and . , ' &amp; ( ) - / only — no @ ; : # _ or other symbols</p>
          )}
        </div>
      )}
      {selected?.origin === 'org' && value && !disabled && (
        <div className="flex items-center justify-between rounded-lg border border-white/[0.06] bg-surface/30 px-2.5 py-1.5">
          <span className="truncate text-[11px] text-slate-400">
            Added by your panel{confirmRemoveId === value ? ' — remove it?' : ''}
          </span>
          <button
            type="button"
            onClick={handleRemove}
            disabled={disabled}
            className={`flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium transition-colors ${
              confirmRemoveId === value
                ? 'bg-red-500/15 text-red-300 hover:bg-red-500/25'
                : 'text-slate-500 hover:text-red-300'
            }`}
          >
            <Trash2 className="h-3 w-3" />
            {confirmRemoveId === value ? 'Confirm remove' : 'Remove'}
          </button>
        </div>
      )}
      {name && value ? (
        <p className="text-xs text-slate-400">This file will underwrite for <span className="font-medium text-slate-200">{name}</span>.</p>
      ) : (
        <p className="text-xs text-slate-400">Optional — pick whose paper this file is for. Your panel, not a market Rytera invented.</p>
      )}
      {error ? <p className="text-[10px] text-amber-400">{error}</p> : null}
    </div>
  );
}
