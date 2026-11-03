# @model-risk check — T-129 (P-079, P-080, P-081; D-155, D-156, D-157)

- Date: 2026-11-03. Reviewer: @model-risk (independent). Commit 50c47b2d (branch pilot-integration), code diff vs e48edf36.
- Scope: the deliverable only (code, as-built, T-129 evidence, screenshots, memo T-121 H1/H2). No model call, no hold-out. All runs on a temp copy (`git archive 50c47b2d`) in the scratchpad (D-069).
- **Not a production approval. The T-027 veto stands.**

## Verdict: REJECT (3 High). D-155 (c) and D-157 conditions are not met as built; per the user's words, STOP and show @user.

## What I re-ran
- Self-checks on the temp copy: `scope ok scope-v6`, `package ok`, `prepare ok`.
- Dev re-check outputs (before v5 / after v6): DEV-01..05 in scope, DEV-06..12 manual intake; 533 and hwy-second now caught by Part A (rule), not by the model count. Matches D-155 (d), (e), (f) shapes as far as the dev set goes.
- Quick-17 baseline vs after: `counted` blocks equal; differences are run ids, cache, per-row metadata only.
- Pure-function probes (`scope._place_words`, `prepare._shows_one_address` / `_address_count`, `package.with_resolutions` / `resolved_to_review`, `package.ack_problem`). Results below.

## High findings

**H1 (P-081, D-157 "every acknowledgment incl. the operations C1 ack"): an operations value entered by a conflict resolve is never acknowledged, and the file is now routable for the account manager.**
- `needs_review_ids` / `is_review_row` list operations only when the row has a value. When the saved run's operations is empty because of the conflict (the SUB-133 "Missing: operations" shape), the saved row has no value, so:
  - the workbench approve (`workbench.py` ~line 624, `needs_review_ids(saved)`) does not list operations for acknowledgment;
  - the send gate (`send_to_carrier` → `ack_problem(submission, report)` with the raw saved run) does not require it.
- Probe: saved run incomplete, operations empty, one operations conflict resolved by UW-002 on this run hash → `with_resolutions` gives `complete — review pending`, `ready_to_route` True; with an approve that acknowledged nothing, `ack_problem(saved)` = `''` (pass), while `ack_problem(resolved)` = "1 value needs review and is not acknowledged (operations)".
- Before P-081 the account-manager path was shut for this file (`agency_problem`: "the file is not complete"); P-081 opens it without the C1 ack.
- Resolves it: the approve list and the send-gate ack check read the resolved run (`with_resolutions(saved)`) so that a resolved operations value is a C1 review row, the same list at approve and at send; a self-check where a resolved-operations file is refused at send until operations is acknowledged on this run hash, then allowed.

**H2 (P-081, D-157 "card text matches the true state", fail closed): the workbench promotes files the send gate does not.**
- `workbench.saved_report` sets `"extra": []` ("not stored in the saved run") over the saved value. `resolved_to_review` relies on `saved.get("extra") == []` to fail closed on items still asked of the producer and on runs saved before P-081. On the card that check is always true.
- Probe: saved run with `extra: ["hours"]` and one resolved conflict → gate view (`prepare.read_saved_run`) stays `incomplete`; card view reads `complete — review pending` with RESOLVED_REASON. A run saved before P-081 (no `extra`) is also promoted on the card.
- Effect: the card says "complete — review pending" and "Withdrawn: … nothing is asked of the producer", and `act()` refuses the producer-draft approve, while the account-manager gate refuses the send as "not complete". The producer is never asked for the owed items (restaurant files: cooking equipment, hood, sprinklers, liquor, hours), and every existing saved run is affected.
- Resolves it: `saved_report` passes the saved `extra` through (`saved.get("extra")`, `None` when absent), or the card/`act()` decision reads `prepare.read_saved_run`; a workbench self-check with `extra: ["hours"]` and a pre-P-081 run (no `extra`) showing the draft still offered and the status unchanged.

**H3 (P-080, memo T-121 H2 step 1; D-155 (c)): `_bare_label` treats a short sentence as a label, so the line after a carrier sentence is skipped whole.**
- `_bare_label` = ≤60 chars and (ends with ":" or has no ":"). "Carrier A loss run attached." has no colon, so it counts as a "bare role label" and the next line is skipped.
- Probe (`_place_words`, application at 100 Main St): `"Carrier A loss run attached.\nWe also keep stock at 2215 Leonard Rd, Bryan."` → **None** (missed). The SUB-533 shape split over two lines in one email paragraph. Memo H2 named this paragraph case and asked for `label_above` only for "a bare role label with no value of its own".
- Why High now: P-079 removes the backstop. Before, a count of 1 with a sentence quote went to manual intake; now it passes on the premises quote. A second address the rules miss now stays in scope unless the model counts 2, which is the single-model dependence H2 was raised against.
- Resolves it: a label means a line ending in ":" (or a name-only line with no sentence punctuation and no verb, e.g. "ABC Insurance Agency"), not any colon-free sentence; add the two-line 533 shape (carrier / agent / prior / loss-run sentence on the line above) as a dev positive and a self-check.

## Medium / Low (backlog, one line each)
- M1: a role word in the same sentence still hides a second address ("Carrier A loss run attached and we also keep stock at 2215 Leonard Rd") and so does "home" ("the owner's home at 9 Oak Ave"); state as a known residual in the as-built.
- M2: memo H1 step 2 near-pass negatives missing from the dev set: a count of 1 whose only valid address is a mailing or PO Box line, and a null count (self-checks only).
- M3: dev re-check replies are not saved in the repo, so the before/after cannot be replayed by a reviewer; save them under evals/T-129 (dev only).
- L1: `HIGHWAY` misses "Spur" (memo listed it; "100 Spur 191, Kerrville TX 78028" fails the shape) and lowercase "highway".
- L2: `_shows_one_address` passes a count quote that names a second place without a number ("100 Main St and the lot next door", "…; warehouse at 9 Oak"). Part A word rules are the only net there.

## Decision
REJECT for T-129. One look-again (D-129) after H1–H3 are fixed with their self-checks. D-155 (a), (b), (d), (e), (f) and D-156 "stricter only" hold on the evidence. D-155 (c) fails on H3, and D-157 fails on H1 and H2. Not a production approval; T-027 veto stands.

Note: the dispatch said not to edit any file except this report, so this verdict is not appended to `team/DISCUSSION.md`. The orchestrator should append it as TYPE: OBJECTION to @ai-engineer-assistant.
