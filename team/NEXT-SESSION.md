# Next session

Written 2026-10-19 by the orchestrator at wrap-up (session 2 of the day, continuation after the T-108 run). Wrap-up commit: `8a488c0` on `ai-team` (this file committed after it), pushed to `origin/ai-team` (private). Previous: `667ce8a` / `14cc123`.

- Budget rule 8: demo blockers only until the demo is done.
- Standing rules: D-065, D-069, the CLAUDE.md "Plugins" section (D-097). One AI session on this repo (D-090). The `frontend/` files and `.claude/settings*.json` belong to the user and are never staged.
- **Work in the permanent worktree `/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team` (branch `ai-team`, D-101).** Never touch the main folder `-insureflow-ai-1`; its `team/NEXT-SESSION.md` is stale.
- **Run every pipeline command with `.venv/bin/python`.** A live run: `LLM_CACHE_DIR=<fresh dir> LLM_PACE_SECONDS=55 HOLDOUT_IDS=<a-b> HOLDOUT_OUT=<path> .venv/bin/python underwriting_pipeline/ai/regression_dev.py --holdout eval_holdout_v7 --write`. A re-score uses `HOLDOUT_RESCORE=1` and a temp cache copy.
- pyright: `npx --yes pyright@1.1.390 --pythonpath .venv/bin/python <files>`. Playwright only for `/opt/homebrew/opt/python@3.14/bin/python3.14`; `snap.py` runs under it.

## Where we stopped (T-108 run done and taken to the gate; root cause written; SUB-206–237 now dev data)

- **T-108 official hold-out done** (SUB-206–237, 32 files), once, scored once with v7 on frozen code (`457f1bf`, prompt `759b3e6bc9b2`, gold manifest `11933e96…`, run id `20261019T140831-50315`). Result `deliverables/ai-engineer/evals/SUB-206-237-holdout-v7.{md,json}`. **Route gate PASS** (0 unsafe, 18/20); **P-055 scope gate FAIL** (1 leak SUB-233, recall 11/12); **0 false completes**; operations 9/20, loss_runs 5/20; silent 0.094 (17/180); 0 call_failed; 8 retries all logged.
- **@model-risk T-027 gate memo** `deliverables/model-risk/T-027-memo.md`: **KEEP — the T-027 production veto is not lifted** (H1 scope leak B-432, H2 operations/loss-run completeness B-433). Resolves when both fixes land on dev with @model-risk checks (no High), code+scorer re-frozen, and a fresh 20+12 hold-out run once/scored once meets every gate criterion.
- **T-108 root cause** `deliverables/ai-engineer/analysis/T-108-root-cause.md` (analysis only, 0 calls): of the 17 silent errors, **7 are a scorer convention** (v7's `loss_run_mark` compares a correct valuation date to the *first* date in the gold "Loss runs" line = the policy-period start), **9 are operations gold-convention wording** (the facts are present), **1 (SUB-224) is a scan read wrongly with no review flag**. The **SUB-233 leak** root cause: `scope.py` (scope-v3) only sees a location label at line start, list item or schedule cell; SUB-233 writes "Loc 1 … ; Loc #2 …" inside the `Premises address:` value, so `multiple_locations` never fires, and the send gate refuses only by status and never re-checks scope.
- **@model-risk assist-mode ruling** `deliverables/model-risk/T-027-assist-mode-pilot.md`: an assist-only pilot (nothing routable, nothing sendable, human reads everything) is **permitted under conditions C1–C8**, outside the T-027 veto while they hold; B-190 (before any real data) and B-191 (before a pilot) are hard blockers. Not a production approval; T-027 unchanged.
- **D-115 recorded** (ACCEPTED by @user, 2026-10-19): **SUB-206-237 is now development data; its published scores stay as published, and it is no longer hold-out evidence.** D-011 (no paid API) stays parked. A stronger-model test is two steps: Step 1 free `openai/gpt-oss-120b` on Groq, Step 2 paid only if Step 1 is unclear, decided by the user after reading the root cause and the plan.
- **Stronger-model plan** `deliverables/ai-engineer/analysis/T-108-stronger-model-plan.md` (plan only, nothing run): honest expectation is that a stronger model moves at most ~1 mark (SUB-224); operations/loss_runs will not move. Step 2 (Claude Sonnet-class, needs a D-011 lift, suggested cap 2 USD) does not run unless Step 1 is unclear.
- **PM docs updated** to the T-108 run: `deliverables/pm/where-we-are.md`, `deliverables/pm/demo-guide.md` (numbers block only; the demo still uses the dev files SUB-127–184).
- Backlog: B-432 (scope detector: multiple locations in the application body, High), B-433 (operations/loss-run completeness + silent errors, High), B-434 (mismatch-file doc errors, fixed), **B-435 (loss-run scorer first-date convention + scan-flag gap)**, **B-436 (operations: separate gold-wording misses from the SUB-211 truncation)**.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. **Approve a scope-detector change (P-###) for B-432/H1** — a detector rule change is a code change under D-017; without it the SUB-233 near-pass form still leaks.
2. **Approve an extractor change (P-###) for B-433/H2** — the operations/loss-run findings need `approve change P-###`; without it the fields stay below the floor. (Note in T-108 root cause: 7 of the loss-run misses are a scorer rule, not the model — a prompt change alone will not move them.)
3. A scorer change for the loss-run first-date convention (B-435) is a separate P-###; v7 stays frozen and published until then.
4. "Go" for Step 1 of the stronger-model test (free gpt-oss-120b); **D-011 lift only for Step 2**, after the plan is read.
5. Still open: P-056 (a) month-first dates (D-104); B-402 email-only locations; detector gaps B-398/B-404; B-416/B-417 (ops check polarity and labels, each needs a P-###); B-429 (xlsx loss runs in the lint).

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | KEEP after the T-108 run. Resolves when B-432 and B-433 are fixed on dev with @model-risk checks (no High), code+scorer re-frozen, and a fresh 20+12 hold-out run once/scored once meets every gate criterion (0 leaks, 100% recall, all fields ≥ 18/20, 0 false completes, 0 unsafe). |
| T-082 | @responsible-ai (fairness) | As written in its veto message in team/DISCUSSION.md. |

## First 3 tasks next session

1. Propose and (on the user's `approve change P-###`) build the scope-detector fix for multiple locations in the application body (H1/B-432) on dev, with a SUB-233-shaped dev self-check; propose and (on approval) build the operations/loss-run fix (H2/B-433) on dev. @model-risk checks (no High).
2. Decide the loss-run scorer convention (B-435): a P-### for v8, or record it as a known convention and keep published scores as published. Then re-freeze code and scorer, hash them, and build a fresh 20+12 hold-out gold-first with the lint passing (D-020, RUN-RULES).
3. Run that hold-out once and score once with the then-current frozen v-scorer; take it to @model-risk for the T-027 gate. Meanwhile keep the demo from `deliverables/pm/demo-guide.md` (`run-demo.sh`, 0 live calls) unchanged.

## For the AI Engineer

- Pending proposals: none open. P-059 to P-062 built and approved by @model-risk.
- Latest scores: T-108 official hold-out (SUB-206–237, v7): route 18/20, 0 unsafe; scope gate FAIL (1 leak SUB-233, 11/12); 0 false completes; operations 9/20; loss_runs 5/20; silent 0.094; automation 0.789. T-104 (SUB-174–205, v6) and T-108 published scores stay as published.
- Top failure to fix next: the P-055 scope detector near-pass form (multiple locations inside the application body, no schedule file) — one file leaked all four ways — and the operations/loss-run completeness. Remember 7 of the 17 silent errors are a **scorer** rule (loss-run first-date), not the model; only SUB-224 is a real read error.
