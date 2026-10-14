# Next session

Written 2026-10-14 by the orchestrator at wrap-up. Wrap-up commit: `b77ffa9` on `ai-team`, pushed to `origin/ai-team` (private). **The weekly usage limit was hit (resets 2026-10-17, 5pm Central).** Budget rule 8 applies: demo blockers only. Standing rules: D-065 (backend + UI), D-069 (sandbox only).

## Where we stopped

- D-070: B-260 accepted (identical re-save keeps the approval). B-264 (suggested market only on senior referrals), B-265 (footer shows the saved run's model and prompt version), B-266 (stale card lists changed fields old → new) built; screenshots `deliverables/software-engineer/screenshots/D-070-*.png` (sandbox).
- B-222 confidence-vs-hit table (`deliverables/ai-engineer/confidence-vs-hit.md`): 15 cached files, 115 values. Scans sort by confidence (0.90+ 15/0, 0.75–0.89 5/2, 0.50–0.74 3/2); typed values all at 0.90+, including all 5 typed errors. @model-risk: **APPROVE**; the T-027 table condition is met.
- P-015 built (S3 H1 M1 T2 V3 W1 A1 E2): `prepare.cooking_facts` (labelled lines, cited), cuisine words out of the cue list, name removed before cue matching; `points.score_run` ("Not scored — reason"; LOSS_HISTORY out, range 0–80; POINTS_VERSION hash + "git:not-recorded"); workbench uses it, mark-wrong per code (W1, `code_marks.jsonl`), decision rows save points/codes/version/model/prompt (E2; cache key null).
- T-067 name-swap (`deliverables/data-scientist/name-swap-T-067.md`): 0 of 56 pairs changed score, match or status, on 7 cached files (1 scored). Thin.
- @model-risk on P-015: **APPROVE WITH CHANGES**. **High B-268:** "no" tested only at line start; "Cooking equipment: no fryer; gas grill and charbroiler" reads "stated none", scores 0, no quote. Fix: negate per clause, show the quote, self-check. **T-017 veto stands** until fixed (other T-017 conditions met).
- **Not run:** @responsible-ai fairness check of P-015 (weekly limit; nothing written) and the @senior-underwriter UI check of D-070 (B-270).
- B-271: only 15 of 60 development files are in the extraction cache; the P-016 drop analysis said 60 of 60 — reconcile.
- Self-checks at wrap-up (no model host): llm_extract, prepare, intake, package, workbench, points all ok.
- Not committed, left alone: `src/insureflow/`, `tests/`, `docs/rag/`, `scripts/`.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 commit hash and status in score output | with T-072 |
| D-048 exits from `all_values_rejected` | no build task |
| D-050 producer-request rule | T-098 (the workbench draft approve calls the existing `prepare.approve`) |

## Pending decisions for the user

1. B-268: fix the cooking negation as a P-015 build fix, or number it P-027.
2. B-269: save the extraction cache key in the saved run (E2) — an `ai/` change needing a P-###.
3. Start the new 20-file hold-out (T-091 to T-093), gold first, scored once — the last T-027 condition.
4. Parked: P-018, P-019/T-099, T-100. OCR price basis: $10.00 or $1.50 per 1,000 pages.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-017 | @model-risk (and @responsible-ai, not yet re-checked) | B-268 fixed; @responsible-ai checks P-015 fairness |
| T-027 | @model-risk (production) | The new 20-file hold-out (T-091 to T-093), gold first, scored once (the table condition is met) |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md` |

## First 3 tasks next session (after the limit resets)

1. @responsible-ai fairness check of P-015 (fresh dispatch, D-070 criteria) and @senior-underwriter UI check of D-070.
2. B-268 once @user decides, then @model-risk re-check of the High.
3. B-271 cache coverage reconcile; then T-091 gold for the new hold-out if @user says so.

## For the AI Engineer

- Pending proposals: none numbered. B-268 and B-269 need your call.
- Latest eval scores (quick-15, P-025-fix, cached; hit / hit (needs review)): named_insured 13/0, operations 12/1, sales 13/0, construction 13/1, year_built 15/0, premises 12/0, tiv 14/0, loss_runs 8/1, conflict 10/3, status 12/1. No extraction-value change this session.
- Top failure to fix next: B-268 (a stated cooking line with "no" at the start hides a fryer/grill).
