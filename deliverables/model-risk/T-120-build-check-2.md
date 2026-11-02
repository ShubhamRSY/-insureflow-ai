# T-120 build check 2 (look-again, D-129): SUB-450 to SUB-481, before the gold freeze
- Reviewer: @model-risk (independent). Date: 2026-10-27. Worktree `insureflow-integration`, branch pilot-integration, commit 4fa5d23. Earlier check: `T-120-build-check.md` (BLOCK, H1).
- Scope: H1 closure and any new High from `git diff 1aea7e4 4fa5d23` (rebuild of SUB-454/455/464/465/468/469, their gold, lint run 3). High only in detail (D-129).
- Not run, not scored. No pipeline, no model call. Only pure functions of frozen v11 were called (`ops_items_hit`, `answer_classes`, `_slots`). The builder and lint were re-run in a scratch copy only.

## Verdict: APPROVE (build and gold, for the gold freeze). H1 is closed and the fixes add no new High.
This approves the build and the gold only. It is not a production approval; the T-027 veto stands. The freeze still needs the items in "Before the freeze" below.

## What I recomputed
- **Freeze intact:** v11 `7ddcfb50…`, lint `01147a75…` and `count_ops_gate.py` `f942010d…` match NEXT-SESSION.md. Nothing changed under `underwriting_pipeline/` or `src/` from 1aea7e4 to 4fa5d23.
- **Rebuild:** I ran the builder at 4fa5d23 in a scratch directory. All 32 folders (SUB-450–481) are byte-identical to `simulation/inbox`.
- **Lint run 3:** I re-ran it and got output identical to `T-120-lint.txt`. It fails only on the declared D-128 marks for SUB-461/463, plus the SUB-468 undated info line.
- **Faithful-answer probe (all 20 in-scope cards):** each answer was the application's own operations line and cooking line, plus its line-of-business liquor words and any hours or seats the email states. It was fed to v11 `ops_items_hit` against the gold `Operations items` line. Result: **20/20 hit**.

| SUB | Before (H1) | Now: document wording → v11 | Result |
|---|---|---|---|
| 454 | "Electrical contracting, …, office and shop" read as {office} | "Electrical contractor, shop and yard" reads as {contractor}; the gold is {contractor} | hit (adding "six vans" still hits) |
| 464 | "Pub with full bar and kitchen" read as {bar_pub, office, restaurant} | the operations line is "Pub with full bar, ground floor; two office suites, second floor" and reads as {bar_pub, office}; fryer, flat-top and hood fill the slots | hit ("flat top" without the hyphen also hits) |
| 468 | "Convection ovens" read as no cooking slot | "Oven, panini press, espresso machine" plus "no liquor" (line of business) gives cooking=full and alcohol=none | hit |
| 469 | {wholesale, other_class} could never be produced | the gold is {wholesale}; "Wholesale auto parts, warehouse" reads as {wholesale}; adding the name "Tire Service" still reads as {wholesale} | hit |

- **Gold vs builder source, changed files (B-465):**
  - These match the builder on all six changed files: insured, sales, square footage, conflict sides, claim count, paid and open amounts, valued-as-of date, and route.
  - Each conflict is real in the source. 454 square footage: 3,200 on the application vs 2,450 in the email. 455 sales: $1,360,000 vs "$1.57 million". 469 square footage: 4,100 vs "3,600 square feet total". 464, 465 and 468 have no conflict, and the source shows none.
  - M1 is closed: the T-119/P-074 pair 1,240,000 / 1.42 million is gone from SUB-455. The only 1,240,000 left is SUB-458's building TIV, a different field with no words-for-amount case.
  - M2 is closed: the 469 email now gives a total.
- **Loss-run dates (M3 closed):**

| SUB | Claim | Date | Term | Valued |
|---|---|---|---|---|
| 464 | C-50612 | 2026-01-19 | 2025-12-03 to 2026-12-03 | 2026-08-21 |
| 465 | C-50734 | 2026-03-09 | 2025-12-12 to 2026-12-12 | 2026-07-15 |
| 454 | — | 2026-01-19 | 2025-11-01 to 2026-11-01 | 2026-05-26 |

  Each claim date falls inside its term and before the valued date, and every valued date is before the effective date. The email wording ("this winter", "this year") and the application claim year (2026) agree with the dates.
- **Routes vs written rules (changed files):**
  - 454 is R11 contractor: senior_referral, Carrier B suggested.
  - 455 and 469 are R17/P-053 wholesale: senior_referral, Carrier A suggested.
  - 464 is R2 under D-125: no market.
  - 465 is R1.
  - 468 is R9/R10: senior_referral, Carrier B.
  - All agree with the rules. C6 counts are unchanged in kind: 454, 455, 465 and 469 still have "None" lines and no cooking word, and 464 and 468 still state cooking.

## High
None open. H1 is closed for all four cards. No new High.

## Medium / Low (backlog, one line each)
- M5 (residual, not a gold error): the 464 email and sprinkler line still say "kitchen". The gold correctly excludes `restaurant` (operations-gold-rule §1: kitchen counts only "as the business"), but v11 reads any "kitchen" as restaurant. So an answer that carries the email's "kitchen … for pub food" misses. Declare it in the plan or the TASKS note as a known scorer ceiling, and if 464 misses, report it as a manual-review miss.
- M6: the gold items for restaurant cards (462, 467, 468) include "no liquor", which appears only in the line of business. A hit needs the answer to carry it. This is consistent with earlier hold-outs; say it in the write-up.
- L3 is still open from the first check: the D-128 exclusion for 461/463 needs @user's confirmation, and the gold manifest sha256 must be recorded before the freeze.
- M4 and L4 from the first check are unchanged (the write-up only).

## Before the freeze
Record the gold manifest sha256 and get @user's confirmation of the D-128 exclusion for 461/463 (L3). After that, no further changes to the build or the gold.
