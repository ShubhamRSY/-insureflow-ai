# T-117 gold summary — SUB-238 to SUB-269
- Owner: @senior-underwriter · Gold written by hand before any run, from the documents and the written rules only. No pipeline output, scope detector, extraction, OCR script or scorer was read or run. Loss-run images (SUB-239, 253, 256) and the scanned applications were read by eye from rendered pages.
- Cards: `deliverables/senior-underwriter/gold-set/SUB-238.md` to `SUB-269.md` (32). Routes: `T-117-routes.md`. Rule line M6 added to `operations-gold-rule.md` section 2.
- Out-of-scope cards carry the `- Scope:` line (criteria codes) and `- Status: manual intake` only.

## Counts
- In scope 20 (SUB-238-257); out of scope 12 (SUB-258-269).
- Criteria: 1 = 4 (260, 261, 262, 263); 2 = 5 (263, 264, 265, 268, 269); 3 = 4 (266, 267, 268, 269); 4 = 2 (258, 259). Two criteria: 3 (263 = 1+2; 268, 269 = 2+3). Criterion 4 alone: 2. Same as the mix.
- Routes (in scope): carrier_a 2, senior_referral 14, no_match 4, hold 0. Status: complete 10, incomplete 10.
- Loss-run lines: dated and recognised 14 (valued-as-of line present); no valued line 6: undated typed runs 242, 254; no-known-loss letters 241 (undated) and 248 (dated 2026-09-15); not recognised layout 239; no loss run 244. Latest valued date 2026-09-30 (SUB-249), before the run date 2026-10-21.

## Coverage
- W1 prohibited, held: 238 (hold year built), 239 (hold loss run), 252 (hold conflict). All three no_match.
- Office-lessor: 246, 248 (both carrier_a). Deli-style: 247, 249 (both R10, carrier_b suggested); 250 two-operation retail/office also. 
- Two-operation: 250 (office + retail, R16), 252 (bar_pub + office, R1), 249 deli + grocery (restaurant + retail, one policy). 251 is one class (retail), see below.
- M6 words ("salad bar", "sushi bar", "espresso bar", "bar snacks"): none in any file.

## Mismatches with the producer's mix (documents win)
1. SUB-239: the mix says "Carrier B layout, valued 2026-07-02". The scanned page prints a valuation date but has no claims table and an inline claim; it is not the recognised Carrier B layout. Gold: needs review, hold, no valued-as-of line.
2. SUB-251: the mix counts it as a two-operation file. The class list has no tasting-room value and no bar word is stated, so gold carries one class (retail). Route is W2d (the word "liquor" in "liquor liability" on the line of business), not a W1 or R16 route.
3. SUB-243 and SUB-257: the mix calls them allow-list retail. "bicycles, parts, repair, service" and "used ... household goods" are goods or trade words, never neutral under R17, so gold is senior_referral with carrier_a suggested, not carrier_a.
4. SUB-255: the mix says referral-style manufacturing. The documents never say manufacturing or name a trade; gold is R8 no_match (overridable), class other_class.
5. SUB-252: the mix expects a pub; gold is no_match R1 (pub beside office), not the R2 referral a pub with restaurant evidence alone would take.
6. SUB-249: the mix says a conflict in square feet; confirmed and held. SUB-257 sales conflict, SUB-252 suite count conflict confirmed and held.
7. SUB-254: the mix says undated; confirmed. "contractors" in the operations names the customers (not R11).
8. Mix coverage counts differ by classification only: allow-list-style direct routes are 2 (246, 248), not 7.

## Judgment calls to check
- Restaurants are "complete" when the pipeline-held fields are present, as in T-108; the extinguishing inspection date, closing hour and liquor share (required-fields.md) are asked for in the recommendation, not a hold.
- Loss runs of one policy term (240, 243, 247, 249, 250, 251, 252, 253, 255, 257) are accepted as recognised layouts; the short history is noted in the recommendation only.
- Cooking items left out when the documents contradict themselves (SUB-239 oven vs "no real kitchen"; SUB-252 fryer vs "no full kitchen"); notes carry both.
- SUB-248 physical therapist (email) and the R17 neutral-word question for lessor language: see `T-117-routes.md`.
- Policy period end dates after the run date (243, 247, 254, others) are period dates, not valued dates.

## Changes after the T-117 lint (gold only)
- SUB-239: "closes midnight" moved from items to notes (fits no slot).
- SUB-247: "catering" moved from items to notes (restaurant synonym; a wrong answer keeping it would read as restaurant).
- SUB-252: alcohol item "full bar" changed to "full liquor" (H1; bar_pub already carried).
- SUB-238: item "no kitchen" changed to "no cooking" (kitchen is a restaurant synonym). Other in-scope cards checked against the class synonym lists: no further fault.
