# Life LOB Architecture — Dedicated Logic Paths per LOB → Product → Coverage

## Decision (confirmed)

Do NOT build one generic config-driven engine. Each Line of Business, each
Product within it, and each Coverage option within that Product gets its own
explicit logic path in code. State rules are applied INSIDE each path — not
as a separate bolt-on layer — because compliance differs by state AND product
at the same time (Term Life + Connecticut executes term-life underwriting and
CT compliance together, in one pass).

This mirrors how underwriters actually work and keeps every decision
traceable to code a reviewer can read top-to-bottom.

## Reference implementation (LOB 1 + LOB 2) — complete

```
src/insureflow/life/lobs/
├── base.py                     # plumbing ONLY: context, outcome, QuoteResult conversion
├── term_life/                  # LOB 1 — 9 product paths
│   ├── level_term.py           #   10/15/20/25/30-Year Level Term
│   ├── decreasing_term.py      #   Mortgage Protection Term · Debt-Reducing Term
│   ├── mortgage_life.py        #   Mortgage Balance Protection · Lender-Assigned Benefit
│   ├── increasing_term.py      #   CPI-Linked Increasing · Step-Up Increasing
│   ├── renewable_term.py       #   Renewable Term · Annual Renewable Style
│   ├── convertible_term.py     #   Conversion window · Convert-to-Permanent
│   ├── rop_term.py             #   Full Return of Premium · Partial Return
│   ├── group_term.py           #   Basic · Supplemental · Dependent Group Life
│   └── credit_life.py          #   Outstanding Balance · Simplified Issue Credit Life
└── whole_life/                 # LOB 2 — 7 sub-product paths
    ├── ordinary_whole.py       #   Guaranteed / Ordinary Whole Life  (A_x/ä_x)
    ├── limited_pay.py          #   10-Pay · 20-Pay · Paid-Up-at-65   (ä_{x:n})
    ├── single_premium.py       #   Lump-Sum · Immediate Cash Value   (NSP = A_x)
    ├── participating.py        #   Dividend Cash Option · PUA        (+dividend load)
    ├── non_participating.py    #   Non-Par Whole Life · Paid-Up at 65
    ├── modified.py             #   Modified Step-Up · Modified 5/10  (premium schedule)
    └── graded.py               #   Graded Benefit · Guaranteed Issue (no-exam GI gates)
```

### What "own logic path" means per module

Every product module contains, explicitly:

| Element | Where in the module | Example |
|---|---|---|
| Issue-age gates | constants at top | `MIN_ISSUE_AGE = 18`, `MAX_ISSUE_AGE = 80` |
| State-rule table | `DEFAULT_STATE_RULES` + `STATE_RULES[state]` | CT free-look 30 days, paramed threshold $100K |
| Underwriting rules | inside `underwrite_*(ctx)` | group life never auto-declines on medical — EOI condition instead |
| Rating math | same function | ROP: level mortality × `full_rop_load` 1.45 |
| Coverage variants | explicit branches per coverage id | limited-pay: `_pay_period()` → 10 / 20 / 65−age |
| Conditions & disclosures | appended into the outcome | graded-benefit acknowledgment, MEC notice |
| Actuarial basis | direct formula calls | `compute_full_whole_life_quote(premium_term=10)` |

`base.py` is deliberately rule-free: it carries the context (`LifeProductContext`),
the outcome envelope (`LobOutcome`), the QuoteResult contract, and three tiny
numeric utilities (class factor, band factor, state relativity). No routing of
rules through configuration tables — duplication across modules is intentional
and auditable.

### How state rules act inside a path

```
ctx.issue_state ("CT")
        │
        ▼
merge_state_rules(ctx, DEFAULT_STATE_RULES, STATE_RULES)
        │   ← state row overrides carrier defaults; stamps issue_state + source
        ▼
applied INSIDE the underwriting/rating decisions of this path
(free-look condition, exam threshold gate, disclosures, projected-face caps…)
        │
        ▼
outcome.metadata["state_rules_applied"] = {…}   ← audit stamp on every quote
```

The platform-wide filing gate is re-applied inside each path via
`apply_state_filing_gate()`: a quote priced on the IL pilot exhibit is marked
ineligible when the selected state has no filed rates for that family — with
the reason recorded on the quote itself.

## Wiring

- UI/API selection (`life_product_id`, `life_coverage_id`) already flows through
  `pipeline.run()` → `rating.quote(commercial_product_id=…, commercial_coverage_id=…)`
  → `rate_life(product_id=…, coverage_id=…)`.
- `rate_life` first tries the dedicated path registry (`life.lobs.run_product_logic`);
  unregistered combinations fall back to generic family classification pricing.
- The catalog (`insurance/life_lobs.py`) is now self-describing: every Term/Whole
  product node and coverage node carries its `logic_path`.

## Replicating for LOB 3–7

When Universal Life / Endowment / ULIP / Money-Back / Annuity taxonomies are
defined, follow exactly this recipe:

1. Create `src/insureflow/life/lobs/<lob>/__init__.py` exporting `<LOB>_LOGIC_PATHS`.
2. One module per product: constants → `DEFAULT_STATE_RULES`/`STATE_RULES` →
   `underwrite_<product>(ctx) -> LobOutcome` → `build_quote(ctx) -> QuoteResult`.
3. Register the product ids in `PRODUCT_LOGIC_PATHS`.
4. Add tests mirroring `tests/test_life_lobs.py`: one ordering/economics test,
   one state-rules-inside-path test, one eligibility-gate test per product.
5. Stamp catalog entries automatically (already handled by the registry loop).

## Why this beats the two extremes (record for future reviewers)

- **Fully config-driven**: fast to add nodes, but underwriting nuance (why a
  graded policy ignores medical declines while credit life caps face instead)
  ends up buried in opaque rule rows; non-technical review becomes impossible.
- **Fully separate engines per LOB**: duplicates document packs, memo formats,
  and API contracts that are genuinely shared.
- **This model**: shared *plumbing* only; every rule lives visibly in the one
  place that owns it. Adding a coverage = adding an explicit branch in its
  product module, never touching other products.
