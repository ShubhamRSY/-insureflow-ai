# T-119 gold summary — SUB-340 to SUB-371
- Owner: @senior-underwriter · Gold written by hand before any run, from the documents and the written rules only (carrier-match.md incl. D-125, operations-gold-rule.md, the T-117 scope criteria, required-fields.md). No pipeline, model, scorer, lint or extraction output was run or read. The four scans (SUB-360, 361, 368, 370) were read by eye from the images. Nothing reused from an earlier set.
- Cards: `deliverables/senior-underwriter/gold-set/SUB-340.md` to `SUB-371.md` (32). Routes: `T-119-routes.md`. Same card format as T-117.
- Out-of-scope cards carry the `- Scope:` line and `- Status: manual intake` only.

## Counts
- In scope 20 (SUB-340-359); out of scope 12 (SUB-360-371).
- Criteria: 1 = 4 (360, 361, 368, 370); 2 = 5 (362, 363, 368, 369, 371); 3 = 4 (364, 365, 369, 370); 4 = 3 (366, 367, 371). Two criteria: 4 (368 = 1+2; 369 = 2+3; 370 = 1+3; 371 = 4+2). Alone: 360, 361, 362, 363, 364, 365, 366, 367. Same as the mix.
- Routes (in scope): carrier_a 4, senior_referral 12 (suggested carrier_b 5, carrier_a 4, carrier_c 2, none 1), no_match 4, hold 0. Status: complete 13, incomplete 7.
- Loss-run lines: dated and recognised 18 (valued-as-of line present); no valued line 2: owner letter 350 (dated 2026-09-29, not a run), no run 359. Latest valued date 2026-09-18 (SUB-347).
- Planted conflicts (open, both sides, status incomplete): 344 square footage 3200 vs 2450; 345 sales 1240000 vs 1420000; 346 suites 8 vs 9; cooking 348 and 349 (below).
- Direct Carrier A routes: 4 (340-343), above the required 3.
- Pub case: SUB-352, rule A (D-125): senior_referral R2, no suggested market, never confirmable; not R1 although offices are a second operation.
- Prohibited class: 353 (lounge), 354 (nightclub, full bar), 355 (hookah lounge) all no_match R1.

## Cooking cases (D-124, D-127), listed separately
- Gold says `no cooking` (an omitted cooking slot is a miss under v11): 340, 341, 342, 343, 344, 345, 346, 347, 350, 353 (also "no kitchen at all"), 354, 355, 358, 359. Fourteen files; all state "Cooking operations: None" and no other document contradicts it.
- Gold states cooking equipment: 351 (griddle, fryer, oven, hood with suppression), 352 (fryer, flat top, hood).
- Cooking in dispute, no cooking item scored, open conflict, hold: 348 (application None vs email stove top and flat grill) and 349 (application None vs schedule Yes vs email griddle). The route is R9/R10 either way ("deli"). These are the cases where the cooking line is stated in another document.
- Not scored: 356, 357 (tenant electric ranges only; same as T-117 SUB-245). 348 and 349 are the disputed cases (above). 
- Out of scope, not carded: 369 (ovens in the Harlingen store).

## Mismatches with the producer's mix (documents and rules win)
1. SUB-344: the mix lists the operations as an electrical contractor with a conflict; confirmed. Gold carries one class (contractor); "office and shop" is premises, not a second operation.
2. SUB-358: the mix says light manufacturing. The documents say metal fabrication and never "manufacturing", so gold is R8 no_match (overridable), class other_class, as T-117 SUB-255; not senior_referral.
3. SUB-345 and SUB-350: wholesale never routes directly (R17/P-053); gold is senior_referral, Carrier A suggested.
4. SUB-346 and SUB-347: office lessors take R17 senior_referral, Carrier A suggested (T-117 H1 reading), not a direct route.
5. SUB-348 and SUB-349: the mix calls these deli conflicts; confirmed and written as open cooking conflicts with all sides; no cooking item.
6. SUB-352: the mix says pub case; gold R2 per D-125.
7. SUB-355: the mix says prohibited; gold carries two classes (hookah and lounge) because both words are stated.
8. SUB-359 and SUB-350: confirmed (no run; owner letter). 350 has no valued-as-of line.
9. SUB-363: the application lists one address; the second location is in the email and in a schedule row marked source "email". Gold still treats this as criterion 2.
10. SUB-371: the mix says criteria 2 and 4. With no application the "two locations" come from the email's two yards; gold keeps both codes.

## Judgment calls to check
- SUB-340-343: carrier_a rests on the operations value only; email goods words (fabric, notions, work wear, donations) could be cited into the operations text and fail the R17 reading (see T-119-routes.md call 1). The test of direct routes is real only if the pipeline's operations text stays the application value.
- SUB-348, SUB-349: cooking left out of items rather than choosing a side; the alternative (take the email's stove top and flat grill as cooking=full, open_flame yes) is a possible later fix if @head-of-underwriting wants a conflict to still score a side.
- SUB-350: "plumbing" is a goods word here (R11 word list); see routes call 2.
- SUB-349: "bar" appears in the insured name and as "sandwich and soup bar" in the email (M6 food counter); gold route is R10, not R2. A word reader that counts it is a fail-closed manual-review miss, not a gold error.
- SUB-351, SUB-353, SUB-354: hours written only as "opens at 6", "till 2", "until 2" with no meridiem; no hours item (a guessed am or pm would be inferred).
- SUB-355: "open to 1 am" carried as an hours item in the documents' form.
- Restaurants are "complete" when the pipeline-held fields are present (T-108 reading); inspection date and closing hour are asks, not holds.
- Loss runs of one policy term are accepted as recognised layouts (as T-117); policy period end dates after the run date are period dates, not valued dates.
- Lint caution (T-117 lesson): no class word sits in a non-class item; kitchen, bar, restaurant and similar words are in notes only. Items hold only `business_type=`, alcohol, seats, units, cooking equipment, hood, entertainment, hours and `no cooking`.

## Lint fixes (T-119 lint 2026-10-23, gold only)
- SUB-348 Conflict: "cooking: none (application, 'Cooking operations: None') vs stove top and flat grill (email, hot food all day)" -> "cooking: none (application, 1900 sq ft counter deli) vs stove top and flat grill (email, hot food all day)". Why: (1) no figure, so v11 sides_stored had no needle (conflict miss); a figure from the application (1900 sq ft) is now the needle. (2) The word "operations" in the line made the lint's perfect answer treat the operations field as flagged by the conflict and blank it (operations miss); the quoted application label is dropped. The notes line still carries the quote (unscored). Documents unchanged in meaning.
- SUB-349 Conflict: "cooking: none (application) vs yes (schedule) and griddle (email)" -> "cooking: none (application, 1700 sq ft counter deli) vs yes (schedule) and griddle (email)". Why: no figure, so no needle (conflict miss); 1700 sq ft is from the application.
- Both: conflict still open, status incomplete, route senior_referral. No other card changed. T-119-routes.md unchanged (no route change). Note for the AI Engineer: the needle is a square-footage figure the scorer requires, not something the pipeline is likely to quote; a conflict miss on these two may be a scorer artefact (H1 backlog).

## D-128 fixes (2026-10-23, gold only)
- SUB-348 Conflict: "cooking: none (application, 1900 sq ft counter deli) vs stove top and flat grill (email, hot food all day)" -> "cooking: none (application) vs stove top and flat grill (email, hot food all day)". Why: true two-sided line restored as the documents state it; the added square-footage figure is removed; the word "operations" stays out of the line so the lint's perfect answer does not blank the operations field. Status, hold, route unchanged.
- SUB-349 Conflict: "cooking: none (application, 1700 sq ft counter deli) vs yes (schedule) and griddle (email)" -> "cooking: none (application) vs yes (schedule) and griddle (email)". Same reasons. Status, hold, route unchanged.
- Under v11 these two conflict marks can't be measured; they are reported separately and excluded from the conflict rate. Noted before the run.
- SUB-344 Conflict: "square footage: 3200 (application) vs 2450 (schedule, appraisal 2025; the email says the application number came off the old lease)" -> "square footage: 3200 (application) vs 2450 (schedule)". Why: "2025" (and "appraisal") were required matches; moved to a new Notes line. Both square-footage sides unchanged.
- SUB-344 added to the no-cooking list (now 14 files): card says "cooking none", no document contradicts it.
