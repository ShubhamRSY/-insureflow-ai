# Extraction score (scorer v11) — SUB-238 through SUB-269

- Author: @ai-engineer-assistant
- 9 of 9 extracted fields scored; claims not read; loss runs = date only.
- Commit: b0c78d54e1f30a2afcc4e29ee7d2bb9f2ffe44be (last pipeline commit 8d605acce37f06f719b5a865a79d783bc3e9c800).
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
| operations | 13 | 0 | 7 | 0 | 0 | 0 |
| sales | 20 | 0 | 0 | 0 | 0 | 0 |
| tiv | 20 | 0 | 0 | 0 | 0 | 0 |
| construction | 20 | 0 | 0 | 0 | 0 | 0 |
| year_built | 20 | 0 | 0 | 0 | 0 | 0 |
| loss_runs | 16 | 0 | 0 | 4 | 0 | 0 |
| conflict | 17 | 0 | 3 | 0 | 0 | 0 |
| status | 11 | 0 | 9 | 0 | 0 | 0 |
| route | 19 | 0 | 1 | 0 | 0 | 0 |

## Status safety and status automation (B-325)

- False completes (plain "complete" on a gold-incomplete file): **0** (none). Critical: must be 0.
- Status automation: 1 of 10 gold-complete files shown as plain "complete". "complete — review pending" is safe but not automated.
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
  - criterion 1 scanned application: 4/4
  - criterion 2 multiple locations: 5/5
  - criterion 3 non-English: 4/4
  - criterion 4 application not identified: 2/2
- Reason accuracy (reported): 12/12 manual-intake cards list every gold criterion.
- False manual intake: 0 of 20 in-scope files (none). At most 2; within the ceiling, they are left out of the in-scope counts above.
- P-055 scope gate: **PASS**.

## Per submission

- SUB-258 (out of scope, criteria 4): manual intake: yes. Reason codes: not_identified. Leaks: none.
- SUB-259 (out of scope, criteria 4): manual intake: yes. Reason codes: not_identified. Leaks: none.
- SUB-260 (out of scope, criteria 1): manual intake: yes. Reason codes: scanned_application. Leaks: none.
- SUB-261 (out of scope, criteria 1): manual intake: yes. Reason codes: scanned_application. Leaks: none.
- SUB-262 (out of scope, criteria 1): manual intake: yes. Reason codes: scanned_application. Leaks: none.
- SUB-263 (out of scope, criteria 1, 2): manual intake: yes. Reason codes: scanned_application, multiple_locations. Leaks: none.
- SUB-264 (out of scope, criteria 2): manual intake: yes. Reason codes: multiple_locations. Leaks: none.
- SUB-265 (out of scope, criteria 2): manual intake: yes. Reason codes: multiple_locations. Leaks: none.
- SUB-266 (out of scope, criteria 3): manual intake: yes. Reason codes: non_english. Leaks: none.
- SUB-267 (out of scope, criteria 3): manual intake: yes. Reason codes: non_english. Leaks: none.
- SUB-268 (out of scope, criteria 2, 3): manual intake: yes. Reason codes: multiple_locations, non_english. Leaks: none.
- SUB-269 (out of scope, criteria 2, 3): manual intake: yes. Reason codes: multiple_locations, non_english. Leaks: none.
- SUB-238 (typed md app, email, typed md loss run (Carrier C)): extracted name Cobalt Room Nightlife LLC. Misses: none. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-239 (typed md app, email, image-only PDF loss run (read by eye)): extracted name Pale Moon Lounge Inc. Misses: operations. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-240 (typed pdf app (text layer), typed md loss run (Carrier B), email): extracted name Rosetta Trattoria LLC. Misses: none. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-241 (typed md app, email, undated no-known-loss letter): extracted name Saigon Mint Cafe LLC. Misses: none. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-242 (typed md app, email, typed md loss run (Carrier A, undated)): extracted name Gulf Coast Frozen Foods Inc. Misses: none. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-243 (typed md app, typed md loss run (Carrier A), schedule csv, email): extracted name Pedal & Spoke Cycle Co LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-244 (typed md app, email; no loss run): extracted name Lone Star Roof Pros LLC. Misses: operations. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-245 (typed md app, typed md loss run (Carrier C), email): extracted name Mesquite Hollow Apartments LP. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-246 (typed md app, typed md loss run (Carrier A), schedule csv, email): extracted name Heritage Oak Office Plaza LLC. Misses: operations, status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-247 (typed md app, typed md loss run (Carrier B), email): extracted name Brisket & Bread Deli LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-248 (typed md app, email, dated no-known-loss letter): extracted name Cedar Mill Professional Center LLC. Misses: operations. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-249 (typed md app, typed md loss run (Carrier B), schedule csv, email): extracted name Corner Stop Deli & Market Inc. Misses: conflict. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-250 (typed md app, typed md loss run (Carrier A), schedule csv, email): extracted name Kestrel Tax & Phone Repair LLC. Misses: operations, status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-251 (typed md app, typed md loss run (Carrier C), schedule csv, email): extracted name Grape & Gravel Wine Shop LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-252 (typed md app, typed md loss run (Carrier C), email): extracted name Hollow Oak Pub & Office Suites LLC. Misses: conflict, route. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-253 (typed md app, email, scanned JPG loss run (read by eye)): extracted name Dragon Pearl Wok Kitchen Inc. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-254 (typed md app, typed md loss run (Carrier C, undated), schedule csv, email): extracted name Panhandle Electric Supply Co. Misses: operations. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-255 (typed md app, typed md loss run (Carrier B), schedule csv, email): extracted name Mesquite Cabinet Works LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-256 (typed md app, email, image-only PDF loss run (read by eye), schedule csv): extracted name Pecan Court Apartments LP. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-257 (typed md app, typed md loss run (Carrier A), schedule csv, email): extracted name Second Chance Threads & Thrift LLC. Misses: operations, conflict. Flagged: none. Call: called: reply used. Retries: 0.

## Silent error rate and automation rate (D-084)

silent error: a value is shown, it is wrong, and it is not flagged needs review or in an open conflict; automation: the value is correct and not flagged. An empty field counts as flagged (it shows as missing). Rates are over scored field values; files whose call failed are left out and counted apart (D-084).

Files with a failed call, not in the rates: 0.

| Field | Scored | Silent errors | Silent error rate | Automated | Automation rate |
|---|---|---|---|---|---|
| named_insured | 20 | 0 | 0.0 | 20 | 1.0 |
| premises | 20 | 0 | 0.0 | 20 | 1.0 |
| effective_date | 20 | 0 | 0.0 | 20 | 1.0 |
| operations | 20 | 0 | 0.0 | 6 | 0.3 |
| sales | 20 | 0 | 0.0 | 20 | 1.0 |
| tiv | 20 | 0 | 0.0 | 20 | 1.0 |
| construction | 20 | 0 | 0.0 | 20 | 1.0 |
| year_built | 20 | 0 | 0.0 | 19 | 0.95 |
| loss_runs | 20 | 0 | 0.0 | 8 | 0.4 |
| overall | 180 | 0 | 0.0 | 153 | 0.85 |
