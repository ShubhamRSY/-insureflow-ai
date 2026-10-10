# Hold-out extraction score — SUB-027 through SUB-036

- Author: @model-risk
- Date: 2026-10-10
- Model: openai/gpt-oss-120b
- Restored from deliverables/model-risk/holdout-SUB-027-036.md after a later development rerun overwrote the scorer's output file.
- The development rerun is deliverables/ai-engineer/evals/SUB-017-036-dev-rerun.md. Do not use it as this baseline.
- A null that matches a missing gold line is not_credited. It is not a hit.
- Synthetic. Not a production approval.

## Per-field

| Field | Hit | Miss | Not credited |
|---|---|---|---|
| named_insured | 10 | 0 | 0 |
| premises | 10 | 0 | 0 |
| operations | 6 | 4 | 0 |
| sales | 9 | 1 | 0 |
| tiv | 8 | 2 | 0 |
| construction | 7 | 3 | 0 |
| year_built | 10 | 0 | 0 |
| loss_runs | 3 | 3 | 4 |
| conflict | 9 | 1 | 0 |
| status | 7 | 3 | 0 |

## Per submission

- SUB-027 (text PDF): Misses: none.
- SUB-028 (scanned page): Misses: operations, sales, construction, tiv, loss_runs, status.
- SUB-029 (Excel schedule): Misses: none.
- SUB-030 (email body): Misses: operations.
- SUB-031 (Spanish): Misses: operations, construction, loss_runs, status.
- SUB-032 (text PDF plus email): Misses: none.
- SUB-033 (scanned page): Misses: tiv.
- SUB-034 (Excel schedule plus email): Misses: conflict.
- SUB-035 (Spanish): Misses: operations, construction, loss_runs, status.
- SUB-036 (text PDF): Misses: none.

Clean calls: SUB-027, SUB-029, SUB-032, SUB-036.
