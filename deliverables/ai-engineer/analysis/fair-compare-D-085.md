# Fair comparison on the 9 files all three models completed (D-085 item 1)

Development data. Files: SUB-087, SUB-089, SUB-090, SUB-091, SUB-092, SUB-093, SUB-095, SUB-097, SUB-098

| Field | openai/gpt-oss-120b | openai/gpt-oss-20b | qwen/qwen3.8-27b |
|---|---|---|---|
| named_insured | 7 of 9 | 6 of 9 | 8 of 9 |
| premises | 5 of 9 | 4 of 9 | 6 of 9 |
| effective_date | 6 of 9 | 5 of 9 | 7 of 9 |
| operations | 7 of 9 | 7 of 9 | 8 of 9 |
| sales | 8 of 9 | 4 of 9 | 3 of 9 |
| tiv | 8 of 9 | 5 of 9 | 8 of 9 |
| construction | 7 of 9 | 7 of 9 | 8 of 9 |
| year_built | 6 of 9 | 5 of 9 | 7 of 9 |
| loss_runs | 5 of 9 | 4 of 9 | 5 of 9 |
| **silent error rate** | 2.5% (2 of 81) | 2.5% (2 of 81) | 2.5% (2 of 81) |
| **automation rate** | 69.1% (56 of 81) | 56.8% (46 of 81) | 71.6% (58 of 81) |
| **hits, all 9 fields** | 59 of 81 | 47 of 81 | 60 of 81 |
