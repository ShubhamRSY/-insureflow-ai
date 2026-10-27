# Extraction score (scorer v11) — SUB-450 through SUB-481

- Author: @ai-engineer-assistant
- 9 of 9 extracted fields scored; claims not read; loss runs = date only.
- Commit: 8c157e9fe176a0f37172df5dd341d25764c25c23 (last pipeline commit c9c8e17cec90002254237429f72e7f0625f42399).
- Scored with this file unchanged after the gold answers were written. A development re-check is not a hold-out.
- A null that matches a missing gold line is not_credited. It is not a correct answer.
- Correctly flagged for human means the documents disagree and the AI stored both sides without picking one. It is not a hit and not a miss.
- Synthetic. Not a production approval.

## Per-field

| Field | Hit | Hit (needs review) | Miss | Not credited | Correctly flagged for human | Call failed |
|---|---|---|---|---|---|---|
| named_insured | 20 | 0 | 0 | 0 | 0 | 0 |
| premises | 20 | 0 | 0 | 0 | 0 | 0 |
| effective_date | 20 | 0 | 0 | 0 | 0 | 0 |
| operations | 19 | 0 | 1 | 0 | 0 | 0 |
| sales | 18 | 0 | 0 | 0 | 2 | 0 |
| tiv | 19 | 0 | 0 | 0 | 1 | 0 |
| construction | 20 | 0 | 0 | 0 | 0 | 0 |
| year_built | 20 | 0 | 0 | 0 | 0 | 0 |
| loss_runs | 20 | 0 | 0 | 0 | 0 | 0 |
| conflict | 11 | 0 | 2 | 0 | 7 | 0 |
| status | 11 | 0 | 9 | 0 | 0 | 0 |
| route | 18 | 0 | 2 | 0 | 0 | 0 |

## Status safety and status automation (B-325)

- False completes (plain "complete" on a gold-incomplete file): **0** (none). Critical: must be 0.
- Status automation: 0 of 9 gold-complete files shown as plain "complete". "complete — review pending" is safe but not automated.
- Failed calls, left out of both: 0.
- Operations scored by checklist (v5): 20 of 20 files; the rest by the v4 word rule.

## T-027 route gate (D-096, D-097)

- Unsafe routes (a carrier, held or not, where gold says senior_referral or no_match): **0** (none). Must be 0.
- Route accuracy: 18/20 (0 files with no route mark). Must be at least 18/20.
- Route hits over all 20 in-scope gold files (none left out): 18/20. Gate rule unchanged.
- Route gate: **PASS**.

## P-055 scope gate (D-108, P-057), apart from the T-027 gate

- Files: 12 out of scope, 20 in scope (gold Scope lines). Out-of-scope files are not field-scored.
- Leakage (hard gate): **1** of 12 (SUB-475). Must be 0.
  - SUB-475: field shown, complete status, suggested market, send enabled
- Detection recall, overall: 11/12 (missed: SUB-475). Must be 100%.
  - criterion 1 scanned application: 3/3
  - criterion 2 multiple locations: 2/3
  - criterion 3 non-English: 3/3
  - criterion 4 application not identified: 3/3
- Reason accuracy (reported): 11/11 manual-intake cards list every gold criterion.
- False manual intake: 0 of 20 in-scope files (none). At most 2; within the ceiling, they are left out of the in-scope counts above.
- P-055 scope gate: **FAIL**.

## Per submission

- SUB-470 (out of scope, criteria 1): manual intake: yes. Reason codes: scanned_application. Leaks: none.
- SUB-471 (out of scope, criteria 1): manual intake: yes. Reason codes: scanned_application. Leaks: none.
- SUB-472 (out of scope, criteria 1): manual intake: yes. Reason codes: scanned_application. Leaks: none.
- SUB-473 (out of scope, criteria 2): manual intake: yes. Reason codes: multiple_locations. Leaks: none.
- SUB-474 (out of scope, criteria 2): manual intake: yes. Reason codes: multiple_locations. Leaks: none.
- SUB-475 (out of scope, criteria 2): manual intake: NO. Reason codes: none. Leaks: field shown, complete status, suggested market, send enabled.
- SUB-476 (out of scope, criteria 3): manual intake: yes. Reason codes: non_english. Leaks: none.
- SUB-477 (out of scope, criteria 3): manual intake: yes. Reason codes: non_english. Leaks: none.
- SUB-478 (out of scope, criteria 3): manual intake: yes. Reason codes: non_english. Leaks: none.
- SUB-479 (out of scope, criteria 4): manual intake: yes. Reason codes: not_identified. Leaks: none.
- SUB-480 (out of scope, criteria 4): manual intake: yes. Reason codes: not_identified. Leaks: none.
- SUB-481 (out of scope, criteria 4): manual intake: yes. Reason codes: not_identified. Leaks: none.
- SUB-450 (typed md app, typed md loss run (Carrier A), email): extracted name Cedar Bend Bookkeeping LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 2 (rate_limit_429, rate_limit_429).
- SUB-451 (typed pdf app (text layer), typed md loss run (Carrier A), email): extracted name Juniper Lane Apparel LLC. Misses: status, route. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-452 (typed md app, typed md loss run (Carrier A), email): extracted name Walnut Creek Hardware Co LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-453 (typed pdf app (text layer), typed md loss run (Carrier A), email): extracted name Mesquite Ridge Insurance Agency LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-454 (typed pdf app (text layer), typed md loss run (Carrier B), email): extracted name Neches River Electric LLC. Misses: none. Flagged: conflict. Call: called: reply used. Retries: 0.
- SUB-455 (typed md app, typed md loss run (Carrier C), email): extracted name Chisholm Trail Janitorial Supply LLC. Misses: none. Flagged: sales, conflict. Call: called: reply used. Retries: 0.
- SUB-456 (typed md app, email; no loss run): extracted name Azalea Floor Works LLC. Misses: none. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-457 (typed md app, typed md loss run (Carrier A), email): extracted name Bayou Ridge Metal Works LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-458 (typed md app, typed md loss run (Carrier C), email): extracted name Pecan Row Professional Center LLC. Misses: operations, route. Flagged: conflict. Call: called: reply used. Retries: 0.
- SUB-459 (typed md app, typed md loss run (Carrier C), email): extracted name Bluebonnet Duval Professional LLC. Misses: none. Flagged: conflict. Call: called: reply used. Retries: 0.
- SUB-460 (typed md app, typed md loss run (Carrier B), email): extracted name Stonegate Roofing & Sheet Metal Co. Misses: none. Flagged: tiv, conflict. Call: called: reply used. Retries: 0.
- SUB-461 (typed pdf app (text layer), typed md loss run (Carrier B), email): extracted name Magnolia Gifts & Home Goods LLC. Misses: conflict. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-462 (typed md app, typed md loss run (Carrier B), email): extracted name Corner Table Deli LLC. Misses: none. Flagged: sales, conflict. Call: called: reply used. Retries: 0.
- SUB-463 (typed md app, typed md loss run (Carrier C), schedule csv, email): extracted name Harbor Deli Co LLC. Misses: conflict. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-464 (typed pdf app (text layer), typed md loss run (Carrier C), email): extracted name Lantern Hill Pub & Grill LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-465 (typed md app, typed md loss run (Carrier C), email): extracted name Sunset Pier Nightclub LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-466 (typed md app, typed md loss run (Carrier A), email): extracted name Smoke Ring Hookah Lounge LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-467 (typed pdf app (text layer), typed md loss run (Carrier C), email): extracted name Harvest Moon Breakfast House LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-468 (typed md app, email, dated no-known-loss letter): extracted name Cypress Bend Bakery Cafe LLC. Misses: none. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-469 (typed md app, typed md loss run (Carrier A), email): extracted name Ridgeline Auto Parts & Tire Service LLC. Misses: none. Flagged: conflict. Call: called: reply used. Retries: 0.

## Silent error rate and automation rate (D-084)

silent error: a value is shown, it is wrong, and it is not flagged needs review or in an open conflict; automation: the value is correct and not flagged. An empty field counts as flagged (it shows as missing). Rates are over scored field values; files whose call failed are left out and counted apart (D-084).

Files with a failed call, not in the rates: 0.

| Field | Scored | Silent errors | Silent error rate | Automated | Automation rate |
|---|---|---|---|---|---|
| named_insured | 20 | 0 | 0.0 | 20 | 1.0 |
| premises | 20 | 0 | 0.0 | 20 | 1.0 |
| effective_date | 20 | 0 | 0.0 | 20 | 1.0 |
| operations | 20 | 0 | 0.0 | 0 | 0.0 |
| sales | 20 | 0 | 0.0 | 18 | 0.9 |
| tiv | 20 | 0 | 0.0 | 19 | 0.95 |
| construction | 20 | 0 | 0.0 | 20 | 1.0 |
| year_built | 20 | 0 | 0.0 | 20 | 1.0 |
| loss_runs | 20 | 0 | 0.0 | 18 | 0.9 |
| overall | 180 | 0 | 0.0 | 155 | 0.861 |
