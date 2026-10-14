# Next session

Written 2026-10-14 by the orchestrator at wrap-up. Wrap-up commit: `d877e88` on `ai-team`, pushed to `origin/ai-team` (private). Read CLAUDE.md "Usage budget rules" first: demo blockers only, sessions of 2–3 hours, one-line estimate at the start. New standing rule D-065 (definition of done = backend + UI) is in CLAUDE.md and the four builder roles.

## Where we stopped

- D-065: backend + UI rule recorded; B-227 (React `frontend/` integration, required for pilot) on the backlog.
- D-066: P-024 built (B-215): agreeing merges keep each side's flag and quote; flagged if either side was. @model-risk: **APPROVE**, B-215 closed; Medium/Low B-228 to B-230.
- P-016 drop analysis (`deliverables/ai-engineer/p-016-drop-analysis.md`): 9 values dropped; 2 clearly correct (SUB-038 loss run 0.58, SUB-067 construction 0.65), 2 arguably correct, 3 wrong (gains: SUB-067 effective date and sales, SUB-074 TIV 220000 vs gold 280000). Confidence alone does not separate right from wrong drops.
- P-025 proposed, not approved, not built (`deliverables/ai-engineer/proposal-P-025.md`): A keep dropping below 0.75; B store as needs-review above a 0.50 floor (assistant's recommendation, about +5 quick-set hits); C store all; D like B, scans only.
- Quick set of 15 after P-024: 0 model calls, no change vs the P-016 run (`regression-quick-15-2026-10-14-P-024.json`).
- Demo runs SUB-009, SUB-010, SUB-029 re-saved from cache with network calls blocked (0 calls); they now carry quotes; manifest check ok.
- Workbench (D-066 block 2, @software-engineer): the page reads only the saved run (status, hash, manifest; never extracts on load); refusals shown on the card in plain words, no bare 400; Send to carrier with the typed line through the same gate; missing-info draft with approve (D-050 via `prepare.approve`); "What's new" panel. Screenshots (sandbox, real logs untouched): `deliverables/software-engineer/screenshots/D-066-SUB-009-send.png`, `D-066-SUB-029-draft.png`, `D-066-SUB-010-refused.png`.
- @senior-underwriter UI review: **APPROVE WITH CHANGES**. **High-1 open (B-231):** 83 of 86 cards are red "No usable saved run"; list saved-run cards first and fold the rest into one collapsed "No saved run (83)" block with the reason and how to create a run. Medium/Low B-232 to B-242.
- UI gaps still open from the D-065 list: carrier override form (D-057), send history (`sends.jsonl`), per-file decision history, acknowledgment history, subjectivity closures and "satisfied is evidence only" (D-058), suggested market as its own field, model/prompt version, intake upload.
- Self-checks at wrap-up (no model host): llm_extract, prepare, intake, package, workbench, points all ok.
- Not committed, left alone: `src/insureflow/`, `tests/`, `docs/rag/`, `scripts/`.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-015 score fixes | no build task |
| P-017 commit hash and status in score output | with T-072 |
| D-048 exits from `all_values_rejected` | no build task |
| D-050 producer-request rule | T-098 (the workbench draft approve calls the existing `prepare.approve`) |

## Pending decisions for the user

1. P-025: "approve change P-025" plus a letter (A, B, C or D), or leave as is.
2. B-231 (UI High-1): build the fix (saved-run cards first, the rest folded).
3. Which remaining UI gaps to build, and in what order.
4. The confidence-versus-hit table (B-222), which @model-risk needs to lift T-027.
5. Parked: P-018, P-019/T-099, T-100. OCR price basis: $10.00 or $1.50 per 1,000 pages.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-017 | @model-risk, @responsible-ai | P-015 built and looked at again |
| T-027 | @model-risk (production) | The confidence-versus-hit table built, then the new 20-file hold-out (T-091 to T-093), gold first, scored once |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md` |

## First 3 tasks next session

1. B-231 fix in the workbench (@software-engineer), screenshot, @senior-underwriter re-check of High-1.
2. P-025 build if @user approves a letter, then the quick set of 15.
3. B-232/B-233 (send form names the carrier, "already sent" line) before any demo send; then the remaining reviewers of T-079, T-083, T-085, T-086, T-087.

## For the AI Engineer

- Pending proposals: P-025 (low-confidence scan values: A drop, B needs-review above 0.50, C keep all, D B for scans only).
- Latest eval scores (quick-15 after P-024, cached): named_insured 13/15, operations 12, sales 13 (+1 flagged), construction 13, year_built 15, premises 12, tiv 14, loss_runs 8, conflict 12, status 12.
- Top failure to fix next: low-confidence scan values (P-025); on scores, SUB-074 (5 misses).
