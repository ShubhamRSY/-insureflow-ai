# T-117 mix — SUB-238 to SUB-269 (producer's intent, not gold)

- Written by @producer, 2026-10-21, for T-117 / D-119. Built by `simulation/inbox/build_SUB-238-269.py` (imports the typed, scan and PDF helpers of the T-108 builders by import only). Files are in `simulation/inbox/SUB-238` … `SUB-269`: 32 folders, nothing run, nothing extracted, no model call, no gold, no route.
- Written to the scratchpad because @producer may not write `deliverables/`. The orchestrator copies it to `deliverables/producer/T-117-mix.md` before gold starts.
- Not read by @producer: `team/`, `deliverables/` (incl. `T-108-mix.md`, `carrier-match.md`, proposal P-055). The class labels below are the producer's plain-language intent, not rule codes. Scope, classes and routes come from the written rules through @senior-underwriter.
- Name check: every insured name in SUB-238–269 was compared against the text of SUB-127–237 (none reused; four collisions were renamed before the build was final).

## In scope — SUB-238 to SUB-257 (20)

| SUB | Class (producer intent) | Documents in folder | Loss run (kind, valued date) | Deliberately tricky |
|---|---|---|---|---|
| 238 | W1 prohibited: nightclub, DJ, dance floor, full liquor, open to 2 am, no kitchen | application.md, email.md, loss-runs.md | typed Carrier C, 2026-06-12 | Year built left off the application; email says "80s, have to dig". Partial sprinklers. |
| 239 | W1 prohibited: cocktail lounge, full liquor, live music Fri and Sat, no real kitchen (countertop oven) | application.md, email.md, loss-runs.pdf | image-only PDF, Carrier B layout, 2026-07-02 | Image-only loss run; "no real kitchen" wording; frame 1968. |
| 240 | Restaurant, sit-down Italian, beer and wine only, wood oven, fryer | application.pdf (typed), email.md, loss-runs.md | typed Carrier B, 2026-08-10 | Grease fire Jan 2026 with hood suppression; plain beer and wine wording. |
| 241 | Restaurant, cafe, no alcohol (noodle bowls, coffee) | application.md, email.md, loss-runs.md | no-known-loss letter, **no date** (declared undated) | Letter has no valued date; owner says it is all he can get. |
| 242 | Wholesale, frozen seafood distributor, cold storage (not a retail or office shape) | application.md, email.md, loss-runs.md | typed Carrier A, **no valued line** (declared undated) | Carrier A layout with the valuation line missing. |
| 243 | Retail, bicycle shop and repair bench (allow-list retail shape) | application.md, email.md, schedule.csv, loss-runs.md | typed Carrier A, 2026-04-14, no claims | Single-row schedule matches application. |
| 244 | Contractor, roofing (tear-off and install, 9 trucks) | application.md, email.md | **none** (loss run promised "Friday") | Missing loss run; incomplete on purpose. |
| 245 | Residential apartments, 12 units, two storeys, one building | application.md, email.md, loss-runs.md | typed Carrier C, 2026-07-21 | Water claim closed; rent roll used as sales. |
| 246 | Office building lessor, 14 suites, professional tenants, two floors | application.md, email.md, schedule.csv, loss-runs.md | typed Carrier A, 2026-05-18 | Roof leak 2024 closed; "no tenant food service" stated. |
| 247 | Deli, counter sandwiches and soups, catering, no beer or wine | application.md, email.md, loss-runs.md | typed Carrier B, 2026-07-08, no claims | Plain "no beer, no wine" wording. |
| 248 | Office building lessor, 6 professional suites | application.md, email.md, loss-runs.md | **dated no-known-loss letter, 2026-09-15** (not a carrier run) | Prior carrier history not included; letter from owner. |
| 249 | Deli plus grocery market (milk, snacks, soda; no alcohol) | application.md, email.md, schedule.csv, loss-runs.md | typed Carrier B, 2026-09-30 (latest valued date in the batch) | Square feet conflict: application 2,800, schedule 3,150 ("appraisal 2025"). |
| 250 | Two operations: tax preparation office (2nd floor) + phone repair retail (ground floor) | application.md, email.md, schedule.csv, loss-runs.md | typed Carrier A, 2026-04-02 | Two operations on one policy; counter theft closed. |
| 251 | Two operations: retail wine shop + tasting room (wine and beer by the glass, no hard liquor, cheese boards) | application.md, email.md, schedule.csv, loss-runs.md | typed Carrier C, 2026-06-20, no claims | Tasting room serves by the glass: possible W1 wording question. Not a bar by name. |
| 252 | Two operations: pub with full bar and fryer/warmer (ground) + two office suites (2nd floor) | application.md, email.md, loss-runs.md | typed Carrier C, 2026-03-03 | Pub with open liquor liability claim; suite count conflict: email 3, application 2. |
| 253 | Restaurant, fast-casual Chinese, wok line and hood, no beer | application.md, email.md, loss-runs_scan.jpg | scanned JPG, Carrier B layout, 2026-08-27 | Scanned loss run; hood suppression discharge 2026. |
| 254 | Wholesale, electrical supplies to contractors (counter pickup, 18,500 sq ft) | application.md, email.md, schedule.csv, loss-runs.md | typed Carrier C, **no valued line** (declared undated) | Forklift racking claim; email says "no date on it I think". |
| 255 | Light manufacturing, custom wood cabinets, table saws, dust collector | application.md, email.md, schedule.csv, loss-runs.md | typed Carrier B, 2026-06-30 | Dust collector fire $38,000, closed. |
| 256 | Residential apartments, 12 units, one building, 1974 | application.md, email.md, schedule.csv, loss-runs.pdf | image-only PDF, Carrier C layout, 2026-05-05 | Image-only loss run. |
| 257 | Retail, thrift and clothing, donations in back | application.md, email.md, schedule.csv, loss-runs.md | typed Carrier A, 2026-09-01 | Revenue conflict: application $412,000, email about $540,000 (accountant used the tax form number). |

In-scope coverage (20): W1 prohibited 3 (238, 239, 252); two-operation with a tasting room, possible W1 wording question 1 (251); allow-list-style retail, office and deli 7 (243, 246, 247, 248, 249, 250, 257); referral-style restaurant, wholesale, contractor, apartments and manufacturing 9 (240, 241, 242, 244, 245, 253, 254, 255, 256). Office-lessor 2 (246, 248); deli-style 2 (247, 249); two-operation 3 (250, 251, 252). Restaurants and bars with plain wording: 238, 239, 240, 241, 247, 252, 253. Phrases "salad bar", "sushi bar", "espresso bar", "bar snacks": not used in any SUB-238–269 file (checked).

Missing or declared loss-run status, in scope: **undated loss runs (declared, `undated_loss_runs`):** SUB-241 (no-known-loss letter), SUB-242 and SUB-254 (typed carrier runs, no valued line). **No loss run:** SUB-244. **Dated letter instead of carrier run:** SUB-248 (2026-09-15). All other carrier loss runs carry a valued date between 2026-03-03 and 2026-09-30, before the run date 2026-10-21.

Scanned or image-only documents in scope: loss runs SUB-239 (image PDF), SUB-253 (JPG), SUB-256 (image PDF). Their valued lines are inside the image (typed text rendered into the scan).

## Out of scope — SUB-258 to SUB-269 (12)

Criteria: 1 = scanned application, 2 = more than one location, 3 = application not in English, 4 = no identifiable application (email only).

| SUB | Criteria | Class / shape | Documents in folder | Loss run (kind, valued date) | What triggers it |
|---|---|---|---|---|---|
| 258 | 4 | Window tint installer | email.md | none | Email only, no application |
| 259 | 4 | Tree trimming and lot clearing | email.md | none | Email only, no application |
| 260 | 1 | Upholstery and trim shop | application_scan.jpg, email.md, loss-runs.md | typed Carrier B, 2026-06-01, no claims | Scanned application |
| 261 | 1 | Auto parts retail and wholesale | application.pdf (image-only), email.md, schedule.csv, loss-runs.md | typed Carrier A, 2026-08-03 | Image-only PDF application, no text layer |
| 262 | 1 | Dental lab (work orders) | application_scan.jpg, email.md, loss-runs.md | typed Carrier C, 2026-07-14, no claims | Scanned application |
| 263 | 1 + 2 | Sign and print shop, shop in Kerrville + storage unit in Fredericksburg | application_scan.jpg, email.md, schedule.csv (2 rows), loss-runs.md | typed Carrier B, 2026-05-29 | Scanned application; second address in schedule and application |
| 264 | 2 | Diner, two full-kitchen locations | application.md ("Location No. 2"), email.md, schedule.csv (2 rows), loss-runs.md | typed Carrier A, 2026-09-09 | Application names Location No. 2 |
| 265 | 2 | Auto glass and detailing, Loc #1 and Loc #2 | application.md ("Loc #2"), email.md, schedule.csv (2 rows), loss-runs.md | typed Carrier C, 2026-08-20 | Application names Loc #2 |
| 266 | 3 | Laundromat (self serve and drop off) | application.pdf (typed Spanish), email.md, loss-runs.md | typed Carrier B, 2026-06-10 | Spanish application (typed PDF) |
| 267 | 3 | Nail salon | application.md (Spanish letter), email.md, loss-runs.md | typed Carrier C, 2026-07-30, no claims | Spanish application letter |
| 268 | 2 + 3 | Tortilla factory and store, Sucursal 1 and Sucursal 2 | application.pdf (typed Spanish, both branches), email.md, schedule.csv (2 rows), loss-runs.md | typed Carrier A, 2026-09-22 | Spanish application; two branches on form and schedule |
| 269 | 2 + 3 | Cell phone stores, Tienda Norte and Tienda Sur | application.md (Spanish letter, both stores), email.md, schedule.csv (2 rows), loss-runs.md | typed Carrier B, 2026-08-12, no claims | Spanish letter; two stores on the letter and in the schedule |

Counts as built: criterion 1: 4 (260, 261, 262, 263). Criterion 2: 5 (263, 264, 265, 268, 269). Criterion 3: 4 (266, 267, 268, 269). Criterion 4: 2 (258, 259). Files with two criteria: 3 (263 = 1+2; 268 = 2+3; 269 = 2+3). Files with criterion 4 alone: 2 (258, 259). Out-of-scope loss runs all carry a valued date from 2026-05-29 to 2026-09-22 (none undated).

## Freeze and checks

- Build: `.venv/bin/python simulation/inbox/build_SUB-238-269.py` (rerun is idempotent, it deletes SUB-238 to SUB-269 first and rebuilds).
- Inventory check run: 32 folders, file lists and valued dates as above. Scan and image-PDF types checked with `file` (JPEG 1275x1650, PDF 1 page). The rendered text of the scans was not read back.
- Not done, by role: no lint, no gold, no pipeline, no scorer. No `team/`, `deliverables/`, outbox or workbench writes. No commit.
- Known limit for the orchestrator: the lint reads `loss-run*` by name; `loss-runs.md` and `loss-runs_scan.jpg` / `loss-runs.pdf` names follow the T-108 pattern.

## Freeze note (T-117), 2026-10-21 (written by the orchestrator)

- Code under test: `ai-team` commit **8d605ac** (`8d605acce37f06f719b5a865a79d783bc3e9c800`, P-069 freeze), prompt version **759b3e6bc9b2**, scorer **v11** sha256 `7ddcfb50521b7af17f00c0e148891ca40008d019ce257b9b5d121c7fa6d3fcbb`, lint sha256 `01147a7532bdd7f1ec00861200d1d5e6bbf87f12612389416ff58b78844ea653`.
- Submissions: `simulation/inbox/SUB-238` … `SUB-269` (32), built by `simulation/inbox/build_SUB-238-269.py`; never extracted, never run, no model call.
- Gold frozen: `deliverables/senior-underwriter/gold-set/SUB-238.md` … `SUB-269.md` plus `T-117-routes.md`. Manifest `deliverables/senior-underwriter/T-117-gold-manifest.sha256` (33 per-file sha256 lines). **Manifest sha256 = `9ab5960db77f49e02b27518fb13eaff7a0ceb8d6e78c498c430bd2ba350a943d`**.
- Lint before freeze: `.venv/bin/python deliverables/senior-test-engineer/lint_holdout.py deliverables/senior-test-engineer/T-117-plan.json --run-date 2026-10-21` → exit 0, 0 failures, 3 info (declared undated 241, 242, 254), 32 files. A first run failed on gold SUB-239/247/252 (class words in non-class items); fixed in gold only (also SUB-238), recorded in `T-117-gold-summary.md`.
- Not done (not requested in D-119): a @model-risk build check of T-117, and a gold-vs-source comparison as in T-108.
- No score exists: T-117 is not run (D-020: run once, score once, later, with the user's approval).

## Re-freeze note (T-117), 2026-10-21 (written by @senior-underwriter after the @model-risk build check)

- Reason: T-117 check H1 (SUB-246, SUB-248 route carrier_a contradicted R17 strict word rule) and H2 (SUB-249 carried business_type=retail the documents never state). Gold only; no code, prompt, scorer, lint or inbox file changed. Nothing was run.
- Files changed: `gold-set/SUB-246.md` (route carrier_a -> senior_referral, suggested carrier_a), `gold-set/SUB-248.md` (same, hold kept), `gold-set/SUB-249.md` (business_type=retail item removed), `T-117-routes.md` (rows 246, 248, counts carrier_a 0 / senior_referral 16, judgment call 2 removed). Also updated, not in the manifest: `T-117-gold-summary.md`, `deliverables/senior-test-engineer/T-117-plan.json` (routes), `T-117-lint.md`, `T-117-lint.txt`.
- Old manifest sha256: `9ab5960db77f49e02b27518fb13eaff7a0ceb8d6e78c498c430bd2ba350a943d` (superseded).
- **New manifest sha256 = `7e076534432f1276bfe6198643547498b613c4f2b7aceb2ed618314b5e39fd33`** (same method: shasum -a 256 of SUB-238..269.md then T-117-routes.md, 33 lines; sha256 of that file).
- Re-checked after the fix: lint PASS (0 failures, 3 info, 32 files); `--check-gold` 32 ok; `--check-ops-gold` 20 ok.
