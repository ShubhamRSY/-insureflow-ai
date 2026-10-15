# @model-risk check — P-040 (H1) and P-041 (H2), D-088

- Date: 2026-10-15. Reviewer: @model-risk (independent; author messages not read).
- Deliverable: commit 201232d (ai-team): `underwriting_pipeline/ai/prepare.py`, `app/workbench.py`, `app/package.py`, `models/points.py`.
- Evidence: the four self-checks pass with LLM_* unset (`prepare ok`, `workbench ok`, `package ok`, `points ok`). Own probes on temp copies with a stubbed model reply (no model call). `git status` the same before and after; no file under the repo newer than the probe start.
- Not a production approval. The T-027 veto stands until a new hold-out passes.

## Verdict: REJECT (as built). Two High findings; the remedies are small.

## High findings

### H1. The no-known-loss rule catches four phrases, not letters "in any language". A letter it misses becomes sendable.
- Criterion 1: letters saying there are no known losses, in any language, are never loss runs; the field stays missing and the file stays incomplete.
- `NKL_LETTER` is a list of phrases. The SUB-112 and SUB-123 letters are caught only by their heading "Carta de pérdidas". The body line "Sin reclamos reportados …" is not on the list.
- Probe: `loss_run_kind` on 12 realistic letters. Only "no-loss letter" counted as a letter. Each of these came back "unclear": the SUB-112 letter with its heading changed to "Historial de pérdidas", "No claims letter", "Loss-free letter", "no losses known", "sin siniestros", "No se conocen pérdidas", "Carta de no siniestralidad", French, Portuguese, and an English NKL letter that names a prior carrier and period.
- End to end (stubbed reply, temp folder): SUB-112 with the changed heading gives status `complete — review pending` and loss-run 2026-09-30 kept. `ready_to_route` is True and `request` is None. So the producer is never asked for loss runs, and after the approve tick the file passes `agency_problem`. Unchanged SUB-112 gives `incomplete` with the request drafted, which is correct.
- Related: the date is dropped only when the model cites the letter file. If the model cites `email.md` for a date the letter supplies, the date is kept with review (probe).
- To resolve:
  - (a) Treat a no-claims statement that does not come from a carrier as a letter. Examples: "sin reclamos", "no claims … to our knowledge / según el solicitante / per prior agent", or "letter/carta" next to a no-claims line.
  - (b) Or: when the loss-run source is "unclear", `ready_to_route` returns False and the file is held until the underwriter confirms.
  - (c) Drop the date when the value or quote appears only in letter files, whatever file the model cites.
  - Add self-checks with the SUB-112 and SUB-123 letters minus their headings, plus at least three of the variants above.

### H2. A file with an open conflict is now given a risk score. P-041 removed this control.
- Before P-041, an open conflict made the status `incomplete`. `points.not_scored_reason` then returned "file incomplete: open conflict on X" (D-070: not scored when incomplete).
- Under P-041 the same file is `complete — review pending`, and `not_scored_reason` returns None for that status.
- Probe: all fields present plus an unresolved square_feet conflict gives `score_run(...)["scored"] == True`. A number now shows on a file whose values are still disputed.
- The self-check at `points.py:203` still tests the old shape (status `incomplete` with a conflict). That shape no longer occurs, so the test hides the change.
- To resolve: for `REVIEW_PENDING`, return "open conflict on X" when any conflict is unresolved, and add a self-check on a review-pending report with an open conflict. Values that only need review may stay scored, as P-041 intends.

## Medium / Low (backlog, one line each)
- M1 (D-065 item 2): a review-pending card with an open conflict gives the send-refusal reason "the file is incomplete (a required field is empty)" (`workbench._no_send_reason`), and the match says "missing information". Both reasons are wrong.
- M2 (decision record): `ready_to_route` lets a file that P-041 calls not complete pass the account-manager gate. This matches "sends stay gated as now", but D-017 says a send only when "complete". The user should confirm the wording in DECISIONS.md.
- M3 (scorer): in `eval_holdout_127.py`, a gold status "complete — review pending" counts as a gold "complete", but the report has `complete=False`. That is always a miss. Settle the gold vocabulary before the SUB-127+ gold is written.
- M4 (P-040 positive test is word-based): an applicant statement that names a carrier and period and says "no claims" counts as a `loss_run` (probe). The test never checks that the statement comes from the carrier.
- L1: across the inbox, 41 of 56 loss-run files read "unclear" and 5 read "loss_run", because synthetic runs name no carrier or period. Most files will be review pending, so expect status and automation rates to move.
- L2: `extra` (a question for the producer) with every field present gives `incomplete`. The criterion says incomplete only when a field is missing; this is a defensible reading, but it should be recorded.
- L3: a letter phrase next to a full set of loss-run parts reads "unclear" and keeps the date. That departs from "never", though the reading is defensible for a carrier run that says "no known losses".

## What would change the verdict
H1 and H2 closed as above, with self-checks; then a re-check by @model-risk (High only).
