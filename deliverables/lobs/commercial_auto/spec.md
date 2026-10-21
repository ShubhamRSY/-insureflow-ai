# commercial_auto — Wave 2 spec

- Authors: @senior-underwriter + @head-of-underwriting (written in OpenCode, not independently reviewed). Date: 2026-10-21.
- Wave 2. Synthetic data and placeholder carriers only. Not a production approval; the T-027 veto stands.
- **needs review** marks an open question, not a settled rule.

## 1. Identity

- LOB id: `commercial_auto` (`InsuranceLine.COMMERCIAL_AUTO`). Family: small commercial P&C.
- Business vehicles: the exposure base is the **vehicle schedule and limits**, not TIV or payroll.
- One garage location per submission in Wave 2; Texas only in the pilot.

## 2. Typical submission documents

| Document | Required | Notes |
|---|---|---|
| Application (`application.md`) | Yes | ACORD 125 + 127-shaped; auto section present |
| Vehicle schedule (`schedule.csv`) | Yes | One row per vehicle: VIN, year, make/model, garaging, use |
| MVR (`mvr.md` or attached) | Optional | Third-party consumer data; @compliance question before real files |
| Carrier loss run (`loss-runs.md`) | Yes for a routable file | Published formats only; per-vehicle claims where stated |
| Email (`email.md`) | No | Producer notes |
| Scanned application | — | Out of scope (criterion 1) |

## 3. Required fields

| Field | Required | Notes |
|---|---|---|
| `named_insured` | Yes | Legal entity |
| `premises_address` | Yes | Garage/operating address |
| `effective_date` | Yes | ISO |
| `operations` | Yes | Class plus stated details |
| `sales_or_payroll` | Optional | Not the auto exposure |
| `loss_run_valued_through` | Yes for a routable file | No-known-loss letter is not a date |
| `vehicle_count` | Yes (new) | Rows in the vehicle schedule; **needs review** name |
| `vehicle_rows` | Yes (new) | VIN, year, make/model, garaging, use per row; **needs review** shape |
| `auto_liability_limit` | Yes (new) | Stated CSL or split limits; **needs review** name |
| `tiv_building`, `construction`, `year_built` | No | `not in documents` unless property is quoted |

## 4. Out-of-scope criteria

Baseline criteria 1–4, plus criterion 5:

- Two distinct garage addresses → criterion 2 in Wave 2.
- A vehicle schedule with no readable VIN/year but otherwise complete is **incomplete**, not manual intake.
- A personal auto submission (personal named insured, personal use) is a **scope criterion 5 → manual intake** (D-121 item 9).

## 5. Operations slots

Same v11 closed list and slots; the class describes the business, not the vehicle. No auto-specific slot in v11.

**needs review:** `fleet_size_band`, `long_haul`, `hazmat_cargo` and `passenger_transport` are proposed slots for a later scorer version, not Wave 2.

## 6. Synthetic appetite and referral rules (placeholder carriers)

Fictional only.

| Carrier | Synthetic appetite | Route |
|---|---|---|
| Carrier A | Office/retail/wholesale; ≤ 10 vehicles; no hazardous cargo; CSL ≤ $1,000,000 | `carrier_a` |
| Carrier B | Contractor or restaurant; ≤ 15 vehicles; clean 3-year loss record | `senior_referral`, suggested `carrier_b` |
| Carrier C | Broader appetite, higher price; habitational/fleet | `senior_referral`, suggested `carrier_c` |

Rules (all **needs review**): CA1 vehicle count or limits missing → hold; CA2 a VIN/year contradiction between application and schedule → conflict, hold; CA3 hazardous cargo or passenger transport → referral; CA4 prohibited class (R1) → `no_match`. No decline and no bind.

## 7. Gold-writing rules

Same format as BOP, plus:

- One `- Vehicle:` line per row: `VIN | year | make/model | garaging | use`.
- `- Vehicle count:` and `- Auto liability limit:` from the schedule/application only.
- `- TIV:` is `not in documents` for an auto-only file.
- A per-vehicle claim is written on the claims line with its vehicle identifier where stated.
- All `operations-gold-rule.md` rules apply unchanged.

## 8. Needs review

- Exact field and row shape for vehicles, and whether VIN is a scored field.
- Synthetic CA1–CA4 and the vehicle/limit placeholders.
- @compliance: MVR is a consumer report; permissible purpose and FCRA notice before real files.
