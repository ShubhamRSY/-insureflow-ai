# Hold-out extraction score — SUB-087 through SUB-106

- Author: @ai-engineer-assistant
- 9 of 9 extracted fields scored; claims not read; loss runs = date only.
- Commit: 9e725e3d067d4b1d30725a46b8d284c4678f38bf.
- Scored by @model-risk with this file unchanged after the gold answers were written.
- A null that matches a missing gold line is not_credited. It is not a correct answer.
- Correctly flagged for human means the documents disagree and the AI stored both sides without picking one. It is not a hit and not a miss.
- Synthetic. Not a production approval.

## Per-field

| Field | Hit | Hit (needs review) | Miss | Not credited | Correctly flagged for human | Call failed |
|---|---|---|---|---|---|---|
| named_insured | 17 | 0 | 2 | 0 | 0 | 1 |
| premises | 7 | 0 | 12 | 0 | 0 | 1 |
| effective_date | 14 | 0 | 5 | 0 | 0 | 1 |
| operations | 12 | 0 | 7 | 0 | 0 | 1 |
| sales | 12 | 0 | 6 | 0 | 1 | 1 |
| tiv | 13 | 0 | 6 | 0 | 0 | 1 |
| construction | 13 | 0 | 6 | 0 | 0 | 1 |
| year_built | 11 | 0 | 7 | 0 | 1 | 1 |
| loss_runs | 13 | 0 | 0 | 6 | 0 | 1 |
| conflict | 10 | 0 | 7 | 0 | 2 | 1 |
| status | 10 | 0 | 9 | 0 | 0 | 1 |

## Per submission

- SUB-087 (typed PDF app, typed loss run, csv schedule, email): extracted name Blue Heron Kitchen LLC. Misses: status. Flagged: none. Call: called: reply used.
- SUB-088 (rotated handwritten-style scan plus email): extracted name Harvest Crumb Bakery LLC. Misses: operations, construction, year_built, premises, tiv. Flagged: none. Call: called: reply used.
- SUB-089 (typed md app, xlsx schedule with 3 locations, typed loss run): extracted name Ironwood Residential Partners LLC. Misses: construction, year_built, premises, status. Flagged: none. Call: called: reply used.
- SUB-090 (Spanish typed app and Spanish email): extracted name Taquería Luna Verde LLC. Misses: none. Flagged: none. Call: called: reply used.
- SUB-091 (typed PDF app and loss run, email): extracted name Kettle & Spur Lounge LLC. Misses: none. Flagged: none. Call: called: reply used.
- SUB-092 (typed PDF app and loss run, xlsx schedule, email): extracted name Border Cold Storage Distributors LLC. Misses: construction, premises, conflict, status. Flagged: none. Call: called: reply used.
- SUB-093 (email only): extracted name Pine Hollow Accounting PLLC. Misses: effective_date, premises, tiv. Flagged: none. Call: called: reply used.
- SUB-094 (typed md app, xlsx schedule, typed loss run, email): extracted name Lone Oak Signworks LLC. Misses: sales, year_built, premises, tiv, conflict. Flagged: none. Call: called: reply used.
- SUB-095 (typed PDF app, csv schedule, email, duplicate resubmission): extracted name Lone Oak Signworks LLC. Misses: sales, premises, conflict. Flagged: none. Call: called: reply used.
- SUB-096 (typed md app, xlsx schedule with 3 locations, typed loss run, email): extracted name Mesquite Home and Gift Co LLC. Misses: effective_date, operations, sales, construction, year_built, premises, tiv, conflict, status. Flagged: none. Call: called: reply used.
- SUB-097 (dark tilted handwritten-style scan plus email): extracted name Bayou Smokehouse and Grill LLC. Misses: named_insured, effective_date, sales, construction, year_built, premises. Flagged: none. Call: called: reply used.
- SUB-098 (typed md app, typed loss run, email): extracted name null. Misses: named_insured, effective_date, operations, sales, construction, year_built, premises, tiv, conflict, status. Flagged: none. Call: called: reply used.
- SUB-099 (typed PDF app, typed loss run, csv schedule, email): extracted name Brazos Paper & Janitorial Supply LLC. Misses: operations, premises, conflict, status. Flagged: none. Call: called: reply used.
- SUB-100 (typed PDF app, typed loss run, email contradicting the app): extracted name Cottonwood Court Apartments LLC. Misses: operations. Flagged: year_built, conflict. Call: called: reply used.
- SUB-101 (typed md app, csv schedule, scanned loss run, email): extracted name null. Misses: none. Flagged: none. Call: call failed: 'str' object has no attribute 'get'.
- SUB-102 (email, typed loss run, csv schedule, duplicate of SUB-087 with changed facts): extracted name Blue Heron Kitchen LLC. Misses: effective_date, premises, status. Flagged: none. Call: called: reply used.
- SUB-103 (typed md app, xlsx schedule, typed loss run, email): extracted name Piney Woods Cabinet Works LLC. Misses: operations, premises, conflict, status. Flagged: none. Call: called: reply used.
- SUB-104 (Spanish typed app, Spanish loss letter, Spanish email): extracted name Lavandería Estrella del Norte LLC. Misses: operations, sales, year_built, tiv, status. Flagged: none. Call: called: reply used.
- SUB-105 (typed PDF app and loss run, email): extracted name Sakura Ridge Grill & Sushi LLC. Misses: none. Flagged: none. Call: called: reply used.
- SUB-106 (typed PDF app plus email contradicting the app): extracted name Redbud Engineering Consulting LLC. Misses: none. Flagged: sales, conflict. Call: called: reply used.
