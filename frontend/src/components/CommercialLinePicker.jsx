import { useMemo } from 'react';
import { formatCategoryLabel, resolveCommercialSelection } from '../lib/commercialTaxonomy';
import { UI_HINTS } from '../lib/uiHints';
import { Hint } from './ui';

/**
 * Cascading picker: Category → Product → Coverage (matches commercial LOB taxonomy).
 */
export default function CommercialLinePicker({ taxonomy = [], value, onChange, disabled = false }) {
  const selection = useMemo(
    () => resolveCommercialSelection(taxonomy, value || {}),
    [taxonomy, value],
  );

  const activeCategory = useMemo(
    () => (taxonomy || []).find((c) => c.id === selection.categoryId),
    [taxonomy, selection.categoryId],
  );

  const products = activeCategory?.products || [];
  const activeProduct = products.find((p) => p.id === selection.productId) || products[0];
  const coverages = activeProduct?.coverages || [];

  const emit = (patch) => {
    onChange?.(resolveCommercialSelection(taxonomy, {
      categoryId: patch.categoryId ?? selection.categoryId,
      productId: patch.productId ?? selection.productId,
      coverageId: patch.coverageId ?? selection.coverageId,
    }));
  };

  const onCategoryChange = (categoryId) => {
    const cat = (taxonomy || []).find((c) => c.id === categoryId);
    const product = cat?.products?.[0];
    const coverage = product?.coverages?.[0];
    emit({ categoryId, productId: product?.id, coverageId: coverage?.id });
  };

  const onProductChange = (productId) => {
    const product = products.find((p) => p.id === productId);
    const coverage = product?.coverages?.[0];
    emit({ productId, coverageId: coverage?.id });
  };

  const onCoverageChange = (coverageId) => {
    emit({ coverageId });
  };

  if (!taxonomy?.length) {
    return null;
  }

  return (
    <div className="space-y-3 rounded-xl border border-white/[0.06] bg-surface/30 p-3">
      <div>
        <Hint text={UI_HINTS.commercialCategory}>
          <label htmlFor="commercial-category" className="hint-label mb-1 block cursor-help text-xs font-semibold uppercase tracking-wider text-slate-300">
            Line of business
          </label>
        </Hint>
        <select
          id="commercial-category"
          value={selection.categoryId}
          onChange={(e) => onCategoryChange(e.target.value)}
          disabled={disabled}
          className="input-field w-full text-sm"
          aria-label="Commercial insurance category"
        >
          {(taxonomy || []).map((cat, i) => (
            <option key={cat.id} value={cat.id}>{formatCategoryLabel(cat, i)}</option>
          ))}
        </select>
      </div>

      {products.length > 0 && (
        <div>
          <Hint text={UI_HINTS.commercialProduct}>
            <label htmlFor="commercial-product" className="hint-label mb-1 block cursor-help text-xs font-semibold uppercase tracking-wider text-slate-300">
              Product
            </label>
          </Hint>
          <select
            id="commercial-product"
            value={selection.productId}
            onChange={(e) => onProductChange(e.target.value)}
            disabled={disabled}
            className="input-field w-full text-sm"
            aria-label="Commercial insurance product"
          >
            {products.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>
      )}

      {coverages.length > 0 && (
        <div>
          <Hint text={UI_HINTS.commercialCoverage}>
            <label htmlFor="commercial-coverage" className="hint-label mb-1 block cursor-help text-xs font-semibold uppercase tracking-wider text-slate-300">
              Coverage
            </label>
          </Hint>
          <select
            id="commercial-coverage"
            value={selection.coverageId}
            onChange={(e) => onCoverageChange(e.target.value)}
            disabled={disabled}
            className="input-field w-full text-sm"
            aria-label="Commercial insurance coverage"
          >
            {coverages.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>
      )}

      {selection.productName && (
        <p className="text-xs leading-relaxed text-slate-400">
          Pipeline will run as{' '}
          <span className="text-slate-300">{selection.productName}</span>
          {selection.coverageName ? (
            <>
              {' '}·{' '}
              <span className="text-slate-300">{selection.coverageName}</span>
            </>
          ) : null}
        </p>
      )}
    </div>
  );
}
