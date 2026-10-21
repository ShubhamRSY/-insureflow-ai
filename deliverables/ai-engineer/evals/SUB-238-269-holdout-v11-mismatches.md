# T-117 mismatches, as-is (SUB-238 to SUB-269, scorer v11, D-119)

Recorded after the single official run on 2026-10-21 (run id `20261021T112723-44537`). Nothing was fixed and nothing was re-scored. Source: `deliverables/ai-engineer/evals/SUB-238-269-holdout-v11.json` and the saved replies in `underwriting_pipeline/cache/T-117-live/`.

Every field mark that is not a plain `hit` is listed below, as the pipeline stored it. `source` is the file the stored value came from; a derived mark (`conflict`, `status`, `route`) has no single source and is shown `—`. Gold is copied from the frozen gold card line.

## Gate failures

### F1 — operations: 13 hits, 7 misses (floor 18/20 not met)
7 misses: SUB-239, 244, 246, 248, 250, 254, 257. The stored free-text description is right in most cases but is not the gold `business_type=` slot set, so the v11 checklist marks it a miss. 0 silent errors: every miss is a field the run flags for review.

### F2 — loss_runs: 16 hits, 4 not_credited (floor 18/20 not met)
4 not_credited: SUB-238, 245, 251, 252. A Carrier C loss run is found but the pipeline cannot read a valued-as-of date from it, so it stores null with `loss run found but no valued-as-of date` and asks the producer. Gold has the date. A null is not a correct answer.

## Route miss (not unsafe)

| File | Gold route | Route used | Note |
|---|---|---|---|
| SUB-252 | no_match (R1) | senior_referral | Gold says R1 no_match with an open office-suite count conflict. Pipeline says senior_referral (R2, pub/office suites). Neither is a carrier route, so it is not unsafe. This is B-448. |

## Every non-hit, as-is (24)

| File | Field | Mark | Source | Answer (as stored) | Gold |
|---|---|---|---|---|---|
| SUB-239 | operations | miss | application.md | Cocktail lounge, full liquor, live music Fri and Sat, closes around midnight, countertop oven, frozen pizza only | business_type=lounge_nightclub; business_type=bar_pub; full liquor; live music Fri and Sat |
| SUB-244 | operations | miss | application.md | Residential and light commercial roofing, tear-off and install; 9 trucks, yard and a small office | business_type=contractor |
| SUB-246 | operations | miss | application.md | Lessor of office building, 14 suites, professional tenants, no tenant food service | business_type=office; no cooking |
| SUB-248 | operations | miss | application.md | Lessor of professional office building, six suites | business_type=office; no cooking |
| SUB-250 | operations | miss | application.md | Tax preparation office (second floor); cell phone repair and retail accessories (ground floor) | business_type=office; business_type=retail; no cooking |
| SUB-254 | operations | miss | application.md | Wholesale electrical supplies to contractors, counter pickup | business_type=wholesale; no cooking |
| SUB-257 | operations | miss | email.md | Thrift retail, used clothing and household goods, donations in the back | business_type=retail; no cooking |
| SUB-238 | loss_runs | not_credited | loss-runs.md | null (reason: loss run found but no valued-as-of date; ask the producer for a dated carrier loss run) | Carrier C format, 2 policy terms 2024-03-01 to 2026-03-01, valued as of 2026-06-12, one claim (2025-08-16 liability, patron injury, $18000 paid, open reserve $0). Recognised Carrier C layout. |
| SUB-245 | loss_runs | not_credited | loss-runs.md | null (reason: loss run found but no valued-as-of date; ask the producer for a dated carrier loss run) | Carrier C format, 2 policy terms 2024-08-01 to 2026-08-01, valued as of 2026-07-21, one claim (2025-12-04 water damage unit 6, $9400 paid, open reserve $0). Recognised Carrier C layout. |
| SUB-251 | loss_runs | not_credited | loss-runs.md | null (reason: loss run found but no valued-as-of date; ask the producer for a dated carrier loss run) | Carrier C format, 1 policy term 2025-07-01 to 2026-07-01, valued as of 2026-06-20, no claims. Recognised Carrier C layout. |
| SUB-252 | loss_runs | not_credited | loss-runs.md | null (reason: loss run found but no valued-as-of date; ask the producer for a dated carrier loss run) | Carrier C format, 1 policy term 2025-03-03 to 2026-03-03, valued as of 2026-03-03, one claim (2025-10-30 liquor liability, pub patron, $22000 paid, open reserve $0). Recognised Carrier C layout. |
| SUB-249 | conflict | miss | — | no open conflict | square footage: 2800 (application) vs 3150 (schedule, appraisal 2025; the email says the application holds the old number) |
| SUB-252 | conflict | miss | — | no open conflict | office suites: 2 (application) vs 3 (email; the third is a storage room) |
| SUB-257 | conflict | miss | — | no open conflict | sales: 412000 (application) vs 540000 (email, 'about 540k'; the accountant used the tax form number) |
| SUB-243 | status | miss | — | complete — review pending | complete |
| SUB-245 | status | miss | — | incomplete | complete |
| SUB-246 | status | miss | — | complete — review pending | complete |
| SUB-247 | status | miss | — | incomplete | complete |
| SUB-250 | status | miss | — | complete — review pending | complete |
| SUB-251 | status | miss | — | incomplete | complete |
| SUB-253 | status | miss | — | complete — review pending | complete |
| SUB-255 | status | miss | — | complete — review pending | complete |
| SUB-256 | status | miss | — | incomplete | complete |
| SUB-252 | route | miss | — | senior_referral | no_match (R1; AG:45-50) — hold: open conflict (office suite count) |

## Silent errors (0 of 180 = 0.0)
No value is shown, wrong, and unflagged. Every operations miss is a review field; every loss_runs miss is a null with a reason.

## Not mismatches (recorded for completeness)
- Leakage: 0 of 12. Detection recall: 12/12 (criterion 1 4/4, criterion 2 5/5, criterion 3 4/4, criterion 4 2/2). False manual intake: 0 of 20.
- False completes: 0. Unsafe routes: 0. call_failed: 0. Retries: 0.
