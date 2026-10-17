# P-056 as built — check fixes from the T-103 root cause (D-103 item 2)

- Approved by @user: "approve change P-056" (D-103, this session). Built in the main session (budget rule 3). No prompt, model or OCR-engine change; no gold, scorer or published score changed.
- Code: `underwriting_pipeline/ai/llm_extract.py`, `underwriting_pipeline/ai/prepare.py`; What's new line in `underwriting_pipeline/app/workbench.py`. Screenshot `deliverables/software-engineer/screenshots/D-103-P-056-values-differ-by-location.png` (sandbox copy, D-069).
- Self-checks: llm_extract, prepare, eval_holdout_v4, eval_holdout_v5 ok.

## What changed

| | Fix | Where |
|---|---|---|
| (a) | 2-digit years parse ("3/1/27" is 2027-03-01) in the quote date parser and for a model value written that way; stored as ISO. **A date that can be read day-first or month-first is read month first (US documents) and flagged NEEDS REVIEW "date read month first (US order)".** Before, such dates were never accepted (P-016 D2), even with 4-digit years, so the 2-digit fix alone would not have read "3/1/27". The day-first reading is never taken. | `_DATES`, `_quote_dates`, `parse_day`, `value_in_span`, `accept_field` |
| (b) | OCR floor: the drop test (SCAN_FLOOR 0.50) uses the average score of the cited words; the lowest word still sets the confidence and, under 0.75, the "Low-confidence scan read" review flag. A single-word value at 0.4 is still dropped; a word missing from the OCR word list still counts 0. Same rule for document-rule values (`_set_cited`). | `cited_ocr_floor`, `accept_field`, `prepare._set_cited` |
| (c) | A quote joining lines with " ... " (or "…") is split like a newline join; every part must be found in the same document. | `_JOIN`, `accept_field` |
| (d) | Reword check strips . , ; : ! ? from the ends of each answer word ("only)." is the quote's "only)"). | `value_in_span` |
| (e) | Two or more values from one non-schedule document, each starting a list item and followed by its own location number ("2012 (loc 1)"), are not a conflict. Premises: loc 1 is the field, the others go to locations. Other fields: loc 1 is the field, flagged "values differ by location: loc 1 …; loc 2 …". A rejected side, two documents, or a repeated number keeps the conflict. | `location_sides`, conflict loop in `llm_extract` |
| (f) | The P-047 operations check reads the whole cited document for rule items, not only the cited line and labelled lines. Carrier match still reads the labelled lines (`context`), unchanged. | `prepare.check_operations` |

## Dev counts before and after (D-103: dev files only, SUB-127–153)

Scorer v4 (frozen), same saved replies before and after, 0 calls for 127–146. SUB-147–153 had no saved reply under the current prompt (it changed in P-047 after they were run), so they were called once, live, free Groq qwen/qwen3.8-27b, paced 55 s, into a temp cache (7 calls, 0 failed); before and after both use those replies. Nothing written to the real cache, logs or outboxes. Files: `evals/P-056-dev/`.

**SUB-127–146** (hits; before → after)

| Field | Before | After |
|---|---|---|
| premises | 17 | 18 (SUB-144) |
| effective_date | 18 | 19 (SUB-142) |
| conflict | 16 | 17 (SUB-140: per-location year and construction no longer a conflict) |
| status | 18 | 17 (SUB-134: complete → complete — review pending) |
| all other fields | unchanged | unchanged |
| false completes | 0 | 0 |
| unsafe routes | 0 | 0 |
| route | 16/20 (gate FAIL, dev gold predates R17, B-392 M4) | 16/20 |
| status automation | 4 of 6 | 3 of 6 |

SUB-134: the application's line of business says "light manufacturing"; the operations answer drops it, so (f) now flags "operations may be missing: on-site processing". Safe direction; it costs one automated complete.

**SUB-147–153:** no mark changed. 0 false completes, 0 unsafe before and after; route 0/7 both (old gold, B-392 M4).

Review flags on values across SUB-127–153 after the change: 1 operations-missing (SUB-134), 1 values-by-location (SUB-140), 0 month-first dates, 2 low-confidence scan, 2 reworded.

## Not done here

- T-103 (SUB-154–173) was not re-scored: it is a published hold-out, and D-103 limits self-checks to dev files.
- No fix for the extras rule firing on "kitchen"/"restaurant" (SUB-159/161) or the SUB-169 laundry route; neither is in P-056.

## After the @model-risk check (D-103, `deliverables/model-risk/check-P-055-P-056-v5.md`)

- **H1 (P-056 b):** numbers and dates are no longer averaged. Their drop test stays on the lowest score of their own digit groups, as before P-056; only text fields (name, address, operations, construction) use the average. A scanned date now scores every word of its quote, so the "27" of "3/15/27" counts. Self-checks: a TIV with "000" at 0.05 is dropped; a date with "27" at 0.2 is dropped. Same rule in `_set_cited`. Whether this narrowing stays inside P-056 (b) is for @user.
- **Code review (D-097):** a scan reason no longer hides the date-order or reword reason ("number or date read from a scan; date read month first (US order)..."); `location_sides` needs a "(loc 1)", so loc 2 is never promoted to the premises.
- **v5 H2:** see `eval_holdout_v5.py` change 9: an item's words must appear together and in order.
- Dev counts re-run after these changes: identical to the table above (SUB-127–146 and 147–153).
