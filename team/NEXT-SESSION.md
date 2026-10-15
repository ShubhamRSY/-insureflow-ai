# Next session

Written 2026-10-14 by the orchestrator at wrap-up. Wrap-up commit: `126e48b` on `ai-team`, pushed to `origin/ai-team` (private). Budget rule 8: demo blockers only (weekly limit resets 2026-10-17). Standing rules: D-065 (backend + UI), D-069 (sandbox only). The frontend/ files are the user's and are never staged. **Run every pipeline command with `.venv/bin/python`.** SUB-087–106 is development data (D-082).

## Where we stopped

- D-082 built in the main session:
  - P-034: a missing reader library or program (pdfplumber, openpyxl, pytesseract, pdf2image, Pillow, tesseract, poppler) raises `sources.ReaderMissing` and stops the run; it is never listed as a damaged file.
  - SUB-101: a reply whose fields, conflicts or conflict sides are not objects is "reply not usable", is never cached and is called again. A saved reply of that shape is not trusted.
  - P-035: the rotation fill is taken in the image's own mode, so greyscale and other single-channel scans are read. OCR_SETTINGS changed, which changes the scan cache keys. SUB-088, 097 and 101 scans are now read (OCR 0.73–0.80). @model-risk: **APPROVE**, no High.
  - Premises trace (`deliverables/ai-engineer/analysis/premises-trace-SUB-087-106.md`): none of P-001, P-002 or P-005 cleared a value. The model reports full vs short forms of the same value as conflicts, and `prepare.agrees()` keeps them open (B-304). SUB-098's premises was correct but has a trailing note, so the exact-match scorer counts a miss (B-305).
  - Smoke test `underwriting_pipeline/ai/smoke_readers.py`: 8 types (typed PDF, image-only PDF, colour, greyscale and rotated scan, Excel, email-only, Spanish), all read, using a temp cache and 8 calls. Run it before any hold-out.
- Quick-15 after P-035 (`regression-quick-15-2026-10-14-D-082.json`): same as D-076, plus construction hit (needs review) 2 (was 1).
- No UI change: P-034 stops batch runs only; a SUB-101-style failure shows on the card as the existing FAILED line.
- Self-checks at wrap-up (.venv, no host): all six ok, plus sources and regression_dev.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. B-304: fix the false full-vs-short conflicts (prompt wording, or `agrees()` treating a street-only or "&"/"and" form as the same value). Needs a P-### and "approve change P-###".
2. B-305: whether future hold-out scorers allow a trailing note on premises (a scorer rule, so a P-###).
3. When to build the next 20-file hold-out (gold first), after B-304.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | RH1 (now fixed by P-035) and RH2 (B-304) fixed under approved P-###, then a new 20-file hold-out, gold first, scored once in a checked .venv after `smoke_readers.py` passes, with all 9 fields at 9/10 or better |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md` |

## First 3 tasks next session

1. @ai-engineer-assistant: proposal for B-304 (false full-vs-short conflicts), with self-checks on SUB-089/092/098/099/103.
2. Rerun SUB-087–106 as development data after B-304 (now including the scans), to see the effect.
3. B-299: show the TIV reason alongside the liquor referral.

## For the AI Engineer

- Pending proposals: none open. B-304 needs a new P-###.
- Latest eval scores: quick-15 (D-082; hit / hit needs review): named_insured 13/0, operations 12/1, sales 13/0, construction 13/2, year_built 15/0, premises 12/0, tiv 14/0, loss_runs 8/1, conflict 10/3, status 12/1. Last hold-out-style run: SUB-087–106 rerun (before P-035), premises 7/19.
- Top failure to fix next: B-304, the false full-vs-short conflicts that empty premises, name and operations.
