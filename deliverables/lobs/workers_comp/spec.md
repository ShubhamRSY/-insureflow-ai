# workers_comp — Wave 2 spec

- Authors: @senior-underwriter + @head-of-underwriting (written in OpenCode, not independently reviewed). Date: 2026-10-21.
- Wave 2. Synthetic data and placeholder carriers only. Not a production approval; the T-027 veto stands.
- **needs review** marks an open question, not a settled rule.

## 1. Identity

- LOB id: `workers_comp` (`InsuranceLine.WORKERS_COMP`). Family: small commercial P&C.
- Workers compensation: the exposure base is **payroll by class code**, with a state, employee count and experience modification.
- Texas only in the pilot. State rating manuals are the hard part, not the document reading.

## 2. Typical submission documents

| Document | Required | Notes |
|---|---|---|
| Application (`application.md`) | Yes | WC application; class codes and payroll by class |
| Payroll/class schedule (`schedule.csv`) | Yes | One row per class code: description, payroll, employee count |
| Experience mod worksheet | Optional | Where stated; never inferred |
| Carrier loss run (`loss-runs.md`) | Yes for a routable file | Published formats only; injury data may be sensitive |
| Email (`email.md`) | No | Producer notes |
| Scanned application | — | Out of scope (criterion 1) |

## 3. Required fields

| Field | Required | Notes |
|---|---|---|
| `named_insured` | Yes | Legal entity |
| `premises_address` | Yes | Operating address |
| `effective_date` | Yes | ISO |
| `operations` | Yes | Business description; class codes come from the schedule |
| `state` | Yes (new) | Rating state; always `TX` in the pilot; **needs review** name |
| `payroll_by_class` | Yes (new) | Rows: class code, description, payroll, employee count; **needs review** shape |
| `total_payroll` | Yes (new) | Sum of stated class payroll; **needs review** name |
| `experience_mod` | Optional | Only when a worksheet states it; never derived |
| `sales_or_payroll` | Replaced by `total_payroll` | Keep the existing field as the total until the pack lands |
| `loss_run_valued_through` | Yes for a routable file | No-known-loss letter is not a date |
| `tiv_building`, `construction`, `year_built` | No | `not in documents` unless property is quoted |

## 4. Out-of-scope criteria

Baseline criteria 1–4. WC readings:

- A payroll schedule is not a location schedule; multiple rows are not criterion 2.
- A non-Texas risk is **out of appetite** (not out of scope) until other states are approved; **needs review**.
- A file with no class-code/payroll rows is **incomplete**, not manual intake.

## 5. Operations slots

Same v11 closed list and slots. The class is the business; class codes are a new structured field, not a slot.

**needs review:** `class_code` as a scored item, and whether `experience_mod` affects route or only price. Recommendation: route (referral outside a band), pending @actuary.

## 6. Synthetic appetite and referral rules (placeholder carriers)

Fictional only; state-rating terms are not invented here.

| Carrier | Synthetic appetite | Route |
|---|---|---|
| Carrier A | Office/retail/wholesale; TX; experience mod 0.85–1.15; payroll ≤ $2,000,000 | `carrier_a` |
| Carrier B | Restaurant or contractor; TX; mod 0.80–1.25 | `senior_referral`, suggested `carrier_b` |
| Carrier C | Habitational or higher-hazard class; TX | `senior_referral`, suggested `carrier_c` |

Rules (all **needs review**): WC1 state missing or not TX → referral; WC2 class payroll rows missing → hold; WC3 mod outside the band → referral; WC4 prohibited class (R1) → `no_match`; WC5 roofing or height work → referral. No decline and no bind.

## 7. Gold-writing rules

Same format as BOP, plus:

- One `- Class:` line per row: `code | description | payroll | employees`.
- `- Total payroll:` and `- Experience mod:` from the stated rows/worksheet only.
- `- Sales:` is `not in documents` for a WC-only file.
- `- TIV:` is `not in documents`.
- A payroll total that does not equal the row sum is a conflict.
- All `operations-gold-rule.md` rules apply unchanged.

## 8. Needs review

- Exact field names for state, class rows, total payroll and mod.
- Whether non-TX is out of scope or out of appetite, and the state list.
- WC1–WC5 and all synthetic limits; @actuary to confirm rating bands before build.
- @compliance: injury/medical data in loss runs, state WC filing and privacy rules.
