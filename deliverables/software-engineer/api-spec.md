# Intake API (step 1)

- Author: @software-engineer
- Date: 2026-10-09
- Status: In review (T-014)
- Code: `underwriting_pipeline/app/intake.py`. Run `python underwriting_pipeline/app/intake.py`.

## Now

`intake(files)` takes `(filename, bytes)` pairs. It returns `submission_id`, sha256 and size per file, and `synthetic: true`. An empty pack raises.

`python underwriting_pipeline/app/intake.py simulation/inbox` hashes each `SUB-*` folder. It does not write into the inbox. Ran on SUB-001, SUB-002, and SUB-003.

No database. No FastAPI process. Add a service when a second caller needs HTTP.

## Not in this module

Decline, bind, carrier submit. Step 6 will refuse a decision with no underwriter id. That code is T-019, not this sprint.
