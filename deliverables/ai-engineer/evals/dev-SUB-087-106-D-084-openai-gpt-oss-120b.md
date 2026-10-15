# DEVELOPMENT CHECK — SUB-087 through SUB-106 (D-084-openai-gpt-oss-120b), not a hold-out score

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
| named_insured | 10 | 0 | 2 | 0 | 0 | 0 |
| premises | 6 | 0 | 6 | 0 | 0 | 0 |
| effective_date | 7 | 0 | 5 | 0 | 0 | 0 |
| operations | 8 | 0 | 4 | 0 | 0 | 0 |
| sales | 9 | 1 | 2 | 0 | 0 | 0 |
| tiv | 8 | 0 | 4 | 0 | 0 | 0 |
| construction | 9 | 0 | 3 | 0 | 0 | 0 |
| year_built | 6 | 0 | 6 | 0 | 0 | 0 |
| loss_runs | 7 | 0 | 0 | 5 | 0 | 0 |
| conflict | 5 | 1 | 5 | 1 | 0 | 0 |
| status | 4 | 1 | 6 | 1 | 0 | 0 |

## Per submission

- SUB-087 (typed PDF app, typed loss run, csv schedule, email): extracted name Blue Heron Kitchen LLC. Misses: status. Flagged: none. Call: from cache: saved reply used, no call in this run.
- SUB-088 (rotated handwritten-style scan plus email): extracted name Harvest Crumb Bakery LLC. Misses: effective_date, operations, year_built, premises, tiv. Flagged: none. Call: from cache: saved reply used, no call in this run.
- SUB-089 (typed md app, xlsx schedule with 3 locations, typed loss run): extracted name Ironwood Residential Partners LLC. Misses: year_built, premises, conflict, status. Flagged: none. Call: from cache: saved reply used, no call in this run.
- SUB-090 (Spanish typed app and Spanish email): extracted name null. Misses: named_insured, conflict. Flagged: none. Call: from cache: saved reply used, no call in this run.
- SUB-091 (typed PDF app and loss run, email): extracted name Kettle & Spur Lounge LLC. Misses: sales, status. Flagged: none. Call: from cache: saved reply used, no call in this run.
- SUB-092 (typed PDF app and loss run, xlsx schedule, email): extracted name Border Cold Storage Distributors LLC. Misses: construction, conflict, status. Flagged: none. Call: from cache: saved reply used, no call in this run.
- SUB-093 (email only): extracted name Pine Hollow Accounting PLLC. Misses: effective_date, premises, tiv. Flagged: none. Call: from cache: saved reply used, no call in this run.
- SUB-094 (typed md app, xlsx schedule, typed loss run, email): extracted name Lone Oak Signworks LLC. Misses: sales, year_built, tiv, conflict. Flagged: none. Call: from cache: saved reply used, no call in this run.
- SUB-095 (typed PDF app, csv schedule, email, duplicate resubmission): extracted name Lone Oak Signworks LLC. Misses: none. Flagged: none. Call: from cache: saved reply used, no call in this run.
- SUB-096 (typed md app, xlsx schedule with 3 locations, typed loss run, email): extracted name Mesquite Home and Gift Co LLC. Misses: effective_date, operations, construction, year_built, premises, tiv, conflict, status. Flagged: none. Call: from cache: saved reply used, no call in this run.
- SUB-097 (dark tilted handwritten-style scan plus email): extracted name null. Misses: named_insured, effective_date, operations, year_built, premises. Flagged: none. Call: from cache: saved reply used, no call in this run.
- SUB-098 (typed md app, typed loss run, email): extracted name Caprock Tile & Stone Inc. Misses: effective_date, operations, construction, year_built, premises, status. Flagged: none. Call: from cache: saved reply used, no call in this run.
- SUB-099 (None): extracted name null. Misses: none. Flagged: none. Call: not run.
- SUB-100 (None): extracted name null. Misses: none. Flagged: none. Call: not run.
- SUB-101 (None): extracted name null. Misses: none. Flagged: none. Call: not run.
- SUB-102 (None): extracted name null. Misses: none. Flagged: none. Call: not run.
- SUB-103 (None): extracted name null. Misses: none. Flagged: none. Call: not run.
- SUB-104 (None): extracted name null. Misses: none. Flagged: none. Call: not run.
- SUB-105 (None): extracted name null. Misses: none. Flagged: none. Call: not run.
- SUB-106 (None): extracted name null. Misses: none. Flagged: none. Call: not run.

## Silent error rate and automation rate (D-084)

silent error: a value is shown, it is wrong, and it is not flagged needs review or in an open conflict; automation: the value is correct and not flagged. An empty field counts as flagged (it shows as missing). Rates are over scored field values; files whose call failed are left out and counted apart (D-084).

Files with a failed call, not in the rates: 0.

| Field | Scored | Silent errors | Silent error rate | Automated | Automation rate |
|---|---|---|---|---|---|
| named_insured | 12 | 0 | 0.0 | 9 | 0.75 |
| premises | 12 | 1 | 0.083 | 6 | 0.5 |
| effective_date | 12 | 0 | 0.0 | 7 | 0.583 |
| operations | 12 | 0 | 0.0 | 7 | 0.583 |
| sales | 12 | 0 | 0.0 | 8 | 0.667 |
| tiv | 12 | 1 | 0.083 | 8 | 0.667 |
| construction | 12 | 0 | 0.0 | 7 | 0.583 |
| year_built | 12 | 0 | 0.0 | 6 | 0.5 |
| loss_runs | 12 | 0 | 0.0 | 7 | 0.583 |
| overall | 108 | 2 | 0.019 | 65 | 0.602 |

- Run: {"model": "openai/gpt-oss-120b", "stopped_at": "SUB-099", "files_run": 12, "seconds_per_file": 0.1, "tokens": {"hosts": ["api.groq.com"], "model_calls": 0, "from_cache": 12, "tokens": 0, "failed_attempts": {"rate_limit_429": 0, "timeout": 0, "other": 0, "reply_not_usable": 0}}, "failed_attempts": {"rate_limit_429": 0, "timeout": 0, "other": 0, "reply_not_usable": 0}}
- STOPPED: daily limit hit at SUB-099; later files not run.
