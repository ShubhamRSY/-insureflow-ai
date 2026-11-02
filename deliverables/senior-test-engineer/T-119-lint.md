# T-119 lint (scorer v11) - @senior-test-engineer, 2026-10-23

## Current result (run 3, after D-128 gold fixes): FAIL (2 failures, 1 info, 32 files)
- Same command; output overwritten in `T-119-lint.txt`. Hashes checked before run: lint `01147a75...ea653` ok; v11 `7ddcfb50...fcbb` ok. Nothing edited; not run for scoring (D-020).
- FAIL SUB-348/scorer (perfect answer marked miss on conflict): one of the two conflict marks D-128 declares unmeasurable under v11 (reported separately, excluded from the conflict rate, noted before the run). Expected, not a defect.
- FAIL SUB-349/scorer (same): the second D-128 unmeasurable mark. Expected, not a defect.
- No other FAIL. No real failure, no owner action. SUB-348 operations FAIL (run 1) is gone; SUB-344 passes. INFO SUB-350 undated as declared.
- Plan check: `T-119-plan.json` counts (routes 4/12/4, criteria 1:4 2:5 3:4 4:3, two-criteria 4, undated SUB-350) pass the lint's plan-vs-gold checks; no plan edit needed.
- Exit code is 1 because of these two declared marks, so the gate reads FAIL by the lint's own rule; the pass condition is D-128's exclusion, not a lint PASS.

## History
- Run 1: FAIL (3 failures) - detail below.
- Run 2 (lint-fix, after gold change): PASS. @model-risk blocked the gold as H1 (conflict lines made scorable by adding square-footage figures / '2025' needles; true lines not measured).
- Run 3: above.

## Run 1 detail
- Command: `.venv/bin/python deliverables/senior-test-engineer/lint_holdout.py deliverables/senior-test-engineer/T-119-plan.json --run-date 2026-10-23` -> `T-119-lint.txt` (unset LLM_*). Result: **FAIL (3 failures, 1 info, 32 files)**. Not run for scoring (D-020). Pipeline, model and scorer-on-submissions not run.
- sha256 checked before run: lint `01147a75...ea653` ok; v11 `7ddcfb50...fcbb` ok. Neither edited. No gold, inbox, simulation or eval file edited. (This lint has no --check-gold / --check-ops-gold flags; only PLAN.json, --run-date, --scorer, --self-check. Gold readability is checked by the scorer test in the same run.)
- Plan: ids 340-371, in 20 / out 12, criteria 1:4, 2:5, 3:4, 4:3, two_criteria 4, criterion_4 3, routes carrier_a 4 / senior_referral 12 / no_match 4, undated SUB-350.
- Plan fix on first run (owner: me, done): SUB-350 loss-runs.md is an owner letter dated 2026-09-29 with no valued/as-of line; lint failed it until declared in `undated_loss_runs`. Gold confirms no valued line. Now INFO.

## FAIL lines (all gold cards, owner @senior-underwriter; plan clean, no inbox-file failures)
1. SUB-348/scorer: perfect answer marked miss on operations (gold line not scorable as written). Likely cause: the card's notes name "stove top" and "flat grill", the scorer reads cooking=full from the answer (COOKING_FULL has grill/range) while the items hold no cooking item; reword or move those words out of what the perfect answer carries.
2. SUB-348/scorer: miss on conflict. The Conflict line has no digits, so `sides_stored` has no needle ("cooking: none (application...) vs stove top and flat grill (email...)").
3. SUB-349/scorer: miss on conflict, same cause (no digits in "cooking: none (application) vs yes (schedule) and griddle (email)").
Fix is the gold line (a figure or date the scorer can match, or another agreed reading from @head-of-underwriting); I do not edit v11 (frozen) or the cards.

## Mix vs gold (gold wins; plan follows gold)
- Mix gives no routes; gold: carrier_a 4, senior_referral 12, no_match 4 (SUB-358 no_match R8, not "light manufacturing" referral).
- Criteria: mix and gold agree (1:4, 2:5, 3:4, 4:3, two-criteria 4).
- Loss runs: mix said "owner's dated letter" SUB-350 and none SUB-359; gold and lint agree. SUB-350 is the only undated; 359 has no file.
- Gold differs from mix on class/route only: wholesale 345/350 and office lessors 346/347 referral, not direct; 352 pub R2; 355 two classes. None changes plan counts.
