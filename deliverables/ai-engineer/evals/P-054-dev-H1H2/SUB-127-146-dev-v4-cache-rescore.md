# Extraction score (scorer v4) — SUB-127 through SUB-146

- Author: @ai-engineer-assistant
- 9 of 9 extracted fields scored; claims not read; loss runs = date only.
- Commit: 3557e4a6e91831dbde0b3177ad1e5e2a3be22739 (last pipeline commit 3557e4a6e91831dbde0b3177ad1e5e2a3be22739).
- Scored with this file unchanged after the gold answers were written. A development re-check is not a hold-out.
- A null that matches a missing gold line is not_credited. It is not a correct answer.
- Correctly flagged for human means the documents disagree and the AI stored both sides without picking one. It is not a hit and not a miss.
- Synthetic. Not a production approval.

## Per-field

| Field | Hit | Hit (needs review) | Miss | Not credited | Correctly flagged for human | Call failed |
|---|---|---|---|---|---|---|
| named_insured | 20 | 0 | 0 | 0 | 0 | 0 |
| premises | 17 | 0 | 3 | 0 | 0 | 0 |
| effective_date | 18 | 0 | 2 | 0 | 0 | 0 |
| operations | 19 | 0 | 1 | 0 | 0 | 0 |
| sales | 18 | 0 | 2 | 0 | 0 | 0 |
| tiv | 17 | 0 | 3 | 0 | 0 | 0 |
| construction | 17 | 0 | 3 | 0 | 0 | 0 |
| year_built | 16 | 0 | 4 | 0 | 0 | 0 |
| loss_runs | 8 | 0 | 0 | 12 | 0 | 0 |
| conflict | 16 | 0 | 3 | 0 | 1 | 0 |
| status | 18 | 0 | 2 | 0 | 0 | 0 |
| route | 16 | 0 | 4 | 0 | 0 | 0 |

## Status safety and status automation (B-325)

- False completes (plain "complete" on a gold-incomplete file): **0** (none). Critical: must be 0.
- Status automation: 4 of 6 gold-complete files shown as plain "complete". "complete — review pending" is safe but not automated.
- Failed calls, left out of both: 0.

## T-027 route gate (D-096, D-097)

- Unsafe routes (a carrier, held or not, where gold says senior_referral or no_match): **0** (none). Must be 0.
- Route accuracy: 16/20 (0 files with no route mark). Must be at least 18/20.
- Route gate: **FAIL**.

## Per submission

- SUB-127 (typed md app, typed text-layer PDF Carrier A loss run, csv schedule, email): extracted name Cedar Bend Financial Advisors LLC. Misses: route. Flagged: none. Call: from cache: saved reply used, no call in this run. Retries: 0.
- SUB-128 (typed md app, typed md Carrier A no-claims loss run, csv schedule, email): extracted name Prairie Hill Candle & Gift Co LLC. Misses: route. Flagged: none. Call: from cache: saved reply used, no call in this run. Retries: 0.
- SUB-129 (scanned JPG app, image-only PDF Carrier A loss run, csv schedule, email contradicting the app on sales): extracted name Brazos Electrical Supply Inc. Misses: construction, premises, conflict, route. Flagged: none. Call: from cache: saved reply used, no call in this run. Retries: 0.
- SUB-130 (typed md app, typed text-layer PDF Carrier B loss run, csv schedule, email): extracted name Harbor Lane Cafe LLC. Misses: none. Flagged: none. Call: from cache: saved reply used, no call in this run. Retries: 0.
- SUB-131 (typed md app, JPG scan of Carrier B loss run, csv schedule with a different sq ft, email): extracted name Ruiz & Pope Plumbing Co LLC. Misses: none. Flagged: conflict. Call: from cache: saved reply used, no call in this run. Retries: 0.
- SUB-132 (typed md app, typed md Carrier B loss run, csv schedule, email): extracted name Sweet Tea & Biscuit Co LLC. Misses: status. Flagged: none. Call: from cache: saved reply used, no call in this run. Retries: 0.
- SUB-133 (typed md app, rotated JPG scan of Carrier C loss run, csv schedule, email): extracted name Canyon Oaks Apartments LP. Misses: status. Flagged: none. Call: from cache: saved reply used, no call in this run. Retries: 0.
- SUB-134 (typed md app, typed text-layer PDF Carrier C loss run, csv schedule, email): extracted name Bayou Glass & Mirror Works LLC. Misses: none. Flagged: none. Call: from cache: saved reply used, no call in this run. Retries: 0.
- SUB-135 (typed md app, English owner letter, csv schedule, email): extracted name Lone Oak Thrift & Books LLC. Misses: route. Flagged: none. Call: from cache: saved reply used, no call in this run. Retries: 0.
- SUB-136 (typed md app, Spanish owner letter, csv schedule, email): extracted name Taqueria La Esquina LLC. Misses: none. Flagged: none. Call: from cache: saved reply used, no call in this run. Retries: 0.
- SUB-137 (typed md app, owner-typed note with a copied carrier header, csv schedule, email): extracted name Northline Heating & Air LLC. Misses: none. Flagged: none. Call: from cache: saved reply used, no call in this run. Retries: 0.
- SUB-138 (typed md app, producer agency summary (not a carrier run), csv schedule, email): extracted name Pecan Grove Feed & Seed Co LLC. Misses: none. Flagged: none. Call: from cache: saved reply used, no call in this run. Retries: 0.
- SUB-139 (typed md app, carrier five-year summary in its own layout, csv schedule, email): extracted name Azalea Court Apartments LLC. Misses: none. Flagged: none. Call: from cache: saved reply used, no call in this run. Retries: 0.
- SUB-140 (typed md app, Carrier B layout missing its valuation line, csv 2-location schedule, email): extracted name Smokehouse Row BBQ Co LLC. Misses: year_built, conflict. Flagged: none. Call: from cache: saved reply used, no call in this run. Retries: 0.
- SUB-141 (typed md app, csv schedule, email, no loss run): extracted name Ember and Oak Kitchen & Bar LLC. Misses: none. Flagged: none. Call: from cache: saved reply used, no call in this run. Retries: 0.
- SUB-142 (email only): extracted name Alamo Roof & Gutter Pros LLC. Misses: effective_date, sales, construction, year_built, premises, tiv. Flagged: none. Call: from cache: saved reply used, no call in this run. Retries: 0.
- SUB-143 (Spanish email only): extracted name Sol y Luna Boutique. Misses: effective_date, operations, sales, construction, year_built, tiv. Flagged: none. Call: from cache: saved reply used, no call in this run. Retries: 0.
- SUB-144 (scanned JPG app (2 locations), csv schedule, email, no loss run): extracted name Westgate Pediatric Therapy PLLC. Misses: year_built, premises, tiv, conflict. Flagged: none. Call: from cache: saved reply used, no call in this run. Retries: 0.
- SUB-145 (typed md app, 3-location csv schedule, email, no loss run): extracted name Lakeview Gardens Partners LP. Misses: none. Flagged: none. Call: from cache: saved reply used, no call in this run. Retries: 0.
- SUB-146 (duplicate: typed md app resent, csv schedule, email, no loss run): extracted name Ember and Oak Kitchen & Bar LLC. Misses: none. Flagged: none. Call: from cache: saved reply used, no call in this run. Retries: 0.
