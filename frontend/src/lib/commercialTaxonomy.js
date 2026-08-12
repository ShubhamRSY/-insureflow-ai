/** Helpers for commercial hub taxonomy (category → product → coverage). */

export function formatCategoryLabel(category, index) {
  const name = category?.name || '';
  return `${index + 1}. ${name.toUpperCase()}`;
}

export function resolveCommercialSelection(taxonomy, { categoryId, productId, coverageId }) {
  const cat = (taxonomy || []).find((c) => c.id === categoryId) || taxonomy?.[0];
  const product = (cat?.products || []).find((p) => p.id === productId) || cat?.products?.[0];
  const coverages = product?.coverages || [];
  const coverage = coverages.find((c) => c.id === coverageId) || coverages[0] || null;

  return {
    categoryId: cat?.id || '',
    categoryName: cat?.name || '',
    productId: product?.id || '',
    productName: product?.name || '',
    productSlug: product?.slug || '',
    insurance_line: product?.insurance_line || '',
    checklist_lob: product?.checklist_lob || '',
    coverageId: coverage?.id || '',
    coverageName: coverage?.name || '',
    hasCoverages: coverages.length > 0,
    coverageRequired: coverages.length > 0,
  };
}

export function defaultCommercialSelection(taxonomy) {
  const cat = taxonomy?.[0];
  const product = cat?.products?.[0];
  const coverage = product?.coverages?.[0];
  return resolveCommercialSelection(taxonomy, {
    categoryId: cat?.id,
    productId: product?.id,
    coverageId: coverage?.id,
  });
}

export function commercialSelectionLabel(selection) {
  if (!selection?.productName) return '';
  const parts = [selection.categoryName, selection.productName];
  if (selection.coverageName) parts.push(selection.coverageName);
  return parts.filter(Boolean).join(' → ');
}

export function isCommercialSelectionComplete(selection) {
  if (!selection?.categoryId || !selection?.productId || !selection?.insurance_line) return false;
  if (selection.coverageRequired && !selection.coverageId) return false;
  return true;
}
