# T-117 — Routes for in-scope submissions (SUB-238 to SUB-257)
- Owner: @senior-underwriter · Written before extraction (D-119), from the documents and carrier-match.md only. Nothing was run.
- Route column: plain rule name only (carrier_a, senior_referral, no_match). "hold" is a status, never a route (D-102). The route is the one the file takes once the hold clears.

| SUB ID | Status | route | suggested market if any | rule references | one line of reason |
|---|---|---|---|---|---|
| SUB-238 | incomplete — hold: year built | no_match | — | R1; W1; AG:45-50 | nightclub, DJ, dance floor, bar service until 2 a.m. (W1 alone) |
| SUB-239 | incomplete — hold: loss run not recognised | no_match | — | R1; W1; AG:45-50 | cocktail lounge, full liquor, live music (W1 alone); image-only run lacks the Carrier B layout |
| SUB-240 | complete | senior_referral | carrier_b | R10; AG:39, AG:62 | Italian restaurant, wood-fired oven, fryer, hood, beer and wine |
| SUB-241 | incomplete — hold: loss run not recognised | senior_referral | carrier_b | R10; AG:39, AG:62 | cafe with gas range, fryer, hood, no alcohol; undated owner letter |
| SUB-242 | incomplete — hold: loss run undated | senior_referral | — | W2c; R14; AG:31 | frozen seafood wholesale with cold storage |
| SUB-243 | complete | senior_referral | carrier_a | R17; AG:29-30 | bicycle retail and repair: goods and service words not on allow-list |
| SUB-244 | incomplete — hold: loss run missing | senior_referral | carrier_b | R11; AG:38, AG:62 | roofing contractor |
| SUB-245 | complete | senior_referral | carrier_c | R12; AG:37, AG:62 | habitational 12 units, no sprinklers (AG:61 candidate) |
| SUB-246 | complete | carrier_a | — | R14; AG:29-31 | office building lessor, 14 suites, TIV 2.65M |
| SUB-247 | complete | senior_referral | carrier_b | R9, R10; AG:39, AG:62 | deli with flat-top, hood, catering, no liquor |
| SUB-248 | incomplete — hold: loss run not recognised | carrier_a | — | R14; AG:29-31 | office building lessor, six suites; verify medical tenant (email only) |
| SUB-249 | incomplete — hold: open conflict (sq ft) | senior_referral | carrier_b | R9, R10; AG:39, AG:62 | deli with grill, hood plus grocery market, no alcohol |
| SUB-250 | complete | senior_referral | — | R16; AG:33 | two operations: tax office plus phone repair retail |
| SUB-251 | complete | senior_referral | — | W2d; R14; AG:30 | wine shop and tasting room; "liquor liability" on the line of business |
| SUB-252 | incomplete — hold: open conflict (suite count) | no_match | — | R1; W1; AG:45-50 | pub with full bar beside office suites (stricter R1 over R2) |
| SUB-253 | complete | senior_referral | carrier_b | R10; AG:39, AG:62 | fast casual Chinese, wok, deep fryer, hood, no alcohol |
| SUB-254 | incomplete — hold: loss run undated | senior_referral | carrier_a | R17; P-053; AG:31 | wholesale electrical supplies; wholesale never routes directly |
| SUB-255 | complete | no_match | — | R8; KO 8 | cabinet and millwork shop, class on no list (overridable) |
| SUB-256 | complete | senior_referral | carrier_c | R12; AG:37, AG:62 | habitational 12 units, no sprinklers (AG:61 candidate) |
| SUB-257 | incomplete — hold: open conflict (sales) | senior_referral | carrier_a | R17; AG:29-30 | thrift retail: "used" and "household goods" not on allow-list |

## Counts per route (SUB-238 to SUB-257)
- carrier_a: 2 (SUB-246, SUB-248)
- carrier_b: 0 and carrier_c: 0 as routes (suggested market only)
- senior_referral: 14 (suggested carrier_b 6: 240, 241, 244, 247, 249, 253; carrier_c 2: 245, 256; carrier_a 3: 243, 254, 257; no suggestion 3: 242, 250, 251)
- no_match: 4 (SUB-238, 239, 252, 255)
- Total 20. No route is "hold".

The twelve out-of-scope ids SUB-258..SUB-269 carry no route (manual intake).

## Judgment calls where the written rules are silent or strained (for @head-of-underwriting)
1. SUB-252: pub plus a fryer (R9 evidence, R2) beside an office operation (R1). Stricter R1 taken (carrier-match note 2: stricter wins except bar beside restaurant evidence alone).
2. SUB-246, SUB-248: R17 strict word list does not list "lessor", "tenants", "professional"; T-108 SUB-206 and SUB-213 set the precedent (carrier_a), followed here.
3. SUB-248: a physical therapist tenant in the email (W2b word) is not in the operations text, so the rule gives carrier_a; AG:29 excludes medical occupancy, so the underwriter verifies.
4. SUB-254: "contractors" names customers; gold reads wholesale, not R11.
5. SUB-255: no manufacturing word and no trade word; R8 no_match (overridable).
