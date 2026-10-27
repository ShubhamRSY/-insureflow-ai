# T-108 gold cards vs builder source data — comparison report

- Author: @senior-underwriter
- Date: 2026-10-19
- Task: T-108 (compare-and-report only; nothing edited, nothing run)
- Reference used: the **builder scripts' source data**, not OCR. For each id, the gold card
  `deliverables/senior-underwriter/gold-set/SUB-<n>.md` was compared field by field against the
  per-submission section of `simulation/inbox/build_SUB-206-225.py` (SUB-206..225) or
  `simulation/inbox/build_SUB-226-237.py` (SUB-228..236): the `fields = {…}` dict, the
  `email_md(...)` body, the `schedule_csv`/`schedule_xlsx` rows, and the `lr_carrier_a/b/c/d/e(...)`
  lines. Submission file names/types under `simulation/inbox/SUB-<n>/` were read only to confirm.
- Not done (per instructions): no pipeline, scorer, lint, extraction or OCR run; `team/`,
  `deliverables/ai-engineer/`, `underwriting_pipeline/` and eval/scorer files not read.

## Headline

- The 10 scanned / image-only submissions checked here are **all faithful to the builder source
  data**. The OCR transcription of the scans introduced **no numerical or wording drift** on any
  field: named insured, addresses, dates, sales, TIV, square footage, construction, year built,
  stories, sprinklers, cooking, operations tokens, loss-run carrier/layout, policy periods,
  valued-as-of date, every claim (date, cause, paid, reserve, status), counts/paid/open totals,
  the conflict line, the missing line and the scope line all match.
- Only three cards show any difference, and only one is substantive: **SUB-214** attributes a scan
  claim to the email that the email does not contain. **SUB-206** and **SUB-208** have a
  wording-only scope slip ("no schedule" although a one-row `schedule.csv` exists).

---

## SUB-206
Difference (wording only; conclusion unaffected):

| SUB | field | gold value | source value | difference |
|---|---|---|---|---|
| SUB-206 | Scope | "…no scan, **no schedule**; no scope criterion applies" | folder has `schedule.csv` (one data row) | Gold says there is no schedule, but a single-row schedule.csv exists. No P-055 criterion triggers (criterion 2 is 2+ address rows), so the in-scope call stands. |

Matched: named insured, premises, effective date, operations wording, operations items, sales
742000, building TIV 2450000, square footage 41500, construction Masonry, year built 2005,
stories 3, sprinklers Yes, cooking None, loss-run carrier/layout (Carrier A), policy periods
2023-06-01→2026-06-01, valued-as-of 2026-08-15, claim (2024-07-18 broken water pipe, $6400,
closed), counts 1 / paid $6400 / open $0, conflict none, missing none, format.

## SUB-207
Entirely faithful to the source data. Matched: named insured, premises, effective date,
operations wording, operations items, sales 612000, TIV 0 (tenant), square footage 1850,
construction Masonry, year built 1968, sprinklers No, cooking None (cold prep), loss-run
carrier/layout (Carrier B), periods 2023-02-01→2026-02-01, valuation date 2026-07-31, no claims,
counts 0 / $0 / $0, conflict none, missing none, scope, format.

## SUB-208
Difference (wording only; conclusion unaffected):

| SUB | field | gold value | source value | difference |
|---|---|---|---|---|
| SUB-208 | Scope | "…no scan, **no schedule**; no scope criterion applies" | folder has `schedule.csv` (one data row) | Gold says there is no schedule, but a single-row schedule.csv exists. No P-055 criterion triggers, so the in-scope call stands. |

Matched: named insured, premises, effective date, operations wording, operations items, sales
1480000, TIV 640000, square footage 12400, construction Tilt-up concrete, year built 1998,
sprinklers Yes, cooking None, loss run absent (email says coming), claims 0, missing (5-yr loss
runs + open-claims flag), conflict none, format.

## SUB-209 (scanned loss run)
Entirely faithful to the source data. Matched: named insured, premises, effective date,
operations wording, operations items, sales 1248000, TIV 0 (tenant), square footage 2200,
construction Masonry, year built 1991, cooking None, loss-run carrier/layout (Carrier B,
transcribed from `loss-runs_scan.jpg`), periods 2023-09-01→2026-09-01, valued 2026-06-15, claim
(2025-03-12 trailer hit client fence, $2150, closed), counts 1 / paid $2150 / open $0, conflict
(sales: app $1,248,000 vs email "around 1.6 mil") — present in the source, missing (GL sales
reconcile), scope, format.

## SUB-210
Entirely faithful to the source data. Matched: named insured, premises, effective date,
operations wording, operations items, sales 224000, TIV 2350000, square footage 16800,
construction Masonry, year built 1996, stories 2, sprinklers Yes, cooking (tenant electric
ranges), loss-run carrier/layout (Carrier C), periods 2023-07-01→2026-07-01, valued 2026-06-30,
claim (2024-12-09 water damage frozen pipe, $11200, closed), counts 1 / $11200 / $0, conflict
none, missing none, scope, format.

## SUB-211 (image-only loss run)
Entirely faithful to the source data. Matched: named insured, premises, effective date,
operations wording, operations items, sales 1980000, TIV 0 (tenant), square footage 3600,
construction Masonry, year built 1994, cooking (mesquite grill and smoker, Type I hood, ansul),
loss-run carrier/layout (Carrier B, transcribed from `loss-runs.pdf`), periods
2023-03-01→2026-03-01, valued 2026-07-20, claim (2025-02-08 kitchen hood fire, $24500, closed),
counts 1 / $24500 / $0, conflict none, missing none, scope, format.

## SUB-212
Entirely faithful to the source data. Matched: named insured, premises, effective date,
operations wording, operations items, sales 740000, TIV 0 (tenant), square footage (not stated
in source — gold correctly omits it), construction Masonry, year built 1984, cooking None,
loss-run format (no-known-loss letter, not a carrier layout), valued-as-of none, claims 0,
missing (recognised carrier run), conflict none, scope, format.

## SUB-213
Entirely faithful to the source data. Matched: named insured, premises, effective date,
operations wording, operations items, sales 388000, TIV 1980000, square footage 32600,
construction Masonry, year built 2008, sprinklers Yes, cooking None, loss-run carrier/layout
(Carrier A), periods 2023-04-01→2026-04-01, valued 2026-04-30, claim (2024-10-02 roof leak
storm, $8900, closed), counts 1 / $8900 / $0, conflict none, missing none, scope, format.

## SUB-214
Difference (substantive — unsupported statement):

| SUB | field | gold value | source value | difference |
|---|---|---|---|---|
| SUB-214 | Source note + scope (email content) | "email.md (mentions a scan…)" and "The email's 'app is a scan' is not supported by the actual file type present" | `email_md(...)` for SUB-214 says only "App is attached, I typed it up… Schedule attached." The word "scan" does not appear | Gold asserts a scan reference in the email that the source email does not contain (confused with SUB-229/SUB-230, whose emails do mention scans). The file-type conclusion (application.md is typed) is right; the stated reason is wrong. |

Matched: named insured, premises, effective date, operations wording, operations items, sales
1120000, TIV 0 (application) vs schedule bldg_tiv 890000, square footage 9800, construction
Masonry, year built 2003, loss run absent, claims 0, missing (loss runs + open-claims flag),
conflict (TIV app vs schedule) — present in source, format, in-scope conclusion.

## SUB-215
Entirely faithful to the source data. Matched: named insured, premises, effective date,
operations wording, operations items, sales 845000, TIV 0 (tenant), square footage 2400,
construction Masonry, year built 1986, cooking None (cold prep), loss-run carrier/layout
(Carrier B), periods 2022-08-01→2025-08-01, valued 2026-07-15, claim (2024-01-19 customer slip
on wet floor, $3750, closed), counts 1 / $3750 / $0, conflict none, missing (has valued date),
scope, format.

## SUB-216
Entirely faithful to the source data. Matched: named insured, premises, effective date,
operations wording, operations items, sales 2140000, TIV 1390000, square footage app 24500 vs
schedule 18900, construction Tilt-up concrete, year built 1996, sprinklers Yes, cooking None,
loss-run carrier/layout (Carrier A, **no** valued-as-of line), periods 2023-08-01→2026-08-01,
claim (2024-06-27 forklift damaged rack, $5100, closed), counts 1 / $5100 / $0, conflict (square
footage) — present in source, missing (valued-as-of date), scope, format.

## SUB-217 (scanned loss run)
Entirely faithful to the source data. Matched: named insured, premises, effective date,
operations wording, operations items, sales 171000, TIV 1290000, square footage 9800,
construction Wood frame, year built 1979, stories 2, sprinklers Yes, cooking (tenant electric
ranges only), loss-run carrier/layout (Carrier C, transcribed from `loss-runs.jpg`), periods
2023-05-01→2026-05-01, valued 2026-08-05, claim (2024-09-15 hail/roof, $14600, open $0), counts
1 / $14600 / $0, conflict none, missing (schedule, partial package), scope, format.

## SUB-218 (image-only loss run)
Entirely faithful to the source data. Matched: named insured, premises, effective date,
operations wording, operations items, sales 3620000, TIV 4200000, square footage 46500,
construction Fire-resistive, year built 2001, sprinklers Yes, cooking None, loss-run
carrier/layout (Carrier C, transcribed from `loss-runs.pdf`), periods 2023-04-01→2026-04-01,
valued 2026-08-31, claim (2025-04-02 ammonia leak no injury, $7400, open $0), counts 1 / $7400 /
$0, conflict none, missing none, scope, format.

## SUB-219
Entirely faithful to the source data. Matched: named insured, premises, effective date,
operations wording, operations items, sales 1740000, TIV 1450000, square footage 28600,
construction Fire-resistive, year built 1989, sprinklers Yes, cooking None, loss-run
carrier/layout (Carrier C, **no** valued-as-of line), periods 2023-02-01→2026-02-01, claim
(2024-11-21 solvent spill cleanup, $9800, open $0), counts 1 / $9800 / $0, conflict (premises:
app 2701 Memorial Blvd, Port Arthur vs schedule 4810 Twin City Hwy, Groves) — present in source,
missing (valued-as-of date), scope, format.

## SUB-220
Entirely faithful to the source data. Matched: named insured, premises, effective date,
operations wording, operations items, sales 690000, TIV 0 (tenant), square footage 1600,
construction Masonry, year built 1999, sprinklers Yes, cooking (wok range, Type I hood, ansul),
loss-run format (no-known-loss letter), claims 0, missing (carrier loss runs), conflict none,
scope, format.

## SUB-221
Entirely faithful to the source data. Matched: named insured, mailing (PO Box 1188, Odessa TX
79760), premises, effective date, operations wording, operations items, sales 0, TIV 1650000,
BPP 0, square footage 22000, construction Masonry, year built 1985, sprinklers Yes, cooking None,
loss-run carrier/layout (Carrier A), periods 2023-08-01→2026-08-01, valued 2026-08-20, claim
(2025-03-04 roof leak/storm, $4600, open $0), counts 1 / $4600 / $0, conflict none, missing none,
scope, format.

## SUB-222
Entirely faithful to the source data. Matched: named insured, premises, effective date,
operations wording, operations items, sales 1980000, TIV 1250000, square footage 8600,
construction Masonry, year built not stated (gold: "not in documents"), stories 2, sprinklers
Yes, cooking (bar snacks only), loss-run carrier/layout (Carrier C), periods
2023-08-01→2026-08-01, valued 2026-05-27, claim (2025-01-12 broken window, $1900, open $0),
counts 1 / $1900 / $0, missing (year built), conflict none, scope, format.

## SUB-223
Entirely faithful to the source data. Matched: named insured, premises, effective date,
operations wording, operations items, sales 168000, TIV 1180000, square footage 11200,
construction Wood frame, year built 1974, stories 2, sprinklers No, cooking (tenant electric
ranges only), loss-run format (owner-prepared summary as of 2026-08-28, not a carrier layout),
periods 2022–2026 no losses, claims 0, missing (carrier run), conflict none, scope, format.

## SUB-224
Entirely faithful to the source data. Matched: named insured, premises, effective date,
operations wording, operations items, sales 171000, TIV 1290000, square footage 9800,
construction Wood frame, year built 1979, stories 2, sprinklers Yes, cooking (tenant electric
ranges only), loss-run carrier/layout (Carrier C), periods 2023-05-01→2026-05-01, valued
2026-07-06, claim (2024-09-15 hail/roof, $14600, open $0), counts 1 / $14600 / $0, conflict
none, missing none, scope, format.

## SUB-225 (image-only loss run)
Entirely faithful to the source data. Matched: named insured, premises, effective date,
operations wording, operations items, sales 1140000, TIV 940000, square footage 7200,
construction Masonry, year built not stated (gold: "not in documents"), stories 1, sprinklers
Yes, cooking (bar snacks only), loss-run carrier/layout (Carrier C, transcribed from
`loss-runs.pdf`), periods 2023-05-01→2026-05-01, valued 2026-06-01, claim (2024-06-14 water
damage, $3300, open $0), counts 1 / $3300 / $0, missing (year built), conflict none, scope,
format.

## SUB-228 (scanned application)
Entirely faithful to the source data. Matched: named insured, premises, effective date,
operations wording, operations items, sales 1060000, TIV 720000, BPP 335000, square footage
9400, construction Masonry, year built 1988, sprinklers No, cooking None, loss-run carrier/layout
(Carrier D), periods 2023-02-01→2026-02-01, valued 2026-08-30, claim (2024-03-05 cut hand no
lost time, $1200, closed), counts 1 / $1200 / $0, conflict none, missing ("not assessed"), scope
(criterion 1, scanned JPG), format.

## SUB-229 (image-only application)
Entirely faithful to the source data. Matched: named insured, premises, effective date,
operations wording, operations items, sales 486000, TIV 0 (tenant), BPP 155000, square footage
2900, construction Masonry, year built 1992, sprinklers No, cooking None, loss-run format
(no-known-loss letter), claims 0, conflict none (one-row schedule matches), missing ("not
assessed"), scope (criterion 1, image-only PDF), format.

## SUB-230 (scanned application)
Entirely faithful to the source data. Matched: named insured, premises, effective date,
operations wording, operations items, sales 890000, TIV 980000, BPP 210000, square footage 4600,
construction Masonry, year built 2007, sprinklers Yes, cooking None, loss-run format
(office-manager summary as of 2026-08-22, four years 2023–2026, one 2025-04-17 dog bite $2800
closed), counts 1 / $2800 / $0, conflict none, missing ("not assessed"), scope (criterion 1,
scanned JPG), format.

## SUB-231 (scanned application, multi-location)
Entirely faithful to the source data. Matched: named insured, premises (Building 1 1802 W
Dickinson Blvd; Bldg 2 1908 W Dickinson Blvd, both Fort Stockton TX 79735), effective date,
operations wording, operations items, sales 1320000, TIV 940000 (store 540000 + warehouse
400000), BPP 180000, square footage 12600 (8200 + 4400), construction Metal, year built
1990/2004, sprinklers No, cooking None, loss-run carrier/layout (Carrier D), periods
2023-02-15→2026-02-15, valued 2026-09-28, no claims, counts 0 / $0 / $0, conflict none (two-row
xlsx matches application), missing ("not assessed"), scope (criteria 1+2), format.

## SUB-236 (typed Spanish, multi-location)
Entirely faithful to the source data. Matched: named insured, premises (Sucursal 1 4809 Maple
Ave, Dallas TX 75219; Sucursal 2 1123 Singleton Blvd, Dallas TX 75212), effective date,
operations wording (plancha y freidora, campana Tipo I con ansul, cerveza solamente, sin licor),
operations items, sales 1540000, TIV 0 (both tenant), square footage 3400 (1900 + 1500),
construction Mamposteria (Masonry), year built 1988/1999, sprinklers No, loss-run carrier/layout
(Carrier E), periods 2023-12-01→2026-12-01, valued 2026-08-11, claim (2025-01-24 water damage
sucursal 1, $3900, open $0), counts 1 / $3900 / $0, conflict none (two-row csv matches), missing
("not assessed"), scope (criteria 2+3; confirms application is a typed PDF with a text layer,
not a scan), format.

---

## Summary of differences

| SUB | differing fields | verdict |
|---|---|---|
| SUB-206 | 1 (scope wording "no schedule") | Minor; conclusion unchanged |
| SUB-208 | 1 (scope wording "no schedule") | Minor; conclusion unchanged |
| SUB-214 | 1 (unsupported "email mentions a scan") | Substantive wording error; file-type conclusion still correct |
| all other ids (207, 209, 210, 211, 212, 213, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 228, 229, 230, 231, 236) | 0 | Faithful to the builder source data |

Note: the four cards that name a **conflict** (SUB-209 sales, SUB-214 TIV, SUB-216 square footage,
SUB-219 premises address) all rest on data genuinely present in the builder scripts. This first pass
also reported SUB-211 as matching, but its card then carried `Conflict: none` while the source email
("their new spot on Guadalupe") disagrees with the application premises (1120 Commerce St). That was a
missed conflict in this report; @model-risk caught it on re-check and SUB-211 was corrected to
`incomplete — hold: open conflict` (addendum below).

## Addendum (2026-10-19, after the @model-risk M2 re-check)

Correction to the summary above: SUB-211 is **not** "no differences". The report compared field values
but did not flag that the source email names a different location from the application. @model-risk's
re-check (`deliverables/model-risk/T-108-M2-close.md`) raised it as H1; the gold was corrected:

| SUB | field | before | after | reason |
|---|---|---|---|---|
| SUB-211 | Conflict | `none` | premises — application 1120 Commerce St vs email "their new spot on Guadalupe"; material, unresolved | source email asserts a relocation against the application premises |
| SUB-211 | Status | `complete` | `incomplete — hold: open conflict` | exposure location unresolved |
| SUB-211 | Expected pipeline status | `complete` | `incomplete` | same |
| SUB-230 | Loss runs (Low L1) | "no valued-as-of line" | "as of 2026-08-22" | the office-manager summary does carry "as of 2026-08-22" |

Route unchanged (`senior_referral`, suggested `carrier_b`). Lint re-run exit 0; manifest re-frozen at
`11933e96b8370f57321ce5c1e1c6c3c3105a4f0517d841fbbbb8821bca18633d`.
