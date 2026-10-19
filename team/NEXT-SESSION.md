# Next session

Written 2026-10-19 by the orchestrator at wrap-up. Wrap-up commit: `f251e71` on `ai-team` (plus this file), pushed to `origin/ai-team` (private).

- Budget rule 8: demo blockers only until the demo is done.
- Standing rules: D-065, D-069, the CLAUDE.md "Plugins" section (D-097). One AI session on this repo (D-090). The `frontend/` files and `.claude/settings*.json` belong to the user and are never staged.
- **Work in the permanent worktree `/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team` (branch `ai-team`, D-101).** Never touch the main folder `-insureflow-ai-1`; its `team/NEXT-SESSION.md` is stale. The code-review plugin reviews the main folder's diff: for the worktree use a reviewer agent on `git -C <worktree> diff <from> <to>`.
- **Run every pipeline command with `.venv/bin/python`.** Re-scores: `HOLDOUT_RESCORE=1`, a temp cache copy in `LLM_CACHE_DIR`, `LLM_PACE_SECONDS=0`, `HOLDOUT_OUT` in a temp folder.
- pyright: `npx --yes pyright@1.1.390 --pythonpath .venv/bin/python <files>`. Playwright is installed only for homebrew python `/opt/homebrew/opt/python@3.14/bin/python3.14`; `snap.py` runs under that interpreter.

## Where we stopped (D-113)

- **B-428 / B-411 fixed and committed as the T-108 code freeze, `457f1bf`.** The workbench "Not read by extraction" line now reads the saved run's unread rows through helper `not_read_by_extraction` in `underwriting_pipeline/app/workbench.py`, whole-file only, never the file name; self-check added. Demo replay 0 live calls; 24 demo screenshots retaken on a temp copy (D-065/D-069). Ruff 98 = baseline, pyright 35 = baseline.
- **B-427 analysis** (`deliverables/ai-engineer/b-427-silent-errors-and-ops-flags.md`): all 9 dev silent errors are stale dev gold with no operations-items line; **0 real check gaps, no P-### needed**. Operations flags 5/16 old -> 0/16 new, 1 of 41 new replies (SUB-134, true positive); B-415's "1 of 16" cell corrected to "1 of 41".
- **T-108 built and frozen, NOT run:**
  - 32 submissions `simulation/inbox/SUB-206..237` (20 in-scope, 12 out-of-scope). Out-of-scope criteria 4/5/4/2, three two-criteria files, two criterion-4-alone. W1 held files SUB-222, SUB-225; office-lessor SUB-206, SUB-213; deli SUB-207, SUB-215; duplicate pair SUB-217 (partial) / SUB-224 (complete). No folder carries a rule code or class label. Mix: `deliverables/producer/T-108-mix.md`.
  - Gold 32 cards `deliverables/senior-underwriter/gold-set/SUB-206..237.md`, route table `T-108-routes.md` (carrier_a 2, **senior_referral 16, no_match 2, carrier_b 0, carrier_c 0**), summary `T-108-gold-summary.md`.
  - Plan `deliverables/senior-test-engineer/T-108-plan.json` (7 `undated_loss_runs`); lint `lint_holdout.py --run-date 2026-10-19` **exit 0** (0 failures, 7 info, 32 files), `T-108-lint.md`; lint not edited.
  - Freeze: code `457f1bf`, prompt `759b3e6bc9b2` (P-059), scorer v7; gold manifest sha256 `7a26b81efbc4794276462caa6ca1a2a84fcbc38d54e6ca6e4534dde10ca02257`. Recorded on the board (`team/TASKS.md` T-108). **No score exists.**
- **@model-risk check** `deliverables/model-risk/T-108-check.md`: first pass OBJECTION (H1: the T-108 board entry did not record the code SHA, prompt and scorer) -> fixed -> **APPROVE, no High**; the build may be called frozen. M2 (gold read the scans with tesseract/pdftoppm as a document reader) is open for the user.
- Backlog: B-429 (lint cannot read xlsx loss runs), B-430 (M2), B-431 (Low).

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. **M2 / B-430:** accept the gold written from the scanned submissions using `tesseract`/`pdftoppm` as a document reader (gold-first integrity intact, but the reader is the same OCR the pipeline uses), or have the affected cards (209, 217 and the out-of-scope scans) redone by eye before the run.
2. **Run T-108:** when to run the frozen hold-out once and score it once with v7 (D-020). The run closes the T-027 production veto only if all 15 gate criteria are met.
3. **Record D-113** (this session's work) in `team/DECISIONS.md`, or renumber it, at the user's word — the board, mix and lint artefacts already cite D-113.
4. Still open: P-056 (a) month-first dates (D-104); B-402 email-only locations; detector gaps B-398/B-404; B-416/B-417 (ops check polarity and labels, each needs a P-###); B-429 (xlsx loss runs in the lint).

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | Re-freeze done (`457f1bf`); the new 20 + 12 hold-out is built gold-first with the lint passing and @model-risk's build approval (T-108, done). Remaining: run T-108 once and score with v7, meeting all 15 criteria. |
| T-082 | @responsible-ai (fairness) | As written in its veto message in team/DISCUSSION.md. |

## First 3 tasks next session

1. Ask the user for decisions 1 and 2 above (M2/B-430, and running T-108); record D-113 in `team/DECISIONS.md`.
2. If approved: run T-108 once under the run rules (`deliverables/ai-engineer/evals/RUN-RULES.md`, temp cache/out, `HOLDOUT_RESCORE` as required), score once with v7, publish, and take it to @model-risk for the production gate.
3. Give the manager demo from `deliverables/pm/demo-guide.md` using `run-demo.sh` (0 live calls) — unchanged by this session.

## For the AI Engineer

- Pending proposals: none open. P-059 to P-062 built and approved by @model-risk.
- Latest scores: no new scores this session (T-108 built, not run). T-104 hold-out stays as published; dev B-415 numbers unchanged (0 unsafe, 0 false completes, silent errors 9/180, operations flags 1/41).
- Top failure to fix next: route accuracy under P-061/P-062 is still unproven on real-shaped files (B-427). T-108 is built and frozen for exactly that — run it once.
