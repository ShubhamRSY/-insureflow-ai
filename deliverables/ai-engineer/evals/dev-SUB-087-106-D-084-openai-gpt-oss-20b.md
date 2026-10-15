# DEVELOPMENT CHECK — SUB-087 through SUB-106 (D-084-openai-gpt-oss-20b), not a hold-out score

- Author: @ai-engineer-assistant
- 9 of 9 extracted fields scored; claims not read; loss runs = date only.
- Commit: 3d961ded180059ea28a7829d29ebd4d803b7045b, with uncommitted changes in: underwriting_pipeline/ai/prepare.py, underwriting_pipeline/ai/regression_dev.py, underwriting_pipeline/app/workbench.py. This is not a score of that commit.
- Development data since D-082: the gold was seen while the code changed. Not a hold-out.
- A null that matches a missing gold line is not_credited. It is not a correct answer.
- Correctly flagged for human means the documents disagree and the AI stored both sides without picking one. It is not a hit and not a miss.
- Synthetic. Not a production approval.

## Per-field

| Field | Hit | Hit (needs review) | Miss | Not credited | Correctly flagged for human | Call failed |
|---|---|---|---|---|---|---|
| named_insured | 12 | 0 | 4 | 0 | 0 | 4 |
| premises | 8 | 0 | 8 | 0 | 0 | 4 |
| effective_date | 9 | 0 | 7 | 0 | 0 | 4 |
| operations | 12 | 0 | 4 | 0 | 0 | 4 |
| sales | 6 | 1 | 9 | 0 | 0 | 4 |
| tiv | 10 | 0 | 6 | 0 | 0 | 4 |
| construction | 13 | 0 | 3 | 0 | 0 | 4 |
| year_built | 9 | 0 | 7 | 0 | 0 | 4 |
| loss_runs | 8 | 0 | 3 | 5 | 0 | 4 |
| conflict | 12 | 0 | 2 | 2 | 0 | 4 |
| status | 6 | 0 | 8 | 2 | 0 | 4 |

## Per submission

- SUB-087 (typed PDF app, typed loss run, csv schedule, email): extracted name Blue Heron Kitchen LLC. Misses: status. Flagged: none. Call: called: reply used.
- SUB-088 (rotated handwritten-style scan plus email): extracted name null. Misses: none. Flagged: none. Call: call failed: Expecting ',' delimiter: line 1 column 839 (char 838).
- SUB-089 (typed md app, xlsx schedule with 3 locations, typed loss run): extracted name Ironwood Residential Partners LLC. Misses: sales, year_built, premises, tiv, status. Flagged: none. Call: called: reply used.
- SUB-090 (Spanish typed app and Spanish email): extracted name null. Misses: named_insured, effective_date, operations, sales, construction, year_built, premises, tiv. Flagged: none. Call: called: every value rejected by the gate.
- SUB-091 (typed PDF app and loss run, email): extracted name Kettle & Spur Lounge LLC. Misses: sales, status. Flagged: none. Call: called: reply used.
- SUB-092 (typed PDF app and loss run, xlsx schedule, email): extracted name Border Cold Storage Distributors LLC. Misses: sales, status. Flagged: none. Call: called: reply used.
- SUB-093 (email only): extracted name Pine Hollow Accounting PLLC. Misses: effective_date, premises, tiv. Flagged: none. Call: called: reply used.
- SUB-094 (typed md app, xlsx schedule, typed loss run, email): extracted name null. Misses: none. Flagged: none. Call: call failed: Unterminated string starting at: line 1 column 107 (char 106).
- SUB-095 (typed PDF app, csv schedule, email, duplicate resubmission): extracted name Lone Oak Signworks LLC. Misses: none. Flagged: none. Call: called: reply used.
- SUB-096 (typed md app, xlsx schedule with 3 locations, typed loss run, email): extracted name null. Misses: none. Flagged: none. Call: call failed: Expecting value: line 1 column 1 (char 0).
- SUB-097 (dark tilted handwritten-style scan plus email): extracted name null. Misses: named_insured, effective_date, operations, year_built, premises. Flagged: none. Call: called: reply used.
- SUB-098 (typed md app, typed loss run, email): extracted name null. Misses: named_insured, effective_date, sales, construction, year_built, premises, tiv, loss_runs, status. Flagged: none. Call: called: reply used.
- SUB-099 (typed PDF app, typed loss run, csv schedule, email): extracted name Brazos Paper & Janitorial Supply LLC. Misses: effective_date, operations, sales, construction, year_built, premises, tiv, loss_runs, status. Flagged: none. Call: called: reply used.
- SUB-100 (typed PDF app, typed loss run, email contradicting the app): extracted name Cottonwood Court Apartments LLC. Misses: year_built, conflict. Flagged: none. Call: called: reply used.
- SUB-101 (typed md app, csv schedule, scanned loss run, email): extracted name null. Misses: named_insured, effective_date, sales, year_built, premises, tiv, loss_runs, status. Flagged: none. Call: called: reply used.
- SUB-102 (email, typed loss run, csv schedule, duplicate of SUB-087 with changed facts): extracted name Blue Heron Kitchen LLC. Misses: effective_date, operations, sales, premises, status. Flagged: none. Call: called: reply used.
- SUB-103 (typed md app, xlsx schedule, typed loss run, email): extracted name null. Misses: none. Flagged: none. Call: call failed: Expecting value: line 1 column 1 (char 0).
- SUB-104 (Spanish typed app, Spanish loss letter, Spanish email): extracted name Lavandería Estrella del Norte LLC. Misses: none. Flagged: none. Call: called: reply used.
- SUB-105 (typed PDF app and loss run, email): extracted name Sakura Ridge Grill & Sushi LLC. Misses: none. Flagged: none. Call: called: reply used.
- SUB-106 (typed PDF app plus email contradicting the app): extracted name Redbud Engineering Consulting LLC. Misses: sales, conflict. Flagged: none. Call: called: reply used.

## Silent error rate and automation rate (D-084)

silent error: a value is shown, it is wrong, and it is not flagged needs review or in an open conflict; automation: the value is correct and not flagged. An empty field counts as flagged (it shows as missing). Rates are over scored field values; files whose call failed are left out and counted apart (D-084).

Files with a failed call, not in the rates: 4.

| Field | Scored | Silent errors | Silent error rate | Automated | Automation rate |
|---|---|---|---|---|---|
| named_insured | 16 | 0 | 0.0 | 12 | 0.75 |
| premises | 16 | 1 | 0.062 | 8 | 0.5 |
| effective_date | 16 | 0 | 0.0 | 9 | 0.562 |
| operations | 16 | 1 | 0.062 | 11 | 0.688 |
| sales | 16 | 0 | 0.0 | 6 | 0.375 |
| tiv | 16 | 1 | 0.062 | 10 | 0.625 |
| construction | 16 | 0 | 0.0 | 12 | 0.75 |
| year_built | 16 | 0 | 0.0 | 9 | 0.562 |
| loss_runs | 16 | 0 | 0.0 | 8 | 0.5 |
| overall | 144 | 3 | 0.021 | 85 | 0.59 |

- Run: {"model": "openai/gpt-oss-20b", "stopped_at": null, "files_run": 20, "seconds_per_file": 58.6, "tokens": {"hosts": ["api.groq.com"], "model_calls": 30, "from_cache": 0, "tokens": 83650, "failed_attempts": {"rate_limit_429": 6, "timeout": 0, "other": 19, "reply_not_usable": 14}}, "failed_attempts": {"rate_limit_429": 6, "timeout": 0, "other": 19, "reply_not_usable": 14}}
