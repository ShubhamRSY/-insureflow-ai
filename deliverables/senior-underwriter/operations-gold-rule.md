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

## Slot definition table (T-114 / D-117, 2026-10-20)

Author: @senior-underwriter. Source of truth for the slot-based operations scorer (D-117: slots are defined here, from underwriting knowledge and the tables above — never from any hold-out answer's phrasing). Each gold `- Operations items:` item must map to exactly one slot below and carry that slot's value. Facts outside this table stay out of gold items (the closed list above is unchanged).

### Shared semantics (apply to every slot)

- **Clause**: the span between two semicolons (or the line's ends). Slots are compared only within one clause; a negation never reaches across a clause boundary.
- **Void / flip (negation)**: within a clause, a negation word before the slot's trigger words — `no`, `not`, `none`, `without`, `never`, `sin`, `no hay`, `nada de` — flips the trigger to the slot's absent value (`none` / `no`). If gold expects presence and the answer negates, that is a miss.
- **Absence is a value, never a drop**: a phrase that itself states the absence ("no alcohol", "sin cocina") sets the absent value. It is a slot fact, not nothing.
- **Comparison rule (all slots)**: two answers match on a slot only if they hold the same value after normalization. Integer slots require the exact integer (a different count is a miss). Presence vs absence is a miss. A slot gold states and the answer omits is a miss. Different enumerated values are a miss (beer & wine vs full bar is a miss, not a partial).
- **Marketing words, menu items, merchandise lists, prices, history**: never slots (NOT required list above).

### The table

| # | Slot | Allowed values | Trigger vocabulary (underwriting synonyms; English + Spanish) | Void / flip (→ absent value) | Notes |
|---|------|----------------|--------------------------------------------------|------------------------------------------------|-------|
| 1 | `business_type` | Open: plain class of business | restaurant; full-service restaurant; bar; restaurant and bar; cafe; cafe/bakery; bakery; taqueria; barbeque/BBQ restaurant; breakfast/lunch restaurant; gift shop; retail store; boutique; stationery/office-supplies store; outdoor gear store; clothing store; thrift/used-goods store; wholesale/warehouse; office; office suite; CPA/tax office; financial advisory; medical clinic; physical therapy clinic; laundromat; apartment building(s); apartments; HVAC contractor; plumbing contractor; roofing contractor; drywall contractor; glass contractor; fireworks retailer. ES: restaurante; taqueria; panaderia; consultorio; oficina; tienda; clínica | — (open value; a negated class, "not a restaurant", sets the stated class only if documents say so) | Match = same trade words in the same clause, loose. Merchandise/menu glosses ("tacos, burritos", "candles, home goods") are not part of the value. |
| 2 | `alcohol` | `none` \| `beer_only` \| `beer_wine` \| `full_bar` | **full_bar**: full liquor license; full liquor; liquor license (unqualified, present tense); bar; restaurant and bar; spirits; mixed drinks; hard liquor; TABC/mixed beverage permit; licor licencia completa; licores; bebidas espirituosas; cocteles. **beer_wine**: beer and wine only; beer & wine; beer/wine; wine and beer; vino y cerveza; cerveza y vino; solo cerveza y vino. **beer_only**: beer only; cerveza solamente. **none**: no alcohol; no liquor; no alcohol of any kind; dry bar/sin bar; sin licor; sin alcohol; no sirven alcohol | Negation before any trigger flips to the negated value: "no liquor license" in a beer & wine clause confirms `beer_wine`, never `full_bar`; "no bar" alone sets no bar service, not a value. | "dry" standing alone ("dry retail/gift shop") is NOT an alcohol trigger — underwriting "dry" is ambiguous with "dry goods"; only explicit "no alcohol/sin licor" sets `none`. |
| 3 | `seats` | Integer N | N seats; N-seat; seating for N; capacity N (persons/seats); N asientos; capacidad N | "no seating"/"no seats" → voids to absent (rare; restaurant with counter service only) | Exact integer compare. Range in documents → conflicts field, not operations (rule above). |
| 4 | `units` | Integer N | N units; N-unit building; N apartments; N rental units; N unidades; N apartamentos | "no units" → absent | Exact integer. Dwelling/rental units only — machine counts (washers, dryers) are NOT units. |
| 5 | `buildings` | Integer N (only when stated) | one building; two buildings; N buildings; N estructuras | — | Optional sub-detail of the units fact; compare only if gold states it. |
| 6 | `stories` | Integer N (only when stated) | one/two/three-story; N stories; two-floor building; de N pisos | — | Optional sub-detail; compare only if gold states it. |
| 7 | `cooking` | `none` \| `light` \| `full` | **full**: full kitchen; kitchen; cooking operations; grill; charbroiler; flat-top/griddle; range; burners; fryer(s); wok; oven(s) (deck, convection, pizza); comal; deep fryer; wood-fired; freidora; fritura; parrilla; plancha; horno. **light**: microwave only; cold prep; assembly only; warming only; no cooktop. **none**: no cooking; no kitchen; no cooking operations; sin cocina; no hay cocina | Negation flips: "no cooking operations (tenant electric ranges only)" → `none` (tenant ranges are not commercial cooking); "no kitchen" → `none` | A single cooking appliance stated → `full` unless the document explicitly limits to microwave/cold prep. |
| 8 | `fryer` | `yes` (+ optional count N) \| `no` | fryer(s); deep fryer; deep fat fryer; deep frying; freidora(s); fritura | "no fryers"; "no frying"; sin freidoras → `no` | Count ("2 fryers") compared only if gold states it; else presence alone. |
| 9 | `open_flame` | `yes` \| `no` | grill; charbroiler; wood-fired (oven/pit); open flame; flame cooking; torch-down/torch down roofing; llama abierta; parrilla | "no hot work"; "no open flame"; "no torch work"; sin llama abierta → `no` | Grills/charbroilers always co-trigger `cooking=full`; torch-down is hot work on contractor jobs, not cooking. |
| 10 | `hood` | `yes` \| `no` | Type I hood; exhaust hood; hood and suppression; hood with suppression; wet chemical; UL 300; extinguishing system; campana (de humos); sistema de supresión | "no hood"; "no suppression system"; sin campana → `no` | "Deck oven", "deck seating" do NOT trigger hood. Cleaning dates are not slots. |
| 11 | `entertainment` | `none` \| `live` | **live**: live music; band; DJ; dancing; dance floor; music on premises; musica en vivo; baile. **none**: no live music; no entertainment; sin musica | "no live music"; "no DJ" → `none` | Any live music/DJ/dancing is one value; days/hours ride in the same clause, not a separate value. |
| 12 | `hours` | Open: stated hours/days as a set of open times + days | open (from/to) X; closes X; X–X; open until midnight; weekends; Friday and Saturday nights; breakfast and lunch service; meal periods as stated; abierto de X a X | "closed Sundays"; "no night operations" → stated absence value | Compare hour set + meridiem + days (v9 hour reading). Meal periods alone ("breakfast and lunch") are hours only when the documents give them as operating periods. |
| 13 | `delivery` | `yes` \| `no` | delivery; delivery service; catering; entrega (a domicilio); domicilio; catering service | "no delivery"; "no delivery service"; sin entrega → `no` | Dine-in / takeout / counter service are NOT delivery. |
| 14 | `open_24h` | `yes` \| `no` | 24-hour; open 24 hours; 24/7; around the clock; las 24 horas; abierto las 24 | "not 24-hour"; "no 24-hour operations" → `no` | Separate from `hours` detail; set when the documents say continuous operation. |
| 15 | `floor` | Open: basement \| ground/first \| second \| Nth (as stated) | Nth floor; ground floor; first floor; second floor; basement; upstairs/downstairs; segundo piso; planta baja; primer piso; sótano | "not on the ground floor" → stated floor only | Location of the premises; "deck oven" is cooking, not a floor/outdoor fact. |
| 16 | `onsite_processing` | `yes` \| `no` | on-site processing; manufacturing on site; repackaging; food prep for resale; sorting on site; repair shop/repair work on premises; storage of flammables on premises; commercial pressing; empaque/reenvasado en el sitio; manufactura en el sitio | "no manufacturing"; "no repackaging"; "no hot work"; no processing; sin manufactura → `no` | Ordinary stock/inventory storage alone is not processing unless documents flag flammables or resale prep. |
| 17 | `outdoor` | `yes` \| `no` | outdoor seating/service; patio; outdoor dining; deck seating; sidewalk cafe; outside seating; terraza; patio (seating); comedor exterior | "no outdoor seating"; sin terraza → `no` | Customer outdoor service ONLY. Materials stored outside, seasonal tents, and "deck oven" do NOT set this slot. |
| 18 | `security` | `yes` \| `no` | security staff; security guard; bouncer; armed guard; doorman (as security); seguridad; guardia; custodio | "no security"; sin seguridad → `no` | — |
| 19 | `hazmat` | `yes` \| `no` | hazardous materials; hazmat; flammable liquids; aerosols; pesticides; explosives; fireworks; propane (bulk); chemicals (as stock); materiales peligrosos; líneas inflamables; explosivos; fuegos artificiales | "no hazardous materials"; "goods not hazardous"; "no flammable liquids"; sin materiales peligrosos → `no` | Fireworks stock = `yes`. A clause that lists the absence of named classes ("no flammable liquids, aerosols, pesticides, batteries") = `no`. |

### Slot coverage of the closed list

Every item of the "Other underwriting-relevant details" closed list maps to a slot: live music/entertainment/DJ/dancing → `entertainment`; deep frying → `fryer` (+ `cooking=full`); open flame → `open_flame` (+ `cooking=full` for restaurant equipment); delivery or catering → `delivery`; 24-hour → `open_24h`; floor/story/basement → `floor` (+ `stories`); on-site processing → `onsite_processing`; outdoor/patio → `outdoor`; security/bouncers → `security`; hazardous materials → `hazmat`. Required items map to slots 1–7 and 12 (`business_type`, `alcohol`, `seats`, `units`, `cooking`, `hours`). Nothing else is a slot.
