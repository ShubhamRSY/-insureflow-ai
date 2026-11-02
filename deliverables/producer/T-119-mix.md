# T-119 hold-out mix: SUB-340 to SUB-371 (32 submissions)

Built by `simulation/inbox/build_SUB-340-371.py` (idempotent, writes only SUB-340..371). Fictional businesses, people, addresses and claim numbers. Nothing run, extracted, scored, or model-called. No paid API. Nothing committed or pushed.

## In scope (SUB-340 to SUB-359, 20 files)

Single location, English, typed application. Carrier counts: Carrier A 8, Carrier B 4, Carrier C 6, owner letter 1 (SUB-350), no run 1 (SUB-359).

| SUB | Insured (fictional) | Operations line | Application | Schedule | Loss run | Flags |
|---|---|---|---|---|---|---|
| 340 | Tallgrass Office LLC | Office | md | no | Carrier A, clean (no-claims sentence), valued 2026-08-27 | Clean shape: office tenant |
| 341 | Pinecrest Threads LLC | Clothing retail storefront | md | no | Carrier A, clean, valued 2026-06-29 | Clean shape: clothing storefront |
| 342 | Prairie Dry Goods Co LLC | Dry goods retail store | md | no | Carrier A, clean, valued 2026-09-14 | Clean shape: dry goods |
| 343 | Old Mill Thrift Co LLC | Thrift store | md | yes | Carrier A, clean, valued 2026-07-16 | Clean shape: thrift |
| 344 | Gulf Plains Electrical Contractors LLC | Electrical contracting, office and shop | typed PDF | yes | Carrier B, 1 claim, valued 2026-05-26 | CONFLICT square footage: app 3,200; schedule and email 2,450 |
| 345 | Brazos Janitorial Supply LLC | Wholesale janitorial supplies, warehouse | md | no | Carrier C, clean, valued 2026-08-05 | CONFLICT annual sales: app $1,240,000; email about $1.42 million |
| 346 | Ironwood Professional Plaza LLC | Lessor of office building, 8 suites | md | yes | Carrier A, 1 roof claim, valued 2026-06-08 | CONFLICT suite count: app 8; email nine. Office lessor |
| 347 | Lamar Professional Center LLC | Lessor of office building, 6 suites | md | yes | Carrier C, clean, valued 2026-09-18 | Office lessor |
| 348 | Sunny Side Deli LLC | Deli, counter service sandwiches and soups | md | no | Carrier B, 1 slip, valued 2026-07-30 | Deli. CONFLICT cooking: app "None"; email says soup on the stove top and panini on a flat grill |
| 349 | Cornerstone Sandwich Bar LLC | Deli, counter sandwiches and soups | md | yes | Carrier A, clean, valued 2026-09-01 | Deli. CONFLICT cooking: app "None"; schedule cooking "Yes"; email says griddle |
| 350 | Hollis Plumbing Supply Co | Wholesale plumbing supplies, warehouse, counter pickup | md | no | Owner's dated no-known-loss letter, dated 2026-09-29 (no carrier run) | Uses the one allowed letter in scope |
| 351 | Blue Plate Pancake House LLC | Breakfast and lunch restaurant | typed PDF | no | Carrier C, 1 kitchen fire, valued 2026-06-24 | Restaurant, cooking named (griddle, fryer) |
| 352 | Foxhole Pub & Kitchen LLC | Pub with full bar and kitchen, ground floor; office suites, second floor | typed PDF | no | Carrier C, 1 liquor claim, valued 2026-08-14 | PUB CASE: two operations on one policy, single building; fryer and flat top |
| 353 | Velvet Crane Cocktail Lounge LLC | Cocktail lounge, full liquor, bottle service, DJ | md | no | Carrier B, 1 claim, valued 2026-09-10 | PROHIBITED: cocktail lounge, full liquor |
| 354 | Neon Harbor Nightclub LLC | Nightclub, dance floor, DJ, full bar | md | no | Carrier C, 1 assault claim, valued 2026-07-09 | PROHIBITED: nightclub |
| 355 | Ember Smoke Hookah Lounge LLC | Hookah lounge, lounge seating, beer and wine | md | no | Carrier A, clean, valued 2026-08-21 | PROHIBITED: hookah lounge |
| 356 | Juniper Glen Apartments LP | Residential apartments, 16 units | typed PDF | no | Carrier C, 1 plumbing claim, valued 2026-09-07 | Apartments |
| 357 | Redbud Court Apartments LLC | Residential apartments, 8 units | md | no | Carrier B, 1 water claim, valued 2026-06-15 | Apartments |
| 358 | Tejas Metal Fabrication LLC | Light metal fabrication, brackets and railings, shop | md | yes | Carrier A, 1 welding-spark fire, valued 2026-07-22 | Light manufacturing |
| 359 | Piney Creek Floors LLC | Flooring installation, hardwood, tile and vinyl | md | no | NONE: email says the run is coming, none in folder | Missing document (the one allowed in scope) |

In-scope counts:
- Clean Carrier A single-operation shapes: 4 (SUB-340 office, 341 clothing storefront, 342 dry goods, 343 thrift). Building TIV all at most $5,000,000 (max $175,000).
- Planted conflicts (both figures stated plainly in the files): 3 (SUB-344 square footage, SUB-345 annual sales, SUB-346 suite count). Cooking conflicts: 2 (SUB-348, SUB-349).
- Cooking "None" with nothing else about cooking anywhere: 340, 341, 342, 343, 345, 346, 347, 353, 354, 355, 358, 359 (12).
- Pub case: 1 (SUB-352).
- Prohibited class: 3 (SUB-353, 354, 355).
- Office-building lessor: 2 (SUB-346, 347).
- Deli-style: 2 (SUB-348, 349).
- Owner's dated no-known-loss letter: 1 (SUB-350). No loss run: 1 (SUB-359).
- Spread: restaurants 2 (351, 352 pub), contractors 2 (344, 359), apartments 2 (356, 357), light wholesale 2 (345, 350), light manufacturing 1 (358), office and retail 4 (340, 341, 342, 343), plus lessors, deli and prohibited above.

## Out of scope (SUB-360 to SUB-371, 12 files)

Criteria: 1 = scanned or image-only application; 2 = more than one location; 3 = application not in English; 4 = no identifiable application (email only).

| SUB | Insured (fictional) | Criteria | Application | Loss run | Notes |
|---|---|---|---|---|---|
| 360 | Harmon Auto Trim LLC | 1 | scanned JPG | Carrier B, clean, valued 2026-07-07 | Scan from the copier |
| 361 | Sabine Tire & Wheel LLC | 1 | image-only PDF | Carrier A, 1 theft, valued 2026-05-13 | Printed, signed, scanned |
| 362 | Red Oak Glass Works LLC | 2 | md, lists 2 locations | Carrier C, 1 break-in, valued 2026-08-29 | Schedule has 2 rows |
| 363 | Crescent Print Shop LLC | 2 | md, lists 1 location | Carrier B, clean, valued 2026-06-03 | Email and schedule show a 2nd press room |
| 364 | Lavandería Azul LLC | 3 | Spanish typed PDF | Carrier B, 1 water claim, valued 2026-07-19 | Spanish laundromat |
| 365 | Taller Mendoza Auto LLC | 3 | Spanish md | Carrier C, clean, valued 2026-09-11 | Spanish auto repair |
| 366 | (unnamed roofing and gutter company, Waco) | 4 | none, email only | none | Email promises app later |
| 367 | (unnamed landscape crew, Killeen) | 4 | none, email only | none | Email only |
| 368 | Brazos Bend Sign Works LLC | 1 + 2 | scanned JPG, lists 2 locations | Carrier A, clean, valued 2026-08-06 | Schedule has 2 rows |
| 369 | Panadería San Judas Inc | 2 + 3 | Spanish typed PDF, 2 stores | Carrier A, clean, valued 2026-09-28 | Schedule has 2 rows |
| 370 | Carpintería Rivera LLC | 1 + 3 | Spanish image-only PDF | Carrier C, 1 theft, valued 2026-08-18 | Spanish scan |
| 371 | (unnamed pressure washing company, Waco and Temple) | 2 + 4 | none, email only | none | Email describes 2 yards |

Out-of-scope counts (criteria touched; at least 2 per criterion):
- Criterion 1: 4 files (360, 361, 368, 370). Alone: 360, 361.
- Criterion 2: 5 files (362, 363, 368, 369, 371). Alone: 362, 363.
- Criterion 3: 4 files (364, 365, 369, 370). Alone: 364, 365.
- Criterion 4: 3 files (366, 367, 371). Alone: 366, 367 (2 required, met).
- Two-criteria files: 4 (368, 369, 370, 371).

## Loss-run coverage (all 32)

- Typed carrier runs: 27, all in the published formats. Carrier C: 9 (345, 347, 351, 352, 354, 356, 362, 365, 370). Carrier B: 7 (344, 348, 353, 357, 360, 363, 364). Carrier A: 11 (340, 341, 342, 343, 346, 349, 355, 358, 361, 368, 369).
- No "| None reported |" rows. No-claims files use each carrier's exact no-claims sentence.
- Every valued date is between 2026-03-01 and 2026-10-15 (earliest 2026-05-13, latest 2026-09-28). Owner letter in SUB-350 is dated 2026-09-29.
- Carrier C claim numbers are "C-" plus digits (C-50311 to C-50851, all unique).
- Missing loss run in scope: SUB-359 only. Owner letter in scope: SUB-350 only.
- Out of scope with no run: SUB-366, 367, 371 (email only).

## Checks (carrier_run_check, run from the worktree with the ai package on sys.path)

Result: 27 of 27 typed loss runs return state "accepted" with the intended valued date. SUB-350 is a no-known-loss letter, so it is not a carrier run (state None, as intended).

```
SUB-340 accepted 2026-08-27   SUB-341 accepted 2026-06-29   SUB-342 accepted 2026-09-14
SUB-343 accepted 2026-07-16   SUB-344 accepted 2026-05-26   SUB-345 accepted 2026-08-05
SUB-346 accepted 2026-06-08   SUB-347 accepted 2026-09-18   SUB-348 accepted 2026-07-30
SUB-349 accepted 2026-09-01   SUB-351 accepted 2026-06-24   SUB-352 accepted 2026-08-14
SUB-353 accepted 2026-09-10   SUB-354 accepted 2026-07-09   SUB-355 accepted 2026-08-21
SUB-356 accepted 2026-09-07   SUB-357 accepted 2026-06-15   SUB-358 accepted 2026-07-22
SUB-360 accepted 2026-07-07   SUB-361 accepted 2026-05-13   SUB-362 accepted 2026-08-29
SUB-363 accepted 2026-06-03   SUB-364 accepted 2026-07-19   SUB-365 accepted 2026-09-11
SUB-368 accepted 2026-08-06   SUB-369 accepted 2026-09-28   SUB-370 accepted 2026-08-18
```

Name, address and claim-number collision check against simulation/inbox/SUB-* (all files) and simulation/inbox-dev/: 0 real collisions. One generic phrase ("same as Loc 1") appears in an older file; it is not an identity. One name was renamed during the build (apartments "Cypress Bend" to "Juniper Glen").

## Freeze and inventory

- 32 folders SUB-340 to SUB-371 under simulation/inbox/. Builder: simulation/inbox/build_SUB-340-371.py. Nothing else in simulation/ or the repo was touched.
- Files per folder match the table above (application.md / application.pdf / application_scan.jpg, email.md, schedule.csv where listed, loss-runs.md where listed).
- Not run, extracted or scored. No model call. Hold-out gold and scores not created or read.
- Paths read: simulation/inbox/SUB-* listing only for the collision check. No team/, deliverables/, CLAUDE.md or .cursor/ read.

## Freeze note (T-119), 2026-10-23 (written by the orchestrator)

- Code under test: `pilot-integration` commit **b6a35b7** (`b6a35b7d94de4afa36d7457b21d28d6f4c8b4358`; pipeline code identical to d7949d2), prompt version **759b3e6bc9b2**, scorer **v11** sha256 `7ddcfb50521b7af17f00c0e148891ca40008d019ce257b9b5d121c7fa6d3fcbb`, lint sha256 `01147a7532bdd7f1ec00861200d1d5e6bbf87f12612389416ff58b78844ea653` (team/NEXT-SESSION.md, Freeze 2026-10-23).
- Submissions: `simulation/inbox/SUB-340` … `SUB-371` (32), built by `simulation/inbox/build_SUB-340-371.py`; never extracted, never run, no model call. All 26 typed carrier runs pass `carrier_run_check` (accepted); SUB-350 owner letter declared undated; SUB-359 no loss run.
- Gold frozen: `deliverables/senior-underwriter/gold-set/SUB-340.md` … `SUB-371.md` plus `T-119-routes.md`. Manifest `deliverables/senior-underwriter/T-119-gold-manifest.sha256` (33 lines: shasum -a 256 of SUB-340..371.md then T-119-routes.md, repo-relative paths). **Manifest sha256 = `2feba3b2b007ab197c22a40427b105242585ee0783bed7c5e5a575408fd55fcc`**.
- Lint (v11): FAIL 2, 1 info, 32 files — the only failures are the SUB-348 and SUB-349 conflict marks, which D-128 declares unmeasurable under v11 ("Under v11 these two conflict marks can't be measured; they are reported separately and excluded from the conflict rate. Noted before the run."). Info: SUB-350 undated as declared. See `deliverables/senior-test-engineer/T-119-lint.md`.
- Checks: @model-risk build check BLOCK (H1, `deliverables/model-risk/T-119-build-check.md`) → D-128 gold fixes → look-again APPROVE (`T-119-build-check-2.md`).
- Noted before the run: D-127 (omitted "no cooking" slots are misses under v11; 14 files carry it, listed in T-119-gold-summary.md) and D-128 (348/349 conflict marks).
- No score exists: T-119 is not run (D-020: run once, score once, later, with the user's approval).
