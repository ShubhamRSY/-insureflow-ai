# Hold-out extraction score — SUB-107 through SUB-126

- Author: @ai-engineer-assistant
- 9 of 9 extracted fields scored; claims not read; loss runs = date only.
- Commit: 178aa2808937b19f3d34ad2277ce83e17e6f2910.
- Scored by @model-risk with this file unchanged after the gold answers were written.
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
| loss_runs | 10 | 0 | 2 | 8 | 0 | 0 |
| conflict | 11 | 1 | 7 | 0 | 1 | 0 |
| status | 14 | 2 | 4 | 0 | 0 | 0 |

## Per submission

- SUB-107 (typed PDF app, typed loss run, csv schedule, email): extracted name Juniper Ridge Bookkeeping LLC. Misses: premises. Flagged: none. Call: called: reply used.
- SUB-108 (scanned PDF app, xlsx schedule, no-known-loss letter, email): extracted name Pecan Street Candle & Gift Co LLC. Misses: premises. Flagged: none. Call: called: reply used.
- SUB-109 (scanned PDF app, csv schedule, email, no loss runs): extracted name Llano Dry Goods Wholesale LLC. Misses: premises, conflict. Flagged: none. Call: called: reply used.
- SUB-110 (typed PDF app, typed loss run, csv schedule, email): extracted name Casa Mesquite Cantina LLC. Misses: premises. Flagged: none. Call: called: reply used.
- SUB-111 (scanned PDF app, typed loss run, csv schedule, email): extracted name Lone Oak Smokehouse & Bar LLC. Misses: sales, premises, conflict, status. Flagged: none. Call: called: reply used.
- SUB-112 (Spanish typed PDF app, Spanish agent letter, email): extracted name Hernandez Plumbing & Drain LLC. Misses: operations, premises, loss_runs, status. Flagged: none. Call: called: reply used.
- SUB-113 (typed PDF app, typed loss run, csv schedule, email): extracted name Mesa Court Apartments LLC. Misses: premises. Flagged: conflict. Call: called: reply used.
- SUB-114 (typed PDF app, csv schedule, no-known-loss letter, email): extracted name Bayfront Villas LP. Misses: operations, premises. Flagged: none. Call: called: reply used.
- SUB-115 (typed PDF app, xlsx schedule, no-known-loss letter, email): extracted name Cedar Gate Dental Partners LLC. Misses: year_built, premises, conflict. Flagged: none. Call: called: reply used.
- SUB-116 (scanned PDF app, typed loss run, csv schedule, email): extracted name Tri-County Air & Heat LLC. Misses: premises. Flagged: none. Call: called: reply used.
- SUB-117 (email only): extracted name Brazos Cabinets. Misses: effective_date, year_built, premises, tiv. Flagged: none. Call: called: reply used.
- SUB-118 (sideways scanned PDF app, csv schedule, email, no loss runs): extracted name Ironwood Physical Therapy PLLC. Misses: premises. Flagged: none. Call: called: reply used.
- SUB-119 (upside-down scanned PDF app, typed loss run, csv schedule, email): extracted name Pastor Norte Taqueria LLC. Misses: sales, premises, conflict. Flagged: none. Call: called: reply used.
- SUB-120 (duplicate resubmission of SUB-107): extracted name Juniper Ridge Bookkeeping LLC. Misses: premises. Flagged: none. Call: called: reply used.
- SUB-121 (typed PDF app, csv schedule, no-known-loss letter, email): extracted name Gulf Coast Pool Supply Wholesale LLC. Misses: premises, conflict. Flagged: none. Call: called: reply used.
- SUB-122 (typed PDF app, typed partial loss run, xlsx schedule, email): extracted name Brewhouse Lane Pizza & Tap Co LLC. Misses: premises. Flagged: none. Call: called: reply used.
- SUB-123 (Spanish scanned PDF app, csv schedule, Spanish agent letter, email): extracted name Tienda Luna Azul LLC. Misses: premises, loss_runs, status. Flagged: none. Call: called: reply used.
- SUB-124 (scanned PDF app, typed loss run, xlsx 2-location schedule, email): extracted name Brisket & Co Group LLC. Misses: operations, year_built, premises, conflict. Flagged: none. Call: called: reply used.
- SUB-125 (typed PDF app, typed loss run, xlsx schedule, email): extracted name Ledger & Lane Tax Services LLC. Misses: premises, conflict, status. Flagged: none. Call: called: reply used.
- SUB-126 (typed PDF app, no-known-loss letter, email, no schedule): extracted name Red Mesa Screen Print Co LLC. Misses: premises. Flagged: none. Call: called: reply used.

## Silent error rate and automation rate (D-084)

silent error: a value is shown, it is wrong, and it is not flagged needs review or in an open conflict; automation: the value is correct and not flagged. An empty field counts as flagged (it shows as missing). Rates are over scored field values; files whose call failed are left out and counted apart (D-084).

Files with a failed call, not in the rates: 0.

| Field | Scored | Silent errors | Silent error rate | Automated | Automation rate |
|---|---|---|---|---|---|
| named_insured | 20 | 0 | 0.0 | 19 | 0.95 |
| premises | 20 | 0 | 0.0 | 0 | 0.0 |
| effective_date | 20 | 0 | 0.0 | 9 | 0.45 |
| operations | 20 | 2 | 0.1 | 16 | 0.8 |
| sales | 20 | 0 | 0.0 | 12 | 0.6 |
| tiv | 20 | 0 | 0.0 | 10 | 0.5 |
| construction | 20 | 0 | 0.0 | 19 | 0.95 |
| year_built | 20 | 0 | 0.0 | 10 | 0.5 |
| loss_runs | 20 | 2 | 0.1 | 10 | 0.5 |
| overall | 180 | 4 | 0.022 | 105 | 0.583 |
