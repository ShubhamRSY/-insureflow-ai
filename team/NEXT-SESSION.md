# Next session

Written 2026-10-14 by the orchestrator at wrap-up. Wrap-up commit: `28e5f28` on `ai-team`, pushed to `origin/ai-team` (private). Budget rule 8: demo blockers only (weekly limit resets 2026-10-17). Standing rules: D-065 (backend + UI), D-069 (sandbox only). The frontend/ files are the user's and are never staged.

## Where we stopped

- D-079 built and committed:
  - B-290: a bar word with restaurant evidence → senior referral "possible bar/liquor exposure — confirm liquor sales"; without it → no_match as before.
  - B-293: bakery, coffee shop, deli → Carrier B food service.
  - P-033 (B-291): negation words ningún, nada, w/o, isn't, removed, zero.
  - B-294: override claim removed from What's new.
  - B-295: failed card shows "Not read — extraction failed".
- Cuisine swap rerun (fairness-swaps-D-079.md): 0 findings.
- Screenshot: D-079-bar-referral-and-failed-card.png.
- @senior-underwriter: **APPROVE**, no High. Mediums logged as B-297 to B-300.
- Self-checks (no model host): llm_extract, prepare, intake, package, workbench, points all ok.
- Not committed, left alone: `src/insureflow/`, `tests/`, `docs/`, `scripts/`, `frontend/`.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 commit hash and status in score output | with T-072 |
| D-048 exits from `all_values_rejected` | no build task |
| D-050 producer-request rule | T-098 |
| B-258 no_match override control | after demo |

## Pending decisions for the user

1. Start the new 20-file hold-out (T-091 to T-093), gold first. This is the last T-027 condition.
2. B-298: whether "bar-b-q" / "sushi bar" restaurants should skip the liquor referral.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | The new 20-file hold-out (T-091 to T-093), gold first, scored once |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md` |

## First 3 tasks next session

1. B-297: the failed card's "Not read: none" / "Needs human read: none" lines (small, workbench.py).
2. B-299: show the TIV reason alongside the liquor referral.
3. T-091 gold for the new hold-out, if @user says so.

## For the AI Engineer

- Pending proposals: none.
- Latest eval scores (quick-15, D-076, cached; hit / hit needs review): named_insured 13/0, operations 12/1, sales 13/0, construction 13/1, year_built 15/0, premises 12/0, tiv 14/0, loss_runs 8/1, conflict 10/3, status 12/1.
- Top failure to fix next: B-297 (a failed card still says "Not read: none").
