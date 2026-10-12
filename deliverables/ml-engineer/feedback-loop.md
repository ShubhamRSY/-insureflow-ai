# Feedback loop — underwriter decisions

- Author: @ml-engineer
- Date: 2026-10-10
- FICTIONAL log. Not a trained model and not a production approval.

When an underwriter approves, edits, or declines on the workbench, the page posts to `/decision`. `record_decision` appends one JSON line to `deliverables/software-engineer/decisions.jsonl`.

Each line stores the submission, the action, the underwriter id, the reason, the date, and `ai_version`. Edit and decline require a reason. Approve stores the reason when one is typed. `bound` and `sent_to_carrier` stay false. This log does not bind and does not send a package.

`correction_counts` totals approve, edit, and decline. Edits and declines are the corrections in the "no corrections" metric. The workbench page shows those three counts.

The self-check in `underwriting_pipeline/app/workbench.py` writes to a temporary file, requires an underwriter id, requires a reason to decline, and counts one approve and one edit.
