# Hold-out extraction score — SUB-017 through SUB-026

- Author: @ai-engineer
- prepare.py was not edited for this run.
- Gold files were already in deliverables/senior-underwriter/gold-set/.
- Synthetic. Not a production approval.
- Command: `python underwriting_pipeline/ai/eval_holdout.py`

A hit means the unchanged extractor matched that gold line. PDF and Excel files are ignored by prepare.process_submission, which only reads .md and .csv.

## Per-field accuracy

| Field | Correct |
|---|---|
| named_insured | 0/10 |
| premises | 0/10 |
| operations | 0/10 |
| sales | 0/10 |
| tiv | 0/10 |
| construction | 0/10 |
| year_built | 0/10 |
| loss_runs | 4/10 |
| conflict | 8/10 |
| status | 5/10 |

## Per submission

- SUB-017 (text PDF): 1/10. Ignored: application.pdf. Misses: named_insured, premises, operations, sales, tiv, construction, year_built, loss_runs, status.
- SUB-018 (scanned-style PDF): 1/10. Ignored: scan.pdf. Misses: named_insured, premises, operations, sales, tiv, construction, year_built, loss_runs, status.
- SUB-019 (Excel schedule): 3/10. Ignored: schedule.xlsx. Misses: named_insured, premises, operations, sales, tiv, construction, year_built.
- SUB-020 (email body): 3/10. Ignored: none. Misses: named_insured, premises, operations, sales, tiv, construction, year_built.
- SUB-021 (Spanish): 1/10. Ignored: none. Misses: named_insured, premises, operations, sales, tiv, construction, year_built, loss_runs, status.
- SUB-022 (text PDF plus email): 1/10. Ignored: application.pdf. Misses: named_insured, premises, operations, sales, tiv, construction, year_built, loss_runs, conflict.
- SUB-023 (scanned-style PDF): 3/10. Ignored: scan.pdf. Misses: named_insured, premises, operations, sales, tiv, construction, year_built.
- SUB-024 (Excel schedule plus email): 2/10. Ignored: schedule.xlsx. Misses: named_insured, premises, operations, sales, tiv, construction, year_built, conflict.
- SUB-025 (Spanish): 1/10. Ignored: none. Misses: named_insured, premises, operations, sales, tiv, construction, year_built, loss_runs, status.
- SUB-026 (text PDF): 1/10. Ignored: application.pdf. Misses: named_insured, premises, operations, sales, tiv, construction, year_built, loss_runs, status.
