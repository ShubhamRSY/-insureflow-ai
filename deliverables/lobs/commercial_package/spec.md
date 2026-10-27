# commercial_package — Wave 1 spec

- Authors: @senior-underwriter + @head-of-underwriting (written in OpenCode, not independently reviewed). Date: 2026-10-21.
- Wave 1. Synthetic data and placeholder carriers only. Not a production approval; the T-027 veto stands.
- **needs review** marks an open question, not a settled rule.
- **D-120 item 4:** this is a pack **composed from the property and GL packs**, not the BOP pack plus flags. It owns no rule text of its own; it composes the two sections' required fields, scope and routes.

## 1. Identity

- LOB id: `commercial_package` (`InsuranceLine.COMMERCIAL_PACKAGE`). Family: small commercial P&C.
- A package of property and general liability on one account. The composition rule: property fields and rules come from `commercial_property`; GL fields and rules come from `general_liability`; the package adds only the rule that both sections must be present and consistent.
- One premises per submission; Texas only in the pilot.

## 2. Typical submission documents

| Document | Required | Notes |
|---|---|---|
| Application (`application.md`) | Yes | ACORD 125 + 140 + 126-shaped; both property and GL sections |
| Property schedule / SOV (`schedule.csv`) | Yes when property is quoted | Building rows |
| Email (`email.md`) | No | Producer notes |
| Carrier loss run (`loss-runs.md`) | Yes for a routable file | Published formats only |
| Scanned application | — | Out of scope (criterion 1) |

## 3. Required fields (the composition)

The required set is the **union** of the property pack and the GL pack:

| Field | Source pack | Required |
|---|---|---|
| `named_insured` | both (identical) | Yes |
| `premises_address` | both (identical) | Yes |
| `effective_date` | both (identical) | Yes |
| `operations` | both (identical) | Yes |
| `sales_or_payroll` | GL | Yes |
| `tiv_building` | property | Yes when property is quoted; $5,000,000 inclusive |
| `construction` | property | Yes when property is quoted |
| `year_built` | property | Yes when property is quoted |
| `loss_run_valued_through` | both (identical) | Yes for a routable file |
| `bpp_limit` | property | Yes when stated; **scored** (D-120 item 6) |
| `sprinklered` | property | Yes when stated; **scored** (D-120 item 6) |

A conflict between the two sections (e.g., different construction) is an open conflict and holds the file; the package adds no third answer.

**needs review:** whether a package with one coverage section missing is incomplete (recommended) or manual intake. It is not a composition failure.

## 4. Out-of-scope criteria

The property and GL criteria are identical in Wave 1 (baseline 1–4). Package readings:

- Two distinct schedule addresses → criterion 2, even if the application shows one.
- A package with only one coverage section is **incomplete**, not manual intake (unless criterion 4 applies).
- A property schedule with several buildings at one address is one location.

## 5. Operations slots

The v11 closed list and slots apply unchanged; the operations value is shared by both sections. No package-specific slot.

**needs review:** whether a stated coverage mix (e.g., property 60% / GL 40%) is an operations item or a notes item. Recommendation: notes, not scored, until a slot is defined.

## 6. Synthetic appetite and referral rules (placeholder carriers)

The package uses the **intersection of the property and GL routes**: a direct `carrier_a` route requires both sections to be in Carrier A appetite by their own rules. If either section refers, the package refers. No package-specific carrier terms exist.

| Carrier | Synthetic appetite | Route |
|---|---|---|
| Carrier A | Property: office/dry retail/light wholesale, TIV ≤ $5M. GL: same class, no TIV requirement | `carrier_a` only when both sections pass |
| Carrier B | Restaurant or light contractor (property or GL) | `senior_referral`, suggested `carrier_b` |
| Carrier C | Habitational with sprinklers (property or GL) | `senior_referral`, suggested `carrier_c` |

Only suggestions that exist in `carrier-match.md` are used (D-120 item 10); the package invents none. **needs review:** "either section out → refer" is the composition rule and still needs @head-of-underwriting's written confirmation.

## 7. Gold-writing rules

Same format as BOP, plus:

- One `- TIV:` line per location (Wave 1: one location).
- `- BPP limit:` and `- Sprinklered:` are written when the pack carries them; until then they are stated in `- Operations notes (unscored):`.
- Both coverage sections are described in `- Format:` (e.g., "typed md app (property + GL), schedule csv, Carrier A loss run").
- If property and GL facts disagree, the field is a conflict, not two answers.
- If only one section is present, `- Missing:` names the missing section's required facts; status is incomplete.
- All `operations-gold-rule.md` rules apply unchanged.

## 8. Dev data (this task)

- 10 synthetic dev files, `simulation/inbox-dev/commercial_package/SUB-270`–`SUB-279`; dev gold at `deliverables/senior-underwriter/gold-set-commercial_package/dev/`. Dev only: never hold-out evidence, never scored as a published result.
- Mix: 4 Carrier A office/retail/wholesale, 2 restaurant, 2 contractor, 1 habitational, 1 over the $5M TIV limit. All complete and in scope; the lint must PASS.
- The dev gold records BPP and sprinklers in the documents now; they become scored lines only when the pack and scorer carry them.

## 9. Needs review

- One-section-missing status (incomplete vs manual intake).
- Written confirmation of "either section out → refer".
- Coverage-mix capture (notes vs slot).
- Exact pack keys and the scorer version for `bpp_limit` / `sprinklered` (P-### under D-017).
- Real carrier terms (confidential) after @head-of-underwriting + @compliance sign-off.
