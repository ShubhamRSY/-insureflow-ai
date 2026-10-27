# T-108 mismatches, as-is (SUB-206 to SUB-237, scorer v7, D-113/D-114)

Recorded after the single official run on 2026-10-19 (run id `20261019T140831-50315`). Nothing was fixed; findings are logged as backlog. Source: `deliverables/ai-engineer/evals/SUB-206-237-holdout-v7.json` and the same run's saved replies in `underwriting_pipeline/cache/T-108-live/`.

## Gate failures (2)

### F1 — SUB-233: out-of-scope file not stopped (P-055 scope gate FAIL)
- Gold: out of scope, criterion 2 (multiple locations). The application itself lists "Loc 1: 3412 S Georgia St" and "Loc #2: 6901 Bell St" with no separate schedule file ("near-pass form").
- Pipeline: treated as in scope — fields shown, a provisional route, an automated missing-info draft, send enabled. Leak list: field shown, provisional route, automated draft, send enabled.
- Effect: leakage 1 of 12 (must be 0); detection recall 11/12 (must be 100%); criterion 2 recall 4/5.
- Backlog: the scope detector does not read a location list inside the application body when no schedule file exists. (New row — B-432.)

### F2 — operations: 9/20 hits, floor 18/20 not met
- 11 misses: SUB-206, 207, 208, 209, 211, 215, 218, 220, 221, 222, 225.
- 9 of these are also silent errors (a value shown, wrong, and not flagged): SUB-207, 208, 209, 211, 215, 218, 220, 221, 222.
- Pattern: the pipeline under-captures the gold "Operations items" checklist items (word order/clause rules, v5). Same class as T-104 (operations 12/20, 3 silent). Backlog: existing operations finding; no new P-### (a prompt change would need `approve change P-###`).

### F3 — loss_runs: 5 hits, 9 misses, 6 not_credited (floor 18/20 not met)
- Misses: SUB-207, 210, 213, 215, 218, 221, 222, 224 and 206 (also SUB 206). Not credited (null + needs review where gold expects a date): SUB-209, 211, 216, 217, 219, 225.
- 8 of the 20 are silent errors (date shown, wrong, not flagged): SUB-206, 207, 210, 213, 215, 221, 222, 224. The v7 rule change did not lift this field on this set.
- Backlog: loss-run date reading/flagging; no new P-### (prompt/scorer frozen).

## Route misses (not unsafe)

| File | Gold | Used | Note |
|---|---|---|---|
| SUB-206 | carrier_a | senior_referral | readable class on no carrier list (R8); not held |
| SUB-213 | carrier_a | senior_referral | same |

Both are office suites, gold says they are a direct Carrier A risk under P-049..P-062. The pipeline sent them to a senior referral instead. Route accuracy 18/20 = gate met (at least 18/20); 0 unsafe.

## Conflict misses (10)
- Missed a conflict that gold records: SUB-209 (sales: app $1,248,000 vs email "around 1.6 mil"), SUB-210 (loss run undated vs valued), SUB-211 (premises: app 1120 Commerce St vs email "new spot on Guadalupe"), SUB-213, SUB-214 (TIV: app $0 tenant vs schedule 890000), SUB-216, SUB-218, SUB-219, SUB-221, SUB-224.
- These are conflict-marks, not extracted fields. No status became unsafe: every affected file is `incomplete` or `complete — review pending` (SUB-210, 218, 221, 224 are `complete — review pending`; gold for them does not require a hold on a value field beyond the conflict — see status note below).

## Status misses (5): SUB-206, 207, 213, 215, 218
- All 5 are the pipeline showing `incomplete` or `complete — review pending` where gold differs on the exact wording/condition, or the reverse. No false complete. Failed calls 0.

## TIV miss (1): SUB-214
- Gold tenant TIV $0 vs schedule $890,000; the pipeline did not record the conflict (see conflict misses). This is the tiv field mark.

## Silent errors (17 of 180 = 0.094)
- operations 9 (SUB-206, 207, 208, 209, 211, 215, 218, 220, 221) and loss_runs 8 (SUB-206, 207, 210, 213, 215, 218, 221, 222, 224). Shown, wrong, not flagged. Same two fields as the T-104 run's only silent errors.

## Not mismatches (recorded for completeness)
- False completes: 0. Unsafe routes: 0. Leakage beyond SUB-233: 0. call_failed: 0. Retries: 8, all `rate_limit_429`, all logged.
