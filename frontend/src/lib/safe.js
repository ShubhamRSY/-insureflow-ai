/** Coerce API payloads that should be arrays (strings/objects from LLM dumps). */
export function asList(value) {
  if (Array.isArray(value)) return value;
  if (value == null || value === '') return [];
  if (typeof value === 'string') return [value];
  return [];
}

/** Safe text for React children — objects are not valid as a React child. */
export function displayText(value, fallback = '') {
  if (value == null || value === '') return fallback;
  const t = typeof value;
  if (t === 'string' || t === 'number' || t === 'boolean') return String(value);
  if (Array.isArray(value)) return value.map((v) => displayText(v)).filter(Boolean).join(', ') || fallback;
  if (t === 'object') {
    return displayText(
      value.title
        || value.label
        || value.text
        || value.message
        || value.reason
        || value.summary
        || value.value
        || value.name
        || value.action,
      fallback,
    );
  }
  return fallback;
}

/** Safe .toLowerCase() — objects/numbers from API dumps must not throw. */
export function safeLower(value, fallback = '') {
  return displayText(value, fallback).toLowerCase();
}

export function fmtFixed(value, digits = 1) {
  const n = Number(value);
  if (!Number.isFinite(n)) return null;
  return n.toFixed(digits);
}

export function asBBox(value) {
  if (!Array.isArray(value) || value.length < 2) return null;
  const nums = value.map(Number);
  if (nums.some((n) => !Number.isFinite(n))) return null;
  return nums;
}
