# Hold-out extraction score — SUB-077 through SUB-086 — rerun, with P-002 and P-003b, not a same-code comparison

- Author: @ai-engineer-assistant
- Rerun by @ai-engineer-assistant on 2026-10-10 for T-060. Not scored by @model-risk. The extraction code changed after the gold answers were written: P-002 and P-003b.
- Not the official score and not an improvement on it. The official baseline is `SUB-077-086-holdout.md` (D-026).
- A null that matches a missing gold line is not_credited. It is not a correct answer.
- Correctly flagged for human means the documents disagree and the AI stored both sides without picking one. It is not a hit and not a miss.
- Synthetic. Not a production approval.

## Per-field

| Field | Hit | Miss | Not credited | Correctly flagged for human | Call failed |
|---|---|---|---|---|---|
| named_insured | 9 | 1 | 0 | 0 | 0 |
| premises | 5 | 4 | 0 | 1 | 0 |
| operations | 8 | 2 | 0 | 0 | 0 |
| sales | 9 | 0 | 0 | 1 | 0 |
| tiv | 10 | 0 | 0 | 0 | 0 |
| construction | 10 | 0 | 0 | 0 | 0 |
| year_built | 8 | 2 | 0 | 0 | 0 |
| loss_runs | 7 | 0 | 2 | 1 | 0 |
| conflict | 7 | 0 | 0 | 3 | 0 |
| status | 6 | 4 | 0 | 0 | 0 |

## Per submission

- SUB-077 (handwritten tilted scan): extracted name Rigsby Watch LLC. Misses: year_built, premises, status. Flagged: none. Call: ok.
- SUB-078 (rotated low-quality scan): extracted name Goliad Bookkeeping LLC. Misses: year_built, premises, status. Flagged: none. Call: ok.
- SUB-079 (multi-page loss run with claims): extracted name Blanco Clinic Office LLC. Misses: none. Flagged: none. Call: ok.
- SUB-080 (multiple locations): extracted name Fresno Wholesale LLC.. Misses: named_insured, operations. Flagged: none. Call: ok.
- SUB-081 (blank ACORD plus attachment): extracted name Hays Accounting LLC. Misses: none. Flagged: none. Call: ok.
- SUB-082 (contradictory emails): extracted name Devine Retail LLC. Misses: none. Flagged: premises, conflict. Call: ok.
- SUB-083 (duplicate resubmission): extracted name Eads Gifts LLC. Misses: none. Flagged: sales, conflict. Call: ok.
- SUB-084 (handwritten Spanish scan): extracted name Taqueria Luna LLC. Misses: operations, premises, status. Flagged: none. Call: ok.
- SUB-085 (upside-down low-quality scan): extracted name Woodlawn Painting LLC. Misses: premises, status. Flagged: none. Call: ok.
- SUB-086 (duplicate loss-run dates): extracted name Soledad Law Office LLC. Misses: none. Flagged: loss_runs, conflict. Call: ok.
