# Hold-out result — SUB-067 through SUB-076

- Author: @model-risk
- Date: 2026-10-10
- Model: openai/gpt-oss-120b through the environment host.
- Gold was written before extraction. Extraction code was not changed after these files existed.
- The scorer's first run crashed before it wrote a score file. A loop variable had the same name as the word helper. That name was changed. No hit, miss, or flagged rule was changed. The counts below are the only completed run.
- Decision: not a production approval.

A null that matches a missing gold line is not_credited. A field where the documents disagree, and the AI stored both sides without picking one, is correctly flagged for human. That column is not a hit and not a miss.

## Compared with SUB-057 through SUB-066

The earlier score had no flagged column. A correct refusal there was a miss.

| Field | SUB-057–066 hit / miss / not credited | This score hit / miss / not credited / flagged |
|---|---|---|
| named_insured | 5 / 5 / 0 | 9 / 1 / 0 / 0 |
| premises | 5 / 5 / 0 | 4 / 5 / 0 / 1 |
| operations | 5 / 5 / 0 | 8 / 2 / 0 / 0 |
| sales | 5 / 5 / 0 | 8 / 1 / 0 / 1 |
| tiv | 6 / 4 / 0 | 8 / 2 / 0 / 0 |
| construction | 6 / 4 / 0 | 9 / 1 / 0 / 0 |
| year_built | 5 / 5 / 0 | 10 / 0 / 0 / 0 |
| loss_runs | 3 / 5 / 2 | 7 / 0 / 2 / 1 |
| conflict | 5 / 1 / 4 | 6 / 1 / 0 / 3 |
| status | 6 / 4 / 0 | 8 / 2 / 0 / 0 |

## What held up

SUB-069, the two-page loss run with paid claims, was clean, including the valuation date 2026-12-01. SUB-071, the blank ACORD filled by an attachment, was clean.

SUB-072 stored both street numbers and did not pick one. SUB-073 stored both sales figures and did not pick one. SUB-076 stored both loss-run dates and did not pick one. Those fields are flagged, not hits and not misses. Loss runs has zero misses. The two files with no loss run were not credited, and no date was invented.

The Groq account has no vision model. After rotation repair and deskew, the four hard scans were readable enough to return a name. They were not marked needs human read, and nothing was guessed from an empty page.

## What failed

SUB-067 returned "Nogalitos watch LLC" against the gold "Nogalitos Watch LLC", and also missed operations, sales, premises, and status.

SUB-068, SUB-074, and SUB-075 read the name and missed the premises line. SUB-074 also missed construction, TIV, and status.

SUB-070 has two real locations. It missed operations, premises, and TIV, and it opened a conflict where the gold says there is none.

This does not approve the extractor, the hazard points, or a bind.
