# Development rerun — SUB-027 through SUB-036

This file is the measurement after OCR and prompt changes. It is not the first hold-out score. Compare a new hold-out with deliverables/model-risk/holdout-SUB-027-036.md.

# Hold-out extraction score — SUB-027 through SUB-036

- Author: @ai-engineer
- Scored by @model-risk with this file unchanged after the gold answers were written.
- A null that matches a missing gold line is not_credited. It is not a correct answer.
- Synthetic. Not a production approval.

## Per-field

| Field | Hit | Miss | Not credited |
|---|---|---|---|
| named_insured | 10 | 0 | 0 |
| premises | 10 | 0 | 0 |
| operations | 10 | 0 | 0 |
| sales | 10 | 0 | 0 |
| tiv | 10 | 0 | 0 |
| construction | 9 | 1 | 0 |
| year_built | 10 | 0 | 0 |
| loss_runs | 6 | 0 | 4 |
| conflict | 9 | 1 | 0 |
| status | 10 | 0 | 0 |

## Per submission

- SUB-027 (text PDF): extracted name Alamo Ledger Office LLC. Misses: none. Call: ok.
- SUB-028 (scanned page): extracted name South Flores Stationery LLC. Misses: none. Call: ok.
- SUB-029 (Excel schedule): extracted name Fredericksburg Paper LLC. Misses: none. Call: ok.
- SUB-030 (email body): extracted name Blanco Street Kitchen LLC. Misses: construction. Call: ok.
- SUB-031 (Spanish): extracted name Bufete Robles LLC. Misses: none. Call: ok.
- SUB-032 (text PDF plus email): extracted name Commerce Tax Office LLC. Misses: none. Call: ok.
- SUB-033 (scanned page): extracted name Dolorosa Court LLC. Misses: none. Call: ok.
- SUB-034 (Excel schedule plus email): extracted name Houston Street Goods LLC. Misses: conflict. Call: ok.
- SUB-035 (Spanish): extracted name Bar La Villita LLC. Misses: none. Call: ok.
- SUB-036 (text PDF): extracted name Olmos Cabinets LLC. Misses: none. Call: ok.
