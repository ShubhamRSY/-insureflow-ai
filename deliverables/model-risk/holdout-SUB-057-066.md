# Hold-out result — SUB-057 through SUB-066

- Author: @model-risk
- Date: 2026-10-10
- Model: openai/gpt-oss-120b through the environment host.
- The scorer was written before these files existed and was not edited after the gold answers or after this score.
- Decision: not a production approval. This set was built to be harder than SUB-047 through SUB-056. The drop in score is the result.

A null that matches a missing gold line is not_credited. It is not a hit. A correct refusal to pick between two sales figures or two loss-run dates is still a miss on that field, because the scorer asks for one value.

## Compared with SUB-047 through SUB-056

| Field | SUB-047–056 hit / miss / not credited | This score |
|---|---|---|
| named_insured | 10 / 0 / 0 | 5 / 5 / 0 |
| premises | 10 / 0 / 0 | 5 / 5 / 0 |
| operations | 10 / 0 / 0 | 5 / 5 / 0 |
| sales | 10 / 0 / 0 | 5 / 5 / 0 |
| tiv | 10 / 0 / 0 | 6 / 4 / 0 |
| construction | 10 / 0 / 0 | 6 / 4 / 0 |
| year_built | 10 / 0 / 0 | 5 / 5 / 0 |
| loss_runs | 6 / 0 / 4 | 3 / 5 / 2 |
| conflict | 10 / 0 / 0 | 5 / 1 / 4 |
| status | 10 / 0 / 0 | 6 / 4 / 0 |

## What held up

SUB-059, the two-page loss run with paid claims at two carriers, was clean, including the valuation date 2026-10-01. SUB-061, the ACORD with blanks filled by an attachment, was clean. SUB-062, the contradictory street numbers 9 and 90, was clean.

## What failed

The four hard scans returned no name: handwritten and tilted (SUB-057), sideways and noisy (SUB-058), handwritten Spanish (SUB-064), and upside down (SUB-065). A person can read SUB-057. The OCR text was empty.

SUB-060 has two real locations. The extracted name carried a trailing period, the primary premises were not exact, and a conflict was opened where the gold says there is none.

SUB-063 did not pick between sales 400000 and 250000. That refusal is right, and the scorer still marks sales as a miss. SUB-066 did not pick between loss-run dates 2026-05-05 and 2026-08-08. That refusal is right, and loss runs is a miss.

No loss-run date was invented for the two files whose runs are missing.

This does not approve the extractor, the hazard points, or a bind.
