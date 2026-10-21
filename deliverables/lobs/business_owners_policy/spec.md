# business_owners_policy — Wave 1 spec

- Authors: @senior-underwriter + @head-of-underwriting (written in OpenCode, not independently reviewed). Date: 2026-10-21.
- Status: reference line for Wave 1. Synthetic data and placeholder carriers only. **Not a production approval**; the T-027 veto stands.
- Anything marked **needs review** is not settled and must not be built as if it were.

## 1. Identity

- LOB id: `business_owners_policy` (`InsuranceLine.BOP`). Family: small commercial P&C.
- Wave 1. This is the current pilot line: the engine's behaviour here is the baseline that every later LOB must not change.
- One premises per submission. Texas only in the pilot.

## 2. Typical submission documents

| Document | Required | Notes |
|---|---|---|
| Application (`application.md`) | Yes | ACORD 125-shaped; property and liability sections |
| Email (`email.md`) | No | Producer notes; may add facts, never overrides the application silently |
| Property schedule / SOV (`schedule.csv`) | No | One row per building; a second location is a scope criterion (2) |
| Carrier loss run (`loss-runs.md`) | Yes for a routable file | Publisher formats in `simulation/carrier-loss-run-formats.md` |
| Scanned application | — | Out of scope (criterion 1) |

## 3. Required fields

Shared nine, all required for a complete file:

| Field | Kind | Required | Notes |
|---|---|---|---|
| `named_insured` | text | Yes | Legal entity, not DBA |
| `premises_address` | address | Yes | One premises |
| `effective_date` | date | Yes | ISO after parsing |
| `operations` | soft text | Yes | Class plus stated details; never marketing words |
| `sales_or_payroll` | number | Yes | Gross annual sales for BOP |
| `tiv_building` | number | Yes | Building TIV; exactly $5,000,000 passes |
| `construction` | soft text | Yes | English word |
| `year_built` | number | Yes | No guess from "the 80s" |
| `loss_run_valued_through` | date | Yes | A no-known-loss letter is not a date |

Scored additions (D-120 item 6), not in today's schema:

- `bpp_limit` (number): business personal property, where stated. Required only if the application quotes BPP.
- `sprinklered` (yes/no): already derived today (`report["sprinklers"]`); it becomes a first-class scored field.

Rule: anything affecting status, route or a value sent to a carrier is scored; display-only facts are context only. `bpp_limit` and `sprinklered` qualify. They are recorded in dev gold now (documents + notes) and scored once the pack and scorer carry them.

## 4. Out-of-scope criteria

Baseline criteria 1–4, unchanged:

1. scanned application;
2. multiple locations (more than one premises or a schedule with two distinct addresses);
3. non-English documents;
4. application not identified.

No BOP-specific criterion is added in Wave 1. A property-only application with no liability section is **not** out of scope; it is incomplete (missing liability facts), not manual intake. **needs review**: whether a BOP pack missing either coverage section should be manual intake instead.

## 5. Operations slots

The v11 closed list (`BT_SYNONYMS`, 22 values) applies unchanged. BOP-relevant values:

`office`, `retail`, `wholesale`, `restaurant`, `contractor`, `habitational`, `other_listed`, plus the prohibited values (`bar_pub`, `lounge_nightclub`, `hookah_adult`, `cannabis`, `fireworks_explosives`, `armed_security`, `bail_bonds`, `student_subsidized_housing`, `sawmill_pallet_plastics_recycling`) and referral values (`hazardous_goods`, `lab_medical`, `cold_storage`, `liquor_store`, `vacant`).

- `business_type` items are compared as a set; a missing or extra class is a miss.
- Slots (alcohol, seats, units, cooking, fryer, open_flame, hood, entertainment, hours, delivery, 24h, onsite_processing, outdoor, security, hazmat, floor) are unchanged.
- Facts outside the slot list go to `Operations notes (unscored)`.

## 6. Synthetic appetite and referral rules (placeholder carriers)

All three carriers and every limit below are **fictional**. They restate today's `carrier-match.md` for BOP and add nothing to it. **D-120 item 10:** BOP keeps only the suggestions that exist in `carrier-match.md`; no other class or market is suggested in this spec.

| Carrier | Synthetic appetite for BOP | Route today |
|---|---|---|
| Carrier A | Office, dry retail, light wholesale; TIV ≤ $5,000,000 per location | `carrier_a` (the only direct route) |
| Carrier B | Restaurant or light contractor with 3 clean loss years | `senior_referral`, suggested `carrier_b`; underwriter confirms |
| Carrier C | Broader appetite, higher price; habitational with sprinklers | `senior_referral`, suggested `carrier_c`; underwriter confirms |

Rules: R1 prohibited class → `no_match` (never overridable, never a decline); R2 bar/liquor exposure → `senior_referral`; R10 restaurant → `senior_referral`, suggested Carrier B only; R11 contractor → `senior_referral`, suggested Carrier B only; R12 habitational → `senior_referral`, suggested Carrier C only, sprinkler answer missing → hold; R13 TIV over $5M → `senior_referral`; R14 allow-list → `carrier_a`; R16 second operation → `senior_referral`; R17 strict allow-list words → `senior_referral` with Carrier A suggested.

No market confirm, no decline and no send by any AI role; the underwriter confirms.

## 7. Gold-writing rules

Every gold file is written from the documents and the written rules, before extraction, and is never rewritten (D-020/D-022, D-102).

Required lines:

```
- Status: complete | incomplete — hold: <reason> | complete — review pending
- Scope: in scope | out of scope — <criteria>
- Named insured:
- Premises:
- Effective date:
- Operations:
- Operations items: business_type=<value>; <slot items>
- Operations notes (unscored):
- Sales:
- TIV:
- Construction:
- Year built: | not in documents
- Loss runs: <format and period>
- Loss runs valued as of: YYYY-MM-DD   # only when a date exists
- Claims:
- Missing:
- Conflict: none | <field>: <value> (source) vs <value> (source)
- Format:
- Expected carrier route:
- Expected recommendation:
- Expected loss run:
- Expected pipeline status:
```

Rules:

- Empty field: exactly `not in documents`.
- "hold" is a status, never a route.
- `Operations items` uses only declared `business_type` values and slots; anything else goes to notes.
- Loss-run date only from `- Loss runs valued as of:`; never the policy-period start.
- New scored lines (`- BPP limit:` and `- Sprinklered:`) are added when the pack lands; until then BPP and sprinklers are stated in `- Operations notes (unscored):` and are not scored by v11.
- Route is the route the file takes once the hold clears.
- Every gold card carries `FICTIONAL. Not a carrier decision.`

## 8. Needs review

- BOP-specific scope criterion for a missing coverage section.
- The exact pack key names for `bpp_limit` and `sprinklered`, and which scorer version first scores them (a P-### under D-017).
- Real carrier terms (confidential) once @head-of-underwriting and @compliance sign them; until then only the placeholder table above.
- `commercial_package` is a separate pack composed from the property and GL packs (D-120 item 4), not a BOP variant; no BOP pack change is implied.
