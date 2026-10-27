# T-120 hold-out mix: SUB-450 to SUB-481 (32 submissions)

Builder: `simulation/inbox/build_SUB-450-481.py` (idempotent; removes and rebuilds only SUB-450..481).
Folders: `simulation/inbox/SUB-450/` .. `simulation/inbox/SUB-481/`. Nothing committed. Pipeline not run; no model called; no team/, deliverables/ or eval/score read.

## Per-file table

| SUB | Insured | Ops line | Docs | Loss run | Flags |
|---|---|---|---|---|---|
| 450 | Cedar Bend Bookkeeping LLC | Office tenant, bookkeeping | app.md, email, loss-runs.md | A, no claims, valued 2026-08-12 | in scope, clean A route |
| 451 | Juniper Lane Apparel LLC | Clothing retail storefront | app.pdf (typed), email, loss-runs.md | A, no claims, valued 2026-07-21 | clean A route |
| 452 | Walnut Creek Hardware Co LLC | Hardware retail store | app.md, email, loss-runs.md | A, no claims, valued 2026-09-02 | clean A route |
| 453 | Mesquite Ridge Insurance Agency LLC | Insurance agency office | app.pdf (typed), email, loss-runs.md | A, no claims, valued 2026-07-30 | clean A route |
| 454 | Neches River Electric LLC | Electrical contractor | app.pdf (typed), email, loss-runs.md | B, 1 van claim, valued 2026-05-26 | CONFLICT sq ft (email 2,450 / app 3,200); contractor; cooking None |
| 455 | Chisholm Trail Janitorial Supply LLC | Janitorial wholesale | app.md, email, loss-runs.md | C, no claims, valued 2026-08-05 | CONFLICT sales (email $1.42 million / app $1,240,000); wholesale |
| 456 | Azalea Floor Works LLC | Flooring contractor | app.md, email | MISSING (email says coming) | missing loss run; contractor |
| 457 | Bayou Ridge Metal Works LLC | Light metal fabrication shop | app.md, email, loss-runs.md | A, welding fire claim, valued 2026-08-18 | cooking None |
| 458 | Pecan Row Professional Center LLC | Office building lessor | app.md, email, loss-runs.md | C, no claims, valued 2026-09-09 | lessor; CONFLICT suite count (email 9 / app 8) |
| 459 | Bluebonnet Duval Professional LLC | Office building lessor | app.md, email, loss-runs.md | C, no claims, valued 2026-08-27 | lessor; CONFLICT floor area, approx (email roughly 2,400 / app 2,950) |
| 460 | Stonegate Roofing & Sheet Metal Co | Roofing / sheet metal contractor | app.md, email, loss-runs.md | B, hail claim, valued 2026-06-30 | contractor; CONFLICT TIV (email 1,180,000 / app $980,000) |
| 461 | Magnolia Gifts & Home Goods LLC | Gift shop with lunch counter | app.pdf (typed), email, loss-runs.md | B, no claims, valued 2026-07-08 | COOKING CONFLICT (app None; email soup on stove top) |
| 462 | Corner Table Deli LLC | Deli, cooking stated | app.md, email, loss-runs.md | B, slip at door, valued 2026-07-30 | deli; cooking stated; CONFLICT sales, approx (email about $560,000 / app $505,000) |
| 463 | Harbor Deli Co LLC | Deli | app.md, email, loss-runs.md, schedule.csv | C, no claims, valued 2026-08-03 | deli; COOKING CONFLICT (app None; schedule cooking Yes; email fryer) |
| 464 | Lantern Hill Pub & Grill LLC | Pub with full bar and kitchen, one building, 2 operations | app.pdf (typed), email, loss-runs.md | C, liquor claim, valued 2026-08-21 | pub-and-kitchen (SUB-352 shape); cooking stated; held |
| 465 | Sunset Pier Nightclub LLC | Nightclub, full bar (W1) | app.md, email, loss-runs.md | C, assault claim, valued 2026-07-15 | HELD prohibited class W1; cooking None |
| 466 | Smoke Ring Hookah Lounge LLC | Hookah lounge, beer and wine (W1) | app.md, email, loss-runs.md | A, no claims, valued 2026-08-26 | HELD prohibited class W1 (not A route); cooking None |
| 467 | Harvest Moon Breakfast House LLC | Breakfast restaurant | app.pdf (typed), email, loss-runs.md | C, grease fire, valued 2026-09-02 | cooking stated (griddle, fryers) |
| 468 | Cypress Bend Bakery Cafe LLC | Bakery cafe, cooking stated | app.md, email, owner NKL letter | NKL letter dated 2026-09-21 (no carrier run) | cooking stated; the only NKL letter in scope |
| 469 | Ridgeline Auto Parts & Tire Service LLC | Mixed: wholesale parts and tire installation | app.md, email, loss-runs.md | A, theft claim, valued 2026-07-28 | mixed class; CONFLICT floor area (email 3,600 / app 4,100) |
| 470 | Tumbleweed Upholstery LLC | Upholstery shop | application_scan.jpg, email, loss-runs.md | B, no claims | OOS criterion 1 (scan) |
| 471 | Brightwater Laundry Co LLC | Coin laundry, dry cleaning drop-off | application.pdf (image-only), email, loss-runs.md | A, no claims | OOS criterion 1 (image-only PDF) |
| 472 | Rosewood Tile & Stone Supply LLC | Tile and stone wholesale | application_scan.jpg, email, loss-runs.md | C, no claims | OOS criterion 1 (scan) |
| 473 | Cactus Hill Pest Control LLC | Pest control, two locations | app.md, email, loss-runs.md, schedule.csv | B, van accident | OOS criterion 2 |
| 474 | Panhandle Office Staffing LLC | Staffing office, two desks | app.md (one loc), email, loss-runs.md, schedule.csv (two rows) | A, no claims | OOS criterion 2 (email and schedule show two) |
| 475 | Coastal Bend Bike Works LLC | Bike retail and repair, two stores | app.pdf (typed), email, loss-runs.md | C, no claims | OOS criterion 2 |
| 476 | Lavanderia Mariposa LLC | Laundry, Spanish | app.pdf (typed Spanish), email, loss-runs.md | C, no claims | OOS criterion 3 |
| 477 | Ferreteria Los Olmos LLC | Hardware, Spanish | app.md (Spanish), email, loss-runs.md | A, no claims | OOS criterion 3 |
| 478 | Servicios de Limpieza Norte LLC | Office cleaning, Spanish | app.pdf (typed Spanish), email, loss-runs.md | B, water claim | OOS criterion 3 |
| 479 | Wren & Hollis Pet Grooming | Pet grooming | email only | none | OOS criterion 4 |
| 480 | Lakeshore Drywall Co | Drywall contractor | email only | none | OOS criterion 4 |
| 481 | Hillcrest Movers | Moving company | email only | none | OOS criterion 4 |

## In-scope counts (20: SUB-450 to SUB-469)

| Requirement | Count | Files |
|---|---|---|
| Single location, English, typed application | 20 / 20 | md or typed PDF; no scans in scope |
| Planted measurable conflicts (>= 5) | 7 | 454, 455, 458, 459, 460, 462, 469 |
| Words for the amount (>= 1) | 1 | 455 |
| Approximate vs exact (>= 1) | 2 | 459, 462 |
| Cooking "None" with no cooking word elsewhere (>= 12) | 14 | 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460, 465, 466, 469 |
| Cooking stated, equipment named (>= 3) | 4 | 462, 464, 467, 468 |
| Cooking conflict (>= 2) | 2 | 461 (soup on stove top), 463 (fryer, schedule cooking Yes) |
| Contractor, wholesale or mixed (>= 2) | 5 | 454, 455, 456, 460, 469 |
| Straight to Carrier A (>= 3) | 4 | 450, 451, 452, 453 (allow-list words only, TIV <= $5M, clean typed A run, no conflicts) |
| Held W1 prohibited (>= 2) | 2 | 465 nightclub, 466 hookah lounge |
| Office-building lessor (>= 2) | 2 | 458, 459 |
| Deli-style (>= 2) | 2 | 462, 463 |
| Pub-and-kitchen, two operations, one building (1) | 1 | 464 |
| Carrier C runs (>= 2) | 7 | 455, 458, 459, 463, 464, 465, 467 |
| Carrier B runs (>= 1) | 4 | 454, 460, 461, 462 |
| Carrier A runs | 7 | 450, 451, 452, 453, 457, 466, 469 |
| Missing loss run (<= 1) | 1 | 456 |
| Owner no-known-loss letter (<= 1) | 1 | 468 |

## Planted conflicts: exact figures and documents (builder source)

| SUB | Figure | Document 1 | Document 2 | Type |
|---|---|---|---|---|
| 454 | Square footage | email.md: "2,450 square feet" | application.md (typed PDF): "Square footage: 3,200" | exact |
| 455 | Annual sales | email.md: "$1.42 million" | application.md: "Annual sales: $1,240,000" | exact vs words |
| 458 | Suite count | email.md: "9 suites" | application.md: "8 suites" (Operations line) | exact |
| 459 | Square footage | email.md: "roughly 2,400 sq ft" | application.md: "Square footage: 2,950" | approximate vs exact |
| 460 | Building TIV | email.md: "1,180,000" | application.md: "Building TIV: $980,000" | exact |
| 462 | Annual sales | email.md: "about $560,000 in sales" | application.md: "Annual sales: $505,000" | approximate vs exact |
| 469 | Square footage | email.md: "3,600 square feet" | application.md: "Square footage: 4,100" | exact |

Cooking-conflict detail: 461 application "Cooking operations: None" vs email.md "heat the soup on the stove top"; 463 application "None" vs schedule.csv cooking "Yes" and email.md "fry chicken tenders in the fryer".

## Collision check

- Names checked: 29 insured names. Addresses: 31 premises/location addresses. Claim numbers: C-50612, C-50734, C-50881.
- Compared against every text and PDF file in simulation/inbox (all SUB-* folders outside 450-481) and simulation/inbox-dev (about 1,026 files via `strings`). Result: 0 hits.
- Limits: scanned JPGs (SUB-470, SUB-472) and xlsx/zip contents are not text-searchable; the check did not cover them.

## Carrier run check (prepare.carrier_run_check, run on every loss-runs.md)

- Accepted: all 27 carrier-format runs (18 in scope, 9 out of scope), valued 2026-05-26 to 2026-09-09 (all before the run date and before each effective date). No "None reported" rows in any file.
- SUB-468 is an owner NKL letter, not a carrier layout, so the check returns None by design.
- SUB-456 has no loss run file (missing document by design).
- Carrier C terms use "YYYY-MM-DD - YYYY-MM-DD"; claim numbers use C-<digits>.

## Cooking and banned-word checks

- Cooking words checked across all files except the application's own "Cooking operations: None" line: none found in the 14 None files.
- Allow-list words for Carrier A routes (450-453): no bar, pub, lounge, liquor, vacant, nightclub, cocktail, beer, wine, hookah words in any file.

## Not met or notes

- Nothing unmet.
- The 4 Carrier A straight-route files are the minimum; no conflicts, no claims.
- Out-of-scope criteria are one each (3 per criterion), not combined.
