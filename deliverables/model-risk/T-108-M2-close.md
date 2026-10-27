# T-108 — M2 closure review (@model-risk)

- Reviewer: @model-risk (independent)
- Date: 2026-10-19
- Task: T-108, follow-up on M2 (gold facts transcribed with OCR)
- Method: read the gold cards and the builder scripts, compared the highest-risk fields myself, re-ran the lint, recomputed the 33-file manifest, checked the freeze elements. I did not rely on the author's summary and did not read the task's author notes before writing this.

## Verdict

- **M2 (the OCR dependency of the gold facts): CLOSED.** The gold facts for the ten scanned / image-only / typed cards no longer depend on an OCR read: every high-risk field I checked matches the builder script's source data, and I found no OCR-induced drift. The three corrections (206, 208, 214) are correct and change no judgement.
- **Freeze: NOT APPROVED — one High finding (H1) blocks it.** The source comparison (the M2 remediation) missed a substantive defect on an in-scope card: SUB-211's gold omits an open premises conflict that the source data contains and labels the file `complete`. The rest of the freeze is in order (code `457f1bf` unchanged, prompt `759b3e6bc9b2`, scorer v7 unchanged, pipeline not run, lint exit 0, manifest reproduces).

## High findings

### H1 — SUB-211 omits an open premises conflict present in the source data; its status is wrong

- Source data, `simulation/inbox/build_SUB-206-225.py`:
  - line 574 (email body): "we just moved them to their new spot **on Guadalupe**."
  - line 582 (`fields["Premises address"]`): "**1120 Commerce St**, Laredo, TX 78040".
- Gold `deliverables/senior-underwriter/gold-set/SUB-211.md`:
  - line 10: `Premises: 1120 Commerce St, Laredo, TX 78040`
  - line 21: `Conflict: none`
  - line 7: `Status: complete`
- The two source statements name different streets, so the source contains a premises inconsistency. The gold does not record it. This is not a judgement I am substituting: the same gold set treats an email statement against the application as a material conflict for SUB-209 (sales), and the prior hold-out gold has the same pattern (SUB-204, sales). The producer also built SUB-211 as an address-conflict file (`deliverables/producer/T-108-mix.md` line 16). The gold writer must decide independently, but `Conflict: none` does not engage with the email's location claim at all.
- Consequence: the expected pipeline status is wrong (`complete` instead of `incomplete — hold: open conflict`). The route is unaffected (`senior_referral`, suggested market `carrier_b` either way), so the lint still passes, but the hold-out's status scoring is contaminated. The report's blanket claim on `T-108-gold-vs-source.md` line 257 ("no card omits a conflict the source data does contain") is false on this card.
- Remediation: record the conflict in SUB-211's Conflict, Status and recommendation lines; update the status in `T-108-routes.md` and the batch-1 table/counts in `T-108-gold-summary.md`; re-run the lint (routes are unchanged, so it should stay green); recompute and re-record the manifest in the freeze note. If @senior-underwriter concludes that "on Guadalupe" is not a premises claim, that reasoning must be written on the card; the card cannot keep `Conflict: none` without it. This is a source-text issue, not an OCR drift: both strings are in the builder script.

## Medium

- None.

## Low

- L1 — SUB-230's gold says the office-manager loss summary has "no valued-as-of line", but the source writes "as of 2026-08-22"; out-of-scope card, no score impact.
- L2 — `team/NEXT-SESSION.md` still records the pre-M2 manifest `7a26b81e…`; stale after the M2 re-freeze.

## Verification performed

### 1. Scanned / image-only / typed cards vs builder source data

| SUB | Source vs gold (high-risk fields) | Result |
|---|---|---|
| SUB-209 | Garcia & Sons Flatwork LLC; 4319 Rittiman Rd; sales 1,248,000; TIV 0; 2,200 sf; 1991; Carrier B valued 2026-06-15; 2025-03-12 trailer hit client fence $2,150/$0 closed | match |
| SUB-217 | Cypress Bend Apartments LLC; 911 N Big Spring St; sales 171,000; TIV 1,290,000; 9,800 sf; 1979; Carrier C valued 2026-08-05; 2024-09-15 hail/roof $14,600/$0 | match |
| SUB-211 | Vaquero Smokehouse & Grill LLC; 1120 Commerce St; sales 1,980,000; TIV 0; 3,600 sf; 1994; Carrier B valued 2026-07-20; 2025-02-08 kitchen hood fire $24,500/$0 | fields match; **conflict omitted — see H1** |
| SUB-218 | Gulf Coast Cold Storage LLC; 5895 Eastex Fwy; sales 3,620,000; TIV 4,200,000; 46,500 sf; 2001; Carrier C valued 2026-08-31; 2025-04-02 ammonia leak $7,400/$0 | match |
| SUB-225 | La Vida Loca Lounge & Bar LLC; 6501 Amarillo Blvd W; sales 1,140,000; TIV 940,000; 7,200 sf; year built absent; Carrier C valued 2026-06-01; 2024-06-14 water damage $3,300/$0 | match |
| SUB-228 | Alamo Hydraulics & Machine LLC; 5920 S Flores St; sales 1,060,000; TIV 720,000; 9,400 sf; 1988; Carrier D valued 2026-08-30; 2024-03-05 cut hand $1,200/$0 closed | match |
| SUB-229 | Harborview Print & Copy LLC; 4101 S Port Ave; sales 486,000; TIV 0; 2,900 sf; 1992; no-known-loss letter | match |
| SUB-230 | Falcon Ridge Veterinary Clinic PLLC; 10760 Kenworthy St; sales 890,000; TIV 980,000; 4,600 sf; 2007; summary as of 2026-08-22; 2025-04-17 dog bite $2,800 closed | match (wording L1) |
| SUB-231 | Pecos Feed & Grain LLC; 1802 + 1908 W Dickinson Blvd; sales 1,320,000; TIV 940,000 (540k+400k); 12,600 sf (8,200+4,400); 1990/2004; Carrier D valued 2026-09-28; no claims | match |
| SUB-236 | Taqueria El Faro LLC; 4809 Maple Ave + 1123 Singleton Blvd; sales 1,540,000; TIV 0 both; 3,400 sf (1,900+1,500); 1988/1999; Carrier E valued 2026-08-11; 2025-01-24 water damage $3,900/$0 | match |

### 2. The three corrections

- SUB-206: Scope now "a one-row schedule (not multi-location)"; source has a one-row `schedule.csv`. In-scope, `complete`, `carrier_a` unchanged.
- SUB-208: same scope correction; source has a one-row `schedule.csv`. `incomplete — hold: loss run missing`, `senior_referral`/`carrier_a` unchanged.
- SUB-214: source note now "email says the application is attached" (source email: "App is attached, I typed it up"), scope note now typed `application.md` / single-row schedule. `incomplete — hold: loss run missing; open conflict`, `senior_referral`/`carrier_a` unchanged.
- All three are wording-only and changed no status, route, rule reference or judgement.

### 3. Lint

`.venv/bin/python deliverables/senior-test-engineer/lint_holdout.py deliverables/senior-test-engineer/T-108-plan.json --run-date 2026-10-19`

- Exit code **0**: `PASS: 0 failure(s), 7 info, 32 files, run date 2026-10-19`.
- The 7 info lines are exactly the seven declared `undated_loss_runs`.

### 4. Gold manifest

- Recomputed over the 32 gold cards `SUB-206`..`SUB-237` plus `T-108-routes.md` (33 files): per-file `sha256` + two spaces + relative path, in file order (206..237 then routes), joined with newlines and a trailing newline.
- Result: **`657c63a97835adfac4815af08e9d06ebf78bb27767859596c040dd0a1cbdc4d0`** — equals the freeze note's value. (The value reproduces in file order; lexicographic sorting of the same lines does not reproduce it, so the order used is part of the recipe.)

### 5. Freeze elements

- Code under test: `457f1bf` exists on `ai-team`; `git diff --name-only 457f1bf` shows **no** changes to `eval_holdout_v7.py`, `prepare.py`, `llm_extract.py` or `workbench.py`. Prompt `759b3e6bc9b2` is present; scorer v7 (`eval_holdout_v7.py`) exists and is unchanged.
- Pipeline not run: no T-108 submission appears in `underwriting_pipeline/cache/` or `deliverables/ai-engineer/`; no T-108 score file exists.
- D-069: `underwriting_pipeline/app/workbench.html` and the three simulation outboxes are untouched (mtimes 2026-10-16).

## Approval

Not a production approval. T-108 is a hold-out; no model is put into production here. The freeze gate is H1 only: once SUB-211 is corrected and the manifest is re-frozen, I have no other objection.

## Re-check (2026-10-19) — H1 remediation

- Reviewer: @model-risk (independent), re-check after the author's SUB-211 correction.
- Method: read the corrected `gold-set/SUB-211.md` against the builder source, spot-read the other corrected cards, re-ran the lint and recomputed the 33-file manifest myself, and re-checked the freeze elements against `457f1bf`. I did not read the author's messages before writing this.

### Verdict

- **H1 (SUB-211): FIXED.** The premises conflict is now recorded and the status is right.
- **M2 (the OCR dependency of the gold facts): stays CLOSED** — no OCR drift reopened, and the H1 that blocked was a source-text omission, not an OCR error.
- **Freeze: APPROVED** (with the caveat below). Code `457f1bf`, prompt `759b3e6bc9b2`, scorer v7 unchanged, T-108 not run, lint exit 0, manifest reproduces. This is not a production approval: T-108 is a hold-out and no model is put into production here; the run itself still needs the user's go (D-020).

### High findings

- None. H1 is closed; I found no new High on re-check.

### Medium

- None.

### Low

- L2 (carried over, still open): `team/NEXT-SESSION.md` line 19 still records the superseded manifest `7a26b81e…`. It is outside the manifest recipe, so it has no effect on the freeze hash; housekeeping only. (The old L1 on SUB-230 is fixed — see below.)

### Verification performed

1. **SUB-211 vs builder source.** `simulation/inbox/build_SUB-206-225.py` line 573-574 (email): "we just moved them to their new spot on Guadalupe"; line 582 (`Premises address`): "1120 Commerce St, Laredo, TX 78040". The corrected card now engages both: `Missing: premises address reconciled (application 1120 Commerce St vs the email's "their new spot on Guadalupe")`, `Conflict: premises — … Material premises conflict; the location of the exposure is unresolved, so no complete status`, `Status: incomplete — hold: open conflict`, `Expected pipeline status: incomplete`. Same pattern as the SUB-209 sales conflict. Correct.
2. **Route unchanged.** SUB-211 is still `senior_referral`, suggested market `carrier_b` (`gold-set/SUB-211.md` line 23; `T-108-routes.md` line 13 now shows `incomplete — hold: open conflict` in the Status column). Other cards unaffected: SUB-206 `complete` / `carrier_a`, SUB-208 `incomplete — hold: loss run missing` / `senior_referral`+`carrier_a`, SUB-214 `incomplete — hold: loss run missing; open conflict` / `senior_referral`+`carrier_a` — all read correctly; SUB-230's Low L1 is fixed (`Loss runs: … the summary carries an as-of date but is not a Carrier A/B/C layout`). Batch-1 counts in `T-108-gold-summary.md` now read complete 5 / incomplete 5, consistent.
3. **Lint.** `.venv/bin/python deliverables/senior-test-engineer/lint_holdout.py deliverables/senior-test-engineer/T-108-plan.json --run-date 2026-10-19` → exit code **0**, `PASS: 0 failure(s), 7 info, 32 files, run date 2026-10-19`. The 7 info lines are the declared `undated_loss_runs`.
4. **Manifest.** Recomputed over the 32 cards `SUB-206`..`SUB-237` plus `T-108-routes.md` (33 files), per-file `sha256` + two spaces + relative path, file order, newline-joined with a trailing newline: **`11933e96b8370f57321ce5c1e1c6c3c3105a4f0517d841fbbbb8821bca18633d`** — equals the value in `T-108-mix.md` line 73.
5. **Freeze elements.** `git diff --name-only 457f1bf` shows no change under `underwriting_pipeline/` or `evaluations/`, and no change to `workbench.py`, `eval_holdout_v7.py`, `prepare.py` or `llm_extract.py`; prompt `759b3e6bc9b2` present; scorer v7 present. No T-108 submission appears in `underwriting_pipeline/cache/`, `deliverables/ai-engineer/` or `evaluations/`; no T-108 score exists. D-069: the workbench page and the simulation outboxes are not touched by this re-check (I changed only this file).
