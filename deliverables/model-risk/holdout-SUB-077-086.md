# Hold-out result — SUB-077 through SUB-086

- Author: @model-risk
- Date: 2026-10-10
- Model: openai/gpt-oss-120b through the environment host.
- Gold was written before extraction. The scorer was copied before these files existed and was not edited after the gold answers or after this score.
- P-005 was already in the code. The EasyOCR test did not change the live reader.
- Decision: not a production approval.

## Compared with SUB-067 through SUB-076

| Field | SUB-067–076 hit / miss / not credited / flagged | This score |
|---|---|---|
| named_insured | 9 / 1 / 0 / 0 | 9 / 1 / 0 / 0 |
| premises | 4 / 5 / 0 / 1 | 5 / 4 / 0 / 1 |
| operations | 8 / 2 / 0 / 0 | 8 / 2 / 0 / 0 |
| sales | 8 / 1 / 0 / 1 | 8 / 1 / 0 / 1 |
| tiv | 8 / 2 / 0 / 0 | 8 / 2 / 0 / 0 |
| construction | 9 / 1 / 0 / 0 | 9 / 1 / 0 / 0 |
| year_built | 10 / 0 / 0 / 0 | 7 / 3 / 0 / 0 |
| loss_runs | 7 / 0 / 2 / 1 | 6 / 1 / 2 / 1 |
| conflict | 6 / 1 / 0 / 3 | 6 / 1 / 0 / 3 |
| status | 8 / 2 / 0 / 0 | 5 / 5 / 0 / 0 |

## What held up

SUB-079, the two-page loss run, was clean, including the valuation date 2026-11-20. SUB-082 stored both street numbers and did not pick one. SUB-083 stored both sales figures and did not pick one. SUB-086 stored both loss-run dates and did not pick one. Those three are flagged. The two files with no loss run were not credited.

SUB-080's premises line was not a miss. The primary address was kept. That is the P-005 case. The extracted name had a trailing period, and operations, TIV, and conflict were misses. The second location did not have to be chosen as the only premises.

## What failed

The four hard scans missed premises: SUB-077, SUB-078, SUB-084, and SUB-085. SUB-077 and SUB-078 also missed year built. SUB-081, the blank ACORD with an attachment, missed operations, sales, construction, year built, TIV, loss runs, and status. That is the new loss-run miss. No date was invented for the two files whose runs are missing.

This does not approve the extractor, the hazard points, or a bind.
