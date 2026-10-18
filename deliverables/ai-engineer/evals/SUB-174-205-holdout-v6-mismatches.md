# T-104 SUB-174 to SUB-205: gold vs pipeline, as-is

- Source: the live run's saved replies (run 20261017T200158-46947, cache `underwriting_pipeline/cache/T-104-live`), replayed from a temp copy of the cache with the model call blocked: 0 model calls, nothing in the repo written by the replay. The replay's marks equal the score file's marks for all 20 in-scope files. Code 6e7cfa2, scorer v6, gold 3678c0f.
- Scores are in `SUB-174-205-holdout-v6.md/.json`; that file governs. This file gives a class per mark and nothing more.
- Every non-hit mark of the 20 in-scope files: 38 in all. The 12 out-of-scope files have none (all 12 detected, 0 leaks). Call failed: 0.
- Classes: extraction, prompt, check, OCR, scorer, gold convention, routing rule. One primary class per mark; a second cause is written in the line.
- No fix is suggested or made here, apart from one "candidate backlog" line per class at the end.

## Class counts (38 marks)

| Class | Marks | Where |
|---|---|---|
| gold convention | 17 | loss_runs 8, status 6, conflict 2, sales 1 |
| extraction | 8 | operations 8 |
| scorer | 5 | loss_runs not credited 3, status 2 |
| check | 4 | conflict 3, status 1 |
| routing rule | 4 | route 4 |
| prompt | 0 | |
| OCR | 0 | |

## Operations (8 miss). Class: extraction

Gold "Operations items" are taken from the whole application (operations-gold-rule.md: record an item when the documents state it). The pipeline value is the text of the application's "Operations:" line; the missing items sit in the sibling lines "Cooking operations:", "Hood & extinguishing system last inspected:" or "Line of business:". Silent errors (wrong and not flagged) are SUB-180, SUB-201, SUB-204.

- SUB-175 miss. Gold: bakery and cafe; 24 seats; deck ovens; convection oven; espresso; lunch sandwiches; no fryer; no beer or wine; no liquor; hood and extinguishing system inspected 2026-08-12. Pipeline (flagged "operations may be missing: liquor"): "Bakery and cafe, seating 24, bakery deck ovens, espresso, lunch sandwiches. No fryer. No beer or wine." Missing: convection oven, no liquor, hood inspection, "24 seats". Source: "Cooking operations: Deck ovens, convection oven, espresso machine"; "Line of business: BOP - bakery/cafe, no liquor"; "Hood & extinguishing system last inspected: 2026-08-12 (semi-annual service)". Why: the model copied the Operations line. Second cause: "seating 24" is not "24 seats" to the item rule.
- SUB-177 miss. Gold: corn masa and tortilla production; retail counter sales; tortilla press; comal; gas-fired masa mill; no deep fryer; no liquor. Pipeline (flagged "may be missing: liquor, on-site processing"): "Corn masa and tortilla production, retail counter sales. Tortilla press, comal, no deep fryer. Sells chips bought in." Source: "Cooking operations: Comal, tortilla press, gas-fired masa mill"; "Line of business: BOP - food manufacturing/retail (no liquor)". Why: items stated in the cooking and line-of-business lines were not carried over.
- SUB-180 miss (silent). Gold: pottery studio and gallery; two electric kilns; class sessions for adults and kids; retail sales of finished work; no gas. Pipeline (not flagged): "Pottery studio and gallery. Two electric kilns (240V), class sessions for adults and kids, retail sales of finished work." Source: "Cooking operations: Two electric kilns, no gas". Why: "no gas" is in the cooking line only.
- SUB-182 miss. Gold: sub shop; cold cuts; hot sandwiches; flat-top grill; two convection ovens; no fryer; no liquor; hood and extinguishing system inspected 2026-07-28. Pipeline (flagged "may be missing: liquor"): "Sub shop, cold cuts, hot sandwiches on flat-top grill, convection ovens. No fryer, no hood suppression unknown." Source: "Cooking operations: Flat-top grill, two convection ovens"; "Line of business: BOP - restaurant (quick service, no liquor)"; "Hood & extinguishing system last inspected: 2026-07-28". Why: "two", "no liquor" and the hood date are in other lines; the garbled sentence is the application's own.
- SUB-186 miss. Gold: restaurant with bar; full-service grill; beer and wine only; 96 seats; two deep fryers; charbroiler; exhaust hood; fire suppression service yearly; hood inspected 2026-08-19. Pipeline (flagged "may be missing: bar"): "Full-service grill, beer and wine only, 96 seats, two deep fryers, charbroiler, exhaust hood". Source (typed PDF): "Line of business: BOP - restaurant with bar"; "fryers, charbroiler, exhaust hood (fire suppression service yearly)."; "Hood & extinguishing system last inspected: 2026-08-19". Why: the parenthetical, the line of business and the hood line were left out.
- SUB-201 miss (silent). Gold: nightclub and lounge; capacity 260; full liquor bar; DJ and live music Thu-Sat; until 2 a.m.; pre-packaged snacks only; snack warmer. Pipeline (not flagged): "Nightclub and lounge, capacity 260, DJ and live music Thu-Sat until 2 a.m. Full liquor bar. Small kitchen, pre-packaged snacks only." Source: "Cooking operations: Snack warmer". Why: "snack warmer" is in the cooking line only. Second cause (scorer): "until 2 a.m." is in the pipeline value but the clause rule cuts at the periods in "a.m.", so it also reads as missing.
- SUB-203 miss. Gold: coffee roasting; 15 kg gas drum roaster; afterburner; retail cafe; 18 seats; wholesale bags; espresso bar; hood inspected 2026-09-10. Pipeline (flagged "may be missing: bar"): "Coffee roasting (15 kg gas drum roaster, afterburner), retail cafe with 18 seats, wholesale bags". Source: "Cooking operations: 15 kg gas drum roaster, afterburner, espresso bar"; "Hood & extinguishing system last inspected: 2026-09-10". Why: espresso bar and hood date are in other lines.
- SUB-204 miss (silent). Gold: pool chemicals; pumps; patio furniture; warehouse and showroom; forklift x2; no cooking. Pipeline (not flagged): "Pool chemicals (non-hazmat bagged), pumps, patio furniture. Warehouse and showroom. Forklift x2. Forklifts electric and LPG." Source: "Cooking operations: None. Forklifts electric and LPG." Why: "no cooking" is stated only in the cooking line.

## Sales (1 miss). Class: gold convention

- SUB-204 miss. Gold: "1100000 (application); 940000 per the email, unconfirmed". Pipeline: "1100000", flagged "conflict with rejected value: "1100000" (application.md); "940000" (email.md)". Source: "Annual sales: $1,100,000"; email "$940K is the number they told me on the phone, not sure." Why: the pipeline value equals the application figure and is flagged; the scorer compares the digits of the whole gold line (1100000940000), so a gold line that holds both figures cannot match.

## Loss runs (8 miss, 3 not credited)

Eight misses. Class: gold convention. Each gold "Loss runs" line describes the typed table and does not start with "missing", so the scorer treats a null as a miss. The gold "Expected loss run" line for each reads "needs review — not a recognised carrier loss run", and the pipeline returned no date with needs_review true, which is what that line expects. Each table has no valued-as-of date.

- SUB-177: gold "typed Redbud Mutual table RBM-22987, three terms 2024-2026, 'No losses' each; no insured line, no valued-as-of date; not a carrier A, B or C layout". Pipeline: none, needs review. Source: "| 2024 | Redbud Mutual | RBM-22987 | No losses | - | $0 | Closed |".
- SUB-178: gold "typed Brazos Surplus table BS-7714, three terms 2024-2026, no losses; no insured line, no valued-as-of date". Pipeline: none, needs review. Source: "| 2024 | Brazos Surplus | BS-7714 | No losses | - | $0 | Closed |".
- SUB-181: gold "typed Redbud Mutual table RBM-44910, terms 2023, 2024, 2025; one claim 2023; no valued-as-of date". Pipeline: none, needs review. Source: "| 2023 | Redbud Mutual | RBM-44910 | Customer vehicle | 03/04/23 | $2,100 | Closed |".
- SUB-200: gold "typed Redbud Mutual table RBM-63310, three terms 2024-2026, no losses; no valued-as-of date". Pipeline: none, needs review. Source: "| 2024 | Redbud Mutual | RBM-63310 | No losses | - | $0 | Closed |".
- SUB-201: gold "typed Brazos Surplus table BS-7790, two 2025 rows only (liquor liability); no valued-as-of date". Pipeline: none, needs review. Source: "| 2025 | Brazos Surplus | BS-7790 | Liquor liability | 06/21/25 | $12,000 | Closed |".
- SUB-202: gold "typed Caprock Specialty table CS-48312, three terms 2024-2026, no losses; no valued-as-of date". Pipeline: none, needs review. Source: "| 2024 | Caprock Specialty | CS-48312 | No losses | - | $0 | Closed |".
- SUB-203: gold "typed Redbud Mutual table RBM-38217, three terms 2024-2026, no losses; no valued-as-of date". Pipeline: none, needs review. Source: "| 2024 | Redbud Mutual | RBM-38217 | No losses | - | $0 | Closed |".
- SUB-204: gold "typed Brazos Surplus table BS-5520, three terms 2024-2026, no losses; no valued-as-of date". Pipeline: none, needs review. Source: "| 2024 | Brazos Surplus | BS-5520 | No losses | - | $0 | Closed |".

Three not credited. Class: scorer (by design: a null that matches a "missing" gold line is not a correct answer and not a miss). Pipeline: none, needs review, in each.

- SUB-176: gold "missing, only an owner's no-known-loss letter (not a loss run)". Source: "No known losses in the last 5 years for the named insured or its premises. Signed: Greenway Pet Grooming LLC (owner)".
- SUB-180: gold "missing, only an owner's no-known-loss letter (not a loss run); no prior commercial carrier". Source: "No known losses in the last 5 years ... Signed: Brazos Pottery Studio LLC (owner)".
- SUB-205: gold "missing, none provided (still coming from the old agent; expiring Redbud Mutual)". Source (email): "Loss runs are still coming from the old agent, I asked twice."

## Conflicts (5 miss)

- SUB-174 miss. Class: gold convention. Gold: "none in the extraction fields. The email says the insured has been 'with Redbud for years' while the application and the run say Carrier A (side remark; ask the producer)". Pipeline: no open conflict (right for the extraction fields). Source: email "they've been with Redbud for years." Why: the scorer treats any gold conflict line other than exactly "none" as a conflict to find; this line starts "none" and goes on.
- SUB-182 miss. Class: gold convention. Gold: "none. The operations sentence 'no hood suppression unknown' is garbled, but the application gives the hood inspection date 2026-07-28". Pipeline: no open conflict. Why: same as SUB-174.
- SUB-180 miss. Class: check. Gold: "the letter covers 5 years, years in business is 3". Pipeline: no conflict. Source: "Years in business: 3" against the letter "No known losses in the last 5 years". Why: nothing compares the years a no-loss letter covers with years in business.
- SUB-203 miss. Class: check. Gold: "square footage: 3200 (application) vs 2850 (schedule)". Pipeline: no conflict. Source: application "Square footage: 3,200"; schedule.csv sq_ft "2850". Why: square footage is not among the pipeline's fields, so the two figures are never compared.
- SUB-204 miss. Class: check. Gold: "sales: 1100000 (application) vs 940000 (email, by phone, producer unsure)". Pipeline: conflicts list empty; the sales field is flagged with both figures in its reason (see Sales). Why: the pipeline records this as a flag on the field, not as an open conflict; the scorer reads only open conflicts. The status (incomplete, hold) matches gold.

## Status (9 miss: the 9 gold-complete files)

All 9 gold-complete files miss. The scorer's status mark is a hit only when the report's `complete` flag matches gold's, and `complete` is false for "complete — review pending".

- SUB-174 miss. Class: scorer. Gold "complete — review pending (Carrier A run read from a scan)", expected pipeline status "complete — review pending". Pipeline: "complete — review pending". Same text; the boolean in the mark is false. Flag: loss run read from a scan (loss-runs_scan.jpg).
- SUB-175 miss. Class: scorer. Gold "complete — review pending (Carrier B run read from a scan)". Pipeline: "complete — review pending". Same as SUB-174.
- SUB-179 miss. Class: gold convention. Gold "complete". Pipeline "complete — review pending": "valued-as-of date 2026-11-17 in loss-runs.md is not a real past date; check it". Source: "Valued as of: 2026-11-17". The gold date is after the run date (2026-10-17); the check fires as written.
- SUB-183 miss. Class: gold convention. Gold "complete". Pipeline "complete — review pending": same date flag, 2027-06-17.
- SUB-184 miss. Class: gold convention. Gold "complete". Pipeline "complete — review pending": same date flag, 2027-02-15.
- SUB-182 miss. Class: gold convention. Gold "complete". Pipeline "complete — review pending": date flag 2027-01-29, and operations flag "may be missing: liquor". Second cause: the operations flag (the line of business says "no liquor").
- SUB-185 miss. Class: gold convention. Gold "complete". Pipeline "complete — review pending": date flag 2027-07-18, and operations flag "may be missing: 6 units". Second cause: the operations flag.
- SUB-187 miss. Class: gold convention. Gold "complete". Pipeline "complete — review pending": date flag 2027-03-17, and operations flag "may be missing: 7 units". Second cause: the operations flag.
- SUB-186 miss. Class: check. Gold "complete". Pipeline "incomplete" with an empty missing list: the restaurant ask-list ("extra") holds "liquor sales" because the word "liquor" is not in the file's text; the application says "beer and wine only". Also flagged: date 2027-05-01 and "operations may be missing: bar". A producer request would be drafted for liquor sales.

## Route (4 miss). Class: routing rule for all four. None is unsafe (no carrier route).

- SUB-174 miss. Gold "senior_referral, suggested market carrier_a" (executive suites with 6 tenants is an office lessor, AG:29). Pipeline route: no_match, note "readable class on no carrier list (R8; KO 8); a restaurant needs generic evidence ...". Source: "Operations: Leased executive suites (6 tenants), reception desk, shared conference room. No cooking."; "Line of business: Commercial property, general liability - office". Why: the class is not matched to the office-lessor list.
- SUB-182 miss. Gold "senior_referral, suggested market carrier_b" (sub shop with stated flat-top and ovens: restaurant evidence, R9/R10). Pipeline: no_match, same R8 note. Source: "Sub shop, cold cuts, hot sandwiches on flat-top grill, convection ovens"; "Line of business: BOP - restaurant (quick service, no liquor)". Why: restaurant evidence not recognised for this wording.
- SUB-186 miss. Gold "senior_referral" (restaurant with a bar, R2; AG:46, AG:39). Pipeline: hold (missing information), provisional no_match with the same R8 note. Source: operations "Full-service grill, beer and wine only, 96 seats"; typed PDF "Line of business: BOP - restaurant with bar". Why: the provisional route does not read the restaurant and bar evidence. The hold itself comes from the Status entry above.
- SUB-201 miss. Gold "no_match" (nightclub, lounge, full liquor bar: R1, W1, AG:45-50). Pipeline: hold (missing information), provisional senior_referral, note "possible bar/liquor exposure — confirm liquor sales (R2; AG:46, AG:39)". Source: "Named insured: Velvet Room Lounge LLC"; "Line of business: Liquor liability and BOP - nightclub"; operations "Nightclub and lounge ... Full liquor bar". Why: the prohibited-class route (R1; W1) was not the one returned for the held file.

## Candidate backlog (one line per class; not decided, nothing changed)

- gold convention: align gold wording with the scorer's reading for the next hold-out gold (conflict line exactly "none", loss-run line starting "missing" or a date, one figure in the sales line, valued-as-of dates not after the run date); published gold is not rewritten.
- extraction: operations value built from the cooking, hood and line-of-business lines as well as the "Operations:" line.
- scorer: status mark reading "complete — review pending" as a match when gold says it; the ops clause rule splitting "a.m."; frozen, not edited.
- check: no-loss-letter years vs years in business; square footage vs schedule; field-level conflict flag vs open-conflict entry; restaurant "liquor sales" ask when beer and wine is stated.
- routing rule: office lessor wording (executive suites); sub shop restaurant evidence; restaurant with bar under hold; prohibited-class (R1; W1) for a held file.
- prompt, OCR: no marks.
