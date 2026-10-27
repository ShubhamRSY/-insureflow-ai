# T-120 lint (scorer v11) - @senior-test-engineer, 2026-10-27

## Current result (run 2, after gold fix of SUB-462/468): FAIL (2 failures, 1 info, 32 files)
- Command: `env -u LLM_API_KEY -u LLM_BASE_URL -u LLM_MODEL .venv/bin/python deliverables/senior-test-engineer/lint_holdout.py deliverables/senior-test-engineer/T-120-plan.json --run-date 2026-10-27 > T-120-lint.txt`. Output in `T-120-lint.txt`. Not run for scoring (D-020).
- Hashes verified before and after: lint_holdout.py `01147a75...` ok; eval_holdout_v11.py `7ddcfb50...` ok. Nothing frozen edited.
- FAIL SUB-461/scorer (gold-set/SUB-461.md Conflict line 23): perfect answer marked miss on conflict; cooking none vs stove top, no figure. v11-unmeasurable mark (D-128 kind), not a gold or build error.
- FAIL SUB-463/scorer (gold-set/SUB-463.md Conflict line 23): same, cooking none vs yes (schedule) and fryer (email). v11-unmeasurable (D-128 kind).
- INFO SUB-468/loss-runs.md: declared undated (owner letter dated 2026-09-21, no valued line), as declared.
- No gold errors, no build errors. Exit 1 only because of the two declared-unmeasurable marks; pass condition is the D-128 exclusion (report separately, exclude from conflict rate), as in T-119. Plan (`T-120-plan.json`: 450-481, 20/12, criteria 3/3/3/3, routes 4/13/3, undated SUB-468) passes the plan-vs-gold checks.

## History
- Run 1: FAIL (4 failures): SUB-462 and SUB-468 gold lines 12-13 unreadable ("stove top", "convection ovens" fit no slot), plus the SUB-461/463 marks. Fixed by @senior-underwriter (words moved to notes); plan fix on my side: SUB-468 declared undated.
