# Self-check record — C1–C6 and B-191 item 2

- Date: 2026-10-21. Branch: `pilot-conditions`. Written in OpenCode, not independently reviewed.
- No model calls. Every write in these tests went to a temp sandbox (D-069).

## Commands and results

```text
../insureflow-ai-team/.venv/bin/python -m pytest tests/pipeline -q
52 passed
```

```text
../insureflow-ai-team/.venv/bin/python underwriting_pipeline/app/workbench.py
workbench ok
```

```text
../insureflow-ai-team/.venv/bin/python -m ruff check underwriting_pipeline/app/pilot.py tests/pipeline/test_pilot.py
All checks passed
```

## What the tests prove

- C1: `send_to_carrier` refuses `user`, `account-manager` and an underwriter id with "assist-only pilot: send disabled"; `build_package` refuses; `/send` writes no package; `/decision approve` is refused; a confirmation requires every value; the decision log has no approve row and the row is `bound: false`.
- C2: `prepare.approve` refuses producer requests; `write_drafts` writes no `pending-approval/` draft and deletes a stale one.
- C3: the page shows the pilot banner and a scope verdict on every card; route text says "Suggestion only — not a decision".
- C5: an edit writes field, suggested value, final value, reason and run hash; the corrections panel is read-only; refusals are counted; a view row carries the run hash, prompt and model; a failed `fsync` returns a refusal naming the error (B-191 item 2).
- C6: every value row says "AI proposal — verify against the source"; the warning names operations 9/20, loss runs 5/20 (T-108) and the unapproved T-117 numbers 13/20, 16/20.
- Default mode is off; an unknown `PILOT_MODE` is refused.
- Screenshot: `deliverables/software-engineer/screenshots/PILOT-C3-C6-assist-only.png`, made from a temp sandbox with synthetic data.

## Not proven here

- The signed-in display log (needs B-190 merged).
- The C3/C6 @senior-underwriter UI check (High only).
- Independent @model-risk review of this code and of B-191 item 2.
- Any real-document data-handling clearance.
