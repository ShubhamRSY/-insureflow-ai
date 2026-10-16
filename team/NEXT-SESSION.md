# Next session

Written 2026-10-16 by the orchestrator at wrap-up. Wrap-up commit: `7b2b1e6` on `ai-team`, pushed to `origin/ai-team` (private).

- Budget rule 8: demo blockers only (the weekly limit resets 2026-10-17).
- Standing rules: D-065, D-069, the CLAUDE.md "Plugins" section (D-097). One AI session on this repo (D-090). The frontend/ files and `.claude/settings*.json` belong to the user and are never staged.
- **Work in the permanent worktree `/Users/disastershubz/INSURANCE FLOW AI/insureflow-ai-team` (branch `ai-team`, D-101).** `.venv` there is a symlink to the main folder's venv (excluded in `.git/info/exclude`). The main folder `-insureflow-ai-1` stays on `feat/gcp-infrastructure` with the user's uncommitted `src/`, `tests/`, `docs/rag/`, `scripts/` changes: never touch it. Check `git branch --show-current` says `ai-team` before work.
- **Run every pipeline command with `.venv/bin/python`.** Score files are written only with `--write`; re-scores use `HOLDOUT_RESCORE=1`, a temp cache copy in `LLM_CACHE_DIR`, `LLM_PACE_SECONDS=0`. intake.py's self-check runs with no argument (not `--self-check`).

## Where we stopped (D-101)

- **T-103 run once and scored once** (scorer v4, `--write`), code `3557e4a`, gold `33e399a`, both confirmed unchanged by git; smoke ok first; qwen paced 55 s; 20 calls, 0 failed, 4 logged 429 retries, 38,396 tokens (~1,920/file, $0 on the free host). Files: `deliverables/ai-engineer/evals/SUB-154-173-holdout-v4.md/.json`, `-run-record.md`, `-mismatches.md` (as-is, cache replay, 0 calls).
- Result: 0 false completes, 0 unsafe routes; route 16/20 (**gate FAIL**); fields at 9/10: only named_insured 19/20 (premises 16, effective 17, operations 7, sales 17, tiv 17, construction 17, year built 16, loss runs 5 hit + 11 not credited). Silent error 3.3%, automation 71.7%, status automation 4/8.
- **@model-risk T-027 memo: KEEP** (`deliverables/model-risk/T-027-gate-memo-T-103.md`). Nothing was fixed (user's instruction). Backlog B-394 (H1 fields), B-395 (H2 route), B-396 (M1–M5, L1–L3).
- Standup missing: @model-risk (took a turn, wrote the memo and a DISCUSSION message, no standup line).

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. **What to fix first for T-027** (B-394, B-395): the scanned application SUB-170 (every field lost though OCR read it), scanned carrier-run dates 0/3 (SUB-159–161), empty date/address/operations on email-only and Spanish files, multi-location address/year built. Each fix needs a numbered P-### and "approve change P-###".
2. **Gold conventions for the next hold-out** (B-396 M1, M4, decide before any new gold): "missing, not given" vs "not in documents" for empty fields; gold route "hold" vs D-097 (route after the hold clears); and whether the operations all-words rule (M2) stays.
3. **Dev gold** (B-392 M4): update SUB-127–146 gold to R17, or leave the dev gate failing on stale gold.
4. **The GCP branch** and the `5ceeef8` roles (B-388): confirm or reject.
5. Senior-underwriter ambiguities for @head-of-underwriting (T-103-gold-summary.md): SUB-161, SUB-173, SUB-167.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | Approved P-### fixes for H1 (field floor) and H2 (route), then a new frozen 20-file hold-out, gold first (after M1/M4 are settled), smoke first, .venv, paced, scorer v4 `--write`, run and scored once: all 9 fields at 9/10, 0 false completes, 0 unsafe, route ≥18/20. T-103's score stays as published. |
| T-082 | @responsible-ai (fairness) | As written in its veto message in team/DISCUSSION.md. |

## First 3 tasks next session

1. Check the worktree and branch (`ai-team`); user decisions 1–2.
2. @ai-engineer-assistant writes the P-### for the top T-103 failure (SUB-170 scanned application and scanned run dates), from the saved replies, no model call.
3. Decisions 3–5.

## For the AI Engineer

- Pending: no open P-###. Decisions: what to fix first (B-394/B-395); gold conventions (B-396 M1/M4); dev gold; GCP branch.
- Latest scores (T-103 hold-out SUB-154–173, v4, live, `3557e4a`): 0 unsafe, 0 false completes, route 16/20, operations 7/20, only named_insured at 9/10; T-027 KEEP.
- Top failure to fix next: scanned inputs: SUB-170's scanned application lost every field, and scanned carrier runs gave 0/3 dates.
