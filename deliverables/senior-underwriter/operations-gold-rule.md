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

## Operations checklist (D-103 item 3, scorer v5): all new gold
Applies to gold written from 2026-10-16 on. Published gold and scores are never rewritten. Scorer v5 (`eval_holdout_v5.py`) is committed before any gold that uses this.
1. Keep the one-line `- Operations:` (for the reader). Add one more line: `- Operations items: item; item; ...`.
2. List each item from the tables above (required items and the closed list of other details) that the documents state, one per `;`. Nothing else: no connectors ("under"), no business words the documents do not use ("taqueria", "apartment building" when the document says "residential apartments").
3. Write each item in the documents' own words, short: "restaurant", "no alcohol", "48 seats", "2 fryers", "Type I hood", "UL 300", "live music Thursday to Sunday", "16 units".
4. Scorer v5 credits operations when every item's words appear together and in order in the answer ("no" and "I" count; and/of/the/a/an/with are skipped). An item the answer leaves out, or whose words are scattered, is a miss. Write each item as the documents order the words ("2 fryers", not "fryers, 2"). An item never holds a comma, period, colon or semicolon: the scorer reads the answer clause by clause. A "no"/"not" right before the item's words in the answer makes it a miss, so write a stated absence as its own item ("no alcohol").
5. No operations stated: `- Operations: not in documents` and no items line.

## Gold lines read exactly (B-437, P-065, 2026-10-19)

Three lines the scorer reads word for word, found by the T-109c lint on T-108 gold. They apply to all future gold; published gold and published scores are never rewritten. The scorer change is `eval_holdout_v9.py` (approved as P-065); the lint `lint_holdout.py --self-check` holds a card of each shape.

1. **Conflict with nothing to flag**: `- Conflict: none` alone, or `none` with a short note after it in parentheses or after a dash saying the documents agree — `none (schedule matches application on TIV/sq ft/construction/year built)`. The note names agreement only; it never names a disagreement as if it were a conflict (a real conflict writes both sides: `sales: 742000 (application) vs 940000 (email)`). v9 reads any of these as "no conflict"; before v9 only the bare `none` did, so a note after it scored the perfect answer a conflict miss (5 T-108 files).
2. **Loss-run valuation date**: every in-scope card whose loss run has a date carries exactly one line `- Loss runs valued as of: YYYY-MM-DD` — the valuation date, never the policy-period start. A review card (`needs review`), a card with no loss run, or a card never assessed carries **no such line**: its presence there is an error that stops the scorer, it is not a second opinion.
3. **Expected loss run**: when review is expected, say `needs review` anywhere on the line (`Carrier A layout but no valued-as-of date; needs review — ask for a dated carrier run`); the two other review wordings keep starting the line: `loss run found but no valued-as-of date`, `not assessed`. A parenthetical is a note to the reader, not the expectation — `Carrier B format recognised (needs review context ok)` expects a date. Before v9 only the start of the line was read, so a card naming review mid-line demanded a date it never has (2 T-108 files).
4. **Hours in `- Operations items:`**: write the documents' own form (`closes 11 p.m.`, `open until 2:00 a.m.`, `11pm`); v9 reads every written form as the same hour and still misses an hour the answer does not state, or the wrong meridiem. Before v9 the item's full stops cut the clause and the item could never match (3 T-108 files).
