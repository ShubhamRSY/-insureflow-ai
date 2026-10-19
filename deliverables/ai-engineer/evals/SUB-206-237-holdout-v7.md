# Extraction score (scorer v7) — SUB-206 through SUB-237

- Author: @ai-engineer-assistant
- 9 of 9 extracted fields scored; claims not read; loss runs = date only.
- Commit: 5d51a9b2e8cf30725058cde726cf6c6ba4291537 (last pipeline commit 457f1bf5784cd8a0c95af72724ca9341be3ba207).
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
| operations | 9 | 0 | 11 | 0 | 0 | 0 |
| sales | 20 | 0 | 0 | 0 | 0 | 0 |
| tiv | 19 | 0 | 1 | 0 | 0 | 0 |
| construction | 20 | 0 | 0 | 0 | 0 | 0 |
| year_built | 20 | 0 | 0 | 0 | 0 | 0 |
| loss_runs | 5 | 0 | 9 | 6 | 0 | 0 |
| conflict | 10 | 0 | 10 | 0 | 0 | 0 |
| status | 15 | 0 | 5 | 0 | 0 | 0 |
| route | 18 | 0 | 2 | 0 | 0 | 0 |

## Status safety and status automation (B-325)

- False completes (plain "complete" on a gold-incomplete file): **0** (none). Critical: must be 0.
- Status automation: 3 of 8 gold-complete files shown as plain "complete". "complete — review pending" is safe but not automated.
- Failed calls, left out of both: 0.
- Operations scored by checklist (v5): 20 of 20 files; the rest by the v4 word rule.

## T-027 route gate (D-096, D-097)

- Unsafe routes (a carrier, held or not, where gold says senior_referral or no_match): **0** (none). Must be 0.
- Route accuracy: 18/20 (0 files with no route mark). Must be at least 18/20.
- Route hits over all 20 in-scope gold files (none left out): 18/20. Gate rule unchanged.
- Route gate: **PASS**.

## P-055 scope gate (D-108, P-057), apart from the T-027 gate

- Files: 12 out of scope, 20 in scope (gold Scope lines). Out-of-scope files are not field-scored.
- Leakage (hard gate): **1** of 12 (SUB-233). Must be 0.
  - SUB-233: field shown, provisional route, automated draft, send enabled
- Detection recall, overall: 11/12 (missed: SUB-233). Must be 100%.
  - criterion 1 scanned application: 4/4
  - criterion 2 multiple locations: 4/5
  - criterion 3 non-English: 4/4
  - criterion 4 application not identified: 2/2
- Reason accuracy (reported): 11/11 manual-intake cards list every gold criterion.
- False manual intake: 0 of 20 in-scope files (none). At most 2; within the ceiling, they are left out of the in-scope counts above.
- P-055 scope gate: **FAIL**.

## Per submission

- SUB-226 (out of scope, criteria 4): manual intake: yes. Reason codes: not_identified. Leaks: none.
- SUB-227 (out of scope, criteria 4): manual intake: yes. Reason codes: not_identified. Leaks: none.
- SUB-228 (out of scope, criteria 1): manual intake: yes. Reason codes: scanned_application. Leaks: none.
- SUB-229 (out of scope, criteria 1): manual intake: yes. Reason codes: scanned_application. Leaks: none.
- SUB-230 (out of scope, criteria 1): manual intake: yes. Reason codes: scanned_application. Leaks: none.
- SUB-231 (out of scope, criteria 1, 2): manual intake: yes. Reason codes: scanned_application, multiple_locations. Leaks: none.
- SUB-232 (out of scope, criteria 2): manual intake: yes. Reason codes: multiple_locations. Leaks: none.
- SUB-233 (out of scope, criteria 2): manual intake: NO. Reason codes: none. Leaks: field shown, provisional route, automated draft, send enabled.
- SUB-234 (out of scope, criteria 3): manual intake: yes. Reason codes: non_english. Leaks: none.
- SUB-235 (out of scope, criteria 3): manual intake: yes. Reason codes: non_english. Leaks: none.
- SUB-236 (out of scope, criteria 2, 3): manual intake: yes. Reason codes: multiple_locations, non_english. Leaks: none.
- SUB-237 (out of scope, criteria 2, 3): manual intake: yes. Reason codes: multiple_locations, non_english. Leaks: none.
- SUB-206 (typed md app, typed md loss run (Carrier A), schedule csv, email): extracted name Bluebonnet Ridge Office Park LLC. Misses: operations, loss_runs, status, route. Flagged: none. Call: called: reply used. Retries: 4 (rate_limit_429, rate_limit_429, rate_limit_429, rate_limit_429).
- SUB-207 (typed pdf app (text layer), typed md loss run (Carrier B), email): extracted name Pecan Street Sandwich Co. LLC. Misses: operations, loss_runs, status. Flagged: none. Call: called: reply used. Retries: 1 (rate_limit_429).
- SUB-208 (typed md app, typed md email, schedule csv; no loss run): extracted name Lone Star Craft Supply LLC. Misses: operations. Flagged: none. Call: called: reply used. Retries: 1 (rate_limit_429).
- SUB-209 (typed md app, email, scanned loss run jpg (transcribed)): extracted name Garcia & Sons Flatwork LLC. Misses: operations, conflict. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-210 (typed md app, typed md loss run (Carrier C), schedule xlsx, email): extracted name Magnolia Court Apartments LLC. Misses: loss_runs, conflict. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-211 (typed md app, email, image-only loss run pdf (transcribed)): extracted name Vaquero Smokehouse & Grill LLC. Misses: operations, conflict. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-212 (typed md app, email, no-known-loss letter): extracted name Reyes Finish Carpentry LLC. Misses: none. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-213 (typed md app, typed md loss run (Carrier A), schedule csv, email): extracted name Cedar Park Office Suites LLC. Misses: loss_runs, conflict, status, route. Flagged: none. Call: called: reply used. Retries: 1 (rate_limit_429).
- SUB-214 (typed md app, email, schedule csv; no loss run): extracted name Brazos Bend Outfitters LLC. Misses: tiv, conflict. Flagged: none. Call: called: reply used. Retries: 1 (rate_limit_429).
- SUB-215 (typed pdf app (text layer), typed md loss run (Carrier B), email): extracted name Delgado's Deli & Market LLC. Misses: operations, loss_runs, status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-216 (typed md app, email, typed md loss run (Carrier A, undated), schedule csv): extracted name Trinity Paper & Packaging LLC. Misses: conflict. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-217 (typed md app, email, scanned JPG loss run (transcribed); no schedule): extracted name Cypress Bend Apartments LLC. Misses: none. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-218 (typed md app, email, image-only PDF loss run (transcribed), schedule xlsx): extracted name Gulf Coast Cold Storage LLC. Misses: operations, loss_runs, conflict, status. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-219 (typed md app, email, typed md loss run (Carrier C, undated), schedule csv): extracted name Sabine Protective Coatings LLC. Misses: conflict. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-220 (typed md app, email, no-known-loss letter): extracted name Golden Wok Express LLC. Misses: operations. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-221 (typed PDF app (text layer), email, typed md loss run (Carrier A), schedule xlsx): extracted name Yucca Flats Retail Center LLC. Misses: operations, loss_runs, conflict. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-222 (typed md app, email, typed md loss run (Carrier C)): extracted name Neon Spur Nightclub LLC. Misses: operations, loss_runs. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-223 (typed md app, email, owner-prepared loss summary (not a carrier run), schedule csv): extracted name Llano Verde Apartments LP. Misses: none. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-224 (typed md app, email, typed md loss run (Carrier C), schedule xlsx): extracted name Cypress Bend Apartments LLC. Misses: loss_runs, conflict. Flagged: none. Call: called: reply used. Retries: 0.
- SUB-225 (typed md app, email, image-only PDF loss run (transcribed)): extracted name La Vida Loca Lounge & Bar LLC. Misses: operations. Flagged: none. Call: called: reply used. Retries: 0.

## Silent error rate and automation rate (D-084)

silent error: a value is shown, it is wrong, and it is not flagged needs review or in an open conflict; automation: the value is correct and not flagged. An empty field counts as flagged (it shows as missing). Rates are over scored field values; files whose call failed are left out and counted apart (D-084).

Files with a failed call, not in the rates: 0.

| Field | Scored | Silent errors | Silent error rate | Automated | Automation rate |
|---|---|---|---|---|---|
| named_insured | 20 | 0 | 0.0 | 20 | 1.0 |
| premises | 20 | 0 | 0.0 | 19 | 0.95 |
| effective_date | 20 | 0 | 0.0 | 20 | 1.0 |
| operations | 20 | 9 | 0.45 | 7 | 0.35 |
| sales | 20 | 0 | 0.0 | 19 | 0.95 |
| tiv | 20 | 0 | 0.0 | 19 | 0.95 |
| construction | 20 | 0 | 0.0 | 20 | 1.0 |
| year_built | 20 | 0 | 0.0 | 18 | 0.9 |
| loss_runs | 20 | 8 | 0.4 | 0 | 0.0 |
| overall | 180 | 17 | 0.094 | 142 | 0.789 |
