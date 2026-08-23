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
  // Truncated stored descriptions ("Top issue c…") — drop the fragment
  [/Top issue c[ode:s×\d ,]*…/g, ''],
  [/\(\s*(\d+) error\(s\), (\d+) warning\(s\)\./g, '($1 error(s), $2 warning(s)) — '],
  // Old next-step phrasing
  [/Verify external data or document synthetic\/unavailable check:/gi,
    'Confirm the external record was checked, or note why it was unavailable:'],
];

export function uwMemoText(text) {
  let t = String(text || '');
  // Translate known finding titles wherever they appear (bullets & next-steps)
  for (const [re, sub] of TITLE_REWRITES) {
    t = t.replace(new RegExp(re.source, 'gi'), sub);
  }
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

// ── Human-review reasons (Final Decision panel) ───────────────────────────────

const REASON_SUBS = [
  [/^Insufficient Data$/i, 'Application is missing key information — request outstanding items from the producer'],
  [/Zero-hallucination gate failed:\s*(\d+) uncited claim\(s\) \(max allowed \d+\)/i,
    '$1 figure(s) on the application could not be traced to supporting documents'],
  [/Extraction verification flagged (\d+) document\(s\)/i,
    '$1 document(s) could not be fully verified against source pages'],
  [/Critical oracle\(s\) unavailable:\s*(.+)/i,
    'External records could not be pulled (service unavailable): $1 — confirm manually or re-run'],
  [/Document quality gate blocked:\s*(\d+)/i,
    '$1 document(s) failed legibility/quality check — request clean copies from the producer'],
  [/Provenance\/reconciliation failure/i,
    'Values conflict across submitted documents — reconcile before relying on them'],
];

export function uwReason(reason) {
  let r = String(reason || '');
  r = uwTitle(r);
  r = uwDescription(r);
  for (const [re, sub] of REASON_SUBS) {
    if (re.test(r)) {
      r = r.replace(re, sub);
      break;
    }
  }
  return r.trim();
}

export function uwReasons(reasons) {
  const out = [];
  const seen = new Set();
  for (const raw of reasons || []) {
    const r = uwReason(raw);
    if (!r) continue;
    const key = r.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(r);
  }
  return out;
}

// ── Premium build-up step labels ──────────────────────────────────────────────

const PREMIUM_STEP_LABELS = {
  iso_base_loss_cost: 'Filed base loss cost',
  base_rate: 'Filed base rate',
  manual_rate: 'Manual rate',
  loss_cost_multiplier: 'Loss cost multiplier (expense & profit)',
  lcm: 'Loss cost multiplier (expense & profit)',
  state_relativity: 'State relativity',
  territory_relativity: 'Territory relativity',
  market_cycle_adjustment: 'Market-cycle adjustment',
  deductible_credit: 'Deductible credit',
  loss_experience: 'Loss experience (claims history)',
  years_in_business: 'Years in business credit',
  uw_schedule_modification: 'Underwriter schedule adjustment',
  schedule_modification: 'Property schedule adjustment',
  cope_schedule: 'Property schedule adjustment',
  commercial_checklist_mod: 'Commercial checklist adjustment',
  tobacco: 'Tobacco use adjustment',
  table_rating: 'Table rating (impaired risk)',
  flat_extra: 'Flat extra premium',
  policy_fee: 'Policy fee',
  rider_premium: 'Rider premium',
  medical_risk: 'Medical risk rating',
};

export function premiumStepLabel(step) {
  const raw = String(step || '').trim();
  if (!raw) return '—';
  const key = raw.toLowerCase();
  if (PREMIUM_STEP_LABELS[key]) return PREMIUM_STEP_LABELS[key];
  // territory_relativity_OH → Territory relativity (OH)
  const m = key.match(/^(territory_relativity)_(.+)$/);
  if (m) return `${PREMIUM_STEP_LABELS[m[1]]} (${m[2].toUpperCase()})`;
  // Generic snake_case → Title Case
  return raw
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
