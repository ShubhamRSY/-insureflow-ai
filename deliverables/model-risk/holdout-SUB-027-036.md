# Hold-out result — SUB-027 through SUB-036

- Author: @model-risk
- Date: 2026-10-10
- Model: openai/gpt-oss-120b through the environment host. The scorer was not edited.
- Decision: not a production approval. The calls succeeded. The extract is not good enough to sign.

A null that matches a missing gold line is not_credited. It is not a hit. The four not-credited loss-run rows are the files whose gold line says the runs are missing.

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

Clean calls: SUB-027, SUB-029, SUB-032, SUB-036.

Misses: SUB-028 (scanned page) missed operations, sales, construction, TIV, loss runs, and status. SUB-030 (email body) missed operations. SUB-031 and SUB-035 (Spanish) missed operations, construction, and loss runs, and status. SUB-033 (scanned page) missed TIV. SUB-034 missed the square-foot conflict.

Named insured, premises, and year built were right on all ten. The weak spots are the scan, the Spanish files, one operations line in an email, and one conflict.
