# Extraction accuracy — SUB-007 through SUB-016

- Author: @ai-engineer
- Reviewed with: @senior-underwriter
- Date: 2026-10-09
- Synthetic gold set only. Not a production approval.
- Command: `python underwriting_pipeline/ai/eval_gold.py`
- Scored with `prepare.process_submission` on `simulation/inbox` before this round's producer replies.

## How a hit is counted

- named_insured and a single premises address must match the gold string.
- SUB-014 premises is a hit only when both addresses are stored with their sources.
- operations is a hit when every gold content word (length 4+, or a number) appears in the extracted operations text. Gold lines are class labels, not a second copy of the ACORD sentence.
- loss_run_valued_through is a hit when a gold 'no loss-runs' line stays null, and a gold 'missing: none' line has a value. A no-known-loss letter stays null.
- schedule_request is a hit when the draft asks for a location schedule only if the gold missing line says the schedule is absent.
- conflict_fields is the set of disagreeing fields. conflict_values checks the gold numbers and which file they came from.
- resolution is one row per open gold conflict (3 rows across SUB-014 and SUB-015). A hit means that row is unresolved and resolved_value is null. Both values stay.
- restaurant_questions is scored only where the gold says to ask the five industry items.
- citation is a hit when every extracted value that has a character span matches that span in the source file.
- carrier_route uses deliverables/head-of-underwriting/carrier-appetite.md: Carrier A office/dry retail/light wholesale at TIV <= $5M; Carrier B restaurants and light contractors with clean runs; bars, nightclubs, fireworks are no-match. An open conflict or a missing loss run is hold, not a decline.

## Per-field accuracy

| Field | Correct |
|---|---|
| named_insured | 10/10 (100%) |
| premises_address | 10/10 (100%) |
| operations | 10/10 (100%) |
| loss_run_valued_through | 10/10 (100%) |
| schedule_request | 10/10 (100%) |
| conflict_fields | 10/10 (100%) |
| conflict_values | 2/2 (100%) |
| resolution | 3/3 (100%) |
| status | 10/10 (100%) |
| restaurant_questions | 1/1 (100%) |
| citation | 10/10 (100%) |
| carrier_route | 10/10 (100%) |

## Per submission

- SUB-007: route carrier_a (gold carrier_a). No field misses.
- SUB-008: route carrier_a (gold carrier_a). No field misses.
- SUB-009: route carrier_a (gold carrier_a). No field misses.
- SUB-010: route carrier_b (gold carrier_b). No field misses.
- SUB-011: route hold (gold hold). No field misses.
- SUB-012: route hold (gold hold). No field misses.
- SUB-013: route hold (gold hold). No field misses.
- SUB-014: route hold (gold hold). No field misses.
- SUB-015: route hold (gold hold). No field misses.
- SUB-016: route no_match (gold no_match). No field misses.

## Not in this score

effective_date, sales, TIV, construction, and year built are extracted and cited, and the gold files do not state an expected value for them, so they are not in the accuracy denominator.
