# T-113 — T-108 dev re-score with scorer v10 (P-068), field by field

- Task: T-113. Proposals: P-068 (scorer v10, operations scored on facts not wording) and P-067 (loss-run scan dates + rejected-value reasons). Date: 2026-10-20. Author: @ai-engineer-assistant (orchestrator session).
- Inputs: `underwriting_pipeline/ai/eval_holdout_v10.py`; corrected gold copy `deliverables/senior-underwriter/gold-set-T-108-corrected/` (32 cards + README); lint `deliverables/senior-test-engineer/lint_holdout.py` (default scorer v10; `--self-check` PASS).
- Method (D-069): `HOLDOUT_RESCORE=1`, `HOLDOUT_GOLD=…-corrected`, `HOLDOUT_IDS=206-237`, `LLM_CACHE_DIR` = a temp copy of `underwriting_pipeline/cache/T-108-live`, `LLM_PACE_SECONDS=0`, `--write`. **0 model calls** (every call served from the copy; 0 call_failed). Nothing written to the real cache, the token log, `team/`, the inbox or the outboxes.
- Output: `deliverables/ai-engineer/evals/P-068-dev/SUB-206-237-holdout-v10-cache-rescore.{json,md}`. This is a development re-check, not a hold-out.
- Cause notes come from the actual report of each submission (`prepare.process_submission`) and the gold card.

Two code changes are folded into this number, so it is not a like-for-like scorer delta:
1. **P-068** (scorer v10): operations items scored on facts, not wording — normalised numbers/units and a short synonym list per checklist item, from `operations-gold-rule.md`, not from T-108 phrasing.
2. **P-067** (committed in 1da0066, plus the 2026-10-20 follow-up fix): the scan loss-run date gate, the three `import prepare` script-mode fixes, and the rejected-value reason now carried to the card. The three import fixes are why the 4 `call_failed` in the pre-fix run (209/217/218/225) are gone.

## Gates

| Gate | v9 re-measure | v10 dev re-score | Verdict |
|---|---|---|---|
| Route accuracy | 18/20 | 18/20 | PASS (≥18/20) |
| Unsafe routes | 0 | 0 | PASS |
| False completes | 0 | 0 | PASS |
| Scope leaks | 0 | 0 | PASS |
| Field floor (9 fields ≥18/20) | fails: operations 10/20, loss_runs 16/20 | **fails: operations 19/20, loss_runs 17/20** | B-433 not closed |

## Per-field: v9 → v10

| Field | v9 | v10 |
|---|---|---|
| named_insured / premises / effective_date / sales / construction / year_built | 20/20 | 20/20 |
| operations | 10/20 | **19/20** |
| tiv | 19/20 | 19/20 |
| loss_runs | 16 hit, 4 not_credited | **17 hit, 0 miss, 3 not_credited** |
| conflict | 15/20 | 15/20 |
| status | 15/20 | 15/20 |
| route | 18/20 | 18/20 |

Silent errors: 1 of 180 (0.006). Automation rate: 0.878. Status automation: 3 of 8 gold-complete files shown plain "complete".

Files that changed mark: operations 206/207/208/209/211/215/218/220/221/225 → hit (v10 facts-not-wording); loss_runs 217 → hit (P-067 scan-date keep; was not_credited in v9).

## Every remaining miss, with its cause

Class: **R** = real pipeline miss (the pipeline lost or got wrong something a human can read) · **D** = an approved rule doing exactly what it says, gold disagrees · **M** = measurement (the answer states the fact, the scorer's words do not match).

### operations — 1 miss (SUB-211), class M

| File | Failing gold item | Why |
|---|---|---|
| 211 | one hours/no-dancing item | answer "Closes at 11 p.m. No dancing or late-night entertainment." — the item survives the v10 normaliser on the other nine files; this one still misses on a clause-boundary/synonym detail |

The other nine v9 operations misses (206/207/208/209/215/218/220/221/225) are now hits under v10. **No real operations miss remains.**

### loss_runs — 3 not_credited

| File | Model returned | Gate that dropped it | Class |
|---|---|---|---|
| 209 | `2026-06-15`, quote "Valuation date: 2026~06-15" | OCR garbles the date, digits do not match the text → dropped; card now **shows** "value not inside the cited text" (P-067 reason fix) | **R** (OCR) |
| 225 | `2026-06-91` (OCR reads day as 91) | `value_in_span` → "the date does not parse"; card now **shows** that reason | **R** (OCR) |
| 211 | nothing — the model is never shown the file | image-only PDF is `needs_human`, its text is empty (`len 0`) | **D** (unread page, not a rejected value) |

SUB-217 (`2026-08-05` from a scan) is now a **hit**: P-067 keeps a cited, parseable scan date for review, card reason "read from a scan — check it against the page". The remaining two are the pipeline's own OCR quality, not the extraction prompt.

### conflict — 5 misses

| File | Cause | Class |
|---|---|---|
| 209 | the model **did** flag sales 1248000 vs 1600000; the email quote crosses a line break → citation rejected → D-086/P-038(c) folds it into the field reason, no conflict card | **D** (scorer reads cards only) |
| 211 | the model returned **no** conflict; gold expects the email's "new spot on Guadalupe" vs 1120 Commerce St | **R** |
| 219 | the model **did** flag the premises conflict; the schedule side is reformatted with commas → same D-086 fold | **D** |
| 214 | the conflict **is** in the report (0 vs 890000); scorer needle `0 tenant` vs blob `$0 (tenant)` | **M** |
| 216 | the conflict **is** in the report (24500 vs 18900); the needle `24500 vs` never appears in JSON | **M** |

### status — 5 misses · route — 2 · tiv — 1

| File | Cause | Class |
|---|---|---|
| 206, 213, 218 | all fields present, status `complete — review pending`, `report.complete` is False vs gold "complete" | **D** (B-325: review pending is safe, not automated) |
| 207, 215 | no "liquor" cue in a food-service text → `extra = ["liquor sales"]` → complete forced False | **D** (P-015 T2 ask) |
| 206 | route `senior_referral`, note "words not on the Carrier A allow-list: owns, leases, suites, tenants, common"; gold says carrier_a | **D** (carrier-match rules P-049) |
| 213 | `therapy` in the tenant list is on the R14 lab/medical list → senior_referral; gold says carrier_a with "verify: no lab or medical" | **D** |
| 214 | an open conflict nulls the field by design; gold still says `TIV: 0` | **D** |

**Totals: 3 real misses (loss_runs 209/225, conflict 211); the other 13 marks are an approved rule or a measurement artefact.**

## Defects found while checking P-066/P-067 (2026-10-20)

- **P-066** (committed 39b2a46): the dict `REFUSED_AS` was deleted while two uses stayed, so every refusal raised `NameError` and `workbench.py --self-check` crashed. Fixed and committed separately (`fix(P-066): restore REFUSED_AS …`); @model-risk APPROVE, no High.
- **P-067** (committed 1da0066): the "rejected value reason carried to the card" path was dead (`prepare.py:1057` skipped a rejected row). Fixed under P-067 (prepare.py) with a self-check; the same fix is in this re-score.
- **llm_extract.py self-check fails at HEAD** (pre-existing, not from this session): line 1532 asserts a text-field scan read with one low word (cited 0.29) is kept with `REASON_LOW_SCAN`, but `SCAN_FLOOR = 0.50` means 0.29 is dropped. The test and the constant disagree; recorded as a defect (see BACKLOG). Not fixed (a threshold/behaviour change needs an approved proposal).

## For the AI Engineer

- Pending proposals: **P-068** (scorer v10) — @model-risk must approve it before any hold-out use; **P-067** is approved and built, defect now closed.
- Scores on dev (v10 + P-067): route 18/20, 0 unsafe, 0 false completes, 0 leaks; operations 19/20, loss_runs 17/20 — both still below the 18/20 floor (loss_runs misses are OCR).
- Top failure to fix next: the pipeline's OCR on loss-run images (209/225), then the SUB-211 operations clause.
