# Next session

Written 2026-10-15 by the orchestrator at wrap-up. Wrap-up commit: `e57af9a` on `ai-team`, pushed to `origin/ai-team` (private).

- Budget rule 8: demo blockers only (weekly limit resets 2026-10-17).
- Standing rules: D-065, D-069. One AI session on this repo (D-090). The frontend/ files are the user's and are never staged.
- **Run every pipeline command with `.venv/bin/python`.**
- Model: qwen/qwen3.8-27b (P-039), `LLM_PACE_SECONDS=55`.
- SUB-087–126 and SUB-147–152 are development data. The next hold-out is SUB-127–146. **No file exists yet** (T-102). It is scored by `eval_holdout_127.py`.

## Where we stopped

- **D-091**
  - Dev files SUB-147–152 built by @producer, with @senior-underwriter's gold first (`77ee2e4`).
  - Pipeline run on qwen, paced, uncached (`dev-SUB-147-152-D-091.md`):

    | File | Case | Result |
    |---|---|---|
    | 147 | Carrier A, typed PDF | accepted 2026-09-30, **plain complete** |
    | 148 | Carrier B, greyscale scan | OCR broke the layout ("Carrier RB", "2026-09-39"); model gave no date; **incomplete** (safe; a scanned run cannot be accepted by design) |
    | 149 | Carrier C, typed text | accepted, **plain complete** |
    | 150 | Letter with copied Carrier A header | no date found; **incomplete** |
    | 151 | Carrier B without valued line | no date; **incomplete** |
    | 152 | Unknown carrier layout | review: "not a recognised carrier loss run"; **complete — review pending** |

    **0 false completes.** On 150 and 151 the P-044 gate was never reached (the field was missing), so gold "needs review" vs pipeline "incomplete" (M1).
  - **T-102** written in `team/TASKS.md`: the SUB-127–146 mix. Loss runs: 8 carrier-format, 6 non-carrier, 6 none. The 8 carrier-format runs are 3 typed PDF, 2 text, 2 JPG scans and 1 image-only PDF; none in xlsx.
  - **R-030** in `team/RISKS.md`: the layouts are synthetic and a copied layout could pass; production needs real carrier formats and a source check.
  - @model-risk (`check-D-091.md`): no High.
    - Dev check: APPROVE.
    - R-030: APPROVE.
    - **T-102 mix: APPROVE WITH CHANGES.** M3–M5 and L2 are recorded on T-102, **not yet applied**:
      - M3: the copied-header letter carries a valued date;
      - M4: one typed no-claims carrier run;
      - M5: gold follows the documents, and the typed carrier files have no other gap;
      - L2: xlsx always goes to review.
- @producer wrote no standup entry; its role cannot write to `team/`.
- Self-checks at wrap-up (.venv, no host): all six ok.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. **T-102 changes M3–M5 and L2:** apply them to the plan (user or @pm), then @model-risk confirms. Only then does @producer build SUB-127–146.
2. **B-341 / B-342** (M6 "_" lines skipped anywhere; M7 valued date not validated): fix them with a P-### before the hold-out?
3. **B-343:** should a scanned or xlsx carrier loss run ever be accepted automatically? Today it never can be.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | The SUB-127–146 hold-out per T-102: gold first, checked .venv, `smoke_readers.py` first, scored once, paced; all 9 fields at 9/10 or better and 0 false completes |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md` |

## First 3 tasks next session

1. User decides on the T-102 changes and B-341/B-342. Apply them; @model-risk confirms the mix.
2. Hold-out SUB-127–146 per T-102:
   - `smoke_readers.py` first;
   - @producer builds the files;
   - @senior-underwriter writes the gold first and it is committed;
   - the run is scored once, paced, by `eval_holdout_127.py`.
3. Backlog Mediums on card wording (B-334, B-339, B-344).

## For the AI Engineer

- Pending proposals: none. B-341 and B-342 would need a P-###.
- Latest scores:
  - P-044 dev check SUB-147–152: 2 plain completes (typed PDF, typed text), 0 false completes.
  - Dev SUB-107–126 (comma-blind): 0 false completes, status automation 0/4, silent error rate 1.7%, automation rate 61.1%.
- Top failure to fix next: apply the T-102 changes so the hold-out can be built. A scanned carrier loss run can never auto-accept (B-343).
