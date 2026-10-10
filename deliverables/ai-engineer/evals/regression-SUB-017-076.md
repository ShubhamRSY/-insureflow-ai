# Regression — SUB-017 through SUB-076, before P-002 and P-003b

- Author: @ai-engineer-assistant
- Date: 2026-10-10
- Task: T-054. Decision: D-020.
- Model: openai/gpt-oss-120b through the environment host.
- Scores: `regression-SUB-017-076-before-P002-P003b.json`. The code had P-001 and P-005 and did not yet have P-002 or P-003b.
- Compared with the published hold-out score of each set. The published files were not rewritten.
- Command: `python underwriting_pipeline/ai/regression_compare.py deliverables/ai-engineer/evals/regression-SUB-017-076-before-P002-P003b.json`
- Synthetic. A development rerun. Not a production approval.

## Every field whose hit count changed

Only hits are counted. A field that is not listed did not change.

| Set | Field | Published hits | regression-SUB-017-076-before-P002-P003b.json hits | Change | Files that lost the hit |
|---|---|---|---|---|---|
| SUB-017-026 | named_insured | 0 | 10 | +10 | — |
| SUB-017-026 | premises | 0 | 10 | +10 | — |
| SUB-017-026 | operations | 0 | 9 | +9 | — |
| SUB-017-026 | sales | 0 | 10 | +10 | — |
| SUB-017-026 | tiv | 0 | 10 | +10 | — |
| SUB-017-026 | construction | 0 | 10 | +10 | — |
| SUB-017-026 | year_built | 0 | 10 | +10 | — |
| SUB-017-026 | loss_runs | 4 | 10 | +6 | — |
| SUB-017-026 | conflict | 8 | 10 | +2 | — |
| SUB-017-026 | status | 5 | 10 | +5 | — |
| SUB-027-036 | operations | 6 | 10 | +4 | — |
| SUB-027-036 | sales | 9 | 10 | +1 | — |
| SUB-027-036 | construction | 7 | 10 | +3 | — |
| SUB-027-036 | tiv | 8 | 10 | +2 | — |
| SUB-027-036 | loss_runs | 3 | 6 | +3 | — |
| SUB-027-036 | status | 7 | 10 | +3 | — |
| SUB-037-046 | named_insured | 10 | 9 | -1 | SUB-043 |
| SUB-037-046 | operations | 9 | 10 | +1 | — |
| SUB-037-046 | construction | 9 | 10 | +1 | — |
| SUB-037-046 | premises | 10 | 9 | -1 | SUB-038 |
| SUB-037-046 | conflict | 9 | 10 | +1 | — |
| SUB-047-056 | named_insured | 10 | 7 | -3 | SUB-051, SUB-053, SUB-055 |
| SUB-047-056 | operations | 10 | 7 | -3 | SUB-051, SUB-053, SUB-055 |
| SUB-047-056 | sales | 10 | 7 | -3 | SUB-051, SUB-053, SUB-055 |
| SUB-047-056 | construction | 10 | 7 | -3 | SUB-051, SUB-053, SUB-055 |
| SUB-047-056 | year_built | 10 | 7 | -3 | SUB-051, SUB-053, SUB-055 |
| SUB-047-056 | premises | 10 | 7 | -3 | SUB-051, SUB-053, SUB-055 |
| SUB-047-056 | tiv | 10 | 7 | -3 | SUB-051, SUB-053, SUB-055 |
| SUB-047-056 | loss_runs | 6 | 4 | -2 | SUB-051, SUB-055 |
| SUB-047-056 | conflict | 10 | 7 | -3 | SUB-051, SUB-053, SUB-055 |
| SUB-047-056 | status | 10 | 7 | -3 | SUB-051, SUB-053, SUB-055 |
| SUB-057-066 | named_insured | 5 | 6 | +1 | SUB-059, SUB-061 |
| SUB-057-066 | construction | 6 | 7 | +1 | SUB-061 |
| SUB-057-066 | year_built | 5 | 6 | +1 | SUB-059, SUB-061 |
| SUB-057-066 | premises | 5 | 4 | -1 | SUB-059, SUB-061 |
| SUB-057-066 | tiv | 6 | 7 | +1 | SUB-059, SUB-061 |
| SUB-057-066 | conflict | 5 | 6 | +1 | SUB-059, SUB-061 |
| SUB-057-066 | status | 6 | 4 | -2 | SUB-059, SUB-061 |
| SUB-067-076 | named_insured | 9 | 6 | -3 | SUB-070, SUB-073, SUB-075 |
| SUB-067-076 | operations | 8 | 5 | -3 | SUB-073, SUB-074, SUB-075 |
| SUB-067-076 | sales | 8 | 7 | -1 | SUB-075 |
| SUB-067-076 | construction | 9 | 8 | -1 | SUB-073, SUB-075 |
| SUB-067-076 | year_built | 10 | 8 | -2 | SUB-073, SUB-075 |
| SUB-067-076 | tiv | 8 | 7 | -1 | SUB-073, SUB-075 |
| SUB-067-076 | loss_runs | 7 | 5 | -2 | SUB-073, SUB-075 |
| SUB-067-076 | status | 8 | 5 | -3 | SUB-068, SUB-073, SUB-075 |

Fields with a lower hit count: 22.

## What the drops are

Eight files came back with no fields at all: SUB-051, SUB-053, SUB-055, SUB-057, SUB-059, SUB-061, SUB-073, and SUB-075. Seven of them had hits on their published score. SUB-057 was already empty on its published score, so it is not a drop. Those seven are the whole cause of 17 of the 22 lower counts, including all of SUB-047–056, and part of 3 more.

This run did not save the model-call error, so the file cannot show whether those eight calls failed or the model returned nothing. P-001 and P-005 do not blank a whole file. From T-058 on, the regression saves the error and repeats a failed call.

The drops that are not an empty file:

- SUB-043 named insured. The read was "LLc" against gold "LLC".
- SUB-038 premises. The read was "san Antonio" against gold "San Antonio".
- SUB-070 named insured, SUB-074 operations, and SUB-068 status. The file was read and that field missed.

SUB-017–026 and SUB-027–036 have no drop. The SUB-017–026 published score is from the reader that ignored PDF and Excel files, so its rise is not a fair gain.
