# Next session

Written 2026-10-14 by the orchestrator at wrap-up. Wrap-up commit: `e5f720a` on `ai-team`, pushed to `origin/ai-team` (private). Budget rule 8: demo blockers only (weekly limit resets 2026-10-17). Standing rules: D-065 (backend + UI), D-069 (sandbox only). The frontend/ files are the user's and are never staged.

## Where we stopped

- D-080 (user's words) built:
  - B-297: a failed card shows "Not read — extraction failed" on the Not read, Not read by extraction and Needs human read lines. Self-check + sandbox screenshot D-080-B-297-failed-card-not-read.png. B-298 kept in backlog as cautious.
  - Freeze commit `d944583`, which includes `eval_holdout_087.py` (P-017 Part 4, X1), written before any submission or gold existed.
  - T-091: @producer built SUB-087 to SUB-106, all fictional. T-092: @senior-underwriter wrote the gold first. Both committed in `9e725e3` (V2).
  - T-093: scored once at `9e725e3` on Groq openai/gpt-oss-120b. 19 submissions read; SUB-101 is call_failed (reply_not_usable on all 3 attempts). Not published.
- **The run is not a valid score of the pipeline.** The orchestrator ran it with the system `python3` (Homebrew 3.14), not `.venv/bin/python`. Without pdfplumber, openpyxl or pytesseract, every PDF (11), xlsx (5) and scan (3) was "could not be opened" and the run carried on. Verified at wrap-up.
- @model-risk (memo `deliverables/model-risk/holdout-SUB-087-106.md`): T-027 veto **stands**. H1 is the environment; H2 is that no field reaches 9/10, even on the 5 fully read files. Route accuracy is 8/19 (own analysis, `route_holdout_087.py`), and only the holds were right.
- The run log `deliverables/ai-engineer/evals/SUB-087-106-holdout-run.log` is on disk; it is git-ignored and not committed.
- Missing standup entries this session: @producer, @senior-underwriter, @model-risk.
- Self-checks at wrap-up (.venv, no host): llm_extract, prepare, intake, package, workbench, points all ok.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 (call sentence in prepare.py, hash in older scorers, U1/V2 refusal) | with T-072; Part 4 built as eval_holdout_087.py |
| D-048 exits from `all_values_rejected` | no build task |
| D-050 producer-request rule | T-098 |
| B-258 no_match override control | after demo |

## Pending decisions for the user

1. The SUB-087–106 result: re-run this hold-out once in `.venv` (the gold is unchanged and the code is frozen), or build a new 20-file set. @model-risk calls this the user's choice.
2. H1 fix: make a missing reader library stop the run, with an import check and recorded library versions. This changes pipeline code and needs a P-### plus "approve change P-###". Under the freeze, it waits on decision 1 unless the user lifts the freeze.
3. Whether to publish anything from this run (the user said "do not publish").

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | H1 fixed, and one gold-first hold-out scored once in a checked environment has all 9 fields at 9/10 or better |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md` |

## First 3 tasks next session

1. Read the user's decision on the SUB-087–106 re-run (decision 1). If it is a re-run: confirm `.venv/bin/python` has pdfplumber, openpyxl and pytesseract, then run `regression_dev.py --holdout eval_holdout_087` once with it.
2. SUB-101 reply_not_usable ("'list'/'str' object has no attribute 'get'"): a model reply shape the parser does not handle. Write it up as a proposal; no change until the hold-out is closed.
3. B-299: show the TIV reason alongside the liquor referral.

## For the AI Engineer

- Pending proposals: none numbered. H1 (reader-library guard) needs a P-###.
- Latest eval scores (SUB-087–106, `9e725e3`, system python, **invalid environment**; hit / miss of 19, 1 call failed): named_insured 13/6, premises 5/14, effective_date 9/10, operations 9/10, sales 8/11, tiv 9/10, construction 10/9, year_built 9/10, loss_runs 10/3 (6 not credited), conflict 14/4, status 10/9. Route 8/19.
- Top failure to fix next: the run environment (H1), then SUB-101's reply shape.
