# RAG Corpus: Life Insurance

Life Underwriting Guide · Version 3.0 · Effective 2026-01-01

## LOB metadata
- LOB slug: life
- Products: 41
- Categories: 7
- Standards: ACORD 100 series, MIB, HIPAA authorizations, NAIC model regs, IRC 7702 / 101(g)
- Underwriting authority: Field authority to $1M face / Table 2; above, or any flat extra > $5/$1,000, refers to the Life Chief Underwriter.

## How to use for RAG
- Index each `documents/<product>.md` as one or more chunks (split on the `##` sections).
- Bias retrieval to this LOB (or category) when the submission's line is known.
- The sections map to likely underwriter questions: eligibility, decline, documents, coverages, exclusions, limits, rating, authority.

## Categories

| id | name | summary |
|---|---|---|
| term | Term Life Insurance | Temporary coverage — level, decreasing (incl. mortgage), increasing, renewable, convertible, ROP, group, and credit life. |
| whole | Whole Life Insurance | Guaranteed permanent coverage — ordinary, limited-pay, single-premium, par, non-par, modified, and graded / guaranteed issue. |
| universal | Universal Life Insurance | Interest-sensitive permanent coverage — GUL, indexed (IUL), variable (VUL), and current assumption / adjustable. |
| endowment | Endowment Plans | Rare / largely discontinued in the US market — pure, with-profit, and guaranteed / fixed endowments. |
| ulip | Unit-Linked Insurance Plans (ULIPs) | US equivalent: variable universal life (VUL) — single / regular premium, Type I & II, pension, and child ULIPs. |
| money_back | Money-Back Policies | Rare in the US (closer to return-of-premium riders) — traditional, with-profit, and children's money-back plans. |
| annuity | Annuities / Pension Plans | Income and retirement products — immediate, deferred, fixed, variable, indexed, life, joint / survivor, QLAC, and structured settlements. |

## Product catalog

| product_id | name | category | status | docs | coverages | forms |
|---|---|---|---|---|---|---|
| level_term | Level Term Life Insurance | term | live | 9 | 5 | 1 |
| decreasing_term | Decreasing Term Life Insurance | term | live | 10 | 2 | 1 |
| mortgage_life | Mortgage Life Insurance | term | live | 11 | 2 | 1 |
| increasing_term | Increasing Term Life Insurance | term | live | 9 | 2 | 1 |
| renewable_term | Renewable Term Life Insurance | term | live | 10 | 2 | 1 |
| convertible_term | Convertible Term Life Insurance | term | live | 10 | 2 | 1 |
| rop_term | Return of Premium (ROP) Term Life Insurance | term | live | 10 | 2 | 1 |
| group_term_life | Group Term Life Insurance | term | live | 10 | 3 | 1 |
| credit_life | Credit Life Insurance | term | live | 12 | 2 | 1 |
| traditional_whole_life | Traditional / Ordinary Whole Life | whole | live | 11 | 2 | 1 |
| limited_pay_whole_life | Limited-Pay Whole Life (10-Pay, 20-Pay, etc.) | whole | live | 10 | 3 | 1 |
| single_premium_whole_life | Single-Premium Whole Life | whole | live | 11 | 2 | 1 |
| participating_whole_life | Participating (Par) Whole Life | whole | live | 10 | 2 | 1 |
| non_participating_whole_life | Non-Participating (Non-Par) Whole Life | whole | live | 9 | 2 | 1 |
| modified_whole_life | Modified Whole Life | whole | live | 10 | 2 | 1 |
| graded_guaranteed_issue_whole_life | Graded / Guaranteed Issue Whole Life | whole | live | 11 | 2 | 1 |
| guaranteed_universal_life | Guaranteed Universal Life (GUL) | universal | live | 10 | 2 | 1 |
| indexed_universal_life | Indexed Universal Life (IUL) | universal | live | 11 | 3 | 1 |
| variable_universal_life | Variable Universal Life (VUL) | universal | live | 13 | 3 | 1 |
| current_assumption_universal_life | Current Assumption / Adjustable Universal Life | universal | live | 10 | 2 | 1 |
| pure_endowment | Pure Endowment | endowment | live | 10 | 1 | 1 |
| full_endowment | Full / With-Profit Endowment | endowment | live | 11 | 1 | 1 |
| guaranteed_fixed_endowment | Guaranteed / Fixed Endowment | endowment | live | 10 | 1 | 1 |
| single_premium_ulip | Single Premium ULIP | ulip | live | 12 | 1 | 1 |
| regular_premium_ulip | Regular Premium ULIP | ulip | live | 12 | 1 | 1 |
| ulip_type_i | Type I ULIP (higher of sum assured or fund value) | ulip | live | 12 | 1 | 1 |
| ulip_type_ii | Type II ULIP (sum assured + fund value) | ulip | live | 12 | 1 | 1 |
| pension_ulip | Pension / Retirement ULIP | ulip | live | 12 | 1 | 1 |
| child_ulip | Child ULIP | ulip | live | 12 | 1 | 1 |
| traditional_money_back | Traditional Money-Back Policy | money_back | live | 10 | 1 | 1 |
| with_profit_money_back | With-Profit Money-Back Policy | money_back | live | 11 | 1 | 1 |
| children_money_back | Children's Money-Back Plan | money_back | live | 11 | 1 | 1 |
| immediate_annuity | Immediate Annuity | annuity | live | 12 | 2 | 1 |
| deferred_annuity | Deferred Annuity | annuity | live | 12 | 2 | 1 |
| fixed_annuity | Fixed Annuity | annuity | live | 12 | 2 | 1 |
| variable_annuity | Variable Annuity | annuity | live | 12 | 2 | 1 |
| indexed_annuity | Indexed Annuity | annuity | live | 11 | 2 | 1 |
| life_annuity | Life Annuity | annuity | live | 12 | 2 | 1 |
| joint_survivor_annuity | Joint Life / Survivor Annuity | annuity | live | 11 | 2 | 1 |
| qlac | Qualified Longevity Annuity Contract (QLAC) | annuity | live | 12 | 2 | 1 |
| structured_settlement_annuity | Structured Settlement Annuity | annuity | live | 11 | 2 | 1 |

## Product summaries

### level_term — Level Term Life Insurance
Guaranteed level premium and death benefit for a fixed term. Base set only — a paramedical exam is required above ~$100K–$250K (insurer-dependent).
- Full guide entry: `documents/level_term.md`

### decreasing_term — Decreasing Term Life Insurance
Death benefit declines over time — typically matches a mortgage or other declining debt balance.
- Full guide entry: `documents/decreasing_term.md`

### mortgage_life — Mortgage Life Insurance
Decreasing term tied to the mortgage so the balance is paid off if the insured dies.
- Full guide entry: `documents/mortgage_life.md`

### increasing_term — Increasing Term Life Insurance
Death benefit rises on a scheduled basis (often tracking CPI or a fixed annual percentage).
- Full guide entry: `documents/increasing_term.md`

### renewable_term — Renewable Term Life Insurance
Term coverage that renews at the end of each period without a new medical exam; premium rises with age.
- Full guide entry: `documents/renewable_term.md`

### convertible_term — Convertible Term Life Insurance
Term coverage convertible to permanent coverage without new medical underwriting during the conversion window.
- Full guide entry: `documents/convertible_term.md`

### rop_term — Return of Premium (ROP) Term Life Insurance
Level term that returns a portion or all premiums paid if the insured outlives the term.
- Full guide entry: `documents/rop_term.md`

### group_term_life — Group Term Life Insurance
Employer-sponsored term life typically 1x salary with supplemental buy-up options.
- Full guide entry: `documents/group_term_life.md`

### credit_life — Credit Life Insurance
Pays outstanding loan balance if the borrower dies — often declining term aligned to the debt.
- Full guide entry: `documents/credit_life.md`

### traditional_whole_life — Traditional / Ordinary Whole Life
Guaranteed permanent coverage with fixed premium and guaranteed cash value.
- Full guide entry: `documents/traditional_whole_life.md`

### limited_pay_whole_life — Limited-Pay Whole Life (10-Pay, 20-Pay, etc.)
Whole life fully paid up after a limited number of premium payments (e.g., 10 or 20 years).
- Full guide entry: `documents/limited_pay_whole_life.md`

### single_premium_whole_life — Single-Premium Whole Life
Whole life funded by one large lump-sum premium payment.
- Full guide entry: `documents/single_premium_whole_life.md`

### participating_whole_life — Participating (Par) Whole Life
Whole life that pays dividends to policyholders from insurer profits.
- Full guide entry: `documents/participating_whole_life.md`

### non_participating_whole_life — Non-Participating (Non-Par) Whole Life
Whole life with guaranteed values and no dividend participation.
- Full guide entry: `documents/non_participating_whole_life.md`

### modified_whole_life — Modified Whole Life
Whole life with lower early premiums that step up to a higher level after a set number of years.
- Full guide entry: `documents/modified_whole_life.md`

### graded_guaranteed_issue_whole_life — Graded / Guaranteed Issue Whole Life
Whole life with limited or no health questions and a graded death benefit in the first years.
- Full guide entry: `documents/graded_guaranteed_issue_whole_life.md`

### guaranteed_universal_life — Guaranteed Universal Life (GUL)
Universal life with a no-lapse guarantee — premium and death benefit guaranteed to a stated age or lifetime.
- Full guide entry: `documents/guaranteed_universal_life.md`

### indexed_universal_life — Indexed Universal Life (IUL)
Universal life whose cash value credits are linked to an equity index with a floor and cap.
- Full guide entry: `documents/indexed_universal_life.md`

### variable_universal_life — Variable Universal Life (VUL)
Universal life with cash value invested in sub-accounts (securities). Must be sold by an agent holding Series 6 or 7 plus an insurance license.
- Full guide entry: `documents/variable_universal_life.md`

### current_assumption_universal_life — Current Assumption / Adjustable Universal Life
Universal life with flexible premiums and an interest rate based on current market assumptions.
- Full guide entry: `documents/current_assumption_universal_life.md`

### pure_endowment — Pure Endowment
Pays the policy amount only at maturity (end of term) if the insured survives; rare / largely discontinued in the US.
- Full guide entry: `documents/pure_endowment.md`

### full_endowment — Full / With-Profit Endowment
Endowment paying the sum assured plus accumulated dividends / bonuses at maturity.
- Full guide entry: `documents/full_endowment.md`

### guaranteed_fixed_endowment — Guaranteed / Fixed Endowment
Endowment with guaranteed fixed returns payable at maturity.
- Full guide entry: `documents/guaranteed_fixed_endowment.md`

### single_premium_ulip — Single Premium ULIP
Unit-linked plan funded by one lump-sum premium; the US equivalent is single-premium variable life.
- Full guide entry: `documents/single_premium_ulip.md`

### regular_premium_ulip — Regular Premium ULIP
Unit-linked plan funded by regular premiums; the US equivalent is flexible-premium variable universal life.
- Full guide entry: `documents/regular_premium_ulip.md`

### ulip_type_i — Type I ULIP (higher of sum assured or fund value)
Death benefit is the higher of the sum assured or the fund value.
- Full guide entry: `documents/ulip_type_i.md`

### ulip_type_ii — Type II ULIP (sum assured + fund value)
Death benefit is the sum assured plus the fund value.
- Full guide entry: `documents/ulip_type_ii.md`

### pension_ulip — Pension / Retirement ULIP
Unit-linked plan designed for retirement accumulation with tax advantages.
- Full guide entry: `documents/pension_ulip.md`

### child_ulip — Child ULIP
Unit-linked plan on a child with the parent / proposer paying premiums.
- Full guide entry: `documents/child_ulip.md`

### traditional_money_back — Traditional Money-Back Policy
Policy paying periodic survival benefits at stated milestones with full death benefit if the insured dies earlier.
- Full guide entry: `documents/traditional_money_back.md`

### with_profit_money_back — With-Profit Money-Back Policy
Money-back policy with an added dividend / bonus component.
- Full guide entry: `documents/with_profit_money_back.md`

### children_money_back — Children's Money-Back Plan
Money-back plan on a child with the parent / proposer paying premiums; payouts are timed to milestones.
- Full guide entry: `documents/children_money_back.md`

### immediate_annuity — Immediate Annuity
Converts a single lump sum into guaranteed income payments starting immediately (typically within one year).
- Full guide entry: `documents/immediate_annuity.md`

### deferred_annuity — Deferred Annuity
Accumulates money now for income payments that begin later.
- Full guide entry: `documents/deferred_annuity.md`

### fixed_annuity — Fixed Annuity
Annuity with guaranteed fixed interest and predictable income.
- Full guide entry: `documents/fixed_annuity.md`

### variable_annuity — Variable Annuity
Annuity with sub-account investment options; SEC-regulated security requiring Series 6 / 7 licensing.
- Full guide entry: `documents/variable_annuity.md`

### indexed_annuity — Indexed Annuity
Fixed-index annuity crediting interest linked to an equity index with a cap and floor.
- Full guide entry: `documents/indexed_annuity.md`

### life_annuity — Life Annuity
Annuity paying income for life — same requirements as an immediate annuity.
- Full guide entry: `documents/life_annuity.md`

### joint_survivor_annuity — Joint Life / Survivor Annuity
Annuity covering two lives, typically paying while either annuitant is alive.
- Full guide entry: `documents/joint_survivor_annuity.md`

### qlac — Qualified Longevity Annuity Contract (QLAC)
Deferred income annuity funded from a qualified retirement account, starting at an advanced age.
- Full guide entry: `documents/qlac.md`

### structured_settlement_annuity — Structured Settlement Annuity
Annuity funding periodic payments under a legal settlement, typically for personal-injury awards.
- Full guide entry: `documents/structured_settlement_annuity.md`
