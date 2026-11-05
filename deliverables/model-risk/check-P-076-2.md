# Check 2 (look-again, D-129) — P-076 (D-135, T-027 C1)

- Reviewer: @model-risk, 2026-10-27. Branch `p076`, commit c9c8e17. Fix diff `git diff 99efa4d c9c8e17`.
- **Verdict: APPROVE.** H1 is closed. The fix adds no new High finding. M1, L1 and L2 from check-P-076.md stay in the backlog.
- This is a check of an approved proposal. It is not a production approval. The T-027 veto stands, because C2–C7 are still open.

## H1: closed (option (a))
- `package.is_review_row` lists `operations` whenever it has a value. It does this whether or not `needs_review` or `policy_review` is set. `needs_review_ids` uses it, and that one list feeds three places: the approve validation (`workbench.record_decision`), the send gate (`ack_problem` → `send_to_carrier`), and the card's ack box and note (`workbench.render`).
- I recomputed this on the saved runs in `deliverables/data-engineer/extractions/`. Of the 17 runs that have an operations value, 17 now list `operations`. In check 1 the count was 0.
- An approve logged before this fix, without `operations` in `acknowledged`, now refuses the send on the same run hash. A new approve is refused until `operations` is acknowledged. Both changes are stricter only.
- A new self-check covers this: SUB-377 is a pre-P-076-shaped run, `complete`, with no flag on operations. The send is refused with "(operations) … not acknowledged" and is allowed after the acknowledgment. A card self-check confirms that the ack box and the policy note show on such a run.

## New High: none
- The only file changes are in `app/package.py` and `app/workbench.py`. There is no change to `ai/`, any prompt, `llm_extract.py`, the scorers, the gold or the inbox, so no model behaviour or score changes. The edits to existing self-checks only add `operations` to the acks, which matches the stricter rule. No assertion was weakened.
- The pilot per-value confirm is unchanged. The cooking-equipment acknowledgment is unchanged.
- Re-run with no model call: the `prepare`, `package` and `workbench` self-checks pass. `pytest tests/pipeline` passes 93. `git status` was clean before and after (D-069).

## Medium / Low (backlog)
- M2: A run saved before P-076 still shows the status label "complete", not "complete — review pending", because `review_pending_html` reads `needs_review`. The gate and the ack box enforce the review, so this is a label-only gap. Re-extract or relabel when convenient.
