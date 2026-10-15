# Next session

Written 2026-10-15 by the orchestrator at wrap-up.

- Last code commit: `19729a6` on `ai-team`. **Not yet pushed.** The wrap-up commit and push were blocked by the session's permission check; see "Before anything else" below.
- Budget rule 8: demo blockers only (weekly limit resets 2026-10-17).
- Standing rules: D-065, D-069. The frontend/ files are the user's and are never staged.
- **Run every pipeline command with `.venv/bin/python`.**
- Model: qwen/qwen3.8-27b (P-039), `LLM_PACE_SECONDS=55`.
- SUB-087–126 is development data. The next hold-out is SUB-127–146, scored by `eval_holdout_127.py`: commas set aside in addresses (D-088); status safety and status automation reported apart (B-325, D-089). No gold exists yet.

## Before anything else

1. Another session wrote to the repo at 12:15 on 2026-10-15 and was not confirmed here. It added:
   - an @pm HANDOFF for T-101 at the end of `team/DISCUSSION.md`;
   - T-101 "LOB expansion plan" in `team/TASKS.md`;
   - `deliverables/pm/lob-expansion-plan.md`.

   Those files are uncommitted. The user decides whether they stand (decisions only from this session).
2. The uncommitted wrap-up files from this session:
   - `team/BACKLOG.md` (B-329 to B-335) and `team/STANDUP.md`;
   - this session's REVIEW entries at the end of `team/DISCUSSION.md`, mixed with the T-101 block;
   - `deliverables/model-risk/check-P-042-P-043-B-324.md` (LOOK-AGAIN 2);
   - `dev-SUB-107-126-D-089-final-qwen-qwen3-8-27b-cached.*`;
   - screenshot `D-089-P-042-P-043-B-324-resolve-conflict.png`;
   - this file.

## Where we stopped

- **D-089 built in the main session:**

  | Commit | What it holds |
  |---|---|
  | `964c159` | P-042, P-043, B-324, B-325 |
  | `3134328` | P-043 fix 1, plus the D-089 dev run |
  | `19729a6` | P-043 fix 2 |

  - **P-042:** the address check accepts "City TX" and "City, TX"; every address flag states its reason. @model-risk: passes.
  - **B-324:** an open conflict blocks every send until the underwriter chooses or enters the value on the card. The choice is logged as a "resolve" row with the run hash; then the file is approved again. @model-risk: passes.
  - **B-325:** the SUB-127–146 scorer reports status safety and status automation apart; committed before any gold. @model-risk: passes.
  - **P-043:** @model-risk **REJECT three times; H1 still open** (B-329). Each fix made more texts go to review, but non-carrier sentences still read as carrier loss runs, e.g. "My policy was issued by Northline Mutual.". The code as built is safer than before P-043; it only sends more to review.
  - @senior-underwriter UI: **APPROVE**, no High.
- **Dev re-check SUB-107–126** (qwen; the replies were taken uncached and paced at 55 s at `964c159`, then re-scored with no model call on `19729a6`; `dev-SUB-107-126-D-089-final-...-cached.md`):

  | Measure | Result |
  |---|---|
  | Status safety | **0 false completes** |
  | Status automation | 0 of 4 gold-complete files plain "complete" (none of the dev loss runs shows the carrier as issuer, so all go to review) |
  | Silent error rate | 10.0% under the frozen 107 scorer; 15 of the 18 are comma-only premises differences. With commas set aside: 1.7% (`analysis/silent-errors-D-089.md`) |
  | Automation rate | 52.8% |

  At `964c159`, before the P-043 fixes, status automation was 3 of 4, still with 0 false completes.
- Self-checks at wrap-up (.venv, no host): all six ok.

## Approved, not built

| Proposal | Task |
|---|---|
| P-006 EasyOCR fallback | T-062, T-068 |
| P-011 read-only published scores | T-072 |
| P-017 Parts 1–3 | with T-072 |
| D-048, D-050 (T-098), B-258 | as before |

## Pending decisions for the user

1. **P-043 approach (B-329).** Text patterns cannot prove who issued a document, and three rounds have not closed @model-risk's H1. Options:
   - (a) every loss-run date needs review unless the document is a recognised carrier format: safe, and status automation stays near 0 until carriers send structured runs;
   - (b) keep tightening patterns (more rounds);
   - (c) accept the current rule with H1 as a known limit, which needs @model-risk to agree.
2. Confirm or discard the other session's T-101 work.
3. The P-041 to P-043 trade-off: 0 false completes, but status automation 0 of 4 on dev.

## Open vetoes and what resolves each

| Task | Holder | Resolves when |
|---|---|---|
| T-027 | @model-risk (production) | P-043 H1 closed; then the SUB-127–146 hold-out (gold first, checked .venv, `smoke_readers.py` first, scored once) with all 9 fields at 9/10 or better and 0 false completes |
| T-082 | @responsible-ai (fairness) | As written in its veto message in `team/DISCUSSION.md` |

## First 3 tasks next session

1. The user commits and pushes the wrap-up files (or allows it), and decides the T-101 files.
2. The user decides the P-043 approach. Build it, @model-risk checks it, then a cached re-score of SUB-107–126 (no model call) for status safety and automation.
3. The hold-out SUB-127–146: @producer builds it, with carrier-issued loss-run headers, carrier_c and senior_referral routes; @senior-underwriter writes the gold first; the run is scored once, paced.

## For the AI Engineer

- Pending proposals: none drafted. P-043 needs your decision on the approach (B-329).
- Latest scores (dev SUB-107–126, qwen, `19729a6`): 0 false completes; status automation 0 of 4; silent error rate 1.7% with commas set aside (10% as scored by the frozen 107 scorer); automation rate 52.8%.
- Top failure to fix next: decide the P-043 approach. It is the open High, and it blocks status automation.
