# builders_risk — Wave 2 spec

- Authors: @senior-underwriter + @head-of-underwriting (written in OpenCode, not independently reviewed). Date: 2026-10-21.
- Wave 2. Synthetic data and placeholder carriers only. Not a production approval; the T-027 veto stands.
- **needs review** marks an open question, not a settled rule.

## 1. Identity

- LOB id: `builders_risk` (`InsuranceLine.BUILDERS_RISK`). Family: small commercial P&C.
- Property under construction or renovation. The exposure base is the **completed project value**, with a construction period and a site address.
- One project site per submission in Wave 2; Texas only in the pilot.

## 2. Typical submission documents

| Document | Required | Notes |
|---|---|---|
| Application (`application.md`) | Yes | ACORD 125-shaped; builders risk section present |
| Project schedule (`schedule.csv`) | Yes | Project value, start/end dates, construction type, site |
| Email (`email.md`) | No | Producer notes |
| Carrier loss run (`loss-runs.md`) | Optional | New projects often have none; a no-known-loss letter is not a date |
| Scanned application | — | Out of scope (criterion 1) |

## 3. Required fields

| Field | Required | Notes |
|---|---|---|
| `named_insured` | Yes | Owner or general contractor, as stated |
| `premises_address` | Yes | The project site |
| `effective_date` | Yes | ISO |
| `operations` | Yes | Project type (e.g., ground-up office, renovation) |
| `sales_or_payroll` | Optional | Not the exposure |
| `project_value` | Yes (new) | Completed value; **needs review** name |
| `project_start_date` | Yes (new) | ISO; **needs review** name |
| `project_end_date` | Yes (new) | ISO; **needs review** name |
| `construction` | Yes | Construction type of the project |
| `tiv_building` | No | Do not reuse building TIV as project value |
| `year_built` | No | Not applicable to a new project; `not in documents` |
| `loss_run_valued_through` | Only if a loss run exists | No-known-loss letter is not a date |

## 4. Out-of-scope criteria

Baseline criteria 1–4. Builders risk readings:

- Two project sites → criterion 2 in Wave 2.
- A project with no stated value or no stated construction period is **incomplete**, not manual intake.
- A renovation of an occupied building is **not** out of scope: D-121 item 8 says `senior_referral` with **both** carriers suggested until a written rule exists. A person decides the line.

## 5. Operations slots

Same v11 closed list and slots. The class is the project/contractor class; `contractor` is common. No builders-risk-specific slot in v11.

**needs review:** `ground_up` vs `renovation` and `occupied_during_work` are proposed items for a later scorer version, not Wave 2.

## 6. Synthetic appetite and referral rules (placeholder carriers)

Fictional only.

| Carrier | Synthetic appetite | Route |
|---|---|---|
| Carrier A | Ground-up office/retail; project value ≤ $10,000,000; frame/masonry; period ≤ 18 months | `carrier_a` |
| Carrier B | Renovation of a contractor/retail project; value ≤ $5,000,000 | `senior_referral`, suggested `carrier_b` |
| Carrier C | Habitational or mixed-use project; value ≤ $7,500,000 | `senior_referral`, suggested `carrier_c` |

Rules (all **needs review**): BR1 project value or end date missing → hold; BR2 project period over 18 months → referral; BR3 occupied renovation → `senior_referral` with both Carrier B and Carrier C suggested (D-121 item 8); BR4 prohibited class (R1) → `no_match`; else class rules. No decline and no bind.

## 7. Gold-writing rules

Same format as BOP, plus:

- `- Project value:` completed value, one number.
- `- Project period:` start and end in ISO, from the schedule only.
- `- TIV:` is `not in documents`; a project value is never written as TIV.
- `- Year built:` is `not in documents` for a new project.
- A stated "reported value" and "completed value" disagreement is a conflict with both sides.
- All `operations-gold-rule.md` rules apply unchanged.

## 8. Needs review

- Exact field names for project value and period.
- Occupied renovation rule is decided (D-121 item 8); the written line-allocation rule is still owed.
- Synthetic BR1–BR4 and the $10M/$5M/$7.5M placeholders.
- Whether a project with no loss run can be complete (recommended: yes, if every other required field is present).
