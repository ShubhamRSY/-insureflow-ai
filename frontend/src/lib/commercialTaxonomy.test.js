import { describe, it, expect } from 'vitest';
import {
  formatCategoryLabel,
  resolveCommercialSelection,
  defaultCommercialSelection,
  commercialSelectionLabel,
  isCommercialSelectionComplete,
} from './commercialTaxonomy';

const sampleTaxonomy = [
  {
    id: 'life',
    name: 'Life',
    products: [
      {
        id: 'level_term',
        name: 'Level Term',
        slug: 'level-term',
        insurance_line: 'term_life',
        checklist_lob: 'term_life',
        coverages: [
          { id: '50k', name: '$50,000' },
          { id: '100k', name: '$100,000' },
        ],
      },
      {
        id: 'whole_life',
        name: 'Whole Life',
        slug: 'whole-life',
        insurance_line: 'whole_life',
        checklist_lob: 'whole_life',
        coverages: [],
      },
    ],
  },
  {
    id: 'health',
    name: 'Health',
    products: [
      {
        id: 'group_health',
        name: 'Group Health',
        slug: 'group-health',
        insurance_line: 'group_health',
        checklist_lob: 'group_health',
        coverages: [{ id: 'basic', name: 'Basic' }],
      },
    ],
  },
];

describe('formatCategoryLabel', () => {
  it('returns "1. NAME" format', () => {
    expect(formatCategoryLabel({ name: 'Life' }, 0)).toBe('1. LIFE');
  });

  it('uses zero-based index', () => {
    expect(formatCategoryLabel({ name: 'Health' }, 2)).toBe('3. HEALTH');
  });

  it('handles missing name gracefully', () => {
    expect(formatCategoryLabel({}, 0)).toBe('1. ');
  });

  it('handles null category', () => {
    expect(formatCategoryLabel(null, 0)).toBe('1. ');
  });
});

describe('resolveCommercialSelection', () => {
  it('resolves the first category/product/coverage by default', () => {
    const sel = resolveCommercialSelection(sampleTaxonomy, {});
    expect(sel.categoryId).toBe('life');
    expect(sel.productId).toBe('level_term');
    expect(sel.coverageId).toBe('50k');
    expect(sel.insurance_line).toBe('term_life');
  });

  it('resolves a specific category and product', () => {
    const sel = resolveCommercialSelection(sampleTaxonomy, {
      categoryId: 'health',
      productId: 'group_health',
    });
    expect(sel.categoryId).toBe('health');
    expect(sel.productId).toBe('group_health');
    expect(sel.coverageId).toBe('basic');
  });

  it('returns empty strings for empty taxonomy', () => {
    const sel = resolveCommercialSelection([], {});
    expect(sel.categoryId).toBe('');
    expect(sel.productId).toBe('');
    expect(sel.coverageId).toBe('');
  });

  it('returns empty strings for null taxonomy', () => {
    const sel = resolveCommercialSelection(null, {});
    expect(sel.categoryId).toBe('');
  });

  it('sets hasCoverages and coverageRequired based on coverages length', () => {
    const withCoverages = resolveCommercialSelection(sampleTaxonomy, {
      categoryId: 'life',
      productId: 'level_term',
    });
    expect(withCoverages.hasCoverages).toBe(true);
    expect(withCoverages.coverageRequired).toBe(true);

    const withoutCoverages = resolveCommercialSelection(sampleTaxonomy, {
      categoryId: 'life',
      productId: 'whole_life',
    });
    expect(withoutCoverages.hasCoverages).toBe(false);
    expect(withoutCoverages.coverageRequired).toBe(false);
  });

  it('selects a specific coverage when coverageId is provided', () => {
    const sel = resolveCommercialSelection(sampleTaxonomy, {
      categoryId: 'life',
      productId: 'level_term',
      coverageId: '100k',
    });
    expect(sel.coverageId).toBe('100k');
    expect(sel.coverageName).toBe('$100,000');
  });

  it('falls back to first coverage for unknown coverageId', () => {
    const sel = resolveCommercialSelection(sampleTaxonomy, {
      categoryId: 'life',
      productId: 'level_term',
      coverageId: 'unknown',
    });
    expect(sel.coverageId).toBe('50k');
  });
});

describe('defaultCommercialSelection', () => {
  it('returns the first category/product/coverage', () => {
    const sel = defaultCommercialSelection(sampleTaxonomy);
    expect(sel.categoryId).toBe('life');
    expect(sel.productId).toBe('level_term');
    expect(sel.coverageId).toBe('50k');
  });

  it('returns empty selection for empty taxonomy', () => {
    const sel = defaultCommercialSelection([]);
    expect(sel.categoryId).toBe('');
  });

  it('returns empty selection for null taxonomy', () => {
    const sel = defaultCommercialSelection(null);
    expect(sel.categoryId).toBe('');
  });
});

describe('commercialSelectionLabel', () => {
  it('joins category, product, and coverage with arrows', () => {
    const sel = resolveCommercialSelection(sampleTaxonomy, {
      categoryId: 'life',
      productId: 'level_term',
      coverageId: '50k',
    });
    expect(commercialSelectionLabel(sel)).toBe('Life → Level Term → $50,000');
  });

  it('omits coverage when not present', () => {
    const sel = resolveCommercialSelection(sampleTaxonomy, {
      categoryId: 'life',
      productId: 'whole_life',
    });
    expect(commercialSelectionLabel(sel)).toBe('Life → Whole Life');
  });

  it('returns empty string when no productName', () => {
    expect(commercialSelectionLabel({})).toBe('');
  });

  it('returns empty string for null selection', () => {
    expect(commercialSelectionLabel(null)).toBe('');
  });
});

describe('isCommercialSelectionComplete', () => {
  it('returns true when categoryId, productId, and insurance_line are present', () => {
    const sel = resolveCommercialSelection(sampleTaxonomy, {
      categoryId: 'life',
      productId: 'level_term',
      coverageId: '50k',
    });
    expect(isCommercialSelectionComplete(sel)).toBe(true);
  });

  it('returns false when categoryId is missing', () => {
    expect(isCommercialSelectionComplete({ productId: 'x', insurance_line: 'y' })).toBe(false);
  });

  it('returns false when productId is missing', () => {
    expect(isCommercialSelectionComplete({ categoryId: 'x', insurance_line: 'y' })).toBe(false);
  });

  it('returns false when insurance_line is missing', () => {
    expect(isCommercialSelectionComplete({ categoryId: 'x', productId: 'y' })).toBe(false);
  });

  it('returns false when coverageRequired but coverageId is missing', () => {
    expect(isCommercialSelectionComplete({
      categoryId: 'x',
      productId: 'y',
      insurance_line: 'z',
      coverageRequired: true,
      coverageId: '',
    })).toBe(false);
  });

  it('returns true when coverageRequired is false and coverageId is empty', () => {
    expect(isCommercialSelectionComplete({
      categoryId: 'x',
      productId: 'y',
      insurance_line: 'z',
      coverageRequired: false,
      coverageId: '',
    })).toBe(true);
  });

  it('returns false for null selection', () => {
    expect(isCommercialSelectionComplete(null)).toBe(false);
  });
});
