# Check — P-076 (D-135, T-027 C1): operations always flagged and acknowledged before send

- Reviewer: @model-risk, 2026-10-27. Independent check of branch `p076`, commit 99efa4d (`git diff pilot-integration...p076`).
- **Verdict: APPROVE WITH CHANGES.** The code path is correct and stricter only. H1 must close before `p076` merges to `pilot-integration`.
- This is a check of an approved proposal. It is not a production approval, and the T-027 veto stands (C2–C7 are still open).

## What I re-ran (no model call; D-069: `git status` was clean before and after)
- `prepare.py`, `package.py`, `workbench.py` self-checks: all ok.
- `pytest tests/pipeline -q`: 93 passed. This includes `test_request_equality.py`, so 0 of 143 requests changed.
- Diff touches no `llm_extract.py`, prompt/`SYSTEM`/`request_for`, `eval_holdout_*`, lint, gold or `simulation/inbox` file.
- `flag_operations` is called after `apply_cooking_rule` (P-075), `check_operations`, the conflict loop (P-074), merges and the address steps, and just before `completeness`/`review`. Nothing later in `process_submission` writes the operations row. Status therefore goes complete → "complete — review pending" through the existing `review` list. No routing, appetite or gate code changed.
- `reason` is never overwritten, and `policy_review` is a separate boolean that is persisted in `_saved_payload`. That meets the C2 separation. The card joins the specific reason with the policy note, and the screenshot (SUB-301) shows both plus the ack box.
- The send refusal test (SUB-376) is refused with "(operations)", then allowed after the acknowledgment on the current run hash. It reuses `needs_review_ids`/`ack_problem`. The pilot per-value confirm is unchanged.

## High

**H1 — Saved runs from before P-076 can still be sent without an operations acknowledgment.** Owner: @ai-engineer-assistant / @software-engineer.
The send gate (`ack_problem` → `needs_review_ids`) reads `needs_review` from the saved run, so the flag is only enforced on new runs. I recomputed this on the worktree's `deliverables/data-engineer/extractions/`. 17 saved runs have an operations value, and all 17 have `needs_review=False`. SUB-009 and SUB-010 are plain `complete`. All 17 would pass the acknowledgment gate with no operations ack, and the card shows no ack box for them. The as-built calls this a "known limit". It breaks the acceptance line "no file is plain complete from an auto-accepted operations value; the send is refused until operations is acknowledged".
**Remediation (choose one, stricter only, no `ai/` change needed):**
(a) In `package.needs_review_ids`, always include `operations` when its value is non-empty. The card must also show the ack box for that row, with the policy note.
(b) Refuse the send of any saved run whose valued operations row lacks `policy_review`, with the plain reason "saved before P-076; re-extract", shown on the card.
Either way, add one self-check that uses a pre-P-076-shaped saved run: send refused until acknowledged or re-extracted.

## Medium / Low (backlog, one line each)
- M1: The rule-copied (P-075) and scan (P-037) paths are tested on `flag_operations` directly, not end to end through `process_submission`. That is acceptable because the flag is unconditional on value, but one end-to-end rule-copied case would close it.
- L1: The workbench review-note expression is a single dense conditional. Split it for readability. The behaviour is verified by the self-check.
- L2: The C2 counting script must treat the P-075 "copied by a rule" note explicitly (specific or not) when it is frozen before T-120 gold. Decide that now, not after the score.
