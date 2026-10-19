# Next session

Written 2026-10-19 by the orchestrator at wrap-up (session 3 of the day). Wrap-up commit: `b39ead7` on `ai-team` (this file committed after it), pushed to `origin/ai-team` (private). Previous: `50ed778`.

- Budget rule 8: demo blockers only until the demo is done.
- Standing rules: D-065, D-069, the CLAUDE.md "Plugins" section (D-097). One AI session on this repo (D-090). The `frontend/` files and `.claude/settings*.json` belong to the user and are never staged.
- **Work in the permanent worktree `/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team` (branch `ai-team`, D-101).** Never touch the main folder `-insureflow-ai-1`; its `team/NEXT-SESSION.md` is stale.
- **Run every pipeline command with `.venv/bin/python`.** New hold-outs are scored with **`eval_holdout_v8`** (v7 frozen). Gold check: `HOLDOUT_IDS=<a-b> .venv/bin/python underwriting_pipeline/ai/eval_holdout_v8.py --check-gold`.
- pyright: `npx --yes pyright@1.1.390 --pythonpath .venv/bin/python <files>`. Playwright only via `/opt/homebrew/opt/python@3.14/bin/python3.14`; `deliverables/software-engineer/T-105-demo/snap.py` runs under it.

## Where we stopped (D-116)

- **T-109a, P-063 built** (B-432, T-027 memo H1). `scope.py` is now **scope-v4**: a numbered location/building/premises label anywhere in an application line counts, e.g. SUB-233's "Loc 1: …; Loc #2: …" inside the premises value. `prepare.scope_problem()` re-checks scope at send time, whatever the status says, in `send_to_carrier`, `prepare.approve` and the workbench card ("Send blocked — … Next step: re-run extraction …").
  - Dev sweep v3→v4 over 237 folders: only SUB-233 changes, to multiple_locations.
  - Fail-closed widening: "Building 2" inside one address is now manual intake (B-439).
- **T-109b, P-064 built** (B-435). `eval_holdout_v8.py` reads the loss-run date only from the gold line `- Loss runs valued as of: <YYYY-MM-DD>`. A card that expects a date without that line stops the run before any call. The convention is in `deliverables/ai-engineer/evals/RUN-RULES.md`.
- **T-109c: the lint now tests the scorer.** `lint_holdout.py` builds a perfect answer from each gold card, which must get no miss. Wrong answers (one per field, leaks, an unsafe route) must each be caught. Any failure blocks the freeze.
  - On T-108 gold, as written: **FAIL 15**. No in-scope card has the valued-as-of line.
  - With the line added in a temp copy: **FAIL 10**. F1: `Conflict: none (…)` is scored a miss, which accounts for 5 of the 10 published T-108 conflict misses. F2: "a.m./p.m." inside an operations item can never match (SUB-211/222/225). F3: "needs review" in the middle of the Expected loss run line is not read (SUB-216/219).
  - 0 wrong answers were missed. Backlog B-437.
- **T-109d** `deliverables/pm/pilot-readiness.md`: C1–C8 are 0 met, 3 partly met, 3 not met, 1 not started, 1 not verified. B-190 (SSO) and B-191 (concurrent writes) are hard blockers, with build plans.
- **Reviews:**
  - @model-risk: **APPROVE** T-109a, T-109b and T-109c, no High (`deliverables/model-risk/check-P-063-P-064-T-109c.md`).
  - @senior-underwriter UI: APPROVE WITH CHANGES; the H1 wording was fixed in the same task.
- The user kept B-433 (no extractor change now) and the free-model test (B-438) in the backlog. New backlog rows: B-435 to B-444.
- Self-checks ok: llm_extract, prepare, intake, package, workbench, points.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. **Gold conventions or a scorer fix for B-437.** Either keep the gold-writing rules now in RUN-RULES (plain `Conflict: none`, no full stops inside operations items, "needs review" first), or approve a P-### for a v9 that reads these forms.
2. **B-435, open part:** a scanned loss run (SUB-224) is read with no needs_review flag. Fixing it is an extraction/check change and needs a P-###.
3. **T-027 path.** The memo's resolution needs B-433 (operations/loss-run completeness) fixed as well as B-432. The user parked B-433, so a fresh hold-out alone cannot lift the veto unless the user changes that.
4. Still open: B-440 (locations only in the email body), P-056 (a) month-first dates, B-402, B-398/B-404, B-416/B-417, B-429.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | KEEP. B-432 is now fixed on dev with a @model-risk check (no High). Still needs B-433 fixed on dev with a check, code and scorer re-frozen (v8), and a fresh 20+12 hold-out, gold first with the lint PASS, run once and scored once, meeting every gate: 0 leaks, 100% recall, all fields ≥ 18/20, 0 false completes, 0 unsafe. |
| T-082 | @responsible-ai (fairness) | As written in its veto message in team/DISCUSSION.md. |

## First 3 tasks next session

1. User decisions: B-437 (conventions or v9 P-###), the T-027 path given that B-433 is parked, and the B-435 scan flag.
2. If the user says go: @senior-underwriter and @producer plan the next 20+12 hold-out under scope-v4 and v8. Gold first, with the valued-as-of line and the B-437 conventions; `lint_holdout.py` must exit 0 before the freeze; code and scorer frozen and hashed.
3. Keep the demo from `deliverables/pm/demo-guide.md` (`run-demo.sh`, 0 live calls) unchanged; re-check that it still runs after scope-v4 (the demo files are SUB-127–184; the sweep showed no change there).

## For the AI Engineer

- Pending proposals: none open. P-063 and P-064 are built and approved by @model-risk (no High).
- Latest scores: T-108 (now dev, v7, published, unchanged): route 18/20, 0 unsafe; scope gate FAIL (1 leak SUB-233, which scope-v4 now catches on dev); 0 false completes; operations 9/20; loss_runs 5/20 (7 of the 8 silent misses were v7's date rule, which v8 fixes); silent 0.094.
- Top failure to fix next: operations/loss-run completeness (B-433, parked) and the scorer/gold conventions the lint found (B-437). Without a decision on these, the next hold-out cannot pass the field floor.
