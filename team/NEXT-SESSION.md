# Next session

Written 2026-10-16 by the orchestrator at wrap-up. The last work commit is `12b3a69` on `ai-team`. **Not pushed:** the permission classifier blocked `git push -u origin ai-team`. The user pushes it (origin is private). Commits since `origin/ai-team`: 2ea37a7, d08dbec, 4b313be, ec23c34, 12b3a69, plus this file.

- Budget rule 8: demo blockers only (the weekly limit resets 2026-10-17).
- Standing rules: D-065, D-069. One AI session on this repo (D-090). The frontend/ files and `.claude/settings.json` belong to the user and are never staged.
- **Run every pipeline command with `.venv/bin/python`.** Re-scores use `HOLDOUT_RESCORE=1`, a temp copy of the cache in `LLM_CACHE_DIR`, and `LLM_PACE_SECONDS=0` (RUN-RULES.md).
- Model: qwen/qwen3.8-27b (P-039), `LLM_PACE_SECONDS=55` for live runs.

## Where we stopped (D-095)

- **P-048 is built and checked.** @model-risk gave APPROVE WITH CHANGES; H1 (B-363) was closed at `4b313be`. @senior-underwriter UI check: APPROVE WITH CHANGES, no High.
  - (a) A prefixed carrier header ("> ", "#", "Fwd:") is checked as the carrier layout. Letter words never make it a letter (B-350).
  - (b) A scanned or image-only carrier run keeps its date for review. The file gets "complete — review pending", not hold (B-357 reason).
  - (c) Every held file shows "Provisional route: X (provisional — file on hold: <reason>) · No send until the hold clears". The route stays "hold", so every send gate stays shut. When TIV, the class or the sprinkler answer is missing, there is no provisional route. Scorer v2 has a route column.
  - (d) A citation may cover non-adjacent lines of one document. Only the cited lines are quoted (B-365).
  - (e) `HOLDOUT_RESCORE=1` makes no model call and writes `-cache-rescore` files. A live run refuses to overwrite an existing score file.
- **Dev re-check SUB-127–146** (dev data, clean at `ec23c34`, 0 calls; `deliverables/ai-engineer/evals/P-048-dev/`, NOTES.md):

  | Measure | Result |
  |---|---|
  | Loss runs, hit / miss / not credited | 8 / 0 / 12 (was 5 / 3 / 12) |
  | Operations | 19/20 |
  | Route | 16/20 (carrier_c 1/1, senior_referral 6/7) |
  | False completes | 0 |
  | Silent errors | 0 |

  The 3 old loss-run misses were scans (SUB-129, 131, 133). OCR broke the layout, so they were treated as undated runs and held.
- **B-364:** dev gold corrected. SUB-134 is now no_match and SUB-139 is senior_referral; provisional routes were added to held dev gold. @head-of-underwriting agrees. **P-049** covers the routing rules that are not written down: `deliverables/head-of-underwriting/proposal-P-049.md`.
- **T-103:** hold-out SUB-154–173 is planned in team/TASKS.md, not built. @model-risk approved the mix with conditions 1–3; condition 4 (H1 closed) is met.
- Backlog: B-369 to B-373.
- Standup: the roles that took turns this session (@senior-underwriter, @head-of-underwriting, @model-risk) have no D-095 entry in team/STANDUP.md.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. **P-049** (unwritten routing rules). Option A writes down 11 rules plus 3 rulings; option B removes 7 rules plus the same 3 rulings. Under the rulings, restaurants and sprinklered habitational go to senior_referral, with Carrier B or C suggested. If approved, this changes the carrier_b and carrier_c routes in T-103 gold. Sign-offs owed: @actuary (Carrier B cap) and @responsible-ai (Spanish words).
2. **B-372:** is the route column part of the T-027 gate?
3. When to build T-103. It runs under P-049 if approved, so decide P-049 first.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | A fresh 20-file hold-out (T-103) runs: gold first, smoke first, .venv, paced, scorer v2, run and scored once on a frozen commit. It needs all 9 fields at 9/10 or better and 0 false completes. |
| T-082 | @responsible-ai (fairness) | As written in its veto message in team/DISCUSSION.md. |

## First 3 tasks next session

1. Push `ai-team` (user), then user decisions on P-049 and B-372.
2. If P-049 is approved: build it, then a dev re-score of SUB-127–146 (`HOLDOUT_RESCORE=1`), @model-risk check, and @senior-underwriter UI fixes B-373.
3. @producer and @senior-underwriter build T-103 (gold first, with conditions 1–3) only when the user says so.

## For the AI Engineer

- Pending proposals: P-049 (head-of-underwriting, routing rules). P-048 is built and checked (H1 closed).
- Latest scores (dev SUB-127–146, scorer v2, cache re-score at ec23c34): loss runs 8/0/12, operations 19/20, route 16/20, 0 false completes, 0 silent errors.
- Top failure to fix next: routing rules. Of the 4 route misses, SUB-135 and SUB-138 are class-list gaps (P-049); SUB-142 and SUB-144 have no provisional route because TIV is missing (B-370).
