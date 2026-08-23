// Translates internal QA/engineering jargon into desk-ready underwriter language.
// Applied at render time so older stored jobs read correctly too.

const TITLE_REWRITES = [
  [/hallucination blocked\s*—\s*uncited claim/i, 'Unverified figure — supporting documentation required'],
  [/extraction verification failed\s*—\s*human review required/i, 'Application data could not be fully verified — manual review required'],
  [/mib no-hit \(uploaded codes absent\)/i, 'MIB check not performed — order bureau report'],
  [/ofac:\s*no named insured to screen/i, 'Sanctions screening incomplete — no named insured on file'],
];

const DESC_SUBS = [
  [/has no page\/bbox\/source citation\s*—\s*blocks STP; treat as hypothesis until grounded/gi,
    'cannot be traced to a page in the submitted documents — do not rely on this figure until supporting paperwork is received'],
  [/failed layered extraction verification with/gi, 'could not be fully verified against source pages ('],
  [/Top issue codes:/gi, 'Unverified items:'],
  [/Do not rely on extracted figures without review\.?/gi, 'Review against the original paperwork before relying on any figure.'],
  [/authorization alone is not a query\.?/gi,
    'a signed authorization alone is not a bureau search — order an MIB report before finalizing the class.'],
  [/Cannot run sanctions screening without a named insured \/ applicant\.?/gi,
    'OFAC / AML screening could not be run because no named insured appears on the application. Obtain the full legal name and re-run screening.'],
  [/\bgrounded\b/gi, 'verified against paperwork'],
  [/\bungrounded\b/gi, 'unverified'],
];

export function uwTitle(title) {
  let t = String(title || '');
  for (const [re, sub] of TITLE_REWRITES) {
    if (re.test(t)) return t.replace(re, sub);
  }
  return t;
}

export function uwDescription(desc) {
  let d = String(desc || '');
  for (const [re, sub] of DESC_SUBS) {
    d = d.replace(re, sub);
  }
  return d;
}

export function uwFinding(finding = {}) {
  return {
    ...finding,
    title: uwTitle(finding.title),
    description: uwDescription(finding.description),
  };
}

// Humanize internal field keys embedded in stored text: "face_amount='750000'" → "Face amount of 750000",
// "spacy.amount='750000'" → "Stated amount of 750000".
const FIELD_KEY_RE = /([A-Za-z][\w-]*(?:\.[\w-]+)?(?:_[\w-]+)+|spacy\.amount)\s*=\s*'([^']*)'/g;

function humanizeFieldKey(key) {
  const base = String(key || '')
    .replace(/^(spacy|regex|llm|layoutlm|ocr)\./i, '')
    .replace(/_/g, ' ')
    .trim();
  return base.charAt(0).toUpperCase() + base.slice(1);
}

function rewriteFieldAssignments(text) {
  return text.replace(FIELD_KEY_RE, (_m, key, value) => `${humanizeFieldKey(key)} of ${value}`);
}

// Full-memo line-level rewrites for anything not covered above.
const MEMO_LINE_SUBS = [
  [/varied with CV ([\d.]+) across extraction passes \(> [\d.]+\); unstable value — route to human review/gi,
    'did not read consistently on repeated verification passes (values varied by roughly $1%) — figure is unreliable, route to manual review'],
  [/No loss run data available — Cannot analyze claims history — loss run not provided or empty/gi,
    'No loss runs on file — claims history cannot be analyzed. Request a 5-year loss run from the producer before finalizing the risk assessment'],
  [/No coverage data available — Cannot verify coverage adequacy without coverage data/gi,
    'No coverage schedule on file — coverage adequacy cannot be verified. Request the declarations page or current schedule of insurance from the producer'],
];

export function uwMemoText(text) {
  let t = String(text || '');
  t = uwDescription(t);
  t = rewriteFieldAssignments(t);
  for (const [re, sub] of MEMO_LINE_SUBS) {
    t = t.replace(re, sub);
  }
  // Strip leftover severity tags and the risk-score bookkeeping line
  t = t.replace(/\[(?:CRITICAL|HIGH|MODERATE|LOW|INFO)\]\s*/g, '');
  t = t.replace(/Risk score:\s*\d+\/100\s*·\s*\d+ findings?\s*\([^)]*\)\s*\.?\s*/g, '');
  return t;
}
