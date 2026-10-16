# Next session

Written 2026-10-15 by the orchestrator at wrap-up. Wrap-up commit: `3b43cf3` on `ai-team`, pushed to `origin/ai-team` (private).

- Budget rule 8: demo blockers only (weekly limit resets 2026-10-17).
- Standing rules: D-065, D-069. One AI session on this repo (D-090). The frontend/ files are the user's and are never staged.
- **Run every pipeline command with `.venv/bin/python`.**
- Model: qwen/qwen3.8-27b (P-039), `LLM_PACE_SECONDS=55`.
- SUB-087–126 is development data. The next hold-out is SUB-127–146, scored by `eval_holdout_127.py`: comma-blind addresses; status safety and status automation reported apart (B-325). No gold exists yet.

## Where we stopped

- **D-090:**
  - T-101 kept (user).
  - **P-044** (replaces P-043; `1c2f02d`): a loss run is accepted automatically only in a recognised carrier A/B/C layout (`simulation/carrier-loss-run-formats.md`), and only its valued-as-of date. Anything else that looks like a loss run needs review: "not a recognised carrier loss run (<file>); check it or ask the producer for the carrier's loss run". P-043's sentence patterns are removed. P-040's letter rule stays.
  - @model-risk: **APPROVE**, no High (`deliverables/model-risk/check-P-044.md`).
  - @senior-underwriter UI: **APPROVE**, no High. Screenshot: `D-090-P-044-not-recognised-loss-run.png`.
- **D-089 still in place:**
  - P-042: address check with or without the comma, every flag with a reason.
  - B-324: an open conflict is resolved on the card (logged with the run hash) before any send.
  - B-325 scorer.
- **Dev re-check SUB-107–126**, comma-blind 127 rules (cached qwen replies, no model call; `dev-SUB-107-126-D-090-commablind-qwen-qwen3-8-27b-cached.md`):

  | Measure | Result |
  |---|---|
  | Status safety | **0 false completes** |
  | Status automation | **0 of 4**: no dev loss run is in a carrier A/B/C layout, so every one goes to review |
  | Silent error rate | 1.7% (3/180) |
  | Automation rate | 61.1% |

  Fields: named 20, premises 15, effective date 18, operations 17, sales 18, TIV 19, construction 20, year built 17. Loss runs: 10 hits, 0 misses.
- Self-checks at wrap-up (.venv, no host): all six ok.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. **B-337:** the P-044 accept path has never run on a real file, a PDF, or OCR text. Decide whether @producer adds carrier A/B/C loss runs to a dev file (and as PDF/scan) before the hold-out.
2. The hold-out SUB-127–146 mix: carrier-format loss runs (typed, PDF, scanned) on the complete files, plus carrier_c and senior_referral routes.
3. B-336 (skip "_" lines only before the header): a small P-044 follow-up, if wanted.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | The SUB-127–146 hold-out: gold first, checked .venv, `smoke_readers.py` first, scored once, paced; all 9 fields at 9/10 or better, 0 false completes |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md` |

## First 3 tasks next session

1. User decides B-337. If yes, a cached re-score proves the accept path on a carrier-format dev file, including a PDF and a scan.
2. Hold-out SUB-127–146:
   - `smoke_readers.py` first;
   - @producer builds it, with carrier A/B/C loss runs per `simulation/carrier-loss-run-formats.md`;
   - @senior-underwriter writes the gold first, complete or incomplete only;
   - the run is scored once, paced, by `eval_holdout_127.py`.
3. Backlog Mediums from D-089/D-090 card wording (B-334, B-339).

## For the AI Engineer

- Pending proposals: none. P-044 approved and built (D-090).
- Latest scores (dev SUB-107–126, comma-blind): 0 false completes, status automation 0 of 4, silent error rate 1.7%, automation rate 61.1%.
- Top failure to fix next: no file reaches plain "complete", because no dev loss run is in a carrier format. Prove the P-044 accept path on carrier-format files, including PDF and OCR (B-337).
