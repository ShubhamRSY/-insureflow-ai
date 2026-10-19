# T-108 mix — the producer's intent (not gold)

- Written by the orchestrator from @producer's build reports and the builder scripts `simulation/inbox/build_SUB-206-225.py` and `build_SUB-226-237.py` (the producer role cannot write deliverables/), 2026-10-19, D-113. Not gold: scope labels, statuses and routes in gold come only from @senior-underwriter, from the documents and the written rules. This file is not shown to the gold writer.
- Code freeze for this hold-out: `ai-team` commit **457f1bf** (workbench B-428/B-411 fix), prompt version **759b3e6bc9b2** (P-059), scorer **v7**. The 34 inbox files of T-108 were written 2026-10-19 and have not been run, extracted or scored.
- Build rules from the T-027 gate memo (D-109, resolution 2): loss runs valued before the run date; at least two held prohibited-class files; at least two office-lessor / deli-style class files.

## In scope — SUB-206 to SUB-225 (20)

| SUB | Producer's intent | Documents written | Loss run (kind + valued date) | Producer's intended status |
|---|---|---|---|---|
| 206 | Office building lessor, 22 suites (Carrier A shape) | application.md, email.md, schedule.csv, loss-runs.md | typed Carrier A, 2026-08-15 | complete |
| 207 | Deli / sub shop, counter service | application.pdf (typed), email.md, loss-runs.md | typed Carrier B, 2026-07-31 | complete |
| 208 | Wholesale craft and hobby distributor | application.md, email.md, schedule.csv | none | incomplete (no loss run) |
| 209 | Concrete flatwork contractor (boundary: scanned loss run; revenue conflict) | application.md, email.md, loss-runs_scan.jpg | scanned JPG Carrier B, 2026-06-15 | incomplete (2026-10-01 revenue conflict $1,248,000 vs email ~$1.6M) |
| 210 | 14-unit garden apartments (Carrier C shape) | application.md, email.md, schedule.xlsx, loss-runs.md | typed Carrier C, 2026-06-30 | complete |
| 211 | Full-service restaurant, mesquite grill and full bar (address conflict) | application.md, email.md, loss-runs.pdf (image-only) | image-only PDF Carrier B, 2026-07-20 | incomplete (address: email "on Guadalupe" vs application 1120 Commerce St) |
| 212 | Interior finish carpentry contractor | application.md, email.md, loss-runs.md | no-known-loss letter (no date) | incomplete (no carrier run) |
| 213 | Office building lessor, 9 professional suites (Carrier A shape) | application.md, email.md, schedule.csv, loss-runs.md | typed Carrier A, 2026-04-30 | complete |
| 214 | Retail outdoor gear and apparel | application.md, email.md, schedule.csv | none | incomplete (no loss run) |
| 215 | Deli and sandwich shop with a small market | application.pdf (typed), email.md, loss-runs.md | typed Carrier B, 2026-07-15 | complete |
| 216 | Paper and packaging wholesale distributor (sq ft conflict; loss run with no valued date) | application.md, email.md, schedule.csv, loss-runs.md | typed Carrier A, **no valued line** | incomplete (application 24,500 sq ft vs schedule 18,900 sq ft) |
| 217 | 10-unit wood-frame apartments — partial, then 224 completes it (duplicate pair) | application.md, email.md, loss-runs.jpg | scanned JPG Carrier C, 2026-08-05 | incomplete (schedule missing) |
| 218 | Refrigerated cold-storage warehouse, ammonia plant | application.md, email.md, schedule.xlsx, loss-runs.pdf (image-only) | image-only PDF Carrier C, 2026-08-31 | complete |
| 219 | Light manufacturing: paint and solvent coatings, hazardous goods (address conflict; loss run with no valued date) | application.md, email.md, schedule.csv, loss-runs.md | typed Carrier C, **no valued line** | incomplete (address: application Port Arthur vs schedule Groves) |
| 220 | Fast-casual Chinese restaurant, wok and hood | application.md, email.md, loss-runs.md | no-known-loss letter (no date) | incomplete (no carrier run) |
| 221 | Retail strip center, 100% vacant | application.pdf (typed), email.md, schedule.xlsx, loss-runs.md | typed Carrier A, 2026-08-20 | complete (vacancy stated) |
| 222 | **Held prohibited class:** nightclub, 2 a.m., full liquor, DJ and dance floor, no kitchen (W1 shape) | application.md, email.md, loss-runs.md | typed Carrier C, 2026-05-27 | incomplete (year built not on the application; email says the owner is checking with the county) |
| 223 | 12-unit older apartments, no sprinklers | application.md, email.md, schedule.csv, loss-runs.md | owner-written loss history "as of 2026-08-28" (not a carrier layout) | incomplete (no carrier loss run) |
| 224 | Cypress Bend Apartments, 10 units — complete resubmission of 217 | application.md, email.md, schedule.xlsx, loss-runs.md | typed Carrier C, 2026-07-06 | complete |
| 225 | **Held prohibited class:** lounge and bar, full liquor, 2 a.m., DJ, no kitchen, no year built (W1 shape) | application.md, email.md, loss-runs.pdf (image-only) | image-only PDF Carrier C, 2026-06-01 | incomplete (year built not on the application; email says the broker is checking) |

## Out of scope — SUB-226 to SUB-237 (12)

Criteria: 1 = scanned application, 2 = more than one location, 3 = application not in English, 4 = no identifiable application (email only).

| SUB | Producer's intent | Documents written | Criteria | What triggers it |
|---|---|---|---|---|
| 226 | Commercial drywall contractor | email.md | 4 | no application at all; facts only in the email |
| 227 | Landscape contractor | email.md | 4 | no application at all; facts only in the email |
| 228 | Machine shop | application_scan.jpg, email.md, loss-runs.md | 1 | scanned application |
| 229 | Print and copy retail | application.pdf (image-only), email.md, schedule.csv, loss-runs.md | 1 | image-only PDF application (no text layer) |
| 230 | Veterinary clinic | application_scan.jpg, email.md, loss-summary.pdf | 1 | scanned application |
| 231 | Feed and grain retail | application_scan.jpg, email.md, schedule.xlsx (2 rows), loss-runs.md | 1 + 2 | scanned application; "Building 1" … "Bldg 2 (warehouse)" |
| 232 | Tex-Mex restaurant | application.md, email.md, schedule.csv (2 rows), loss-runs.md | 2 | application names "Location No. 2" |
| 233 | Auto detailing and salon | application.md, email.md, loss-runs.md | 2 | application names "Loc #2" |
| 234 | Bakery (Spanish) | application.pdf (typed, Spanish), email.md, loss-runs.md | 3 | Spanish application "SOLICITUD DE SEGURO" |
| 235 | Beauty salon (Spanish) | application.md (Spanish letter), email.md, loss-runs.md | 3 | Spanish application letter |
| 236 | Taqueria (Spanish, two branches) | application.pdf (typed Spanish, text layer, Sucursal 1 and Sucursal 2 on the form), email.md, schedule.csv, loss-runs.md | 3 + 2 | Spanish application; both branches on the form and in the schedule |
| 237 | Furniture retail (Spanish, near-pass) | application.md (Spanish letter), email.md, schedule.csv (2 rows), loss-runs.md | 3 + 2 | Spanish letter; "Tienda 1 / Tienda 2", second store also in the email |

Counts as built: criterion 1: 4 (228, 229, 230, 231); criterion 2: 5 (231, 232, 233, 236, 237); criterion 3: 4 (234, 235, 236, 237); criterion 4: 2 (226, 227); files with two criteria: 3 (231, 236, 237); files carrying criterion 4 alone: 2 (226, 227). Out-of-scope files have no scope label or route in the mix (gold carries both).

## Coverage required by the gate memo

- **Held prohibited-class files (2):** SUB-222 (nightclub, full liquor) and SUB-225 (lounge and bar, full liquor). Both are incomplete on purpose: the year built is not on the application, and both emails say so. No rule label, class code or rule ID appears anywhere in SUB-206 to SUB-237 (checked 2026-10-19).
- **Office-lessor files (2):** SUB-206, SUB-213. **Deli / sub-shop files (2):** SUB-207, SUB-215.
- **Duplicate pair:** SUB-217 (partial) and SUB-224 (complete) are the same insured, Cypress Bend Apartments.
- **Loss runs with no valued date, to be declared in the plan (`undated_loss_runs`):** SUB-216, SUB-219 (typed carrier runs with no valued line), SUB-212, SUB-220 (no-known-loss letters), SUB-229, SUB-233, SUB-235 (out of scope). Everything else carries a valued date before 2026-09-30; the latest is SUB-231 at 2026-09-28.

## Producer's route intent (old rules, not verified, not gold)

Carrier A 5 (206, 208, 213, 214, 216), Carrier B 4 (207, 209, 212, 215), Carrier C 3 (210, 217, 224), senior referral 6 (211, 218, 219, 220, 221, 223), no match 2 (222, 225). The producer cannot read `deliverables/head-of-underwriting/carrier-match.md`, so these shapes are intent only. They are wrong under the current rules on purpose-built evidence: under P-049..P-062 Carrier A is the only direct route and Carrier B and C are suggested markets only (P-049, D-097), so everything that is not an allow-list office, retail or wholesale file, and not a prohibited class, is a senior referral with a suggested market. The plan's routes are the gold routes, stated under the current rules by @senior-underwriter in `deliverables/senior-underwriter/T-108-routes.md` and transcribed into `T-108-plan.json` by @senior-test-engineer: **carrier_a 2 (206, 213), senior_referral 16, no_match 2 (222, 225), carrier_b 0, carrier_c 0**. The lint compares plan against gold, and the pipeline against gold only when T-108 is run later. The two allow-list offices are the direct-route check; the wholesale files (208, 214, 216) and the W2 files (218, 219, 221) must **not** reach Carrier A.

## Lint notes

- The lint reads loss runs by name (`loss-run*`) and cannot read an `.xlsx` loss run at all (`text_of` returns None, a FAIL). SUB-213 and SUB-221 were therefore built with a typed `loss-runs.md` in the same Carrier A layout, keeping their xlsx schedules. Extending the lint to xlsx loss runs is B-429.
- Scanned JPG and image-only PDF loss runs (209, 211, 217, 218, 225) were checked with the lint's own readers before the freeze (tesseract / pdftoppm): each yields a readable valued date before 2026-09-30.

## Freeze note (T-108), 2026-10-19

- Code under test: `ai-team` commit **457f1bf** (the B-428/B-411 workbench fix), prompt version **759b3e6bc9b2** (P-059), scorer **v7**. No pipeline change after this freeze; any later change needs a new freeze note.
- Submissions: `simulation/inbox/SUB-206` … `SUB-237`, 32 files, written 2026-10-19, never extracted, never run, no model call.
- Gold frozen: `deliverables/senior-underwriter/gold-set/SUB-206.md` … `SUB-237.md` (32 files) plus `deliverables/senior-underwriter/T-108-routes.md`. Manifest: 33 sha256 lines (per-file) over those files. **Manifest sha256 = `7a26b81efbc4794276462caa6ca1a2a84fcbc38d54e6ca6e4534dde10ca02257`** (re-taken after the presentation-only polish pass below; the earlier manifest `196152332a…` covered the same judgements before that pass). Frozen before any run; gold is changed only by a new decision and a new freeze note (D-020).
- Polish pass before the freeze, presentation only: seven `- Expected recommendation:` lines rewritten as finished statements (207, 208, 210, 211, 212, 214, 215), the duplicated `- Expected carrier route:` line removed from SUB-208 and SUB-214 (@model-risk L1), one scope line tidied (SUB-211). No status, route, rule reference or judgement changed. The lint was re-run after the pass: exit 0, 0 failures, 7 info.
- Gold writing deviation of record: the gold was written by @senior-underwriter from the documents and the written rules only; for the scanned documents (209, 217 loss runs and the out-of-scope scans) the writer transcribed the page text with `tesseract` / `pdftoppm` as a **document reader**. No pipeline, extraction, scope detector, scorer or `deliverables/ai-engineer/` artifact was read or run. Raise with the user at wrap-up; revert or redo if the user prefers a human or vision read.
- Plan and lint: `deliverables/senior-test-engineer/T-108-plan.json`; `.venv/bin/python deliverables/senior-test-engineer/lint_holdout.py deliverables/senior-test-engineer/T-108-plan.json --run-date 2026-10-19` → **exit 0**, 0 failures, 7 info (the seven declared undated loss runs), 32 files. Written up in `deliverables/senior-test-engineer/T-108-lint.md`.
- No score exists: the pipeline is not run on T-108 (D-020: gold first, run once, score once, later, with the user's approval).
- Known limit for the backlog: `lint_holdout.py` cannot read an `.xlsx` loss run at all (B-429).
