# Extraction score (scorer v11) — SUB-510 through SUB-541

- Author: @ai-engineer-assistant
- 9 of 9 extracted fields scored; claims not read; loss runs = date only.
- Commit: b92a5b8849ae73780ceca028ed760ed3d0c74acf (last pipeline commit 8baa00a43abcc77ea76f511de99c8e3b6ab33ab7).
- Scored with this file unchanged after the gold answers were written. A development re-check is not a hold-out.
- A null that matches a missing gold line is not_credited. It is not a correct answer.
- Correctly flagged for human means the documents disagree and the AI stored both sides without picking one. It is not a hit and not a miss.
- Synthetic. Not a production approval.

## Per-field

| Field | Hit | Hit (needs review) | Miss | Not credited | Correctly flagged for human | Call failed |
|---|---|---|---|---|---|---|
| named_insured | 16 | 0 | 4 | 0 | 0 | 0 |
| premises | 16 | 0 | 4 | 0 | 0 | 0 |
| effective_date | 16 | 0 | 4 | 0 | 0 | 0 |
| operations | 16 | 0 | 4 | 0 | 0 | 0 |
| sales | 14 | 0 | 4 | 0 | 2 | 0 |
| tiv | 15 | 0 | 4 | 0 | 1 | 0 |
| construction | 16 | 0 | 4 | 0 | 0 | 0 |
| year_built | 16 | 0 | 4 | 0 | 0 | 0 |
| loss_runs | 16 | 0 | 0 | 4 | 0 | 0 |
| conflict | 8 | 0 | 2 | 4 | 6 | 0 |
| status | 9 | 0 | 11 | 0 | 0 | 0 |
| route | 16 | 0 | 4 | 0 | 0 | 0 |

## Status safety and status automation (B-325)

- False completes (plain "complete" on a gold-incomplete file): **0** (none). Critical: must be 0.
- Status automation: 0 of 11 gold-complete files shown as plain "complete". "complete — review pending" is safe but not automated.
- Failed calls, left out of both: 0.
- Operations scored by checklist (v5): 20 of 20 files; the rest by the v4 word rule.

## T-027 route gate (D-096, D-097)

- Unsafe routes (a carrier, held or not, where gold says senior_referral or no_match): **0** (none). Must be 0.
- Route accuracy: 16/20 (0 files with no route mark). Must be at least 18/20.
- Route hits over all 20 in-scope gold files (none left out): 16/20. Gate rule unchanged.
- Route gate: **FAIL**.

## P-055 scope gate (D-108, P-057), apart from the T-027 gate

- Files: 12 out of scope, 20 in scope (gold Scope lines). Out-of-scope files are not field-scored.
- Leakage (hard gate): **0** of 12 (none). Must be 0.
- Detection recall, overall: 12/12 (missed: none). Must be 100%.
  - criterion 1 scanned application: 2/2
  - criterion 2 multiple locations: 6/6
  - criterion 3 non-English: 2/2
  - criterion 4 application not identified: 2/2
- Reason accuracy (reported): 12/12 manual-intake cards list every gold criterion.
- False manual intake: 4 of 20 in-scope files (SUB-510, SUB-513, SUB-527, SUB-529). At most 2; ABOVE the ceiling: they stay in the in-scope counts as misses.
- P-055 scope gate: **FAIL**.

## Per submission

- SUB-530 (out of scope, criteria 1): manual intake: yes. Reason codes: scanned_application. Leaks: none.
- SUB-531 (out of scope, criteria 1): manual intake: yes. Reason codes: scanned_application. Leaks: none.
- SUB-532 (out of scope, criteria 2): manual intake: yes. Reason codes: multiple_locations. Leaks: none.
- SUB-533 (out of scope, criteria 2): manual intake: yes. Reason codes: multiple_locations. Leaks: none.
- SUB-534 (out of scope, criteria 2): manual intake: yes. Reason codes: multiple_locations. Leaks: none.
- SUB-535 (out of scope, criteria 2): manual intake: yes. Reason codes: multiple_locations. Leaks: none.
- SUB-536 (out of scope, criteria 2): manual intake: yes. Reason codes: multiple_locations. Leaks: none.
- SUB-537 (out of scope, criteria 2): manual intake: yes. Reason codes: multiple_locations. Leaks: none.
- SUB-538 (out of scope, criteria 3): manual intake: yes. Reason codes: non_english. Leaks: none.
- SUB-539 (out of scope, criteria 3): manual intake: yes. Reason codes: non_english. Leaks: none.
- SUB-540 (out of scope, criteria 4): manual intake: yes. Reason codes: not_identified. Leaks: none.
- SUB-541 (out of scope, criteria 4): manual intake: yes. Reason codes: not_identified. Leaks: none.
- SUB-510 (typed md app, typed md loss run (Carrier A), email): extracted name null. Misses: named_insured, effective_date, operations, sales, construction, year_built, premises, tiv, status, route. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-511 (typed pdf app (text layer), typed md loss run (Carrier A), email): extracted name Bluestem Boutique LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-512 (typed md app, typed md loss run (Carrier A), email): extracted name Pine Hollow Mercantile LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-513 (typed pdf app (text layer), typed md loss run (Carrier A), email): extracted name null. Misses: named_insured, effective_date, operations, sales, construction, year_built, premises, tiv, status, route. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-514 (typed pdf app (text layer), typed md loss run (Carrier B), email): extracted name Riverbend Plumbing Services LLC. Misses: none. Flagged: conflict. Call: called: reply used. Retries: 0.
- SUB-515 (typed md app, typed md loss run (Carrier C), email): extracted name Trinity Bay Paper Supply LLC. Misses: none. Flagged: sales, conflict. Call: called: reply used. Retries: 0.
- SUB-516 (typed md app, email; no loss run): extracted name Copperleaf Painting LLC. Misses: none. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-517 (typed md app, typed md loss run (Carrier C), email): extracted name Live Oak Commons Office Center LLC. Misses: none. Flagged: conflict. Call: called: reply used. Retries: 1 (other).
- SUB-518 (typed md app, typed md loss run (Carrier C), email): extracted name Kestrel Point Professional Building LLC. Misses: none. Flagged: conflict. Call: called: reply used. Retries: 1 (rate_limit_429).
- SUB-519 (typed md app, typed md loss run (Carrier B), email): extracted name High Plains Roofing Co. Misses: none. Flagged: tiv, conflict. Call: called: reply used. Retries: 0.
- SUB-520 (typed pdf app (text layer), typed md loss run (Carrier B), email): extracted name Willow Creek Gifts LLC. Misses: conflict. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-521 (typed md app, typed md loss run (Carrier B), email): extracted name Station Street Deli LLC. Misses: none. Flagged: sales, conflict. Call: called: reply used. Retries: 0.
- SUB-522 (typed md app, typed md loss run (Carrier C), email): extracted name Seawall Deli Co LLC. Misses: conflict. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-523 (typed md app, typed md loss run (Carrier C), email): extracted name Rusty Spur Tavern LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-524 (typed md app, typed md loss run (Carrier A), email): extracted name Midnight Mesa Nightclub LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-525 (typed pdf app (text layer), typed md loss run (Carrier C), email): extracted name Sunrise Skillet LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-526 (typed md app, typed md loss run (Carrier B), email): extracted name Golden Crust Bakery LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-527 (typed md app, typed md loss run (Carrier A), email): extracted name null. Misses: named_insured, effective_date, operations, sales, construction, year_built, premises, tiv, status, route. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-528 (typed pdf app (text layer), typed md loss run (Carrier C), email): extracted name Hardin & Pruitt PLLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-529 (typed md app, typed md loss run (Carrier A), email): extracted name null. Misses: named_insured, effective_date, operations, sales, construction, year_built, premises, tiv, status, route. Flagged: none. Call: called: reply used. Retries: 0.

## Silent error rate and automation rate (D-084)

silent error: a value is shown, it is wrong, and it is not flagged needs review or in an open conflict; automation: the value is correct and not flagged. An empty field counts as flagged (it shows as missing). Rates are over scored field values; files whose call failed are left out and counted apart (D-084).

Files with a failed call, not in the rates: 0.

| Field | Scored | Silent errors | Silent error rate | Automated | Automation rate |
|---|---|---|---|---|---|
| named_insured | 20 | 0 | 0.0 | 16 | 0.8 |
| premises | 20 | 0 | 0.0 | 16 | 0.8 |
| effective_date | 20 | 0 | 0.0 | 16 | 0.8 |
| operations | 20 | 0 | 0.0 | 0 | 0.0 |
| sales | 20 | 0 | 0.0 | 14 | 0.7 |
| tiv | 20 | 0 | 0.0 | 15 | 0.75 |
| construction | 20 | 0 | 0.0 | 16 | 0.8 |
| year_built | 20 | 0 | 0.0 | 16 | 0.8 |
| loss_runs | 20 | 0 | 0.0 | 15 | 0.75 |
| overall | 180 | 0 | 0.0 | 124 | 0.689 |
