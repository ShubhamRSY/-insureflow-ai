# Extraction score (scorer v4) — SUB-154 through SUB-173

- Author: @ai-engineer-assistant
- 9 of 9 extracted fields scored; claims not read; loss runs = date only.
- Commit: 2c6b2d93865ba7bfef57c81aa60c00047aba8d36 (last pipeline commit 3557e4a6e91831dbde0b3177ad1e5e2a3be22739).
- Scored with this file unchanged after the gold answers were written. A development re-check is not a hold-out.
- A null that matches a missing gold line is not_credited. It is not a correct answer.
- Correctly flagged for human means the documents disagree and the AI stored both sides without picking one. It is not a hit and not a miss.
- Synthetic. Not a production approval.

## Per-field

| Field | Hit | Hit (needs review) | Miss | Not credited | Correctly flagged for human | Call failed |
|---|---|---|---|---|---|---|
| named_insured | 19 | 0 | 1 | 0 | 0 | 0 |
| premises | 16 | 0 | 4 | 0 | 0 | 0 |
| effective_date | 17 | 0 | 3 | 0 | 0 | 0 |
| operations | 7 | 0 | 13 | 0 | 0 | 0 |
| sales | 17 | 0 | 3 | 0 | 0 | 0 |
| tiv | 17 | 0 | 3 | 0 | 0 | 0 |
| construction | 17 | 0 | 3 | 0 | 0 | 0 |
| year_built | 16 | 0 | 4 | 0 | 0 | 0 |
| loss_runs | 5 | 0 | 4 | 11 | 0 | 0 |
| conflict | 17 | 0 | 3 | 0 | 0 | 0 |
| status | 15 | 0 | 4 | 1 | 0 | 0 |
| route | 16 | 0 | 4 | 0 | 0 | 0 |

## Status safety and status automation (B-325)

- False completes (plain "complete" on a gold-incomplete file): **0** (none). Critical: must be 0.
- Status automation: 4 of 8 gold-complete files shown as plain "complete". "complete — review pending" is safe but not automated.
- Failed calls, left out of both: 0.

## T-027 route gate (D-096, D-097)

- Unsafe routes (a carrier, held or not, where gold says senior_referral or no_match): **0** (none). Must be 0.
- Route accuracy: 16/20 (0 files with no route mark). Must be at least 18/20.
- Route gate: **FAIL**.

## Per submission

- SUB-154 (typed md app, typed text-layer PDF Carrier A loss run, csv schedule, email): extracted name Hollis & Varga Tax Advisory LLC. Misses: none. Flagged: none. Call: called: reply used. Retries: 1 (rate_limit_429).
- SUB-155 (typed md app, typed .md Carrier A loss run with no-claims line, csv schedule, email): extracted name Plains Home & Candle Co LLC. Misses: none. Flagged: none. Call: called: reply used. Retries: 1 (rate_limit_429).
- SUB-156 (typed md app, typed text-layer PDF Carrier B loss run, csv schedule, email): extracted name Sunny Side Grill LLC. Misses: operations, conflict. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-157 (typed md app, typed .md Carrier B loss run, csv schedule, email): extracted name Rio Bend Kitchen & Bar LLC. Misses: operations. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-158 (typed md app, typed text-layer PDF Carrier C loss run, csv schedule, email): extracted name Garden Row Apartments LLC. Misses: operations, status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-159 (typed md app, JPG greyscale scan of Carrier B loss run, csv schedule, email): extracted name Crumb & Cup Bakery Cafe LLC. Misses: operations, loss_runs, status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-160 (typed md app, JPG colour scan of Carrier C loss run (rotated), csv schedule, email): extracted name Alder Park Apartments LLC. Misses: operations, loss_runs, status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-161 (typed md app, image-only PDF Carrier A loss run (scan of a printout), csv schedule, email): extracted name Gulf Plains Hardware Wholesale LLC. Misses: loss_runs, status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-162 (typed md app, owner no-claims letter, csv schedule, email): extracted name Ellison Bookkeeping & Payroll PLLC. Misses: none. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-163 (Spanish md app, Spanish owner letter, csv schedule, Spanish email): extracted name Cenaduria Los Abuelos LLC. Misses: operations, route. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-164 (typed md app, forwarded applicant note with copied carrier header and '>' prefix (not a carrier run), csv schedule, email): extracted name Gulf Shore Roofing LLC. Misses: loss_runs. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-165 (typed md app, producer agency summary (not a carrier run), csv schedule, email): extracted name Boom Town Fireworks LLC. Misses: operations. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-166 (typed md app, JPG scan (Carrier B header plus insured's typed note), csv schedule, email): extracted name Pinecrest Office Holdings LLC. Misses: none. Flagged: none. Call: called: reply used. Retries: 1 (rate_limit_429).
- SUB-167 (typed md app (sprinklers blank), typed .md Carrier C loss run with no valued line, csv schedule (sprinklers blank), email): extracted name Mesquite Court Apartments LP. Misses: operations, route. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-168 (email only): extracted name Cobble Creek Holdings LLC. Misses: effective_date, sales, construction, year_built, premises, tiv. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-169 (Spanish email only): extracted name Lavanderia Burbuja. Misses: effective_date, operations, sales, construction, year_built, premises, tiv, route. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-170 (scanned JPG app (2 locations), csv 2-location schedule, email, no loss run): extracted name null. Misses: named_insured, effective_date, operations, sales, construction, year_built, premises, tiv, conflict, route. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-171 (duplicate: typed md app resent, csv schedule, email, no loss run): extracted name Rio Bend Kitchen & Bar LLC. Misses: operations. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-172 (typed md app, 3-location csv schedule, email, no loss run): extracted name Cypress Pointe Apartments LLC. Misses: operations, year_built, premises, conflict. Flagged: none. Call: called: reply used. Retries: 1 (rate_limit_429).
- SUB-173 (typed md app, csv schedule, email, no loss run): extracted name Los Primos Taqueria LLC. Misses: operations. Flagged: none. Call: called: reply used. Retries: 0.

## Silent error rate and automation rate (D-084)

silent error: a value is shown, it is wrong, and it is not flagged needs review or in an open conflict; automation: the value is correct and not flagged. An empty field counts as flagged (it shows as missing). Rates are over scored field values; files whose call failed are left out and counted apart (D-084).

Files with a failed call, not in the rates: 0.

| Field | Scored | Silent errors | Silent error rate | Automated | Automation rate |
|---|---|---|---|---|---|
| named_insured | 20 | 0 | 0.0 | 19 | 0.95 |
| premises | 20 | 0 | 0.0 | 16 | 0.8 |
| effective_date | 20 | 0 | 0.0 | 17 | 0.85 |
| operations | 20 | 6 | 0.3 | 6 | 0.3 |
| sales | 20 | 0 | 0.0 | 17 | 0.85 |
| tiv | 20 | 0 | 0.0 | 17 | 0.85 |
| construction | 20 | 0 | 0.0 | 16 | 0.8 |
| year_built | 20 | 0 | 0.0 | 16 | 0.8 |
| loss_runs | 20 | 0 | 0.0 | 5 | 0.25 |
| overall | 180 | 6 | 0.033 | 129 | 0.717 |
