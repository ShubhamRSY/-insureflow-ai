# T-120 — commercial_package synthetic dev set

- Author: @producer (written in OpenCode, not independently reviewed). Date: 2026-10-21.
- Dev data only. Not a hold-out, not a published score, not a carrier decision. Every business, person, address and policy number is fictional.
- Built by `deliverables/producer/build_commercial_package_dev.py`; output in `simulation/inbox-dev/commercial_package/SUB-270`–`SUB-279`.
- 10 files, 6 in scope + 4 out of scope (one per P-055 criterion 1–4), per D-120.

## Mix

| File | Class | Route (gold) | Why |
|---|---|---|---|
| SUB-270 | Office | `carrier_a` (R14) | Allow-list office, TIV 1.25M |
| SUB-271 | Retail | `carrier_a` (R14) | Dry retail, TIV 850K |
| SUB-272 | Office | `carrier_a` (R14) | Office, TIV 2.4M |
| SUB-273 | Retail | `carrier_a` (R14) | Clothing retail, TIV 975K |
| SUB-274 | Restaurant | `senior_referral`, Carrier B (R10) | Cooking stated |
| SUB-276 | Contractor | `senior_referral`, Carrier B (R11) | Contractor |
| SUB-275 | Dental office | out of scope, criterion 1 | Application is a JPG scan |
| SUB-277 | Office | out of scope, criterion 2 | `Location 2:` line + two-row schedule |
| SUB-278 | Retail | out of scope, criterion 3 | Application typed in Spanish |
| SUB-279 | Office | out of scope, criterion 4 | Email and loss run only, no application |

## Files per in-scope submission

`application.md` (ACORD 125/140/126-style, both property and GL sections), `email.md`, `schedule.csv` (one row), `loss-runs.md` (Carrier A layout, valued 2026-07-15, no claims).

## Checks

- Dev gold: `deliverables/senior-underwriter/gold-set-commercial_package/dev/`, hash manifest `dev-manifest.sha256`.
- Lint: PASS (0 failures, 10 files); `deliverables/senior-test-engineer/commercial-package-dev-lint.txt`.
- No pipeline run, no model call, no write to `simulation/inbox/`, `deliverables/**/gold-set/` or any real outbox.

## Limits

- This set does not test the package composition rule (property + GL), BPP/sprinkler scoring, or real carrier terms. Those wait for the pack and a P-###.
