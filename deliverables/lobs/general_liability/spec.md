# general_liability — Wave 1 spec

- Authors: @senior-underwriter + @head-of-underwriting (written in OpenCode, not independently reviewed). Date: 2026-10-21.
- Wave 1. Synthetic data and placeholder carriers only. Not a production approval; the T-027 veto stands.
- **needs review** marks an open question, not a settled rule.

## 1. Identity

- LOB id: `general_liability` (`InsuranceLine.GENERAL_LIABILITY`). Family: small commercial P&C.
- Liability-only file: property COPE fields are optional; sales/payroll is the exposure base.
- Texas only in the pilot.

## 2. Typical submission documents

| Document | Required | Notes |
|---|---|---|
| Application (`application.md`) | Yes | ACORD 125 + 126-shaped; GL section must be present |
| Email (`email.md`) | No | Producer notes |
| Payroll/sales statement (`schedule.csv`) | Optional | Class-code payroll where stated |
| Carrier loss run (`loss-runs.md`) | Yes for a routable file | Published formats only |
| Scanned application | — | Out of scope (criterion 1) |

No property schedule is required. A schedule that contains only payroll rows is not a location schedule.

## 3. Required fields

| Field | Required | Notes |
|---|---|---|
| `named_insured` | Yes | Legal entity |
| `premises_address` | Yes | The insured's premises (mailing or operating) |
| `effective_date` | Yes | ISO |
| `operations` | Yes | Class plus stated details |
| `sales_or_payroll` | Yes | Gross annual sales or payroll, whichever the application states |
| `loss_run_valued_through` | Yes for a routable file | No-known-loss letter is not a date |
| `tiv_building` | **Optional** | Only when property is also quoted |
| `construction` | **Optional** | Only when property is also quoted |
| `year_built` | **Optional** | Only when property is also quoted |

Engine consequence: the GL pack sets `requires_tiv: false`. Routing must not apply R6 (TIV missing → hold) to a GL-only file. That is a routing-config change, not a new rule id; **needs review** before build.

## 4. Out-of-scope criteria

Baseline criteria 1–4. GL readings:

- Criterion 2 is about premises, not payroll rows: a payroll schedule with no addresses is not multiple locations.
- Criterion 4 applies when neither the application nor an ACORD 126-shaped section can be identified.

**needs review:** whether a GL file with no `sales_or_payroll` but a clear class is incomplete (recommended) or manual intake.

## 5. Operations slots

Same v11 closed list and slots. The class is the route driver. `business_type` values are the same 22; `contractor`, `restaurant`, `habitational` and prohibited values keep their current routes.

**needs review:** class-code capture (e.g., a 5-digit GL class) is not in today's field set. It is proposed for a later scorer version, not Wave 1.

## 6. Synthetic appetite and referral rules (placeholder carriers)

Fictional only.

| Carrier | Synthetic appetite | Route |
|---|---|---|
| Carrier A | Office, dry retail, light wholesale; no TIV requirement for GL-only | `carrier_a` |
| Carrier B | Restaurant or light contractor with 3 clean loss years | `senior_referral`, suggested `carrier_b` |
| Carrier C | Habitational, sprinklered; broader appetite | `senior_referral`, suggested `carrier_c` |

Rules R1, R2, R10–R14, R16, R17 unchanged, except R6 is not applied when `requires_tiv` is false. Rule ordering and note text stay the same.

**needs review:** whether a GL-only file over $5M sales (not TIV) should refer. Today's R13 is a TIV rule and cannot be reused as a sales cap without a written source.

## 7. Gold-writing rules

Same format as BOP, plus:

- `- TIV:` is `not in documents` for a GL-only file; the property fields are written `not in documents`, never guessed.
- `- Sales:` is the stated gross annual sales or payroll, one number.
- `- Expected carrier route:` is computed with R6 disabled for GL-only; the gold notes which pack flag applied.
- Scope line unchanged.
- A property/GL disagreement (e.g., construction) is a conflict only when property is quoted; otherwise the field is `not in documents`.
- All `operations-gold-rule.md` rules apply unchanged.

## 8. Needs review

- `requires_tiv: false` and the route-gate wording for GL-only files.
- Whether a missing `sales_or_payroll` is incomplete or manual intake.
- GL class-code field and its scorer slot.
- Any sales-based referral rule needs a written source before it exists.
