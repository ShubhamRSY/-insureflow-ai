# Operations gold rule (small commercial) — D-094 item 2

Author: @senior-underwriter, 2026-10-15. Applies to NEW gold only. It is never applied backward: published gold and published scores (including SUB-127–146 as scored in T-027) are not rewritten.

## All fields, all future gold (D-102, 2026-10-16)
These two rules apply to every field of every gold file written from now on. Published gold and published scores are never rewritten.
1. **Empty field**: when the documents do not state a field, gold writes exactly `not in documents`. Never "missing", "missing, not given", "none" or a blank.
2. **"hold" is a status, never a route.** The gold route is the route the file takes once the hold clears (carrier_a, senior_referral, no_match, ...). A hold is written on the status line with its reason (e.g. "incomplete — hold: carrier run missing").

## Principle
Operations is what the insured does, written so an underwriter can price and route it. Gold records each item below **only when the documents state it**. Never infer, never add what the documents do not say. If an item is stated, gold must include it; an answer that drops it is a miss.

## Required items (each only when stated)
| Item | Gold writes | Example |
|---|---|---|
| Business type | Plain class of business | "full-service restaurant", "apartment building", "retail clothing store" |
| Alcohol | Yes/no kind, as stated. Types: "full liquor license", "beer and wine only", "beer only"; "no alcohol" only if the documents say so | "full liquor license" |
| Seating | Number + "seats" | "90 seats" |
| Unit count | Number + "units", plus buildings/stories if stated | "12 units in one two-story building" |
| Cooking | Cooking type if stated | "full kitchen", "no cooking", "microwave only" |
| Hours | Stated hours or days | "open 11am–2am", "Friday and Saturday nights" |

If the documents give a figure with a range or conflict, gold writes what is stated and the conflict goes to the conflicts field, not into operations.

## Other underwriting-relevant details (closed list; include only if stated)
live music / entertainment / DJ / dancing; deep frying or open flame (grill, wood-fired); delivery or catering; 24-hour operation; floor / story / basement location; on-site processing (manufacturing, food prep for resale, repair, storage of flammables); outdoor or patio service; security staff / bouncers; hazardous materials.
Anything not on this list is not required.

## NOT required
Marketing words and adjectives ("family-friendly", "award-winning", "cozy", "popular"), history, owner biography, awards, menu items (unless they show cooking type), prices.

## No operations stated
Gold writes exactly: `not in documents`. An empty extraction then counts as correct (scorer v2, D-094 item 4).

## Format
One line, comma-separated, most rating-relevant first: type, alcohol, seats/units, cooking, hours, other details.
Example: "Full-service restaurant and bar, full liquor license, 180 seats, live music Friday and Saturday".
