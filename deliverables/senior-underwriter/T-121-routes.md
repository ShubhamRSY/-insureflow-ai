# T-121 — Routes for in-scope submissions (SUB-510 to SUB-529)
- Owner: @senior-underwriter · Written before extraction, from the documents and carrier-match.md only (R1-R17, W1, W2, D-125). Nothing was run.
- Route column: plain rule name only (carrier_a, senior_referral, no_match). "hold" is a status, never a route (D-102). The route is the one the file takes once the hold clears.

| SUB ID | Status | route | suggested market if any | rule references | one line of reason |
|---|---|---|---|---|---|
| SUB-510 | complete | carrier_a | — | R14, R17; AG:29-31 | office tenant; "Office" only, TIV 96000, clean A run |
| SUB-511 | complete | carrier_a | — | R14, R17; AG:29-31 | clothing boutique; allow-list words only |
| SUB-512 | complete | carrier_a | — | R14, R17; AG:29-31 | dry goods retail store; allow-list words only |
| SUB-513 | complete | carrier_a | — | R14, R17; AG:29-31 | office suite; allow-list and non-occupancy words only |
| SUB-514 | incomplete — hold: open conflict (sq ft) | senior_referral | carrier_b | R11; AG:38, AG:62 | plumbing contractor; sq ft 3500 vs 2700 |
| SUB-515 | incomplete — hold: open conflict (sales) | senior_referral | carrier_a | R17/P-053; AG:31 | wholesale paper goods; wholesale never direct; sales 2080000 vs 2350000 |
| SUB-516 | incomplete — hold: loss run missing | senior_referral | carrier_b | R11; AG:38, AG:62 | painting contractor, no loss run |
| SUB-517 | incomplete — hold: open conflict (suite count) | senior_referral | carrier_a | R17; AG:29-30 | office lessor; 11 vs 12 suites |
| SUB-518 | incomplete — hold: open conflict (sq ft) | senior_referral | carrier_a | R17; AG:29-30 | office lessor, 6 suites; sq ft 5800 vs roughly 5100 |
| SUB-519 | incomplete — hold: open conflict (TIV) | senior_referral | carrier_b | R11; AG:38, AG:62 | roofing contractor; building 1050000 vs 1320000 |
| SUB-520 | incomplete — hold: open conflict (cooking) | senior_referral | carrier_a (ambiguous, see call 3) | R17/P-053; AG:29-30 | gift shop; cooking none vs countertop fryer |
| SUB-521 | incomplete — hold: open conflict (sales) | senior_referral | carrier_b | R9, R10; AG:39, AG:62 | deli, flat-top stated; sales 575000 vs around 610000 |
| SUB-522 | incomplete — hold: open conflict (cooking) | senior_referral | carrier_b | R9, R10; AG:39, AG:62 | deli; cooking none vs daily fryer (email) |
| SUB-523 | complete | no_match | — | R1; W1; AG:45-50 | tavern, full bar, pool tables; no restaurant evidence |
| SUB-524 | complete | no_match | — | R1; W1; AG:45-50 | nightclub, dance floor, DJ, full bar |
| SUB-525 | complete | senior_referral | carrier_b | R9, R10; AG:39, AG:62 | breakfast restaurant, griddle, 2 fryers, hood, no liquor |
| SUB-526 | complete | senior_referral | carrier_b | R9, R10; AG:39, AG:62 | bakery cafe, oven, no liquor |
| SUB-527 | complete | senior_referral | carrier_a | R17; AG:29 | tax and accounting office (two floors, one building) |
| SUB-528 | complete | senior_referral | carrier_a | R17; AG:29 | law office (2nd floor, Ste 210) |
| SUB-529 | complete | senior_referral | carrier_a | R17; AG:30 | shoe and boot retail store (two entrances, one building) |

## Counts per route (SUB-510 to SUB-529)
- carrier_a: 4 (SUB-510, 511, 512, 513; direct routes, R14 and R17, TIV at most 174000, clean Carrier A runs)
- carrier_b and carrier_c: 0 as routes (suggested market only)
- senior_referral: 14 (suggested carrier_a 7: 515, 517, 518, 520, 527, 528, 529; carrier_b 7: 514, 516, 519, 521, 522, 525, 526)
- no_match: 2 (SUB-523, 524 R1)
- Total 20. No route is "hold". Status: complete 11, incomplete 9 (514-522).

The twelve out-of-scope ids SUB-530..SUB-541 carry no route (manual intake): criterion 1 = 530, 531; criterion 2 = 532-537 (534-537 words only); criterion 3 = 538, 539; criterion 4 = 540, 541.

## Judgment calls where the written rules are silent or strained (for @head-of-underwriting)
1. SUB-510, 512, 513: the insured names (Accounting, Mercantile, Consulting) carry business words; R17 reads the operations text, so a pipeline that cites a name word could fail closed to senior_referral; that would be a rule-reading miss, not a gold error (T-120 M4 reading).
2. SUB-527, 528, 529 (P-077 near-misses): "two floors", "2nd floor, suite 210" and "two entrances" describe one building at one address. Gold keeps them in scope; scope-v5 sending them to manual intake would be a false manual intake (safe direction, counted).
3. SUB-520: "gift shop" reads as retail in the class list, but 'gift' and 'shop' are not R14 allow-list words, so R17 senior_referral with Carrier A suggested. If the Saturday fryer is confirmed a person would call it a cooking exposure and suggest Carrier B (R10). The route (senior_referral) is the same.
4. SUB-515, 518, 521: the second side is "$2.35 million" (words), "roughly 5,100" and "around $610,000" (approximate). Gold keeps each as an open conflict and a hold (D-132, P-074).
5. SUB-516: the mailing address is a PO Box (role-labelled), not a second premises; in scope.
6. SUB-528: building TIV 64000 for a 2nd-floor tenant is unexplained (improvements?); not a conflict, noted.
7. SUB-537: "closed our second store" is out of scope under D-146 (fail closed), though only one store operates now.
