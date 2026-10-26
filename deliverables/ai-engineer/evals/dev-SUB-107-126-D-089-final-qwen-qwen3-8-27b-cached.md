# DEVELOPMENT CHECK — SUB-107 through SUB-126 (D-089-final-qwen-qwen3-8-27b-cached), not a hold-out score

- Author: @ai-engineer-assistant
- 9 of 9 extracted fields scored; claims not read; loss runs = date only.
- Commit: 19729a6b4ba987eb82435d589df008228bcf4b34.
- Development data since D-088: the gold was seen while the code changed. Not a hold-out.
- A null that matches a missing gold line is not_credited. It is not a correct answer.
- Correctly flagged for human means the documents disagree and the AI stored both sides without picking one. It is not a hit and not a miss.
- Synthetic. Not a production approval.

## Per-field

| Field | Hit | Hit (needs review) | Miss | Not credited | Correctly flagged for human | Call failed |
|---|---|---|---|---|---|---|
| named_insured | 19 | 1 | 0 | 0 | 0 | 0 |
| premises | 0 | 0 | 20 | 0 | 0 | 0 |
| effective_date | 18 | 0 | 1 | 1 | 0 | 0 |
| operations | 17 | 0 | 3 | 0 | 0 | 0 |
| sales | 17 | 1 | 2 | 0 | 0 | 0 |
| tiv | 19 | 0 | 1 | 0 | 0 | 0 |
| construction | 20 | 0 | 0 | 0 | 0 | 0 |
| year_built | 17 | 0 | 3 | 0 | 0 | 0 |
| loss_runs | 10 | 0 | 0 | 10 | 0 | 0 |
| conflict | 11 | 1 | 7 | 0 | 1 | 0 |
| status | 14 | 2 | 4 | 0 | 0 | 0 |

## Per submission

- SUB-107 (typed PDF app, typed loss run, csv schedule, email): extracted name Juniper Ridge Bookkeeping LLC. Misses: premises, status. Flagged: none. Call: from cache: saved reply used, no call in this run.
- SUB-108 (scanned PDF app, xlsx schedule, no-known-loss letter, email): extracted name Pecan Street Candle & Gift Co LLC. Misses: premises. Flagged: none. Call: from cache: saved reply used, no call in this run.
- SUB-109 (scanned PDF app, csv schedule, email, no loss runs): extracted name Llano Dry Goods Wholesale LLC. Misses: premises, conflict. Flagged: none. Call: from cache: saved reply used, no call in this run.
- SUB-110 (typed PDF app, typed loss run, csv schedule, email): extracted name Casa Mesquite Cantina LLC. Misses: premises, status. Flagged: none. Call: from cache: saved reply used, no call in this run.
- SUB-111 (scanned PDF app, typed loss run, csv schedule, email): extracted name Lone Oak Smokehouse & Bar LLC. Misses: sales, premises, conflict. Flagged: none. Call: from cache: saved reply used, no call in this run.
- SUB-112 (Spanish typed PDF app, Spanish agent letter, email): extracted name Hernandez Plumbing & Drain LLC. Misses: operations, premises. Flagged: none. Call: from cache: saved reply used, no call in this run.
- SUB-113 (typed PDF app, typed loss run, csv schedule, email): extracted name Mesa Court Apartments LLC. Misses: premises. Flagged: conflict. Call: from cache: saved reply used, no call in this run.
- SUB-114 (typed PDF app, csv schedule, no-known-loss letter, email): extracted name Bayfront Villas LP. Misses: operations, premises. Flagged: none. Call: from cache: saved reply used, no call in this run.
- SUB-115 (typed PDF app, xlsx schedule, no-known-loss letter, email): extracted name Cedar Gate Dental Partners LLC. Misses: year_built, premises, conflict. Flagged: none. Call: from cache: saved reply used, no call in this run.
- SUB-116 (scanned PDF app, typed loss run, csv schedule, email): extracted name Tri-County Air & Heat LLC. Misses: premises, status. Flagged: none. Call: from cache: saved reply used, no call in this run.
- SUB-117 (email only): extracted name Brazos Cabinets. Misses: effective_date, year_built, premises, tiv. Flagged: none. Call: from cache: saved reply used, no call in this run.
- SUB-118 (sideways scanned PDF app, csv schedule, email, no loss runs): extracted name Ironwood Physical Therapy PLLC. Misses: premises. Flagged: none. Call: from cache: saved reply used, no call in this run.
- SUB-119 (upside-down scanned PDF app, typed loss run, csv schedule, email): extracted name Pastor Norte Taqueria LLC. Misses: sales, premises, conflict. Flagged: none. Call: from cache: saved reply used, no call in this run.
- SUB-120 (duplicate resubmission of SUB-107): extracted name Juniper Ridge Bookkeeping LLC. Misses: premises, status. Flagged: none. Call: from cache: saved reply used, no call in this run.
- SUB-121 (typed PDF app, csv schedule, no-known-loss letter, email): extracted name Gulf Coast Pool Supply Wholesale LLC. Misses: premises, conflict. Flagged: none. Call: from cache: saved reply used, no call in this run.
- SUB-122 (typed PDF app, typed partial loss run, xlsx schedule, email): extracted name Brewhouse Lane Pizza & Tap Co LLC. Misses: premises. Flagged: none. Call: from cache: saved reply used, no call in this run.
- SUB-123 (Spanish scanned PDF app, csv schedule, Spanish agent letter, email): extracted name Tienda Luna Azul LLC. Misses: premises. Flagged: none. Call: from cache: saved reply used, no call in this run.
- SUB-124 (scanned PDF app, typed loss run, xlsx 2-location schedule, email): extracted name Brisket & Co Group LLC. Misses: operations, year_built, premises, conflict. Flagged: none. Call: from cache: saved reply used, no call in this run.
- SUB-125 (typed PDF app, typed loss run, xlsx schedule, email): extracted name Ledger & Lane Tax Services LLC. Misses: premises, conflict. Flagged: none. Call: from cache: saved reply used, no call in this run.
- SUB-126 (typed PDF app, no-known-loss letter, email, no schedule): extracted name Red Mesa Screen Print Co LLC. Misses: premises. Flagged: none. Call: from cache: saved reply used, no call in this run.

## Silent error rate and automation rate (D-084)

silent error: a value is shown, it is wrong, and it is not flagged needs review or in an open conflict; automation: the value is correct and not flagged. An empty field counts as flagged (it shows as missing). Rates are over scored field values; files whose call failed are left out and counted apart (D-084).

Files with a failed call, not in the rates: 0.

| Field | Scored | Silent errors | Silent error rate | Automated | Automation rate |
|---|---|---|---|---|---|
| named_insured | 20 | 0 | 0.0 | 19 | 0.95 |
| premises | 20 | 16 | 0.8 | 0 | 0.0 |
| effective_date | 20 | 0 | 0.0 | 9 | 0.45 |
| operations | 20 | 2 | 0.1 | 16 | 0.8 |
| sales | 20 | 0 | 0.0 | 12 | 0.6 |
| tiv | 20 | 0 | 0.0 | 10 | 0.5 |
| construction | 20 | 0 | 0.0 | 19 | 0.95 |
| year_built | 20 | 0 | 0.0 | 10 | 0.5 |
| loss_runs | 20 | 0 | 0.0 | 0 | 0.0 |
| overall | 180 | 18 | 0.1 | 95 | 0.528 |

## Status safety and status automation (D-089 item 6, B-325 rule; computed here, the frozen scorer is unchanged)

- False completes: **0** (none). Critical: must be 0.
- Status automation: 0 of 4 gold-complete files shown as plain "complete".
- Statuses: {"SUB-107": "complete — review pending", "SUB-108": "incomplete", "SUB-109": "incomplete", "SUB-110": "complete — review pending", "SUB-111": "complete — review pending", "SUB-112": "incomplete", "SUB-113": "incomplete", "SUB-114": "incomplete", "SUB-115": "incomplete", "SUB-116": "complete — review pending", "SUB-117": "incomplete", "SUB-118": "incomplete", "SUB-119": "incomplete", "SUB-120": "complete — review pending", "SUB-121": "incomplete", "SUB-122": "incomplete", "SUB-123": "incomplete", "SUB-124": "incomplete", "SUB-125": "complete — review pending", "SUB-126": "incomplete"}

- Run: {"model": "qwen/qwen3.8-27b", "stopped_at": null, "files_run": 20, "seconds_per_file": 1.8, "tokens": {"hosts": ["api.groq.com"], "model_calls": 0, "from_cache": 20, "tokens": 0, "failed_attempts": {"rate_limit_429": 0, "timeout": 0, "other": 0, "reply_not_usable": 0}}, "failed_attempts": {"rate_limit_429": 0, "timeout": 0, "other": 0, "reply_not_usable": 0}}
