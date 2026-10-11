# Hold-out extraction score — SUB-077 through SUB-086

- Author: @ai-engineer
- Scored by @model-risk with this file unchanged after the gold answers were written.
- A null that matches a missing gold line is not_credited. It is not a correct answer.
- Correctly flagged for human means the documents disagree and the AI stored both sides without picking one. It is not a hit and not a miss.
- Synthetic. Not a production approval.

## Per-field

| Field | Hit | Miss | Not credited | Correctly flagged for human |
|---|---|---|---|---|
| named_insured | 9 | 1 | 0 | 0 |
| premises | 5 | 4 | 0 | 1 |
| operations | 8 | 2 | 0 | 0 |
| sales | 8 | 1 | 0 | 1 |
| tiv | 8 | 2 | 0 | 0 |
| construction | 9 | 1 | 0 | 0 |
| year_built | 7 | 3 | 0 | 0 |
| loss_runs | 6 | 1 | 2 | 1 |
| conflict | 6 | 1 | 0 | 3 |
| status | 5 | 5 | 0 | 0 |

## Per submission

- SUB-077 (handwritten tilted scan): extracted name Rigsby Watch LLC. Misses: year_built, premises, status. Flagged: none. Call: ok.
- SUB-078 (rotated low-quality scan): extracted name Goliad Bookkeeping LLC. Misses: year_built, premises, status. Flagged: none. Call: ok.
- SUB-079 (multi-page loss run with claims): extracted name Blanco Clinic Office LLC. Misses: none. Flagged: none. Call: ok.
- SUB-080 (multiple locations): extracted name Fresno Wholesale LLC.. Misses: named_insured, operations, tiv, conflict. Flagged: none. Call: ok.
- SUB-081 (blank ACORD plus attachment): extracted name Hays Accounting LLC. Misses: operations, sales, construction, year_built, tiv, loss_runs, status. Flagged: none. Call: ok.
- SUB-082 (contradictory emails): extracted name Devine Retail LLC. Misses: none. Flagged: premises, conflict. Call: ok.
- SUB-083 (duplicate resubmission): extracted name Eads Gifts LLC. Misses: none. Flagged: sales, conflict. Call: ok.
- SUB-084 (handwritten Spanish scan): extracted name Taqueria Luna LLC. Misses: premises, status. Flagged: none. Call: ok.
- SUB-085 (upside-down low-quality scan): extracted name Woodlawn Painting LLC. Misses: premises, status. Flagged: none. Call: ok.
- SUB-086 (duplicate loss-run dates): extracted name Soledad Law Office LLC. Misses: none. Flagged: loss_runs, conflict. Call: ok.
