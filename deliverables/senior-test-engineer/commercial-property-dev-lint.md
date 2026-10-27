# commercial_property dev lint — SUB-280–289

- Author: @senior-test-engineer (written in OpenCode, not independently reviewed). Date: 2026-10-21.
- Command: `HOLDOUT_INBOX=simulation/inbox-dev/commercial_property HOLDOUT_GOLD=deliverables/senior-underwriter/gold-set-commercial_property/dev .venv/bin/python deliverables/senior-test-engineer/lint_holdout.py deliverables/senior-test-engineer/commercial-property-dev-plan.json --run-date 2026-10-21`
- Result: **PASS — 0 failures, 0 info, 10 files** (6 in scope, 4 out of scope, one per criterion 1–4). Output: `commercial-property-dev-lint.txt`.
- Plan: `commercial-property-dev-plan.json`, routes carrier_a 4 / senior_referral 2 / no_match 0.
- Frozen inputs checked before the run: lint sha256 `01147a75…ea653`; scorer v11 sha256 `7ddcfb50…fcbb`. Neither file was edited.
- Dev only: this is not a hold-out, no score is published, and the dev gold is not a freeze (D-020/D-022).
- `bpp_limit` and `sprinklered` are notes in gold only (D-121 item 3); v11 ignores them.
- No pipeline run, no model call, no write to `simulation/inbox/`, real logs or real outboxes.
