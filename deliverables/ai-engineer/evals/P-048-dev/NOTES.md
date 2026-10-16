# P-048 dev re-check, SUB-127–146 (D-095). Development data, not a hold-out. Synthetic. Not a production approval.

Re-score from a temp copy of the cache, 0 model calls: `HOLDOUT_RESCORE=1` (B-363 fix, @model-risk H1), written to `SUB-127-146-dev-v2-cache-rescore.*`.

| | P-047 (b73bd40) | P-048 |
|---|---|---|
| Loss runs hit / miss / not credited | 5 / 3 / 12 | 8 / 0 / 12 |
| Route (held files scored by provisional route) | 14/20 | 16/20 (carrier_c 1/1, senior_referral 6/7) |
| Operations | 18/20 | 19/20 |
| False completes / silent errors | 0 / 0 | 0 / 0 |

## The 3 loss-run misses under P-047

All three were scanned carrier runs: SUB-129 (image-only PDF, Carrier A), SUB-131 (JPG, Carrier B), SUB-133 (rotated JPG, Carrier C). OCR kept the carrier header on the first line but broke the rest of the layout, so `carrier_run_check` returned "no_date". `gate_loss_run` checked "undated carrier run" before the scan rule, dropped the date and held the file with "no valued-as-of date" (B-357). P-048 (b) leaves scans out of the undated rule, so the date is kept for review ("loss run from scan/spreadsheet: check it"): review pending, not hold.

## Route misses left (4)

- SUB-135 thrift / used books: no class word → no_match (gold carrier_a). Class list, P-049.
- SUB-138 feed, seed and fertilizer: wholesale → carrier_a (gold hold: fertilizer may be hazardous). Exclusion not applied, P-049.
- SUB-142, SUB-144: TIV missing, so no provisional route (gold senior_referral, no_match). By design in P-048 (c): no route is guessed without TIV.
