# gold-set-commercial_package — layout

- Owner: @senior-underwriter. Created 2026-10-21 under D-120 item 9 (`gold-set-<lob>/`, frozen and hashed per LOB).
- `dev/` — the synthetic dev cards for `SUB-270–279` (6 in scope, 4 out of scope, one per P-055 criterion). Dev only: never hold-out evidence, never a published score, and not a freeze.
- `holdout/` — reserved for the future 20 in + 12 out hold-out, written gold-first and frozen once (D-020/D-022). It does not exist yet.
- `dev-manifest.sha256` — sha256 of every dev card, made after the lint passed. The hold-out will get its own manifest when it is frozen.
- Lint: `deliverables/senior-test-engineer/lint_holdout.py` with `deliverables/senior-test-engineer/commercial-package-dev-plan.json` and `HOLDOUT_INBOX=simulation/inbox-dev/commercial_package HOLDOUT_GOLD=deliverables/senior-underwriter/gold-set-commercial_package/dev`. Result: PASS (0 failures, 10 files), `deliverables/senior-test-engineer/commercial-package-dev-lint.txt`.
- No real applicant data. Every business, person and address is fictional.
