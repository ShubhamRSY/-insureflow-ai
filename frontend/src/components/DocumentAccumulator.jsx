import { useState } from 'react';
import { FileText, X, Package, Loader2, AlertCircle } from 'lucide-react';

/**
 * DocumentAccumulator — persistent document list that survives source switches.
 *
 * Shows all accumulated documents across multiple source pulls, grouped by source.
 * Each document has a remove button. The total is always visible so the user
 * knows what they're about to submit to the pipeline.
 */
export default function DocumentAccumulator({
  bundleId,
  documents = [],
  onRemove,
  onRunPipeline,
  onClearAll,
  loading = false,
  useLlm = true,
  onToggleLlm,
}) {
  const [running, setRunning] = useState(false);

  if (!bundleId || documents.length === 0) return null;

  // Group documents by source
  const grouped = {};
  for (const doc of documents) {
    const key = doc.source_id || 'unknown';
    if (!grouped[key]) {
      grouped[key] = { label: doc.connection_label || doc.source_id || 'Unknown', docs: [] };
    }
    grouped[key].docs.push(doc);
  }

  const handleRun = async () => {
    setRunning(true);
    try {
      await onRunPipeline?.(bundleId, useLlm);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="rounded-xl border border-brand/20 bg-brand/5 p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Package className="h-4 w-4 text-brand" />
          <p className="text-sm font-semibold text-slate-200">
            {documents.length} document{documents.length !== 1 ? 's' : ''} accumulated
          </p>
          <span className="rounded-full bg-brand/15 px-2 py-0.5 text-[10px] font-semibold text-brand">
            Multi-source
          </span>
        </div>
        {onClearAll && (
          <button
            type="button"
            onClick={() => onClearAll(bundleId)}
            className="text-[11px] text-red-400/70 hover:text-red-400 transition"
          >
            Clear all
          </button>
        )}
      </div>

      {/* Grouped documents */}
      <div className="space-y-3">
        {Object.entries(grouped).map(([sourceKey, { label, docs }]) => (
          <div key={sourceKey}>
            <div className="flex items-center gap-1.5 mb-1.5">
              <div className="h-px flex-1 bg-white/[0.06]" />
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 shrink-0">
                {label}
              </span>
              <div className="h-px flex-1 bg-white/[0.06]" />
            </div>
            <ul className="space-y-1">
              {docs.map((doc) => (
                <li
                  key={doc.doc_id}
                  className="flex items-center gap-2 rounded-lg bg-white/[0.02] px-3 py-2 group"
                >
                  <FileText className="h-3.5 w-3.5 shrink-0 text-insurance" />
                  <span className="truncate text-xs text-slate-300 flex-1">{doc.filename}</span>
                  {onRemove && (
                    <button
                      type="button"
                      onClick={() => onRemove(bundleId, doc.doc_id)}
                      className="opacity-0 group-hover:opacity-100 text-slate-600 hover:text-red-400 transition"
                      title="Remove document"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between border-t border-white/[0.06] pt-3">
        <label className="flex items-center gap-2 text-sm text-slate-400">
          <input
            type="checkbox"
            checked={useLlm}
            onChange={(e) => onToggleLlm?.(e.target.checked)}
            className="rounded"
          />
          LLM enhancement
        </label>
        <button
          type="button"
          onClick={handleRun}
          disabled={loading || running || documents.length === 0}
          className="btn-primary"
        >
          {loading || running ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Submitting…
            </>
          ) : (
            `Run pipeline (${documents.length} docs)`
          )}
        </button>
      </div>

      {documents.length === 0 && (
        <div className="flex items-center gap-2 text-xs text-amber-400/70">
          <AlertCircle className="h-3.5 w-3.5" />
          Add documents from one or more sources before running the pipeline.
        </div>
      )}
    </div>
  );
}
