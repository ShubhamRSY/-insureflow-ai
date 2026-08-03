import { useState, useEffect, useCallback } from 'react';
import {
  BookOpen, RefreshCw, Plus, CheckCircle, XCircle, Send, Camera,
  GitCompare, Upload, ListChecks, FlaskConical, FileText, Cpu, Shield,
  Bot, Boxes, Clock, User, ChevronRight, X, Sparkles,
} from 'lucide-react';
import { Badge, EmptyState } from '../components/ui';
import { endpoints } from '../lib/api';

function fmtDate(value) {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit',
  });
}

const TYPE_META = {
  prompt: { label: 'Prompt', icon: FileText, accent: 'text-amber-400', bg: 'bg-amber-500/15' },
  llm_config: { label: 'LLM Config', icon: Cpu, accent: 'text-sky-400', bg: 'bg-sky-500/15' },
  compliance_rule: { label: 'Compliance Rule', icon: Shield, accent: 'text-rose-400', bg: 'bg-rose-500/15' },
  agent_logic: { label: 'Agent Logic', icon: Bot, accent: 'text-violet-400', bg: 'bg-violet-500/15' },
};

function entryName(e) {
  if (e.component_type === 'prompt') return e.prompt_key || 'Untitled prompt';
  if (e.component_type === 'llm_config') return `${e.model_tier || 'llm'} config`;
  if (e.component_type === 'compliance_rule') return 'Compliance rules snapshot';
  if (e.component_type === 'agent_logic') return e.agent_type || 'agent logic';
  return e.entry_id;
}

function entryDetail(e) {
  if (e.component_type === 'prompt') {
    return `${(e.prompt_text || '').length} chars${e.prompt_hash ? ` · ${e.prompt_hash}` : ''}`;
  }
  if (e.component_type === 'llm_config') {
    return [e.model_name, e.provider, e.temperature != null ? `temp ${e.temperature}` : null, e.max_tokens != null ? `max ${e.max_tokens}` : null]
      .filter(Boolean).join(' · ');
  }
  if (e.component_type === 'compliance_rule') return `${Object.keys(e.rules_snapshot || {}).length} rules`;
  if (e.component_type === 'agent_logic') return e.source_file || 'no source file';
  return '';
}

function statusBadge(s) {
  return { draft: 'pending', review: 'processing', approved: 'approved', rejected: 'error', superseded: 'superseded' }[s] || s;
}

function stageBadge(s) {
  return {
    draft: 'pending', offline_eval: 'processing', hitl_review: 'processing',
    registry_review: 'processing', shadow: 'pending', canary: 'refer',
    champion: 'approved', production: 'ok', archived: 'archived', rejected: 'error',
  }[s] || s;
}

const OWNER_STYLES = {
  engineer: 'text-sky-400 bg-sky-500/15 ring-sky-500/25',
  ci: 'text-emerald-400 bg-emerald-500/15 ring-emerald-500/25',
  licensed_uw: 'text-amber-400 bg-amber-500/15 ring-amber-500/25',
  compliance: 'text-violet-400 bg-violet-500/15 ring-violet-500/25',
  platform: 'text-cyan-400 bg-cyan-500/15 ring-cyan-500/25',
  admin: 'text-rose-400 bg-rose-500/15 ring-rose-500/25',
  uw_ops: 'text-lime-400 bg-lime-500/15 ring-lime-500/25',
};

function snapshotCount(s) {
  return Object.keys(s.prompts || {}).length
    + Object.keys(s.llm_configs || {}).length
    + (s.compliance_rules || []).length
    + Object.keys(s.agent_logic || {}).length;
}

function DiffView({ diff }) {
  if (!diff) return null;
  if (diff.error) return <div className="text-sm text-red-300">{diff.error}</div>;
  const changedFields = diff.changes && typeof diff.changes === 'object' ? Object.entries(diff.changes) : [];
  const ruleLists = ['added', 'removed', 'changed'].filter((k) => Array.isArray(diff[k]) && diff[k].length > 0);
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2 text-xs text-slate-400">
        <span className="rounded-lg bg-surface-overlay px-2 py-1 ring-1 ring-white/[0.06]">type: <span className="text-slate-200">{diff.component_type || '—'}</span></span>
        <span className="rounded-lg bg-surface-overlay px-2 py-1 ring-1 ring-white/[0.06]">v{diff.from_version} → v{diff.to_version}</span>
        {diff.hash_changed !== undefined && (
          <span className="rounded-lg bg-surface-overlay px-2 py-1 ring-1 ring-white/[0.06]">hash changed: <span className={diff.hash_changed ? 'text-amber-400' : 'text-slate-200'}>{diff.hash_changed ? 'yes' : 'no'}</span></span>
        )}
        {diff.text_changed !== undefined && (
          <span className="rounded-lg bg-surface-overlay px-2 py-1 ring-1 ring-white/[0.06]">text changed: <span className={diff.text_changed ? 'text-amber-400' : 'text-slate-200'}>{diff.text_changed ? 'yes' : 'no'}</span></span>
        )}
        {diff.from_hash && diff.to_hash && (
          <span className="rounded-lg bg-surface-overlay px-2 py-1 ring-1 ring-white/[0.06] font-mono">{diff.from_hash} → {diff.to_hash}</span>
        )}
      </div>
      {changedFields.length > 0 && (
        <div className="rounded-lg bg-black/20 p-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">Changed fields</p>
          {changedFields.map(([k, v]) => (
            <div key={k} className="flex items-center justify-between gap-4 border-b border-white/[0.04] py-1.5 text-xs last:border-0">
              <span className="font-medium text-slate-300">{k}</span>
              <span className="font-mono text-slate-400">{JSON.stringify(v?.from)} → {JSON.stringify(v?.to)}</span>
            </div>
          ))}
        </div>
      )}
      {ruleLists.length > 0 && (
        <div className="rounded-lg bg-black/20 p-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">Rule diff</p>
          {ruleLists.map((k) => (
            <p key={k} className="pb-1 text-xs">
              <span className={`capitalize ${k === 'added' ? 'text-emerald-400' : k === 'removed' ? 'text-red-400' : 'text-amber-400'}`}>{k}:</span>{' '}
              <span className="font-mono text-slate-400">{diff[k].join(', ')}</span>
            </p>
          ))}
        </div>
      )}
      <div>
        <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-500">Raw diff</p>
        <pre className="max-h-64 overflow-y-auto rounded-lg bg-black/20 p-3 text-xs text-slate-400">{JSON.stringify(diff, null, 2)}</pre>
      </div>
    </div>
  );
}

function EntryCard({ entry, onAction }) {
  const meta = TYPE_META[entry.component_type] || { label: entry.component_type, icon: Boxes, accent: 'text-slate-400', bg: 'bg-white/5' };
  const Icon = meta.icon;
  const lastComment = entry.review_comments?.length ? entry.review_comments[entry.review_comments.length - 1] : null;
  return (
    <div className="glass-card p-4 transition hover:border-white/10">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${meta.bg}`}>
            <Icon className={`h-5 w-5 ${meta.accent}`} />
          </div>
          <div className="min-w-0">
            <p className="truncate font-semibold text-white">{entryName(entry)}</p>
            <p className="text-xs text-slate-500">{meta.label} · v{entry.version_label}</p>
          </div>
        </div>
        <Badge status={statusBadge(entry.status)} />
      </div>
      {entry.description && <p className="mt-2.5 text-xs leading-relaxed text-slate-400">{entry.description}</p>}
      {lastComment && lastComment.comment && (
        <p className="mt-2 rounded-lg bg-black/20 px-2.5 py-1.5 text-[11px] leading-relaxed text-slate-500">
          <span className="text-slate-300">{lastComment.reviewer || 'reviewer'}:</span> {lastComment.comment}
        </p>
      )}
      <div className="mt-3 flex items-center justify-between gap-2 border-t border-white/[0.06] pt-3">
        <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
          {entry.created_by && (
            <span className="inline-flex items-center gap-1 text-[11px] text-slate-500"><User className="h-3 w-3" />{entry.created_by}</span>
          )}
          <span className="inline-flex items-center gap-1 text-[11px] text-slate-500"><Clock className="h-3 w-3" />{fmtDate(entry.updated_at)}</span>
        </div>
        <div className="flex shrink-0 gap-1.5">
          {entry.status === 'draft' && (
            <button onClick={() => onAction(entry.entry_id, 'submit')} className="rounded-lg bg-sky-500/20 px-2.5 py-1 text-xs text-sky-400 transition hover:bg-sky-500/30" title="Submit for review">
              <Send className="mr-1 inline h-3 w-3" />Submit
            </button>
          )}
          {entry.status === 'review' && (
            <>
              <button onClick={() => onAction(entry.entry_id, 'approve')} className="rounded-lg bg-emerald-500/20 px-2.5 py-1 text-xs text-emerald-400 transition hover:bg-emerald-500/30" title="Approve">
                <CheckCircle className="mr-1 inline h-3 w-3" />Approve
              </button>
              <button onClick={() => onAction(entry.entry_id, 'reject')} className="rounded-lg bg-red-500/20 px-2.5 py-1 text-xs text-red-400 transition hover:bg-red-500/30" title="Reject">
                <XCircle className="mr-1 inline h-3 w-3" />Reject
              </button>
            </>
          )}
        </div>
      </div>
      <p className="mt-2 truncate font-mono text-[11px] text-slate-600">{entry.entry_id}</p>
      {entryDetail(entry) && <p className="mt-0.5 text-[11px] text-slate-500">{entryDetail(entry)}</p>}
    </div>
  );
}

function ContextSection({ title, icon: Icon, accent, items, emptyLabel }) {
  return (
    <div className="glass-card p-4">
      <div className="mb-3 flex items-center gap-2">
        <Icon className={`h-4 w-4 ${accent}`} />
        <h4 className="text-sm font-semibold text-slate-200">{title}</h4>
        <span className="ml-auto rounded-full bg-surface-overlay px-2 py-0.5 text-[11px] text-slate-400 ring-1 ring-white/[0.06]">{items.length}</span>
      </div>
      {items.length === 0 ? (
        <p className="text-xs leading-relaxed text-slate-500">{emptyLabel}</p>
      ) : (
        <ul className="space-y-2">
          {items.map((it) => (
            <li key={it.key} className="rounded-lg bg-black/20 px-3 py-2">
              <div className="flex items-center justify-between gap-2">
                <p className="truncate text-xs font-medium text-slate-200">{it.key}</p>
                <span className="shrink-0 text-[11px] text-slate-400">v{it.version || '—'}</span>
              </div>
              <div className="mt-1 flex items-center justify-between gap-2">
                <span className="truncate font-mono text-[10px] text-slate-600">{it.entry_id || '—'}</span>
                <span className="shrink-0 text-[10px] text-slate-500">{fmtDate(it.approved_at)}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function RegistryPage() {
  const [entries, setEntries] = useState([]);
  const [snapshots, setSnapshots] = useState([]);
  const [checklist, setChecklist] = useState(null);
  const [experiments, setExperiments] = useState(null);
  const [context, setContext] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [filter, setFilter] = useState('all');
  const [diffOpen, setDiffOpen] = useState(false);
  const [diffData, setDiffData] = useState(null);
  const [diffA, setDiffA] = useState('');
  const [diffB, setDiffB] = useState('');
  const [bootstrapping, setBootstrapping] = useState(false);
  const [form, setForm] = useState({ component: 'prompt', key: '', version: '1.0.0', description: '', change_notes: '' });

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [v, s, cl, ex, ctx] = await Promise.all([
        endpoints.registryVersions().catch(() => ({ entries: [] })),
        endpoints.registrySnapshots().catch(() => ({ snapshots: [] })),
        endpoints.releaseChecklist().catch(() => null),
        endpoints.releaseExperiments().catch(() => null),
        endpoints.registryContexts().catch(() => null),
      ]);
      setEntries(v.entries || []);
      setSnapshots(s.snapshots || []);
      setChecklist(cl);
      setExperiments(ex);
      setContext(ctx);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await endpoints.createRegistryEntry(form);
      setShowForm(false);
      setForm({ component: 'prompt', key: '', version: '1.0.0', description: '', change_notes: '' });
      await load();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleAction = async (id, action) => {
    try {
      if (action === 'submit') await endpoints.submitRegistryEntry(id);
      else if (action === 'approve') await endpoints.approveRegistryEntry(id);
      else if (action === 'reject') await endpoints.rejectRegistryEntry(id);
      await load();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleSnapshot = async () => {
    try {
      await endpoints.registrySnapshot();
      await load();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleBootstrap = async () => {
    setBootstrapping(true);
    try {
      await endpoints.registryBootstrap();
      await load();
    } catch (err) {
      alert(err.message);
    } finally {
      setBootstrapping(false);
    }
  };

  const handleDiff = async () => {
    try {
      const d = await endpoints.registryDiff(diffA, diffB);
      setDiffData(d);
    } catch (err) {
      alert(err.message);
    }
  };

  const steps = checklist?.checklist?.steps || [];
  const approvedCount = entries.filter((e) => e.status === 'approved').length;
  const byType = entries.reduce((acc, e) => {
    acc[e.component_type] = (acc[e.component_type] || 0) + 1;
    return acc;
  }, {});
  const visible = filter === 'all' ? entries : entries.filter((e) => e.component_type === filter);

  const stats = [
    { label: 'Release checklist', value: steps.length || '—', sub: 'engineering → compliance → production', icon: ListChecks, accent: 'text-amber-400', bar: 'from-amber-500 to-orange-400' },
    { label: 'Experiments', value: experiments?.summary?.total_runs ?? '—', sub: `${Object.keys(experiments?.summary?.by_class || {}).length} classes tracked`, icon: FlaskConical, accent: 'text-sky-400', bar: 'from-sky-500 to-cyan-400' },
    { label: 'Registry entries', value: entries.length, sub: `${approvedCount} approved`, icon: Boxes, accent: 'text-violet-400', bar: 'from-violet-500 to-fuchsia-400' },
    { label: 'Snapshots', value: snapshots.length, sub: 'audit pins of approved set', icon: Camera, accent: 'text-emerald-400', bar: 'from-emerald-500 to-teal-400' },
  ];

  const contextSections = [
    { key: 'prompts', title: 'Prompts', icon: FileText, accent: 'text-amber-400', items: Object.entries(context?.prompts || {}).map(([k, v]) => ({ key: k, ...v })), emptyLabel: 'No approved prompts — run Bootstrap to seed from current code.' },
    { key: 'llm_configs', title: 'LLM Configs', icon: Cpu, accent: 'text-sky-400', items: Object.entries(context?.llm_configs || {}).map(([k, v]) => ({ key: k, ...v })), emptyLabel: 'No approved LLM configs — run Bootstrap to seed tiers.' },
    { key: 'compliance_rules', title: 'Compliance Rules', icon: Shield, accent: 'text-rose-400', items: (context?.compliance_rules || []).map((id) => ({ key: id, entry_id: id })), emptyLabel: 'No approved compliance rule snapshots yet.' },
    { key: 'agent_logic', title: 'Agent Logic', icon: Bot, accent: 'text-violet-400', items: Object.entries(context?.agent_logic || {}).map(([k, v]) => ({ key: k, ...v })), emptyLabel: 'No approved agent logic — run Bootstrap to seed agents.' },
  ];

  const keyPlaceholder = {
    prompt: 'prompt key, e.g. uw_decision',
    llm_config: 'tier, e.g. cheap / expensive / default',
    compliance_rule: 'optional',
    agent_logic: 'agent type, e.g. uw_decision',
  }[form.component];

  return (
    <div className="mx-auto max-w-7xl space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-500/15">
            <BookOpen className="h-6 w-6 text-amber-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Model Registry</h1>
            <p className="mt-1 text-sm text-slate-400">
              Every agent change ships as an experiment: classify → MLflow run → gates → HITL → registry approval → canary → production.
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => { setDiffOpen((o) => !o); if (!diffOpen) setDiffData(null); }} className="btn-secondary btn-sm text-xs"><GitCompare className="h-3.5 w-3.5" /> Diff</button>
          <button type="button" onClick={handleBootstrap} disabled={bootstrapping} className="btn-secondary btn-sm text-xs"><Upload className={`h-3.5 w-3.5 ${bootstrapping ? 'animate-spin' : ''}`} /> Bootstrap</button>
          <button type="button" onClick={handleSnapshot} className="btn-secondary btn-sm text-xs"><Camera className="h-3.5 w-3.5" /> Snapshot</button>
          <button type="button" onClick={() => setShowForm(true)} className="btn-primary btn-sm text-xs"><Plus className="h-3.5 w-3.5" /> New Entry</button>
          <button type="button" onClick={load} className="btn-secondary btn-sm text-xs"><RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /></button>
        </div>
      </div>

      {error && <div className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((s) => (
          <div key={s.label} className="glass-card group relative overflow-hidden p-5 animate-slide-up">
            <div className={`absolute inset-x-0 top-0 h-px bg-gradient-to-r ${s.bar} opacity-60`} />
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium uppercase tracking-wider text-slate-500">{s.label}</p>
              <s.icon className={`h-4 w-4 ${s.accent}`} />
            </div>
            <p className="mt-2 text-3xl font-bold tracking-tight text-white">{s.value}</p>
            {s.sub && <p className="mt-1 text-xs text-slate-500">{s.sub}</p>}
          </div>
        ))}
      </div>

      {checklist && (
        <div className="glass-card p-6">
          <div className="mb-5 flex items-start justify-between gap-4">
            <div>
              <h3 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
                <ListChecks className="h-4 w-4 text-amber-400" /> Agent release checklist
              </h3>
              <p className="mt-1 text-sm text-slate-400">{checklist.summary}</p>
            </div>
            <span className="shrink-0 rounded-full bg-amber-500/15 px-2.5 py-1 text-xs font-semibold text-amber-400 ring-1 ring-amber-500/20">{steps.length} steps</span>
          </div>
          <ol className="space-y-0">
            {steps.map((s, i) => (
              <li key={s.id || i} className="relative flex gap-4">
                {i < steps.length - 1 && <span className="absolute left-4 top-9 h-[calc(100%-1.75rem)] w-px bg-white/[0.06]" />}
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface-overlay text-xs font-bold text-amber-400 ring-1 ring-amber-500/25">
                  {s.step}
                </div>
                <div className="pb-5">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-semibold text-slate-200">{s.title}</p>
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ring-1 ${OWNER_STYLES[s.owner] || 'text-slate-400 bg-white/5 ring-white/10'}`}>{s.owner}</span>
                    {s.required && <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-amber-400/70 ring-1 ring-amber-500/15">required</span>}
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-slate-400">{s.detail}</p>
                  {s.artifacts?.length > 0 && (
                    <div className="mt-1.5 flex flex-wrap gap-1.5">
                      {s.artifacts.map((a) => (
                        <span key={a} className="rounded bg-black/25 px-1.5 py-0.5 text-[10px] text-slate-500">{a}</span>
                      ))}
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ol>
          {checklist.stages_explained && (
            <div className="border-t border-white/[0.06] pt-4">
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">Promotion path — hover for meaning</p>
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(checklist.stages_explained).map(([stage, desc]) => (
                  <span key={stage} title={desc} className="cursor-default rounded-lg bg-surface-overlay px-2 py-1 text-[11px] text-slate-400 ring-1 ring-white/[0.06] hover:text-slate-200">{stage}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {experiments && (
        <div className="glass-card p-6">
          <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
                <FlaskConical className="h-4 w-4 text-sky-400" /> Experiments
              </h3>
              <p className="mt-1 text-xs text-slate-500">
                {experiments.experiment_name}
                {experiments.mlflow_tracking_uri ? ' · MLflow tracking URI set' : ' · local JSONL store (set MLFLOW_TRACKING_URI to sync)'}
                {' · '}{experiments.summary?.total_runs || 0} runs
              </p>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(experiments.summary?.by_class || {}).map(([k, v]) => (
                <span key={k} className="rounded-lg bg-surface-overlay px-2.5 py-1 text-xs text-slate-400 ring-1 ring-white/[0.06]">{k}: {v}</span>
              ))}
            </div>
          </div>
          {experiments.runs?.length ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/[0.06] text-left text-xs uppercase tracking-wider text-slate-500">
                    <th className="px-3 py-2">Run</th>
                    <th className="px-3 py-2">Class</th>
                    <th className="px-3 py-2">Stage</th>
                    <th className="px-3 py-2">Key metrics</th>
                    <th className="px-3 py-2">Logged</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  {experiments.runs.slice().reverse().map((r) => (
                    <tr key={r.run_id} className="align-top hover:bg-white/[0.02]">
                      <td className="px-3 py-2.5">
                        <p className="font-medium text-slate-200">{r.name}</p>
                        {r.hypothesis && <p className="mt-0.5 max-w-xs text-[11px] text-slate-500">{r.hypothesis}</p>}
                        <p className="mt-0.5 font-mono text-[10px] text-slate-600">{r.run_id}</p>
                      </td>
                      <td className="px-3 py-2.5">
                        <span className="rounded-lg bg-surface-overlay px-2 py-0.5 text-xs text-slate-300 ring-1 ring-white/[0.06]">{r.experiment_class}</span>
                      </td>
                      <td className="px-3 py-2.5"><Badge status={stageBadge(r.stage)} /></td>
                      <td className="px-3 py-2.5">
                        <div className="flex max-w-xs flex-wrap gap-1">
                          {Object.entries(r.metrics || {}).slice(0, 3).map(([k, v]) => (
                            <span key={k} className="rounded bg-black/25 px-1.5 py-0.5 font-mono text-[11px] text-slate-400" title={k}>
                              {k}={typeof v === 'number' ? v.toFixed(3) : v}
                            </span>
                          ))}
                          {Object.keys(r.metrics || {}).length > 3 && <span className="text-[10px] text-slate-600">+{Object.keys(r.metrics).length - 3} more</span>}
                        </div>
                      </td>
                      <td className="whitespace-nowrap px-3 py-2.5 text-xs text-slate-500">{fmtDate(r.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-slate-500">No experiment runs yet — start one from the release workflow.</p>
          )}
        </div>
      )}

      <div className="glass-card p-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
              <Boxes className="h-4 w-4 text-violet-400" /> Registry entries
            </h3>
            <p className="mt-1 text-xs text-slate-500">draft → review → approved · approved entries pin the live agent stack</p>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {[['all', 'All', entries.length], ['prompt', 'Prompts', byType.prompt || 0], ['llm_config', 'LLM Configs', byType.llm_config || 0], ['compliance_rule', 'Compliance', byType.compliance_rule || 0], ['agent_logic', 'Agent Logic', byType.agent_logic || 0]].map(([k, label, count]) => (
              <button
                key={k}
                type="button"
                onClick={() => setFilter(k)}
                className={`rounded-full px-3 py-1 text-xs font-medium ring-1 transition ${filter === k ? 'bg-violet-500/15 text-violet-300 ring-violet-500/30' : 'bg-surface-overlay text-slate-400 ring-white/[0.06] hover:text-slate-200'}`}
              >
                {label} <span className="ml-0.5 opacity-60">{count}</span>
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="flex justify-center py-12">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
          </div>
        ) : visible.length === 0 ? (
          <EmptyState
            icon={Boxes}
            title="No registry entries"
            description="Seed the registry from current code (prompts, LLM configs, compliance rules, agent logic) or create an entry by hand."
            action={<button type="button" onClick={handleBootstrap} disabled={bootstrapping} className="btn-secondary btn-sm"><Upload className={`mr-1.5 inline h-3.5 w-3.5 ${bootstrapping ? 'animate-spin' : ''}`} />Bootstrap registry</button>}
          />
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {visible.map((e) => <EntryCard key={e.entry_id} entry={e} onAction={handleAction} />)}
          </div>
        )}
      </div>

      <div className="glass-card p-6">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h3 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
              <BookOpen className="h-4 w-4 text-emerald-400" /> Approved registry context
            </h3>
            <p className="mt-1 text-xs text-slate-500">What a snapshot pins — the currently approved versions by component</p>
          </div>
          <span className="rounded-full bg-emerald-500/15 px-2.5 py-1 text-xs font-semibold text-emerald-400 ring-1 ring-emerald-500/20">{entries.filter((e) => e.status === 'approved').length} approved</span>
        </div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {contextSections.map((sec) => <ContextSection key={sec.key} {...sec} />)}
        </div>
      </div>

      <div className="glass-card p-6">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h3 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
              <Camera className="h-4 w-4 text-slate-400" /> Snapshots
            </h3>
            <p className="mt-1 text-xs text-slate-500">Audit pins of the approved set at release time</p>
          </div>
          <button type="button" onClick={handleSnapshot} className="btn-secondary btn-sm text-xs"><Camera className="h-3.5 w-3.5" /> Take snapshot</button>
        </div>
        {snapshots.length === 0 ? (
          <p className="text-sm text-slate-500">No snapshots yet — take one after approvals to pin the audit set.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/[0.06] text-left text-xs uppercase tracking-wider text-slate-500">
                  <th className="px-3 py-2">Snapshot</th>
                  <th className="px-3 py-2">Taken</th>
                  <th className="px-3 py-2">Pinned components</th>
                  <th className="px-3 py-2">Bundle</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {snapshots.slice().reverse().map((s) => (
                  <tr key={s.snapshot_id} className="hover:bg-white/[0.02]">
                    <td className="whitespace-nowrap px-3 py-2.5 font-mono text-xs text-slate-300">{s.snapshot_id}</td>
                    <td className="whitespace-nowrap px-3 py-2.5 text-xs text-slate-400">{fmtDate(s.generated_at)}</td>
                    <td className="px-3 py-2.5">
                      <div className="flex flex-wrap gap-1">
                        {Object.keys(s.prompts || {}).length > 0 && <span className="rounded bg-amber-500/10 px-1.5 py-0.5 text-[11px] text-amber-400">prompts {Object.keys(s.prompts).length}</span>}
                        {Object.keys(s.llm_configs || {}).length > 0 && <span className="rounded bg-sky-500/10 px-1.5 py-0.5 text-[11px] text-sky-400">llm {Object.keys(s.llm_configs).length}</span>}
                        {(s.compliance_rules || []).length > 0 && <span className="rounded bg-rose-500/10 px-1.5 py-0.5 text-[11px] text-rose-400">rules {(s.compliance_rules || []).length}</span>}
                        {Object.keys(s.agent_logic || {}).length > 0 && <span className="rounded bg-violet-500/10 px-1.5 py-0.5 text-[11px] text-violet-400">agents {Object.keys(s.agent_logic).length}</span>}
                        {snapshotCount(s) === 0 && <span className="text-[11px] text-slate-600">empty</span>}
                      </div>
                    </td>
                    <td className="px-3 py-2.5 text-xs text-slate-500">{s.bundle_id || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {diffOpen && (
        <div className="glass-card p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
              <GitCompare className="h-4 w-4" /> Diff viewer
            </h3>
            <button type="button" onClick={() => { setDiffOpen(false); setDiffData(null); }} className="text-xs text-slate-500 hover:text-slate-300"><X className="mr-1 inline h-3 w-3" />Close</button>
          </div>
          <div className="mb-4 flex flex-wrap items-end gap-3">
            <div className="min-w-[220px] flex-1">
              <label className="mb-1 block text-xs text-slate-500">Version A</label>
              <select className="input-field w-full text-sm" value={diffA} onChange={(e) => setDiffA(e.target.value)}>
                <option value="">Select…</option>
                {entries.map((e) => <option key={e.entry_id} value={e.entry_id}>{entryName(e)} v{e.version_label}</option>)}
              </select>
            </div>
            <ChevronRight className="mb-2 hidden h-4 w-4 text-slate-600 md:block" />
            <div className="min-w-[220px] flex-1">
              <label className="mb-1 block text-xs text-slate-500">Version B</label>
              <select className="input-field w-full text-sm" value={diffB} onChange={(e) => setDiffB(e.target.value)}>
                <option value="">Select…</option>
                {entries.map((e) => <option key={e.entry_id} value={e.entry_id}>{entryName(e)} v{e.version_label}</option>)}
              </select>
            </div>
            <button type="button" onClick={handleDiff} disabled={!diffA || !diffB || diffA === diffB} className="btn-primary btn-sm text-xs">Compare</button>
          </div>
          {diffData && <DiffView diff={diffData} />}
        </div>
      )}

      {showForm && (
        <div className="glass-card p-6">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400">
              <Sparkles className="h-4 w-4" /> Create registry entry
            </h3>
            <button type="button" onClick={() => setShowForm(false)} className="text-xs text-slate-500 hover:text-slate-300"><X className="mr-1 inline h-3 w-3" />Close</button>
          </div>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Component</label>
                <select className="input-field w-full text-sm" value={form.component} onChange={(e) => setForm((f) => ({ ...f, component: e.target.value, key: '' }))}>
                  <option value="prompt">Prompt</option>
                  <option value="llm_config">LLM Config</option>
                  <option value="compliance_rule">Compliance Rule</option>
                  <option value="agent_logic">Agent Logic</option>
                </select>
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Key</label>
                <input className="input-field w-full text-sm" value={form.key} onChange={(e) => setForm((f) => ({ ...f, key: e.target.value }))} placeholder={keyPlaceholder} required={form.component !== 'compliance_rule'} />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">Version</label>
                <input className="input-field w-full text-sm" value={form.version} onChange={(e) => setForm((f) => ({ ...f, version: e.target.value }))} required placeholder="1.0.0" />
              </div>
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-400">Description</label>
              <textarea className="input-field w-full text-sm" rows={2} value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} placeholder="What changed and why" />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-400">Change notes</label>
              <textarea className="input-field w-full text-sm" rows={2} value={form.change_notes} onChange={(e) => setForm((f) => ({ ...f, change_notes: e.target.value }))} placeholder="Review context for compliance" />
            </div>
            <div className="flex gap-2">
              <button type="submit" className="btn-primary btn-sm">Create</button>
              <button type="button" onClick={() => setShowForm(false)} className="btn-secondary btn-sm">Cancel</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
