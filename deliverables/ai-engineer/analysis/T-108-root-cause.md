# T-108 root cause (SUB-206 to SUB-237), D-113/D-114

- Author: @ai-engineer-assistant (orchestrator session), 2026-10-19. **Analysis only. No code, prompt, gold, scorer or score file was changed. 0 model calls.**
- Method: the 21 saved replies of the official T-108 run (`underwriting_pipeline/cache/T-108-live/extractions/`, run id `20261019T140831-50315`) were read directly; the frozen scorer v7 (`underwriting_pipeline/ai/eval_holdout_v7.py`) and the scope detector (`underwriting_pipeline/ai/scope.py`, `scope-v3`) were read to name the rule that produced each mark. Nothing was run through the pipeline. The marks reproduced here are exactly the published `deliverables/ai-engineer/evals/SUB-206-237-holdout-v7.json`.
- Classes, one per mark: **extraction** (the model read the document wrongly), **prompt** (the instruction text caused it), **check** (a gate or rule in the pipeline), **OCR** (the scan text), **scorer** (the frozen v7 comparison), **gold convention** (how the gold line is written).
- Headline: of the 17 silent errors, **0 are the model reading a document wrongly except one loss run (SUB-224, OCR)**. **7 of 8 loss-run "misses" are a scorer convention artifact** (v7 reads the first date in the gold "Loss runs" line, which is the policy-period start, not the valuation date), and **9 of 9 operations "misses" are a gold-convention/scorer-wording artifact** (the answer carries the facts; one checklist phrase differs). The one true pipeline safety failure is the **SUB-233 scope leak**.

## (a) The 17 silent errors

A silent error = a value is shown, the scorer counts it wrong, and it is not flagged `needs_review` and not in an open conflict (D-084). All 17 are `operations` (9) or `loss_runs` (8). No other field has a silent error; every other field is 18/20 or better and flagged correctly when uncertain.

### Group 1 — loss runs, 7 of 8: scorer convention (gold line first date)

Every in-scope file with a recognised carrier loss run is marked **miss** although the pipeline returns the correct valuation date. Cause: `loss_run_mark` (v7 line 414/466) takes `date = re.search(r"20\d\d-\d\d-\d\d", gold["loss runs"])` — the **first** date anywhere in the gold "Loss runs" line. In every T-108 gold card the line reads "Carrier X format, 3 policy periods <start> to <end>, valued as of <valuation date>, …", so the first date is the **policy-period start**, and the pipeline's valuation date never contains it. The answer is right; the scorer compares it to the wrong date.

| SUB | source text (valuation line) | pipeline answer | gold valuation date | scorer's first date | why no flag |
|---|---|---|---|---|---|
| SUB-206 | `loss-runs.md: Valued as of: 2026-08-15` | 2026-08-15 | 2026-08-15 | 2023-06-01 (period start) | value shown, conf 1.0, nothing uncertain |
| SUB-207 | `loss-runs.md: Valuation date: 2026-07-31` | 2026-07-31 | 2026-07-31 | 2023-02-01 | same |
| SUB-210 | `loss-runs.md: Valued: 2026-06-30` | 2026-06-30 | 2026-06-30 | 2023-07-01 | same |
| SUB-213 | `loss-runs.md: Valued as of: 2026-04-30` | 2026-04-30 | 2026-04-30 | 2023-04-01 | same |
| SUB-215 | `loss-runs.md: Valuation date: 2026-07-15` | 2026-07-15 | 2026-07-15 | 2022-08-01 | same |
| SUB-221 | `loss-runs.md: Valued as of: 2026-08-20` | 2026-08-20 | 2026-08-20 | 2023-08-01 | same |
| SUB-222 | `loss-runs.md: Valued: 2026-05-27` | 2026-05-27 | 2026-05-27 | 2023-08-01 | same |

Class: **scorer** (the metric, not the pipeline). The value the underwriter sees is correct in all seven. Note this is a *published v7 result*; per D-020/D-025 the scorer is frozen and this is recorded as a finding, not fixed. It also means the loss-run column **understates** the pipeline: the published row for `loss_runs` is 5 hit / 7 flagged / 8 silent, and **7 of those 8 silent marks are a correct valuation date compared to the policy-period start**. Corrected, the field would be **12 hit / 7 flagged / 1 silent** (the 1 silent being SUB-224). Backlog row B-435.

### Group 2 — loss run, 1 of 8: extraction/OCR

| SUB | source | pipeline answer | gold | why no flag |
|---|---|---|---|---|
| SUB-224 | `loss-runs.jpg` (scanned carrier run; gold valuation 2026-07-06) | 2026-08-05 | 2026-07-06 | read from a scan; conf 1.0, **not** flagged |

Class: **OCR/extraction** — the scan was transcribed with the wrong day (07-06 → 08-05). The one genuine loss-run error in the set is a scanned document read with no review flag, even though the pipeline's own `REASON_LOW_SCAN` exists for exactly this. Worth a check: a scanned loss run should be `needs_review` (D-084 flagged), which would have made it a *flagged* value, not a silent one. Backlog row B-435 covers the scan-flag gap alongside the scoring.

### Group 3 — operations, 9 of 9: gold-convention wording (checklist phrase differs)

The checklist rule (`ops_items_hit`, v7 line 319) needs every gold `Operations items` phrase present together and in order in one clause. In all nine files the answer carries the underlying facts; one or more gold phrases are worded/ordered differently, so `found()` fails and the whole field is a **miss** — and because nothing is uncertain, no flag fires.

| SUB | gold item(s) not matched | pipeline answer says | why no flag |
|---|---|---|---|
| SUB-207 | `24 seats` | "Retail seating for 24." | value shown, conf 1.0; check found no rule item missing |
| SUB-208 | `craft supplies` | "craft and hobby supplies" | same |
| SUB-209 | `25% subcontracted` | "approximately 25% of work subcontracted" | same |
| SUB-211 | `beer wine liquor`; `closes 11 p.m.`; `no late-night entertainment` | "Full bar (beer, wine, liquor)"; "Closes at 11 p.m."; "No dancing or late-night entertainment" | same |
| SUB-215 | `canned goods` | "canned and dry goods" | same |
| SUB-218 | `no packaging` | "no processing or packaging" | same |
| SUB-220 | `18 seats` | "limited seating for 18" | same |
| SUB-221 | `owner marketing the space` | "Owner is marketing the space." | same |
| SUB-222 | `open until 2:00 a.m.` | "open until 2:00 a.m.:" | same |

Class: **gold convention** (the gold line writes the phrase one way, the document/model another). This is the same shape the B-427 analysis found on the B-415 dev set: the answer holds the facts; the mark is the gold's own wording. It is not a model failure. It *is* a real lesson for gold writing: the checklist convention should use the documents' words, and where the model rephrases, the field is a miss by design. Two sub-cases deserve a look because they are not pure wording:
- **SUB-211** — the answer truncates ("…Cooking operations: Mesquite grill and smoker, Type I hood and ansul" with no closing items) and repeats; even a tolerant rule may miss `closes 11 p.m.` and `no late-night entertainment`. This one is partly **extraction/prompt** (the model's operations answer is long and self-repeating), not only gold convention.
- **SUB-220** — the answer repeats "Wok range, Type I hood and ansul" as a second trailing clause; `18 seats` still appears as "seating for 18". Gold convention.

Backlog row B-436 (operations: distinguish gold-wording misses from the SUB-211 truncation, which is a model/prompt issue).

### The 17 in one line
- **Scorer convention: 7** (loss-run first-date). **Extraction/OCR: 1** (SUB-224). **Gold-convention wording: 9** (operations).
- **Prompt: 0** direct. **Check (a missing gate): 0** — no gate should have flagged these values, because the values are not wrong; only SUB-224's unflagged scan is a check gap (a scan should be `needs_review`).

### Compare with the previous sets

| Set | Scored | Silent | Rate | Fields | Cause mix |
|---|---|---|---|---|---|
| SUB-154–173 (B-415 dev, v4) | 180 | **6** (the number to compare) | 0.033 | operations 6 | all gold-convention wording (dev gold had no items line; v4 word rule wanted gold's own words) |
| SUB-174–205 (T-104 hold-out, v6) | 180 | **3** | 0.017 | operations 3 | all gold-convention wording (B-427: same shape as SUB-154–173) |
| **SUB-206–237 (T-108 hold-out, v7)** | 180 | **17** | 0.094 | operations 9, loss_runs 8 | **7 scorer convention (new; loss-run first-date), 1 OCR (SUB-224), 9 gold convention** |

For T-108 the published rows are `operations` 9 hit / 2 flagged / 9 silent and `loss_runs` 5 hit / 7 flagged / 8 silent.

Note on the "6": the number 6 belongs to the **B-415 dev set SUB-154–173** (v4); the **T-104 hold-out SUB-174–205 (v6) had 3**. Both are operations-only, gold-convention. The user's phrase "T-104 (6 silent errors)" conflates the two; this report gives both.

**What changed:** the T-108 silent count jumped to 17 (9.4%) from 3–6 (1.7–3.3%). Two new contributors:
1. **Loss runs entered the silent set for the first time (8).** T-104's loss runs were 9 hit / 8 miss / 3 not credited with 0 silent because in T-104 the reported value was `null`+flagged or a date flagged "not a real past date". In T-108 the gold loss-run lines carry a **policy-period start date first**, so v7's first-date rule turns a *correct* valuation date into a silent miss. This is a **measurement regression introduced by the run-date/gold interaction**, not by a code change (the v6→v7 change is in the loss-run mark only, and the T-104 run date was before the typed dates, which is why it flagged them).
2. **Operations stayed the same class but doubled (9 vs 3).** T-108 gold writes richer `Operations items` lines (P-055/D-103 convention), so there are more phrases to mismatch. Same root: gold convention.

**Bottom line:** no code changed between T-104 and T-108 (`457f1bf` is the pipeline for both lineage); the silent-error rise is **dominated by the scorer's loss-run date rule interacting with the new gold-line format (7)**, plus the richer operations checklist (9 gold-convention). Only **1 of 17** is a real read error (SUB-224, OCR) and only it points at a pipeline flag gap.

## (b) The SUB-233 leak

SUB-233 (Amarillo Auto Salon LLC) is gold-out-of-scope on **criterion 2, multiple locations**. The application names two premises in one field:

```
Premises address: Loc 1: 3412 S Georgia St, Amarillo, TX 79109; Loc #2: 6901 Bell St, Amarillo, TX 79106
```

**Why the detector missed it.** `scope.py` (scope-v3) detects multiple locations only through label regexes that require the location marker at the **start of a line**, as a **list item**, or as a **schedule cell**: `LOC_LABELS` (`(loc 2)` / `Location 2:` at line start), `NUMBERED` (a line that *begins* with "Loc"/"Location"/"Building"/"Premises" + number), `LOC_ORDINAL` ("second location"), `LOC_HEADING` ("Locations:") . In SUB-233 neither "Loc 1" nor "Loc #2" is at line start — both sit **inside the value of the "Premises address:" line**, separated by ";" and ":". Running the detector's own regexes against the file returns **no match** (verified read-only). The only premises line the detector sees is a single `Premises address:` line, which it reads as one premises. There is no schedule file, and the home/`LOC_LABELS` "(loc N)" pattern needs parentheses. So `multiple_locations` never fires and the file is judged **in scope** — a "near-pass form" the gold card itself flags ("no schedule file exists, but the application's own location list carries the second location").

This is a **check** gap: a genuine second location expressed inside a premises field, not as a schedule row or a line-leading label.

**Why send was enabled.** The scope result drives the whole record: `prepare.process_submission` only takes the out-of-scope branch (`_manual_intake`, `prepare.py:1024`) when the detector returns out-of-scope. Because the detector said in-scope, SUB-233 was processed normally: fields were extracted, a route was computed (provisional), a missing-info draft was formed, and the status was an ordinary in-scope status — which is **not** in `REFUSED_STATUSES = ("extraction_failed", "all_values_rejected", "manual_intake")` (`prepare.py:31`). The send gate refuses only by status (`prepare.py:1344`: `refused = report.get("status") in REFUSED_STATUSES`); it does **not** re-run the scope check independently. So with an in-scope status, the gate did not refuse, and the file was send-enabled. The leak is therefore **one** failure (the detector's missed near-pass form) that propagates to all four leak symptoms (field shown, provisional route, draft, send enabled) — there is no second, independent guard.

**Consequence and the fix.** Leakage 1/12 (must be 0) and detection recall 11/12 (criterion 2 4/5) — both fail on this one file. Fix (B-432): extend the multiple-location detection to read location markers **inside the premises value** (e.g. a `Loc N:` / `Location #N:` token after ";" or ":" within a premises/address line), with a dev self-check using a SUB-233-shaped file; then a fresh frozen run for 0 leaks / 12/12. Not a scorer change. Optionally, a defence-in-depth second guard (a scope re-check inside the send gate) would stop a detector miss from reaching send — worth proposing separately.
