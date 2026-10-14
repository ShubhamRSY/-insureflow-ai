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

| field | P-024 | P-025 hit | P-025 hit (needs review) | other |
|---|---|---|---|---|
| named_insured | 13 | 13 | 0 | miss 2 |
| operations | 12 | 12 | 1 | miss 2 |
| sales | 13 | 13 | 0 | miss 1, flagged 1 |
| construction | 13 | 13 | 1 | miss 1 |
| year_built | 15 | 15 | 0 | |
| premises | 12 | 12 | 0 | miss 3 |
| tiv | 14 | 14 | 0 | miss 1 |
| loss_runs | 8 | 8 | 1 | not_credited 5, flagged 1 |
| conflict | 12 | 13 | 0 | flagged 2 (P-024: not_credited 1) |
| status | 12 | 12 | 1 | miss 2 |

No field's plain hit count dropped. Plain hits equal P-024; the five regained checks are in the separate column (conflict is a plain hit). The proposal expected SUB-067 status to stay a miss: it did.

## Not done
Screenshot (D-065 item 4) and @senior-underwriter UI check: not taken here; the workbench change is one What's new line and an existing label. The send gate still does not read needs_review (see proposal). Not a production approval; T-027 stands.
