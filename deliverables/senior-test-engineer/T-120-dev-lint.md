# T-120 dev lint — commercial_package (SUB-270–279)

- Author: @senior-test-engineer (written in OpenCode, not independently reviewed). Date: 2026-10-21.
- Command: `HOLDOUT_INBOX=simulation/inbox-dev/commercial_package HOLDOUT_GOLD=deliverables/senior-underwriter/gold-set-commercial_package/dev .venv/bin/python deliverables/senior-test-engineer/lint_holdout.py deliverables/senior-test-engineer/commercial-package-dev-plan.json --run-date 2026-10-21`
- Result: **PASS — 0 failures, 0 info, 10 files** (6 in scope, 4 out of scope, one per criterion 1–4). Output: `commercial-package-dev-lint.txt`.
- Plan: `commercial-package-dev-plan.json`, routes carrier_a 4 / senior_referral 2 / no_match 0.
- Frozen inputs checked before the run: lint sha256 `01147a75...ea653`; scorer v11 sha256 `7ddcfb50...fcbb`. Neither file was edited.
- Dev only: this is not a hold-out, no score is published, and the dev gold is not a freeze (D-020/D-022). It exists so the package pack can be developed against typed, lint-clean files.
- No pipeline run, no model call, no write to `simulation/inbox/`, real logs or real outboxes.
