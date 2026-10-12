# Hold-out result — SUB-037 through SUB-046

- Author: @model-risk
- Date: 2026-10-10
- Model: openai/gpt-oss-120b through the environment host.
- The scorer `underwriting_pipeline/ai/eval_holdout_037.py` was written before these files existed and was not edited after the gold answers or after this score.
- Decision: not a production approval.

Gold answers were written before any extraction call on these folders. A null that matches a missing gold line is not_credited. It is not a hit.

## Compared with the first SUB-027–036 score

The baseline is `deliverables/model-risk/holdout-SUB-027-036.md`, not the later development rerun.

| Field | First score hit / miss / not credited | This score hit / miss / not credited |
|---|---|---|
| named_insured | 10 / 0 / 0 | 10 / 0 / 0 |
| premises | 10 / 0 / 0 | 10 / 0 / 0 |
| operations | 6 / 4 / 0 | 9 / 1 / 0 |
| sales | 9 / 1 / 0 | 10 / 0 / 0 |
| tiv | 8 / 2 / 0 | 10 / 0 / 0 |
| construction | 7 / 3 / 0 | 9 / 1 / 0 |
| year_built | 10 / 0 / 0 | 10 / 0 / 0 |
| loss_runs | 3 / 3 / 4 | 6 / 0 / 4 |
| conflict | 9 / 1 / 0 | 9 / 1 / 0 |
| status | 7 / 3 / 0 | 10 / 0 / 0 |

## Target before pilot

Every field that has a gold value scored 9 or 10 hits. Loss runs were not guessed: 6 dates matched, 0 dates were wrong, and 4 files whose gold line says the runs are missing stayed null. Those 4 nulls are not hits, so loss runs are not 9 hits out of 10 files.

Misses: SUB-040 (email body) missed operations and construction. SUB-044 missed the square-foot conflict. The scan, the Spanish forms, and the address conflict were clean.

This does not approve the extractor, the hazard points, or a bind.
