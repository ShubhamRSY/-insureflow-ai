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
