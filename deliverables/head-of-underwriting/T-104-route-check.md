# T-104 route check: SUB-174, 182, 186, 201 (T-106b, D-111)

- Owner: @head-of-underwriting. Date: 2026-10-18. Report only: no code, gold, score or team/ file changed. FICTIONAL data.
- Read: v6 score + mismatch files, the 4 gold files, the 4 applications, carrier-match.md (R1-R17, W1, W1b, W2), appetite-guide.md (AG), carrier-appetite.md, and `_match()` in `underwriting_pipeline/app/workbench.py` (read only, to see which text the rules are applied to).
- Route gate is 16/20 (needs 18); 0 unsafe. None of these 4 reached a carrier. All four are the safe kind of miss (no_match or senior_referral, never a send).

## What the code reads (matters for every file)

`_match()` reads the extracted `operations` answer (`_ops`) and the extracted `cooking.equipment` state. It never reads the "Line of business:" line, the "Cooking operations:" line, or the insured's name. carrier-match.md says "operations text" only in R17; for the class words (R9, R10, R14, W1b) it does not say which text is read. This is the one unclear point behind 174, 182 and 186.

## Summary

| File | Pipeline route | Gold route | Class | Proposal |
|---|---|---|---|---|
| SUB-174 | no_match (R8) | senior_referral, Carrier A suggested | RULE UNCLEAR (source text of class words). Strict reading: pipeline right. Intent reading: code wrong | P-061 if I rule "read the line of business" |
| SUB-182 | no_match (R8) | senior_referral, Carrier B suggested | CODE WRONG | P-061 (and P-059 may already fix it) |
| SUB-186 | hold, provisional no_match (R8) | senior_referral (R2) | CODE WRONG for the route; the hold is a status issue, not a route issue | P-061 (and P-059 may already fix it) |
| SUB-201 | hold, provisional senior_referral (R2) | no_match (R1) | GOLD WRONG under the rules as written; rule defect (W1 vs W1b, R9 "kitchen") | P-062 if I rule nightclub is always R1 |

## SUB-174 Sunbelt Office Suites LLC

- Documents: Operations "Leased executive suites (6 tenants), reception desk, shared conference room. No cooking." Line of business "Commercial property, general liability - office". Name has "Office". TIV 640,000, sprinklered masonry, Austin TX, expiring Carrier A. Loss run is a scan (review pending, status not a route issue).
- Pipeline route: no_match, "readable class on no carrier list (R8; KO 8)", overridable.
- Gold route: senior_referral, suggested Carrier A.
- Rule by rule:
  - R5/R6 hold gates: pass (operations readable, TIV 640,000).
  - W1: no word. W1b: no word. W2a-e: no word ("No cooking" is dropped as a negation).
  - R9/R10: no restaurant evidence; correct.
  - R14 office list: office, offices, office building, oficina. The word "office" is not in the operations text, only in the name and line of business. "Executive suites" and "tenants" are not on the list. AG:29 says "Office: tenants and office-building lessors", so the class is in the guide, but carrier-match.md lists words, and none is in the operations.
  - R17: even with an office word, the operations words (leased, executive, tenants, reception, desk, shared, conference) are not allow-list or neutral, so the answer would be senior_referral, Carrier A suggested. That is exactly the gold route.
  - R8: applies if no class word is found. It does here, if only operations is read.
- Verdict: the written rules do not say whether the line of business counts as class text. Strict word-list reading: pipeline correct (R8). Intent reading (AG:29 names office lessors as the target; the application says "office" on its own class line): code wrong. I will not pick it in this report; it is my call to make and it is listed under "Decisions owed" below. The gold used the intent reading without saying so.

## SUB-182 Gulf Coast Sub & Deli Co

- Documents: Line of business "BOP - restaurant (quick service, no liquor)". Operations "Sub shop, cold cuts, hot sandwiches on flat-top grill, convection ovens. No fryer, no hood suppression unknown." Cooking operations "Flat-top grill, two convection ovens". Hood inspected 2026-07-28. Unsprinklered, TIV 240,000, Corpus Christi TX, expiring Carrier B.
- Pipeline route: no_match (R8), same note.
- Gold route: senior_referral, Carrier B suggested (R9, R10).
- Rule by rule:
  - R5/R6: pass for the route (the status flag "may be missing: liquor" is a status matter).
  - W1/W1b: no bar word. W2: none ("No fryer" dropped; no cold storage, liquor or chemical word; "no liquor" is only in the line of business and a negation anyway).
  - R9: restaurant evidence is "stated cooking equipment yes" or a generic word. The operations text itself states a flat-top grill and convection ovens, which is stated cooking equipment. The line of business says the generic word "restaurant". The name has "Deli" (R9 word), though a name is not named as a source anywhere.
  - R10: AG:39 and AG:62 put every restaurant or cooking occupancy at senior referral; carrier-appetite.md suggests Carrier B. Matches gold.
  - R8: should not apply, because AG:39 says restaurants are a referral class, not an unlisted class.
- Verdict: CODE WRONG. Here the rule is clear on its own words: stated cooking equipment is evidence (R9) and it is in the operations text. The code only counts equipment through the extracted `cooking.equipment` state, which did not come out "yes", and the single operations answer has no listed generic word. No market was sent, but the file is told "no carrier list" when AG:39 says "referral".
- Fix: P-061 below. P-059 (T-106a) puts the "Cooking operations" and "Line of business" lines into the operations answer; that alone would probably give R9 a hit ("restaurant"). Re-check after P-059 before building P-061.

## SUB-186 Dos Rios Grill LLC

- Documents (typed PDF): Line of business "BOP - restaurant with bar". Operations (pipeline value) "Full-service grill, beer and wine only, 96 seats, two deep fryers, charbroiler, exhaust hood". Fire suppression yearly; hood inspected 2026-08-19. Unsprinklered, TIV 480,000, Laredo TX, expiring Carrier B.
- Pipeline route: hold (missing information, from the "liquor sales" ask-list), provisional no_match (R8).
- Gold route: senior_referral (R2), no suggested market.
- Rule by rule:
  - R5 hold: applies in the pipeline (open ask for liquor sales). The gold called the file complete; that is the status mismatch (class "check"), not the route.
  - W1/W1b: the bar word "bar" appears only in the line of business ("restaurant with bar"). "Beer and wine only" is not a bar word. W2d liquor: "liquor" is not in the text, so it does not fire.
  - R9: deep fryers and a charbroiler are stated cooking equipment, so restaurant evidence exists in the operations text itself. "Full-service grill" is not a listed word. The line of business has "restaurant".
  - R10 gives senior_referral, Carrier B suggested if no bar word is read. R2 gives senior_referral, no market, never confirmable, if the bar word is read.
  - R8: should not apply.
- Verdict: CODE WRONG on the route. Both readings (R10 or R2) are senior_referral; no_match is wrong under either. The suggested market differs (gold: none, because of R2), which only matters if the line of business is read. Same fix as 182.
- Note: the provisional route does not matter for a held file's send gates (all shut), but the card shows a plain wrong class to the underwriter.

## SUB-201 Velvet Room Lounge LLC

- Documents: Line of business "Liquor liability and BOP - nightclub". Operations "Nightclub and lounge, capacity 260, DJ and live music Thu-Sat until 2 a.m. Full liquor bar. Small kitchen, pre-packaged snacks only." Cooking operations "Snack warmer". Loss run: Brazos table, open claim, no valued date. Joisted masonry, TIV 520,000, Houston TX.
- Pipeline route: hold (missing information), provisional senior_referral, "possible bar/liquor exposure (R2; AG:46, AG:39)".
- Gold route: no_match (R1; W1; AG:45-50).
- Rule by rule:
  - R5 hold: applies (open claim detail, loss run format). Gold also incomplete. Agrees.
  - W1 list contains nightclub, nightclubs, lounge, lounges, and "bar" is in operations ("full liquor bar"). W1 says no_match, never overridable.
  - W1b lists the same words (bar, nightclub, lounge, pub...) and says: with restaurant evidence the route is R2, senior_referral, never a market confirm.
  - R9: "kitchen" is on the generic list. "Small kitchen" is in the operations text. "Pre-packaged snacks only" is not a listed negation. So restaurant evidence is present on the words.
  - Order of checks says W1 before W1b-style referral words. The two tables overlap, and the text does not say which wins when a W1 bar word has R9 evidence. The code applies W1b (D-079, B-290: "a bar word with restaurant evidence is a person's call").
  - R16: not reached.
- Verdict: GOLD WRONG under the rules as written. The gold applied R1 without running the W1b/R9 check, which gives R2 for this wording; the pipeline did what D-079 and carrier-match.md R2 say. But the written rule is also defective: it lets "a small kitchen with snacks only" in a nightclub count as restaurant evidence. My business intent is that a nightclub or lounge whose food is snacks only is a prohibited class (AG:46 lists nightclubs and lounges outright), so the outcome I want is the gold's. Safety is the same in both: neither route can reach a carrier, R2 cannot be market-confirmed, and only a person declines.
- Not a missed detection: the extraction miss on this file ("snack warmer") is P-059's and is not a route item.

## Proposals (drafted, not built, not recorded in team/)

Next free number after P-060 is P-061.

**P-061 Class words are read from the application's class lines (SUB-174, 182, 186).**
- Change: `_match()` also reads the application's "Line of business:" and "Cooking operations:" lines (the text of those lines, not the insured's name) for R9, R10, R14 and W1b words, and counts stated cooking equipment in the operations answer or the "Cooking operations" line as R9 evidence. R17 keeps reading the operations text only.
- Why: AG:29 and AG:39 are about the class; the application states the class on its line of business. A file that says "restaurant" must never go to "no carrier list".
- What happens when it is wrong: a word on the line of business could pull a file into a class it does not belong to. The result is still senior_referral or no_match, never a send. A carrier_a route would still need every operations word on the R17 list. Risk: low.
- Expected effect on T-104 scores: 174, 182, 186 route would become senior_referral (186 likely R2 with the bar word). Scores for T-104 stay as published; this is for a future set (do not re-score).
- Order: check after P-059 lands. If P-059 puts the line of business into the operations answer and the three files then route right on a replay, P-061 is not needed. Only the model-input route is different; P-061 removes the dependence on one model answer.
- Needs: my decision on the 174 reading (see below), @compliance not needed (no new words), @model-risk check as with P-051/P-053.

**P-062 Nightclub and lounge are never softened by snack-only food (SUB-201).**
- Change: (a) nightclub, nightclubs, lounge, lounges, hookah, adult entertainment, cannabis words stay R1 even with R9 evidence; R2 stays for bar, bars, tavern, pub, pubs beside real restaurant evidence. (b) "pre-packaged snacks only", "snack warmer" and "snacks only" are listed negations for R9, so they are not restaurant evidence. (c) carrier-match.md: W1 and W1b tables rewritten so the two lists no longer overlap.
- What happens when it is wrong: a restaurant described as "bar and lounge" with real cooking would still have the cooking word, so (a) would have to be tested on "restaurant and lounge" cases first; this is the real risk. R1 is a recommendation only, a person declines.
- Needs: my decision (below), @senior-underwriter review of the "lounge" case, @compliance read as for the W1 list.

## Decisions owed (mine, not recorded here)

1. Do class words come from the line of business as well as operations? My recommendation: yes (P-061). That makes SUB-174 "code wrong" and gives the gold route; it also makes SUB-182 and SUB-186 the same fix.
2. Nightclub or lounge with snack-only food: R1. I want this. It needs the W1/W1b rewrite in P-062 before the gold counts as right.
Both go to `team/DECISIONS.md` only when @user types the approve line for P-061 and P-062; I did not write either.

## Gold lessons for future sets

1. Write the source line for every route word. SUB-174, 182 and 186 gold use the line of business or the name (e.g. "the word office sits only in the name and line of business") but route as if the operations answer carried it. Gold must say "route word X is on the Y line" and, if the rule does not read that line, expect the code's route.
2. Run the whole order of checks, not only the class. SUB-201 gold stopped at W1 and never ran W1b and R9 ("kitchen"). For any file with a bar word, check every R9 word in the file and write R2 or R1 by the written rule.
3. Do not write a route from AG intent when the code reads word lists. If gold wants the intent route, note it as "intent: X; word-list: Y" so the scorer can tell a rule gap from a code miss.
4. Do not use "no suggested market" as a route mark unless the R2 bar word is in the text the code reads (SUB-186).
5. Where a rule is unclear, the gold writes "rule unclear" and the file is excluded from the route gate until I rule, instead of choosing one reading.

## Not changed

T-104 scores (16/20, gate FAIL), scorer v6, gold, code, team/ files: untouched. No commit.
