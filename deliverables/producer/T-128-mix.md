# T-128 hold-out mix: SUB-550 to SUB-581 (32 submissions)

Builder: `simulation/inbox/build_SUB-550-581.py` (idempotent; removes and rebuilds only SUB-550..581). Written 2026-11-05 by @producer (work done in the main session: the D-165 tool rule allows subagents only for @model-risk), before any gold. Pipeline not run; no model called; no scope detector run; no eval or score read. Freeze recorded first (team/NEXT-SESSION.md, code 1ddae83c, scope-v8).
Scope rule used (P-077, D-146, D-149, P-080): a different premises street, highway or route address in any document, or a second store, branch or shop in words (incl. a sold or closed one), is out of scope (criterion 2). "Two floors", "2nd floor", "two entrances", "one address, one building" and role-labelled addresses (mailing PO Box) stay in scope. B-525: in-scope highway premises use the "2604 Hwy 71 W" and "3115 US-59 N" forms, not FM…Rd, State Highway N, County Road N or I-35 Frontage.

## Per-file table

| SUB | Insured | Ops line | Docs | Loss run | Flags |
|---|---|---|---|---|---|
| 550 | Yaupon Ridge Advisors LLC | Office | app.md, email, loss-runs.md | A, no claims, valued 2026-09-22 | direct A; HIGHWAY premises (2604 Hwy 71 W); email "everything is under one roof at the address on the application" |
| 551 | Calico Thread Apparel LLC | Apparel boutique | app.pdf (typed), email, loss-runs.md | A, no claims, valued 2026-08-27 | direct A |
| 552 | Big Thicket Dry Goods LLC | Dry retail storefront | app.md, email, loss-runs.md | A, no claims, valued 2026-10-05 | direct A; HIGHWAY premises (3115 US-59 N) |
| 553 | Pecan Bayou Consulting LLC | Office suite | app.pdf (typed), email, loss-runs.md | A, no claims, valued 2026-09-30 | direct A |
| 554 | Sabine Current Electric LLC | Electrical contractor, shop and yard | app.pdf (typed), email, loss-runs.md | B, 1 van claim, valued 2026-08-18 | CONFLICT sq ft, plain (email 2,450 / app 3,150); contractor |
| 555 | Ship Channel Packaging Supply LLC | Wholesale packaging goods, warehouse | app.md, email, loss-runs.md | C, no claims, valued 2026-09-14 | CONFLICT sales, words (email "$1.9 million" / app $1,640,000); wholesale |
| 556 | Redbud Lawn & Landscape LLC | Landscaping contractor, mowing and planting | app.md, email, loss-runs.md | B, no claims, valued 2026-09-09 | CONFLICT sales, plain (email 812,000 / app $745,000); mailing PO Box (role-labelled, in scope); contractor |
| 557 | Louetta Oaks Executive Suites LLC | Lessor of office building, 9 suites | app.md, email, loss-runs.md | C, no claims, valued 2026-10-08 | lessor; CONFLICT suites, plain (email 10 / app 9); P-081-resolvable (the conflict is the only hold), still gold incomplete |
| 558 | Chisos Professional Plaza LLC | Lessor of office building, 5 suites | app.md, email, loss-runs.md | C, no claims, valued 2026-10-12 | lessor; CONFLICT sq ft, approx (email about 4,300 / app 4,900) |
| 559 | Caprock Roofing Co | Roofing contractor, shop and material yard | app.md, email, loss-runs.md | B, hail claim, valued 2026-07-28 | CONFLICT TIV, plain (email 980,000 / app $845,000); contractor |
| 560 | Bluebonnet Candle Co LLC | Candle and gift shop | app.pdf (typed), email, loss-runs.md | B, no claims, valued 2026-08-06 | COOKING CONFLICT (app None; email countertop fryer) |
| 561 | Courthouse Square Deli LLC | Deli, counter service sandwiches and salads | app.md, email, loss-runs.md | B, slip claim, valued 2026-08-21 | deli; cooking stated; CONFLICT sales, approx (email about $530,000 / app $498,000) |
| 562 | Mustang Island Deli LLC | Deli, counter sandwiches | app.md, email, loss-runs.md | C, no claims, valued 2026-09-03 | deli; COOKING CONFLICT (app None; email fries every day) |
| 563 | Iron Horse Tavern LLC | Tavern, full bar, darts, pool tables | app.md, email, loss-runs.md | C, fight claim C-62418, valued 2026-09-01 | HELD W1 |
| 564 | Coyote Moon Nightclub LLC | Nightclub, dance floor, DJ, full bar | app.md, email, loss-runs.md | A, no claims, valued 2026-09-18 | HELD W1 |
| 565 | Prairie Dawn Restaurant LLC | Breakfast and lunch restaurant, 48 seats | app.pdf (typed), email, loss-runs.md | C, grease fire C-62533, valued 2026-09-25 | cooking stated |
| 566 | Kolache Corner Bakery LLC | Bakery cafe, counter service | app.md, email, loss-runs.md | B, no claims, valued 2026-10-14 | cooking stated (oven); CONFLICT sq ft, plain (email 2,450 / app 2,150) |
| 567 | Tierra Alta Architects LLC | Architecture office | app.md, email, loss-runs.md | A, no claims, valued 2026-09-24 | NEAR-MISS "two floors" + "it is all at the address on the application" (in scope) |
| 568 | Vasquez & Lund PLLC | Law office | app.pdf (typed), email, loss-runs.md | C, no claims, valued 2026-09-11 | NEAR-MISS "2nd floor", Ste 220 (in scope) |
| 569 | Rio Frio Saddle & Tack LLC | Saddle and tack retail store | app.md, email, loss-runs.md | A, no claims, valued 2026-10-02 | NEAR-MISS "two entrances" (in scope) |
| 570 | Caprice Sign Shop LLC | Sign shop | application_scan.jpg, email, loss-runs.md | B | OOS criterion 1 (scan) |
| 571 | Pedernales Bike Works LLC | Bicycle shop | application.pdf (image only, 0 text), email, loss-runs.md | A | OOS criterion 1 (image-only PDF) |
| 572 | Navasota Post & Wire LLC | Fence supply retail store | app.md, email, loss-runs.md | B | OOS criterion 2, SUB-533 shape: HIGHWAY second address (1408 Hwy 36 S, Brenham) in a sentence naming Carrier B |
| 573 | Guadalupe Glass & Mirror LLC | Glass and mirror shop | app.md, email, loss-runs.md | C | OOS criterion 2, SUB-533 shape: second address (711 N Austin St, Seguin) on the line below "Mailing address: same as premises" |
| 574 | Red River Shoe Repair LLC | Shoe and boot repair shop | app.md, email, loss-runs.md | A | OOS criterion 2, words only ("both shops") |
| 575 | Spicewood Printing LLC | Printing shop | app.pdf (typed), email, loss-runs.md | C | OOS criterion 2, words only ("Our other location in Round Rock") |
| 576 | Concho Valley Hardware LLC | Hardware retail store | app.md, email, loss-runs.md | B | OOS criterion 2, words only ("a second store in Ballinger") |
| 577 | Lavaca Bay Marine Supply LLC | Marine supply retail store | app.md, email, loss-runs.md | A | OOS criterion 2, words only ("sold our second shop", D-146) |
| 578 | Muebleria Los Encinos LLC | Furniture, Spanish | app.pdf (typed Spanish), email, loss-runs.md | C | OOS criterion 3 |
| 579 | Ferreteria El Mezquite LLC | Hardware, Spanish | app.md (Spanish), email, loss-runs.md | A | OOS criterion 3 |
| 580 | Sandy Creek Stables | Horse boarding stable | email only | none | OOS criterion 4 |
| 581 | Blue Norther Moving | Moving company | email only | none | OOS criterion 4 |

## Counts against the T-128 plan

| Requirement | Count | Files |
|---|---|---|
| In scope / out of scope | 20 / 12 | 550–569 / 570–581 |
| Per criterion (≥ 2 each) | 1: 2, 2: 6, 3: 2, 4: 2 | none combined |
| Criterion 2 (≥ 6); words-only (≥ 4); SUB-533-shaped (≥ 2) | 6; 4; 2 | 572–577; words only 574, 575, 576, 577; 533-shaped 572 (carrier sentence), 573 (below the mailing line) |
| In-scope highway premises (≥ 2), one address in every document | 2 | 550 (2604 Hwy 71 W), 552 (3115 US-59 N); the emails name the highway without a house number |
| Out-of-scope highway second address (≥ 1) | 1 | 572 (1408 Hwy 36 S, Brenham) |
| In-scope near-misses (≥ 3) + "one address, one building" (≥ 1) | 3 + 2 | 567 two floors, 568 2nd floor, 569 two entrances; "under one roof at the address on the application" (550) and "all at the address on the application" (567) (+ 556 mailing PO Box) |
| Planted measurable conflicts, plain figures both sides (≥ 5) | 5 | 554 sq ft, 556 sales, 557 suites, 559 TIV, 566 sq ft |
| Worded amount (≥ 1) / approximate (≥ 1) | 1 / 2 | 555 / 558, 561 |
| P-081-resolvable conflict still gold incomplete (≥ 1) | 1 | 557 (the suite conflict is its only hold; nothing missing) |
| Cooking None, no cooking word elsewhere (≥ 12) | 15 | 550–559, 563, 564, 567, 568, 569 |
| Cooking stated (≥ 3) | 3 | 561, 565, 566 |
| Cooking conflicts (≥ 2) | 2 | 560, 562 |
| Direct Carrier A (≥ 3) | 4 | 550, 551, 552, 553 |
| Held W1 (≥ 2) | 2 | 563 tavern, 564 nightclub |
| Office-building lessor (≥ 2) | 2 | 557, 558 |
| Deli-style (≥ 2) | 2 | 561, 562 |
| Carrier C runs (≥ 2) / Carrier B (≥ 1), in scope | 7 / 6 | C: 555, 557, 558, 562, 563, 565, 568; B: 554, 556, 559, 560, 561, 566 |

## Planted conflicts (builder source)

| SUB | Figure | Document 1 | Document 2 | Type |
|---|---|---|---|---|
| 554 | Square footage | email: "2,450 square feet" | application (typed PDF): "Square footage: 3,150" | plain |
| 555 | Annual sales | email: "$1.9 million" | application: "Annual sales: $1,640,000" | words vs exact (fresh figures) |
| 556 | Annual sales | email: "Please use 812,000 for sales" | application: "Annual sales: $745,000" | plain |
| 557 | Suite count | email: "10 suites are now leased" | application: "9 suites" (Operations line) | plain |
| 558 | Square footage | email: "about 4,300 sq ft in all by my estimate" | application: "Square footage: 4,900" | approximate vs exact |
| 559 | Building TIV | email: "put the building at 980,000" | application: "Building TIV: $845,000" | plain |
| 561 | Annual sales | email: "came in at about $530,000" | application: "Annual sales: $498,000" | approximate vs exact |
| 566 | Square footage | email: "measures 2,450 square feet" | application: "Square footage: 2,150" | plain |

Cooking conflicts: 560 application "Cooking operations: None" vs email "the owner fries funnel cakes in a small countertop fryer"; 562 application "None" vs email "shrimp and fries are fried every day".

## Checks run (pure functions only; no pipeline, no model, no scope detector)

- `prepare.carrier_run_check` on all 30 loss runs: 30 accepted, valued 2026-07-28 to 2026-10-14 (before 2026-11-05 and before each effective date). Every listed loss date falls inside its term. Carrier C terms "D - D", claim numbers C-62418, C-62533.
- Found while building: an insured name with the word "Copy" ("Spicewood Print & Copy LLC") makes `carrier_run_check` read a clean Carrier C run as negated. SUB-575 was renamed "Spicewood Printing LLC" before any gold; the quirk goes to the backlog.
- `prepare.cooking_word` over every md and PDF text of 550–569, skipping the application's own cooking line: None-line files with no other cooking word = 15; 560 hits "fry" (email); 562 hits the deli word and the email fry; 561, 565, 566 state cooking.
- PDF text layers (pdftotext): typed 711–829 characters; 571 = 0 (image only, by design); 578 Spanish 531.
- Collisions (B-515, stems and not only full names): full names, the first two words of each name, each name's first word in insured and subject lines, and 33 premises/mailing addresses vs 1,023 other text files in simulation/inbox and simulation/inbox-dev. Renamed before any gold: 572 "Brazos Valley Fence Supply" (stem in SUB-199) → "Navasota Post & Wire"; 564 "Neon Prairie Nightclub" (near SUB-222 "Neon Spur Nightclub", SUB-354 "Neon Harbor Nightclub") → "Coyote Moon Nightclub"; 555 "Gulf Prairie Packaging Supply" (near the "Gulf Coast … Wholesale" names) → "Ship Channel Packaging Supply"; 557 "Cypress Landing Office Park" (shares "Office Park" with lessor SUB-206) → "Louetta Oaks Executive Suites". Remaining single-word overlaps (Pecan, Sabine, Redbud, Caprock, Bluebonnet, Guadalupe, Concho, Lavaca, Frio, Navasota) are Texas place words in names of other classes. Scans and PDFs not text-searched.
- v11 vocabulary traps from T-120/T-121 avoided: no "kitchen" beside a bar word, no plural "ovens", no "office" in a contractor line, no wholesale + second class, every listed loss date inside its term.
- P-084 shapes kept out of in-scope files: no all-capitals or all-lower-case street address with a comma, no route code other than the premises itself, no PMB, General Delivery, Calle, Camino or "Av." text.

## Rewrite after the @model-risk build check (2026-11-05, T-128-build-check.md H2), before the gold freeze

The first build copied T-121 slot by slot (15 of 32 emails ≥ 0.80 similar to an earlier email). Every one of the 32 emails was rewritten with new sentence structures; facts, figures, names, addresses and applications are unchanged, and the gold was rewritten where it quotes an email. The direct Carrier A emails (550–553) now carry no goods or trade words (M2).
- Similarity gate (added to the B-515 collision check): `deliverables/senior-test-engineer/T-128-similarity.py` → `T-128-similarity.txt`. difflib ratio on email bodies, digits masked, against every earlier email in simulation/inbox and inbox-dev: **0 of 32 ≥ 0.80**; highest 0.641 (SUB-579), mean best match 0.539 (T-121 measured the same way: 0 ≥ 0.80, mean 0.631). No email sentence appears in the scope.py or prepare.py source (self-checks) or in inbox-dev (the FICTIONAL banner and 573's required "Mailing address: same as premises" label are skipped).
- Re-run after the rewrite: carrier_run_check 30/30 accepted; cooking_word 15 none-only, 560 and 562 conflicts, 561/565/566 stated; v11 --check-gold and --check-ops-gold 32/32; lint 2 FAIL (560, 562 cooking marks only); B-465 0 mismatches; faithful-answer probe 20/20.
