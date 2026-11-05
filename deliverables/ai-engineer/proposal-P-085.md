# P-085 — A file with an open conflict never reads "complete — review pending"; the card label matches the routing state (B-531)

- Author: orchestrator, drafted 2026-11-05 at @user's request (D-168). **Draft for @user to read. Not approved, not built.**
- Source: @model-risk memo `deliverables/model-risk/T-027-memo-T-128.md` M2; backlog B-531. D-167: must close before any send-enabled mode.
- Direction: **stricter only, display only.** No gate, route, status value or score changes. The card can say "complete" less often, never more.
- Approval: the user types `approve change P-085`. The frozen build changes (`workbench.py`), so @model-risk checks it before the lift conditions hold again (D-167).

## Problem

SUB-554, 558 and 562 (T-128) each had an open planted conflict. Their gold says incomplete / hold. The card read **"Complete — review pending: open conflict: …"**.

- `prepare.py:1493` sets `pending` when every field is present and there is an open conflict **or** a value to review. Both cases get status `REVIEW_PENDING` ("complete — review pending").
- `ready_to_route()` (`prepare.py:669`) is already False for the open-conflict case, so nothing was routed or sent. Only the words are wrong.
- The card shows the raw status twice: `workbench.py:1331` ("Saved run: status complete — review pending") and `review_pending_html()` (`workbench.py:868-875`).

## Change (`underwriting_pipeline/app/workbench.py` only)

1. One helper, `card_status(report)`, gives the words the card shows:
   - status `REVIEW_PENDING` and `ready_to_route(report)` is False → **"Held — open conflict: <topics in plain words>. Not complete. Resolve each conflict, then approve."**
   - status `REVIEW_PENDING` and routable → unchanged ("Complete — review pending: values to review: …").
   - every other status → unchanged.
2. Line 1331 and `review_pending_html()` use that helper. The saved run keeps its status string, and the change log records it unchanged.
3. Invariant, asserted in the self-check: **the card shows the word "complete" only when `ready_to_route(report)` is True.**
4. D-065: one "What's new" line; a Playwright screenshot of a held card in a temp copy (D-069), named `P-085-*.png`; @senior-underwriter UI check, High only.

## Not changed

- `prepare.py`, the stored `status`, `ready_to_route()`, the send gate, `points.py`, scorer v11 and the gold. T-128 scores re-mark identically by construction.
- After every conflict is resolved, the P-081 path (D-157) still reads "complete — review pending", with its reason.

## Option considered and not recommended

- **B. Store status `incomplete` when a conflict is open (`prepare.py`).** This matches the gold more closely. It also changes a value scorer v11 reads, the P-081 resolve path (`package.py:1068`), `points.py:116` and the producer-request logic. It is a bigger change, with a score effect that would need its own ruling.

## Tests (dev only, temp dirs)

- A fixture shaped like 554/558/562 (all fields present, one open conflict): neither the card HTML nor the status line contains "complete" in any case. The card shows "Held — open conflict: <topic>".
- The same file with every conflict resolved: "Complete — review pending" plus the resolved reason (P-081).
- A file with only a value to review and no conflict: label unchanged.
- An invariant loop over every status, with and without an open conflict: "complete" appears ⇔ `ready_to_route` is True.
- `tests/pipeline` and every module self-check pass. Re-marking the T-128 run gives 0 differences.

## Decision for @user

1. `approve change P-085` (option A, recommended), or ask for option B instead, or defer.
