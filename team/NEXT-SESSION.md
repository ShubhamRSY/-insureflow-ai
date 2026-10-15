# Next session

Written 2026-10-15 by the orchestrator at wrap-up. Wrap-up commit: `864abce` on `ai-team`, pushed to `origin/ai-team` (private). Budget rule 8: demo blockers only (weekly limit resets 2026-10-17). Standing rules: D-065, D-069. The frontend/ files are the user's and are never staged. **Run every pipeline command with `.venv/bin/python`.** SUB-087–106 is development data. Production model is still openai/gpt-oss-120b (no switch, D-085).

## Where we stopped

- D-085 development checks, no code change to the pipeline:
  - **Fair comparison** (`deliverables/ai-engineer/analysis/fair-compare-D-085.md`), on the 9 files all three models completed:

    | | qwen/qwen3.8-27b | openai/gpt-oss-120b | openai/gpt-oss-20b |
    |---|---|---|---|
    | Hits (of 81) | 60 | 59 | 47 |
    | Automation rate | 71.6% | 69.1% | 56.8% |
    | Silent error rate | 2.5% | 2.5% | 2.5% |
    | Sales | 3 of 9 | 8 of 9 | — |
  - **qwen stability** (`stability-qwen-D-085.md`): a second uncached run changed 0 of 180 marks. Automation 71.7% → 71.1%.
  - **Pacing:** `DEV_PACE_SECONDS=55` in `dev_rerun_087.py`. qwen's cap is 1,000 output tokens per minute at about 731 per reply; 429s fell from 35 to 5.
  - **qwen sales misses** (`sales-trace-qwen-D-085.md`), 14 in all:

    | Cause | Files | Count |
    |---|---|---|
    | Sales and payroll (or a label) in one value; the gate rejects it. The right number was read. | 087, 091, 092, 097, 099, 100, 105 | 7 |
    | As above, and the quote drops the markdown "**" | 096, 098, 101, 103 | 4 |
    | Empty | 095 | 1 |
    | One-sided conflict dropped (B-318) | 094 | 1 |
    | Scorer $/comma match (B-319) | 106 | 1 |
    | Wrong number chosen | none | 0 |
- Recommendation given to the user: fix sales first, then switch (see below).
- Self-checks at wrap-up (.venv, no host): all six ok.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. The recommendation: fix qwen's sales format first (B-317, a P-###: e.g. the prompt asks for one number per field and the exact quote, or the gate takes the sales part of a "sales; payroll" value), re-check on SUB-087–106, then decide the switch (also a P-###).
2. B-313: confirm the P-037 "needs-review conflict" reading.
3. Hold-out SUB-107–126: after the model decision. B-319 goes into eval_holdout_107 before its gold.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | A new 20-file hold-out (SUB-107–126), gold first, scored once in a checked .venv after `smoke_readers.py` passes, with all 9 fields at 9/10 or better |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md` |

## First 3 tasks next session

1. @ai-engineer-assistant: proposal for B-317 (qwen sales format), if the user agrees with the recommendation.
2. B-318 (one-sided conflict drops the good side) and B-319 (scorer $/comma in eval_holdout_107), as proposals.
3. B-299: show the TIV reason alongside the liquor referral.

## For the AI Engineer

- Pending proposals: none open. B-317 needs a P-###.
- Latest eval scores: see the fair comparison table above. qwen full 20 files: silent error 1.7%, automation 71.7% / 71.1% (two runs).
- Top failure to fix next: B-317, qwen's sales format (11 of 14 misses).
