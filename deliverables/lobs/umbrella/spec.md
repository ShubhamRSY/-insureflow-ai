# umbrella — Wave 1 spec

- Authors: @senior-underwriter + @head-of-underwriting (written in OpenCode, not independently reviewed). Date: 2026-10-21.
- Wave 1. Synthetic data and placeholder carriers only. Not a production approval; the T-027 veto stands.
- **needs review** marks an open question, not a settled rule.

## 1. Identity

- LOB id: `umbrella` (`InsuranceLine.UMBRELLA`). Family: small commercial P&C.
- Excess liability over underlying GL, auto and employers liability. No building COPE in Wave 1; the exposure base is the underlying limits and the umbrella limit.
- Texas only in the pilot.

## 2. Typical submission documents

| Document | Required | Notes |
|---|---|---|
| Application (`application.md`) | Yes | ACORD 125-shaped; umbrella section with limits |
| Underlying declarations (`schedule.csv` or an attached declarations page) | Yes | GL, auto and employers liability limits, carrier and policy period |
| Email (`email.md`) | No | Producer notes |
| Carrier loss run (`loss-runs.md`) | Yes for a routable file | Published formats only |
| Scanned application | — | Out of scope (criterion 1) |

**needs review:** whether an umbrella file with no machine-readable underlying declarations is manual intake (recommended: incomplete, with a named missing item) or out of scope.

## 3. Required fields

Shared nine plus new fields. All new ones are **needs review** until the engine pack exists.

| Field | Required | Notes |
|---|---|---|
| `named_insured` | Yes | Legal entity |
| `premises_address` | Yes | Named insured's premises |
| `effective_date` | Yes | ISO |
| `operations` | Yes | The underlying class of business |
| `sales_or_payroll` | Yes | Underlying GL exposure |
| `loss_run_valued_through` | Yes for a routable file | No-known-loss letter is not a date |
| `umbrella_limit` | Yes (new) | Per-occurrence or aggregate as stated; record which |
| `underlying_gl_limit` | Yes (new) | Each occurrence / aggregate as stated |
| `underlying_auto_limit` | Yes (new) | Combined single limit as stated |
| `underlying_employers_liability_limit` | Yes (new) | Per accident / disease as stated |
| `underlying_carrier(s)` | Yes (new) | One or more names; a carrier note can exclude a market |
| `tiv_building`, `construction`, `year_built` | No | Not umbrella exposures; `not in documents` when absent |

The engine consequence is a **field-schema-only** change: the extraction prompt gains four limit fields and one carrier field; the property fields become optional. No new reader.

## 4. Out-of-scope criteria

Baseline criteria 1–4, plus one proposed criterion:

- 5. **underlying coverage not evidenced** (no declarations or limits anywhere) → manual intake.

Criterion 5 is **needs review** because it changes the scope gate and therefore needs a P-### and a new scorer/lint. Until approved, such a file is incomplete.

## 5. Operations slots

Same v11 closed list and slots; the class comes from the underlying GL policy. No umbrella-specific slot in Wave 1.

**needs review:** whether the underlying carrier names and policy numbers are operations items (recommended: no, they are fields) and whether a "claims-made vs occurrence" item is a slot (recommended: notes until defined).

## 6. Synthetic appetite and referral rules (placeholder carriers)

Fictional only.

| Carrier | Synthetic appetite | Route |
|---|---|---|
| Carrier A | Umbrella over a Carrier A underlying GL/property account; umbrella limit ≤ $5,000,000; all underlying limits stated | `carrier_a` |
| Carrier B | Umbrella over restaurant/contractor underlying; limit ≤ $3,000,000 (synthetic) | `senior_referral`, suggested `carrier_b` |
| Carrier C | Broader appetite, higher price; habitational underlying with sprinklers | `senior_referral`, suggested `carrier_c` |

Proposed umbrella rules (all synthetic, all **needs review**):

- U1: any required underlying limit missing → hold "missing information".
- U2: umbrella limit below the highest underlying limit → hold, because attachment is unclear.
- U3: underlying carrier note excludes a market → that carrier is not suggested (reuses the current exclusion logic).
- U4: underlying class is prohibited (R1) → `no_match`, never overridable.
- U5: two or more underlying carriers with different classes → `senior_referral`.

No decline and no bind, as everywhere.

## 7. Gold-writing rules

Same format as BOP, plus new lines (only once the fields are in the pack):

```
- Underlying GL limit:
- Underlying auto limit:
- Underlying employers liability:
- Underlying carrier(s):
- Umbrella limit:
```

Rules:

- Each limit line records the stated figure and its basis (occurrence/aggregate/CSL); a missing limit is `not in documents`.
- A limit that appears in two documents with different figures is a conflict with both sides.
- `- TIV:`, `- Construction:`, `- Year built:` are `not in documents` for an umbrella-only file.
- `- Expected carrier route:` follows U1–U5; a hold is a status, never a route.
- The underlying carrier exclusion note is read for market confirms exactly as today.
- All `operations-gold-rule.md` rules apply unchanged.

## 8. Needs review

- The five new fields: exact names, required/optional, and whether a carrier name is a scored field.
- Scope criterion 5 (underlying not evidenced) and its scorer change.
- Synthetic U1–U5 rules and B/C limits; @head-of-underwriting to confirm or replace.
- Whether umbrella shares the BOP operations pack or needs its own.
- @compliance: underlying declarations may contain other insureds' data; check the data-handling question before real files.
