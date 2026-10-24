# T-119 — Routes for in-scope submissions (SUB-340 to SUB-359)
- Owner: @senior-underwriter · Written before extraction, from the documents and carrier-match.md only (R1-R17, W1, W2, D-125). Nothing was run.
- Route column: plain rule name only (carrier_a, senior_referral, no_match). "hold" is a status, never a route (D-102). The route is the one the file takes once the hold clears.

| SUB ID | Status | route | suggested market if any | rule references | one line of reason |
|---|---|---|---|---|---|
| SUB-340 | complete | carrier_a | — | R14, R17; AG:29-31 | office tenant; "Office" only, TIV 95000, clean run |
| SUB-341 | complete | carrier_a | — | R14, R17; AG:29-31 | clothing retail storefront; clothing, retail, storefront all allow-list |
| SUB-342 | complete | carrier_a | — | R14, R17; AG:29-31 | dry goods retail store; allow-list words only |
| SUB-343 | complete | carrier_a | — | R14, R17; AG:29-31 | thrift store; allow-list phrase only |
| SUB-344 | incomplete — hold: open conflict (sq ft) | senior_referral | carrier_b | R11; AG:38, AG:62 | electrical contractor; sq ft 3200 vs 2450 |
| SUB-345 | incomplete — hold: open conflict (sales) | senior_referral | carrier_a | R17/P-053; AG:31 | wholesale janitorial supplies; wholesale never direct; sales 1240000 vs 1420000 |
| SUB-346 | incomplete — hold: open conflict (suite count) | senior_referral | carrier_a | R17; AG:29-30 | office lessor: lessor, suites, professional, tenants not on allow-list; 8 vs 9 suites |
| SUB-347 | complete | senior_referral | carrier_a | R17; AG:29-30 | office lessor, 6 suites: same word reason |
| SUB-348 | incomplete — hold: open conflict (cooking) | senior_referral | carrier_b | R9, R10; AG:39, AG:62 | deli; cooking none (application) vs stove top and flat grill (email) |
| SUB-349 | incomplete — hold: open conflict (cooking) | senior_referral | carrier_b | R9, R10; AG:39, AG:62 | deli; cooking none vs yes (schedule) vs griddle (email); "sandwich bar" is not a bar class (M6) |
| SUB-350 | incomplete — hold: loss run not recognised | senior_referral | carrier_a | R17/P-053; AG:31 | wholesale plumbing supplies; owner letter only |
| SUB-351 | complete | senior_referral | carrier_b | R9, R10; AG:39, AG:62 | breakfast and lunch restaurant, griddle, fryer, oven, hood, no liquor |
| SUB-352 | complete | senior_referral | — | R2; D-125; AG:46, AG:39 | pub with full bar and kitchen beside office suites: bar word with restaurant evidence is R2, never confirmable |
| SUB-353 | complete | no_match | — | R1; W1; AG:45-50 | cocktail lounge, full liquor, bottle service, DJ |
| SUB-354 | complete | no_match | — | R1; W1; AG:45-50 | nightclub, dance floor, DJ, full bar |
| SUB-355 | complete | no_match | — | R1; W1; AG:47-49 | hookah lounge, beer and wine |
| SUB-356 | complete | senior_referral | carrier_c | R12; AG:37, AG:62 | habitational 16 units, no sprinklers (AG:61 candidate) |
| SUB-357 | complete | senior_referral | carrier_c | R12; AG:37, AG:62 | habitational 8 units, no sprinklers (AG:61 candidate) |
| SUB-358 | complete | no_match | — | R8; KO 8 | light metal fabrication shop, class on no list (overridable) |
| SUB-359 | incomplete — hold: loss run missing | senior_referral | carrier_b | R11; AG:38, AG:62 | flooring contractor |

## Counts per route (SUB-340 to SUB-359)
- carrier_a: 4 (SUB-340, 341, 342, 343; direct routes, R14 and R17, TIV at most 175000, clean Carrier A runs)
- carrier_b: 0 and carrier_c: 0 as routes (suggested market only)
- senior_referral: 12 (suggested carrier_b 5: 344, 348, 349, 351, 359; carrier_c 2: 356, 357; carrier_a 4: 345, 346, 347, 350; no suggestion 1: 352, R2 never confirmable)
- no_match: 4 (SUB-353, 354, 355 R1; SUB-358 R8)
- Total 20. No route is "hold". Status: complete 13, incomplete 7 (344, 345, 346, 348, 349, 350, 359).

The twelve out-of-scope ids SUB-360..SUB-371 carry no route (manual intake).

## Judgment calls where the written rules are silent or strained (for @head-of-underwriting)
1. SUB-340-343: gold reads the operations value only ("Office", "Clothing retail storefront", "Dry goods retail store", "Thrift store"). The emails add goods and premises words (fabric, notions, work wear; donations; racks, fitting rooms; desks and computers). R17 reads value, quote and cited lines, so a pipeline that cites an email line could fail closed to senior_referral with Carrier A suggested; that would be a route miss caused by the rule, not by the gold.
2. SUB-350: "plumbing" is on the R11 list, here as goods sold to plumbers. Gold reads wholesale (T-117 SUB-254 reading), senior_referral with Carrier A suggested; a word reader that adds R11 gets R7 or carrier_b instead.
3. SUB-349: "sandwich bar" and "soup bar" (email, insured name) are food counters (M6), not R2; the operations value holds no bar word.
4. SUB-358: "fabrication" is not on the OTHER list and "manufacturing" is never stated; R8 no_match, as T-117 SUB-255.
5. SUB-352: R2 senior_referral with no suggested market, per D-125 (bar word with restaurant evidence beside a second non-food operation).
6. SUB-355: "hookah lounge" carries two classes (hookah_adult, lounge_nightclub) because both words are stated; the route is no_match either way.
