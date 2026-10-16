# Next session

Written 2026-10-15 by the orchestrator at wrap-up. Wrap-up commit: `d0e362b` on `ai-team`, pushed to `origin/ai-team` (private).

- Budget rule 8: demo blockers only (weekly limit resets 2026-10-17).
- Standing rules: D-065, D-069. One AI session on this repo (D-090). The frontend/ files and `.claude/settings.json` are the user's and are never staged.
- **Run every pipeline command with `.venv/bin/python`.**
- Model: qwen/qwen3.8-27b (P-039), `LLM_PACE_SECONDS=55`.

## Frozen for the hold-out

| What | Commit |
|---|---|
| **Hold-out code** (last commit touching `underwriting_pipeline/`; @model-risk APPROVE as frozen hold-out code) | `3a7741506c72ae966654f529d56f3ab242389d7f` |
| **Hold-out files and gold** SUB-127–146 | `bd9168e13fcd91a4e64421a69b1d8284798ab01a` |

- Do not change `underwriting_pipeline/` before the hold-out run. A change means a new freeze and a user decision.
- SUB-127–146 have not been opened, run or changed since the gold was frozen.

## Where we stopped

- **D-093**
  - B-349 confirmed (`28b6d4d`, `ecf69c2` are within D-092 1c).
  - **P-046:** each loss-run document is judged separately. Plain "complete" only when every loss-run document is accepted. An undated, copy/sample, scan/spreadsheet or unrecognised run beside an accepted one gives "complete — review pending" with that document's reason. No-known-loss letters are not loss-run documents (P-040).
  - Built at `57d56b9`. @model-risk REJECT twice (H1 letter words in a carrier run; H2 file-name-only detection; H3 undated run pasted elsewhere), fixed at `cb7b259` and `3a77415`. **H1–H3 resolved; APPROVE `3a77415`.**
  - Dev file SUB-153 (dated Carrier A plus undated Carrier B): @producer built it, @senior-underwriter wrote the gold first.
- **Dev check SUB-147–153** (`dev-SUB-147-153-D-093c-cached.md`; SUB-153 one live paced qwen call, the rest cached):
  - 0 false completes; plain complete on 147 and 149.
  - SUB-153 is "complete — review pending" naming `loss-runs-b.md` as undated. Its email.md also adds an undated-history reason (noise, L7).
- @producer cannot write `team/STANDUP.md`, so it has no standup entry for its SUB-153 turn.
- Self-checks at wrap-up (.venv, no host): all six ok.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. **When to run the hold-out SUB-127–146** on the frozen code `3a77415`.
2. **B-350 (M3):** a prefixed carrier header ("> ", "#", "Fwd:") with letter words is still excused as a letter. @model-risk says this needs a P-### after the hold-out.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | SUB-127–146 run once on `3a77415` (`smoke_readers.py` first, checked .venv, paced) with all 9 fields at 9/10 or better and 0 false completes |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md` |

## First 3 tasks next session

1. Confirm HEAD's `underwriting_pipeline/` equals `3a77415` (`git diff 3a77415 HEAD -- underwriting_pipeline/` is empty). Run `smoke_readers.py` (8 file types, uncached).
2. Hold-out run: one paced qwen run of SUB-127–146 with `regression_dev.py --holdout eval_holdout_127`, recording commit, model, Python and library versions. Retry failed calls only.
3. @model-risk scores it from the frozen gold `bd9168e`: per field, status safety (false completes must be 0), status automation, silent error rate, automation rate and route. It then states whether T-027 is lifted.

## For the AI Engineer

- Pending proposals: none. B-350 may need one after the hold-out.
- Latest scores: dev SUB-147–153, 0 false completes and 2 plain completes. Dev SUB-107–126 (comma-blind): 0 false completes, silent error rate 1.7%, automation rate 61.1%.
- Top failure to fix next: none blocking. Next is the frozen hold-out run (code `3a77415`, gold `bd9168e`).
