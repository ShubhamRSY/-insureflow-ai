# Next session

Written 2026-10-17 by the orchestrator at wrap-up. Wrap-up commit: `30db83e` on `ai-team`, pushed to `origin/ai-team` (private).

- Budget rule 8: demo blockers only.
- Standing rules: D-065, D-069, the CLAUDE.md "Plugins" section (D-097). One AI session on this repo (D-090). The frontend/ files and `.claude/settings*.json` belong to the user and are never staged.
- **Work in the permanent worktree `/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team` (branch `ai-team`, D-101).** The main folder `-insureflow-ai-1` stays on `feat/gcp-infrastructure` with the user's uncommitted work: never touch it. Its `team/NEXT-SESSION.md` is stale; read this one.
- **Run every pipeline command with `.venv/bin/python`.** Re-scores: `HOLDOUT_RESCORE=1`, a temp cache copy in `LLM_CACHE_DIR`, `LLM_PACE_SECONDS=0`, `HOLDOUT_OUT` in a temp folder. Reviewer dispatches must say so: `regression_dev.py` with no argument makes live calls (B-405).
- pyright: `npx --yes pyright@1.1.390 --pythonpath .venv/bin/python <files>`.
- Roster includes @frontend-engineer and @senior-test-engineer (D-106).

## Where we stopped (D-108, D-109)

- **D-108:** P-055 fixes confirmed in scope; **P-057 scorer v6** and **P-058 detector scope-v3** built, code-review fixes, @model-risk BLOCK (H1) → BLOCK (H2) → APPROVE; re-frozen at `6e7cfa2`; scorer v6 sha256 `4bf1cd63a632ad38834909f6822c92619a7b597fe5994a24be1a5914c9d54e5b`.
- **D-109 T-104 official run, once** (code `6e7cfa2`, scorer v6, gold `3678c0f`, all verified by @model-risk): smoke ok; fresh empty cache `underwriting_pipeline/cache/T-104-live` (git-ignored; holds this run's replies and token log); qwen paced 55 s; 20 calls, 0 failed, 5 logged 429 retries; 35,455 tokens, $0.
  - **P-055 scope gate PASS:** 0 leaks of 12, recall 12/12 (criteria 4/4, 5/5, 4/4, 2/2), reasons 12/12, false manual intake 0/20.
  - **T-027:** 0 false completes, 0 unsafe; **route 16/20 FAIL** (SUB-174, 182, 186, 201); fields at 20/20 except sales 19, **operations 12/20**, **loss runs 9/20**; silent 0.017, automation 0.817; loss runs accepted automatically 0/20; status automation 0 of 9 gold-complete files.
  - Files: `deliverables/ai-engineer/evals/SUB-174-205-holdout-v6.md/.json`, `-run-record.md`, `-holdout-v6-mismatches.md` (38 non-hits: gold convention 17, extraction 8, scorer 5, check 4, routing rule 4), `-console.txt`.
- **@model-risk T-027 memo: KEEP** (`deliverables/model-risk/T-027-gate-memo-T-104.md`): 12 of 15 criteria met. H1 operations (items on cooking, hood and line-of-business lines dropped), H2 route (3 files to no_match; SUB-201 W1 nightclub provisional senior_referral), H3 loss runs (test runs valued after the run date; v6 marks "null, needs review" a miss). Backlog B-406 to B-409. Nothing fixed.
- T-104 is spent: published scores are never rewritten, and it is not re-run.
- Standups for this session's turns: labelled orchestrator entries for @model-risk, @producer, @ai-engineer-assistant (D-108 item 5, D-109).

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

1. Check the worktree and branch (`ai-team`). User decisions 1–3.
2. Build the approved fixes; dev re-score (read-only, 0 calls where saved replies exist); @model-risk check (High only); re-freeze.
3. @producer builds and @senior-underwriter writes gold for the next 20 + 12 hold-out (loss runs valued before the run date); freeze; run only when the user says so.

## For the AI Engineer

- Pending: none open as P-###; needed: H1 operations, H2 routing, H3 scorer rule (B-406–B-408).
- Latest scores (T-104, v6, `6e7cfa2`): P-055 gate PASS; 0 false completes, 0 unsafe; route 16/20; operations 12/20, loss runs 9/20, other fields ≥ 19/20; T-027 KEEP.
- Top failure to fix next: operations items dropped from cooking/hood/line-of-business lines (H1, 8 files, 3 silent errors).
