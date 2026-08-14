import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { History, RefreshCw, Search } from 'lucide-react';
import { Badge, EmptyState } from '../components/ui';
import { endpoints } from '../lib/api';
import { insuranceLineLabel } from '../lib/insuranceLines';

export default function PriorDecisionsPage() {
  const navigate = useNavigate();
  const [q, setQ] = useState('');
  const [line, setLine] = useState('');
  const [state, setState] = useState('');
  const [decision, setDecision] = useState('');
  const [rows, setRows] = useState([]);
  const [archive, setArchive] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams();
      if (q.trim()) params.set('q', q.trim());
      if (line.trim()) params.set('line', line.trim());
      if (state.trim()) params.set('state', state.trim());
      if (decision.trim()) params.set('decision', decision.trim());
      const [mem, arch] = await Promise.all([
        endpoints.decisionMemory(params.toString()),
        endpoints.decisionArchive(),
      ]);
      setRows(mem.records || []);
      setArchive(arch);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }, [q, line, state, decision]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="mx-auto max-w-6xl space-y-8 animate-fade-in">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand/15">
            <History className="h-6 w-6 text-brand" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Prior decisions</h1>
            <p className="mt-1 text-slate-400">
              Reopen an old memo from the landing-zone archive. Search is pattern memory — line, state, TIV band, outcome — not named insureds. Source files stay in the carrier PAS.
            </p>
          </div>
        </div>
        <button type="button" onClick={load} className="btn-secondary btn-sm text-xs">
          <RefreshCw className="h-3.5 w-3.5" /> Refresh
        </button>
      </div>

      {archive && archive.source_docs_retained === false && (
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
          Bank mode: raw statements are not stored here. Open the memo for the decision; pull the file from the PAS if you need the original.
        </div>
      )}

      <div className="glass-card p-4">
        <form
          className="flex flex-wrap gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            load();
          }}
        >
          <div className="relative min-w-[12rem] flex-1">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
            <input
              className="input-field w-full pl-9"
              placeholder="Search line, state, TIV band, bundle id…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>
          <input className="input-field w-36" placeholder="Line" value={line} onChange={(e) => setLine(e.target.value)} />
          <input className="input-field w-20" placeholder="ST" maxLength={2} value={state} onChange={(e) => setState(e.target.value)} />
          <input className="input-field w-28" placeholder="Decision" value={decision} onChange={(e) => setDecision(e.target.value)} />
          <button type="submit" className="btn-primary btn-sm text-xs">Search</button>
        </form>
      </div>

      {error && <div className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
        </div>
      ) : !rows.length && !(archive?.cases || []).length ? (
        <EmptyState
          icon={History}
          title="No prior decisions yet"
          description="Run files on this desk. Each completed memo is archived here and remembered as a risk shape, not a person."
        />
      ) : (
        <div className="space-y-3">
          {(rows.length ? rows : archive?.cases || []).map((r) => {
            const id = r.bundle_id;
            const dec = r.decision || r.ai_decision || '';
            return (
              <button
                key={id}
                type="button"
                onClick={() => navigate(`/insurance/${id}`)}
                className="glass-card flex w-full items-center justify-between gap-4 p-4 text-left transition hover:ring-brand/30"
              >
                <div className="min-w-0">
                  <p className="font-mono text-sm font-semibold text-slate-100">{id}</p>
                  <p className="mt-1 text-xs text-slate-400">
                    {insuranceLineLabel(r.line || r.insurance_line) || r.line || r.insurance_line || '—'}
                    {(r.state || r.primary_state) ? ` · ${r.state || r.primary_state}` : ''}
                    {r.tiv_band ? ` · ${r.tiv_band}` : ''}
                    {r.naics ? ` · NAICS ${r.naics}` : ''}
                  </p>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1">
                  {dec ? <Badge status={dec} label={dec} /> : null}
                  <span className="text-[10px] text-slate-500">
                    {r.remembered_at || r.updated_at
                      ? new Date(r.remembered_at || r.updated_at).toLocaleString()
                      : ''}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
