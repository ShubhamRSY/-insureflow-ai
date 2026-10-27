# commercial_property — Wave 1 spec

- Authors: @senior-underwriter + @head-of-underwriting (written in OpenCode, not independently reviewed). Date: 2026-10-21.
- Wave 1. Synthetic data and placeholder carriers only. Not a production approval; the T-027 veto stands.
- **needs review** marks an open question, not a settled rule.

## 1. Identity

- LOB id: `commercial_property` (`InsuranceLine.COMMERCIAL_PROPERTY`). Family: small commercial P&C.
- One location per submission in Wave 1; a schedule with two distinct addresses is scope criterion 2.
- Texas only in the pilot.

## 2. Typical submission documents

| Document | Required | Notes |
|---|---|---|
| Application (`application.md`) | Yes | ACORD 125 + 140-shaped; property section must be present |
| Property schedule / SOV (`schedule.csv`) | Yes | Building rows: address, construction, year built, TIV, BPP, sprinklers |
| Email (`email.md`) | No | Producer notes; conflicts are recorded, never silently resolved |
| Carrier loss run (`loss-runs.md`) | Yes for a routable file | Published formats only |
| Inspection report | Optional | May state construction/year built; conflicts go to the conflict field |
| Scanned application | — | Out of scope (criterion 1) |

## 3. Required fields

| Field | Required | Notes |
|---|---|---|
| `named_insured` | Yes | Legal entity |
| `premises_address` | Yes | The scheduled location |
| `effective_date` | Yes | ISO |
| `operations` | Yes | Occupancy/class of the tenant or owner |
| `tiv_building` | Yes | Building TIV for this location; $5,000,000 inclusive |
| `construction` | Yes | Frame/masonry/etc. in English |
| `year_built` | Yes | No inference from prose |
| `loss_run_valued_through` | Yes for a routable file | No-known-loss letter is not a date |
| `sales_or_payroll` | **Optional** | Not a property exposure; missing it must not hold the file |
| `bpp_limit` | Yes when stated | **Scored field** (D-120 item 6); required only when the schedule states BPP |
| `sprinklered` | Yes | **Scored field** (D-120 item 6); yes/no only when the schedule or application states it |

The property pack therefore makes `sales_or_payroll` optional and keeps every property field required. This is the first LOB where the required set differs from BOP; the engine change is the `required` flag in the pack, not code.

## 4. Out-of-scope criteria

Baseline criteria 1–4. Two property-specific readings:

- A schedule with several **buildings at one address** is one location (not criterion 2).
- A schedule with two **distinct addresses** is multiple locations (criterion 2), even if the application names only one.

**needs review:** whether a submission with no property schedule at all (application only) is manual intake or incomplete. Recommendation: incomplete, because the application still gives a class and TIV.

## 5. Operations slots

Same v11 closed list and slots. Property-relevant values: `office`, `retail`, `wholesale`, `restaurant`, `contractor`, `habitational`, `other_listed`, plus prohibited/referral values. Slots unchanged.

**needs review:** a property-only `occupancy` slot (owner-occupied vs tenant) is not in today's slot list and is proposed for a later scorer version, not Wave 1.

## 6. Synthetic appetite and referral rules (placeholder carriers)

Fictional only; a restatement of the current class rules with a property TIV reading.

| Carrier | Synthetic appetite | Route |
|---|---|---|
| Carrier A | Office, dry retail, light wholesale; building TIV ≤ $5,000,000; construction frame or better | `carrier_a` |
| Carrier B | Restaurant or light contractor property; TIV ≤ $3,000,000 (synthetic) | `senior_referral`, suggested `carrier_b` |
| Carrier C | Habitational and older construction; TIV ≤ $2,500,000 (synthetic) | `senior_referral`, suggested `carrier_c` |

Rules reuse R1, R2, R10–R14, R16, R17 unchanged. Property additions (all **needs review**):

- P1: TIV over $5M → `senior_referral` (today's R13, unchanged).
- P2: `construction` missing → hold, never a guess.
- P3: `year_built` missing → hold (today's status rule, unchanged).
- P4: roof age or protection class, if added later, must come from a written source.

## 7. Gold-writing rules

Same format as BOP, plus:

- `- TIV:` is the building TIV for the one location.
- `- BPP limit:` and `- Sprinklered:` are required once the pack lands; until then they are stated in `- Operations notes (unscored):` and are not scored by v11.
- A schedule/application disagreement on TIV, square feet, construction or year built writes both sides in `- Conflict:`; operations never absorbs the disagreement.
- Multiple buildings at one address: one premises line, TIV summed only when the schedule states a total; otherwise list the stated figures in the loss-run/claims note and mark **needs review**.
- Scope line: two distinct schedule addresses → `out of scope — 2 multiple locations`.
- All other rules from `operations-gold-rule.md` and D-102 apply unchanged.

## 8. Needs review

- The exact pack key names for `bpp_limit` and `sprinklered`, and which scorer version first scores them (a P-### under D-017).
- Whether application-only property files are incomplete or manual intake.
- Synthetic B/C property limits (they are placeholders, not sourced appetite).
- Owner-occupied vs tenant occupancy slot.
