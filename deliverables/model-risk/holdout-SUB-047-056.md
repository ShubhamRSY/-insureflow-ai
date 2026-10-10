# Hold-out result — SUB-047 through SUB-056

- Author: @model-risk
- Date: 2026-10-10
- Model: openai/gpt-oss-120b through the environment host.
- The scorer was written before these files existed and was not edited after the gold answers or after this score.
- The model prompt and the OCR step were not changed. Cited document rules in prepare.py were added before this gold set, then frozen.
- Decision: not a production approval.

A null that matches a missing gold line is not_credited. It is not a hit.

## Compared with SUB-037 through SUB-046

| Field | SUB-037–046 hit / miss / not credited | This score |
|---|---|---|
| named_insured | 10 / 0 / 0 | 10 / 0 / 0 |
| premises | 10 / 0 / 0 | 10 / 0 / 0 |
| operations | 9 / 1 / 0 | 10 / 0 / 0 |
| sales | 10 / 0 / 0 | 10 / 0 / 0 |
| tiv | 10 / 0 / 0 | 10 / 0 / 0 |
| construction | 9 / 1 / 0 | 10 / 0 / 0 |
| year_built | 10 / 0 / 0 | 10 / 0 / 0 |
| loss_runs | 6 / 0 / 4 | 6 / 0 / 4 |
| conflict | 9 / 1 / 0 | 10 / 0 / 0 |
| status | 10 / 0 / 0 | 10 / 0 / 0 |

Every field that has a gold value is 10/10. That clears the 9/10 target on those fields. Loss runs were not guessed: 6 dates matched, 0 were wrong, and 4 files with no run stayed null. Those nulls are not hits.

The email case (SUB-050) and the square-foot conflict (SUB-054) were hits. SUB-056 used the carrier loss-run date and not the no-known-loss letter.

This does not approve the extractor, the hazard points, or a bind.
