# P-025 as built (option D, D-067)

2026-10-14. @ai-engineer-assistant. PROMPT_VERSION unchanged (82be09bd42f7). Frozen scorers and published scores not edited.

## Code
- `ai/llm_extract.py`: `SCAN_FLOOR = 0.50`, `REASON_LOW_SCAN`. In `accept_field`, on a scan source only, a value with gate score 0.50 to below 0.75 keeps going (quote must still be found and hold the value) and is stored with needs_review True and reason "Low-confidence scan read — check against the page". Below 0.50: dropped as before. Typed documents: unchanged. This reason replaces the S2 "number or date read from a scan" reason on the same row.
- `ai/prepare.py` `_set_cited` (document-rule values on scans, e.g. loss-run date): same floor and flag.
- `ai/regression_dev.py`: `split_review_hits`. The scorer's own report is captured by wrapping `prepare.process_submission` in-process; a check that is "hit" where the stored field row has the low-confidence reason is counted "hit (needs review)". `status` counts as "hit (needs review)" when any stored row has that reason (the status depends on it). Mapping: sales->sales_or_payroll, tiv->tiv_building, loss_runs->loss_run_valued_through.
- `app/workbench.py`: the card already prints "NEEDS REVIEW: <reason>", so the label is the reason text. Added one What's new line and one self-check. `needs_review_ids()` lists any row with needs_review and a value, so the approve acknowledgment includes these rows (checked).
- Existing self-checks that expected a drop at 0.6 now use 0.4 (and a 0.6 case expecting storage).

## Self-checks (LLM_* unset)
llm_extract, prepare, sources, workbench, package: all pass. New: scan 0.49 dropped; 0.50 and 0.74 stored, flagged, reasoned; 0.75 as before; typed 0.60 dropped; low scan value without its quote dropped.

## Quick set (cache only)
`evals/regression-quick-15-2026-10-14-P-025.json`. model_calls 0, from_cache 15, failed attempts 0.
Changes vs P-024 (every other check identical):
- SUB-038 loss_runs miss -> hit (needs review); status miss -> hit (needs review)
- SUB-067 operations miss -> hit (needs review); construction miss -> hit (needs review)
- SUB-067 conflict not_credited -> hit (no open conflict now that the values are stored)
- SUB-074 tiv: no change in the scorer's mark (hit in both runs).

## Fix for @model-risk H1 (D-068 item 2, B-243, B-246)
`regression_dev.py`: `split_review_hits` now treats `conflict` like `status` (a conflict hit on a submission where any stored row has the low-confidence reason is "hit (needs review)", never plain) and `CHECK_FIELD` adds premises -> premises_address. Self-check: `regression_dev.py --self-check` (flagged: conflict, premises, status go to "hit (needs review)", sales stays hit, tiv stays miss; unflagged row unchanged) prints "regression_dev self-check ok".
Rerun: `evals/regression-quick-15-2026-10-14-P-025-fix.json`, model_calls 0, from_cache 15, failed attempts 0. Same cache, so only the labels moved. The earlier `regression-quick-15-2026-10-14-P-025.json` is kept unedited and its conflict count (13 plain hits) was the H1 error.

| field | P-024 hit | P-025 hit / needs review | P-025-fix hit | P-025-fix hit (needs review) | other (fix) |
|---|---|---|---|---|---|
| named_insured | 13 | 13 / 0 | 13 | 0 | miss 2 |
| operations | 12 | 12 / 1 | 12 | 1 | miss 2 |
| sales | 13 | 13 / 0 | 13 | 0 | miss 1, flagged 1 |
| construction | 13 | 13 / 1 | 13 | 1 | miss 1 |
| year_built | 15 | 15 / 0 | 15 | 0 | |
| premises | 12 | 12 / 0 | 12 | 0 | miss 3 |
| tiv | 14 | 14 / 0 | 14 | 0 | miss 1 |
| loss_runs | 8 | 8 / 1 | 8 | 1 | not_credited 5, flagged 1 |
| conflict | 12 | 13 / 0 | 10 | 3 | flagged 2 |
| status | 12 | 12 / 1 | 12 | 1 | miss 2 |

Only conflict moved against the first P-025 file: plain hits 13 -> 10, "hit (needs review)" 0 -> 3. Against P-024 the plain conflict count is 12 -> 10: two conflict hits that were plain in P-024 now sit on submissions that hold a low-confidence value, so they are labelled needs-review; the extraction did not get worse (total conflict hits 12 -> 13). Every other field: plain hit count equals P-024. No plain hit in this file comes from a low-confidence value, by construction of the split (checked for the ten fields above).

## Not done
Screenshot (D-065 item 4) and @senior-underwriter UI check: not taken here; the workbench change is one What's new line and an existing label. The send gate still does not read needs_review (see proposal). Not a production approval; T-027 stands.
