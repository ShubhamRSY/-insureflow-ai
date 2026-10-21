# gold-set-commercial_property — layout

- Owner: @senior-underwriter. Created 2026-10-21 under D-120 item 9 (`gold-set-<lob>/`, frozen and hashed per LOB).
- `dev/` — synthetic dev cards for `SUB-280–289` (6 in scope, 4 out of scope, one per P-055 criterion). Dev only: never hold-out evidence, never a published score, and not a freeze.
- `holdout/` — reserved for the future 20 in + 12 out hold-out, written gold-first and frozen once (D-020/D-022). It does not exist yet.
- `dev-manifest.sha256` — sha256 of every dev card, made after the lint passed.
- `bpp_limit` and `sprinklered` are recorded in each in-scope card as notes only, per D-121 item 3. Scorer v11 does not score them; no scorer version is changed.
- Lint: `deliverables/senior-test-engineer/lint_holdout.py` with `deliverables/senior-test-engineer/commercial-property-dev-plan.json` and `HOLDOUT_INBOX=simulation/inbox-dev/commercial_property HOLDOUT_GOLD=deliverables/senior-underwriter/gold-set-commercial_property/dev`. Result: PASS (0 failures, 10 files), `deliverables/senior-test-engineer/commercial-property-dev-lint.txt`.
- No real applicant data. Every business, person and address is fictional.
