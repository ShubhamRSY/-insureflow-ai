import { useEffect, useState } from 'react';
import { CheckCircle2, Circle, Loader2, ListChecks, Plus } from 'lucide-react';
import { endpoints } from '../lib/api';

export default function BindReadinessPanel({ bundleId, onChanged }) {
  const [data, setData] = useState(null);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    if (!bundleId) return;
    try {
      const res = await endpoints.subjectivities(bundleId);
      setData(res);
      setError('');
    } catch (e) {
      setError(e.message);
    }
  };

  useEffect(() => { load(); }, [bundleId]);

  if (!bundleId) return null;

  const readiness = data?.bind_readiness;
  const items = data?.subjectivities || [];

  const clearItem = async (id) => {
    setBusy(true);
    try {
      await endpoints.clearSubjectivity(bundleId, id, { notes: 'Cleared by UW' });
      await load();
      onChanged?.();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const addItem = async () => {
    if (!text.trim()) return;
    setBusy(true);
    try {
      await endpoints.addSubjectivity(bundleId, { text, category: 'uw' });
      setText('');
      await load();
      onChanged?.();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-xl bg-surface-overlay p-5 ring-1 ring-white/[0.04]">
      <div className="mb-3 flex items-center gap-2">
        <ListChecks className="h-4 w-4 text-brand" />
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Bind readiness</p>
        {readiness?.ready_to_bind ? (
          <span className="ml-auto rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-400">Ready to bind</span>
        ) : (
          <span className="ml-auto rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium text-amber-400">
            {readiness?.summary || 'Pending'}
          </span>
        )}
      </div>

      <ul className="mb-4 space-y-1.5">
        {(readiness?.checks || []).map((c) => (
          <li key={c.id} className="flex items-start gap-2 text-xs">
            {c.status === 'pass' ? (
              <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-400" />
            ) : (
              <Circle className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${c.status === 'fail' ? 'text-red-400' : 'text-amber-400'}`} />
            )}
            <span className="text-slate-300">
              {c.label}
              {c.detail ? <span className="text-slate-500"> — {c.detail}</span> : null}
            </span>
          </li>
        ))}
      </ul>

      <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Subjectivities</p>
      <div className="mb-3 max-h-40 space-y-2 overflow-y-auto">
        {!items.length && <p className="text-xs text-slate-500">No subjectivities — conditions will seed here after a run.</p>}
        {items.map((s) => (
          <div key={s.id} className={`flex items-start justify-between gap-2 rounded-lg px-3 py-2 text-xs ${s.status === 'open' ? 'bg-amber-500/10' : 'bg-black/20'}`}>
            <div className="min-w-0">
              <p className="text-slate-300">{s.text}</p>
              <p className="mt-0.5 text-[10px] text-slate-600">{s.category} · {s.status}</p>
            </div>
            {s.status === 'open' && (
              <button type="button" disabled={busy} onClick={() => clearItem(s.id)} className="shrink-0 text-[10px] text-brand hover:underline">
                Clear
              </button>
            )}
          </div>
        ))}
      </div>

      <div className="flex gap-2">
        <input className="input-field flex-1 text-xs" placeholder="Add subjectivity…" value={text} onChange={(e) => setText(e.target.value)} />
        <button type="button" onClick={addItem} disabled={busy || !text.trim()} className="btn-secondary btn-sm text-xs disabled:opacity-40">
          {busy ? <Loader2 className="h-3 w-3 animate-spin" /> : <Plus className="h-3 w-3" />} Add
        </button>
      </div>
      {error && <p className="mt-2 text-xs text-red-300">{error}</p>}
    </div>
  );
}
