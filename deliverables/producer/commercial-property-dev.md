# commercial_property synthetic dev set (SUB-280–289)

- Author: @producer (written in OpenCode, not independently reviewed). Date: 2026-10-21.
- Dev data only. Not a hold-out, not a published score, not a carrier decision. Every business, person, address and policy number is fictional.
- Output: `simulation/inbox-dev/commercial_property/SUB-280`–`SUB-289`; dev gold in `deliverables/senior-underwriter/gold-set-commercial_property/dev/`.
- 10 submissions: 6 in scope + 4 out of scope (one per P-055 criterion 1–4), per the commercial_property spec.
- `bpp_limit` and `sprinklered` appear in the application and schedule of every in-scope file, and in the gold as notes only (D-121 item 3). Scorer v11 does not score them.

## Mix

| File | Class | BPP / sprinklers | Route (gold) | Why |
|---|---|---|---|---|
| SUB-280 | Office | 60000 / yes, full | `carrier_a` (R14) | Office, TIV 1.3M |
| SUB-281 | Retail | 140000 / no | `carrier_a` (R14) | Dry retail, TIV 860K |
| SUB-282 | Office | 0 / yes, partial | `carrier_a` (R14) | Office, TIV 2.45M |
| SUB-283 | Wholesale | 95000 / no | `carrier_a` (R14) | Light wholesale, TIV 1.8M |
| SUB-284 | Restaurant | 120000 / yes, full | `senior_referral`, Carrier B (R10) | Cooking stated |
| SUB-285 | Contractor | 230000 / no | `senior_referral`, Carrier B (R11) | Contractor |
| SUB-286 | Dental office | not assessed | out of scope, criterion 1 | Application is a JPG scan |
| SUB-287 | Office | not assessed | out of scope, criterion 2 | `Location 2:` line + two-row schedule |
| SUB-288 | Retail | not assessed | out of scope, criterion 3 | Application typed in Spanish |
| SUB-289 | Office | not assessed | out of scope, criterion 4 | Email and loss run only, no application |

## Files per in-scope submission

`application.md` (ACORD 125/140-style property section with BPP and sprinklers), `email.md`, `schedule.csv` (one row, BPP column), `loss-runs.md` (Carrier A layout, valued 2026-08-15, no claims).

## Checks

- Dev gold: `deliverables/senior-underwriter/gold-set-commercial_property/dev/`, hash manifest `dev-manifest.sha256`.
- Lint: PASS (0 failures, 10 files); `deliverables/senior-test-engineer/commercial-property-dev-lint.txt`.
- No pipeline run, no model call, no write to `simulation/inbox/`, real logs or real outboxes.

## Limits

- Dev only. It does not test the property pack's required-field set, BPP/sprinkler scoring, or real carrier terms; those wait for the pack and a P-###.
