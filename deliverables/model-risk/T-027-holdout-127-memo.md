# T-027 production veto — hold-out SUB-127–146 memo

- Author: @model-risk (independent). 2026-10-15.
- Inputs read: `deliverables/ai-engineer/evals/SUB-127-146-holdout.{md,json}`, `T-027/RUN-RECORD.md`, `T-027/route-lossrun-readout.json`, `T-027/reports/SUB-*.json`, gold `deliverables/senior-underwriter/gold-set/SUB-127..146.md`, frozen scorer `underwriting_pipeline/ai/eval_holdout_127.py`.
- Nothing rescored or edited. Counts below are recomputed from the per-submission `checks` and `metrics` in the score JSON and match the published table exactly.
- Synthetic data. Not a production approval.

## Verdict: KEEP (T-027 veto not lifted)

Resolution condition (NEXT-SESSION.md): one run on `3a77415`, smoke first, checked .venv, paced, **all 9 fields at 9/10 or better** and **0 false completes**.

| Condition | Result | Met |
|---|---|---|
| Code = `3a77415` | `git diff 3a77415 15265d4 -- underwriting_pipeline/` empty (re-checked); no uncommitted paths | Yes |
| Gold = `bd9168e` | only change since is SUB-153.md added (not in this set) | Yes |
| .venv, smoke_readers first, qwen paced, no cache | RUN-RECORD; 20 calls, 0 from cache, 0 failed, 1 retry after 429 (SUB-145) | Yes |
| 0 false completes | 0 | Yes |
| All 9 fields at 9/10 or better | **3 of 9** | **No** |

## Per-field vs the 9/10 floor

Rate = (hit + hit needing review) / (hit + miss); not-credited and flagged excluded (same convention as SUB-087–106 and SUB-107–126).

| Field | Hit | Hit (review) | Miss | Not credited | Rate | Floor |
|---|---|---|---|---|---|---|
| named_insured | 20 | 0 | 0 | 0 | 100% | met |
| premises | 17 | 0 | 3 | 0 | 85% | **no** |
| effective_date | 17 | 1 | 2 | 0 | 90% | met |
| operations | 12 | 0 | 8 | 0 | 60% | **no** |
| sales | 17 | 1 | 2 | 0 | 90% | met |
| tiv | 17 | 0 | 3 | 0 | 85% | **no** |
| construction | 17 | 0 | 3 | 0 | 85% | **no** |
| year_built | 16 | 0 | 4 | 0 | 80% | **no** |
| loss_runs | 5 | 0 | 3 | 12 | 62.5% (5/8) | **no** |

Previous hold-out SUB-107–126: 5 of 9 at floor. This one: 3 of 9.

## Status, automation, silent errors

- False completes: **0** (critical criterion met). Status: 17 hit + 1 hit (review), 2 misses (SUB-132, SUB-133: gold complete, pipeline incomplete — the safe direction).
- Status automation: 4 of 6 gold-complete files shown plain "complete".
- Silent error rate: 7 / 180 = **3.9%**; all 7 are `operations` (35% of that field). Every other field: 0 silent errors.
- Automation rate: 132 / 180 = **73.3%** (loss_runs 25%, operations 60%, others 75–100%).

## Route accuracy (readout, `workbench.match()` on each saved report)

**14 / 20.** No file routed to carrier_c (gold 2) or senior_referral (gold 2).

| File | Pipeline | Gold | Cause as seen |
|---|---|---|---|
| SUB-132 | hold | carrier_b | held "incomplete" on extra "liquor sales" (beer and wine); missing [] |
| SUB-133 | hold | carrier_c | scanned Carrier C run held for review (loss run missing) |
| SUB-134 | no_match | carrier_c | glass shop given the restaurant-evidence note (D-078): class-lookup defect, same shape as SUB-107-126 M2 |
| SUB-139 | hold | no_match | file incomplete, so match not reached |
| SUB-141, SUB-146 | hold | senior_referral | file incomplete (no loss run), so referral not reached |

All 6 misses are toward hold/no_match; none sends a file anywhere wrong. But routing to carrier_c and to senior_referral has **no positive evidence** on this hold-out.

## Loss run: accept vs review per document

| Outcome | Files | vs gold |
|---|---|---|
| Accepted (typed carrier run, dated) | 127, 128, 130, 132, 134 | 5/5 correct |
| Review: scan / image-only run | 129, 131, 133 | right outcome; field reason says "no valued-as-of date", gold expects "loss run from scan/spreadsheet" — scored miss ×3 |
| Review: not a recognised carrier run | 135, 136, 138 | correct (no-known-loss letters and agency summary not credited) |
| Review: no valued-as-of date | 137, 139, 140 | correct outcome; 139 gold says "not a recognised carrier run" (reason differs) |
| No loss run | 141–146 | correct |

**0 false accepts.** Re-applied per-document rule also flags `application.jpg` in SUB-129 and SUB-144 as "loss run from scan/spreadsheet" (readout only; did not change the field).

## Gold-vs-pipeline mismatches, as they are (not rescored)

- **operations ×8** — 7 silent: pipeline keeps the head phrase, gold has the qualifiers; scorer needs every gold word. 127 "Financial advisory and tax office" (gold + "2nd floor"); 132 "Southern breakfast and lunch restaurant" (+ 90 seats, beer and wine); 133 "Residential apartments" (+ 12 units, two-story, long-term leases); 135 "Used book and thrift shop" (+ donated goods sorted on site); 136 "Mexican restaurant" (+ 70 seats, beer and wine, no bar); 141 and 146 "Full-service restaurant and bar" (+ 180 seats, full liquor license, live music). 143 "clothing store" vs "Clothing boutique retail store", flagged (translated).
- **sales/tiv/construction/year_built on SUB-142, SUB-143 (8 misses)** — gold says "missing, not given"; pipeline null. The frozen scorer calls `judge(False, …)` for these four fields, so a correct null is a miss here, while effective_date and loss_runs use the gold "missing" line (not credited). Scorer convention, frozen; recorded, not changed.
- **premises**: 129 and 144 null from scanned JPG applications (flagged); 142 "2270 Fredericksburg Rd San Antonio 78201" lacks "TX" (flagged by address check).
- **year_built**: 140 (1987 / 1999) and 144 (2002 / 2015) — two-location buildings, pipeline null and flagged; 129 scan null.
- **tiv / construction**: 144 and 129 scan nulls (flagged).
- **effective_date**: 142, 143 null; gold has 2027-01-01 and 2027-02-01 from the email body (flagged).
- **conflict ×3**: 129 email-vs-app sales conflict (3,100,000 vs 2,600,000) not stored, sales kept 2,600,000 flagged needs-review; 140 construction "loc 1 / loc 2" and 144 premises two locations raised as conflicts where gold says none.
- **status ×2**: 132, 133 (above).

## Findings

### H1 — Score condition not met (owner: @ai-engineer-assistant; decision: @user)
6 of 9 fields are below 9/10 on the frozen scorer. Even reading the SUB-142/143 null-on-missing misses generously (informational only, not a score), operations (60%), loss_runs (62.5%) and year_built stay below floor; premises stays at 85%. This is a real shortfall, not a scorer artefact.
Resolve: approved P-### changes for H2 and the Mediums below, then a new 20-file hold-out under the same rules with all 9 fields ≥ 9/10 and 0 false completes. SUB-127–146 is now development data.

### H2 — Operations: silent, confident truncation of material facts (owner: @ai-engineer-assistant)
All 7 silent errors on the hold-out are `operations`, each at confidence 1.0, unflagged. The dropped words are underwriting-material: full liquor license and live music (141, 146), beer and wine (132, 136), seat and unit counts (132, 133, 136, 141). The full sentence is inside the stored citation quote, so the model shortened it. An underwriter reading the value alone sees a lower hazard than the documents state.
Resolve: an approved P-### so `operations` carries the full stated operations (or the citation quote) rather than a summary, with a test on these shapes; @senior-underwriter states in the gold convention before the next hold-out which qualifiers are required, so the scorer rule and the extraction target agree. No change to the frozen scorer or published scores.

### Medium / Low (backlog, one line each)
- M1 Routing: no carrier_c or senior_referral route demonstrated; SUB-134 glass shop gets the restaurant note (class lookup, repeat of SUB-107–126 M2) — @software-engineer, @head-of-underwriting.
- M2 Scanned applications (129, 144): premises/construction/tiv/year_built null — OCR/extraction on JPG apps — @ai-engineer-assistant.
- M3 Multi-location year built and construction/premises: null or false conflict (140, 144) — needs a stated multi-location convention — @senior-underwriter, @ai-engineer-assistant.
- M4 SUB-129 email-vs-application sales conflict not detected (value was flagged, so not silent) — @ai-engineer-assistant.
- M5 Scorer convention: sales/tiv/construction/year_built score null-on-gold-missing as miss, unlike effective_date/loss_runs; settle before the next gold, never retro-apply — @ai-engineer-assistant, @senior-underwriter.
- M6 Loss-run field reason for scanned runs says "no valued-as-of date" though the per-document rule says "from scan" (129, 131, 133); outcome right, reason shown to the user is wrong — @software-engineer.
- L1 SUB-132 held as incomplete on "liquor sales" extra for a beer-and-wine cafe gold calls complete — @senior-underwriter.
- L2 Per-document readout flags `application.jpg` as a loss run from scan (129, 144) — @software-engineer.
- L3 Frozen code retries more than the run rule; the driver capped it and documented it — keep the cap in the pipeline for the next hold-out — @ai-engineer-assistant.
- L4 Score header shows HEAD `15265d4`, not `3a77415`; verified no pipeline diff, record the frozen commit in the header next time — @ai-engineer-assistant.

## What went right
0 false completes, 0 false loss-run accepts, 0 failed calls, 0 cache use, no silent error outside operations, named insured 20/20, source, quote and confidence present on every non-null field in all 20 reports (checked). Process discipline was clean.

## Decision
**T-027: KEEP.** The production veto stands. Resolves when H1 and H2 are closed as above and a fresh 20-file hold-out (gold first, `smoke_readers.py` first, checked .venv, paced, run and scored once on a frozen commit) shows all 9 fields at 9/10 or better with 0 false completes. Any approved P-### that follows is not a production approval.
