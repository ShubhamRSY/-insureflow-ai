# Extraction score (scorer v11) — SUB-550 through SUB-581

- Author: @ai-engineer-assistant
- 9 of 9 extracted fields scored; claims not read; loss runs = date only.
- Commit: fffdcca5ba346ddb625fac46bbb2458cd389444d (last pipeline commit 1ddae83c9b3755a6b9c4ffe383347f17251ebb01).
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
| sales | 17 | 0 | 0 | 0 | 3 | 0 |
| tiv | 19 | 0 | 0 | 0 | 1 | 0 |
| construction | 20 | 0 | 0 | 0 | 0 | 0 |
| year_built | 19 | 0 | 1 | 0 | 0 | 0 |
| loss_runs | 20 | 0 | 0 | 0 | 0 | 0 |
| conflict | 10 | 0 | 2 | 0 | 8 | 0 |
| status | 10 | 0 | 10 | 0 | 0 | 0 |
| route | 19 | 0 | 1 | 0 | 0 | 0 |

## Status safety and status automation (B-325)

- False completes (plain "complete" on a gold-incomplete file): **0** (none). Critical: must be 0.
- Status automation: 0 of 10 gold-complete files shown as plain "complete". "complete — review pending" is safe but not automated.
- Failed calls, left out of both: 0.
- Operations scored by checklist (v5): 20 of 20 files; the rest by the v4 word rule.

## T-027 route gate (D-096, D-097)

- Unsafe routes (a carrier, held or not, where gold says senior_referral or no_match): **0** (none). Must be 0.
- Route accuracy: 19/20 (0 files with no route mark). Must be at least 18/20.
- Route hits over all 20 in-scope gold files (none left out): 19/20. Gate rule unchanged.
- Route gate: **PASS**.

## P-055 scope gate (D-108, P-057), apart from the T-027 gate

- Files: 12 out of scope, 20 in scope (gold Scope lines). Out-of-scope files are not field-scored.
- Leakage (hard gate): **0** of 12 (none). Must be 0.
- Detection recall, overall: 12/12 (missed: none). Must be 100%.
  - criterion 1 scanned application: 2/2
  - criterion 2 multiple locations: 6/6
  - criterion 3 non-English: 2/2
  - criterion 4 application not identified: 2/2
- Reason accuracy (reported): 12/12 manual-intake cards list every gold criterion.
- False manual intake: 0 of 20 in-scope files (none). At most 2; within the ceiling, they are left out of the in-scope counts above.
- P-055 scope gate: **PASS**.

## Per submission

- SUB-570 (out of scope, criteria 1): manual intake: yes. Reason codes: scanned_application. Leaks: none.
- SUB-571 (out of scope, criteria 1): manual intake: yes. Reason codes: scanned_application. Leaks: none.
- SUB-572 (out of scope, criteria 2): manual intake: yes. Reason codes: multiple_locations. Leaks: none.
- SUB-573 (out of scope, criteria 2): manual intake: yes. Reason codes: multiple_locations. Leaks: none.
- SUB-574 (out of scope, criteria 2): manual intake: yes. Reason codes: multiple_locations. Leaks: none.
- SUB-575 (out of scope, criteria 2): manual intake: yes. Reason codes: multiple_locations. Leaks: none.
- SUB-576 (out of scope, criteria 2): manual intake: yes. Reason codes: multiple_locations. Leaks: none.
- SUB-577 (out of scope, criteria 2): manual intake: yes. Reason codes: multiple_locations. Leaks: none.
- SUB-578 (out of scope, criteria 3): manual intake: yes. Reason codes: non_english. Leaks: none.
- SUB-579 (out of scope, criteria 3): manual intake: yes. Reason codes: non_english. Leaks: none.
- SUB-580 (out of scope, criteria 4): manual intake: yes. Reason codes: not_identified. Leaks: none.
- SUB-581 (out of scope, criteria 4): manual intake: yes. Reason codes: not_identified. Leaks: none.
- SUB-550 (typed md app, typed md loss run (Carrier A), email): extracted name Yaupon Ridge Advisors LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 1 (rate_limit_429).
- SUB-551 (typed pdf app (text layer), typed md loss run (Carrier A), email): extracted name Calico Thread Apparel LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-552 (typed md app, typed md loss run (Carrier A), email): extracted name Big Thicket Dry Goods LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-553 (typed pdf app (text layer), typed md loss run (Carrier A), email): extracted name Pecan Bayou Consulting LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-554 (typed pdf app (text layer), typed md loss run (Carrier B), email): extracted name Sabine Current Electric LLC. Misses: none. Flagged: conflict. Call: called: reply used. Retries: 0.
- SUB-555 (typed md app, typed md loss run (Carrier C), email): extracted name Ship Channel Packaging Supply LLC. Misses: none. Flagged: sales, conflict. Call: called: reply used. Retries: 0.
- SUB-556 (typed md app, typed md loss run (Carrier B), email): extracted name Redbud Lawn & Landscape LLC. Misses: none. Flagged: sales, conflict. Call: called: reply used. Retries: 0.
- SUB-557 (typed md app, typed md loss run (Carrier C), email): extracted name Louetta Oaks Executive Suites LLC. Misses: operations, route. Flagged: conflict. Call: called: reply used. Retries: 0.
- SUB-558 (typed md app, typed md loss run (Carrier C), email): extracted name Chisos Professional Plaza LLC. Misses: none. Flagged: conflict. Call: called: reply used. Retries: 1 (timeout).
- SUB-559 (typed md app, typed md loss run (Carrier B), email): extracted name Caprock Roofing Co. Misses: none. Flagged: tiv, conflict. Call: called: reply used. Retries: 1 (rate_limit_429).
- SUB-560 (typed pdf app (text layer), typed md loss run (Carrier B), email): extracted name Bluebonnet Candle Co LLC. Misses: conflict. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-561 (typed md app, typed md loss run (Carrier B), email): extracted name Courthouse Square Deli LLC. Misses: year_built. Flagged: sales, conflict. Call: called: reply used. Retries: 0.
- SUB-562 (typed md app, typed md loss run (Carrier C), email): extracted name Mustang Island Deli LLC. Misses: conflict. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-563 (typed md app, typed md loss run (Carrier C), email): extracted name Iron Horse Tavern LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-564 (typed md app, typed md loss run (Carrier A), email): extracted name Coyote Moon Nightclub LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-565 (typed pdf app (text layer), typed md loss run (Carrier C), email): extracted name Prairie Dawn Restaurant LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-566 (typed md app, typed md loss run (Carrier B), email): extracted name Kolache Corner Bakery LLC. Misses: none. Flagged: conflict. Call: called: reply used. Retries: 0.
- SUB-567 (typed md app, typed md loss run (Carrier A), email): extracted name Tierra Alta Architects LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-568 (typed pdf app (text layer), typed md loss run (Carrier C), email): extracted name Vasquez & Lund PLLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-569 (typed md app, typed md loss run (Carrier A), email): extracted name Rio Frio Saddle & Tack LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.

## Silent error rate and automation rate (D-084)

silent error: a value is shown, it is wrong, and it is not flagged needs review or in an open conflict; automation: the value is correct and not flagged. An empty field counts as flagged (it shows as missing). Rates are over scored field values; files whose call failed are left out and counted apart (D-084).

Files with a failed call, not in the rates: 0.

| Field | Scored | Silent errors | Silent error rate | Automated | Automation rate |
|---|---|---|---|---|---|
| named_insured | 20 | 0 | 0.0 | 20 | 1.0 |
| premises | 20 | 0 | 0.0 | 20 | 1.0 |
| effective_date | 20 | 0 | 0.0 | 20 | 1.0 |
| operations | 20 | 0 | 0.0 | 0 | 0.0 |
| sales | 20 | 0 | 0.0 | 17 | 0.85 |
| tiv | 20 | 0 | 0.0 | 19 | 0.95 |
| construction | 20 | 0 | 0.0 | 20 | 1.0 |
| year_built | 20 | 1 | 0.05 | 19 | 0.95 |
| loss_runs | 20 | 0 | 0.0 | 20 | 1.0 |
| overall | 180 | 1 | 0.006 | 155 | 0.861 |
