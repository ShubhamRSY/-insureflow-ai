import { useState } from 'react';
import {
  AlertCircle, AlertTriangle, Info, ChevronDown, ChevronRight,
  Clock, User, FileText, Download
} from 'lucide-react';
import { Badge } from './ui';
import { endpoints } from '../lib/api';

const SEVERITY_CONFIG = {
  critical: { icon: AlertCircle, cls: 'text-red-400 bg-red-500/10 ring-red-500/20' },
  error: { icon: AlertCircle, cls: 'text-red-400 bg-red-500/10 ring-red-500/20' },
  warning: { icon: AlertTriangle, cls: 'text-amber-400 bg-amber-500/10 ring-amber-500/20' },
  info: { icon: Info, cls: 'text-sky-400 bg-sky-500/10 ring-sky-500/20' },
  success: { icon: Info, cls: 'text-emerald-400 bg-emerald-500/10 ring-emerald-500/20' },
};

function formatTS(ts) {
  if (!ts) return '';
  try { return new Date(ts).toLocaleString(); } catch { return String(ts); }
}

function EntryRow({ entry, index }) {
  const [open, setOpen] = useState(false);
  const sev = SEVERITY_CONFIG[entry.severity] || SEVERITY_CONFIG.info;
  const SevIcon = sev.icon;

  return (
    <div className="group">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={`flex w-full items-start gap-3 rounded-lg p-3 text-left transition hover:bg-white/[0.03] ${open ? 'bg-white/[0.02]' : ''}`}
      >
        <div className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full ring-1 ${sev.cls}`}>
          <SevIcon className="h-3.5 w-3.5" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">{entry.event}</span>
            {entry.agent_name && (
              <span className="flex items-center gap-1 rounded bg-white/[0.04] px-1.5 py-0.5 text-[10px] text-slate-500">
                <User className="h-2.5 w-2.5" /> {entry.agent_name}
              </span>
            )}
          </div>
          {entry.message && <p className="mt-0.5 text-sm text-slate-400">{entry.message}</p>}
          <div className="mt-1 flex items-center gap-3 text-[10px] text-slate-500">
            <span className="flex items-center gap-1"><Clock className="h-2.5 w-2.5" /> {formatTS(entry.timestamp)}</span>
            <span className="font-mono">#{index + 1}</span>
          </div>
        </div>
        {entry.metadata && Object.keys(entry.metadata).length > 0 && (
          <div className="shrink-0 text-slate-600 transition group-hover:text-slate-400">
            {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </div>
        )}
      </button>
      {open && entry.metadata && Object.keys(entry.metadata).length > 0 && (
        <div className="ml-10 mb-2 rounded-lg bg-black/20 p-3">
          <pre className="overflow-x-auto text-[11px] text-slate-500">{JSON.stringify(entry.metadata, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

export default function AuditTrailViewer({ data, bundleId, onClose }) {
  const [exporting, setExporting] = useState(false);
  const [exportResult, setExportResult] = useState(null);

  const trail = data?.audit_trail;
  const entries = trail?.entries || [];
  const summary = trail?.summary?.() || {};
  const eventCounts = {};

  if (trail && trail.entries) {
    trail.entries.forEach(e => {
      eventCounts[e.event] = (eventCounts[e.event] || 0) + 1;
    });
  }

  const severityCounts = {};
  if (trail && trail.entries) {
    trail.entries.forEach(e => {
      severityCounts[e.severity] = (severityCounts[e.severity] || 0) + 1;
    });
  }

  const handleExport = async () => {
    setExporting(true);
    try {
      const r = await endpoints.auditPackage(bundleId);
      setExportResult(r);
    } catch (e) {
      alert(e.message || 'Export failed');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Audit Trail</p>
          <Badge status={entries.length > 0 ? `${entries.length} events` : 'empty'} />
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleExport}
            disabled={exporting}
            className="btn-secondary btn-sm text-xs"
          >
            <Download className="mr-1 h-3.5 w-3.5" />
            {exporting ? 'Exporting...' : 'Export Package'}
          </button>
          <button onClick={onClose} className="text-xs text-slate-500 hover:text-slate-300">Close</button>
        </div>
      </div>

      {exportResult && (
        <div className="rounded-lg bg-emerald-500/10 p-3 ring-1 ring-emerald-500/20">
          <p className="text-xs font-semibold text-emerald-400">Package Exported</p>
          <p className="mt-1 text-xs text-slate-400">
            {exportResult.artifact_count} artifacts &middot; SHA-256: <code className="font-mono text-[10px]">{exportResult.manifest_sha256?.slice(0, 16)}...</code>
          </p>
          <p className="text-xs text-slate-500">{exportResult.package_path}</p>
        </div>
      )}

      {(severityCounts.warning || severityCounts.error || severityCounts.critical) && (
        <div className="flex flex-wrap gap-2">
          {severityCounts.critical > 0 && <Badge status={`${severityCounts.critical} critical`} />}
          {severityCounts.error > 0 && <Badge status={`${severityCounts.error} errors`} />}
          {severityCounts.warning > 0 && <Badge status={`${severityCounts.warning} warnings`} />}
        </div>
      )}

      {trail && (
        <div className="grid grid-cols-3 gap-2 text-center">
          {[
            ['Started', formatTS(trail.started_at)],
            ['Completed', formatTS(trail.completed_at) || 'In Progress'],
            ['Entries', entries.length],
          ].map(([label, val]) => (
            <div key={label} className="rounded-lg bg-surface-overlay p-2 ring-1 ring-white/[0.04]">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{label}</p>
              <p className="mt-0.5 text-xs font-medium text-slate-300">{String(val)}</p>
            </div>
          ))}
        </div>
      )}

      {data?.provenance && (
        <details className="rounded-lg bg-surface-overlay ring-1 ring-white/[0.04]">
          <summary className="flex cursor-pointer items-center gap-2 p-3 text-xs font-semibold text-slate-400 hover:text-slate-300">
            <FileText className="h-3.5 w-3.5" /> Provenance Record
          </summary>
          <div className="border-t border-white/[0.04] p-3">
            <pre className="max-h-40 overflow-y-auto text-[11px] text-slate-500">{JSON.stringify(data.provenance, null, 2)}</pre>
          </div>
        </details>
      )}

      {entries.length === 0 ? (
        <p className="py-8 text-center text-sm text-slate-500">No audit entries recorded.</p>
      ) : (
        <div className="divide-y divide-white/[0.04] rounded-lg bg-surface-overlay ring-1 ring-white/[0.04]">
          {entries.map((entry, i) => (
            <EntryRow key={entry.entry_id || i} entry={entry} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}
