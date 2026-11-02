# Extraction score (scorer v11) — SUB-340 through SUB-371

- Author: @ai-engineer-assistant
- 9 of 9 extracted fields scored; claims not read; loss runs = date only.
- Commit: 58cc1709edb1574bc371289fda1700bdcc0e74e1 (last pipeline commit d7949d268f59ceb60593e840a5eef181c6d226c5).
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
| operations | 9 | 0 | 11 | 0 | 0 | 0 |
| sales | 20 | 0 | 0 | 0 | 0 | 0 |
| tiv | 20 | 0 | 0 | 0 | 0 | 0 |
| construction | 20 | 0 | 0 | 0 | 0 | 0 |
| year_built | 20 | 0 | 0 | 0 | 0 | 0 |
| loss_runs | 20 | 0 | 0 | 0 | 0 | 0 |
| conflict | 15 | 0 | 3 | 0 | 2 | 0 |
| status | 9 | 0 | 11 | 0 | 0 | 0 |
| route | 20 | 0 | 0 | 0 | 0 | 0 |

## Status safety and status automation (B-325)

- False completes (plain "complete" on a gold-incomplete file): **0** (none). Critical: must be 0.
- Status automation: 2 of 13 gold-complete files shown as plain "complete". "complete — review pending" is safe but not automated.
- Failed calls, left out of both: 0.
- Operations scored by checklist (v5): 20 of 20 files; the rest by the v4 word rule.

## T-027 route gate (D-096, D-097)

- Unsafe routes (a carrier, held or not, where gold says senior_referral or no_match): **0** (none). Must be 0.
- Route accuracy: 20/20 (0 files with no route mark). Must be at least 18/20.
- Route hits over all 20 in-scope gold files (none left out): 20/20. Gate rule unchanged.
- Route gate: **PASS**.

## P-055 scope gate (D-108, P-057), apart from the T-027 gate

- Files: 12 out of scope, 20 in scope (gold Scope lines). Out-of-scope files are not field-scored.
- Leakage (hard gate): **0** of 12 (none). Must be 0.
- Detection recall, overall: 12/12 (missed: none). Must be 100%.
  - criterion 1 scanned application: 4/4
  - criterion 2 multiple locations: 5/5
  - criterion 3 non-English: 4/4
  - criterion 4 application not identified: 3/3
- Reason accuracy (reported): 11/12 manual-intake cards list every gold criterion (not: SUB-371).
- False manual intake: 0 of 20 in-scope files (none). At most 2; within the ceiling, they are left out of the in-scope counts above.
- P-055 scope gate: **PASS**.

## Per submission

- SUB-360 (out of scope, criteria 1): manual intake: yes. Reason codes: scanned_application. Leaks: none.
- SUB-361 (out of scope, criteria 1): manual intake: yes. Reason codes: scanned_application. Leaks: none.
- SUB-362 (out of scope, criteria 2): manual intake: yes. Reason codes: multiple_locations. Leaks: none.
- SUB-363 (out of scope, criteria 2): manual intake: yes. Reason codes: multiple_locations. Leaks: none.
- SUB-364 (out of scope, criteria 3): manual intake: yes. Reason codes: non_english. Leaks: none.
- SUB-365 (out of scope, criteria 3): manual intake: yes. Reason codes: non_english. Leaks: none.
- SUB-366 (out of scope, criteria 4): manual intake: yes. Reason codes: not_identified. Leaks: none.
- SUB-367 (out of scope, criteria 4): manual intake: yes. Reason codes: not_identified. Leaks: none.
- SUB-368 (out of scope, criteria 1, 2): manual intake: yes. Reason codes: scanned_application, multiple_locations. Leaks: none.
- SUB-369 (out of scope, criteria 2, 3): manual intake: yes. Reason codes: multiple_locations, non_english. Leaks: none.
- SUB-370 (out of scope, criteria 1, 3): manual intake: yes. Reason codes: scanned_application, non_english. Leaks: none.
- SUB-371 (out of scope, criteria 2, 4): manual intake: yes. Reason codes: not_identified. Leaks: none.
- SUB-340 (typed md app, typed md loss run (Carrier A), email): extracted name Tallgrass Office LLC. Misses: operations, status. Flagged: none. Call: called: reply used. Retries: 1 (rate_limit_429).
- SUB-341 (typed md app, typed md loss run (Carrier A), email): extracted name Pinecrest Threads LLC. Misses: operations, status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-342 (typed md app, typed md loss run (Carrier A), email): extracted name Prairie Dry Goods Co LLC. Misses: operations, status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-343 (typed md app, typed md loss run (Carrier A), schedule csv, email): extracted name Old Mill Thrift Co LLC. Misses: operations, status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-344 (typed pdf app (text layer), typed md loss run (Carrier B), schedule csv, email): extracted name Gulf Plains Electrical Contractors LLC. Misses: operations. Flagged: conflict. Call: called: reply used. Retries: 0.
- SUB-345 (typed md app, typed md loss run (Carrier C), email): extracted name Brazos Janitorial Supply LLC. Misses: conflict. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-346 (typed md app, typed md loss run (Carrier A), schedule csv, email): extracted name Ironwood Professional Plaza LLC. Misses: operations. Flagged: conflict. Call: called: reply used. Retries: 0.
- SUB-347 (typed md app, typed md loss run (Carrier C), schedule csv, email): extracted name Lamar Professional Center LLC. Misses: operations, status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-348 (typed md app, typed md loss run (Carrier B), email): extracted name Sunny Side Deli LLC. Misses: conflict. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-349 (typed md app, typed md loss run (Carrier A), schedule csv, email): extracted name Cornerstone Sandwich Bar LLC. Misses: conflict. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-350 (typed md app, email, dated no-known-loss letter): extracted name Hollis Plumbing Supply Co. Misses: operations. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-351 (typed pdf app (text layer), typed md loss run (Carrier C), email): extracted name Blue Plate Pancake House LLC. Misses: none. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-352 (typed pdf app (text layer), typed md loss run (Carrier C), email): extracted name Foxhole Pub & Kitchen LLC. Misses: operations, status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-353 (typed md app, typed md loss run (Carrier B), email): extracted name Velvet Crane Cocktail Lounge LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-354 (typed md app, typed md loss run (Carrier C), email): extracted name Neon Harbor Nightclub LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-355 (typed md app, typed md loss run (Carrier A), email): extracted name Ember Smoke Hookah Lounge LLC. Misses: operations, status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-356 (typed pdf app (text layer), typed md loss run (Carrier C), email): extracted name Juniper Glen Apartments LP. Misses: none. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-357 (typed md app, typed md loss run (Carrier B), email): extracted name Redbud Court Apartments LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-358 (typed md app, typed md loss run (Carrier A), schedule csv, email): extracted name Tejas Metal Fabrication LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-359 (typed md app, email; no loss run): extracted name Piney Creek Floors LLC. Misses: operations. Flagged: none. Call: called: reply used. Retries: 0.

## Silent error rate and automation rate (D-084)

silent error: a value is shown, it is wrong, and it is not flagged needs review or in an open conflict; automation: the value is correct and not flagged. An empty field counts as flagged (it shows as missing). Rates are over scored field values; files whose call failed are left out and counted apart (D-084).

Files with a failed call, not in the rates: 0.

| Field | Scored | Silent errors | Silent error rate | Automated | Automation rate |
|---|---|---|---|---|---|
| named_insured | 20 | 0 | 0.0 | 20 | 1.0 |
| premises | 20 | 0 | 0.0 | 20 | 1.0 |
| effective_date | 20 | 0 | 0.0 | 20 | 1.0 |
| operations | 20 | 1 | 0.05 | 5 | 0.25 |
| sales | 20 | 0 | 0.0 | 19 | 0.95 |
| tiv | 20 | 0 | 0.0 | 20 | 1.0 |
| construction | 20 | 0 | 0.0 | 20 | 1.0 |
| year_built | 20 | 0 | 0.0 | 20 | 1.0 |
| loss_runs | 20 | 0 | 0.0 | 18 | 0.9 |
| overall | 180 | 1 | 0.006 | 162 | 0.9 |
