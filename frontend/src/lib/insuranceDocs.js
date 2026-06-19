/** Client-side insurance document typing (mirrors server classifier). */

export const DOC_SLOTS = {
  acord_xml: {
    id: 'acord_xml',
    label: 'ACORD Application',
    required: true,
    accept: '.xml,application/xml,text/xml',
    hint: 'Standard broker application XML — the core submission form (required).',
  },
  loss_run: {
    id: 'loss_run',
    label: 'Loss Run',
    required: false,
    accept: '.pdf,.txt,.md,.xml,.json',
    hint: 'Claims history from the current/prior carrier: claim dates, amounts paid & incurred, loss ratio.',
  },
  schedule_of_values: {
    id: 'schedule_of_values',
    label: 'Schedule of Values (SOV)',
    required: false,
    accept: '.pdf,.txt,.md,.xlsx,.csv',
    hint: 'Property schedule listing each location/asset and its insured value (TIV, building limits).',
  },
  inspection_report: {
    id: 'inspection_report',
    label: 'Inspection Report',
    required: false,
    accept: '.pdf,.txt,.md',
    hint: 'Third-party property inspection — roof, sprinkler, occupancy, hazards.',
  },
  broker_slip: {
    id: 'broker_slip',
    label: 'Broker API / JSON',
    required: false,
    accept: '.json,.txt,.md',
    hint: 'Broker portal export or submission summary JSON from the wholesaler.',
  },
  supplemental: {
    id: 'supplemental',
    label: 'Other / PDF',
    required: false,
    accept: '.pdf,.png,.jpg,.jpeg,.txt,.md',
    hint: 'Additional PDFs or scans — OCR will extract text automatically.',
  },
};

const BINARY_EXT = new Set(['pdf', 'png', 'jpg', 'jpeg', 'tiff', 'bmp', 'tif']);

export function detectDocType(filename, textPreview = '') {
  const combined = `${filename}\n${textPreview}`.toLowerCase();
  if (filename.endsWith('.xml') || combined.includes('<acord') || combined.includes('acord xmlns')) {
    return 'acord_xml';
  }
  if (filename.endsWith('.json') || combined.includes('"submission"') || combined.includes('broker')) {
    return 'broker_slip';
  }
  if (combined.includes('loss run') || combined.includes('claims history') || combined.includes('total incurred') || /claim\s*#?\s*\d+/.test(combined)) {
    return 'loss_run';
  }
  if (combined.includes('schedule of values') || combined.includes('sov') || combined.includes('total insurable')) {
    return 'schedule_of_values';
  }
  if (combined.includes('inspection report') || combined.includes('property condition') || combined.includes('roof condition')) {
    return 'inspection_report';
  }
  return 'supplemental';
}

export async function readFileForUpload(file) {
  const ext = (file.name.split('.').pop() || '').toLowerCase();
  if (BINARY_EXT.has(ext)) {
    const dataUrl = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
    const base64 = String(dataUrl).split(',')[1] || '';
    return { filename: file.name, content: base64, encoding: 'base64' };
  }
  const text = await file.text();
  return { filename: file.name, content: text, encoding: 'utf-8' };
}

export function buildSubmissionPayload(files, useLlm = true) {
  const documents = files.map((f) => ({
    filename: f.filename,
    content: f.content,
    encoding: f.encoding,
  }));
  return { documents, use_llm: useLlm };
}

export function validatePackage(files) {
  const hasAcord = files.some((f) => f.slot === 'acord_xml');
  if (!hasAcord) {
    return 'Upload an ACORD XML application (required). Other documents are optional but improve the quote.';
  }
  return null;
}
