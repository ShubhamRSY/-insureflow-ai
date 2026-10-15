# Confidence versus hit (B-222)

- Author: @ai-engineer-assistant (rebuild: orchestrator, main session). 2026-10-14. D-070 item 3, D-077 item 3. Synthetic. Not a production approval.
- A report, not a UI change. No model call (`_post` raised), no code, prompt, scorer, or score file changed. Cache read from a scratch copy.
- Rebuilt 2026-10-14 under D-077 on every cached file up to SUB-076. The first version (15 files, 115 values) is in git at b77ffa9.
- Files judged: 62 (cached and with a gold file): 009, 010, 017, 018, 019, 020, 021, 022, 023, 024, 025, 026, 027, 028, 029, 030, 031, 032, 033, 034, 035, 036, 037, 038, 039, 040, 041, 042, 043, 044, 045, 046, 047, 048, 049, 050, 051, 052, 053, 054, 055, 056, 057, 058, 059, 060, 061, 062, 063, 064, 065, 066, 067, 068, 069, 070, 071, 072, 073, 074, 075, 076.
- Cached but not judged (no usable gold file): 1: SUB-002 (FileNotFoundError).
- Values not judged because the gold file has no line for that field: 10.
- Values judged: 464 (stored 446, dropped 18).
- Confidence: the gate's own number: the model's, or for a scan the lower of the model's and the OCR score of the cited words.
- Stored: the gate kept the value. Dropped: the gate removed it (low confidence, quote not found, or value not in the quote); the raw model value is judged anyway. Each side of a model-reported conflict counts as a value.
- Correct: the value passes the existing scorer comparison (`eval_holdout.hit_named / hit_ops / hit_number / hit_text / hit_loss`, used read-only) against the gold line. Premises where gold says both addresses conflict, and effective_date (no gold line), are not judged. Operations is a word-overlap test, so it is lenient.
- Cells are correct/incorrect counts. Small counts: read direction, not rates.

## Typed sources, stored

| Field | <0.50 | 0.50-0.74 | 0.75-0.89 | 0.90-1.00 |
|---|---|---|---|---|
| construction | - | - | - | 44/2 |
| loss_run_valued_through | - | - | - | 29/2 |
| named_insured | - | - | - | 46/2 |
| operations | - | - | 1/0 | 45/0 |
| premises_address | - | - | - | 42/2 |
| sales_or_payroll | - | - | - | 46/2 |
| tiv_building | - | - | - | 46/0 |
| year_built | - | - | - | 46/1 |
| ALL | - | - | 1/0 | 344/11 |

## Typed sources, dropped

| Field | <0.50 | 0.50-0.74 | 0.75-0.89 | 0.90-1.00 |
|---|---|---|---|---|
| construction | - | - | - | - |
| loss_run_valued_through | - | - | - | - |
| named_insured | - | - | - | - |
| operations | - | - | - | - |
| premises_address | - | - | - | - |
| sales_or_payroll | - | - | - | - |
| tiv_building | - | - | - | - |
| year_built | - | - | - | - |
| ALL | - | - | - | - |

## Scan sources, stored

| Field | <0.50 | 0.50-0.74 | 0.75-0.89 | 0.90-1.00 |
|---|---|---|---|---|
| construction | - | 3/0 | 2/0 | 7/0 |
| loss_run_valued_through | - | 2/0 | 2/0 | 5/0 |
| named_insured | - | 0/2 | 5/0 | 5/0 |
| operations | - | 1/0 | 0/2 | 10/0 |
| premises_address | - | 0/1 | 1/1 | 4/0 |
| sales_or_payroll | - | 1/0 | 1/0 | 9/0 |
| tiv_building | - | 0/1 | 2/0 | 9/0 |
| year_built | - | 1/0 | 4/0 | 9/0 |
| ALL | - | 8/4 | 17/3 | 58/0 |

## Scan sources, dropped

| Field | <0.50 | 0.50-0.74 | 0.75-0.89 | 0.90-1.00 |
|---|---|---|---|---|
| construction | 1/0 | - | - | - |
| loss_run_valued_through | 1/1 | - | - | - |
| named_insured | 1/1 | - | - | - |
| operations | 0/1 | - | - | - |
| premises_address | 0/7 | - | - | - |
| sales_or_payroll | 1/2 | - | - | - |
| tiv_building | 2/0 | - | - | - |
| year_built | - | - | - | - |
| ALL | 6/12 | - | - | - |

