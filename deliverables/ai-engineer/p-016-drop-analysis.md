# P-016 drop analysis (quick set of 15)

Author: @ai-engineer-assistant. 2026-10-14. D-066 block 1 item 2. No code change for this file. FICTIONAL submissions.

How: values recomputed from a copy of the cache, no model call (60 of 60 cache hits). "Before" = the P-022 code (git 485eed7, run from a scratch copy). "After" = current code. Host openai/gpt-oss-120b on the Groq URL, no real key (a placeholder string was needed to start; it was never sent). Reproduced the two score files for SUB-038 and SUB-067. No scorer main was run and no published score file was written.

## Checks that went from hit to something else

| Submission | Check | Gold | Value before P-016 | P-016 did | Reason, confidence | Dropped value correct? |
|---|---|---|---|---|---|---|
| SUB-038 | loss_runs | valued through 2026-08-01 | 2026-08-01 | dropped | cited words read 0.58, under 0.75 (model said 1.0) | Yes, correct |
| SUB-038 | status | complete | complete | follows loss_runs: file now incomplete | missing loss-run date | n/a (result of the drop) |
| SUB-067 | operations | dry retail | "ary retail watch repaty" | dropped | scan read 0.66 (model 0.7) | Partly. Misread text. The scorer gave a hit only because it ignores words under 4 letters ("dry") and matched "retail" |
| SUB-067 | construction | masonry | masonry | dropped | scan read 0.65 | Yes, correct |
| SUB-067 | conflict | none | no conflict | hit becomes not_credited | named insured and operations are both gone, so the scorer sees no identity | n/a (result of the drops) |

## Every other value P-016 dropped on the quick set (value existed before, none after)

| Submission | Field | Gold | Before | Reason, confidence | Dropped value correct? |
|---|---|---|---|---|---|
| SUB-038 | effective_date | no gold line (not scored) | 2027-01-01 | scan read 0.58 | Not checkable. Same date on SUB-053, likely right |
| SUB-067 | named_insured | Nogalitos Watch LLC | Nogalitos watch LLC | scan read 0.64 | Right except capital W. The scorer already counted it a miss |
| SUB-067 | effective_date | no gold line | 2RO2F-O1-O1 | scan read 0.00 | WRONG (not a date). Good drop |
| SUB-067 | sales_or_payroll | 175000 | #5000 | scan read 0.00 | WRONG. Good drop |
| SUB-074 | tiv_building | 280000 | 220000 | scan read 0.67 | WRONG. Good drop. The score did not move (miss before, miss after) |

premises_address was also dropped on SUB-067 (0.00) and SUB-074 (0.21), but no value was stored before, so nothing changed.

## Counts

- Values dropped that existed before: 9 (SUB-038: 2, SUB-067: 5, SUB-074: 1; none elsewhere). Rows lost as score hits: 5 (above).
- Correct: 2 clearly (SUB-038 loss run, SUB-067 construction). 1 right in substance but scored a miss anyway (named insured, capital letter). 1 garbled but scorer-hit (operations). 1 cannot be checked (effective date SUB-038).
- Wrong: 3 (SUB-067 effective_date, SUB-067 sales, SUB-074 tiv_building). These are gains even though no score moved: the old code stored them unflagged.

## Pattern

- Correct drops sit at 0.58 to 0.66. The wrong drops sit at 0.00, 0.00 and 0.67. Confidence alone does not separate right from wrong at 0.67 (the wrong TIV on SUB-074 is above two of the right ones).
- Values read at 0.00 are the model citing words the OCR never saw. Those are the ones to keep dropping under any option.

## Note on P-024 (same run)

With P-024 in, the recomputed run also shows more flagged values: scan numbers on SUB-038, SUB-053, SUB-067, SUB-074, and "translated or reworded" operations on SUB-050, SUB-051, SUB-074. No stored value changed from P-016 beyond the drops above. Conflict sides on SUB-042, SUB-073, SUB-076 now carry quote and flag.
