import { insuranceLineLabel } from './insuranceLines';
import { displayText } from './safe';

export const STATUS_META = {
  processing: { label: 'Processing', status: 'processing' },
  completed: { label: 'Processed', status: 'completed' },
  failed: { label: 'Failed', status: 'failed' },
  appetite_check_failed: { label: 'Appetite Check Failed', status: 'appetite_check_failed' },
};

// Row-level status: the triage agent's "no_fit" tier means the submission
// never cleared the carrier's appetite in the first place — surfaced as its
// own status rather than lumped in with "processing", since it's a distinct
// outcome an underwriter would triage differently.
export function deriveStatus(priority, jobStatus) {
  if (priority === 'no_fit') return STATUS_META.appetite_check_failed;
  const raw = jobStatus || 'processing';
  return STATUS_META[raw] || { label: displayText(raw).replace(/_/g, ' '), status: raw };
}

// Normalizes a triage-queue item (insureflow.agents.triage_agent.TriageResult,
// via GET /pipeline/queue) plus its matching full job into one display row —
// shared by the Submission Queue page and the Insurance landing page's
// "Recent submissions" table so both render identical columns.
export function buildQueueRows(items, insuranceJobs) {
  return (items || []).map((item) => {
    const fullJob = insuranceJobs?.find(({ job }) => job?.results?.bundle_id === item.bundle_id)?.job;
    const results = fullJob?.results || {};
    const lob = results.commercial_product_name || results.commercial_coverage_name || results.insurance_line || '';
    return {
      bundleId: item.bundle_id,
      submissionId: item.bundle_id,
      insuredName: displayText(item.insured_name || results.insured_name, ''),
      priority: item.priority,
      score: item.score,
      lob: lob ? insuranceLineLabel(lob) : '',
      agency: displayText(results.broker_name, ''),
      statusMeta: deriveStatus(item.priority, fullJob?.status),
      assignee: results.assigned_to || '',
      fullJob,
    };
  });
}

// Normalizes a raw job list entry ({id, job}) into the same row shape when no
// triage-queue entry exists for it yet (e.g. still processing, or triage
// hasn't run) — priority/score are honestly left blank rather than guessed.
export function buildJobRow(entry, queueItemsByBundleId) {
  const job = entry.job || entry;
  const results = job?.results || {};
  const bundleId = results.bundle_id || entry.id;
  const queueItem = queueItemsByBundleId?.get(bundleId);
  const lob = results.commercial_product_name || results.commercial_coverage_name || results.insurance_line || entry.insurance_line || entry.product_line || '';
  return {
    bundleId: entry.id,
    submissionId: bundleId || entry.id,
    insuredName: displayText(entry.name || results.insured_name || entry.insured_name, ''),
    priority: queueItem?.priority || null,
    score: queueItem?.score ?? null,
    lob: lob ? insuranceLineLabel(lob) : '',
    agency: displayText(results.broker_name, ''),
    statusMeta: deriveStatus(queueItem?.priority, job?.status),
    assignee: results.assigned_to || '',
  };
}

export function queueItemsByBundleId(queueStats) {
  const map = new Map();
  for (const item of queueStats?.queue || []) map.set(item.bundle_id, item);
  return map;
}
