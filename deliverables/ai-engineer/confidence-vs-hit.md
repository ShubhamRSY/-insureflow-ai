# Confidence versus hit (B-222)

- Author: @ai-engineer-assistant. 2026-10-14. D-070 item 3. Synthetic. Not a production approval.
- A report, not a UI change. No model call (`_post` raised), no code, prompt, scorer, or score file changed. Cache read from a scratch copy.
- Files: 15 of 60 development files (SUB-017 to SUB-076) hit the cache: 027, 029, 038, 042, 044, 050, 051, 053, 056, 067, 070, 071, 073, 074, 076.
- Values judged: 115 (stored 112, dropped 3).
- Confidence: the gate's own number: the model's, or for a scan the lower of the model's and the OCR score of the cited words.
- Stored: the gate kept the value. Dropped: the gate removed it (low confidence, quote not found, or value not in the quote); the raw model value is judged anyway. Each side of a model-reported conflict counts as a value.
- Correct: the value passes the existing scorer comparison (`eval_holdout.hit_named / hit_ops / hit_number / hit_text / hit_loss`, used read-only) against the gold line. Premises where gold says both addresses conflict, and effective_date (no gold line), are not judged. Operations is a word-overlap test, so it is lenient.
- Cells are correct/incorrect counts. Small counts: read direction, not rates.

## Typed sources, stored

| Field | <0.50 | 0.50-0.74 | 0.75-0.89 | 0.90-1.00 |
|---|---|---|---|---|
| construction | - | - | - | 10/1 |
| loss_run_valued_through | - | - | - | 7/1 |
| named_insured | - | - | - | 10/1 |
| operations | - | - | - | 10/0 |
| premises_address | - | - | - | 10/1 |
| sales_or_payroll | - | - | - | 11/1 |
| tiv_building | - | - | - | 11/0 |
| year_built | - | - | - | 11/0 |
| ALL | - | - | - | 80/5 |

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
| construction | - | 1/0 | - | 2/0 |
| loss_run_valued_through | - | 1/0 | 1/0 | 1/0 |
| named_insured | - | 0/1 | 1/0 | 2/0 |
| operations | - | 1/0 | 0/1 | 2/0 |
| premises_address | - | - | 0/1 | 1/0 |
| sales_or_payroll | - | - | 1/0 | 2/0 |
| tiv_building | - | 0/1 | 1/0 | 2/0 |
| year_built | - | - | 1/0 | 3/0 |
| ALL | - | 3/2 | 5/2 | 15/0 |

## Scan sources, dropped

| Field | <0.50 | 0.50-0.74 | 0.75-0.89 | 0.90-1.00 |
|---|---|---|---|---|
| construction | - | - | - | - |
| loss_run_valued_through | - | - | - | - |
| named_insured | - | - | - | - |
| operations | - | - | - | - |
| premises_address | 0/2 | - | - | - |
| sales_or_payroll | 0/1 | - | - | - |
| tiv_building | - | - | - | - |
| year_built | - | - | - | - |
| ALL | 0/3 | - | - | - |

