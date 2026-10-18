# Extraction score (scorer v6) — SUB-174 through SUB-205

- Author: @ai-engineer-assistant
- 9 of 9 extracted fields scored; claims not read; loss runs = date only.
- Commit: 066d774b8eb4ed4227f513038076f9ed0efa7f8f (last pipeline commit 6e7cfa2a9896c24658bf8c8aa4404157e9a33fed).
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
| operations | 12 | 0 | 8 | 0 | 0 | 0 |
| sales | 19 | 0 | 1 | 0 | 0 | 0 |
| tiv | 20 | 0 | 0 | 0 | 0 | 0 |
| construction | 20 | 0 | 0 | 0 | 0 | 0 |
| year_built | 20 | 0 | 0 | 0 | 0 | 0 |
| loss_runs | 9 | 0 | 8 | 3 | 0 | 0 |
| conflict | 15 | 0 | 5 | 0 | 0 | 0 |
| status | 11 | 0 | 9 | 0 | 0 | 0 |
| route | 16 | 0 | 4 | 0 | 0 | 0 |

## Status safety and status automation (B-325)

- False completes (plain "complete" on a gold-incomplete file): **0** (none). Critical: must be 0.
- Status automation: 0 of 9 gold-complete files shown as plain "complete". "complete — review pending" is safe but not automated.
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
  - criterion 1 scanned application: 4/4
  - criterion 2 multiple locations: 5/5
  - criterion 3 non-English: 4/4
  - criterion 4 application not identified: 2/2
- Reason accuracy (reported): 12/12 manual-intake cards list every gold criterion.
- False manual intake: 0 of 20 in-scope files (none). At most 2; within the ceiling, they are left out of the in-scope counts above.
- P-055 scope gate: **PASS**.

## Per submission

- SUB-188 (out of scope, criteria 1): manual intake: yes. Reason codes: scanned_application. Leaks: none.
- SUB-189 (out of scope, criteria 1): manual intake: yes. Reason codes: scanned_application. Leaks: none.
- SUB-190 (out of scope, criteria 1, 2): manual intake: yes. Reason codes: scanned_application, multiple_locations. Leaks: none.
- SUB-191 (out of scope, criteria 2): manual intake: yes. Reason codes: multiple_locations. Leaks: none.
- SUB-192 (out of scope, criteria 2): manual intake: yes. Reason codes: multiple_locations. Leaks: none.
- SUB-193 (out of scope, criteria 3): manual intake: yes. Reason codes: non_english. Leaks: none.
- SUB-194 (out of scope, criteria 2, 3): manual intake: yes. Reason codes: multiple_locations, non_english. Leaks: none.
- SUB-195 (out of scope, criteria 1, 3): manual intake: yes. Reason codes: scanned_application, non_english. Leaks: none.
- SUB-196 (out of scope, criteria 3): manual intake: yes. Reason codes: non_english. Leaks: none.
- SUB-197 (out of scope, criteria 4): manual intake: yes. Reason codes: not_identified. Leaks: none.
- SUB-198 (out of scope, criteria 4): manual intake: yes. Reason codes: not_identified. Leaks: none.
- SUB-199 (out of scope, criteria 2): manual intake: yes. Reason codes: multiple_locations. Leaks: none.
- SUB-174 (typed md app, JPG scan of a Carrier A loss run, email, no schedule): extracted name Sunbelt Office Suites LLC. Misses: conflict, status, route. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-175 (typed md app, image-only PDF scan of a Carrier B loss run, email): extracted name Marisol's Bakery & Cafe LLC. Misses: operations, status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-176 (typed md app, owner's no-known-loss letter, Spanish email, no schedule): extracted name Greenway Pet Grooming LLC. Misses: none. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-177 (typed md app, typed md Redbud table, csv one-row schedule, email): extracted name La Esquina Tortilleria LLC. Misses: operations, loss_runs. Flagged: none. Call: called: reply used. Retries: 1 (rate_limit_429).
- SUB-178 (typed md app, typed md Brazos table, csv one-row schedule, email): extracted name Ridgeline Auto Glass Repair LLC. Misses: loss_runs. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-179 (typed md app, typed md Carrier A loss run, csv one-row schedule, email): extracted name Pinecrest Tax & Accounting PLLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-180 (typed md app, owner's no-known-loss letter, email, no schedule): extracted name Brazos Pottery Studio LLC. Misses: operations, conflict. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-181 (typed md app, typed md Redbud table, csv one-row schedule, email): extracted name Lone Star Tire & Lube Inc. Misses: loss_runs. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-182 (typed md app, typed md Carrier B loss run, email, no schedule): extracted name Gulf Coast Sub & Deli Co. Misses: operations, conflict, status, route. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-183 (typed md app, typed md Carrier A loss run with no-claims line, xlsx one-row schedule, email): extracted name Stellar Self Storage LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-184 (typed PDF app (text layer), typed md Carrier A loss run, email): extracted name Keller Insurance Services PA. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-185 (typed md app, typed md Carrier C loss run, csv one-row schedule, email): extracted name Sierra Vista Apartments LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 3 (rate_limit_429, rate_limit_429, rate_limit_429).
- SUB-186 (typed PDF app (text layer), typed md Carrier B loss run, email): extracted name Dos Rios Grill LLC. Misses: operations, status, route. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-187 (typed md app, typed md Carrier C loss run, email, no schedule): extracted name Carrizo Court Apartments LLC. Misses: status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-200 (typed md app, typed md Redbud table, email, no schedule): extracted name Brenner Roofing & Sheet Metal Inc. Misses: loss_runs. Flagged: none. Call: called: reply used. Retries: 1 (rate_limit_429).
- SUB-201 (typed md app, typed md Brazos table (open claim), email, no schedule): extracted name Velvet Room Lounge LLC. Misses: operations, loss_runs, route. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-202 (typed md app, typed md Caprock table, csv one-row schedule (year built blank), email): extracted name Oakhurst Physical Therapy LLC. Misses: loss_runs. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-203 (typed md app, typed md Redbud table, csv one-row schedule, email): extracted name Blue Heron Coffee Roasters LLC. Misses: operations, loss_runs, conflict. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-204 (typed md app, typed md Brazos table, email, no schedule): extracted name Tejas Pool & Patio Supply. Misses: operations, sales, loss_runs, conflict. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-205 (typed md app, email, no loss run, no schedule): extracted name Sabine Pass Seafood Market LLC. Misses: none. Flagged: none. Call: called: reply used. Retries: 0.

## Silent error rate and automation rate (D-084)

silent error: a value is shown, it is wrong, and it is not flagged needs review or in an open conflict; automation: the value is correct and not flagged. An empty field counts as flagged (it shows as missing). Rates are over scored field values; files whose call failed are left out and counted apart (D-084).

Files with a failed call, not in the rates: 0.

| Field | Scored | Silent errors | Silent error rate | Automated | Automation rate |
|---|---|---|---|---|---|
| named_insured | 20 | 0 | 0.0 | 20 | 1.0 |
| premises | 20 | 0 | 0.0 | 20 | 1.0 |
| effective_date | 20 | 0 | 0.0 | 20 | 1.0 |
| operations | 20 | 3 | 0.15 | 9 | 0.45 |
| sales | 20 | 0 | 0.0 | 19 | 0.95 |
| tiv | 20 | 0 | 0.0 | 20 | 1.0 |
| construction | 20 | 0 | 0.0 | 20 | 1.0 |
| year_built | 20 | 0 | 0.0 | 19 | 0.95 |
| loss_runs | 20 | 0 | 0.0 | 0 | 0.0 |
| overall | 180 | 3 | 0.017 | 147 | 0.817 |
