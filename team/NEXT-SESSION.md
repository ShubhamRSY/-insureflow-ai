# Next session

Written 2026-10-14 by the orchestrator at wrap-up. Wrap-up commit: `8c77f8d` on `ai-team`, pushed to `origin/ai-team` (private). Budget rule 8: demo blockers only (weekly limit resets 2026-10-17). Standing rules: D-065 (backend + UI), D-069 (sandbox only). The frontend/ files are the user's and are never staged. **Run every pipeline command with `.venv/bin/python`** (Playwright screenshots use the system python3, sandbox only). SUB-087–106 is development data.

## Where we stopped

- D-083 built in the main session:
  - **P-036** (B-304). In `llm_extract.py` (words, same_address, split_schedule) and `prepare.py` (agrees, fuller):
    - Two values agree when they are identical once case, punctuation, "&"/"and", St/Rd/Ave/Dr and spacing are normalized.
    - A street-only short form agrees with the full address only when it has a street type, and the full form adds only city, state and ZIP: no unit and no direction.
    - Any differing number stays a conflict, and every pair of sides must agree.
    - Operations agree on the same class, or when all business words of the shorter wording are in the fuller one.
    - Schedule addresses become locations only when every non-schedule side agrees with the same schedule row. Otherwise everything stays a conflict.
    - The card keeps the fuller value, shows each other quote with its file after "also:", and the review note says "merged: N documents agree".
  - @model-risk: REJECT ×3 (H1–H6), then **APPROVE** on the 4th check. @senior-underwriter UI check: APPROVE WITH CHANGES; both Highs (file name, merged note) fixed. Screenshot `D-083-P-036-also-quoted.png`.
  - **B-305**: `eval_holdout_107.py` for SUB-107–126 compares addresses without parenthetical notes. Committed in `0bf3cf2`, before any submission or gold exists.
  - Development check (`deliverables/ai-engineer/analysis/dev-SUB-087-106-D-083-comparison.md`): premises 7 → 11 and construction 13 → 16. Scans now read but OCR noise empties fields on SUB-088, 097 and 101 (B-311). Run-to-run variation is about ±1–2 per field.
  - Smoke test: 8 of 8 types read. Quick-15 unchanged vs D-082.
- Self-checks at wrap-up (.venv, no host): all six ok.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. B-311 / B-301: noisy scan OCR competes with typed facts. A fix (e.g. prefer typed sources over a low-confidence scan read, or P-006 EasyOCR) needs a P-###.
2. When to build the next hold-out SUB-107–126 (gold first, scorer `eval_holdout_107.py` ready, `smoke_readers.py` first).
3. Mediums B-306 to B-310 (P-036 edge cases) before or after the hold-out.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | A new 20-file hold-out (SUB-107–126), gold first, scored once in a checked .venv after `smoke_readers.py` passes, with all 9 fields at 9/10 or better |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md` |

## First 3 tasks next session

1. @ai-engineer-assistant: proposal for B-311 (scan OCR noise vs typed facts).
2. B-299: show the TIV reason alongside the liquor referral.
3. If @user says so: T-091/T-092 for SUB-107–126 (submissions, then gold), scorer already committed.

## For the AI Engineer

- Pending proposals: none open. B-311 needs a new P-###.
- Latest eval scores:
  - Quick-15 (D-083, hit / needs review): named_insured 13/0, operations 12/1, sales 13/0, construction 13/2, year_built 15/0, premises 12/0, tiv 14/0, loss_runs 8/1, conflict 10/3, status 12/1.
  - Dev SUB-087–106 (D-083, hit of 20): named 17, premises 11, effective date 13, operations 11, sales 10 (+1 needs review), TIV 14, construction 16, year built 12, loss runs 13.
- Top failure to fix next: B-311, noisy scan text overriding typed facts.
