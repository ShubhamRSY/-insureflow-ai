# T-103 root cause (SUB-154 to SUB-173), D-102 item 1

- Author: @ai-engineer-assistant, 2026-10-16. Analysis only. No code, prompt, gold, scorer or score file was changed. 0 model calls.
- Method: the 20 saved replies of live run 20261016T151351-65695 (`underwriting_pipeline/cache/extractions/`) were copied to a temp folder, the model call was blocked, and the pipeline (commit 2c6b2d9, pipeline 3557e4a) was replayed on `simulation/inbox/SUB-154` to `SUB-173`. Nothing was written to the repo (git status afterwards showed only the two files changed earlier today by others). The replay reproduces the published status and route marks.
- Dev comparison: `deliverables/ai-engineer/evals/P-054-dev/SUB-127-146-dev-v4-cache-rescore.json` (v4, commit b007002, operations 19 hit, 1 miss). The older `SUB-127-146-holdout.json` (T-027, v2) shows 12/20 and is not the 19/20.
- Classes, one per mark: extraction (the model read the document wrongly), prompt, check (a gate or rule in the pipeline), OCR (the scan text), scorer (the frozen v4 comparison), gold convention (how the gold line is written).
- Headline: no mark is the model reading a document wrongly. Of 49 non-hit marks (not credited excluded): 13 OCR, 12 check, 5 scorer, 19 gold convention, 0 extraction, 0 prompt.

## (a) Operations: 19/20 on dev, 7/20 on T-103

### Where P-047 stands
P-047 (`check_operations`, prepare.py:868-884) takes the cited source line (plus labeled lines of the same file that carry a rule word) and flags the answer when a word from a closed list of 15 items (liquor, beer, wine, alcohol, bar, stories or floor, music, hours, frying, cooking, delivery, processing, patio, security, hazardous; `OPS_ITEMS`, prepare.py:811-826) or a count (seats, units) is in the source and not in the answer. It never sees the gold, never reads a file other than the cited one, and does nothing on an empty value. In T-103 it flagged 0 of 20 files (no reason in any row contains "operations may be missing"). Seven of the 13 misses are flagged or empty (158, 160, 163, 167, 169, 170, 172); they were flagged by other gates (below), not by P-047.

### The 13 misses and the 6 silent errors
Silent errors (a value is shown, v4 calls it wrong, nothing is flagged): SUB-156, 157, 159, 165, 171, 173.

#### SUB-156 operations — class: scorer
- Source: `application.md: Operations: Restaurant. Breakfast and lunch counter service, 48 seats, dine-in and takeout. No alcohol of any kind.`
- Source: `application.md: Cooking operations: Flat-top, 2 fryers, 4-burner range, Type I hood with UL 300 suppression, hood cleaned 2026-07`
- Extracted (full): "Restaurant. Breakfast and lunch counter service, 48 seats, dine-in and takeout. No alcohol of any kind. Cooking operations: Flat-top, 2 fryers, 4-burner range, Type I hood with UL 300 suppression, hood cleaned 2026-07"
- Pipeline flag: needs_review=False, reason=None, confidence=1.0
- Gold: "Restaurant, no alcohol of any kind, 48 seats, flat-top, 2 fryers and 4-burner range under Type I hood with UL 300 suppression, breakfast and lunch counter service, dine-in and takeout"
- Why P-047 did not flag it: P-047 compares the source line with the answer, never with gold. The answer carries every item of the source (restaurant, no alcohol, 48 seats, hood, UL 300, fryers, counter service). The miss is the single gold word "under" ("under Type I hood"); the answer says "Type I hood with UL 300". Not flagged, so it is a silent error.

#### SUB-157 operations — class: scorer
- Source: `application.md: Operations: Restaurant and bar. Full liquor (TABC mixed beverage permit), 140 seats, live music Thursday to Sunday until midnight. Dinner service and weekend brunch.`
- Source: `application.md: Cooking operations: Charbroiler, 2 fryers, flat-top, 8-burner range, pizza oven. Type I hood with UL 300 system, serviced 2026-08.`
- Extracted (full): "Restaurant and bar. Full liquor (TABC mixed beverage permit), 140 seats, live music Thursday to Sunday until midnight. Dinner service and weekend brunch. Charbroiler, 2 fryers, flat-top, 8-burner range, pizza oven. Type I hood with UL 300 system, serviced 2026-08."
- Pipeline flag: needs_review=False, reason=None, confidence=0.95
- Gold: "Restaurant and bar, full liquor (TABC mixed beverage permit), 140 seats, charbroiler, 2 fryers, flat-top, 8-burner range and pizza oven under Type I hood with UL 300, live music Thursday to Sunday until midnight, dinner service and weekend brunch"
- Why P-047 did not flag it: Same: the answer holds liquor, 140 seats, live music, equipment, hood, UL 300, dinner, brunch. Only the gold connector "under" is absent. P-047 had nothing missing to report.

#### SUB-158 operations — class: gold convention
- Source: `application.md: Operations: Residential apartments, 16 units in two two-story buildings, long-term leases. Occupancy 93 percent.`
- Source: `application.md: Cooking operations: None (tenant electric ranges only)`
- Extracted (full): "Residential apartments, 16 units in two two-story buildings, long-term leases. Occupancy 93 percent. No cooking operations (tenant electric ranges only)."
- Pipeline flag: needs_review=True, reason='value is not in the cited text (translated or reworded)', confidence=0.95
- Gold: "Apartment building, 16 units in two two-story buildings, long-term leases, no cooking operations (tenant electric ranges only)"
- Why P-047 did not flag it: Gold rewrites the document's "Residential apartments" as "Apartment building"; the answer has the document's words, so "apartment" and "building" are not in it. It is flagged (see below), so not silent.

#### SUB-159 operations — class: scorer
- Source: `application.md: Operations: Bakery and cafe. Pastries, sandwiches, coffee. 30 seats, dine-in and takeout. No alcohol sold.`
- Source: `application.md: Cooking operations: Deck oven, 2 convection ovens, 4-burner range, flat-top, Type I hood with UL 300`
- Extracted (full): "Bakery and cafe. Pastries, sandwiches, coffee. 30 seats, dine-in and takeout. No alcohol sold. Deck oven, 2 convection ovens, 4-burner range, flat-top, Type I hood with UL 300"
- Pipeline flag: needs_review=False, reason=None, confidence=0.95
- Gold: "Bakery and cafe (pastries, sandwiches, coffee), no alcohol sold, 30 seats, deck oven, 2 convection ovens, 4-burner range and flat-top under Type I hood with UL 300, dine-in and takeout"
- Why P-047 did not flag it: Same "under Type I hood" connector. The answer has the deck oven, 2 convection ovens, 4-burner range, flat-top, hood, UL 300, 30 seats, no alcohol. Not flagged: silent.

#### SUB-160 operations — class: gold convention
- Source: `application.md: Operations: Residential apartments, 8 units in two two-story buildings, long-term leases. Occupancy 88 percent.`
- Source: `application.md: Cooking operations: None (tenant electric ranges only)`
- Extracted (full): "Residential apartments, 8 units in two two-story buildings, long-term leases. Occupancy 88 percent. No cooking operations (tenant electric ranges only)."
- Pipeline flag: needs_review=True, reason='value is not in the cited text (translated or reworded)', confidence=0.95
- Gold: "Apartment building, 8 units in two two-story buildings, long-term leases, no cooking operations (tenant electric ranges only)"
- Why P-047 did not flag it: Same as 158: "Apartment building" vs the document's "Residential apartments". Flagged, not silent.

#### SUB-163 operations — class: check
- Source: `application.md: Operaciones: Restaurante familiar de cocina mexicana. 60 asientos, cerveza y vino, sin barra. Servicio en mesa y para llevar.`
- Source: `application.md: Operaciones de cocina: Comal, parrilla, 2 freidoras, estufa de 6 quemadores. Campana tipo I con sistema UL 300, limpieza 2026-06.`
- Extracted (full): "null (empty)"
- Pipeline flag: needs_review=True, reason=None, confidence=0.0
- Gold: "Mexican restaurant, beer and wine only, no bar, 60 seats, comal, grill, 2 fryers and 6-burner range under Type I hood with UL 300, table service and takeout"
- Why P-047 did not flag it: Spanish application. The model returned an English value and a quote with a literal " ... " joining two non-adjacent lines. accept_field (llm_extract.py:417) finds no such substring: "quote not found in application.md", confidence 0.0, value dropped (the \n split of P-048(d), llm_extract.py:463, does not split on an ellipsis). check_operations returns at once on an empty value (prepare.py:872). Operations ends null and the file is held.

#### SUB-165 operations — class: gold convention
- Source: `application.md: Operations: Retail sale of consumer fireworks (aerial, ground and cakes), storefront and seasonal tent. Fireworks inventory stored on premises, including in a trailer on the lot.`
- Source: `application.md: Cooking operations: None`
- Extracted (full): "Retail sale of consumer fireworks (aerial, ground and cakes), storefront and seasonal tent. Fireworks inventory stored on premises, including in a trailer on the lot."
- Pipeline flag: needs_review=False, reason=None, confidence=1.0
- Gold: "Retail sale of consumer fireworks (aerial, ground and cakes), storefront and seasonal tent (June and July), fireworks inventory stored on premises including in a trailer on the lot"
- Why P-047 did not flag it: "(June and July)" is in the producer's email only ("seasonal tent June and July"); the application's operations line says "seasonal tent" without months. P-047 reads the cited file (application.md) plus labeled lines of that file (prepare.py:868-884) and never email.md; OPS_ITEMS has no season or month item (prepare.py:811-826). The closed list of the gold rule does not contain "seasonal months" either, yet gold has them. Not flagged: silent.

#### SUB-167 operations — class: gold convention
- Source: `application.md: Operations: Residential apartments, 24 units in three two-story buildings, long-term leases. Occupancy 90 percent.`
- Source: `application.md: Cooking operations: None (tenant electric ranges only)`
- Extracted (full): "Residential apartments, 24 units in three two-story buildings, long-term leases. Occupancy 90 percent. No cooking operations (tenant electric ranges only)."
- Pipeline flag: needs_review=True, reason='value is not in the cited text (translated or reworded)', confidence=0.95
- Gold: "Apartment building, 24 units in three two-story buildings, long-term leases, no cooking operations (tenant electric ranges only)"
- Why P-047 did not flag it: Same as 158: "Apartment building" vs "Residential apartments". Flagged, not silent.

#### SUB-169 operations — class: gold convention
- Extracted (full): "Self-service laundry with 14 washers and 8 gas dryers; customers wash their own clothes; no commercial ironing; no delivery service"
- Pipeline flag: needs_review=True, reason='value is not in the cited text (translated or reworded)', confidence=0.95
- Gold: "Self-service laundromat, 14 washers and 8 gas dryers, customers wash their own clothes, no commercial pressing, no delivery service"
- Why P-047 did not flag it: Spanish email. The model translated "lavanderia de autoservicio" as "Self-service laundry" and "planchado" as "ironing"; gold chose "laundromat" and "pressing". Both are translations, not document words. Flagged (translated), not silent. OPS_ITEMS covers the email's items (delivery is carried); nothing missing.

#### SUB-170 operations — class: OCR
- Source (OCR text, as read): application.jpg OCR text: operations: pestaurant: 2 jocations- Burgers. chicke® and preakfast gine-it and / takeout: Beer and wine, no Liquor License: / cooking operations ' Flat-teP: 2 fryerse charbroiler: g-purner range: TYpe sis nood / with gL 300 at poth yocations:
- Source (by eye, gold): the typed form says: Operations: Restaurant, 2 locations, burgers, chicken and breakfast, dine-in and takeout, beer and wine, no liquor license; Cooking operations: flat-top, 2 fryers, charbroiler, 8-burner range, Type I hood with UL 300 at both locations.
- Extracted (full): "null (empty)"
- Pipeline flag: needs_review=True, reason=None, confidence=0.0
- Gold: "Restaurant, 2 locations, burgers, chicken and breakfast, beer and wine only (no liquor license), flat-top, 2 fryers, charbroiler and 8-burner range under Type I hood with UL 300 at both locations, dine-in and takeout"
- Why P-047 did not flag it: Value is empty, so check_operations does nothing (prepare.py:872). The values were lost earlier, see (b): the word "takeout:" scored 0.29 in the OCR word list, under SCAN_FLOOR 0.50, so accept_field dropped operations (llm_extract.py:455-458).

#### SUB-171 operations — class: scorer
- Source: `application.md: Operations: Restaurant and bar. Full liquor (TABC mixed beverage permit), 140 seats, live music Thursday to Sunday until midnight. Dinner service and weekend brunch.`
- Source: `application.md: Cooking operations: Charbroiler, 2 fryers, flat-top, 8-burner range, pizza oven. Type I hood with UL 300 system, serviced 2026-08.`
- Extracted (full): "Restaurant and bar. Full liquor (TABC mixed beverage permit), 140 seats, live music Thursday to Sunday until midnight. Dinner service and weekend brunch. Charbroiler, 2 fryers, flat-top, 8-burner range, pizza oven. Type I hood with UL 300 system, serviced 2026-08."
- Pipeline flag: needs_review=False, reason=None, confidence=1.0
- Gold: "Restaurant and bar, full liquor (TABC mixed beverage permit), 140 seats, charbroiler, 2 fryers, flat-top, 8-burner range and pizza oven under Type I hood with UL 300, live music Thursday to Sunday until midnight, dinner service and weekend brunch"
- Why P-047 did not flag it: SUB-171 is the same application text as SUB-157 (resent with a different file mix). Same "under" connector. Not flagged: silent.

#### SUB-172 operations — class: gold convention
- Source: `application.md: Operations: Residential apartments, 3 properties, 30 units total, long-term leases. Occupancy 95 percent.`
- Source: `application.md: Cooking operations: None (tenant electric ranges only)`
- Extracted (full): "Residential apartments, 3 properties, 30 units total, long-term leases. Occupancy 95 percent. No cooking operations (tenant electric ranges only). Sprinklers: Yes, NFPA 13 at all 3 locations. 2 stories all locations."
- Pipeline flag: needs_review=True, reason='value is not in the cited text (translated or reworded)', confidence=0.95
- Gold: "Apartment buildings, 3 properties, 30 units total, long-term leases, no cooking operations (tenant electric ranges only)"
- Why P-047 did not flag it: Same as 158: "Apartment buildings" vs "Residential apartments". Flagged, not silent. The answer also carries the sprinkler and stories lines because the model merged them in.

#### SUB-173 operations — class: gold convention
- Source: `application.md: Operations: Counter service. Tacos, burritos, quesadillas and agua fresca, 35 seats, dine-in and takeout. No liquor.`
- Source: `application.md: Cooking operations: not listed`
- Extracted (full): "Counter service. Tacos, burritos, quesadillas and agua fresca, 35 seats, dine-in and takeout. No liquor."
- Pipeline flag: needs_review=False, reason=None, confidence=1.0
- Gold: "Counter service taqueria (tacos, burritos, quesadillas, agua fresca), no liquor, 35 seats, dine-in and takeout"
- Why P-047 did not flag it: Gold adds the business word "taqueria" (from the insured's name and the email: "our taqueria"); the application's operations line is "Counter service. Tacos, burritos, ...". Nothing in a source operations line is dropped. Not flagged: silent.

### Why 19/20 on dev and 7/20 on T-103
The inputs are the same kinds of file (typed application, email, loss runs, schedule), the same pipeline and the same model. The difference is the gold, the scorer and, for scans, the picture quality.

1. **The v4 operations rule is "every gold word (4 letters or more, or a number) must be in the answer"** (eval_holdout_v4.py:197, `words()` stop list: with, and, the, that, this, from, unit). Short gold is easy, long gold is hard.
2. **Dev gold is short; T-103 gold is long.** Mean gold words per file: dev 7.5 (max 12), T-103 17.2 (max 32). Dev gold lines naming cooking equipment, hood or UL 300: 0 of 20. T-103: 10 of 20. T-103 gold follows the D-094 operations rule (equipment, dine-in, takeout, service type); dev gold (2026-10-15) has type, seats, units, alcohol.
3. **T-103 gold wording differs from the documents.** Dev gold copies the document ("Residential apartments, 12 units ..."). T-103 gold writes "Apartment building" for four files (158, 160, 167, 172) where the documents say "Residential apartments". Four files have "under Type I hood" (document and answer say "Type I hood"). Three more add a word the application does not have (taqueria, June and July, laundromat and pressing).
4. **Dev was the development set.** The P-047 word list says "add words when a dev file shows a gap" (prepare.py:810). P-047 to P-054 were built while looking at the dev files; T-103 is the first set scored against them with gold written under the D-094 rule.
5. The one dev miss is SUB-143 (Spanish email only, operations "Clothing boutique retail store"); I did not trace it.
6. The other fields are close between the two sets: tiv 17 and 17, construction 17 and 17, year_built 16 and 16, sales 18 and 17, effective_date 18 and 17. The gap is operations (19 vs 7), loss_runs (8 of 8 vs 5 of 9), status (18 vs 15). The pipeline is not much weaker on T-103; the gold changed the test for operations, and the picture quality for the scans.

Without the 4 "under" files and the 7 gold-wording files, operations is 18/20 (the remaining misses are 163, check, and 170, OCR).

## (b) SUB-170: OCR text was read, every field empty

Path, in order:

1. **OCR** (`sources.read_folder`): application.jpg read with `tesseract psm6; osd turn; deskew +-12; rule lift; x2 lanczos`, page confidence 0.565, 179 words, 1129 characters. The text is garbled ("named insured? piueponnet Kitches co LLC", "agos8 glide Rd; puppock. TX 79414", "annual gales* 53, 300,000 combined", "Building TIV: 51,040,009 toc Li 5465, 000 toc 2").
2. **Prepare and prompt** (prepare.py:964, llm_extract.py:698): the file is sent whole (not needs_human, not unread). The model call succeeded on the first attempt.
3. **Reply** (saved reply for this cache key): the model read the garble well. It returned named_insured "Bluebonnet Kitchen Co LLC" (0.95), effective_date 2027-03-01 from the email (0.9), operations "Restaurant; 2 locations; Burgers, chicken and breakfast; dine-in and takeout; Beer and wine, no Liquor License; flat-top, 2 fryers, charbroiler, 8-burner range, Type I hood UL 300 at both locations" (0.85), sales 53300000 (0.9), tiv_building 1586000 (0.8), and conflicts for premises (4808 Slide Rd, Lubbock vs 2200 N Judge Ely Blvd, Abilene), construction (Masonry vs Metal) and year_built (2004 vs 1998).
4. **Parse and gate, where the values are lost: `accept_field`, llm_extract.py:417-507.** For a scanned source the confidence becomes `min(model, cited_ocr_score)` (llm_extract.py:436-439); `cited_ocr_score` (llm_extract.py:402) is the lowest Tesseract word score in the quote. Below `SCAN_FLOOR` 0.50 the value is dropped (llm_extract.py:455-458); from 0.50 to 0.75 it is kept for review. Replayed per field:

| Field | Model conf | OCR-cited conf | Lowest words | Result |
|---|---|---|---|---|
| named_insured | 0.95 | 0.74 | co 0.74, llc 0.83 | above the floor, but "Bluebonnet Kitchen Co LLC" is not inside the quote "piueponnet Kitches co LLC": `value_in_span` (llm_extract.py:371) returns "value not inside the cited text"; dropped |
| effective_date | 0.9 | n/a (email) | none | quote "Eff 3/1/27." has a 2-digit year; `_quote_dates` (llm_extract.py:341) and `_DATES` (line 313) read only 4-digit years; "value not inside the cited text"; dropped |
| operations | 0.85 | 0.29 | takeout 0.29, burgers 0.32, type 0.33 | under 0.50: dropped |
| sales_or_payroll | 0.9 | 0.27 | 000 0.27, gales 0.35 | dropped |
| tiv_building | 0.8 | 0.27 | 000 0.27, 009 0.43 | dropped |
| premises (both sides) | 0.9 | 0.37 | tx 0.37 | dropped; the conflict has no valid side |
| construction (2 sides) | 0.9 | 0.94, 0.83 | masonry, metal | kept as an open conflict |
| year_built (2 sides) | 0.9 | 0.88, 0.92 | 2004, 1998 | kept as an open conflict, flagged "number or date read from a scan" |

5. **Fields** (prepare.py:964-1060): `merged` keeps the empty default for every dropped field; construction and year_built appear only as open conflicts. `completeness` lists all 9 fields missing, status "incomplete", route "hold" with no provisional route (workbench.match: missing information).

Result: the model read the page. The per-field OCR gate dropped five scanned fields because one low word in a quote sets the score of the whole field (and a word seen twice takes its lowest score, the `ponytail` note at llm_extract.py:407). The model's cleaned-up name failed the in-quote test, and the email date failed the date parser. Class: OCR for the five scan fields and the TIV conflict; check for the date and the two-location conflicts. The gold TIV conflict (465000 vs 546000) cannot be found: the 465000 is read as "5465, 000" and the TIV is rejected with the rest.

For comparison, dev SUB-144 (also a scanned two-location application) was read at OCR confidence 0.937; SUB-170 at 0.565.

## (c) Scanned carrier runs SUB-159 to 161: no valued-through date, status "incomplete"

| File | OCR conf | OCR text of the date line | Model reply for loss_run_valued_through | What happened |
|---|---|---|---|---|
| SUB-159 loss-runs.jpg | 0.555 | "Valuation date, 7026-99. 5," | null, confidence 0 | The model did not guess (prompt: never invent a date). Field missing |
| SUB-160 loss-runs.jpg | 0.583 | "Valueg, 7026-99. 5" | null, confidence 0 | Same |
| SUB-161 loss-runs.pdf (image only) | 0.731 | "Valueg @s of: 2026~09.35" | "2026-09-35", quote "Valueg @s of: 2026~09.35", 0.9 | "30" was read "35". The OCR-cited confidence is 0.0 (token 2026 also appears in "2026-04-91" at 0.0 and the lowest score wins), so `accept_field` drops it: "confidence 0.00 is under 0.75". It would also fail `datetime.date.fromisoformat` (llm_extract.py:388): September has no 35th |

The date gate did the right thing each time: a garbled date is not kept. The dev scans read at 0.884 to 0.932 with "Valued as of: 2026-09-30" intact, and all 8 dev loss-run marks are hits. The T-103 images are noisier. Class: OCR.

**Why "incomplete" and not P-048(b) "complete — review pending".** P-048(b) keeps a date read from a scan or an image-only PDF and marks it for review (`gate_loss_run`, prepare.py:560-608; self-check prepare.py:2231-2239). It needs a date to keep. With no date, `gate_loss_run` takes its first branch (`if not row.get("value")`, prepare.py:564-571): it sets the reason "from scan" and leaves the field empty. The field is missing, `completeness` returns complete False, and `pending` (prepare.py:1084: `report["complete"] and not extra and bool(...)`) is False. The status is "incomplete". Two of the files have a second blocker that would remain even with a perfect date:

- SUB-159: the application's line of business says "restaurant" (it is a bakery and cafe), which fires the P-015 ask lists (prepare.py:1064-1073): extra = cooking equipment, liquor sales. `pending` requires `not extra`.
- SUB-161: the hardware wholesaler sells "kitchenware"; the substring "kitchen" fires the same lists (cooking equipment, hood and fire suppression, liquor sales).
- SUB-160 has no extra, so with a readable date it would be review pending.

Gold for 159 to 161 says "Expected pipeline status: complete — review pending". That holds only when OCR gives the date and, for 159 and 161, the extras rule is not fired by "restaurant" and "kitchenware". Class for the three status misses: OCR first, check second (159, 161).

## (d) SUB-172 and the email-only and Spanish files

**SUB-172 (3 locations, typed).** The application says "Premises address: A (loc 1); B (loc 2); C (loc 3)" and "Year built: 2012 (loc 1), 2015 (loc 2), 2017 (loc 3)". The model, following the prompt ("do not pick a side; leave the field null and add a conflict"), returned premises_address null and year_built null, each with three conflict sides; all quotes are valid; source application.md.
- The code that turns several addresses into locations (`split_schedule`, llm_extract.py:677-697) works only when the sides come from a schedule file (`.csv`, `.xlsx` or a name with "schedule"). These sides are from application.md, so they stay an open premises conflict. `labeled_locations` (prepare.py:705) knows "main premises / second premises" or a tab table with a Location column, not "(loc N)". `apply_locations` returned no locations (report locations: []).
- Nothing combines year values labeled by location, so year_built stays null with an open conflict.
- schedule.csv in the folder has the same three addresses and years, but the model cited the application, so the schedule rule did not apply. Dev SUB-145 (3-location csv schedule) had no misses; I did not trace its reply.
- Result: premises miss, year_built miss, and a conflict miss (gold: none). Class: check (location handling) for all three. Operations (Apartment buildings) is gold convention.

**SUB-168 (email only, English).**
- effective_date: the email says "Eff 4/1/27". The model returned "4/1/27" (the prompt gives no date format). `value_in_span` calls `fromisoformat("4/1/27")`, which fails: "the date does not parse" (llm_extract.py:388-390). Had the model written 2027-04-01, the quote parser would still not read "4/1/27" (see SUB-169). Class: check.
- premises: "800 Eighth St Wichita Falls 76301" kept (it has a ZIP). Gold: "800 Eighth St, Wichita Falls, TX 76301". The email has no state, so v4's address comparison (commas ignored) differs by "TX". Class: gold convention.
- sales, tiv, construction, year_built: not in the email; the pipeline correctly leaves them empty. Gold wrote "missing, not given"; v4 scores an empty value as a miss unless the gold line is exactly "not in documents" (`judge()`, eval_holdout_v4.py:131-137). Class: gold convention (settled forward by D-102 item 2).

**SUB-169 (email only, Spanish).**
- effective_date: the model returned 2027-05-01 from "Eff 5/1/27"; `_quote_dates` cannot read a 2-digit year, so "value not inside the cited text". Class: check.
- premises: the model returned "Pharr TX". `drop_premises_without_zip` (prepare.py:248-262, P-001) drops any premises without a five-digit ZIP. Gold records "Pharr, TX (street address not given)" as a hit. Class: gold convention (gold contradicts the P-001 rule).
- operations: translated and flagged; "laundry"/"ironing" vs gold "laundromat"/"pressing". Gold convention.
- sales, tiv, construction, year_built: same "missing, not given" convention as SUB-168.
- route: gold no_match (R8, laundromat). The pipeline sends "self, service, laundry, washers, gas" through P-053 (words not on the Carrier A allow-list) and gives a provisional senior_referral with Carrier A suggested. Class: check (no laundry word in the class lists).

**SUB-163 (Spanish application).**
- Name, premises, effective date, sales, TIV, year built and construction were read. Operations is null. The model's quote is "Restaurante familiar de cocina mexicana. 60 asientos, cerveza y vino, sin barra. Servicio en mesa y para llevar. ... Comal, parrilla, 2 freidoras, estufa de 6 quemadores. Campana tipo I con sistema UL 300" (two lines joined with " ... "). `find_quote` finds no such substring, and the P-048(d) fallback splits only on newlines (llm_extract.py:463), so: "quote not found in application.md", confidence 0.0, value dropped. `check_operations` skips an empty value. With operations missing and no provisional route the file is held (route miss against gold senior_referral). Had the quote matched, the English value would have been flagged as translated. Class: check (quote matching of an ellipsis). Secondary: the model also used " ... " in SUB-170; the prompt says only "quote must be an exact substring of one document" and does not say how to cite two lines.

## Summary table (every non-hit mark except not credited)

| Submission | Field | Class | Cause |
|---|---|---|---|
| SUB-156 | operations | scorer | Gold says "under Type I hood"; answer has every fact but not the word "under" (silent). |
| SUB-156 | conflict | gold convention | Gold conflict line is "none (the email's 'last winter'...)"; v4 only accepts exactly "none". |
| SUB-157 | operations | scorer | Gold word "under" absent; all facts present (silent). |
| SUB-158 | operations | gold convention | Gold "Apartment building" vs document "Residential apartments". |
| SUB-158 | status | check | Reword flag fires on a trailing period ("only)." vs "only)"): review pending instead of complete. |
| SUB-159 | operations | scorer | Gold word "under" absent; all facts present (silent). |
| SUB-159 | loss_runs | OCR | Valuation date read as "7026-99. 5," (conf 0.555); model returned null. |
| SUB-159 | status | OCR | No date, so incomplete; also P-015 extras ("restaurant" in line of business) would block review pending. |
| SUB-160 | operations | gold convention | Gold "Apartment building" vs document "Residential apartments". |
| SUB-160 | loss_runs | OCR | Valuation date read as "7026-99. 5" (conf 0.583); model returned null. |
| SUB-160 | status | OCR | No date, so incomplete instead of review pending. |
| SUB-161 | loss_runs | OCR | Date read as "2026~09.35" (30 read as 35); model copied "2026-09-35", gate rejects. |
| SUB-161 | status | OCR | No date, so incomplete; extras from "kitchenware" would also block review pending. |
| SUB-163 | operations | check | Quote with " ... " is not an exact substring; value dropped. |
| SUB-163 | route | check | Follows from operations null: held, no provisional route. |
| SUB-164 | loss_runs | scorer | Date kept but flagged for the right reason; v4 scores any value against a gold "missing" as a miss. |
| SUB-165 | operations | gold convention | "(June and July)" is only in the email; not a rule item. |
| SUB-167 | operations | gold convention | Gold "Apartment building" vs document "Residential apartments". |
| SUB-167 | route | gold convention | Gold route is "hold" (D-102 now bans it as a route). |
| SUB-168 | premises | gold convention | Email has no state; gold adds "TX". |
| SUB-168 | effective_date | check | Model returned "4/1/27"; date gate wants ISO and does not parse 2-digit years. |
| SUB-168 | sales | gold convention | Gold "missing, not given"; v4 scores an empty value as a miss unless gold is exactly "not in documents". |
| SUB-168 | tiv | gold convention | Same ("missing, no values given"). |
| SUB-168 | construction | gold convention | Same. |
| SUB-168 | year_built | gold convention | Same. |
| SUB-169 | premises | gold convention | "Pharr TX" has no ZIP; P-001 drops it by design; gold counts city and state. |
| SUB-169 | effective_date | check | Model gave 2027-05-01 from "Eff 5/1/27"; date gate cannot read a 2-digit year and rejects it. |
| SUB-169 | operations | gold convention | Translation choice: laundry/ironing vs gold laundromat/pressing (flagged as translated). |
| SUB-169 | sales | gold convention | Gold "missing, not given". |
| SUB-169 | tiv | gold convention | Same. |
| SUB-169 | construction | gold convention | Same. |
| SUB-169 | year_built | gold convention | Same. |
| SUB-169 | route | check | Laundry words are on no list; P-053 sends unlisted words to senior_referral, gold R8 says no_match. |
| SUB-170 | named_insured | OCR | Model fixed the garbled name; value not inside the OCR text, rejected. |
| SUB-170 | premises | OCR | Both address sides at 0.37 (word "TX"), under the 0.50 floor. |
| SUB-170 | effective_date | check | Email "Eff 3/1/27." (2-digit year) not parsed by the date gate; value rejected. |
| SUB-170 | operations | OCR | Word "takeout:" at 0.29, field under the 0.50 floor. |
| SUB-170 | sales | OCR | Words "000" 0.27 and "gales" 0.35; under the floor. |
| SUB-170 | tiv | OCR | "$1,040,000" read "51,040,009", "$465,000" read "5465, 000"; under the floor. |
| SUB-170 | construction | check | "Masonry (loc 1) / metal (loc 2)" is opened as a conflict; no per-location rule. |
| SUB-170 | year_built | check | "2004 (loc 1), 1998 (loc 2)" is opened as a conflict; no per-location rule. |
| SUB-170 | conflict | OCR | Gold TIV conflict 465000/546000 is not found: the 465000 read as "5465, 000" and the TIV was rejected. |
| SUB-170 | route | OCR | Every field empty, so held with no provisional route. |
| SUB-171 | operations | scorer | Gold word "under" absent; all facts present (silent). |
| SUB-172 | premises | check | Three "(loc N)" addresses in one line become a premises conflict; the schedule rule only works on a schedule file. |
| SUB-172 | operations | gold convention | Gold "Apartment buildings" vs document "Residential apartments". |
| SUB-172 | year_built | check | Three "(loc N)" years become a conflict; no per-location rule. |
| SUB-172 | conflict | check | Gold "none"; the false premises and year conflicts are the same check gap. |
| SUB-173 | operations | gold convention | Gold adds "taqueria"; not in the application's operations line (silent). |

## Counts per class

| Class | Marks |
|---|---|
| extraction | 0 |
| prompt | 0 |
| check | 12 |
| OCR | 13 |
| scorer | 5 |
| gold convention | 19 |
| total | 49 |

Operations alone (13 misses): scorer 4, gold convention 7, check 1, OCR 1. The 6 silent errors: scorer 4 (156, 157, 159, 171), gold convention 2 (165, 173).

## Notes for the AI Engineer (no proposal made; nothing here changes code)
- The date gate cannot read "3/1/27"-style dates (SUB-168, 169, 170): three files in this set.
- The reword check (`value_in_span`, llm_extract.py:394) compares whitespace-split words with punctuation, so a trailing period on the model's value flags an exact copy ("only)." vs "only)"). It sent 158 to review pending and flags the four apartment files.
- The extras rule fires on any substring "kitchen" and on a line of business that says "restaurant" (159, 161).
- The per-field OCR score uses the lowest word of the whole quote, and the lowest score of a repeated token.
- 24 of 49 marks (19 gold convention, 5 scorer) are outside the pipeline. D-102 item 2 settles empty fields and "hold" forward. Still open: operations gold wording that is not in a document (apartment building, taqueria, laundromat) is a miss under the v4 word rule.
