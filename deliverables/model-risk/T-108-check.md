# T-108 — @model-risk build check (pre-freeze)

- Reviewer: @model-risk (independent)
- Date: 2026-10-19
- Scope: T-108 acceptance criteria, High only in detail; Medium/Low to the backlog.
- Method: read the deliverable and the files it cites, recomputed the counts and the freeze hash, ran the frozen lint myself. I did not read the author's messages about this task.

## Verdict

**The build may NOT be called frozen yet.** One High finding (H1) is an unmet acceptance criterion. Everything else I checked passes: counts, loss-run dates, W1 and office-lessor/deli coverage, gold-first integrity, the freeze hash, the lint, and D-069. H1 is a one-line board fix; once it is closed I have no other objection to the freeze.

## High findings

### H1 — The T-108 board entry does not record the code under test
Criterion 1 requires: "the task records that git SHA, prompt version 759b3e6bc9b2 (P-059) and scorer v7 as the code under test."

- `team/TASKS.md` `### T-108` (line 1711) has no Notes section and records none of the three. A search of `team/TASKS.md` for `457f1bf` returns nothing; `759b3e6bc9b2` appears only inside the criterion text itself (line 1715), not as a recorded value; `scorer v7` is not on the entry.
- The values do exist elsewhere and I verified them independently: `ai-team` commit `457f1bf5784cd8a0c95af72724ca9341be3ba207` is on the branch and its diff contains the `underwriting_pipeline/app/workbench.py` B-428/B-411 fix and the +14-line T-108 board addition; the mix records `457f1bf`, prompt `759b3e6bc9b2` (P-059) and scorer `v7`.
- So the substance of the freeze is in place; the board just does not carry it as the criterion demands. Remediation: add the git SHA, prompt version and scorer version to the T-108 entry (Notes or a `Code under test:` line). No pipeline change is needed.

## What I verified and it passes

- **Freeze hash.** The mix's gold manifest reproduces exactly: sha256 of the sorted `sha256sum`-format lines (hash + path + newline) over the 32 gold cards `SUB-206`..`SUB-237` plus `T-108-routes.md` = `196152332acac46ff8dc07a4872fca29b84d9fd4de595a82249d626af97b51ec`, matching the mix's freeze note (33 files, per-file). Gold hash and code SHA are recorded (criterion 6 met).
- **Lint.** `.venv/bin/python deliverables/senior-test-engineer/lint_holdout.py deliverables/senior-test-engineer/T-108-plan.json --run-date 2026-10-19` → exit 0, `0 failure(s), 7 info, 32 files` (criterion 5 met). The 7 info lines are exactly the 7 declared `undated_loss_runs`.
- **Counts (mix vs plan vs gold).** in 20 / out 12; per_criterion 1:4, 2:5, 3:4, 4:2; two_criteria 3; criterion_4 2; routes carrier_a 2 (206, 213), carrier_b 0, carrier_c 0, senior_referral 16, no_match 2 (222, 225). The routes doc table, the plan JSON and the gold cards agree; the frozen parser reads gold routes the same way. No in-scope route value is `hold` and no out-of-scope card carries a route.
- **Loss-run dates.** Every dated loss-run line in SUB-206..SUB-237 is before the run date 2026-10-19; the latest is SUB-231 at 2026-09-28 (out-of-scope). No late-date FAIL.
- **Coverage (D-109, resolution 2).** W1 held prohibited-class: SUB-222 (nightclub, full liquor) and SUB-225 (lounge/bar, full liquor), both incomplete on a missing year built. Office-lessor: SUB-206, SUB-213. Deli/sub: SUB-207, SUB-215. Duplicate pair SUB-217/SUB-224 present.
- **Gold-first integrity.** No score exists and no pipeline/extraction/scope-detector/scorer artifact was read or run (I searched `team/`, `deliverables/`, `underwriting_pipeline/` and the outboxes: only T-108's own artifacts and the board mention `SUB-206..237`). Every in-scope card has `- Scope:` and `- Operations items:`; every card carries `- Scope:`; empty fields say `not in documents`.
- **D-069.** No real workbench page (`underwriting_pipeline/app/workbench.html`), real log, token log or outbox (`simulation/to-carrier/`, `simulation/to-producer/`, `simulation/pending-approval/`) was written by this task.
- **Fact (b), mix vs plan.** No contradiction. The mix labels its route-intent table "producer's old rules, not verified, not gold" and states the plan's routes explicitly; the intent counts (intent-only) are clearly separated from the plan's route counts.

## Medium

- **M1 — `T-108-gold-summary.md` batch-1 table is stale.** It still lists SUB-209 as `complete` (line 11) and "complete: 6", contradicting the SUB-209 gold card (`incomplete — hold: open conflict (sales)`) and the summary's own correction note (line 77). Fix the table/status counts so a downstream reader cannot mislabel SUB-209.
- **M2 — OCR deviation (fact (a)).** Gold for scanned documents was transcribed with `tesseract`/`pdftoppm`, which the criterion's letter forbids ("no ... OCR script ... run or read"). It does **not** break gold-first integrity: the labels come from the source documents and the written rules, not from the system under test, and no pipeline/scorer output was read. But the reader is the same OCR the pipeline uses for scans, so scanned items share an error mode. Keep the documented deviation and get the user's explicit acceptance at wrap-up (the mix already asks for it); if the user prefers a human/vision read, redo the affected cards before the freeze.

## Low

- **L1** — SUB-208 and SUB-214 each carry `- Expected carrier route:` twice (SUB-208 lines 23/25; SUB-214 lines 23/25). The frozen parser is last-wins and both values are the same route, so nothing changes today; de-duplicate the two cards.
- **L2** — `T-108-gold-summary.md` claims route normalisation left "no `hold`" on the route lines, but SUB-209/210/211/212/214 still show `— hold: ...` on the route line. The route value is a plain rule name and parses correctly, so only the summary's claim is imprecise.
- **L3** — The 12 out-of-scope cards carry more than "- Scope: line and criteria codes only" (full field cards); harmless but a literal stretch of criterion 5.
- **L4** — The mix file mtime is after the gold cards because the freeze note is appended to it; the "mix written before gold" ordering cannot be confirmed from the filesystem alone.

## Approval

Not a production approval. T-108 is a hold-out; no model is being put into production here. The freeze gate is H1 only.
