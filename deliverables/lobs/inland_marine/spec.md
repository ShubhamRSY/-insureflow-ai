# inland_marine — Wave 2 spec

- Authors: @senior-underwriter + @head-of-underwriting (written in OpenCode, not independently reviewed). Date: 2026-10-21.
- Wave 2. Synthetic data and placeholder carriers only. Not a production approval; the T-027 veto stands.
- **needs review** marks an open question, not a settled rule.
- D-120 item 1: Wave 2 starts with `umbrella`; this line follows it.

## 1. Identity

- LOB id: `inland_marine` (`InsuranceLine.INLAND_MARINE`). Family: small commercial P&C.
- Scheduled property in transit or at unscheduled/remote locations: contractor equipment, tools, cameras, medical or office equipment, goods in transit. The exposure base is **per-item values**, not one building TIV.
- One named insured; one or more scheduled items. Texas only in the pilot.

## 2. Typical submission documents

| Document | Required | Notes |
|---|---|---|
| Application (`application.md`) | Yes | ACORD 125-shaped; inland marine section present |
| Equipment / item schedule (`schedule.csv`) | Yes | One row per item: description, value/limit, location, serial where stated |
| Email (`email.md`) | No | Producer notes |
| Carrier loss run (`loss-runs.md`) | Yes for a routable file | Published formats only |
| Scanned application/schedule | — | Out of scope (criterion 1) |

## 3. Required fields

| Field | Required | Notes |
|---|---|---|
| `named_insured` | Yes | Legal entity |
| `premises_address` | Yes | Mailing/operating address; item locations come from the schedule |
| `effective_date` | Yes | ISO |
| `operations` | Yes | Class plus stated details |
| `sales_or_payroll` | Optional | Not an inland marine exposure; never holds the file |
| `loss_run_valued_through` | Yes for a routable file | No-known-loss letter is not a date |
| `tiv_building` | No | A building TIV is not the exposure; `not in documents` when absent |
| `construction`, `year_built` | No | Only when a building is also scheduled |
| `scheduled_item_count` | Yes (new) | Number of rows in the schedule; **needs review** name |
| `scheduled_items_total` | Yes (new) | Sum of stated item values/limits; **needs review** name |
| `scheduled_item_values` | Yes (new) | The item rows themselves (description/value/location); **needs review** shape |

The item rows are a structured list, not a single number. The engine needs a schedule reader for them; that is the expensive part of this line.

## 4. Out-of-scope criteria

Baseline criteria 1–4. Inland marine readings:

- Items at several **stated locations** are normal for this line and are **not** criterion 2. Criterion 2 is multiple named insureds/premises addresses on the application, or a second application.
- A schedule with no readable item value, and no total, is **incomplete**, not manual intake.
- A scanned schedule is criterion 1 until a reader is approved.

**needs review:** confirm the multi-location reading above; it differs from property/BOP.

## 5. Operations slots

Same v11 closed list and slots. `contractor`, `office`, `retail`, `wholesale` are the common classes. No inland-marine-specific slot in this spec.

**needs review:** a `transit` / `off_premises` slot is proposed for a later scorer version; not in v11.

## 6. Synthetic appetite and referral rules (placeholder carriers)

Fictional only; a placeholder for @head-of-underwriting.

| Carrier | Synthetic appetite | Route |
|---|---|---|
| Carrier A | Office/retail/wholesale class; scheduled total ≤ $2,500,000; no transit exposure | `carrier_a` |
| Carrier B | Contractor tools/equipment; scheduled total ≤ $1,500,000 | `senior_referral`, suggested `carrier_b` |
| Carrier C | Broader appetite, higher price; transit and remote locations | `senior_referral`, suggested `carrier_c` |

Rules (all **needs review**): IM1 any item value missing → hold; IM2 total over the carrier limit → referral; IM3 transit or off-premises storage → senior referral; IM4 prohibited class (R1) → `no_match`; everything else follows the class rules. No decline and no bind.

## 7. Gold-writing rules

Same format as BOP, plus:

- One line per item: `- Item: <description> | value <amount> | <location>`; no item is inferred from a total.
- `- Scheduled items:` count and total, both from the schedule only.
- `- TIV:` is `not in documents` for an item-only file.
- A schedule/application disagreement is a conflict with both sides.
- All `operations-gold-rule.md` rules apply unchanged.

## 8. Needs review

- The exact new field names and whether item rows live in the field set or a separate schedule table.
- Multi-location scope reading (items at stated locations are in scope).
- Synthetic IM1–IM4 and the $2.5M/$1.5M placeholders.
- Whether a transit slot is added before build or after the first eval.
