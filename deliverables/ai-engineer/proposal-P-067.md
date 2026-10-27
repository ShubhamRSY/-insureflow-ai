# P-067 — Loss-run dates read from a scan: keep a cited, parseable date for review, and say on the card why one was dropped

- Author: orchestrator (main session), from the T-110 re-measure of T-108 (B-433). **Not approved, not built.** Development data only (SUB-206–237). Not a production approval; @model-risk can still block it.
- Raised because B-433's rule is: operations **and** loss_runs ≥18/20 after the v9 re-measure → close as a measurement issue; otherwise draft a P-### for the **real misses only** and stop for the user's approval. The re-measure gave operations 10/20 and loss_runs 16/20, so this proposal is that P-###. Evidence: `deliverables/ai-engineer/analysis/T-110-v9-remeasure.md`.

## Problem (real misses only)

Four files are `not_credited` on the loss-run date. Three are the pipeline throwing away a date its own documents contain:

| File | Model read | What dropped it | Gold |
|---|---|---|---|
| SUB-217 | `2026-08-05`, quote "Valued: 2026-08-05" (the line is in the OCR text) | the OCR word list scores that date token **0.0**, so `confidence 0.00 is under 0.75` (`llm_extract.py:30,499`) | 2026-08-05 |
| SUB-209 | `2026-06-15`, quote "Valuation date: 2026~06-15" | OCR garbles the date → word score 0.35 < 0.75, same gate | 2026-06-15 |
| SUB-225 | `2026-06-91` (OCR reads the day as 91) | `value_in_span` → "the date does not parse" (`llm_extract.py:397`) | 2026-06-01 |
| SUB-211 | nothing | image-only PDF is `needs_human`: no text, no model value | 2026-07-20 |

Two further problems sit on the same path:

1. The reason never reaches the underwriter. `prepare.py:1057-1059` skips a rejected row, so the card shows `value=None, reason=None` — "missing" with no why, which D-065 asks every block to have. `llm_extract` already computed the reason ("confidence 0.35 is under 0.75", "the date does not parse").
2. SUB-211's date is not a defect and is not proposed here: the file is `needs_human` by design (B-343), and a human transcription is what gold was written from.

## Change

1. **Card reason (no scoring effect).** When a model value is rejected, `prepare` keeps the row's `reason`, `model_confidence` and `ocr_cited_confidence` on the merged field (value stays `None`, `needs_review` stays True) so the workbench card can say it in plain words: "loss-run date read from the scan is too uncertain (0.35, needs 0.75)" / "the date read from the scan does not parse (2026-06-91)".
2. **A cited, parseable scan date is kept for review.** For `loss_run_valued_through` only, when the source is an OCR'd document (scan or image-only PDF page) **and** the model's date parses **and** the date's own digits appear in that document's text (`digits_of` agreement, the same test `gate_loss_run` already uses at `prepare.py:591-592`), store the value with `needs_review=True` and reason "read from a scan — check it against the page", instead of dropping it at the 0.75 confidence line. A date whose digits are not in the text is still dropped, exactly as now. No other field, no typed file, no other gate changes.
3. **Self-checks (D-097):** SUB-217's token at OCR 0.0 is kept and flagged; SUB-209's garbled `2026~06-15` is kept and flagged; SUB-225's `2026-06-91` still drops but now carries the reason; a scan date whose digits are absent from the text still drops; the typed `loss-runs.md` files are unchanged; `lint_holdout.py --self-check` stays PASS.
4. **D-065:** the workbench card shows the new reason, one "What's new" line (date, task id, decision number), a Playwright screenshot under `deliverables/software-engineer/screenshots/`, and @senior-underwriter's UI review (High only).

Nothing else changes: no prompt, no model, no gold card, no scorer, no frozen file.

## Expected effect (on this dev re-measure)

- loss_runs: 16 → **18/20** (217 and 209 become hits; 225 stays a miss with a stated reason; 211 stays not_credited).
- operations: **unchanged at 10/20** — all ten operations misses are wording (`T-110-v9-remeasure.md`), so this proposal cannot and does not touch them. B-433's "AND" therefore still fails; closing the operations half is a separate decision asked in the same turn (the model quoting the documents' wording vs a gold/scorer wording rule).
- No effect on route, false completes, scope or any published score.

## Not included (the measurement half)

`Conflict: none (…)` folds (SUB-209, SUB-219 → D-086 field reasons), the `sides_stored` needles (SUB-214 `0 tenant`, SUB-216 `24500 vs`), `complete — review pending` (206/213/218), the P-015 T2 liquor ask (207/215), the R14/allow-list routes (206/213), the conflict-nulled TIV (214) and every operations wording miss. Those are approved rules or scorer artefacts, not real misses, so nothing is proposed for them here. SUB-211's unflagged premises conflict is a real model miss but is outside B-433's scope: it belongs in the backlog (candidate **B-445**) with its own proposal if the user wants one.

## Risk

Keeping a scan-sourced date below the 0.75 line narrows P-016/P-025 ("never keep a guess") for one field, one document class, one extra condition. The guard is the digits-in-text test plus `needs_review`, and the file still cannot be `complete` without an underwriter acknowledging it (D-039). @model-risk must check it before any use beyond development.

To approve, the user types: `approve change P-067`.
