import { useMemo, useState } from 'react';
import {
  ChevronDown, ChevronRight, FileText, FolderOpen, Loader2, X, AlertTriangle, Eye,
} from 'lucide-react';
import { endpoints } from '../lib/api';
import ConnectorLogo from './ConnectorLogo';

function formatBytes(n) {
  const bytes = Number(n) || 0;
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function buildTree(documents = []) {
  const sources = {};
  for (const doc of documents) {
    const sid = doc.source_id || 'unknown';
    const label = doc.connection_label || sid;
    if (!sources[sid]) sources[sid] = { source_id: sid, label, directories: {} };
    const directory = (doc.directory || '').replace(/^\/+|\/+$/g, '');
    if (!sources[sid].directories[directory]) sources[sid].directories[directory] = [];
    sources[sid].directories[directory].push(doc);
  }
  return Object.values(sources).map((src) => ({
    source_id: src.source_id,
    label: src.label,
    file_count: Object.values(src.directories).reduce((n, files) => n + files.length, 0),
    directories: Object.entries(src.directories)
      .sort(([a], [b]) => (a === '' ? -1 : b === '' ? 1 : a.localeCompare(b)))
      .map(([path, files]) => ({
        path,
        name: path ? path.split('/').pop() : '/',
        file_count: files.length,
        files,
      })),
  }));
}

/**
 * Connect & pull file viewer: source → directory → files, with preview.
 */
export default function PulledFilesBrowser({
  bundleId,
  documents = [],
  tree = null,
  relevanceByName = {},
  onRemove,
  onRemoveIrrelevant,
}) {
  const sources = useMemo(
    () => (tree?.length ? tree : buildTree(documents)),
    [tree, documents],
  );
  const [openSources, setOpenSources] = useState(() => new Set(sources.map((s) => s.source_id)));
  const [openDirs, setOpenDirs] = useState(() => {
    const keys = new Set();
    sources.forEach((s) => s.directories.forEach((d) => keys.add(`${s.source_id}::${d.path}`)));
    return keys;
  });
  const [preview, setPreview] = useState(null);
  const [loadingPreview, setLoadingPreview] = useState(false);

  const toggleSource = (id) => {
    setOpenSources((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };
  const toggleDir = (key) => {
    setOpenDirs((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  };

  const openPreview = async (doc) => {
    if (!bundleId || !doc?.doc_id) return;
    setLoadingPreview(true);
    try {
      const data = await endpoints.previewDraftDocument(bundleId, doc.doc_id);
      setPreview(data);
    } catch (e) {
      setPreview({
        filename: doc.filename,
        path: doc.path || doc.filename,
        previewable: false,
        message: e.message || 'Could not preview this file',
      });
    } finally {
      setLoadingPreview(false);
    }
  };

  if (!bundleId || (!documents.length && !sources.length)) return null;

  const irrelevantCount = documents.filter((d) => relevanceByName[d.filename]?.relevant === false).length;

  return (
    <div className="rounded-lg border border-white/[0.06] bg-surface/40 p-2">
      <div className="mb-1.5 flex items-center justify-between px-1">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
          Pulled files · {documents.length || sources.reduce((n, s) => n + s.file_count, 0)} · {sources.length} source{sources.length === 1 ? '' : 's'}
        </p>
        {irrelevantCount > 0 && onRemoveIrrelevant && (
          <button type="button" onClick={onRemoveIrrelevant} className="text-[10px] text-amber-400 hover:text-amber-300">
            Remove irrelevant
          </button>
        )}
      </div>

      <div className="max-h-72 space-y-1 overflow-y-auto">
        {sources.map((src) => {
          const open = openSources.has(src.source_id);
          return (
            <div key={src.source_id} className="rounded-md border border-white/[0.04] bg-white/[0.02]">
              <button
                type="button"
                onClick={() => toggleSource(src.source_id)}
                className="flex w-full items-center gap-2 px-2 py-1.5 text-left"
              >
                {open ? <ChevronDown className="h-3 w-3 text-slate-500" /> : <ChevronRight className="h-3 w-3 text-slate-500" />}
                <ConnectorLogo sourceId={src.source_id} name={src.label} size={14} />
                <span className="min-w-0 flex-1 truncate text-[11px] font-medium text-slate-200">{src.label}</span>
                <span className="shrink-0 text-[9px] text-slate-500">{src.file_count}</span>
              </button>
              {open && (
                <div className="space-y-0.5 border-t border-white/[0.04] px-1 pb-1.5 pt-1">
                  {src.directories.map((dir) => {
                    const dirKey = `${src.source_id}::${dir.path}`;
                    const dirOpen = openDirs.has(dirKey);
                    const folderLabel = dir.path ? dir.path : '/';
                    return (
                      <div key={dirKey}>
                        <button
                          type="button"
                          onClick={() => toggleDir(dirKey)}
                          className="flex w-full items-center gap-1.5 rounded px-2 py-1 text-left hover:bg-white/[0.03]"
                        >
                          {dirOpen ? <ChevronDown className="h-3 w-3 text-slate-600" /> : <ChevronRight className="h-3 w-3 text-slate-600" />}
                          <FolderOpen className="h-3 w-3 text-amber-400/80" />
                          <span className="min-w-0 flex-1 truncate font-mono text-[10px] text-slate-400">{folderLabel}</span>
                          <span className="text-[9px] text-slate-600">{dir.file_count}</span>
                        </button>
                        {dirOpen && (
                          <ul className="ml-5 space-y-0.5 border-l border-white/[0.06] pl-2">
                            {(dir.files || []).map((doc) => {
                              const rel = relevanceByName[doc.filename];
                              const bad = rel && rel.relevant === false;
                              return (
                                <li key={doc.doc_id} className={`group flex items-center gap-1.5 rounded px-1.5 py-1 ${bad ? 'bg-amber-500/10' : 'hover:bg-white/[0.03]'}`}>
                                  {bad ? <AlertTriangle className="h-3 w-3 shrink-0 text-amber-400" /> : <FileText className="h-3 w-3 shrink-0 text-insurance" />}
                                  <button
                                    type="button"
                                    onClick={() => openPreview(doc)}
                                    className="min-w-0 flex-1 truncate text-left text-[11px] text-slate-300 hover:text-white"
                                    title={doc.path || doc.filename}
                                  >
                                    {doc.filename}
                                  </button>
                                  <span className={`shrink-0 text-[9px] ${bad ? 'text-amber-400' : 'text-slate-600'}`}>
                                    {bad ? 'irrelevant' : formatBytes(doc.size_bytes)}
                                  </span>
                                  <button
                                    type="button"
                                    onClick={() => openPreview(doc)}
                                    className="shrink-0 text-slate-600 opacity-0 transition hover:text-brand group-hover:opacity-100"
                                    title="Preview"
                                  >
                                    <Eye className="h-3 w-3" />
                                  </button>
                                  {onRemove && (
                                    <button
                                      type="button"
                                      onClick={() => onRemove(bundleId, doc.doc_id)}
                                      className="shrink-0 text-slate-600 opacity-0 transition hover:text-red-400 group-hover:opacity-100"
                                      title="Remove"
                                    >
                                      <X className="h-3 w-3" />
                                    </button>
                                  )}
                                </li>
                              );
                            })}
                          </ul>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {(preview || loadingPreview) && (
        <div className="mt-2 overflow-hidden rounded-lg border border-white/[0.08] bg-black/30">
          <div className="flex items-start justify-between gap-2 border-b border-white/[0.06] px-3 py-2">
            <div className="min-w-0">
              <p className="truncate text-xs font-medium text-slate-200">{preview?.filename || 'Preview'}</p>
              <p className="truncate font-mono text-[10px] text-slate-500">
                {(preview?.connection_label || preview?.source_id || '') + (preview?.path ? ` · ${preview.path}` : '')}
              </p>
            </div>
            <button type="button" onClick={() => setPreview(null)} className="text-slate-500 hover:text-slate-300">
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
          <div className="max-h-56 overflow-auto p-3">
            {loadingPreview && !preview?.content ? (
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading preview…
              </div>
            ) : preview?.previewable ? (
              <pre className="whitespace-pre-wrap break-words font-mono text-[11px] leading-relaxed text-slate-300">
                {preview.content || '(empty file)'}
                {preview.truncated ? '\n\n… truncated …' : ''}
              </pre>
            ) : (
              <p className="text-xs text-slate-400">{preview?.message || 'This file cannot be previewed.'}</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
