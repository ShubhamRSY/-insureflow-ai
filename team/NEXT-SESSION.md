# Next session

Written 2026-10-19 by the orchestrator at wrap-up. Wrap-up commit: `14cc123` on `ai-team` (this file committed after it), pushed to `origin/ai-team` (private). Previous: `5d51a9b` / `3529a32`.

- Budget rule 8: demo blockers only until the demo is done.
- Standing rules: D-065, D-069, the CLAUDE.md "Plugins" section (D-097). One AI session on this repo (D-090). The `frontend/` files and `.claude/settings*.json` belong to the user and are never staged.
- **Work in the permanent worktree `/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team` (branch `ai-team`, D-101).** Never touch the main folder `-insureflow-ai-1`; its `team/NEXT-SESSION.md` is stale.
- **Run every pipeline command with `.venv/bin/python`.** A live hold-out run: `LLM_CACHE_DIR=<fresh dir> LLM_PACE_SECONDS=55 HOLDOUT_IDS=<a-b> HOLDOUT_OUT=<path> .venv/bin/python underwriting_pipeline/ai/regression_dev.py --holdout eval_holdout_v7 --write`. A re-score uses `HOLDOUT_RESCORE=1` and a temp cache copy.
- pyright: `npx --yes pyright@1.1.390 --pythonpath .venv/bin/python <files>`. Playwright only for `/opt/homebrew/opt/python@3.14/bin/python3.14`; `snap.py` runs under it.

## Where we stopped (D-114 recorded; T-108 run done; T-027 KEEP)

- **D-114 recorded** (ACCEPTED by @user, 2026-10-19): M2/B-430 resolved — gold checked against builder source data (not OCR), wording fixes to SUB-206/208/214/230, H1 fix (SUB-211 `incomplete — hold: open conflict`), lint exit 0, gold re-frozen at manifest `11933e96b8370f57321ce5c1e1c6c3c3105a4f0517d841fbbbb8821bca18633d`. D-113 point (5) amended; T-108 gold is final.
- **Official T-108 hold-out run done** (SUB-206–237, 32 files), once and scored once with v7 on the frozen code:
  - Run: code `457f1bf`, prompt `759b3e6bc9b2`, scorer v7, gold manifest `11933e96…`, fresh empty cache (`underwriting_pipeline/cache/T-108-live/`), 0 cached replies, qwen paced 55 s, `--write`. Run id `20261019T140831-50315`.
  - Result: `deliverables/ai-engineer/evals/SUB-206-237-holdout-v7.{md,json}`; record `SUB-206-237-run-record.md`; mismatches as-is `SUB-206-237-holdout-v7-mismatches.md`.
  - **Route gate PASS** (0 unsafe, 18/20); **P-055 scope gate FAIL** (1 leak SUB-233, recall 11/12, criterion 2 4/5); **0 false completes**; operations 9/20 and loss_runs 5/20 (below the 18/20 floor); silent error rate 0.094 (17/180); 0 call_failed; 8 retries all `rate_limit_429`, all logged; 21 calls, 42,158 tokens, $0 free tier.
- **@model-risk T-027 memo** `deliverables/model-risk/T-027-memo.md`: **KEEP — the T-027 production veto is not lifted.** H1 = P-055 scope gate fail (SUB-233 leak; backlog B-432). H2 = operations/loss-run completeness and silent errors (backlog B-433). Resolves only when both fixes land on dev with @model-risk checks (no High), code+scorer re-frozen and hashed, and a fresh 20+12 hold-out gold-first and lint-passing is run once and scored once meeting every gate criterion (all 9 fields ≥ 18/20, 0 false completes, 0 unsafe, 0 leaks, 100% recall).
- Backlog: B-432 (scope detector: multiple locations in the application body), B-433 (operations/loss-run completeness), B-434 (mismatch-file doc errors, fixed). Open: B-429 (xlsx loss runs in the lint), B-431 (Lows).

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. **Approve an extractor change (P-###) for the operations and loss-run findings (H2/B-433)** — the fix needs `approve change P-###`; without it the fields stay below the floor.
2. Still open: P-056 (a) month-first dates (D-104); B-402 email-only locations; detector gaps B-398/B-404; B-416/B-417 (ops check polarity and labels, each needs a P-###); B-429 (xlsx loss runs in the lint); B-432 (scope detector).

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | KEEP after the T-108 run (route gate PASS, but scope gate FAIL and two fields below floor). Resolves when B-432 and B-433 are fixed on dev with @model-risk checks (no High), code+scorer re-frozen, and a fresh 20+12 hold-out run once/scored once meets every gate criterion (0 leaks, 100% recall, all fields ≥ 18/20, 0 false completes, 0 unsafe). |
| T-082 | @responsible-ai (fairness) | As written in its veto message in team/DISCUSSION.md. |

## First 3 tasks next session

1. Propose and (on the user's `approve change P-###`) build the operations and loss-run fix (H2/B-433) on dev; build the scope-detector fix for multiple locations in the application body (H1/B-432) on dev; @model-risk checks (no High).
2. Re-freeze code and scorer, hash them, and build a fresh 20+12 hold-out gold-first with the lint passing (D-020, RUN-RULES).
3. Run that hold-out once and score once with the then-current frozen v-scorer; take it to @model-risk for the T-027 gate. Meanwhile keep the demo from `deliverables/pm/demo-guide.md` (`run-demo.sh`, 0 live calls) unchanged.

## For the AI Engineer

- Pending proposals: none open. P-059 to P-062 built and approved by @model-risk.
- Latest scores: T-108 official hold-out (SUB-206–237, v7): route 18/20, 0 unsafe; scope gate FAIL (1 leak SUB-233, 11/12); 0 false completes; operations 9/20; loss_runs 5/20; silent 0.094; automation 0.789. T-104 (SUB-174–205, v6) stays as published.
- Top failure to fix next: the P-055 scope detector near-pass form (multiple locations inside the application body, no schedule file) — one file leaked all four ways — and the operations/loss-run completeness that carries the whole silent-error burden.
