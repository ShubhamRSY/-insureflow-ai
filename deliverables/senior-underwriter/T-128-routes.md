# T-128 — Routes for in-scope submissions (SUB-550 to SUB-569)
- Owner: @senior-underwriter (work done in the main session, D-165 tool rule) · Written before extraction, from the documents and carrier-match.md only (R1-R17, W1, W2, D-125). Nothing was run.
- Route column: plain rule name only (carrier_a, senior_referral, no_match). "hold" is a status, never a route (D-102). The route is the one the file takes once the hold clears.

| SUB ID | Status | route | suggested market if any | rule references | one line of reason |
|---|---|---|---|---|---|
| SUB-550 | complete | carrier_a | — | R14, R17; AG:29-31 | office tenant on Hwy 71 W; "Office" only, TIV 112000, clean A run |
| SUB-551 | complete | carrier_a | — | R14, R17; AG:29-31 | apparel boutique; allow-list words only |
| SUB-552 | complete | carrier_a | — | R14, R17; AG:29-31 | dry retail storefront on US-59 N; allow-list words only |
| SUB-553 | complete | carrier_a | — | R14, R17; AG:29-31 | office suite; allow-list and non-occupancy words only |
| SUB-554 | incomplete — hold: open conflict (sq ft) | senior_referral | carrier_b | R11; AG:38, AG:62 | electrical contractor; sq ft 3150 vs 2450 |
| SUB-555 | incomplete — hold: open conflict (sales) | senior_referral | carrier_a | R17/P-053; AG:31 | wholesale packaging goods; wholesale never direct; sales 1640000 vs $1.9 million |
| SUB-556 | incomplete — hold: open conflict (sales) | senior_referral | carrier_b | R11; AG:38, AG:62 | landscaping contractor; sales 745000 vs 812000 |
| SUB-557 | incomplete — hold: open conflict (suite count) | senior_referral | carrier_a | R17; AG:29-30 | office lessor; 9 vs 10 suites (only hold; P-081-resolvable) |
| SUB-558 | incomplete — hold: open conflict (sq ft) | senior_referral | carrier_a | R17; AG:29-30 | office lessor, 5 suites; sq ft 4900 vs about 4300 |
| SUB-559 | incomplete — hold: open conflict (TIV) | senior_referral | carrier_b | R11; AG:38, AG:62 | roofing contractor; building 845000 vs 980000 |
| SUB-560 | incomplete — hold: open conflict (cooking) | senior_referral | carrier_a (ambiguous, see call 3) | R17/P-053; AG:29-30 | candle and gift shop; cooking none vs countertop fryer |
| SUB-561 | incomplete — hold: open conflict (sales) | senior_referral | carrier_b | R9, R10; AG:39, AG:62 | deli, flat-top stated; sales 498000 vs about 530000 |
| SUB-562 | incomplete — hold: open conflict (cooking) | senior_referral | carrier_b | R9, R10; AG:39, AG:62 | deli; cooking none vs daily frying (email) |
| SUB-563 | complete | no_match | — | R1; W1; AG:45-50 | tavern, full bar, darts, pool tables; no restaurant evidence |
| SUB-564 | complete | no_match | — | R1; W1; AG:45-50 | nightclub, dance floor, DJ, full bar |
| SUB-565 | complete | senior_referral | carrier_b | R9, R10; AG:39, AG:62 | breakfast restaurant, griddle, 2 fryers, hood, no liquor |
| SUB-566 | incomplete — hold: open conflict (sq ft) | senior_referral | carrier_b | R9, R10; AG:39, AG:62 | bakery cafe, oven, no liquor; sq ft 2150 vs 2450 |
| SUB-567 | complete | senior_referral | carrier_a | R17; AG:29 | architecture office (two floors, one building) |
| SUB-568 | complete | senior_referral | carrier_a | R17; AG:29 | law office (2nd floor, Ste 220) |
| SUB-569 | complete | senior_referral | carrier_a | R17; AG:30 | saddle and tack retail store (two entrances, one building) |

## Counts per route (SUB-550 to SUB-569)
- carrier_a: 4 (SUB-550, 551, 552, 553; direct routes, R14 and R17, TIV at most 186000, clean Carrier A runs)
- carrier_b and carrier_c: 0 as routes (suggested market only)
- senior_referral: 14 (suggested carrier_a 7: 555, 557, 558, 560, 567, 568, 569; carrier_b 7: 554, 556, 559, 561, 562, 565, 566)
- no_match: 2 (SUB-563, 564 R1)
- Total 20. No route is "hold". Status: complete 10, incomplete 10 (554-562, 566).

The twelve out-of-scope ids SUB-570..SUB-581 carry no route (manual intake): criterion 1 = 570, 571; criterion 2 = 572-577 (572 highway second address in a sentence naming Carrier B, 573 second address below "Mailing address: same as premises", 574-577 words only); criterion 3 = 578, 579; criterion 4 = 580, 581.

## Judgment calls where the written rules are silent or strained (for @head-of-underwriting)
1. SUB-550, 553: the insured names (Advisors, Consulting) carry business words; R17 reads the operations text, so a pipeline that cites a name word could fail closed to senior_referral; that would be a rule-reading miss, not a gold error (T-120 M4 reading).
2. SUB-550, 552 (P-080): the premises is a highway address ("2604 Hwy 71 W", "3115 US-59 N"); the emails name the highway with no house number, so each file has one address in every document. A scope result of manual intake here would be a false manual intake (safe direction, counted).
3. SUB-560: "candle and gift shop" reads as retail, but 'candle', 'gift' and 'shop' are not R14 allow-list words, so R17 senior_referral with Carrier A suggested. If the weekend fryer is confirmed a person would call it a cooking exposure and suggest Carrier B (R10). The route (senior_referral) is the same.
4. SUB-555, 558, 561: the second side is "$1.9 million" (words), "about 4,300" and "about $530,000" (approximate). Gold keeps each as an open conflict and a hold (D-132, P-074).
5. SUB-556: the mailing address is a PO Box (role-labelled), not a second premises; in scope.
6. SUB-557: the suite conflict is the only hold. Under P-081 an underwriter resolving it would make the file routable; the pipeline is scored before any underwriter action, so gold stays "incomplete".
7. SUB-566: the email says the space grew when the back room was added; that is the same premises, not a second place.
8. SUB-568: building TIV 58000 for a 2nd-floor tenant is unexplained (improvements?); not a conflict, noted.
9. SUB-577: "The second shop was sold in March, leaving just this one" is out of scope under D-146 (fail closed), though only one shop operates now.
10. SUB-573: "Mailing address: same as premises" sits in the email, and the next line names a second address; the line is a filled label, not a bare one (P-080), so the address counts.
