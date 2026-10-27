/** Returns the URL only when it is http(s); anything else (javascript:, data:, relative) gives null, so no link is rendered. */
export function safeHttpUrl(value) {
  if (typeof value !== 'string') return null;
  const url = value.trim();
  return /^https?:\/\/[^\s]+$/i.test(url) ? url : null;
}
