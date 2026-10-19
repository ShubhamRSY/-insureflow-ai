# Next session

Written 2026-10-19 by the orchestrator at wrap-up. Wrap-up commit: `3529a32` on `ai-team` (this file committed after it), pushed to `origin/ai-team` (private). Previous wrap-up: `f251e71` / `1261f7e`.

- Budget rule 8: demo blockers only until the demo is done.
- Standing rules: D-065, D-069, the CLAUDE.md "Plugins" section (D-097). One AI session on this repo (D-090). The `frontend/` files and `.claude/settings*.json` belong to the user and are never staged.
- **Work in the permanent worktree `/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team` (branch `ai-team`, D-101).** Never touch the main folder `-insureflow-ai-1`; its `team/NEXT-SESSION.md` is stale. The code-review plugin reviews the main folder's diff: for the worktree use a reviewer agent on `git -C <worktree> diff <from> <to>`.
- **Run every pipeline command with `.venv/bin/python`.** Re-scores: `HOLDOUT_RESCORE=1`, a temp cache copy in `LLM_CACHE_DIR`, `LLM_PACE_SECONDS=0`, `HOLDOUT_OUT` in a temp folder.
- pyright: `npx --yes pyright@1.1.390 --pythonpath .venv/bin/python <files>`. Playwright is installed only for homebrew python `/opt/homebrew/opt/python@3.14/bin/python3.14`; `snap.py` runs under that interpreter.

## Where we stopped (D-113 recorded and ACCEPTED)

- **D-113 recorded** in `team/DECISIONS.md` (Status ACCEPTED by @user, 2026-10-19): (1) B-428/B-411 fixed and committed as the T-108 code freeze `457f1bf`; (2) T-108 built gold-first, lint exit 0 before freeze; (3) T-108 **not** run, no score; (4) B-427 closed as analysis only (0 real gaps, no P-###); (5) M2/B-430 resolved in a separate decision.
- **M2 / B-430 resolved.** Every T-108 gold card was compared field by field against the **builder scripts' source data** (not OCR): `deliverables/senior-underwriter/T-108-gold-vs-source.md`. No OCR-induced drift in any scanned field. Wording-only corrections to SUB-206, SUB-208, SUB-214, SUB-230.
- **@model-risk M2 closure** `deliverables/model-risk/T-108-M2-close.md`: first pass M2 CLOSED but **H1** — SUB-211's gold omitted an open premises conflict (application 1120 Commerce St vs the email's "their new spot on Guadalupe"). Gold corrected to `incomplete — hold: open conflict` (route unchanged, `senior_referral` / suggested `carrier_b`). Re-check: **M2 CLOSED, H1 FIXED, freeze APPROVED, no High**.
- **T-108 built and frozen, NOT run:**
  - 32 submissions `simulation/inbox/SUB-206..237` (20 in-scope, 12 out-of-scope; criteria 4/5/4/2, three two-criteria, two criterion-4-alone). Mix: `deliverables/producer/T-108-mix.md`.
  - Gold 32 cards `deliverables/senior-underwriter/gold-set/SUB-206..237.md`, route table `T-108-routes.md` (carrier_a 2, **senior_referral 16, no_match 2, carrier_b 0, carrier_c 0**), summary `T-108-gold-summary.md`.
  - Plan `deliverables/senior-test-engineer/T-108-plan.json` (7 `undated_loss_runs`); lint `lint_holdout.py --run-date 2026-10-19` **exit 0** (0 failures, 7 info, 32 files), re-run twice after the M2/SUB-211 corrections, `T-108-lint.md`; lint not edited.
  - Freeze: code `457f1bf`, prompt `759b3e6bc9b2` (P-059), scorer v7; **gold manifest sha256 `11933e96b8370f57321ce5c1e1c6c3c3105a4f0517d841fbbbb8821bca18633d`** (32 gold cards + `T-108-routes.md`, file order 206..237 then routes). Recorded on the board (`team/TASKS.md` T-108). **No score exists.**
- Backlog: B-429 (lint cannot read xlsx loss runs), B-430 (M2 — resolved, keep the row as closed), B-431 (Lows: summary wording done; out-of-scope full fields; mix mtime).

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. **Run T-108:** when to run the frozen hold-out once and score it once with v7 (D-020). The run closes the T-027 production veto only if all 15 gate criteria are met.
2. Still open: P-056 (a) month-first dates (D-104); B-402 email-only locations; detector gaps B-398/B-404; B-416/B-417 (ops check polarity and labels, each needs a P-###); B-429 (xlsx loss runs in the lint).

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | Re-freeze done (`457f1bf`); T-108 built gold-first, lint passing, build approved and M2 closed (all done). Remaining: run T-108 once and score with v7, meeting all 15 criteria. |
| T-082 | @responsible-ai (fairness) | As written in its veto message in team/DISCUSSION.md. |

## First 3 tasks next session

1. Ask the user for decision 1 (when to run T-108 once and score with v7).
2. If approved: run T-108 once under the run rules (`deliverables/ai-engineer/evals/RUN-RULES.md`, temp cache/out, `HOLDOUT_RESCORE` as required), score once with v7, publish, and take it to @model-risk for the production gate.
3. Give the manager demo from `deliverables/pm/demo-guide.md` using `run-demo.sh` (0 live calls) — unchanged by this session.

## For the AI Engineer

- Pending proposals: none open. P-059 to P-062 built and approved by @model-risk.
- Latest scores: no new scores this session (T-108 built, not run). T-104 hold-out stays as published; dev B-415 numbers unchanged (0 unsafe, 0 false completes, silent errors 9/180 = stale dev gold, operations flags 1/41).
- Top failure to fix next: route accuracy under P-061/P-062 is still unproven on real-shaped files. T-108 is built and frozen for exactly that — run it once.
