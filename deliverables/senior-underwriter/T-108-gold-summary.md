# T-108 gold summary (batch 1: SUB-206 to SUB-215)

- Gold written by hand from documents and written rules only (P-055, carrier-match, operations-gold-rule, carrier-loss-run-formats, required-fields). Nothing was run.
- Scanned documents transcribed with tesseract/pdftoppm as a document reader only (orchestrator-granted deviation). No pipeline, extraction, scope detector, scorer, or ai-engineer artifact was read.

| Submission | Status | Expected carrier route |
|------------|--------|-----------------------|
| SUB-206 | complete | carrier_a (R14; AG:29) |
| SUB-207 | complete | senior_referral, suggested market carrier_a — words not on Carrier A allow-list |
| SUB-208 | incomplete — hold: loss run missing | senior_referral, suggested market carrier_a — words not on Carrier A allow-list; hold: loss run missing |
| SUB-209 | incomplete — hold: open conflict (sales) | senior_referral, suggested market carrier_b |
| SUB-210 | complete | senior_referral, suggested market carrier_c |
| SUB-211 | complete | senior_referral, suggested market carrier_b |
| SUB-212 | incomplete — hold: loss run not a recognised carrier format | senior_referral, suggested market carrier_b — hold: loss run not a recognised carrier format |
| SUB-213 | complete | carrier_a (R14; AG:29) |
| SUB-214 | incomplete — hold: loss run missing; open conflict | senior_referral, suggested market carrier_a — words not on Carrier A allow-list; hold: loss run missing, open conflict |
| SUB-215 | complete | senior_referral, suggested market carrier_a — words not on Carrier A allow-list |

Status counts (batch 1, after the SUB-209 correction):
- complete: 6 (SUB-206, 207, 210, 211, 213, 215)
- incomplete: 4 (SUB-208, 209, 212, 214) — 209 for the sales conflict, 208 and 214 for the missing loss run, 212 for the loss run format

# T-108 gold summary (batch 2: SUB-216 to SUB-225)

- Gold written by hand from documents and written rules only (P-055, carrier-match, operations-gold-rule, carrier-loss-run-formats, required-fields). Nothing was run.
- Scanned documents transcribed with tesseract and pdftoppm as document readers only (orchestrator-granted deviation). No pipeline, extraction, scope detector, scorer, plan, mix or ai-engineer artifact was read.

| Submission | Status | Expected carrier route |
|------------|--------|-----------------------|
| SUB-216 | incomplete — hold: loss run has no valued-as-of date | senior_referral, suggested market carrier_a (R17/P-053; wholesale) |
| SUB-217 | incomplete — hold: schedule missing (partial package) | senior_referral, suggested market carrier_c (R12) |
| SUB-218 | complete | senior_referral (W2c; R14; AG:31) |
| SUB-219 | incomplete — hold: loss run has no valued-as-of date; open conflict | senior_referral (W2a; R14; AG:31) |
| SUB-220 | incomplete — hold: loss run not a recognised carrier format (no-known-loss letter) | senior_referral, suggested market carrier_b (R10) |
| SUB-221 | complete | senior_referral (W2e; R14; AG:40, AG:51) |
| SUB-222 | incomplete — hold: year built not in documents | no_match (R1; AG:45-50) |
| SUB-223 | incomplete — hold: loss run not a recognised carrier format | senior_referral, suggested market carrier_c (R12) |
| SUB-224 | complete | senior_referral, suggested market carrier_c (R12) |
| SUB-225 | incomplete — hold: year built not in documents | no_match (R1; AG:45-50) |

Status counts (batch 2):
- complete: 3 (SUB-218, SUB-221, SUB-224)
- incomplete: 7 (SUB-216, SUB-217, SUB-219, SUB-220, SUB-222, SUB-223, SUB-225)
- manual intake: 0

Note: Scanned documents were transcribed with `tesseract` and `pdftoppm` as document readers only (SUB-217 loss run JPG; SUB-218 and SUB-225 image-only loss run PDFs), the orchestrator-granted deviation. No pipeline, scope detector, extraction, OCR script, scorer, plan, mix or ai-engineer artifact was opened, run or read, so every card is hand-written gold-first. Two ids record a conflict between two documents: SUB-216 (square footage, application 24500 vs schedule.csv 18900, email explains the schedule is the old smaller space) and SUB-219 (premises address, application 2701 Memorial Blvd, Port Arthur vs schedule.csv 4810 Twin City Hwy, Groves).

# T-108 gold summary (batch 3: SUB-226 to SUB-237, the 12 out-of-scope files)

- Gold written by hand from documents and written rules only (P-055 scope criteria 1-4, carrier-match, operations-gold-rule, carrier-loss-run-formats, required-fields). Nothing was run.
- Scanned documents transcribed with `tesseract` and image-only PDFs with `pdftoppm`+`tesseract` as document readers only (orchestrator-granted deviation). No pipeline, scope detector, extraction, OCR script, scorer, plan, mix or ai-engineer artifact was opened, run or read.
- Every card carries `- Scope:`, the criteria codes, and the manual-intake route/recommendation/loss-run/status lines the T-108 criterion asks for.

| Submission | Criteria |
|------------|----------|
| SUB-226 | 4 |
| SUB-227 | 4 |
| SUB-228 | 1 |
| SUB-229 | 1 |
| SUB-230 | 1 |
| SUB-231 | 1, 2 |
| SUB-232 | 2 |
| SUB-233 | 2 |
| SUB-234 | 3 |
| SUB-235 | 3 |
| SUB-236 | 2, 3 |
| SUB-237 | 2, 3 |

Count by criterion (a two-criteria file counts under each). Corrected after SUB-236's application was retyped as a typed Spanish PDF with both branches on the form, so criterion 1 no longer applies to it:
- criterion 1 (scanned application): 4 (SUB-228, SUB-229, SUB-230, SUB-231)
- criterion 2 (more than one location): 5 (SUB-231, SUB-232, SUB-233, SUB-236, SUB-237)
- criterion 3 (non-English content): 4 (SUB-234, SUB-235, SUB-236, SUB-237)
- criterion 4 (application not identifiable): 2 (SUB-226, SUB-227)
- files matching two criteria: 3 (SUB-231, SUB-236, SUB-237); files with criterion 4 alone: 2 (SUB-226, SUB-227)

Corrections in this batch:
- SUB-209 corrected: the card did not record the material revenue conflict. The application states annual sales $1,248,000; the email says the business is "Doing around 1.6 mil the last couple yrs". Status changed from `complete` to `incomplete — hold: open conflict (sales)`; Missing now names the unreconciled GL sales base; Conflict now records the application-vs-email revenue disagreement; recommendation adds the hold. Loss-run facts unchanged.
- Route normalisation: every in-scope card's `- Expected carrier route:` line now begins with a plain rule name from carrier-match.md, with no `?`, no hesitation and no "hold" as the route (holds sit on the Status and recommendation lines). Cards fixed: SUB-206, SUB-207, SUB-208, SUB-214, SUB-215.
