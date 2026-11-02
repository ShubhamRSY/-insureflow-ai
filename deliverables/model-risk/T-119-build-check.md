# T-119 build check — hold-out SUB-340–371 (@model-risk, 2026-10-23)

Independent check of the build before the gold manifest is frozen. It also serves as the B-457 look-again on the two lint gold fixes (SUB-348, SUB-349). Not a production approval. The T-027 veto stands.

## What I re-ran or recomputed (read only, no pipeline, no model, no scorer on submissions)
- Builder `simulation/inbox/build_SUB-340-371.py` read in full. Every gold value for SUB-340–359 checked against the builder and the built files: named insured, premises, effective date, sales, TIV, construction, year built, claims count and paid, and operations. All match. Typed PDFs (344, 351, 352, 356, 364, 369) have a text layer. Scans (361, 370 image-only PDF; 360, 368 JPEG) have none.
- Loss runs: re-checked every `loss-runs.md` against the `CARRIER_RUN_FORMATS` regexes (my own copy of them, not the pipeline). All 26 runs match a published layout: in scope, Carrier A 8, Carrier B 4, Carrier C 6. Every valued date equals the gold "valued as of" line and falls before 2026-10-23. Undated: 350 (owner letter) and 359 (no file), as declared. No `| None reported |` rows.
- Routes: each of the 20 rows in T-119-routes.md re-derived from carrier-match.md (R1–R17, W1/W2, D-125). The route column is correct for all 20. There are 4 direct Carrier A routes (340–343).
- Scope: the criteria for 360–371 match the files. Counts are 1:4, 2:5, 3:4, 4:3, two-criteria 4.
- Reuse: grep of every insured name and premises address against all other inbox folders and gold cards found no reuse. "Azul" in SUB-123 is a different business.
- The mix file is timestamped before the first gold card.
- Lint re-run: `lint_holdout.py T-119-plan.json --run-date 2026-10-23` (v11, sha256 7ddcfb50…fcbb, unchanged since 8d605ac) gives **PASS, 0 failures, 1 info**.
- Conflict needles recomputed with v11 `sides_stored` from each gold Conflict line:
  - 344: `3200, 2450, 2025`
  - 345: `42 million`
  - 346: `8, 9`
  - 348: `1900 sq`
  - 349: `1700 sq`

## High

**H1. The SUB-348 and SUB-349 conflict marks (the B-457 look-again fix) cannot be earned by a correct answer. SUB-344 has the same defect in a milder form.**

The lint fix added "1900 sq ft" and "1700 sq ft" to the cooking conflict lines only to give v11 a needle. The disputed sides are cooking "None" against stove top and flat grill (348), and None, Yes and griddle (349). Square footage is not in dispute.

v11 marks "flagged" only when an open conflict contains the string `1900 sq` / `1700 sq`. No document has that string: the application says `Square footage: 1,900`. So:
- a pipeline that correctly holds the file on the cooking conflict and quotes both sides scores a miss;
- any open conflict that happens to write "1900 sq ft" scores a hit.

The lint passes only because its "perfect answer" copies the gold line. The test of the test is circumvented, not satisfied. The gold for this slot is now shaped by the scorer, not by the documents.

SUB-344 has the same defect: the line carries "appraisal 2025", so `2025` becomes a required needle that is not a side of the dispute. A correct 3200-vs-2450 conflict without the year scores a miss.

Remediation, before the gold manifest sha256 is recorded, owner @senior-underwriter with @senior-test-engineer:
- **(a) SUB-344:** move "appraisal 2025" out of the Conflict line into notes, so the needles are only `3200` and `2450`.
- **(b) SUB-348 and SUB-349:** either
  - remove the sq-ft needle, write the conflict as the documents state it, and have @user decide (as D-127 did for cooking) that these two conflict marks are not measurable under v11, are reported separately, and are excluded from the conflict rate; or
  - keep the line as it is, with the same written @user decision and exclusion recorded in T-119-gold-summary.md and the plan before freeze.

Either way, re-run the lint and record the result, then @model-risk looks again (B-457).

## Medium (backlog, one line each)
- M1. SUB-345's needle is `42 million` (from "$1.42 million"): it checks the email's wording, not the 1240000 side. SUB-346's needles `8` and `9` are met by almost any conflict text. Fix the wording in the same pass as H1 where possible.
- M2. The lint record on file is stale. T-119-lint.txt/.md show the pre-fix FAIL (3 failures). The post-fix PASS and the gold manifest sha256 are not recorded yet.
- M3. The D-127 "no cooking" list in T-119-gold-summary.md omits SUB-344, whose card carries `no cooking`. The true set is 14, not 13, and the results list it separately.

## Low (one line each)
- L1. Claim dates fall outside the only policy term shown in 352 (2025-10-11), 354 (2025-09-06), 358 (2025-11-03) and OOS 362. The documents are internally inconsistent. Claims are not a v11 slot.
- L2. SUB-371 criterion 2 rests on the email alone, with no application or schedule. P-055 precedent reads criterion 2 from the application or schedule, so reason accuracy (reported, not a gate) may show a false "not".
- L3. Suggested market only, route unchanged:
  - 344 ("office" + contractor) and 350 (wholesale + "plumbing") could read as R7;
  - the 348/349 Line of business "no liquor" contains the W2d word "liquor".
- L4. Single-term loss runs are accepted as recognised, per T-117; a 5-year history is not tested.

## Verdict: BLOCK (freeze and scoring)
- Everything else passes: gold vs builder, scope, routes, valued dates, carrier formats, no reuse, ≥3 Carrier A, ≥3 figure conflicts (344/345/346), and lint PASS on re-run.
- H1 must close before the gold manifest is frozen: the 348/349 conflict needles, and the 344 `2025` needle.
- Nothing has been run or scored, so the fix is gold-only and cheap.
- Not a production approval.
