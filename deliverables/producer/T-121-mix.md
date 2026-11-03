# T-121 hold-out mix: SUB-510 to SUB-541 (32 submissions)

Builder: `simulation/inbox/build_SUB-510-541.py` (idempotent; removes and rebuilds only SUB-510..541). Written 2026-11-03 by @producer (work done in the main session, D-139 tool rule), before any gold. Pipeline not run; no model called; no eval or score read.
Scope rule used (P-077, D-146, D-149): a different premises street address in any document, or a second store, branch or shop in words (incl. a closed one), is out of scope (criterion 2). "Two floors", "2nd floor", "two entrances" and role-labelled addresses (mailing PO Box) stay in scope.

## Per-file table

| SUB | Insured | Ops line | Docs | Loss run | Flags |
|---|---|---|---|---|---|
| 510 | Lone Oak Accounting LLC | Office | app.md, email, loss-runs.md | A, no claims, valued 2026-09-15 | direct A |
| 511 | Bluestem Boutique LLC | Clothing boutique | app.pdf (typed), email, loss-runs.md | A, no claims, valued 2026-08-24 | direct A |
| 512 | Pine Hollow Mercantile LLC | Dry goods retail store | app.md, email, loss-runs.md | A, no claims, valued 2026-10-02 | direct A |
| 513 | Granite Shoals Consulting LLC | Office suite | app.pdf (typed), email, loss-runs.md | A, no claims, valued 2026-09-29 | direct A |
| 514 | Riverbend Plumbing Services LLC | Plumbing contractor, shop and yard | app.pdf (typed), email, loss-runs.md | B, 1 truck claim, valued 2026-08-11 | CONFLICT sq ft (email 2,700 / app 3,500); contractor |
| 515 | Trinity Bay Paper Supply LLC | Wholesale paper and packaging goods, warehouse | app.md, email, loss-runs.md | C, no claims, valued 2026-09-18 | CONFLICT sales, words (email "$2.35 million" / app $2,080,000); wholesale |
| 516 | Copperleaf Painting LLC | Painting contractor, interior and exterior repaints | app.md, email | MISSING (email says coming) | missing loss run; mailing PO Box (role-labelled, in scope) |
| 517 | Live Oak Commons Office Center LLC | Lessor of office building, 11 suites | app.md, email, loss-runs.md | C, no claims, valued 2026-10-06 | lessor; CONFLICT suites (email 12 / app 11) |
| 518 | Kestrel Point Professional Building LLC | Lessor of office building, 6 suites | app.md, email, loss-runs.md | C, no claims, valued 2026-10-09 | lessor; CONFLICT sq ft, approx (email roughly 5,100 / app 5,800) |
| 519 | High Plains Roofing Co | Roofing contractor, shop and material yard | app.md, email, loss-runs.md | B, hail claim, valued 2026-07-21 | CONFLICT TIV (email 1,320,000 / app $1,050,000); contractor |
| 520 | Willow Creek Gifts LLC | Gift shop | app.pdf (typed), email, loss-runs.md | B, no claims, valued 2026-08-04 | COOKING CONFLICT (app None; email countertop fryer) |
| 521 | Station Street Deli LLC | Deli, counter service sandwiches and soups | app.md, email, loss-runs.md | B, slip claim, valued 2026-08-19 | deli; cooking stated; CONFLICT sales, approx (email around $610,000 / app $575,000) |
| 522 | Seawall Deli Co LLC | Deli, counter sandwiches | app.md, email, loss-runs.md | C, no claims, valued 2026-09-02 | deli; COOKING CONFLICT (app None; email fryer daily) |
| 523 | Rusty Spur Tavern LLC | Tavern, full bar, pool tables | app.md, email, loss-runs.md | C, fight claim C-61207, valued 2026-08-28 | HELD W1 |
| 524 | Midnight Mesa Nightclub LLC | Nightclub, dance floor, DJ, full bar | app.md, email, loss-runs.md | A, no claims, valued 2026-09-10 | HELD W1 |
| 525 | Sunrise Skillet LLC | Breakfast and lunch restaurant, 54 seats | app.pdf (typed), email, loss-runs.md | C, grease fire C-61344, valued 2026-09-24 | cooking stated |
| 526 | Golden Crust Bakery LLC | Bakery cafe, counter service | app.md, email, loss-runs.md | B, no claims, valued 2026-10-13 | cooking stated (oven) |
| 527 | Cottonwood Tax & Accounting LLC | Tax and accounting office | app.md, email, loss-runs.md | A, no claims, valued 2026-09-21 | NEAR-MISS "two floors" (in scope) |
| 528 | Hardin & Pruitt PLLC | Law office | app.pdf (typed), email, loss-runs.md | C, no claims, valued 2026-09-08 | NEAR-MISS "2nd floor", Ste 210 (in scope) |
| 529 | Brazos Boot & Shoe LLC | Shoe and boot retail store | app.md, email, loss-runs.md | A, no claims, valued 2026-10-01 | NEAR-MISS "two entrances" (in scope) |
| 530 | Mesa Verde Frame Shop LLC | Picture framing shop | application_scan.jpg, email, loss-runs.md | B | OOS criterion 1 (scan) |
| 531 | Clearwater Pool Supply LLC | Pool supply retail store | application.pdf (image only, 0 text), email, loss-runs.md | A | OOS criterion 1 (image-only PDF) |
| 532 | Bayside Auto Glass LLC | Auto glass shop | app.md, email, loss-runs.md, schedule.csv (2 rows) | C | OOS criterion 2, second street address (schedule: 1902 Wildcat Dr, Portland) |
| 533 | Prairie Rose Florist LLC | Florist | app.md, email, loss-runs.md | A | OOS criterion 2, second street address (email: warehouse 2215 Leonard Rd) |
| 534 | Hill Country Vacuum & Sew LLC | Vacuum and sewing sales and repair | app.md, email, loss-runs.md | B | OOS criterion 2, words only ("both stores") |
| 535 | Permian Pump & Supply LLC | Pump and pipe supply | app.pdf (typed), email, loss-runs.md | C | OOS criterion 2, words only ("our other branch in Midland") |
| 536 | Northgate Key & Lock LLC | Locksmith shop | app.md, email, loss-runs.md | A | OOS criterion 2, words only ("a second shop") |
| 537 | Twin Pines Pet Supply LLC | Pet supply retail store | app.md, email, loss-runs.md | B | OOS criterion 2, words only ("closed our second store", D-146) |
| 538 | Llantera El Faro LLC | Tire store, Spanish | app.pdf (typed Spanish), email, loss-runs.md | C | OOS criterion 3 |
| 539 | Papeleria Santa Cruz LLC | Stationery, Spanish | app.md (Spanish), email, loss-runs.md | A | OOS criterion 3 |
| 540 | Oakmont Kennels | Boarding kennel | email only | none | OOS criterion 4 |
| 541 | Redbird Courier | Courier | email only | none | OOS criterion 4 |

## Counts against the T-121 plan

| Requirement | Count | Files |
|---|---|---|
| In scope / out of scope | 20 / 12 | 510–529 / 530–541 |
| Per criterion (≥ 2 each) | 1: 2, 2: 6, 3: 2, 4: 2 | none combined |
| Criterion 2 (≥ 6), words-only (≥ 4) | 6, 4 | 532–537; words only 534, 535, 536, 537 |
| In-scope near-misses (≥ 3) | 3 | 527 two floors, 528 2nd floor, 529 two entrances (+ 516 mailing PO Box) |
| Planted measurable conflicts (≥ 5) | 6 | 514, 515, 517, 518, 519, 521 |
| Worded amount (≥ 1) / approximate (≥ 1) | 1 / 2 | 515 / 518, 521 |
| Cooking None, no cooking word elsewhere (≥ 12) | 15 | 510–519, 523, 524, 527, 528, 529 |
| Cooking stated (≥ 3) | 3 | 521, 525, 526 |
| Cooking conflicts (≥ 2) | 2 | 520, 522 |
| Direct Carrier A (≥ 3) | 4 | 510, 511, 512, 513 |
| Held W1 (≥ 2) | 2 | 523 tavern, 524 nightclub |
| Office-building lessor (≥ 2) | 2 | 517, 518 |
| Deli-style (≥ 2) | 2 | 521, 522 |
| Carrier C runs (≥ 2) / Carrier B (≥ 1) | 7 / 5 in scope | C: 515, 517, 518, 522, 523, 525, 528 (7); B: 514, 519, 520, 521, 526 |
| Missing loss run | 1 | 516 |

## Planted conflicts (builder source)

| SUB | Figure | Document 1 | Document 2 | Type |
|---|---|---|---|---|
| 514 | Square footage | email: "2,700 square feet" | application (typed PDF): "Square footage: 3,500" | exact |
| 515 | Annual sales | email: "$2.35 million" | application: "Annual sales: $2,080,000" | words vs exact (fresh figures, not the P-074 self-test pair) |
| 517 | Suite count | email: "12 suites" | application: "11 suites" (Operations line) | exact |
| 518 | Square footage | email: "roughly 5,100 sq ft" | application: "Square footage: 5,800" | approximate vs exact |
| 519 | Building TIV | email: "1,320,000" | application: "Building TIV: $1,050,000" | exact |
| 521 | Annual sales | email: "around $610,000" | application: "Annual sales: $575,000" | approximate vs exact |

Cooking conflicts: 520 application "Cooking operations: None" vs email "fry empanadas in a small countertop fryer"; 522 application "None" vs email "We run a fryer for fries and shrimp every day".

## Checks run (pure functions only; no pipeline, no model)

- `prepare.carrier_run_check` on all 29 loss runs: 29 accepted, valued 2026-07-21 to 2026-10-13 (before 2026-11-03 and before each effective date). Every listed loss date falls inside its term. No "None reported" rows. Carrier C terms "D - D", claim numbers C-61207, C-61344.
- `prepare.cooking_word` over every md, csv and PDF text of 510–529, skipping the application's own cooking line: none-line files with no other cooking word = 15; 520 hits "fry" (email), 522 hits the deli word and the email fryer.
- PDF text layers (pdftotext): typed 709–823 characters; 531 = 0 (image only, by design); 538 Spanish 525.
- Collisions: 44 insured names and addresses (incl. schedule rows) vs 941 other text files in simulation/inbox and simulation/inbox-dev: 0 hits. Scans and PDFs not text-searched.
- v11 vocabulary traps from the T-120 check avoided: no "kitchen" beside a bar word, no plural "ovens", no "office" in a contractor line, no wholesale + second class, every listed loss date inside its term.
- Correction 2026-11-03 (@model-risk M1, before the gold freeze): the collision check compared full names only; SUB-524 "Velvet Room Nightclub LLC" was close to published SUB-201 "Velvet Room Lounge LLC". Renamed to "Midnight Mesa Nightclub LLC" in the builder and the gold; no other change.
