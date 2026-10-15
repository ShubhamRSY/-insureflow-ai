# DEVELOPMENT CHECK — SUB-087 through SUB-106 (D-086-qwen-qwen3-8-27b), not a hold-out score

- Author: @ai-engineer-assistant
- 9 of 9 extracted fields scored; claims not read; loss runs = date only.
- Commit: 6ca8c0616cbe556b02dca67535bb7bc63ff799bb, with uncommitted changes in: underwriting_pipeline/ai/llm_extract.py, underwriting_pipeline/app/workbench.py. This is not a score of that commit.
- Development data since D-082: the gold was seen while the code changed. Not a hold-out.
- A null that matches a missing gold line is not_credited. It is not a correct answer.
- Correctly flagged for human means the documents disagree and the AI stored both sides without picking one. It is not a hit and not a miss.
- Synthetic. Not a production approval.

## Per-field

| Field | Hit | Hit (needs review) | Miss | Not credited | Correctly flagged for human | Call failed |
|---|---|---|---|---|---|---|
| named_insured | 19 | 0 | 1 | 0 | 0 | 0 |
| premises | 14 | 0 | 6 | 0 | 0 | 0 |
| effective_date | 17 | 0 | 3 | 0 | 0 | 0 |
| operations | 17 | 0 | 3 | 0 | 0 | 0 |
| sales | 17 | 1 | 1 | 0 | 1 | 0 |
| tiv | 17 | 0 | 3 | 0 | 0 | 0 |
| construction | 18 | 0 | 2 | 0 | 0 | 0 |
| year_built | 15 | 0 | 5 | 0 | 0 | 0 |
| loss_runs | 13 | 0 | 1 | 6 | 0 | 0 |
| conflict | 13 | 2 | 4 | 0 | 1 | 0 |
| status | 13 | 2 | 5 | 0 | 0 | 0 |

## Per submission

- SUB-087 (typed PDF app, typed loss run, csv schedule, email): extracted name Blue Heron Kitchen LLC. Misses: status. Flagged: none. Call: called: reply used.
- SUB-088 (rotated handwritten-style scan plus email): extracted name Harvest Crumb Bakery LLC. Misses: year_built, premises, tiv. Flagged: none. Call: called: reply used.
- SUB-089 (typed md app, xlsx schedule with 3 locations, typed loss run): extracted name Ironwood Residential Partners LLC. Misses: construction, year_built, premises, conflict, status. Flagged: none. Call: called: reply used.
- SUB-090 (Spanish typed app and Spanish email): extracted name Taquería Luna Verde LLC. Misses: none. Flagged: none. Call: called: reply used.
- SUB-091 (typed PDF app and loss run, email): extracted name Kettle & Spur Lounge LLC. Misses: operations. Flagged: none. Call: called: reply used.
- SUB-092 (typed PDF app and loss run, xlsx schedule, email): extracted name Border Cold Storage Distributors LLC. Misses: none. Flagged: none. Call: called: reply used.
- SUB-093 (email only): extracted name Pine Hollow Accounting PLLC. Misses: effective_date, premises, tiv. Flagged: none. Call: called: reply used.
- SUB-094 (typed md app, xlsx schedule, typed loss run, email): extracted name Lone Oak Signworks LLC. Misses: sales, year_built, tiv, conflict. Flagged: none. Call: called: reply used.
- SUB-095 (typed PDF app, csv schedule, email, duplicate resubmission): extracted name Lone Oak Signworks LLC. Misses: none. Flagged: none. Call: called: reply used.
- SUB-096 (typed md app, xlsx schedule with 3 locations, typed loss run, email): extracted name Mesquite Home and Gift Co LLC. Misses: construction, year_built, premises, conflict, status. Flagged: none. Call: called: reply used.
- SUB-097 (dark tilted handwritten-style scan plus email): extracted name Bayou Smokehouse and Grill LLC. Misses: named_insured, effective_date, year_built, premises. Flagged: none. Call: called: reply used.
- SUB-098 (typed md app, typed loss run, email): extracted name Caprock Tile & Stone Inc. Misses: none. Flagged: none. Call: called: reply used.
- SUB-099 (typed PDF app, typed loss run, csv schedule, email): extracted name Brazos Paper & Janitorial Supply LLC. Misses: operations. Flagged: none. Call: called: reply used.
- SUB-100 (typed PDF app, typed loss run, email contradicting the app): extracted name Cottonwood Court Apartments LLC. Misses: operations, conflict. Flagged: none. Call: called: reply used.
- SUB-101 (typed md app, csv schedule, scanned loss run, email): extracted name Pappa Sal's Pizza Co LLC. Misses: loss_runs, status. Flagged: none. Call: called: reply used.
- SUB-102 (email, typed loss run, csv schedule, duplicate of SUB-087 with changed facts): extracted name Blue Heron Kitchen LLC. Misses: effective_date, premises, status. Flagged: none. Call: called: reply used.
- SUB-103 (typed md app, xlsx schedule, typed loss run, email): extracted name Piney Woods Cabinet Works LLC. Misses: none. Flagged: none. Call: called: reply used.
- SUB-104 (Spanish typed app, Spanish loss letter, Spanish email): extracted name Lavandería Estrella del Norte LLC. Misses: none. Flagged: none. Call: called: reply used.
- SUB-105 (typed PDF app and loss run, email): extracted name Sakura Ridge Grill & Sushi LLC. Misses: none. Flagged: none. Call: called: reply used.
- SUB-106 (typed PDF app plus email contradicting the app): extracted name Redbud Engineering Consulting LLC. Misses: none. Flagged: sales, conflict. Call: called: reply used.

## Silent error rate and automation rate (D-084)

silent error: a value is shown, it is wrong, and it is not flagged needs review or in an open conflict; automation: the value is correct and not flagged. An empty field counts as flagged (it shows as missing). Rates are over scored field values; files whose call failed are left out and counted apart (D-084).

Files with a failed call, not in the rates: 0.

| Field | Scored | Silent errors | Silent error rate | Automated | Automation rate |
|---|---|---|---|---|---|
| named_insured | 20 | 1 | 0.05 | 19 | 0.95 |
| premises | 20 | 0 | 0.0 | 14 | 0.7 |
| effective_date | 20 | 0 | 0.0 | 17 | 0.85 |
| operations | 20 | 1 | 0.05 | 14 | 0.7 |
| sales | 20 | 0 | 0.0 | 16 | 0.8 |
| tiv | 20 | 1 | 0.05 | 17 | 0.85 |
| construction | 20 | 0 | 0.0 | 15 | 0.75 |
| year_built | 20 | 0 | 0.0 | 14 | 0.7 |
| loss_runs | 20 | 0 | 0.0 | 13 | 0.65 |
| overall | 180 | 3 | 0.017 | 139 | 0.772 |

- Run: {"model": "qwen/qwen3.8-27b", "stopped_at": null, "files_run": 20, "seconds_per_file": 3.9, "tokens": {"hosts": ["api.groq.com"], "model_calls": 20, "from_cache": 0, "tokens": 31884, "failed_attempts": {"rate_limit_429": 3, "timeout": 0, "other": 7, "reply_not_usable": 0}}, "failed_attempts": {"rate_limit_429": 3, "timeout": 0, "other": 7, "reply_not_usable": 0}}
