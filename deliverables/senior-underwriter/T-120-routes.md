# T-120 — Routes for in-scope submissions (SUB-450 to SUB-469)
- Owner: @senior-underwriter · Written before extraction, from the documents and carrier-match.md only (R1-R17, W1, W2, D-125). Nothing was run.
- Route column: plain rule name only (carrier_a, senior_referral, no_match). "hold" is a status, never a route (D-102). The route is the one the file takes once the hold clears.

| SUB ID | Status | route | suggested market if any | rule references | one line of reason |
|---|---|---|---|---|---|
| SUB-450 | complete | carrier_a | — | R14, R17; AG:29-31 | office tenant; "Office" only, TIV 88000, clean run |
| SUB-451 | complete | carrier_a | — | R14, R17; AG:29-31 | clothing retail storefront; allow-list words only |
| SUB-452 | complete | carrier_a | — | R14, R17; AG:29-31 | retail store, dry goods, front room; allow-list and non-occupancy words only |
| SUB-453 | complete | carrier_a | — | R14, R17; AG:29-31 | office building, suite; allow-list and non-occupancy words only |
| SUB-454 | incomplete — hold: open conflict (sq ft) | senior_referral | carrier_b | R11; AG:38, AG:62 | electrical contractor; sq ft 3200 vs 2450 |
| SUB-455 | incomplete — hold: open conflict (sales) | senior_referral | carrier_a | R17/P-053; AG:31 | wholesale janitorial supplies; wholesale never direct; sales 1240000 vs 1420000 |
| SUB-456 | incomplete — hold: loss run missing | senior_referral | carrier_b | R11; AG:38, AG:62 | flooring contractor, no loss run |
| SUB-457 | complete | no_match | — | R8; KO 8 | light metal fabrication shop, class on no list (overridable) |
| SUB-458 | incomplete — hold: open conflict (suite count) | senior_referral | carrier_a | R17; AG:29-30 | office lessor; 8 vs 9 suites |
| SUB-459 | incomplete — hold: open conflict (sq ft) | senior_referral | carrier_a | R17; AG:29-30 | office lessor, 4 suites; sq ft 2950 vs roughly 2400 |
| SUB-460 | incomplete — hold: open conflict (TIV) | senior_referral | carrier_b | R11; AG:38, AG:62 | roofing and sheet metal contractor; building 980000 vs 1180000 |
| SUB-461 | incomplete — hold: open conflict (cooking) | senior_referral | carrier_a (ambiguous, see call 4) | R17/P-053; AG:29-30 | gift shop with lunch counter; cooking none vs stove top |
| SUB-462 | incomplete — hold: open conflict (sales) | senior_referral | carrier_b | R9, R10; AG:39, AG:62 | deli, cooking stated (flat grill, stove top); sales 505000 vs about 560000 |
| SUB-463 | incomplete — hold: open conflict (cooking) | senior_referral | carrier_b | R9, R10; AG:39, AG:62 | deli; cooking none vs yes (schedule) vs fryer (email) |
| SUB-464 | complete | senior_referral | — | R2; D-125; AG:46, AG:39 | pub with full bar and kitchen beside office suites: R2, never confirmable |
| SUB-465 | complete | no_match | — | R1; W1; AG:45-50 | nightclub, dance floor, DJ, full bar |
| SUB-466 | complete | no_match | — | R1; W1; AG:47-49 | hookah lounge, beer and wine |
| SUB-467 | complete | senior_referral | carrier_b | R9, R10; AG:39, AG:62 | breakfast restaurant, griddle, 2 fryers, oven, hood, no liquor |
| SUB-468 | incomplete — hold: loss run not recognised | senior_referral | carrier_b (ambiguous, see call 5) | R9, R10; AG:39, AG:62 | bakery cafe; owner letter only; Carrier B program closed |
| SUB-469 | incomplete — hold: open conflict (sq ft) | senior_referral | carrier_a (ambiguous, see call 6) | R17/P-053; AG:29-31 | wholesale auto parts plus tire mounting; 4100 vs 3600 (warehouse part) |

## Counts per route (SUB-450 to SUB-469)
- carrier_a: 4 (SUB-450, 451, 452, 453; direct routes, R14 and R17, TIV at most 185000, clean Carrier A runs)
- carrier_b and carrier_c: 0 as routes (suggested market only)
- senior_referral: 13 (suggested carrier_a 5: 455, 458, 459, 461, 469; carrier_b 7: 454, 456, 460, 462, 463, 467, 468; no suggestion 1: 464, R2 never confirmable)
- no_match: 3 (SUB-465, 466 R1; SUB-457 R8)
- Total 20. No route is "hold". Status: complete 9, incomplete 11 (454, 455, 456, 458, 459, 460, 461, 462, 463, 468, 469).

The twelve out-of-scope ids SUB-470..SUB-481 carry no route (manual intake).

## Judgment calls where the written rules are silent or strained (for @head-of-underwriting)
1. SUB-450, 451, 452, 453 (documents rebuilt for 450, 452, 453): operations values are allow-list words only, so all four are direct. The insured names (Bookkeeping, Hardware, Insurance Agency) and the emails carry business words; R17 reads the operations text, so a pipeline that cites an email or name word could fail closed to senior_referral; that would be a rule-reading miss, not a gold error. SUB-453: whether the insured is lessor or tenant is not stated.
2. SUB-457: "fabrication" is not on the OTHER list and "manufacturing" is not stated; R8 no_match as T-119 SUB-358. "Railings for commercial jobs" might mean installation (R11); the documents never say so.
3. SUB-459, SUB-462: the email figure is approximate ("roughly", "about"); gold keeps both as open conflicts and a hold (D-132, P-074: an approximate amount never verifies an exact one). SUB-455 states "$1.42 million" exactly, read as 1420000.
4. SUB-461: "lunch counter" is not a carrier-match class word, so the word rule gives R17 senior_referral with Carrier A suggested. If the stove-top cooking is accepted a person would call it a cooking occupancy and suggest Carrier B (R10). Route (senior_referral) is the same.
5. SUB-468: the expiring carrier is Carrier B and its program closed in 2026; suggested market carrier_b is by R9/R10, but the underwriter must check that the market still writes it (P-054 c reading). Owner letter, not a run: same hold as T-119 SUB-350.
6. SUB-469: tire mounting and installation is a service operation not on the OTHER list ("auto repair" is); R17 gives senior_referral with Carrier A suggested, R16 would give none. The email's 3600 is the warehouse alone, not a total, so the "conflict" is not a clean two-number dispute; kept as an open conflict, ambiguous.
7. SUB-453 (5 employees vs five agents and a receptionist) and SUB-456 (7 employees vs five crew) are not card fields; no conflict written, ambiguity in the notes.
8. SUB-462: "flat grill" is a flat-top; the open_flame slot triggers on "grill". Items carry the documents' words; the hood is implied by "Sprinklers: Yes, hood only" but never stated, so no hood item.
9. SUB-463: the schedule row is labelled source "application" yet its cooking value differs from the application; provenance unclear, written as a three-way cooking conflict as in T-119 SUB-349.
