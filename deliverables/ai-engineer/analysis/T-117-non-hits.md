# T-117 non-hits — cause analysis (read-only)

Run: `20261021T112723-44537`, official run of 2026-10-21, 20 submissions, scorer v11, D-119.
Scope: the 24 non-hits listed in `deliverables/ai-engineer/evals/SUB-238-269-holdout-v11-mismatches.md`
(7 operations, 4 loss_runs, 9 status, 3 conflict, 1 route). Nothing was fixed and nothing was re-scored.

Method: no model call. The run cache was copied to a temporary directory
(`/var/folders/g4/nw3tvq1j6q7c8jjlxwf19c5c0000gn/T/opencode/t117-cachecopy`),
`LLM_CACHE_DIR` was pointed there, `LLM_PACE_SECONDS=0` was set, and
`llm_extract._post` was replaced with a function that raises. Every report below
comes from the cached replies of the official run plus the deterministic rules in
`underwriting_pipeline/ai/prepare.py` and `eval_holdout_v11.py`.
The diagnostics wrote nothing under `simulation/`, `deliverables/` or the real cache/logs.

Classification used:

- **Real miss** — the pipeline failed to carry something the documents state and gold records,
  or a deterministic rule failed, or it raised a hold that the gold says is not needed.
- **Gold/fixture artefact** — the pipeline follows the written rule or the published format,
  but the built fixture or the gold card is inconsistent with it.
- **Predicted-before-run** — already written in the backlog before the run (B-447/B-448).
- **Route (safe)** — neither the gold route nor the used route is a carrier route.

## Count

| Class | Rows | Count |
|---|---|---|
| Real miss | ops 246, 248, 250, 257; status 246, 247, 250, 253, 255, 256; conflict 249, 252, 257 | 13 |
| Predicted-before-run | ops 239, 254 (B-447) | 2 |
| Gold/fixture artefact | ops 244, status 243; loss 238, 245, 251, 252; status 245, 251 | 8 |
| Route (safe) | 252 (B-448) | 1 |
| **Total** | | **24** |

Root causes, in blast-radius order:

| # | Cause | Rows | Backlog |
|---|---|---|---|
| C1 | Carrier C fixtures were built as `Term: <date> to <date>` and `CL-` numbers; the published format (`simulation/carrier-loss-run-formats.md:38-45`) is `Term: <date> - <date>` and `C-`. `carrier_run_check` follows the published format and refuses them; gold calls them recognised. Not a date-reading failure. | loss 238, 245, 251, 252; status 245, 251; latent on 254, 256 | B-453; reason wording B-454/B-455 |
| C2 | The labelled `Cooking operations: None` line is dropped or paraphrased in the operations answer | ops 246, 248, 250, 257; status 246, 250; secondary on 254 | B-451 |
| C3 | The v11 `business_type` reader counts facility/customer words (`small office`, `to contractors`) as classes; the email's `full bar` is not merged | ops 244, 254, 239 | B-447, B-450 L1 |
| C4 | No deterministic conflict backstop: the square-footage rule does not read `Square footage:` or the schedule's `sq_ft`; suite counts and the email's sales figure have no cross-check | conflict 249, 252, 257 | B-452 |
| C5 | False `extra` asks: narrow cooking-equipment cues; `kitchen` in a habitational email triggers restaurant asks | status 247, 256 | new (this analysis) |
| C6 | Grounding/scan review flags (reworded value; OCR-read loss-run date) turn a correct file into review-pending/incomplete | status 253, 255, 256 | new (this analysis) |
| C7 | Gold card 243 omits the stated `Cooking operations: None` item, so gold says complete while the pipeline flags it per the rule | status 243 | B-450 L4 area (gold lint) |

## 1. Operations (7)

The v11 slot diff (gold `- Operations items:` split into `business_type` vs remaining slots;
answer read with `answer_classes` + `_slots`; extra slots ignored):

| File | Answer (stored) | Gold items | Difference | Class |
|---|---|---|---|---|
| 239 | Cocktail lounge, full liquor, live music Fri and Sat, closes around midnight, countertop oven, frozen pizza only | `lounge_nightclub; bar_pub; full liquor; live music Fri and Sat` | classes `{lounge_nightclub}` vs gold `{lounge_nightclub, bar_pub}`; alcohol and entertainment match. The app line has "full liquor"; only the email says "full bar", and the email was not merged. | Predicted (B-447) |
| 244 | Residential and light commercial roofing, tear-off and install; 9 trucks, yard and a small office | `contractor` | classes `{contractor, office}` vs gold `{contractor}`. "small office" is a facility and is explicitly unscored in the gold's own notes (`SUB-244.md:15`); the v11 class reader still reads it as `office`. The value also merges the email into the app quote, which raises the reword flag. | Gold/reader artefact (B-450 L1) |
| 246 | Lessor of office building, 14 suites, professional tenants, no tenant food service | `office; no cooking` | classes match; gold `cooking=none` missing. The app says `Cooking operations: None (no tenant food service)` (`SUB-246/application.md:23`); the answer kept only the parenthetical, and v11's `none` vocabulary has `no cooking / no kitchen / no cooking operations`, not `no tenant food service`. | Real miss (paraphrase) |
| 248 | Lessor of professional office building, six suites | `office; no cooking` | classes match; `no cooking` missing. App line 23 states `Cooking operations: None`; the answer never mentions cooking. | Real miss |
| 250 | Tax preparation office (second floor); cell phone repair and retail accessories (ground floor) | `office; retail; no cooking` | classes match; `no cooking` missing. App line 23 states `Cooking operations: None`. | Real miss |
| 254 | Wholesale electrical supplies to contractors, counter pickup | `wholesale; no cooking` | classes `{wholesale, contractor}` vs gold `{wholesale}`: "to contractors" names the customers, not the insured's class (the gold notes say exactly this). Also `no cooking` missing. The first difference alone fails the mark. | Predicted (B-447); second cause C2 |
| 257 | Thrift retail, used clothing and household goods, donations in the back | `retail; no cooking` | class matches; `no cooking` missing. The model took the email as the operations source (the email does not mention cooking); the app's `Cooking operations: None` (line 23) was not merged. | Real miss |

B-447 predicted three misses; only 239 and 254 materialised (253 hit). It did not foresee
244 or the dropped cooking item (B-457).

## 2. Loss runs (4)

All four are typed `.md` Carrier C documents. `prepare.carrier_run_check` returns
`("no_date", None, None)` on each, so `gate_loss_run` stores null with
`loss run found but no valued-as-of date; ask the producer for a dated carrier loss run (loss-runs.md)`.
That reason is inaccurate (B-454): the dates are present, ISO and parseable. The files are
not scans (no OCR). The check refuses them on the layout, before it reaches `Valued:`.

Published Carrier C format (`simulation/carrier-loss-run-formats.md:38-45`):

```
Term: 2025-04-01 - 2026-04-01
...
| C-1042 | 2025-11-20 | wind/hail | $8,500 | $0 |
```

Frozen regexes (`prepare.CARRIER_RUN_FORMATS["carrier_c"]`):

- period: `Term: (20\d\d-\d\d-\d\d) - (20\d\d-\d\d-\d\d)`
- row: `\| C-\d+ \| 20\d\d-\d\d-\d\d \|[^|]+\|[^|]+\|[^|]+\|`

The T-117 builder passed the Carrier A/B term style and `CL-` numbers into the Carrier C
helper (B-453). The files and the gold, not the pipeline, are off-spec:

| File | Period line (actual) | Period regex | Row (actual) | Row regex | Gold |
|---|---|---|---|---|---|
| 238 | `SUB-238/loss-runs.md:3  Term: 2024-03-01 to 2025-03-01` | fails (`-` vs `to`) | `:8  \| CL-771204 \| ...` | would fail (`C-` vs `CL-`) | valued 2026-06-12 |
| 245 | `SUB-245/loss-runs.md:3  Term: 2024-08-01 to 2025-08-01` | fails | `:8  \| CL-660118 \| ...` | would fail | valued 2026-07-21 |
| 251 | `SUB-251/loss-runs.md:3  Term: 2025-07-01 to 2026-07-01` | fails | `:5  Carrier C: no claims reported.` | n/a | valued 2026-06-20 |
| 252 | `SUB-252/loss-runs.md:3  Term: 2025-03-03 to 2026-03-03` | fails | `:7  \| CL-552901 \| ...` | would fail | valued 2026-03-03 |

The check fails at the period line, so the row regex is never reached. C1's row half is
latent: after fixing the period line, 238/245/252 would still fail on the claim row, and
256 (image-only PDF, `CL-598711`) would fail too if it went through `carrier_run_check`.

Contrast: SUB-254 is the same off-format Carrier C layout with no `Valued:` line at all.
Gold expects null there, the pipeline stores null, and the mark is a hit. SUB-256 is the
same off-format layout on an image-only PDF; it is a "sheet" file, so `gate_loss_run`
skips the `no_date` drop and keeps the model's OCR-read date with a review flag — the
loss-run mark hits, but the status does not (C5/C6).

## 3. Status (9)

The status is derived from all fields, `extra`, open conflicts and the review flags
(`prepare.process_submission`, P-041). The nine files and the single trigger each time:

| File | Stored | Gold | Trigger (exact) | Class |
|---|---|---|---|---|
| 243 | complete — review pending | complete | `operations` needs review: `operations may be missing: no cooking`; app line 23 says `Cooking operations: None`, answer omits it. Gold's own items omit it too (`SUB-243.md:14` is `business_type=retail` only), although the gold rule (D-094, "Cooking … if stated") says it belongs. | Gold artefact (C7) |
| 245 | incomplete | complete | `missing: ["loss_run_valued_through"]`, reason `loss run found but no valued-as-of date` — C1. | Gold/fixture artefact (B-453) |
| 246 | complete — review pending | complete | same `no cooking` flag as 243, but here gold *does* require the item; the answer paraphrased it. | Real miss |
| 247 | incomplete | complete | `extra: ["cooking equipment"]`. The app says `Line of business: Restaurant package, no liquor` (line 12) and lists `Cooking operations: Slicer, flat-top grill, steam table, hood` (line 23); the `extra` cue block looks for `cooking equipment` or `fryer`, so a fully stated equipment line is treated as missing. | Real miss (C5) |
| 250 | complete — review pending | complete | same `no cooking` flag; gold requires it. | Real miss |
| 251 | incomplete | complete | `missing: ["loss_run_valued_through"]` — C1. | Gold/fixture artefact (B-453) |
| 253 | complete — review pending | complete | two flags: `operations` `value is not in the cited text (translated or reworded)` (the answer merges email facts — restaurant, 40 seats, no liquor, no beer — into the app quote), and `loss_run_valued_through` `read from a scan — check it against the page`. Gold reads the scanned JPG and calls the file complete. | Real miss (C6) |
| 255 | complete — review pending | complete | `operations` reworded: the value merges `Cooking operations: None, shop heaters only` and `table saws` into the Operations quote, so it is not a substring of the cited line. | Real miss (C6) |
| 256 | incomplete | complete | `extra: ["cooking equipment", "hood and fire suppression", "liquor sales"]` because the email says `rehabbed kitchens`; an apartment kitchen triggers the restaurant equipment asks. Plus the scan review flag on the loss-run date. | Real miss (C5 + C6) |

Status automation is 1 of 10 gold-complete files (`status_split.gold_complete = 10`,
`automated = 1`). All nine non-hits are in the safe direction: no file is called complete
when gold says incomplete.

## 4. Conflicts (3)

| File | Documents say | Gold conflict | Pipeline | Cause |
|---|---|---|---|---|
| 249 | app `Square footage: 2,800`; email says the application holds the old number; schedule `sq_ft` = `3150` from `appraisal 2025` | square footage: 2800 vs 3150 | `conflicts: []`; `_square_feet(texts)` returns `[]` | C4: the area regex accepts `square feet`, `sq ft`, `sqft`, `sf`, not `Square footage:`; the CSV header is `sq_ft`, which also does not match. The model's raw `conflicts` is `[]`, so there is no fallback. |
| 252 | app `two office suites`; email says three, the third is a storage room | office suites: 2 vs 3 | `conflicts: []` | C4: suite count is not a modelled field and `apply_document_rules` has no cross-check; the model's raw `conflicts` is `[]`. |
| 257 | app `Annual sales: $412,000`; email `about 540k in sales` | sales: 412000 vs 540000 | `conflicts: []`; stored sales 412000 from the app | C4: no deterministic sales cross-check; the model read the email but did not record the disagreement. The file is saved with sales 412000 and only a status hold; the gold has an open conflict. |

Planted-conflict recall is 0/3 (B-452). The correct value is shown, so the silent-error
rate does not see it; the problem is the missing hold.

## 5. Route (1, safe)

SUB-252: gold `no_match` (R1) vs pipeline `senior_referral` (R2). This is B-448, written
before the run, and follows from the open office-suite conflict not being recorded (§4)
plus the pub/office-suite referral rule. Neither route is a carrier route, so the route
gate is still safe (0 unsafe of 20).

## What the run does not show

- No silent error: every operations miss is a review field; every loss-run miss is null with a reason.
- No extraction failure, no retry, no cached reply, no unsafe route, no false complete.
- The 7 operations misses are not scattered: 4 are the same dropped `no cooking` item
  (246 is a paraphrase), 2 are the pre-registered `business_type` reading (239, 254),
  1 is the v11 reader counting an unscored facility word (244).
- The 4 loss-run misses are a **test-fixture defect** (B-453), not an extractor or regex
  defect: the pipeline follows the published format, and the built files do not. The
  wording "cannot read a valued-as-of date" in the run record and mismatches F2 is wrong
  (B-454) and should be corrected by addendum, not by rewriting the score files.
- The 9 status misses reduce to C1 (2), C2 (2), C5 (2), C6 (3), plus the gold-card
  inconsistency on 243 (C7).

## Cross-reference to the backlog

- B-447 — pre-registration: 3 named, 2 materialised (239, 254); 253 hit; 244/246 and the
  cooking line were not foreseen (B-457).
- B-448 — SUB-252 R1 vs R2 still unruled; the one route miss.
- B-450 L1 — SUB-244 "small office" in the gold's Operations line; the v11 reader is the
  other half of that miss.
- B-451 — cooking line dropped: 248/250/254/257; this analysis adds 246 (paraphrase) and
  243 (status/gold inconsistency).
- B-452 — 0/3 planted conflicts; this analysis locates the deterministic gaps (C4).
- B-453 / B-454 / B-455 — Carrier C build format; reason wording; producer asked for a
  date already sent.
- B-456 — the mismatches F1 cause is wrong; the per-file causes are above.
- B-457 — the look-again was skipped and the pre-registration missed 244/246.
- B-458 — same as B-448.
- B-459 L8 — status automation 1/10; 245/251 follow from C1.

## If this is taken forward (no change made here)

Approval path: C4/C5 (deterministic `prepare.py`) can be fixed as ordinary code; C2 (the
cooking line) and anything that touches prompts/extraction (`underwriting_pipeline/ai/`)
or the scorer/gold needs the user's `approve change P-###` first (D-017). C1 is a
test-data fix, not a pipeline change.

1. C1 — rebuild the Carrier C fixtures to the published format (`-`, `C-`) and add the
   B-453 lint: run every built carrier run through the frozen `carrier_run_check` and fail
   the build when it disagrees with the gold "Expected loss run" line. Do not loosen the
   regex to accept the build error. Correct the reason text (B-454/B-455) by addendum.
2. C2 — carry the labelled `Cooking operations:` line into the operations answer (4 ops
   rows, 2 statuses; 1 gold-card fix on 243). Needs an approved P-###.
3. C4 — read `Square footage:`/`sq_ft`, and add deterministic cross-checks for the fields
   the gold already treats as conflicts (sq ft, sales, suite counts). Planted-conflict
   recall 100% from the next hold-out (B-452).
4. C5/C6 — narrow the `extra` cues (equipment words, habitational `kitchen`) and decide the
   scan/grounding policy against the gold's "complete" definition.
5. C7 — reconcile `SUB-243.md` with the D-094 rule (gold change, never a re-score of a
   published score).
