# T-110 — T-108 re-measured with scorer v9 (P-065), field by field

- Task: T-110. Proposal: P-065 (scorer v9 = B-437 F1/F2/F3 + the gold-writing guide). Date: 2026-10-19. Author: @ai-engineer-assistant (orchestrator session).
- Inputs: `underwriting_pipeline/ai/eval_holdout_v9.py` (new, uncommitted), corrected gold copy `deliverables/senior-underwriter/gold-set-T-108-corrected/` (32 cards + README; 13 valued-as-of lines inserted, review cards 208/212/214/216/219/220/223 unchanged), lint output `deliverables/senior-test-engineer/T-110-lint-T-108-corrected-gold.txt` (PASS, exit 0).
- Method (D-069): `HOLDOUT_RESCORE=1`, `HOLDOUT_GOLD=…-corrected`, `HOLDOUT_IDS=206-237`, `LLM_CACHE_DIR` = a temp copy of the cache, `LLM_PACE_SECONDS=0`, `--write`. **0 model calls** (every call served from the copy). Nothing written to the real cache, the token log, `team/`, the inbox or the outboxes.
- Output: `deliverables/ai-engineer/evals/SUB-206-237-holdout-v9-cache-rescore.{json,md}` (a re-score writes its own `-cache-rescore` files, B-363; the published v7 score files are untouched).
- Cause notes were produced from the *actual* report of each submission (`prepare.process_submission`), the cached model reply (cache key = `report["cache_key"]`) and the gold card — never from a filename guess.

## Gates

| Gate | v7 published (original gold) | v9 re-measure (corrected gold) | Verdict |
|---|---|---|---|
| Route accuracy | 18/20 | 18/20 | PASS (≥18/20) |
| Unsafe routes | 0 | 0 | PASS |
| False completes | 0 | 0 | PASS |
| Scope leaks | 1 (SUB-233) | 0 (scope-v4 on this code) | PASS on dev |
| Field floor (9 fields ≥18/20) | fails: operations 9, loss_runs 5 | **fails: operations 10/20, loss_runs 16/20** | B-433 not closed |

Two changes are in this number, so it is not a like-for-like scorer delta: the gold correction (valued-as-of lines) and scorer v9. Published v7 scores stay as published (D-015/D-020).

## Per-field: v7 → v9

| Field | v7 | v9 |
|---|---|---|
| named_insured / premises / effective_date / sales / construction / year_built | 20/20 | 20/20 |
| operations | 9/20 | **10/20** |
| tiv | 19/20 | 19/20 |
| loss_runs | 5 hit, 9 miss, 6 not_credited | **16 hit, 4 not_credited** |
| conflict | 10/20 | 15/20 |
| status | 15/20 | 15/20 |
| route | 18/20 | 18/20 |

Files that changed mark: loss_runs 206/207/210/213/215/216/218/219/221/222/224 → hit; conflict 210/213/218/221/224 → hit (F1, `Conflict: none (…)`); operations 222 → hit (F2, a.m./p.m. in an item).

## Every remaining miss, with its cause

Class: **R** = real pipeline miss (the pipeline lost or got wrong something a human can read) · **D** = an approved rule doing exactly what it says, gold disagrees · **M** = measurement (the answer states the fact, the scorer's words do not match).

### operations — 10 misses, **all M**

| File | Failing gold item | Why |
|---|---|---|
| 206 | "office building lessor" | answer: "Building owner/lessor only … office building" — words present, not in one clause in order |
| 207 | "24 seats" | answer: "Retail seating for 24" |
| 208 | "craft supplies" | answer: "craft and hobby supplies" |
| 209 | "25% subcontracted" | answer: "approximately 25% of work subcontracted" |
| 211 | "beer wine liquor" · "closes 11 p.m." · "no late-night entertainment" | comma list splits the clause · answer "closes at 11 p.m." · "No dancing or late-night entertainment" |
| 215 | "canned goods" | answer: "(canned and dry goods" |
| 218 | "no packaging" | answer: "no processing or packaging" |
| 220 | "18 seats" | answer: "limited seating for 18" |
| 221 | "owner marketing the space" | answer: "Owner is marketing the space" |
| 225 | "bar snacks only" · "no cooking" | answer: "beyond bar snacks" · "No kitchen" |

Every one of the ten answers states the fact; none drops an operation. Under the approved checklist rule (v5, `ops_items_hit`, eval_holdout_v9.py:368) they are still misses. **Zero real misses in operations.**

### loss_runs — 4 not_credited

| File | Model returned | Gate that dropped it | Class |
|---|---|---|---|
| 217 | `2026-08-05`, quote "Valued: 2026-08-05" (line is in the OCR text) | the OCR word list scores that date token **0.0** → `confidence 0.00 is under 0.75` (llm_extract.py:30,499) | **R** |
| 209 | `2026-06-15`, quote "Valuation date: 2026~06-15" | OCR garbles the date, word score 0.35 → dropped at the same gate | **R** |
| 225 | `2026-06-91` (OCR reads day as 91) | `value_in_span` → "the date does not parse" (llm_extract.py:397-400) | **R** |
| 211 | nothing — the model is never shown the file | image-only PDF is `needs_human`, its text is empty (`len 0`) | **D** |

tesseract at 200 dpi read all four pages correctly (Valuation/Valued dates 2026-06-15, 2026-07-20, 2026-08-05, 2026-06-01), so the documents are readable; the pipeline's own OCR pass is what fails. **The loss-run floor gap is OCR quality plus the confidence/parse gates, not the extraction prompt.**

Also: `prepare.py:1057-1059` skips a rejected row, so the field card shows `value=None, reason=None` — the underwriter is told nothing about *why* the date is missing (D-065: every block needs a plain-language reason).

### conflict — 5 misses

| File | Cause | Class |
|---|---|---|
| 211 | the model returned **no** conflict; gold expects the email's "just moved them to their new spot on Guadalupe" vs 1120 Commerce St | **R** |
| 209 | the model **did** flag sales 1248000 vs 1600000; the email quote crosses a line break → citation rejected → D-086/P-038(c) folds it into the field reason (`conflict with rejected value: …`), no conflict card | **D** (scorer reads cards only) |
| 219 | the model **did** flag the premises conflict; the schedule side is reformatted with commas, so the value is not inside its own quote → same D-086 fold | **D** |
| 214 | the conflict **is** in the report (0 vs 890000); `sides_stored`'s needle is `0 tenant` (eval_holdout_v9.py:445-450) and the blob holds `$0 (tenant)` | **M** |
| 216 | the conflict **is** in the report (24500 vs 18900); the needle `24500 vs` never appears in JSON | **M** |

### status — 5 misses · route — 2 · tiv — 1

| File | Cause | Class |
|---|---|---|
| 206, 213, 218 | all fields present, status `complete — review pending`, `report.complete` is False vs gold "complete" (prepare.py:1142-1144) | **D** (B-325: review pending is safe, not automated) |
| 207, 215 | no "liquor" cue in a food-service text → `extra = ["liquor sales"]` → complete forced False (prepare.py:1121-1144) | **D** (P-015 T2 ask) |
| 206 | route `senior_referral` with note "words not on the Carrier A allow-list: owns, leases, suites, tenants, common" and `suggested: carrier_a`; gold says carrier_a | **D** (carrier-match rules P-049) |
| 213 | `therapy` in the tenant list is on the R14 lab/medical list (workbench.py:145-146) → senior_referral; gold says carrier_a with "verify: no lab or medical" | **D** |
| 214 | an open conflict nulls the field by design (prepare.py:1104-1106); gold still says `TIV: 0` | **D** |

**Totals: 4 real misses (loss_runs 217/209/225, conflict 211); the other 26 marks are an approved rule or a measurement artefact.**

## B-433 verdict

Rule: operations **and** loss_runs ≥18/20 → close as a measurement issue; otherwise draft a P-### for the real misses only and stop for the user's approval.

- operations 10/20, loss_runs 16/20 → **not closed**.
- Real misses only → **P-067** drafted: `deliverables/ai-engineer/proposal-P-067.md` (loss-run reasons on the card + a scan loss-run date that is cited and parseable kept for review instead of dropped).
- Operations has no real miss, so it is not in P-067: closing that half needs a user decision (the model quoting the documents' wording vs a gold/scorer wording rule) — asked in the same turn.
- B-439 (`Building 2` fail-closed widening → manual intake) stays as it is; nothing here touches it.

## For the AI Engineer

- Pending proposals: **P-067** (awaiting `approve change P-067`), plus the operations-wording decision.
- Scores on dev: route 18/20, 0 unsafe, 0 false completes, 0 leaks; operations 10/20, loss_runs 16/20 (both below the floor).
- Top failure to fix next: the pipeline's OCR on loss-run images (3 of the 4 loss-run not-credits), then the operations wording decision.
