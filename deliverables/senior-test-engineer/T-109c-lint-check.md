# T-109c — "Test the test": lint scorer check, run on T-108 gold (D-116 item 5)

- Author: orchestrator session for @senior-test-engineer, 2026-10-19. Read-only: no pipeline run, no model call, no gold or score file changed.
- Tool: `deliverables/senior-test-engineer/lint_holdout.py` (extended). Self-check `--self-check`: PASS (includes: a blind loss-run mark is caught; a card with no valued-as-of line fails under v8; v7 on a D-116 card gives the perfect answer a loss-run miss, the B-435 defect).
- Data: T-108 gold SUB-206–237. Development data since D-115, so this is a check of the lint, not hold-out evidence.

## What the lint now does before any freeze

1. (a) A perfect answer is built from each gold card and scored by the scorer itself (`score_report`; a frozen scorer is fed through its own `score_one` with the pipeline call answered by the report). No mark may be "miss" or "call_failed" ("not_credited", the scorer's own null-where-gold-says-missing rule, is allowed). The perfect set must pass the route gate and the P-055 gate with 0 false completes.
2. (b) Deliberately wrong answers, each must be caught: one per field on every in-scope file (9 fields + conflict, status, route → that mark is "miss"), two leaks on every out-of-scope file (answered as in scope; manual intake with a value shown → leak, P-055 gate FAIL), and an unsafe route (carrier_a where gold says senior_referral or no_match → counted unsafe, route gate FAIL).
3. A gold card the scorer cannot read is a FAIL. Exit 1 on any failure blocks the freeze.

## Result 1 — T-108 gold as written, scorer v8: FAIL (15), freeze blocked

All 15 failures are the same: in-scope cards with a dated loss run have no `- Loss runs valued as of:` line (v8 reads only that line). Output: `T-109c-lint-T-108-as-written.txt`. The other 17 cards pass (a) and (b).

## Result 2 — temp copy with the valued-as-of line added mechanically: FAIL (10)

The line was copied from the "valued as of / valuation date <date>" phrase of each `Loss runs` line (19 cards, 13 of them the in-scope cards of Result 1; temp copy only, D-069). Output: `T-109c-lint-T-108-with-valued-line.txt`. **Every deliberately wrong answer was caught (0 "not caught"); the unsafe route and leaks were caught.** The 10 remaining failures are gold lines the scorer cannot score as written, so even a perfect pipeline loses the mark:

| Finding | Files | Cause | Effect on the published T-108 v7 score |
|---|---|---|---|
| F1 conflict "none (…)" | SUB-210, 213, 218, 221, 224 | v7/v8 treat only an exact `Conflict: none` as no conflict; a note after it goes to the conflict-sides branch, which finds no sides → miss | **5 of the 10 published conflict misses** are this artifact (verified in `SUB-206-237-holdout-v7.json`). Not in the 9-field gate. |
| F2 "a.m."/"p.m." in an operations item | SUB-211 ("closes 11 p.m."), 222, 225 ("open until 2:00 a.m.") | the checklist splits clauses on "." and ":", so the item's words can never sit in one clause | SUB-222's operations "silent error" in the T-108 root cause is this, not model wording; SUB-211 partly |
| F3 "needs review" not at line start | SUB-216, 219 ("Carrier A layout but no valued-as-of date; needs review — …") | v7/v8 read review only when `Expected loss run` starts with it; v8 then demands a date line | v7 compared to the policy-period start; under v8 the card stops |

## What this means

- Freeze rule works: T-108 gold would not freeze under the new lint.
- F1–F3 are fixed either by gold convention (now written in `RUN-RULES.md`) or by a scorer change; a scorer change needs a new P-###. Backlog B-437.
- Published T-108 and earlier scores stay as published (D-020, D-115).
