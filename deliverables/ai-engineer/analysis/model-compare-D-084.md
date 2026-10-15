# Model comparison on SUB-087–106 (D-084), development data, not a hold-out

Same code (P-035, P-036, P-037), one uncached run per model on Groq, frozen eval_holdout_087.py marks, D-084 rates.

| Field | openai/gpt-oss-120b | openai/gpt-oss-20b | qwen/qwen3.8-27b |
|---|---|---|---|
| named_insured hits | 10 of 12 | 12 of 16 | 19 of 20 |
| premises hits | 6 of 12 | 8 of 16 | 14 of 20 |
| effective_date hits | 7 of 12 | 9 of 16 | 17 of 20 |
| operations hits | 8 of 12 | 12 of 16 | 17 of 20 |
| sales hits | 10 of 12 | 7 of 16 | 6 of 20 |
| tiv hits | 8 of 12 | 10 of 16 | 17 of 20 |
| construction hits | 9 of 12 | 13 of 16 | 18 of 20 |
| year_built hits | 6 of 12 | 9 of 16 | 14 of 20 |
| loss_runs hits | 7 of 12 | 8 of 16 | 13 of 20 |
| **silent error rate (overall)** | 0.019 | 0.021 | 0.017 |
| **automation rate (overall)** | 0.602 | 0.59 | 0.717 |
| files run | 12 | 20 | 20 |
| failed calls (files) | 0 | 4 | 0 |
| failed attempts | {} | {"rate_limit_429": 6, "other": 19, "reply_not_usable": 14} | {"rate_limit_429": 35} |
| tokens per file | see note | 2788 | 1579 |
| seconds per file (incl. rate-limit waits) | see note | 58.6 | 35.4 |
| stopped (daily limit) | SUB-099 | no | no |

- openai/gpt-oss-120b: Stopped at SUB-099 (daily token limit hit; 12 of 20 files). Seconds per file before the limit: 12.7; the two files after it took 468 s and 555 s. Tokens: 33,145 for 12 calls (2,762 per file).
