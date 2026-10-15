# Next session

Written 2026-10-14 by the orchestrator at wrap-up. Wrap-up commit: `e7ec2fe` on `ai-team`, pushed to `origin/ai-team` (private). Budget rule 8: demo blockers only (weekly limit resets 2026-10-17). Standing rules: D-065 (backend + UI), D-069 (sandbox only). The frontend/ files are the user's and are never staged. **Run every pipeline command with `.venv/bin/python`, never `python3`.**

## Where we stopped

- D-081: SUB-087–106 rerun once at frozen `9e725e3`.
  - Environment check passed, saved in `SUB-087-106-rerun-env-check.txt`: .venv 3.14.6, pdfplumber 0.11.10, openpyxl 3.1.5, pytesseract 0.3.13, pdf2image 1.17.0, pillow 12.3.0, tesseract 5.5.2, poppler 26.10.0, and a real pdf2image page converted and read by OCR. Poppler was installed this session with brew.
  - The run used a worktree at 9e725e3 and a fresh cache, on Groq openai/gpt-oss-120b. SUB-101 is call_failed (reply_not_usable, 3 attempts). Not published.
- Run 1 is kept as `SUB-087-106-holdout-run1-invalid.*`, marked invalid in the memo, and never quoted as a score.
- @model-risk (`deliverables/model-risk/holdout-SUB-087-106.md`): T-027 veto **stands**. Only 1 of 9 fields reaches 9/10. Route 9/19, and 0 of 5 files expected at carrier A/B/C got there.
  - RH1 (verified by the orchestrator): all 3 .jpg scans (SUB-088, 097, 101) are "could not be opened" even in .venv. `sources._fill` returns an RGB fill for a greyscale image, Pillow 12.3 raises a TypeError in rotate, and a bare except reports it as a damaged file. P-034 does not cover this.
  - RH2: premises is empty on typed files that state it (SUB-089/092/099/103), and SUB-098 has an empty name and operations.
- Freeze is over (the hold-out is scored). The hold-out set SUB-087–106 is now used; a new hold-out needs a new 20.
- Self-checks at wrap-up (.venv, no host): all six ok.
- Missing standups from the earlier wrap-up: @producer, @senior-underwriter (T-091, T-092).

## Approved, not built

| Proposal | Task |
|---|---|
| **P-034** a missing reader library stops the run with a clear error, never skips files (D-081 item 6) | build now; plus the SUB-101 reply-shape fix (D-081 item 6) |
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. RH1 greyscale-scan fix (`sources._fill` / rotate). It is extraction/OCR code, so it needs a P-### and "approve change P-###".
2. RH2 premises/name empties on typed files: @ai-engineer-assistant to diagnose, then a P-### if a prompt or gate changes.
3. Then a new 20-file hold-out (gold first) to try to lift T-027.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | RH1 and RH2 fixed under approved P-### changes, then a new 20-file hold-out, gold first, scored once in a checked .venv, with all 9 fields at 9/10 or better |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md` |

## First 3 tasks next session

1. Build P-034 (reader-library guard) and the SUB-101 reply-shape fix (D-081 item 6, approved), with self-checks; quick-15 after.
2. @ai-engineer-assistant: proposal for RH1 (greyscale scans) and a diagnosis of RH2 (premises empty).
3. B-299: show the TIV reason alongside the liquor referral.

## For the AI Engineer

- Pending proposals: P-034 approved, not built. RH1 and RH2 need new P-### numbers.
- Latest eval scores (SUB-087–106 rerun, 9e725e3, .venv; "9 of 9 extracted fields scored; claims not read; loss runs = date only"; hit/scored, SUB-101 call failed): named_insured 17/19, premises 7/19, effective_date 14/19, operations 12/19, sales 12/18 (1 flagged), tiv 13/19, construction 13/19, year_built 11/18 (1 flagged), loss_runs 13/13 (6 not credited), conflict 10/19 (2 flagged), status 10/19, route 9/19.
- Top failure to fix next: RH1, all scans unread (greyscale fill in `sources._fill`).
