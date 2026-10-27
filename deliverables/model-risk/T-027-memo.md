# T-027 production veto — gate memo on T-108 (SUB-206–237), D-113/D-114

- Author: @model-risk (independent). 2026-10-19.
- Read: `deliverables/ai-engineer/evals/SUB-206-237-holdout-v7.{md,json}`, `SUB-206-237-holdout-v7-mismatches.md`, `SUB-206-237-run-record.md`, `RUN-RULES.md`; gold `deliverables/senior-underwriter/gold-set/SUB-206..237.md` (spot-checked, SUB-233 in full) and `T-108-routes.md`; frozen scorer `underwriting_pipeline/ai/eval_holdout_v7.py`; `team/DECISIONS.md` D-020, D-096, D-097, D-108–D-114.
- Recomputed: every per-field, status, route and P-055 count from the per-submission `checks`, `metrics`, `counted`, `status_split`, `route_gate` and `p055_gate` in the score JSON. All match the published tables and the fixed run facts except the mismatch-file ID lists noted below. No model call, nothing rescored, no code, scorer, gold or score file changed.
- Synthetic data. Not a production approval. Approved P-055/P-057/P-059/P-060/P-061/P-062 are not production approvals.

## Verdict: KEEP (T-027 veto not lifted)

Run integrity holds and the route gate passes, but a **hard safety gate fails** (P-055 scope gate: 1 leak, recall 11/12) and **two fields sit far below the 18/20 floor** (operations 9/20, loss runs 5/20). Lift-with-conditions is not justified: the failures are a scope guard that let an out-of-scope file reach the underwriter as routable, send-enabled and auto-drafted, plus materially wrong field values. Neither is cured by a condition that a gate could add; both need code fixes and a fresh frozen run.

## Integrity (checked by @model-risk)

| Check | Result |
|---|---|
| `git diff 457f1bf -- underwriting_pipeline` | empty; HEAD `5d51a9b`, `uncommitted: []` in the JSON |
| Prompt version | `759b3e6bc9b2`, reproduced from `llm_extract.PROMPT_VERSION` |
| Scorer v7 sha256 | `efe532a0006e21e60082279e29c97613eb5decdfadf12bedcdeb24f0d0437ca7`, matches the run record |
| Gold manifest sha256 | `11933e96…`, reproduced with the recipe in `T-108-M2-close.md` item 4 (per-file sha256 + two spaces + relative path, file order, trailing newline) |
| Model / host | `qwen/qwen3.8-27b` on `api.groq.com` (D-011 free tier) |
| Run once, scored once, fresh cache | run id `20261019T140831-50315`; `from_cache` 0; 21 call rows, 11 non-in-scope files stopped before any call |
| Retries / failed calls | 8 retries, all `rate_limit_429`, all logged; `call_failed` 0 |
| Smoke / .venv / pacing 55 s | as the run record states (not independently re-observed) |

## Gate table (20 in-scope files; floor = 18/20 per D-013 item 3)

| Criterion | Target | Result | Met |
|---|---|---|---|
| named_insured | ≥ 18/20 | 20/20 | Yes |
| premises | ≥ 18/20 | 20/20 | Yes |
| effective_date | ≥ 18/20 | 20/20 | Yes |
| operations | ≥ 18/20 | 9/20 (11 miss) | **No** |
| sales | ≥ 18/20 | 20/20 | Yes |
| tiv | ≥ 18/20 | 19/20 | Yes |
| construction | ≥ 18/20 | 20/20 | Yes |
| year_built | ≥ 18/20 | 20/20 | Yes |
| loss_runs (date only) | ≥ 18/20 | 5/20 (9 miss, 6 not credited) | **No** |
| False completes | 0 | 0 | Yes |
| Unsafe routes | 0 | 0 | Yes |
| Route accuracy | ≥ 18/20 | 18/20 | Yes |
| Leakage (out of scope) | 0 | **1 of 12 (SUB-233)** | **No** |
| Detection recall | 100% | **11/12** (C1 4/4, C2 4/5, C3 4/4, C4 2/2) | **No** |
| False manual intake | ≤ 2/20 | 0/20 | Yes |
| Silent error rate | watch | 17/180 = 0.094 (operations 9, loss_runs 8) | — |

4 of 16 criteria fail.

## High findings

**H1 — P-055 scope gate FAIL: SUB-233 leaked (owner @ai-engineer-assistant).** Gold marks SUB-233 out of scope (criterion 2, multiple locations: the application body lists "Loc 1: 3412 S Georgia St" and "Loc #2: 6901 Bell St" with no schedule file). The pipeline treated it as in scope and leaked all four ways: field shown, provisional route, automated missing-info draft, send enabled. Leakage is a hard gate (must be 0) and detection recall must be 100%; both fail on this one file. This is the one control that keeps an out-of-scope file from reaching an underwriter as a routable, sendable draft. Remediation: fix the scope detector to read a location list inside the application body when no schedule file exists (backlog B-432); dev self-checks including a SUB-233-shaped file; then a fresh frozen run with 0 leaks and 12/12 recall. Not a scorer change.

**H2 — operations 9/20 and loss_runs 5/20, carrying the run's entire silent-error burden (owner @ai-engineer-assistant).** Operations misses 11 (SUB-206, 207, 208, 209, 211, 215, 218, 220, 221, 222, 225); loss-run misses 9 (SUB-206, 207, 210, 213, 215, 218, 221, 222, 224) plus 6 not credited. Of the 17 silent errors (0.094), 9 are operations and 8 are loss_runs: a wrong value is shown, unflagged, with confidence 1.0. Operations repeats the T-104 shape (checklist items dropped from the summary); loss-run dates are shown wrong or dropped without a flag. These are what the underwriter reads; the field scores are less than half the floor. Remediation: an approved extractor change (`approve change P-###` required for prompt/extraction) so operations keeps every stated item and loss-run dates are read or flagged; build on dev; then a new 20 + 12 hold-out under the same rules meeting all criteria.

## Medium / Low (backlog, one line each)

- M1 Acceptance criteria 2 and 3 are still unticked in `team/TASKS.md`, and this hold-out does not test the <0.75 drop; I confirmed `source`, `quote` and `confidence` are present on every field in the saved replies (`underwriting_pipeline/cache/T-108-live/extractions/`), so the boxes are a board/owner action, not new code — @ai-engineer-assistant / @user.
- M2 Mismatches file F2 and the silent-error summary name the wrong operations silent IDs (list includes SUB-206, omits SUB-222); the count 9 is right — @ai-engineer-assistant.
- M3 Mismatches file lists 9 loss-run silent IDs for a count of 8 and wrongly includes SUB-218 (flagged, not silent); actual set is SUB-206, 207, 210, 213, 215, 221, 222, 224 — @ai-engineer-assistant.
- M4 Mismatches file calls SUB-218 a plain "complete"; the JSON shows "complete — review pending" (automation 3 of 8, not 4) — @ai-engineer-assistant.
- M5 Conflict 10/20 and status 15/20 with no false complete; the 2 route misses (SUB-206, 213, gold carrier_a → senior_referral) are not unsafe, but carrier_a has thin positive evidence — @head-of-underwriting.
- L1 Smoke and pacing are stated by the orchestrator, not evidenced by a log line in the run record.
- L2 Out-of-scope reason accuracy 11/11 is reported but is not a gate criterion; keep it reported.

## Verification of the memo and mismatches against the JSON

- `SUB-206-237-holdout-v7.md`: every per-field count, the status split (0 false completes, 3 of 8 automated), the route gate (0 unsafe, 18/20 PASS), the P-055 gate (1 leak SUB-233, recall 11/12, FAIL), and the silent-error table (17/180 = 0.094) are all supported by the JSON exactly.
- `SUB-206-237-holdout-v7-mismatches.md`: counts and totals are right; **three claims are not supported by the JSON** — F2's operations silent-ID list (SUB-206 named, SUB-222 omitted), the summary's loss-run silent-ID list (9 IDs for a count of 8, SUB-218 wrongly named), and line 34 calling SUB-218 a plain "complete". These are documentation errors only; they change no JSON number and no gate verdict.

## What would resolve the veto next

1. Approved P-### extractor fix for H2 (operations completeness; loss-run date read/flag), built and checked on dev only; @model-risk check, no High.
2. Detector fix for H1 (multiple locations in the application body; B-432), dev self-checks; a @model-risk check, no High.
3. Correct the three mismatch-file ID/wording errors (documentation only).
4. Code and scorer re-frozen and hashed; a fresh 20 + 12 hold-out, gold first and lint-passing, run once and scored once under D-109 rules, meeting every criterion in the gate table above (all 9 fields ≥ 18/20, 0 false completes, 0 unsafe, **0 leaks and 100% recall**).
5. The T-027 veto resolves only when those gate criteria are met; an approved P-### is not a production approval. Production use would additionally need the ongoing monitoring plan for operations and loss-run silent errors; this memo does not grant it.
