# Next session

Written 2026-10-15 by the orchestrator at wrap-up. Wrap-up commit: `1c5b838` on `ai-team`, pushed to `origin/ai-team` (private). Budget rule 8: demo blockers only (weekly limit resets 2026-10-17). Standing rules: D-065, D-069. The frontend/ files are the user's and are never staged. **Run every pipeline command with `.venv/bin/python`** (Playwright screenshots: system python3, sandbox only). SUB-087–106 is development data.

## Where we stopped

- D-084 built in the main session:
  - **P-037** (B-311): a typed or structured value is never replaced by a scan read. A differing scan read keeps the typed value and flags it NEEDS REVIEW ("scan read differs: …; the typed value is kept — check against the page"). A scan still fills an empty field. This applies to the model's fields, the model's conflicts and the document rules, all using one scan list. @model-risk: REJECT (H1, document rules), then **APPROVE**. @senior-underwriter UI: **APPROVE**. Screenshot `D-084-P-037-scan-differs.png`.
  - **Rates on every score report** (`regression_dev.py`: value_metrics, summarize, add_metrics):
    - Silent error = a value is shown, it is wrong, and nothing flags it.
    - Automation = the value is correct and not flagged.
    - An empty field counts as flagged. Files with a failed call are left out of the rates and counted apart.
    - @model-risk: no High.
    - Results: dev check (D-083 replies, current code) 2.2% / 63.3% over 180 values; quick-15 1.7% / 70.0% over 120.
  - **Model comparison** (`deliverables/ai-engineer/analysis/model-compare-D-084.md`, uncached, same code):

    | | qwen/qwen3.8-27b | openai/gpt-oss-20b | openai/gpt-oss-120b |
    |---|---|---|---|
    | Silent error rate | 1.7% | 2.1% | 1.9% |
    | Automation rate | 71.7% | 59.0% | 60.2% |
    | Files run | 20 | 20 (4 failed: invalid JSON) | 12 (stopped: daily token limit hit at SUB-099) |
    | Tokens per file | 1,579 | 2,788 | 2,762 |
    | Seconds per file | 35.4 (incl. 35 per-minute 429 waits) | 58.6 | 12.7 before the limit |
    | Weak spot | sales 6/20 | — | — |
- Self-checks at wrap-up (.venv, no host): all six ok.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. Model choice for the next hold-out: qwen/qwen3.8-27b led on automation and every field but sales (6/20). A model switch is a P-### (D-017).
2. B-313: confirm the reading that a P-037 "needs-review conflict" is a flag acknowledged at approve, not an open conflict that blocks the send.
3. When to build hold-out SUB-107–126 (gold first; scorer `eval_holdout_107.py` ready; run `smoke_readers.py` first).

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | A new 20-file hold-out (SUB-107–126), gold first, scored once in a checked .venv after `smoke_readers.py` passes, with all 9 fields at 9/10 or better |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md` |

## First 3 tasks next session

1. @ai-engineer-assistant: why qwen misses sales (6/20). Error analysis only, from the D-084 qwen run.
2. The user's model decision (1), then the hold-out SUB-107–126 if they say so.
3. B-299: show the TIV reason alongside the liquor referral.

## For the AI Engineer

- Pending proposals: none open. A model switch would need a P-###.
- Latest eval scores: quick-15 (D-084, gpt-oss-120b): silent error 1.7%, automation 70.0%; hits as D-083. Model comparison as in the table above.
- Top failure to fix next: qwen sales 6/20, if qwen is chosen; otherwise gpt-oss-120b's daily token budget for a 20-file run.
