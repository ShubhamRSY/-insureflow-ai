# Next session

Written 2026-10-15 by the orchestrator at wrap-up. Wrap-up commit: `fd57930` on `ai-team`, pushed to `origin/ai-team` (private).

- Budget rule 8: demo blockers only (weekly limit resets 2026-10-17).
- Standing rules: D-065, D-069. One AI session on this repo (D-090). The frontend/ files and `.claude/settings.json` are the user's and are never staged.
- **Run every pipeline command with `.venv/bin/python`.**
- Model: qwen/qwen3.8-27b (P-039), `LLM_PACE_SECONDS=55`.

## Where we stopped

- **D-092 built in the main session.**
  - **P-045** (`0a56520`; fixes `28b6d4d` and `ecf69c2`):
    - "_" lines are not skipped.
    - A carrier-negating line (not from / not issued by / copy / sample, plus Spanish) sends the run to review with its reason.
    - The valued date must be a real past date.
    - A carrier layout with no valued date leaves the field missing and the file incomplete, with "loss run found but no valued-as-of date; ask the producer for a dated carrier loss run". This holds whatever file the model cited.
  - **B-343:** scanned, image-only and spreadsheet loss runs always go to review: "loss run from scan/spreadsheet: check it".
  - Dev gold for SUB-150/151 corrected (@senior-underwriter, with a note).
  - SUB-147–152 cached re-run: 0 false completes, plain complete on 147 and 149, status as gold 5 of 6.
  - @model-risk: H1 found twice and **resolved** on the second look-again; no new High (`deliverables/model-risk/check-D-092.md`).
  - **T-102 mix CONFIRMED** by @model-risk, all changes applied.
- **Hold-out SUB-127–146 built** by @producer per T-102.
  - Gold written from the documents only by @senior-underwriter.
  - **Gold frozen at commit `bd9168e13fcd91a4e64421a69b1d8284798ab01a`.**
  - **The pipeline has NOT been run on them.**
  - Gold summary:

    | Measure | Count |
    |---|---|
    | Status | 6 complete, 14 incomplete |
    | Routes | carrier_a 2, carrier_b 2, carrier_c 2, hold 11, no_match 1, senior_referral 2 |
    | Expected pipeline status | complete 5, complete — review pending 3, incomplete 12 |
- Self-checks at wrap-up (.venv, no host): all six ok.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. **B-349 (L6):** confirm that the two P-045 (c) fixes (`28b6d4d`, `ecf69c2`) fall within D-092 1c. @model-risk asked; they have no P-### of their own.
2. **B-346 (M5):** does D-092 1c apply to each document separately? Today an undated carrier run next to a dated, accepted run can still give plain "complete".
3. **When to run the hold-out SUB-127–146:** `smoke_readers.py` first, then one paced run scored once by `eval_holdout_127.py`.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | SUB-127–146 run once (`smoke_readers.py` first, checked .venv, paced) with all 9 fields at 9/10 or better and 0 false completes |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md` |

## First 3 tasks next session

1. User answers B-349 and B-346. Do not change `underwriting_pipeline/` before the hold-out run unless the user approves a P-###.
2. Hold-out run:
   - `smoke_readers.py` (8 file types, uncached);
   - commit freeze;
   - one paced qwen run of SUB-127–146 with `regression_dev.py --holdout eval_holdout_127`, recording commit, model, Python and library versions;
   - @model-risk scores and reports per field, status safety, status automation, silent error rate, automation rate and route.
3. Backlog Mediums on card wording (B-334, B-339, B-347).

## For the AI Engineer

- Pending proposals: none. B-346 may need one.
- Latest scores: dev SUB-147–152, 0 false completes and 2 plain completes (typed PDF, typed text). Dev SUB-107–126 (comma-blind): 0 false completes, silent error rate 1.7%, automation rate 61.1%.
- Top failure to fix next: none blocking. Next is the frozen hold-out SUB-127–146 run (gold `bd9168e`).
