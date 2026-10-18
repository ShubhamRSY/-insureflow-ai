# Next session

Written 2026-10-18 by the orchestrator at wrap-up. Wrap-up commit: `0d3d872` on `ai-team`, pushed to `origin/ai-team` (private).

- Budget rule 8: demo blockers only.
- Standing rules: D-065, D-069, the CLAUDE.md "Plugins" section (D-097). One AI session on this repo (D-090). The frontend/ files and `.claude/settings*.json` belong to the user and are never staged.
- **Work in the permanent worktree `/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team` (branch `ai-team`, D-101).** Never touch the main folder `-insureflow-ai-1` (user's uncommitted work); its `team/NEXT-SESSION.md` is stale.
- **Run every pipeline command with `.venv/bin/python`.** Re-scores: `HOLDOUT_RESCORE=1`, a temp cache copy in `LLM_CACHE_DIR`, `LLM_PACE_SECONDS=0`, `HOLDOUT_OUT` in a temp folder. `regression_dev.py` with no argument makes live calls (B-405).
- pyright: `npx --yes pyright@1.1.390 --pythonpath .venv/bin/python <files>`. Playwright is not in `.venv`; screenshots used system Chrome (`channel="chrome"`).

## Where we stopped (D-110, T-105 DONE)

- Manager demo prep, no pipeline code changes; code still frozen at `6e7cfa2`.
- Demo files (dev data, not hold-out): **SUB-133** messy in-scope, senior referral → Carrier C quote; **SUB-129** manual intake ("scanned application"), approve/send/draft refused; **SUB-127** non-senior confirm refused, UW-001 confirms (P-052) → Carrier A quote. Quotes are simulated, fictional figures.
- Guide: `deliverables/pm/demo-guide.md`; one-pager: `deliverables/pm/where-we-are.md`; screenshots: `deliverables/software-engineer/screenshots/demo/` (19).
- Replay: `deliverables/software-engineer/T-105-demo/run-demo.sh <new temp folder>` (copies dev inbox + saved replies, blocks live calls; needs `LLM_BASE_URL`/`LLM_MODEL` = Groq + qwen/qwen3.8-27b in the shell). Ran clean 2026-10-18: 21 cache hits, 0 calls, D-069 clean.
- Rehearsal (`deliverables/senior-test-engineer/T-105-rehearsal.md`): READY WITH FIXES; the 3 High setup breaks, the driver-location mismatch, the "45 entries" count and the banner quote were fixed in the guide by the orchestrator. Not re-dispatched for a second rehearsal.
- Caveats to say out loud: no dev file routes straight to Carrier A on frozen code (B-414); the account-manager check refuses senior referrals with "not in appetite" (B-412), so the sends in the demo are the user's typed line; time saved is an unmeasured estimate that @senior-underwriter has not yet checked.
- New backlog: B-410 (collapse "What's new"), B-411, B-412, B-413, B-414.
- T-104 is spent and is not re-run; scores stay as published.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. **H1 operations (B-406):** a P-### so the operations answer includes items stated on cooking, hood and line-of-business lines.
2. **H2 routing (B-407):** a P-### for the three no_match class misses and the W1 nightclub provisional route.
3. **H3 loss runs (B-408):** scorer rule for "null, needs review" (a P-###), and a build rule for the next hold-out: carrier runs valued before the run date.
4. Then a new 20 + 12 hold-out (gold first), as @model-risk's memo sets out.
5. Still open: P-056 (a) month-first dates (D-104); B-402 email-only locations wording; detector gaps B-398/B-404.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | Approved fixes for H1, H2 and the H3 scorer rule, checked on dev files; re-freeze; a new 20 + 12 hold-out, gold first, loss runs valued before the run date; run and scored once, meeting all 15 criteria (9 fields at 9/10 on in-scope files, 0 false completes, 0 unsafe, route ≥ 18/20, 0 leaks, 100% detection per criterion, false manual intake ≤ 2/20). |
| T-082 | @responsible-ai (fairness) | As written in its veto message in team/DISCUSSION.md. |

## First 3 tasks next session

1. Check the worktree and branch (`ai-team`). Ask the user how the demo went; record any decisions they type.
2. User decisions 1–3 above (H1 operations, H2 routing, H3 scorer rule); build the approved fixes, dev re-score read-only, @model-risk check (High only), re-freeze.
3. Optional demo polish only if the user approves a UI task: B-410 (collapse "What's new"), B-412 (account-manager check screen and wording), with D-065 screenshots and a "What's new" line.

## For the AI Engineer

- Pending: no P-### open; needed: H1 operations, H2 routing, H3 scorer rule (B-406–B-408).
- Latest scores (T-104, v6, `6e7cfa2`): P-055 gate PASS; 0 false completes, 0 unsafe; route 16/20; operations 12/20, loss runs 9/20, other fields ≥ 19/20; T-027 KEEP.
- Top failure to fix next: operations items dropped from cooking/hood/line-of-business lines (H1, 8 files, 3 silent errors).
