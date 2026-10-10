# Required fields by class

- Author: @senior-underwriter
- Date: 2026-10-09
- Status: Draft for review (@ai-engineer, @data-engineer)
- Rule: if a **required** field is missing, the file is Incomplete. Do not quote and do not decline.

## Shared — every package account

| Field | Required to quote | Usual source | Often wrong |
|---|---|---|---|
| Named insured and legal entity | Yes | ACORD 125 | DBA used as the legal name |
| Mailing and premises addresses | Yes | ACORD 125 / 140 / SOV | Do not match each other |
| Effective date and prior carrier | Yes | ACORD 125 | — |
| Description of operations | Yes | ACORD 125 | Marketing language, not a class |
| Class code | Yes, underwriter-confirmed | ACORD or rater | Code copied from the expiring policy when operations changed |
| 5-year currently valued loss runs | Yes | Carrier PDF | "No known loss" letter; short runs |
| Open claims flag | Yes | Loss runs | Omitted on summary pages |
| Sales or payroll (GL base) | Yes | ACORD 126 | Estimated, not actual |
| Building TIV, BPP TIV | Yes if property is quoted | ACORD 140 / SOV | Blanket figure with no split |
| Construction, year built, protection class, sprinkler | Yes if property is quoted | ACORD 140 / SOV | Sprinkler inferred from "fire protection: yes" |
| Producer and BOR | Yes | Transmittal | — |

## Office (target)

Shared fields only, plus: occupancy (tenant vs owner), floors occupied, and whether any medical or lab use exists. Medical/lab is not office.

## Retail (target)

Shared fields, plus: percent of receipts from liquor (must be ≤ 10 for target), hours, and whether cooking exists. Any cooking → restaurant path.

## Lessor's risk / habitational (target only if ≤ 9 units)

Shared fields, plus: unit count, subsidized indicator, owner-occupied percent, smoke detectors, and **any cooking in units is assumed**. Senior referral even when all fields are present. Student housing and subsidized are prohibited for the pilot (assumption: confirm with @head-of-underwriting — I am treating them as prohibited because we cannot underwrite the program terms from an ACORD).

## Artisan contractor (target only with the limits in the appetite guide)

Shared fields, plus: percent receipts by trade, max stories, roofing percent, new vs service, written safety program (yes/no), and additional-insured requirements. Roofing percent > 0 → restricted, never auto-quote. Missing trade split → Incomplete.

## Restaurant (restricted, senior referral)

Do not auto-quote. Required before a human quotes: cooking type (griddle, fryer, solid fuel), extinguishing system inspection date, liquor percent, closing hour, seating. Missing extinguishing inspection → Incomplete, not decline.

## Fields that are not required and must not block a file

Website URL, social reviews, owner credit, owner criminal history, "AI risk score" from a vendor. If someone proposes using them, that is a @compliance question, not an underwriting convenience.
