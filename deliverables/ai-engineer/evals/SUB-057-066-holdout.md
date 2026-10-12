# Hold-out extraction score — SUB-057 through SUB-066

- Author: @ai-engineer
- Scored by @model-risk with this file unchanged after the gold answers were written.
- A null that matches a missing gold line is not_credited. It is not a correct answer.
- Synthetic. Not a production approval.

## Per-field

| Field | Hit | Miss | Not credited |
|---|---|---|---|
| named_insured | 5 | 5 | 0 |
| premises | 5 | 5 | 0 |
| operations | 5 | 5 | 0 |
| sales | 5 | 5 | 0 |
| tiv | 6 | 4 | 0 |
| construction | 6 | 4 | 0 |
| year_built | 5 | 5 | 0 |
| loss_runs | 3 | 5 | 2 |
| conflict | 5 | 1 | 4 |
| status | 6 | 4 | 0 |

## Per submission

- SUB-057 (handwritten tilted scan): extracted name null. Misses: named_insured, operations, sales, construction, year_built, premises, tiv, loss_runs, status. Call: ok.
- SUB-058 (rotated low-quality scan): extracted name null. Misses: named_insured, operations, sales, construction, year_built, premises, tiv, loss_runs, status. Call: ok.
- SUB-059 (multi-page loss run with claims): extracted name Vance Jackson Clinic Office LLC. Misses: none. Call: ok.
- SUB-060 (multiple locations): extracted name Babcock Wholesale LLC.. Misses: named_insured, operations, year_built, premises, conflict. Call: ok.
- SUB-061 (blank ACORD plus attachment): extracted name Hackberry Accounting LLC. Misses: none. Call: ok.
- SUB-062 (contradictory emails): extracted name Poplar Retail LLC. Misses: none. Call: ok.
- SUB-063 (duplicate resubmission): extracted name Duval Gifts LLC. Misses: sales. Call: ok.
- SUB-064 (handwritten Spanish scan): extracted name null. Misses: named_insured, operations, sales, construction, year_built, premises, tiv, loss_runs, status. Call: ok.
- SUB-065 (upside-down low-quality scan): extracted name null. Misses: named_insured, operations, sales, construction, year_built, premises, tiv, loss_runs, status. Call: ok.
- SUB-066 (duplicate loss-run resubmission): extracted name Bandera Law Office LLC. Misses: loss_runs. Call: ok.
