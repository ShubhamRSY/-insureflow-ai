import { describe, it, expect } from 'vitest';
import { safeHttpUrl } from './safeUrl';

describe('safeHttpUrl', () => {
  it('keeps http and https links', () => {
    expect(safeHttpUrl('https://rytera.ai')).toBe('https://rytera.ai');
    expect(safeHttpUrl(' HTTP://example.com/a ')).toBe('HTTP://example.com/a');
  });
  it('drops every other scheme and non-strings', () => {
    for (const bad of ['javascript:alert(1)', ' JavaScript:alert(1)', 'data:text/html,x', 'vbscript:x', '//evil.com', 'example.com', '', null, undefined, 42]) {
      expect(safeHttpUrl(bad)).toBeNull();
    }
  });
});
