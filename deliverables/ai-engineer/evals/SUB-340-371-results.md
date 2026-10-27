# T-119 results (SUB-340 to SUB-371, scorer v11, run id 20261024T000318-70195)

Source: `SUB-340-371-holdout-v11.json/.md` (scored once), run record and mismatch list beside it. Code b6a35b7 line, PROMPT_VERSION 759b3e6bc9b2, qwen/qwen3.8-27b on Groq. Synthetic. Not a production approval.

## Gates and targets

| Measure | Result | Target | Status |
|---|---|---|---|
| Leakage (out-of-scope files with extracted values) | 0 of 12 | 0 | met |
| Detection recall, overall | 12/12 = 100% | 100% | met |
| - criterion 1 scanned application | 4/4 | 100% | met |
| - criterion 2 multiple locations | 5/5 | 100% | met |
| - criterion 3 non-English | 4/4 | 100% | met |
| - criterion 4 application not identified | 3/3 | 100% | met |
| In-scope files wrongly sent to manual intake | 0 of 20 | at most 2 | met |
| False completes | 0 | 0 | met |
| Unsafe routes | 0 | 0 | met |
| Route accuracy | 20/20 | at least 18/20 | met |
| call_failed files | 0 | (none set) | none |

Reason accuracy (reported, no target): 11/12 manual-intake cards list every gold criterion; SUB-371 (gold criteria 2 and 4) lists only not_identified.

## Route gate, named files
- Route gate: PASS (0 unsafe, 20/20).
- Direct Carrier A files: SUB-340, 341, 342, 343 gold carrier_a, route used carrier_a, 4/4 hit. Their status is "complete — review pending" and the status mark is a miss on each (gold complete).
- SUB-352 (pub plus office, gold senior_referral): route used senior_referral, hit. Operations and status marks on this file are misses.
- Other routes: senior_referral 12/12, no_match 4/4 (SUB-353, 354, 355, 358).

## Every field against the 18/20 floor (20 in-scope files)

| Field | Hit | Miss | Not credited | Flagged | Floor 18/20 |
|---|---|---|---|---|---|
| named_insured | 20 | 0 | 0 | 0 | met |
| premises | 20 | 0 | 0 | 0 | met |
| effective_date | 20 | 0 | 0 | 0 | met |
| operations | 9 | 11 | 0 | 0 | not met |
| sales | 20 | 0 | 0 | 0 | met |
| tiv | 20 | 0 | 0 | 0 | met |
| construction | 20 | 0 | 0 | 0 | met |
| year_built | 20 | 0 | 0 | 0 | met |
| loss_runs (date only) | 20 | 0 | 0 | 0 | met |

Other marks: status 9 hit / 11 miss; route 20/0; conflict below.

## Operations: omitted "no cooking" slots, listed apart (D-127)
Under v11 an answer that omits the "no cooking" slot where gold says no cooking is a miss. Gold has "no cooking" on 14 in-scope files. Of those 14, the answer omits the slot on 9 files: SUB-340, 341, 342, 343, 344, 346, 347, 355, 359. It carries the slot on 5 (SUB-345, 350, 353, 354, 358).
- Operations misses (11) split by what the checklist found missing: only "no cooking": SUB-340, 341, 342, 343, 346, 347, 359 (7); "no cooking" plus a business_type slot: SUB-344 (contractor), SUB-355 (hookah_adult, lounge_nightclub) (2); business_type slot only, no cooking omission: SUB-350 (wholesale), SUB-352 (bar_pub, office) (2).
- Operations hits if the 7 "only no cooking" misses were not misses: not computed by the scorer; shown here for the reader only, the score above stands.
- Operations answers are flagged for review on 10 of the 11 misses; SUB-350 is not flagged (the silent error below).

## Conflict (D-128, B-467)
Scorer marks as written: hit 15, flagged 2, miss 3 (of 20). The 3 misses are SUB-345, 348, 349.
- Excluded by hand per D-128 and reported separately: SUB-348 (gold cooking: none vs stove top and flat grill, miss) and SUB-349 (gold cooking: none vs yes and griddle, miss). v11 cannot measure these two marks.
- Conflict rate without them (18 files): 15 hit (gold "none", no open conflict), 2 correctly flagged, 1 miss. Of the 3 measurable planted conflicts: 2 flagged, 1 missed (67%). No false conflict on a gold-none file (0 of 15).
- Per file, planted conflict files:

| File | Planted conflict | Result |
|---|---|---|
| SUB-344 | square footage 3200 (application) vs 2450 (schedule) | flagged (open conflict square_feet 3200 vs 2450; the 2450 source stored as email.md) |
| SUB-345 | sales 1,240,000 (application) vs 1,420,000 (email "about $1.42 million") | miss (no open conflict) |
| SUB-346 | suites 8 (application) vs 9 (email) | flagged (open conflict suite_count 9 vs 8) |
| SUB-348 | cooking none vs stove top and flat grill | miss, excluded (D-128) |
| SUB-349 | cooking none vs yes and griddle | miss, excluded (D-128) |

- Gold-none files (15): SUB-340, 341, 342, 343, 347, 350 to 359: all hit.
- Target: none set for the conflict rate; no met / not met call.

## Loss runs, per document
All 20 hit, 0 not_credited, 0 miss.
- Carrier A (SUB-340, 341, 342, 343, 346, 349, 355, 358): 8/8 hit.
- Carrier B (SUB-344, 348, 353, 357): 4/4 hit.
- Carrier C (SUB-345, 347, 351, 352, 354, 356): 6/6 hit.
- No loss run (SUB-350 email only, SUB-359 none): 2/2 hit (gold expects no date).
- Floor 18/20: met.

## Silent error rate and automation rate (D-084)
- Silent errors: 1 of 180 = 0.006 (SUB-350 operations: value shown, missing the business_type=wholesale slot, not flagged for review). There is no stated target; the earlier hold-out had 0.
- Automation rate: 162 of 180 = 0.90. By field: named_insured, premises, effective_date, tiv, construction, year_built 1.0; sales 0.95; loss_runs 0.90; operations 0.25.
- Status automation: 2 of 13 gold-complete files shown as plain "complete" (SUB-351, 356); 11 are "complete — review pending" or "incomplete" (safe direction).

## Retries and failed calls (RUN-RULES.md)
- Total retries: 1 (SUB-340, HTTP 429 on output tokens per minute, waited 3.0 s, then reply used; attempts 1 in `score_retry`). Every other file: 0 retries. timeout 0, other 0, reply_not_usable 0.
- call_failed files: 0.
- from_cache: 0; model calls 20 (the 12 out-of-scope files stopped before any call).

## Cost (token log of this run)
- 20 calls plus 1 retry row: 22,258 prompt + 13,057 completion = 35,315 tokens (1,766 per call).
- Paid at Groq: $0 (free tier, D-011).
- Same tokens at the repo's paid list prices (Gemini prices, not qwen's, D-038 item 5): Flash ($0.30 in, $2.50 out) $0.0393; Pro ($1.25 in, $10.00 out) $0.1584.
- Per file over all 32: Flash $0.0012, Pro $0.0049. Per in-scope call: Flash $0.0020, Pro $0.0079.

## Status marks
9 hit, 11 miss. False completes 0. Misses: SUB-340, 341, 342, 343, 347, 352, 354, 355, 358 ("complete — review pending" where gold complete) and SUB-353, 357 ("incomplete" where gold complete).
