# Next session

Written 2026-10-15 by the orchestrator at wrap-up. Wrap-up commit: `000cb7b` on `ai-team`, pushed to `origin/ai-team` (private).

- Budget rule 8: demo blockers only (weekly limit resets 2026-10-17).
- Standing rules: D-065, D-069. The frontend/ files are the user's and are never staged.
- **Run every pipeline command with `.venv/bin/python`.**
- Model: qwen/qwen3.8-27b (P-039), `LLM_PACE_SECONDS=55`. Check `echo $LLM_MODEL` at session start.
- SUB-087–106 and SUB-107–126 are development data. The next hold-out is SUB-127–146, scored by `eval_holdout_127.py` (committed in `201232d`; commas set aside in addresses).

## Where we stopped

- **D-088 built in the main session** (`201232d`, fixes `feb525d`).
  - **P-040:** a loss run needs a carrier, a policy period, a valued-as-of date, and claims (or the carrier's no-claims line). These are letters, never loss runs:
    - no-known-loss letters in any language;
    - no-claims statements from an agent, owner, applicant or letter (EN/ES/FR/PT).

    A date that only letters show is dropped. Anything unclear needs review.
  - **P-041:** status `complete — review pending` when every field is present but a value needs review or a conflict is open. Routing and sends are gated as before (`prepare.ready_to_route`). A review-pending file with an open conflict is not scored. The workbench card says what is pending.
- **Reviews:**
  - @model-risk: REJECT, then after the fixes LOOK-AGAIN **APPROVE WITH CHANGES**, no High (`deliverables/model-risk/check-P-040-P-041.md`).
  - @senior-underwriter UI: **APPROVE**, no High.
  - Screenshot: `D-088-P-040-P-041-review-pending.png`.
- **Dev re-check SUB-107–126** (qwen, paced, uncached; 4 replies reused after a restart; `dev-SUB-107-126-D-088-qwen-qwen3-8-27b.md`):

  | Measure | Hold-out (before) | D-088 re-check |
  |---|---|---|
  | Status accuracy | 16/20, 4 false completes | 16/20, **0 false completes**, 4 false incompletes |
  | Loss-run misses | 2 | 0 |
  | Silent error rate | 2.2% | 1.1% |
  | Automation rate | 58.3% | 55.6% |

  The 4 false incompletes (107, 110, 116, 120) have one cause. The P-002 address check needs "City, TX" with a comma and qwen writes "Austin TX". Every premises value is therefore flagged "address invalid", so no file can be complete. **P-042 is drafted** (`deliverables/ai-engineer/proposal-P-042.md`), not approved.
- Self-checks at wrap-up (.venv, no host): all six ok.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. **P-042:** the address check accepts "City TX" without a comma and gives a reason when it flags. Type `approve change P-042` to approve.
2. **B-324:** confirm that "complete — review pending" with no open conflict can still be sent after the approve tick, as complete was.
3. **B-325:** how the SUB-127 scorer treats a gold "complete — review pending". Decide before that gold.
4. **B-322/B-323:** whether an "unclear" loss-run source should hold the file, not just go to review (M5, M6).
5. B-313: as before.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | H1/H2 closed (done: D-088, APPROVE WITH CHANGES); the address comparison fixed before gold (done: `eval_holdout_127.py`); a new 20-file hold-out SUB-127–146, gold first, checked .venv, `smoke_readers.py` first, scored once, all 9 fields at 9/10 or better and 0 false completes |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md` |

## First 3 tasks next session

1. User decides P-042. If approved: build it, @model-risk checks it, then a quick dev re-check from the D-088 cached replies (no model call needed for this change).
2. Decide B-324/B-325. Then the hold-out SUB-127–146: @producer builds it, with carrier_c and senior_referral routes in the gold; @senior-underwriter writes the gold first; the run is scored once, paced.
3. B-327/B-328 card wording, and the missing standup entries from the earlier hold-out turns (@producer).

## For the AI Engineer

- Pending proposals: **P-042** (address check without a comma).
- Latest scores (D-088 dev re-check, qwen, SUB-107–126): status 16/20 with 0 false completes, silent error rate 1.1%, automation rate 55.6%. Fields as the hold-out except loss runs: 10 hits, 0 misses, 10 not credited. Premises 0/20 under the frozen 107 scorer's comma rule.
- Top failure to fix next: the address check flags every comma-less address (P-042), which blocks every complete.
