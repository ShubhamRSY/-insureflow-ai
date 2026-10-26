# P-049 (final rules list, rework under D-096 item 1) — every routing rule is written with its reason, or removed
- Date / Owner: 2026-10-16 / @head-of-underwriting; decided by @user (types `approve change P-049`)
- Source: D-096 item 1; D-095 item 2 (B-364); deliverables/senior-underwriter/B-364-gold-check.md. AG = appetite-guide.md, CAG = carrier-appetite.md (same text as simulation/carriers.md).
- This file changes no code and no guide. Nothing is built until the user types the approval.
- THE RULES FILE: `deliverables/head-of-underwriting/carrier-match.md` (exists, stale; on approval I rewrite it as the one table below, each row with an ID R1..R15). The code cites the ID in its note text. The guides keep only the business policy (AG, CAG).

## (a) "All restaurants -> senior_referral": JUSTIFIED, not narrowed
- Written source, three places: AG:39 "Restaurants and any cooking occupancy, including food trucks. Senior referral." AG:62 Knock-out 6 "habitational, contractor, or restaurant THEN senior referral, never auto-quote." AG:66 "I will not defend an auto-quote on a restaurant."
- Against it: CAG:6 says Carrier B takes restaurants, with 3 clean loss years. That is the carrier's market, not our authority. Same shape D-060 ruled for contractors: senior_referral, Carrier B shown as the suggested market.
- D-079 does not conflict. It handled only the bar/liquor words (a cuisine word must not decide); it left the ordinary restaurant route "as now" because the question was not before it.
- The code cannot check what makes Carrier B safe: 3 clean years (note on the route says "not checked"), liquor <= 10% of receipts, or the AG:41 loss-history referral. A restaurant is a cooking occupancy; profitability first, so a human looks.
- Plain cost: after this, no restaurant and no habitational file reaches carrier_b or carrier_c as a final route. Only carrier_a is a direct route; B and C appear as suggested markets. If the user wants clean restaurants to go to B directly, that is an AG amendment plus a built 3-clean-years check, not a code tweak. I do not recommend it before the pilot.
- Narrowing offered and rejected: "referral only if bar/liquor" has no written source. AG:39 has no exception.

## (b) Sprinklered apartments: the intent is BOTH, and the code line is the bug
- Plainly: sprinklered AND unsprinklered habitational both go to senior_referral. AG:37 "All habitational ... Senior referral", AG:62. Sprinklers do not lift the referral; they decide the suggested market (C) and the AG:61 knock-out.
- AG:61 (Knock-out 5) is NOT the referral. It is a decline candidate only when habitational AND cooking AND no sprinklers.
- Code bugs (workbench.py, `_match`), fixed by the orchestrator after approval, not written as rules:
  1. Line 184: `... else out("carrier_c")` sends sprinklered habitational with TIV <= 5M straight to carrier_c, against AG:37/62. Fix: `out("senior_referral", "habitational (AG:37, AG:62); suggested market: carrier_c", suggested="carrier_c")`. Same shape as contractor, line 180.
  2. Line 186: the note "habitational without sprinklers (AG:61)" cites the wrong rule. Fix: cite "AG:37, AG:62"; add "AG:61 knock-out candidate, human decides" only when the file also shows cooking equipment. Never a decline. The same wrong citation is in D-059 item 6 (annotate, do not rewrite).
  3. Line 194: restaurants return carrier_b against AG:39. Fix: senior_referral, suggested carrier_b, note "restaurant / cooking occupancy (AG:39); Carrier B needs 3 clean loss years, not checked".
  4. Lines 192-193 and `CAP_B` (line 116): the $2,000,000 Carrier B cap becomes unreachable once line 194 is fixed (the only class that reaches it is B). Remove it. It never had a source and @actuary never signed.

## Final rules list
| ID | Rule (what the code does) | Reason / source | Keep-write or remove | Code changes? |
|---|---|---|---|---|
| R1 | Prohibited class words (bar, tavern, nightclub, cannabis, fireworks, explosives, armed security, student or subsidized housing) -> no_match, a recommendation, never a decline | AG:45-49, Knock-out 1; D-059 item 5 | Keep-write (word list in the file) | No |
| R2 | Add pub, lounge to the bar words; a bar word with restaurant evidence -> senior_referral "possible bar/liquor exposure" | D-079 (user); AG:46 line to read "Bars, pubs, lounges, taverns, nightclubs, hookah..." | Keep-write | No |
| R3 | Spanish names of a sourced class (cantina, taberna, antro, discoteca, dispensario, etc.) read as that class | D-060 translation of sourced classes only; @responsible-ai review owed (B-197) before pilot | Keep-write | No |
| R4 | Synonyms: armed guard = armed security; marijuana/marihuana, dispensary = cannabis; explosive(s), firework(s) | Same AG lines, wording variants | Keep-write | No |
| R5 | No readable operations, open conflict, or review pending (gated) -> hold | AG Knock-out 3 and 4; D-021, P-041 | Keep-write | No |
| R6 | TIV missing, blank, zero or negative -> hold (P-050 adds a labelled provisional class route) | D-061, D-062; add to AG Knock-out 4 | Keep-write | No (P-050 is separate) |
| R7 | Two carrier classes match -> senior_referral, never pick one silently | D-059 item 7 (my rule, no guide text); add as AG Knock-out 7 | Keep-write | No |
| R8 | Readable class on no list -> no_match, overridable with a reason | D-059 item 5, D-060; add as AG Knock-out 8 | Keep-write | No |
| R9 | Cooking equipment stated "yes" counts as generic restaurant evidence; class B words are generic only (restaurant, food service, kitchen, eatery, cafe, catering, bakery, coffee shop, deli), never a cuisine word | D-078, D-079 | Keep-write | No |
| R10 | Restaurant or cooking occupancy -> senior_referral, suggested carrier_b, never an automatic carrier_b | AG:39, AG:62, AG:66; CAG:6 is the market only. Justified in (a) | Keep-write | Yes: line 194 (bug) |
| R11 | Contractor (word list: contractor, roofing, handyman, painter, carpenter, flooring, drywall, plumbing, electrician) -> senior_referral, suggested carrier_b. Add HVAC, glazier, mason. Any trade not listed is still a contractor | AG:38, AG:62; D-060. List only helps the reader | Keep-write | Yes: add 3 words |
| R12 | Habitational (word list as in code, 1 unit or more) -> senior_referral, suggested carrier_c. Sprinkler answer missing -> hold. Sprinklers "no" with cooking shown -> note "AG:61 knock-out candidate, human decides", never a decline | AG:37, AG:62, AG:61; CAG:7 is the market only. Justified in (b) | Keep-write | Yes: lines 184, 186 (bug) |
| R13 | TIV over $5,000,000 per location -> senior_referral, reason "outside pilot TIV limit (AG:16)" | AG:16; D-060. AG wording "out of pilot" becomes "senior referral" | Keep-write | No |
| R14 | Class A words (office, retail, storefront, wholesale, Spanish variants) and TIV <= $5,000,000 inclusive -> carrier_a, shown as a suggestion with "verify: no restaurant, liquor <= 10%, no cold storage, no hazardous goods, no lab or medical" | AG:29-31, CAG:5 | Keep-write | Yes: add the "verify" note text (the code does not check the exclusions) |
| R15 | Carrier B cap $2,000,000, over cap -> senior_referral | No guide states it; @actuary never signed; unreachable once R10 is fixed | REMOVE | Yes: delete lines 192-193 and CAP_B |

Count: 15 rules; 14 kept and written, 1 removed (R15). Code changes after approval: R10, R11, R12, R14, R15 (five rules; bug lines 184, 186, 194, 192-193, 116). Nothing else changes code. Guides edited by me on approval: AG:46 and :16 wording, Knock-outs 4, 7, 8, the CAG sentence "Carrier B and C are suggested markets for restaurants and habitational; the route is always senior referral (AG:39, AG:37)". Item 15 (territory, locations 4-10, premium and revenue gates, liquor > 10%) stays out of P-049: a code gap against written rules, backlog, after the demo.

## T-103 gold rows that change if approved (T-103 is plan only; no file or gold exists yet)
- Row 3 (restaurant, Carrier B run): carrier_b -> senior_referral (AG:39).
- Row 5 (sprinklered apartments, Carrier C run): carrier_c -> senior_referral (AG:37).
- Row 6 (cafe/bakery scan): carrier_b -> senior_referral (cooking occupancy).
- Row 7 (unsprinklered apartments): stays senior_referral; citation label changes from AG:61 to AG:37, AG:62.
- Row 10 (Spanish restaurant, provisional): carrier_b -> senior_referral. Row 17 (restaurant, 2 locations): carrier_b -> senior_referral. Row 19 (3-location sprinklered apartments): carrier_c -> senior_referral.
- Rows 4, 18 unchanged. Rows 1, 2, 8, 9, 13 (carrier_a) unchanged. Side effect: T-103 line "every route appears in gold" loses carrier_b and carrier_c as final routes; they remain as suggested markets. @senior-underwriter and @model-risk re-approve the mix after the edit.
- Existing dev gold SUB-130, 132, 133, 136, 140 (carrier_b or carrier_c) also change to senior_referral if approved; they are dev gold, not frozen hold-out. Re-check from cache, no model calls. The older route scores stay as published.

## Sign-offs still owed
@actuary: none now (cap removed). @responsible-ai: R3 Spanish words and the housing proxy (B-197). @compliance: only if a Spanish word is used in a producer notice.
