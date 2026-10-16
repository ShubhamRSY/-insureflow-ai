# Next session

Written 2026-10-15 by the orchestrator at wrap-up. Wrap-up commit: `8b921b7` on `ai-team`, pushed to `origin/ai-team` (private).

- Budget rule 8: demo blockers only (weekly limit resets 2026-10-17).
- Standing rules: D-065, D-069. One AI session on this repo (D-090). The frontend/ files and `.claude/settings.json` are the user's and are never staged.
- **Run every pipeline command with `.venv/bin/python`.**
- Model: qwen/qwen3.8-27b (P-039), `LLM_PACE_SECONDS=55`.

## Where we stopped

- **T-027 official hold-out SUB-127–146 is done:** run once and scored once on frozen code `3a77415` with gold `bd9168e`, following the rules the user typed.
  - Checks before the run:
    - smoke_readers 8/8.
    - No cached replies for SUB-127–146.
  - Calls: 20 model calls, 0 failed. One 429 on SUB-145 was posted again once.
  - Retry limit: the frozen code retries more than the user's rule allows, so `deliverables/ai-engineer/evals/T-027/t027_run.py` capped retries from outside the pipeline. No pipeline file was edited.
  - Score files: `SUB-127-146-holdout.md` and `.json`. Run record and per-file reports: `deliverables/ai-engineer/evals/T-027/`.
- **Results:**
  - 0 false completes.
  - Fields at 9/10 or better: 3 of 9 (named insured 20/20, effective date 18, sales 18). Below: premises 17, tiv 17, construction 17, year built 16, operations 12, loss runs 5 hit / 3 miss / 12 not credited.
  - Silent error rate 3.9% (7 of 180, all in operations). Automation rate 73.3%. Status automation 4 of 6.
  - Route 14/20. carrier_c 0 of 2 and senior_referral 0 of 2 (both held).
  - Loss runs: 5 of 5 typed carrier runs accepted. Scans, letters and undated runs went to review.
  - Cost: $0 (free tier). About $0.0021 per file at the 8.3 list prices; 1,778 tokens per call on average.
- **@model-risk KEEP** (`deliverables/model-risk/T-027-holdout-127-memo.md`, OBJECTION in `team/DISCUSSION.md`):
  - H1: the 9/10 floor is not met.
  - H2: operations drops underwriting-material qualifiers (liquor, beer and wine, seats, units) at confidence 1.0, unflagged.
  - M1–M6 and L1–L4 are in the memo. They are not yet in `team/BACKLOG.md`.
- **SUB-127–146 is now development data.**
- @model-risk has no `team/STANDUP.md` entry for its T-027 turn this session.
- Self-checks at wrap-up (.venv, no host): all six ok.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. Whether to raise a P-### for H2 (operations keeps the full stated text, with a test on these shapes). This is @model-risk's resolution path.
2. B-350 (M3 from D-093): prefixed carrier header with letter words. @model-risk said it needs a P-### after the hold-out.
3. M5 scorer convention (null on gold "missing" for sales/tiv/construction/year built) before the next gold set. It must never be applied backward.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | An approved P-### for H2 is built. @senior-underwriter sets a gold convention for qualifiers. A fresh 20-file hold-out runs under the same rules with all 9 fields at 9/10 or better and 0 false completes. |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md` |

## First 3 tasks next session

1. @pm: route the memo's M1–M6 and L1–L4 to `team/BACKLOG.md` (one line each), and record the T-027 KEEP on the T-027 card.
2. @ai-engineer-assistant: write the P-### for H2 (operations qualifiers). It is a proposal only, waiting for the user's "approve change P-###".
3. @senior-underwriter: gold conventions for operations qualifiers and M5 (missing fields), written before any new hold-out gold.

## For the AI Engineer

- Pending proposals: none yet. H2 (operations) and B-350 each need a P-###.
- Latest scores: hold-out SUB-127–146 has 0 false completes, 3 of 9 fields at 9/10, silent error rate 3.9%, automation 73.3%, route 14/20.
- Top failure to fix next: operations shortened at confidence 1.0 (7 silent errors).
