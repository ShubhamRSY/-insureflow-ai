# commercial_package — Wave 1 spec

- Authors: @senior-underwriter + @head-of-underwriting (written in OpenCode, not independently reviewed). Date: 2026-10-21.
- Wave 1. Synthetic data and placeholder carriers only. Not a production approval; the T-027 veto stands.
- **needs review** marks an open question, not a settled rule.

## 1. Identity

- LOB id: `commercial_package` (`InsuranceLine.COMMERCIAL_PACKAGE`). Family: small commercial P&C.
- A package of property and general liability on one account. In Wave 1 it is intentionally close to BOP: same pack shape, two coverage sections, no new readers.
- One premises per submission; Texas only in the pilot.

## 2. Typical submission documents

| Document | Required | Notes |
|---|---|---|
| Application (`application.md`) | Yes | ACORD 125 + 140 + 126-shaped; both property and GL sections |
| Property schedule / SOV (`schedule.csv`) | Yes when property is quoted | Building rows |
| Email (`email.md`) | No | Producer notes |
| Carrier loss run (`loss-runs.md`) | Yes for a routable file | Published formats only |
| Scanned application | — | Out of scope (criterion 1) |

## 3. Required fields

| Field | Required | Notes |
|---|---|---|
| `named_insured` | Yes | Legal entity |
| `premises_address` | Yes | One premises |
| `effective_date` | Yes | ISO |
| `operations` | Yes | Class plus stated details |
| `sales_or_payroll` | Yes | GL exposure |
| `tiv_building` | Yes when property is quoted | $5,000,000 inclusive |
| `construction` | Yes when property is quoted | English word |
| `year_built` | Yes when property is quoted | No inference |
| `loss_run_valued_through` | Yes for a routable file | No-known-loss letter is not a date |
| `bpp_limit` | **needs review** | Proposed new field; required only when the schedule states BPP |

**needs review:** whether the package pack is literally the BOP pack plus a `coverages: ["property", "gl"]` flag, or a separate pack. Recommendation: separate pack that shares values, so the two can diverge without a code branch.

## 4. Out-of-scope criteria

Baseline criteria 1–4. Package readings:

- Two distinct schedule addresses → criterion 2, even if the application shows one.
- A package with only one coverage section is **incomplete**, not manual intake (unless criterion 4 applies).
- A property schedule with several buildings at one address is one location.

## 5. Operations slots

Same v11 closed list and slots; the operations value is shared by both coverage sections. No package-specific slot in Wave 1.

**needs review:** whether a stated coverage mix (e.g., property 60% / GL 40%) is an operations item or a notes item. Recommendation: notes, not scored, until a slot is defined.

## 6. Synthetic appetite and referral rules (placeholder carriers)

Fictional only; identical to BOP in Wave 1.

| Carrier | Synthetic appetite | Route |
|---|---|---|
| Carrier A | Office, dry retail, light wholesale; property TIV ≤ $5,000,000; GL class on the allow-list | `carrier_a` |
| Carrier B | Restaurant or light contractor package; 3 clean loss years | `senior_referral`, suggested `carrier_b` |
| Carrier C | Habitational with sprinklers; broader appetite | `senior_referral`, suggested `carrier_c` |

R1, R2, R10–R14, R16, R17 unchanged. Both sections must be in appetite for a direct route; if either section is out of appetite, the file refers. **needs review:** that "either section out" rule has no written source today; it is a placeholder for @head-of-underwriting.

## 7. Gold-writing rules

Same format as BOP, plus:

- One `- TIV:` line per location (Wave 1: one location).
- Both coverage sections are described in `- Format:` (e.g., "typed md app (property + GL), schedule csv, Carrier A loss run").
- If property and GL facts disagree (e.g., construction), the field is a conflict, not two answers.
- If only one section is present, `- Missing:` names the missing section's required facts; status is incomplete.
- All `operations-gold-rule.md` rules apply unchanged.

## 8. Needs review

- Separate pack vs BOP pack with coverage flags.
- "Either section out of appetite → refer" as a written rule.
- `bpp_limit` field and gold line.
- Coverage-mix capture (notes vs slot).
