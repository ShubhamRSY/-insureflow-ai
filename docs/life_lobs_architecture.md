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

## Reference implementation (LOB 1–7) — complete

```
src/insureflow/life/lobs/
├── base.py                     # plumbing ONLY: context, outcome, QuoteResult conversion
├── actuarial.py                # rule-free math: ä_{x:n}, A^1, endowments, J&S factors
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
├── whole_life/                 # LOB 2 — 7 sub-product paths
│   ├── ordinary_whole.py       #   Guaranteed / Ordinary Whole Life  (A_x/ä_x)
│   ├── limited_pay.py          #   10-Pay · 20-Pay · Paid-Up-at-65   (ä_{x:n})
│   ├── single_premium.py       #   Lump-Sum · Immediate Cash Value   (NSP = A_x)
│   ├── participating.py        #   Dividend Cash Option · PUA        (+dividend load)
│   ├── non_participating.py    #   Non-Par Whole Life · Paid-Up at 65
│   ├── modified.py             #   Modified Step-Up · Modified 5/10  (premium schedule)
│   └── graded.py               #   Graded Benefit · Guaranteed Issue (no-exam GI gates)
├── universal_life/             # LOB 3 — 4 sub-product paths (actuarial basis)
│   ├── guaranteed_universal_life.py   # No-Lapse Guarantee · GUL-to-120 (AV projection)
│   ├── indexed_universal_life.py      # Indexed/Fixed/Blend (floor-cap-participation)
│   ├── variable_universal_life.py     # Vx Account · FINRA gate · GMDB rider load
│   └── current_assumption_universal_life.py  # current vs guaranteed crediting columns
├── endowment/                  # LOB 4 — 3 product paths
│   ├── pure_endowment.py       #   v^n·npx maturity only, NO death benefit
│   ├── full_endowment.py       #   mixed endowment + illustrated reversionary bonus
│   └── guaranteed_fixed_endowment.py # fully guaranteed values, carrier bears risk
├── ulip/                       # LOB 5 — 6 product paths (unit-linked)
│   ├── single_premium_ulip.py  #   statutory SA multiple, 5-year lock-in
│   ├── regular_premium_ulip.py #   10×/7× multiple rule + dual-track suitability UW
│   ├── ulip_type_i.py          #   DB = max(SA, FV) — COI on nominal SA
│   ├── ulip_type_ii.py         #   DB = SA + FV — extra mortality load
│   ├── pension_ulip.py         #   vesting age + mandatory ≥2/3 annuitization
│   └── child_ulip.py           #   proposer-owned, WP rider, milestone vesting
├── money_back/                 # LOB 6 — 3 product paths
│   ├── traditional_money_back.py     # survival coupons + full SA death cover
│   ├── with_profit_money_back.py     # same skeleton + illustrated bonuses
│   └── children_money_back.py        # milestone payouts, WP on proposer death
└── annuity/                    # LOB 7 — 9 payout paths (illustration only)
    ├── immediate_annuity.py    #   life income · 10-yr certain & life
    ├── deferred_annuity.py     #   accumulate → annuitize at vesting age
    ├── fixed_annuity.py        #   declared rate + surrender charge schedule
    ├── variable_annuity.py     #   AIR illustration + GMWB rider fee
    ├── indexed_annuity.py      #   participation/cap/floor crediting ladder
    ├── life_annuity.py         #   single life · cash-refund guarantee load
    ├── joint_survivor_annuity.py # J&S priced on joint survival (not flat %)
    ├── qlac.py                 #   IRS premium cap enforced inside the path
    └── structured_settlement_annuity.py  # schedule PV · qualified assignment
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

## Replicating the pattern (done for LOB 3–7)

LOB 3–7 followed exactly this recipe, so it remains the template for any new
Life product family:

1. Create `src/insureflow/life/lobs/<lob>/__init__.py` exporting `<LOB>_LOGIC_PATHS`.
2. One module per product: constants → `DEFAULT_STATE_RULES`/`STATE_RULES` →
   `underwrite_<product>(ctx) -> LobOutcome` → `build_quote(ctx) -> QuoteResult`.
3. Register the product ids in `PRODUCT_LOGIC_PATHS`.
4. Add tests mirroring `tests/test_life_lobs.py`: one ordering/economics test,
   one state-rules-inside-path test, one eligibility-gate test per product.
5. Stamp catalog entries automatically (already handled by the registry loop).

Family-specific conventions established during the LOB 3–7 build:

- **Universal Life / Endowment / Money-Back**: priced on actuarial equivalence
  (`compute_full_whole_life_quote`, `endowment_insurance_nsp`, coupon PVs) —
  every path ends `eligible = False` ("illustrative only, no filed rates").
- **ULIP**: `finish_quote(..., apply_minimum_premium=False)`; SA-multiple and
  lock-in rules enforced inside each module.
- **Annuity**: consideration-based (`purchase_price(ctx)`), `adjusted_premium = 0`,
  payouts live in metadata; `rate_life` moved its face-amount gate BELOW the LOB
  dispatch so annuity paths own their gates. Unregistered annuity text falls back
  to the generic illustration (`annuity_rating.rate_annuity`).

## Why this beats the two extremes (record for future reviewers)

- **Fully config-driven**: fast to add nodes, but underwriting nuance (why a
  graded policy ignores medical declines while credit life caps face instead)
  ends up buried in opaque rule rows; non-technical review becomes impossible.
- **Fully separate engines per LOB**: duplicates document packs, memo formats,
  and API contracts that are genuinely shared.
- **This model**: shared *plumbing* only; every rule lives visibly in the one
  place that owns it. Adding a coverage = adding an explicit branch in its
  product module, never touching other products.

## Platform state-law layer (51 jurisdictions)

`lobs/state_law.py` is the single source of truth for state consumer-protection
and sales-process law; `merge_state_rules` (base.py) layers it into every
product path: carrier `DEFAULT_STATE_RULES` ← canonical law row ← module
`STATE_RULES`. Each merged row stamps `source` and `rule_layer` so reviewers
can see which level set each value.

- **Free look**: separate life and annuity tables with real statutory values
  (e.g. CA 30d life / 30d annuity, FL 14d life / 21d annuity, CT 10d statute
  §38a-436); annuity replacement extensions and senior extensions
  (AZ 65+, CA 60+ per §10127.10) layered on top.
- **Community property**: spousal consent required on annuity elections in all
  nine CP states (module-layer rows).
- **Sales-process regimes** (`apply_platform_state_law`, called from
  `finish_quote` so no path can forget them): NY Reg 187 documented-suitability
  conditions on ALL NY life/annuity quotes; NAIC Model #275 Best Interest
  four-obligation condition on annuities in the 49 adopting states (NY, DC are
  legacy-suitability holdouts).
- **Guaranty-fund caps**: death/cash-value/annuity-PV/aggregate caps per state
  incl. CA 80% coinsurance — stamped as `metadata["guaranty_protection"]`
  family-appropriately.
- **Grace period & claims settlement interest**: per-state days and
  accrual-anchor rules stamped in metadata.
- **Annuity premium tax**: computed against purchase consideration for taxed
  states (CA 2.35%, NV 3.5%, SD tiered, FL 1% pass-through credit, …) —
  `metadata["premium_tax"]`.
- **Pricing relativities** stay in `life_rate_manual.json`: only genuinely
  filed states appear in `state_relativities` (presence there drives the
  state-of-filing gate); `relativity_basis` records filing status for all 51.
