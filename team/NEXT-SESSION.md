# Next session

Written 2026-10-15 by the orchestrator at wrap-up. Wrap-up commit: `380d6e5` on `ai-team`. **Not pushed:** the push was refused by the session's permission check; the user pushes `git push -u origin ai-team` (origin is private). Budget rule 8: demo blockers only (weekly limit resets 2026-10-17). Standing rules: D-065, D-069. The frontend/ files are the user's and are never staged. **Run every pipeline command with `.venv/bin/python`.** Model: qwen/qwen3.8-27b (P-039, D-087), `LLM_PACE_SECONDS=55`; check with `echo $LLM_MODEL` at session start.

## Where we stopped

- `smoke_readers.py` on qwen, uncached: 8 of 8 file types read.
- Pipeline frozen at `ea921ea`.
- SUB-107–126 built by @producer (builder script: `deliverables/producer/build_SUB-107-126.py`).
- Gold written by @senior-underwriter. Submissions and gold committed in `178aa28` before any extraction.
- Hold-out run once, paced: 20 of 20 calls ok, no cache. Environment recorded in `SUB-107-126-run-env.txt`.
- @model-risk scored it in `deliverables/model-risk/holdout-SUB-107-126.md`. **The T-027 veto stands.**

  Label: 9 of 9 extracted fields scored; claims not read; loss runs = date only.

  | Field | Hits |
  |---|---|
  | Named insured | 20/20 |
  | Premises | 0/20 |
  | Effective date | 18/19 |
  | Operations | 17/20 |
  | Sales | 18/20 |
  | TIV | 19/20 |
  | Construction | 20/20 |
  | Year built | 17/20 |
  | Loss runs | 10/12 |

  | Measure | Result |
  |---|---|
  | Fields at the D-013 floor (9/10) | 5 of 9 |
  | Silent error rate | 2.2% (4/180) |
  | Automation rate | 58.3% |
  | Status | 16/20, all 4 misses false completes (111, 112, 123, 125) |
  | Route | 12/20 |

  - H1: Spanish no-known-loss letters (112, 123) are read as loss runs, so the file goes complete.
  - H2: needs-review values and missed conflicts (111 sales, 125 effective date) still leave a file complete.
  - M1: premises misses are mostly a comma mismatch ("Austin TX" vs "Austin, TX"). Ignoring commas it is 16/20.
- Coverage gap (orchestrator note): the gold has no carrier_c and no senior_referral route, though @producer was asked to include both.
- Missing standup entries for this session's turns: @producer, @senior-underwriter (gold), @model-risk (hold-out).
- Self-checks at wrap-up (.venv, no host): all six ok.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. Whether to accept @model-risk's path to lift T-027:
   - H1 and H2 fixed under approved P-### changes.
   - The address comparison fixed before the next gold.
   - A new 20-file hold-out.
2. B-313: confirm the P-037 "needs-review conflict" reading.
3. Whether the next hold-out's gold must cover every route, including carrier_c and senior_referral.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | H1 and H2 closed with approved P-### changes and tests; the address comparison fixed before the next gold; a new 20-file hold-out with all 9 fields at 9/10 or better and no false completes |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md` |

## First 3 tasks next session

1. User pushes `ai-team` if not done. The three missing standup entries are written by their roles.
2. @ai-engineer-assistant drafts proposals for H1 (no-known-loss letter is not a loss run, Spanish included) and H2 (needs-review or a missed conflict blocks complete).
3. Address comparison: a scorer for the next hold-out that sets commas aside, written before its gold (do not edit `eval_holdout_107.py`).

## For the AI Engineer

- Pending proposals: none drafted yet for H1/H2.
- Latest hold-out (qwen, SUB-107–126): see the table above. Silent 2.2%, automation 58.3%, status 16/20, route 12/20.
- Top failure to fix next: false completes. Spanish no-known-loss letters are read as loss runs (H1), and needs-review values or missed conflicts don't block complete (H2).
