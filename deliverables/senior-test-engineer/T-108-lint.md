# T-108 — hold-out lint result (@senior-test-engineer)

- Date: 2026-10-19
- Task: T-108 (plan JSON lint, pre-freeze) · Decision: D-113
- Artifacts: `deliverables/senior-test-engineer/T-108-plan.json`, `deliverables/senior-underwriter/T-108-routes.md`, `deliverables/producer/T-108-mix.md`

## Command

```
.venv/bin/python deliverables/senior-test-engineer/lint_holdout.py deliverables/senior-test-engineer/T-108-plan.json --run-date 2026-10-19
```

- Run date: 2026-10-19
- Exit code: **0** (PASS: 0 failure(s), 7 info, 32 files)

Nothing was edited except `T-108-plan.json` (written by hand from the mix `.md` and the routes `.md`), which is the plan the lint reads. `lint_holdout.py`, `deliverables/ai-engineer/` and the frozen `eval_holdout_v6` scorer were not touched. No gold or submission file was edited.

## Info lines (verbatim)

```
INFO  SUB-212/loss-runs.md: declared undated in the plan; no valued date found, as declared
INFO  SUB-216/loss-runs.md: declared undated in the plan; no valued date found, as declared
INFO  SUB-219/loss-runs.md: declared undated in the plan; no valued date found, as declared
INFO  SUB-220/loss-runs.md: declared undated in the plan; no valued date found, as declared
INFO  SUB-229/loss-runs.md: declared undated in the plan; no valued date found, as declared
INFO  SUB-233/loss-runs.md: declared undated in the plan; no valued date found, as declared
INFO  SUB-235/loss-runs.md: declared undated in the plan; no valued date found, as declared
PASS: 0 failure(s), 7 info, 32 files, run date 2026-10-19
```

## Fail lines

None. The run exited 0 on the first lint after the plan was written.

## Re-run after the M2 gold-vs-source corrections (2026-10-19, same session)

The gold was compared against the builder source data and three non-factual wording differences were corrected (SUB-206, SUB-208 scope lines; SUB-214 source/scope lines). The lint was re-run on the same plan: `.venv/bin/python deliverables/senior-test-engineer/lint_holdout.py deliverables/senior-test-engineer/T-108-plan.json --run-date 2026-10-19` → **exit 0**, `PASS: 0 failure(s), 7 info, 32 files`. The plan JSON did not change and `lint_holdout.py` was not edited. The gold manifest was re-frozen at sha256 `657c63a97835adfac4815af08e9d06ebf78bb27767859596c040dd0a1cbdc4d0`.

What I did to get there, and what it proves:

1. `undated_loss_runs` was worked out from the files, not guessed. I ran the lint's own `lint_dates()` (read-only, temp plan, no declaration) over SUB-206..SUB-237 and read the ids the lint failed for a missing valued date, then read each of those loss-run files by eye to confirm the finding:
   - SUB-212, SUB-220, SUB-229 are "No known loss letter" files (owner letter in place of carrier loss runs) — no valued/as-of date.
   - SUB-235 is a Spanish no-known-loss letter — no valued/as-of date.
   - SUB-216 (Carrier A), SUB-219 (Carrier C) and SUB-233 (Carrier D) are typed carrier-format loss runs with policy-term rows and claim/loss date rows but **no valued/as-of/run-date line** — the term and loss dates are not a valuation date, so the lint's rule that a typed file must carry a valued date would otherwise fail them.
   These seven are declared in the plan and each returns an INFO, not a FAIL.
2. Route counts were transcribed exactly from `deliverables/senior-underwriter/T-108-routes.md` (plain rule names): carrier_a 2, carrier_b 0, carrier_c 0, senior_referral 16, no_match 2 (20 in-scope). The lint's gold-route check agrees with the gold cards, so the routes doc, mix and gold line up.
3. Mix counts (in 20 / out 12, per_criterion 4/5/4/2, two_criteria 3, criterion_4 2) agree with the gold Scope lines as read by the frozen parser.
4. Every dated loss-run line in SUB-206..SUB-237 is before the run date 2026-10-19; no late-date FAIL. Readable scans (SUB-209, SUB-211, SUB-217, SUB-218, SUB-225 loss-run PDF/JPG) read fine and carry valued dates before the run date.

## Plan JSON as written

```json
{"ids": "206-237", "in": 20, "out": 12,
 "per_criterion": {"1": 4, "2": 5, "3": 4, "4": 2},
 "two_criteria": 3, "criterion_4": 2,
 "routes": {"carrier_a": 2, "carrier_b": 0, "carrier_c": 0, "senior_referral": 16, "no_match": 2},
 "undated_loss_runs": ["SUB-212", "SUB-216", "SUB-219", "SUB-220", "SUB-229", "SUB-233", "SUB-235"]}
```

## Observations (no defect handed to @producer)

- SUB-230 carries `loss-summary.pdf`, not a `loss-run*` file. The lint only date-checks `loss-run*`, so it is never inspected; SUB-230 is an out-of-scope id (criterion 1, scanned application), so this does not affect the hold-out. Noted, not a blocker.
- SUB-223's loss run is an owner-prepared "loss history" labelled "as of 2026-08-28", which the lint reads as a valued date (as expected). Its route reason in `T-108-routes.md` says "not a recognised carrier format" — a @senior-underwriter wording point, not a file defect.

No FAIL line pointed at a submission file, so nothing is handed to @producer.

## D-069

Read-only run: this lint reads the inbox and gold and writes nothing — no real workbench page, no real log, no token log and no outbox (`simulation/to-carrier/`, `simulation/to-producer/`, `simulation/pending-approval/`) was written by this task.
