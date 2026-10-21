# Operations gold rule (small commercial) — D-094 item 2

Change 2026-10-21 (P-069, D-119, T-116): `business_type` is now a closed slot over the carrier-match.md class list; items that fit no slot move to an unscored notes line. See the last section.

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
| 1 | `business_type` | Closed list of 22 values (carrier-match.md); see section "business_type slot" below (P-069, D-119) | Synonyms per value: see that section | Negated class is not present | Gold writes `business_type=<value>`, one item per operation. Replaces the former open-valued row. |
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

## business_type slot, closed class list, and unscored notes (P-069 / D-119, 2026-10-21)

Author: @senior-underwriter. Replaces row 1 of the slot table (open-valued) and the free-text business items. Applies to NEW gold only (T-117 onward); published gold and scores are never rewritten. Source of the class list: `deliverables/head-of-underwriting/carrier-match.md` (R9-R14, R16, W1, W2). If that file changes a class, this list changes with it, in one commit.

### 1. business_type: allowed values (closed list, 22 values)
The value is the class the file would be routed on. Synonyms are the carrier-match.md words (English, plus its listed Spanish). Whole words and exact phrases only, no substrings (`bar` is not `barber`, `pub` is not `public`), case-insensitive.

**Allow-list classes (R14)**
| Value | Synonyms |
|---|---|
| `office` | office, offices, office building, office suite(s), office lessor, oficina(s) |
| `retail` | retail, retail store, dry retail, dry goods, storefront, clothing, clothing store, boutique, apparel, thrift shop/store, gift shop, comercio minorista, tienda minorista, tienda de ropa, ropa |
| `wholesale` | wholesale, light wholesale, wholesale distributor, mayoreo, mayorista |

**Referral classes (R10-R12, R16, W2)**
| Value | Synonyms |
|---|---|
| `restaurant` | restaurant(s), food service, foodservice, kitchen (as the business), eatery, cafe, café, cafeteria, catering (as the business), bakery, coffee shop, deli, restaurante(s), servicio de alimentos, comedor, banquetes. Never a cuisine word alone ("taqueria" alone is not a synonym; write the documents' class word) |
| `contractor` | contractor(s), roofing, roofer, handyman, painter, painting, carpenter, carpentry, flooring, drywall, plumbing, electrician, HVAC, glazier, glass contractor, mason, concrete/flatwork contractor, contratista, techado, techador, pintor, carpintero. A trade not listed is still `contractor` |
| `habitational` | habitational, apartment(s), apartment building, residential apartments, flats, multifamily, duplex, triplex, fourplex, habitacional, apartamento(s), multifamiliar |
| `hazardous_goods` | fertilizer, pesticide, herbicide, chemical(s), hazardous, flammable, solvent, propane, fuel (as the stock in trade; W2a) |
| `lab_medical` | laboratory, lab, medical, clinic, therapy, therapist, physician, doctor, dental, dentist, pediatric, chiropractic, hospital, médico, clínica (W2b) |
| `cold_storage` | cold storage, refrigerated, freezer(s), almacenamiento en frío (W2c) |
| `liquor_store` | liquor store, package store, liquor sales as the business, licor (W2d). "Restaurant with a liquor license" is `restaurant` + the `alcohol` slot, not `liquor_store` |
| `vacant` | vacant, vacancy, unoccupied, no utilities, utilities off, no tenants, empty building, abandoned, vacante, desocupado (W2e) |
| `other_listed` | gym(s), fitness, salon(s), spa(s), daycare, day care, school(s), church(es), hotel(s), motel(s), theater/theatre, auto repair, car wash, gas station, manufacturing, factory (R16 OTHER list) |

**Prohibited classes (W1)**
| Value | Synonyms |
|---|---|
| `bar_pub` | bar, bars, tavern(s), pub(s), cantina, taberna |
| `lounge_nightclub` | nightclub(s), lounge(s), antro, discoteca |
| `hookah_adult` | hookah, adult entertainment |
| `cannabis` | cannabis, marijuana, marihuana, dispensary, dispensario |
| `fireworks_explosives` | fireworks, firework, explosives, explosive, ammunition, fuegos artificiales, explosivos |
| `armed_security` | armed security, armed guard, seguridad armada, guardia armado |
| `bail_bonds` | bail bonds |
| `student_subsidized_housing` | student housing, subsidized housing, alojamiento estudiantil, vivienda subsidiada |
| `sawmill_pallet_plastics_recycling` | sawmill(s), pallet manufacturing, plastics manufacturing, recycling |

**Not on any list**: `other_class` (carrier-match R8, "readable class on no carrier list"). Use it only when the documents state a business that fits no row above; never as a dump for an unclear card.

Precedence when one phrase fits two rows: the more restrictive row wins in the order W1, W2, referral, allow-list (the order carrier-match.md checks). "Restaurant and bar" is two values, not one (see 2).

### 2. Gold syntax for business_type, including two operations (R16 style)
- One value per item, written `business_type=<value>`, value copied exactly from the list above (lowercase, underscores).
- **Two or more operations: one item per operation, in any order.** "Office with a pub" is `business_type=office; business_type=bar_pub`. "Retail and office" is `business_type=retail; business_type=office`. "Restaurant and bar" is `business_type=restaurant; business_type=bar_pub`.
- **Bar word about the premises (H1, T-116, 2026-10-21):** a bar, tavern or pub word the documents state about the premises ("full bar", "full liquor bar", "bar service") is `business_type=bar_pub` beside the other class (restaurant plus full bar is `business_type=restaurant; business_type=bar_pub`; nightclub plus full liquor bar is `business_type=lounge_nightclub; business_type=bar_pub`). The alcohol item is then written without a class word ("full liquor"). Never reword gold to dodge the word reader. "No bar" and "not a bar" are negated and add nothing.
- A card carries a business_type item for every class the documents state, and for no class they do not state. Never infer a second operation.
- **Scoring (set equality, for the scorer):** the answer's set of classes must equal the gold set. A missing class is a miss; an extra class the gold does not hold is a miss (an invented second operation changes the route). Order never matters.
- The answer is read with the synonym lists above: a class is present when one of its synonyms appears in a clause with no negation word before it (shared negation rules of the slot table). The most restrictive reading wins when a phrase fits two rows.

### 3. Every other slot stays; how items map
All slots 2-19 of the table stay as written (alcohol, seats, units, buildings, stories, cooking, fryer, open_flame, hood, entertainment, hours, delivery, open_24h, floor, onsite_processing, outdoor, security, hazmat). Row 1 `business_type` is now the closed list above, not open-valued. `buildings` and `stories` stay as optional sub-details.

Item kinds seen in T-114 / T-115 and where each goes:
| Item kind (examples) | Goes to |
|---|---|
| business class phrases: `office building lessor`, `leases office suites`, `wholesale distributor`, `concrete flatwork contractor`, `refrigerated cold storage warehouse`, `retail strip center`, `lounge`, `bar` | `business_type=` (office, office, wholesale, contractor, cold_storage, retail, lounge_nightclub, bar_pub) |
| `100% vacant` | `business_type=vacant` (W2e is a routing class) |
| `patios`, `deck seating` | `outdoor` slot (unchanged) |
| `no food service`, `no cooking`, `cold prep; assembly only` | `cooking` slot. A card holds ONE cooking value; if the documents say both "cold prep" and "no cooking", gold picks the value that holds for the premises and the other phrase goes to notes (SUB-215 ambiguity, T-115 G class) |
| `22 suites`, `6 units` of a retail/office building | `units` only for dwelling or rental units as the slot says; suite counts of a commercial building are an unscored note |
| `closes 11 p.m.`, `open until 2 a.m.` | `hours` slot (unchanged, v9 hour reading) |
| trade exclusions: `no roofing`, `no residential work` | unscored note |
| merchandise or work lists: `craft supplies`, `driveways`, `sidewalks`, menu items | unscored note |
| owner/tenant role words: `building owner only`, `lessor only` | unscored note (the class is already `business_type=office`) |
| anything else that is not on the required or closed list | unscored note, or not written |

Rule: an operations item that matters to rating or routing must be a slot value. An item that fits no slot is NOT written in `Operations items:`; it goes to the notes line.

### 4. Gold card syntax (machine-parseable; the scorer reads exactly this)
```
- Operations: <one readable line, for the reader, unscored>
- Operations items: business_type=<value>; business_type=<value>; <slot item>; <slot item>
- Operations notes (unscored): <free text>; <free text>
```
Parsing contract:
1. `Operations items:` is split on `;`. Trim spaces. Each part is one item.
2. An item that starts with `business_type=` is parsed exactly: the text after `=` must be one value of the list in 1; anything else is a lint error (stops the run), not a free-text item.
3. Every other item is a T-114 slot item written in the documents' words, parsed by the slot vocabulary (unchanged from T-114). An item that matches no slot and does not start with `business_type=` is a lint error ("move to notes").
4. `Operations notes (unscored):` is split on `;`; it is never scored, never compared. The scorer ignores the line; the lint only checks it is not empty when present.
5. No operations stated: `- Operations: not in documents`; no items line, no notes line (unchanged).
6. If the card has an items line but no `business_type=` item, the lint warns (a stated business always has a class). Exception: `not in documents`.
7. An item never holds `;`. A note may hold commas, colons and periods.

Example, one operation: `- Operations items: business_type=restaurant; beer and wine only; 48 seats; Type I hood; closes 11 p.m.` and `- Operations notes (unscored): tamales and menudo; family owned.`
Example, two operations (R16): `- Operations items: business_type=office; business_type=bar_pub; Friday and Saturday nights` with `- Operations notes (unscored): pub is a tenant on the ground floor.`

### 5. Near-miss negatives the scorer must catch for business_type
Each pair: gold, then the answer that must be a miss.
1. Gold `restaurant`; answer "bar" or "restaurant and bar" (adds `bar_pub`; restaurant is a referral, bar is prohibited).
2. Gold `bar_pub`; answer "full-service restaurant" (a prohibited class downgraded to a referral class).
3. Gold `office`; answer "office with pub" (extra `bar_pub`; allow-list becomes prohibited).
4. Gold `office` + `bar_pub` (R16); answer "office" alone (second operation dropped).
5. Gold `retail`; answer "cocktail lounge" or "retail and lounge" (`lounge_nightclub` is prohibited).
6. Gold `habitational` (apartments); answer "vacant building" or "apartments, vacant" (`vacant` is W2e; gold has no vacancy).
7. Gold `vacant`; answer "apartment building" (occupied habitational vs vacant).
8. Gold `wholesale`; answer "retail store" (both allow-list but different groups; wholesale never routes directly, R17).
9. Gold `wholesale`; answer "wholesale of fertilizer and pesticides" (adds `hazardous_goods`).
10. Gold `cold_storage`; answer "warehouse" or "wholesale distributor" (the W2c fact is dropped).
11. Gold `contractor`; answer "roofing and sheet metal manufacturing" (adds `other_listed`) or "building owner" (`office`).
12. Gold `lab_medical` (physical therapy clinic); answer "office" (the W2b referral is read as allow-list).
13. Gold `cannabis`; answer "retail" or "smoke shop" (prohibited class dropped).
14. Gold `restaurant`; answer "no restaurant" or "not a bar, restaurant" read as no `restaurant`. A negated class never counts as present, and a negated class never masks another ("not a bar" must not erase a stated `restaurant`).
15. Substring traps that must NOT trigger: "barber" (not `bar_pub`), "public" (not `bar_pub`), "post office box" read as office is allowed only if the documents state an office; "lounge chairs sold" in a retail furniture store is `retail`, not `lounge_nightclub` (the scorer cannot tell; this case is a known ceiling: report it as a manual-review miss, do not silently pass).

Known ceiling for the scorer: synonym matching reads words, not meaning. Case 15 and "fuel" (heating-oil delivery vs gas station) are the two phrases a word list cannot separate. The scorer must fail closed (miss), never credit.
