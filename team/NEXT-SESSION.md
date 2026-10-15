# Next session

Written 2026-10-15 by the orchestrator at wrap-up. Wrap-up commit: `21f758c` on `ai-team`, pushed to `origin/ai-team` (private). Budget rule 8: demo blockers only (weekly limit resets 2026-10-17). Standing rules: D-065, D-069. The frontend/ files are the user's and are never staged. **Run every pipeline command with `.venv/bin/python`.** SUB-087–106 is development data. The default model is still openai/gpt-oss-120b (`LLM_MODEL` in the user's `~/.zshrc`).

## Where we stopped

- D-086 built in the main session:
  - **P-038** (B-317):
    - (a) The prompt says sales is one gross-revenue number, never payroll. The prompt version and every cache key changed.
    - (b) Quotes match across markdown marks (`**`, `__`, `*`), still needing exact words and digits.
    - (c) A conflict with one side rejected keeps the cited side, flagged "conflict with rejected value: <value> (<file>)", after the side's own reason.
    - @model-risk: **APPROVE**, no High. @senior-underwriter UI: **APPROVE**. Screenshot `D-086-P-038-rejected-side.png`.
  - **B-319**: `eval_holdout_107.py` matches conflict sides with "$" and thousands commas set aside. Committed in `6ca8c06`, before any SUB-107+ submission or gold.
  - **qwen re-check** (uncached, paced 55 s): all three criteria pass (`pass-check-D-086.md`).

    | Criterion | Result | Needed |
    |---|---|---|
    | Sales, 9 shared files | 9 of 9 | 8 of 9 |
    | Silent error rate, 20 files | 1.7% | ≤ 2.5% |
    | Automation rate, 20 files | 77.2% | ≥ 71% |

    Sales on all 20 went 6 → 18 and status 9 → 15. A 43-minute DNS outage mid-run was retried with no file lost.
  - **P-039 drafted** (`deliverables/ai-engineer/proposal-P-039.md`): switch the default model to qwen/qwen3.8-27b. **Not approved, not switched.**
- Self-checks at wrap-up (.venv, no host): all six ok.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. **P-039**: type `approve change P-039` to switch. The switch is your edit of `LLM_MODEL` in `~/.zshrc`; batch runs then need pacing (about 18 min per 20 files).
2. B-313: confirm the P-037 "needs-review conflict" reading.
3. Then hold-out SUB-107–126 on the chosen model (gold first, scorer ready, `smoke_readers.py` first).

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | A new 20-file hold-out (SUB-107–126), gold first, scored once in a checked .venv after `smoke_readers.py` passes, with all 9 fields at 9/10 or better |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md` |

## First 3 tasks next session

1. The user's word on P-039.
2. If switched: the hold-out SUB-107–126. @producer builds the submissions, @senior-underwriter writes the gold first, and the run is scored once, paced.
3. B-321 (card wording for "conflict with rejected value") and B-299 (TIV reason with the liquor referral).

## For the AI Engineer

- Pending proposals: **P-039** (switch to qwen/qwen3.8-27b), waiting for your approval.
- Latest eval scores (qwen, D-086, development data, 20 files): named 19, premises 14, effective date 17, operations 17, sales 18, TIV 17, construction 18, year built 15, loss runs 13. Silent error rate 1.7%, automation rate 77.2%.
- Top failure to fix next: premises (14/20) and loss runs (13/20) on qwen.
