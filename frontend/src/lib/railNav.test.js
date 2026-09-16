import { describe, it, expect } from 'vitest';
import { RAIL_GROUPS, deriveActiveGroupId } from './railNav';

describe('RAIL_GROUPS', () => {
  it('has a home group with Overview and System health', () => {
    const home = RAIL_GROUPS.find((g) => g.id === 'home');
    expect(home).toBeDefined();
    expect(home.items.map((i) => i.to)).toEqual(['/', '/system']);
  });

  it('every group has a non-empty items array', () => {
    RAIL_GROUPS.forEach((g) => {
      expect(g.items.length).toBeGreaterThan(0);
    });
  });

  it('every group id is unique', () => {
    const ids = RAIL_GROUPS.map((g) => g.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
});

describe('deriveActiveGroupId', () => {
  it('matches the queue page to uw-operations', () => {
    expect(deriveActiveGroupId('/queue')).toBe('uw-operations');
  });

  it('matches a nested insurance route to the insurance group', () => {
    expect(deriveActiveGroupId('/insurance/life')).toBe('insurance');
  });

  it('falls back to home for an unmatched path', () => {
    expect(deriveActiveGroupId('/some/unknown/path')).toBe('home');
  });

  it('falls back to home for the root path', () => {
    expect(deriveActiveGroupId('/')).toBe('home');
  });

  it('picks the longest prefix match when two groups could both match', () => {
    const groups = [
      { id: 'short', items: [{ to: '/a', label: 'A' }] },
      { id: 'long', items: [{ to: '/a/b', label: 'AB' }] },
    ];
    expect(deriveActiveGroupId('/a/b/c', groups)).toBe('long');
  });
});
