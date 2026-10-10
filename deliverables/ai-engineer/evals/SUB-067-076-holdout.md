# Hold-out extraction score — SUB-067 through SUB-076

- Author: @ai-engineer
- Scored by @model-risk with this file unchanged after the gold answers were written.
- A null that matches a missing gold line is not_credited. It is not a correct answer.
- Correctly flagged for human means the documents disagree and the AI stored both sides without picking one. It is not a hit and not a miss.
- Synthetic. Not a production approval.

## Per-field

| Field | Hit | Miss | Not credited | Correctly flagged for human |
|---|---|---|---|---|
| named_insured | 9 | 1 | 0 | 0 |
| premises | 4 | 5 | 0 | 1 |
| operations | 8 | 2 | 0 | 0 |
| sales | 8 | 1 | 0 | 1 |
| tiv | 8 | 2 | 0 | 0 |
| construction | 9 | 1 | 0 | 0 |
| year_built | 10 | 0 | 0 | 0 |
| loss_runs | 7 | 0 | 2 | 1 |
| conflict | 6 | 1 | 0 | 3 |
| status | 8 | 2 | 0 | 0 |

## Per submission

- SUB-067 (handwritten tilted scan): extracted name Nogalitos watch LLC. Misses: named_insured, operations, sales, premises, status. Flagged: none. Call: ok.
- SUB-068 (rotated low-quality scan): extracted name Military Drive Office LLC. Misses: premises. Flagged: none. Call: ok.
- SUB-069 (multi-page loss run with claims): extracted name Huebner Clinic Office LLC. Misses: none. Flagged: none. Call: ok.
- SUB-070 (multiple locations): extracted name De Zavala Wholesale LLC. Misses: operations, premises, tiv, conflict. Flagged: none. Call: ok.
- SUB-071 (blank ACORD plus attachment): extracted name Eleanor Avenue Accounting LLC. Misses: none. Flagged: none. Call: ok.
- SUB-072 (contradictory emails): extracted name Mistletoe Retail LLC. Misses: none. Flagged: premises, conflict. Call: ok.
- SUB-073 (duplicate resubmission): extracted name St Cloud Gifts LLC. Misses: none. Flagged: sales, conflict. Call: ok.
- SUB-074 (handwritten Spanish scan): extracted name Tortilleria Sol LLC. Misses: construction, premises, tiv, status. Flagged: none. Call: ok.
- SUB-075 (upside-down low-quality scan): extracted name West Avenue Painting LLC. Misses: premises. Flagged: none. Call: ok.
- SUB-076 (duplicate loss-run dates): extracted name Main Avenue Law Office LLC. Misses: none. Flagged: loss_runs, conflict. Call: ok.
