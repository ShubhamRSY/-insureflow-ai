# T-116 — scorer v11 (P-069): business_type operations slot

- Task: T-116. Decision: D-119 (item 1). Proposal: P-069, approved by the user on 2026-10-21 ("approve change P-069"). Author: @ai-engineer-assistant. Date: 2026-10-21.
- Spec implemented, not reinterpreted: `deliverables/senior-underwriter/operations-gold-rule.md`, last section ("business_type slot, closed class list, and unscored notes"); classes from `deliverables/head-of-underwriting/carrier-match.md`.
- Not a production approval. @model-risk check (High only) is still to do; nothing is frozen yet.

## Files

| File | State | sha256 |
|---|---|---|
| `underwriting_pipeline/ai/eval_holdout_v11.py` | new | `7ddcfb50521b7af17f00c0e148891ca40008d019ce257b9b5d121c7fa6d3fcbb` |
| `underwriting_pipeline/ai/eval_holdout_v10.py` | unchanged (checked before and after the validation runs) | `ffd1afdda55fd761f21deb2f6ede49b9294d7517bed6500ccd9520eba361302b` |
| `deliverables/senior-test-engineer/lint_holdout.py` | default scorer now v11, v10 selectable with `--scorer eval_holdout_v10` | `01147a7532bdd7f1ec00861200d1d5e6bbf87f12612389416ff58b78844ea653` (orchestrator fix: WARNS cleared per run, code-review finding; before that a14f1345…fdb; previous: `d21b92cb...936a`) |
| `deliverables/ai-engineer/evals/P-069-dev/` | new: migrated dev gold, mapping, score files, lint output, `migrate_gold.py` | |

No prompt, `llm_extract.py`, `prepare.py` or other scorer was touched. `gold-set/` and `gold-set-T-108-corrected/` are untouched.

## What v11 is (v10 plus operations only)

1. **business_type slot.** Gold item `business_type=<value>`, 22 values (21 classes + `other_class`) in `BT_SYNONYMS`, synonyms copied from the rule file. The answer's class set is read with whole-word / exact-phrase matches (no substrings), case-insensitive, clause by clause (clauses split on `, ; . : ( )` and newline). A negation word earlier in the clause removes the class; a negated class never masks another ("not a bar, restaurant" keeps restaurant). A phrase that fits two classes takes the more restrictive (W1, W2, referral, allow-list). **Set equality**: a missing class or an extra class is a miss; order never matters (two-operation files). No listed class in a non-empty answer reads as `other_class` (carrier-match R8); an empty answer or "not in documents" reads as nothing, so it never hits. An explicit `business_type=<value>` in the answer is read as that value (that is how the lint's perfect answer carries the gold).
2. **Unscored notes.** `- Operations notes (unscored):` is never read by any scoring code. The gold check only errors when the line is present and empty.
3. **Gold check (stops the run before any call).** Every scored item must be `business_type=<one of the 22>` or must name a T-114 slot; otherwise the error says "fits no slot (move to notes ...)". The v10 free-text fallback for non-slot items is removed; `ops_items_hit` also fails closed (miss) on such an item. An items line with no `business_type=` is a warning. New switches: `--check-gold` now includes this check; `--check-ops-gold` checks the items lines only (needed because SUB-127–173 gold has no Scope or valued-as-of lines).
4. **Everything else is v10.** Slots 2-19, negation, hours, counts, Scope, loss-run date, conflict, status, route, gates and score files. Non-operations marks on the T-108 re-score: 0 differences from v10 (all 11 other fields, all 20 in-scope files).
5. **Self-check** (`--self-check`, prints `eval_holdout_v11 self-check ok`): the v10 checks (items rewritten to `business_type=` form where they used free text) plus `_v11_self_check`: true positives (one and two operations, Spanish, other_class), all 15 near-miss groups of rule section 5, the substring traps, the gold-check cases, parsing of the notes line.

## Lint (`lint_holdout.py`, default v11)

- Perfect answers are the gold `Operations items` line itself; they must score no miss. Wrong answers: the existing per-field set, the P-068 near-miss list (kept), and now `NEARMISS_BT`: every near-miss negative of rule section 5 (about 23 cases incl. the explicit wrong token and "drop one of two operations"), applied two ways: (a) on every card whose gold class set is exactly that set, the perfect answer with only the class swapped; (b) once per run on a synthetic card, so each case is tested whatever the set holds. `BT_TRUE` true positives must hit; every one of the 22 values must be read from its explicit token and from its first synonym; a gold item that fits no slot must be refused. Any failure blocks the freeze.
- Self-check `SELF-CHECK PASS`. It adds three v11 cases: a two-operation card with a notes line scores clean; a non-slot item and an unlisted value are gold errors; a blind scorer and a scorer that reads no class are both caught (27 and 49 findings).
- **Lint on the T-108 dev gold copy (v11): PASS**, 0 failures, 7 info (declared-undated loss runs), 32 files, run date 2026-10-19. Output: `deliverables/ai-engineer/evals/P-069-dev/lint-T-108-v11.txt`. (A first run failed on SUB-211 and SUB-222: see "Findings" item 2.)

## Validation (D-069: temp cache copy, no real log or outbox touched)

- Gold check SUB-127–173 (migrated copy), `--check-ops-gold`: 47 of 47 ok, 0 fail (`gold-check-SUB-127-173.txt`). The full `--check-gold` cannot run on that range (the older gold has no `Scope` or valued-as-of lines, unrelated to this change).
- Gold check T-108 migrated copy, `--check-gold`: 32 ok, 0 fail (`gold-check-T-108.txt`).
- Dev re-score of T-108 (SUB-206–237), `HOLDOUT_RESCORE=1`, `LLM_CACHE_DIR` = temp copy of `underwriting_pipeline/cache/T-108-live`, `LLM_PACE_SECONDS=0`, outputs in `P-069-dev/`. **0 model calls**: every file reports "from cache: saved reply used, no call in this run"; the temp token log gained 20 rows, all `cache_hit`; the real cache log is unchanged; `git status` shows only the intended files.
- Baseline for v10 is v10 run today on `gold-set-T-108-corrected` (same cache): `SUB-206-237-holdout-v10-on-corrected-gold-cache-rescore.*`. (The older `P-068-dev` file shows operations 19/20 because it was scored before the items lines existed; it is not the baseline.)

| Field (20 in-scope files) | v10 hit | v11 hit |
|---|---|---|
| named_insured, premises, effective_date, sales, construction, year_built | 20 | 20 |
| operations | 12 | **15** |
| tiv | 19 | 19 |
| loss_runs | 17 (3 not credited) | 17 (3 not credited) |
| conflict / status | 15 / 15 | 15 / 15 |
| route | 18 | 18 |

Route gate, scope gate, false completes: unchanged (0 unsafe, 0 false completes).

Per file, operations only (re-run 2026-10-21 against the updated dev gold; SUB-211 and SUB-222 gold changed by @senior-underwriter, scorer, lint and cache unchanged): v10 miss to v11 hit: 206, 209, 211, 215, 218, 221, 225. v10 hit to v11 miss: 207, 213, 216, 219. Miss both: 208. Net 12 to 15 (before the gold change: 13, with 211 and 222 also missing). The 5 v11 misses are correct answers that also mention another class in passing, not real class disagreements; the word-list reader counts the passing mention as an extra class.

## Why the 5 v11 misses miss (correct answers that mention another class in passing; the word-list ceiling the rule file names, none is a bug)

The first run (before the gold change) also missed SUB-211 and SUB-222 for the word "bar" in "full bar" / "full liquor bar"; both now hit.

| File | Answer set vs gold set | Cause |
|---|---|---|
| 208 | wholesale + office + retail vs wholesale | "small office"; "sells to retail shops" |
| 216 | wholesale + office + restaurant vs wholesale | "small office"; customers "restaurants and offices" |
| 213 | office + lab_medical vs office | tenants "(insurance, accounting, therapy)" |
| 219 | hazardous_goods + other_listed + office vs hazardous_goods + other_listed | "Small office" |
| 207 | restaurant + retail vs restaurant, and cooking light vs none | "Retail seating for 24"; the answer holds both "cold prep" (light) and "No cooking" (none), the v10 reader keeps light |

## Mapping of the dev gold (66 cards migrated; 1 card and 12 out-of-scope cards copied unchanged)

Folders: `P-069-dev/gold-SUB-127-173/` (SUB-168 "not in documents" copied unchanged) and `P-069-dev/gold-T-108/` (SUB-226–237 out of scope, byte copies). Generated by `P-069-dev/migrate_gold.py` from the hand-written table inside it. SUB-127–173 had only the one-line `Operations:`; those items were decomposed from it. T-108 items came from the existing items lines.

Decision rules used (rule file section 3 unless stated):

| Decision | Applied to |
|---|---|
| A business class phrase becomes `business_type=` with the rule's synonym row | every card |
| A stated second class gets its own item ("every class the documents state") | fertilizer / fireworks stock = `hazardous_goods` / `fireworks_explosives` next to the retail or wholesale class (138, 165); paint blending = `hazardous_goods` + `other_listed` (219); deli + small grocery section = `restaurant` + `retail` (215); restaurant and bar (141, 146, 157, 171, 225) |
| `100% vacant` is `business_type=vacant`; the suite count of a commercial building is a note | 221 |
| Merchandise lists, work lists, trade exclusions, owner / tenant role words, service style, location and building counts, lease terms, occupancy, dates go to notes | all |
| Items the slot reader has no trigger for go to notes, even though the slot table lists them: `no bar`, `no hot work`, `ansul`, buildings / stories, meal periods, `until midnight`, `Friday and Saturday`, `no tenant cooking`, `no processing`, `no repair`, `2nd floor` is written `second floor` | e.g. 136, 151, 157, 158, 211, 213, 218 |
| One cooking value per card; documents saying both "cold prep" and "no cooking" hold `no cooking` (none), the other phrase goes to notes | 207, 215 (rule: SUB-215 ambiguity) |
| Two locations with two seat counts: seat counts go to notes (one integer slot) | not in the scored set (232 is out of scope) |
| `full bar` / `full liquor bar` written as the alcohol item `full liquor`, so the perfect answer does not carry the word bar (which reads as `bar_pub`); the documents' words are kept in a note | 211, 222 |
| Judgement calls on class | glass cutting / tempering = `contractor` (134); laundromat = `other_class` (169); "taqueria" = `restaurant` (173); a taqueria / deli class word not stated in the documents is still the class (207, 236 not scored); vet clinic not in the scored set |
| Hours | `closes 11 p.m.`, `open until 2:00 a.m.` kept as items (v9 hour reading); `monitored 24/7` (218) is not `open_24h`, so it is a note |

Full per-card table (old gold to new items and notes):

| Card | Old (gold today) | New Operations items | New Operations notes (unscored) |
|---|---|---|---|
| SUB-127 | ops: Financial advisory and tax office, 2nd floor | business_type=office; second floor | financial advisory and tax; 4-story building, insured on 2nd floor |
| SUB-128 | ops: Dry retail gift shop: candles, home goods, greeting cards, gift wrap | business_type=retail | gift shop: candles, home goods, greeting cards, gift wrap |
| SUB-129 | ops: Light wholesale of electrical supplies (wire, breakers, conduit, fixtures) | business_type=wholesale | electrical supplies: wire, breakers, conduit, fixtures |
| SUB-130 | ops: Breakfast and lunch cafe, 64 seats, beer and wine only | business_type=restaurant; 64 seats; beer and wine only | breakfast and lunch |
| SUB-131 | ops: Commercial plumbing service and repair, water heater installs, small remodel work | business_type=contractor | water heater installs; small remodel work |
| SUB-132 | ops: Southern breakfast and lunch restaurant, 90 seats, beer and wine only | business_type=restaurant; 90 seats; beer and wine only | Southern; breakfast and lunch |
| SUB-133 | ops: Residential apartments, 12 units in one two-story building, long-term leases | business_type=habitational; 12 units | one two-story building; long-term leases |
| SUB-134 | ops: Glass cutting, tempering and framing for commercial storefronts | business_type=contractor | glass cutting, tempering and framing for commercial storefronts |
| SUB-135 | ops: Used book and thrift shop, donated goods sorted on site | business_type=retail; sorting on site | used book and thrift shop; donated goods |
| SUB-136 | ops: Mexican restaurant, 70 seats, beer and wine only, no bar | business_type=restaurant; 70 seats; beer and wine only | Mexican; no bar |
| SUB-137 | ops: HVAC installation and service contractor | business_type=contractor | HVAC installation and service |
| SUB-138 | ops: Wholesale and retail of animal feed, seed and fertilizer bags | business_type=wholesale; business_type=retail; business_type=hazardous_goods | animal feed, seed and fertilizer bags |
| SUB-139 | ops: Residential apartments, 6 units in two two-story buildings, long-term leases | business_type=habitational; 6 units | two two-story buildings; long-term leases |
| SUB-140 | ops: Barbecue restaurants, two locations, dine-in and takeout | business_type=restaurant | barbecue; two locations; dine-in and takeout |
| SUB-141 | ops: Full-service restaurant and bar, 180 seats, full liquor license, live music Friday and Saturday | business_type=restaurant; business_type=bar_pub; 180 seats; full liquor license; live music | music Friday and Saturday |
| SUB-142 | ops: Roofing contractor | business_type=contractor |  |
| SUB-143 | ops: Clothing boutique retail store | business_type=retail |  |
| SUB-144 | ops: outpatient pediatric physical and speech therapy | business_type=lab_medical | outpatient physical and speech therapy |
| SUB-145 | ops: Residential apartments, 40 units in three two-story buildings, long-term leases | business_type=habitational; 40 units | three two-story buildings; long-term leases |
| SUB-146 | ops: Full-service restaurant and bar, 180 seats, full liquor license, live music Friday and Saturday | business_type=restaurant; business_type=bar_pub; 180 seats; full liquor license; live music | music Friday and Saturday |
| SUB-147 | ops: CPA tax preparation and bookkeeping office | business_type=office | CPA tax preparation and bookkeeping |
| SUB-148 | ops: full-service restaurant, 140 seats, beer and wine only, Type I hood with UL 300 wet chemical, hood and duct cleaned quarterly, last 2026-08-20 | business_type=restaurant; 140 seats; beer and wine only; Type I hood; UL 300 | wet chemical; hood and duct cleaned quarterly, last 2026-08-20 |
| SUB-149 | ops: 12-unit apartment building, long-term leases, 92 percent occupied | business_type=habitational; 12 units | long-term leases; 92 percent occupied |
| SUB-150 | ops: light wholesale of hardware and janitorial supplies to contractors, trade counter, no manufacturing or repackaging | business_type=wholesale; no manufacturing; no repackaging | hardware and janitorial supplies to contractors; trade counter |
| SUB-151 | ops: interior drywall hanging and finishing, trim carpentry, acoustic ceilings, commercial and residential remodel; office and tool shop, no hot work on premises | business_type=contractor | drywall, trim carpentry, acoustic ceilings; commercial and residential remodel; office and tool shop; no hot work on premises |
| SUB-152 | ops: retail outdoor gear and apparel, sales floor and one storage room, no firearms or ammunition | business_type=retail | outdoor gear and apparel; sales floor and one storage room; no firearms or ammunition |
| SUB-153 | ops: Dry retail stationery and office supplies with light wholesale and admin office | business_type=retail; business_type=wholesale | stationery and office supplies; admin office |
| SUB-154 | ops: Office, 2nd floor, clients by appointment, no inventory, no goods held for sale | business_type=office; second floor | clients by appointment; no inventory, no goods held for sale |
| SUB-155 | ops: Dry retail storefront, ground floor, clothing and dry goods, no food, no alcohol, no repackaging | business_type=retail; ground floor; no alcohol; no repackaging | clothing and dry goods; no food |
| SUB-156 | ops: Restaurant, no alcohol of any kind, 48 seats, flat-top, 2 fryers and 4-burner range under Type I hood with UL 300 suppression, breakfast and lunch counter service, dine-in and takeout | business_type=restaurant; no alcohol; 48 seats; flat-top; 2 fryers; 4-burner range; Type I hood; UL 300 | breakfast and lunch counter service; dine-in and takeout |
| SUB-157 | ops: Restaurant and bar, full liquor (TABC mixed beverage permit), 140 seats, charbroiler, 2 fryers, flat-top, 8-burner range and pizza oven under Type I hood with UL 300, live music Thursday to Sunda | business_type=restaurant; business_type=bar_pub; full liquor license; 140 seats; charbroiler; 2 fryers; flat-top; 8-burner range; pizza oven; live music; Type I hood; UL 300 | TABC mixed beverage permit; live music Thursday to Sunday until midnight; dinner service and weekend brunch |
| SUB-158 | ops: Apartment building, 16 units in two two-story buildings, long-term leases, no cooking operations (tenant electric ranges only) | business_type=habitational; 16 units; no cooking operations | two two-story buildings; long-term leases; tenant electric ranges only |
| SUB-159 | ops: Bakery and cafe (pastries, sandwiches, coffee), no alcohol sold, 30 seats, deck oven, 2 convection ovens, 4-burner range and flat-top under Type I hood with UL 300, dine-in and takeout | business_type=restaurant; no alcohol; 30 seats; deck oven; 4-burner range; flat-top; Type I hood; UL 300 | pastries, sandwiches, coffee; 2 convection ovens; dine-in and takeout |
| SUB-160 | ops: Apartment building, 8 units in two two-story buildings, long-term leases, no cooking operations (tenant electric ranges only) | business_type=habitational; 8 units; no cooking operations | two two-story buildings; long-term leases; tenant electric ranges only |
| SUB-161 | ops: Light wholesale of home goods, kitchenware and small hand tools to retail stores, goods not hazardous (no flammable liquids, aerosols, pesticides, batteries), warehouse with loading dock, no repa | business_type=wholesale; no flammable liquids; no repackaging | home goods, kitchenware, small hand tools to retail stores; no aerosols, pesticides, batteries; warehouse with loading dock |
| SUB-162 | ops: Office suite, clients by appointment, no inventory | business_type=office | clients by appointment; no inventory |
| SUB-163 | ops: Mexican restaurant, beer and wine only, no bar, 60 seats, comal, grill, 2 fryers and 6-burner range under Type I hood with UL 300, table service and takeout | business_type=restaurant; beer and wine only; 60 seats; comal; grill; 2 fryers; 6-burner range; Type I hood; UL 300 | Mexican; no bar; table service and takeout |
| SUB-164 | ops: Roofing contractor, residential and commercial re-roofing and repair, shop and yard on premises, materials stored outside under tarps, torch-down work on some jobs | business_type=contractor; torch-down | residential and commercial re-roofing and repair; shop and yard on premises; materials stored outside under tarps |
| SUB-165 | ops: Retail sale of consumer fireworks (aerial, ground and cakes), storefront and seasonal tent (June and July), fireworks inventory stored on premises including in a trailer on the lot | business_type=retail; business_type=fireworks_explosives; fireworks | aerial, ground and cakes; seasonal tent June and July; inventory stored on premises including a trailer on the lot |
| SUB-166 | ops: Owner-occupied two-story office building, insured occupies first floor, two tenants on second floor, office use only, no retail, no food | business_type=office | two-story, owner-occupied; insured on first floor, two tenants on second floor; no retail, no food |
| SUB-167 | ops: Apartment building, 24 units in three two-story buildings, long-term leases, no cooking operations (tenant electric ranges only) | business_type=habitational; 24 units; no cooking operations | three two-story buildings; long-term leases; tenant electric ranges only |
| SUB-168 | (copied unchanged: not in documents or out of scope) | | |
| SUB-169 | ops: Self-service laundromat, 14 washers and 8 gas dryers, customers wash their own clothes, no commercial pressing, no delivery service | business_type=other_class; no commercial pressing; no delivery service | self-service laundromat; 14 washers and 8 gas dryers; customers wash their own clothes |
| SUB-170 | ops: Restaurant, 2 locations, burgers, chicken and breakfast, beer and wine only (no liquor license), flat-top, 2 fryers, charbroiler and 8-burner range under Type I hood with UL 300 at both locations | business_type=restaurant; beer and wine only; flat-top; 2 fryers; charbroiler; 8-burner range; Type I hood; UL 300 | burgers, chicken and breakfast; 2 locations; no liquor license; dine-in and takeout |
| SUB-171 | ops: Restaurant and bar, full liquor (TABC mixed beverage permit), 140 seats, charbroiler, 2 fryers, flat-top, 8-burner range and pizza oven under Type I hood with UL 300, live music Thursday to Sunda | business_type=restaurant; business_type=bar_pub; full liquor license; 140 seats; charbroiler; 2 fryers; flat-top; 8-burner range; pizza oven; live music; Type I hood; UL 300 | TABC mixed beverage permit; live music Thursday to Sunday until midnight; dinner service and weekend brunch |
| SUB-172 | ops: Apartment buildings, 3 properties, 30 units total, long-term leases, no cooking operations (tenant electric ranges only) | business_type=habitational; 30 units; no cooking operations | 3 properties; long-term leases; tenant electric ranges only |
| SUB-173 | ops: Counter service taqueria (tacos, burritos, quesadillas, agua fresca), no liquor, 35 seats, dine-in and takeout | business_type=restaurant; no liquor; 35 seats | counter service taqueria: tacos, burritos, quesadillas, agua fresca; dine-in and takeout |
| SUB-206 | items: office building lessor; leases office suites | business_type=office | leases office suites; lessor only |
| SUB-207 | items: deli; sub shop; counter service; cold prep; assembly only; no cooking; no fryer; no hood; 24 seats | business_type=restaurant; no cooking; no fryer; no hood; 24 seats | deli and sub shop; counter service; cold prep and assembly only (documents say both this and no cooking; gold holds cooking=none) |
| SUB-208 | items: wholesale distributor; craft supplies; hobby supplies; small-package novelties; sells to retail shops only; warehouse shelving; small office; no manufacturing; no retail walk-in | business_type=wholesale; no manufacturing | craft and hobby supplies, small-package novelties; sells to retail shops only; warehouse shelving, small office; no retail walk-in |
| SUB-209 | items: concrete flatwork contractor; driveways; patios; sidewalks; small commercial slabs; 12 employees; 25% subcontracted; no roofing; no demolition; no structural | business_type=contractor | concrete flatwork: driveways, patios, sidewalks, small commercial slabs; 12 employees; 25% subcontracted; no roofing, no demolition, no structural |
| SUB-210 | items: residential apartments; 14 units; 2 two-story garden buildings; long-term leases; on-site part-time manager; no short-term rentals | business_type=habitational; 14 units | 2 two-story garden buildings; long-term leases; on-site part-time manager; no short-term rentals |
| SUB-211 | items: full-service restaurant; mesquite grill; offset smoker; Type I hood; ansul system; 96 seats; full bar; beer wine liquor; closes 11 p.m.; no dancing; no late-night entertainment | business_type=restaurant; grill; Type I hood; 96 seats; full liquor; closes 11 p.m.; no dancing | offset smoker; ansul system; documents say full bar (beer, wine, liquor); gold item is full liquor so the word bar does not read as bar_pub; no late-night entertainment |
| SUB-212 | items: interior finish carpentry; cabinet installation; residential; light commercial; 6 employees; 3 crews; no roofing; no structural; no demolition; no exterior work above 2 stories | business_type=contractor | interior finish carpentry and cabinet installation; residential and light commercial; 6 employees in 3 crews; no roofing, no structural, no demolition, no exterior work above 2 stories |
| SUB-213 | items: office building lessor; single-story office building; 9 suites; professional tenants; no tenant cooking; no retail | business_type=office | single-story building; 9 suites leased to small professional tenants; lessor only; no tenant cooking, no retail |
| SUB-214 | items: retail store; outdoor gear; apparel; footwear; no repair; no fuel; no firearms; no rentals | business_type=retail | outdoor gear, apparel, footwear; no repair, no fuel, no firearms, no rentals |
| SUB-215 | items: deli; sandwich shop; grocery; market section; canned goods; dry goods; no meat counter; cold prep; assembly only; no cooking; no fryer; no hood; 6 tables | business_type=restaurant; business_type=retail; no cooking; no fryer; no hood | deli and sandwich shop with a small grocery/market section; canned and dry goods, no meat counter; cold prep and assembly only (documents say both this and no cooking; gold holds cooking=none); 6 tables |
| SUB-216 | items: wholesale distributor; paper and packaging supplies; restaurants; offices; warehouse racking; small office; no manufacturing | business_type=wholesale; no manufacturing | paper and packaging supplies to restaurants and offices; warehouse racking, small office |
| SUB-217 | items: residential apartments; 10 units; 2 two-story wood frame buildings; long-term leases; on-site manager unit; no short-term rentals; tenant electric ranges only | business_type=habitational; 10 units | 2 two-story wood frame buildings; long-term leases; on-site manager unit; no short-term rentals; tenant electric ranges only |
| SUB-218 | items: refrigerated cold storage warehouse; frozen and chilled goods; food distributors; ammonia refrigeration plant; 2 compressors; monitored 24/7; storage only; no processing; no packaging | business_type=cold_storage | frozen and chilled goods for food distributors; ammonia refrigeration plant, 2 compressors; monitored 24/7; storage only, no processing, no packaging |
| SUB-219 | items: light manufacturing; blending and packaging; industrial paints; solvent-based coatings; small batch; no bulk storage above ground; flammable liquids in a rated cabinet; max 55 gal per batch; sm | business_type=hazardous_goods; business_type=other_listed; flammable liquids | blending and packaging of industrial paints and solvent-based coatings, small batch; no bulk storage above ground; rated cabinet, max 55 gal per batch; small office |
| SUB-220 | items: fast-casual Chinese restaurant; wok line; Type I hood; ansul; takeout; 18 seats; no bar; no alcohol | business_type=restaurant; wok; Type I hood; 18 seats; no alcohol | fast-casual Chinese; ansul; takeout; no bar |
| SUB-221 | items: retail strip center; 6 units; 100% vacant; building owner; no contents; no business income; owner marketing the space; no cooking | business_type=retail; business_type=vacant; no cooking | strip center, 6 units; last tenant vacated June 2026; building owner; no contents, no business income; owner marketing the space |
| SUB-222 | items: nightclub; open until 2:00 a.m.; full liquor bar; dance floor; DJ booth; bottle service; cover charge; capacity 350; 21+; no cooking; bar snacks only | business_type=lounge_nightclub; open until 2:00 a.m.; full liquor; dance floor; DJ; capacity 350; no cooking | bottle service; cover charge; 21+ only; bar snacks only; documents say full liquor bar; gold item is full liquor so the word bar does not read as bar_pub |
| SUB-223 | items: residential apartments; 12 units; single two-story wood frame building; long-term leases; on-site manager unit; no short-term rentals; no commercial tenants; tenant electric ranges only | business_type=habitational; 12 units | single two-story wood frame building; long-term leases; on-site manager unit; no short-term rentals, no commercial tenants; tenant electric ranges only |
| SUB-224 | items: residential apartments; 10 units; 2 two-story wood frame buildings; long-term leases; on-site manager unit; no short-term rentals; tenant electric ranges only | business_type=habitational; 10 units | 2 two-story wood frame buildings; long-term leases; on-site manager unit; no short-term rentals; tenant electric ranges only |
| SUB-225 | items: lounge; bar; full liquor license; open until 2:00 a.m.; DJ; small dance floor on weekends; 21+; no food service; bar snacks only; no cooking | business_type=lounge_nightclub; business_type=bar_pub; full liquor license; open until 2:00 a.m.; DJ; dance floor; no cooking | small dance floor on weekends; 21+; no food service beyond bar snacks |
| SUB-226 | (copied unchanged: not in documents or out of scope) | | |
| SUB-227 | (copied unchanged: not in documents or out of scope) | | |
| SUB-228 | (copied unchanged: not in documents or out of scope) | | |
| SUB-229 | (copied unchanged: not in documents or out of scope) | | |
| SUB-230 | (copied unchanged: not in documents or out of scope) | | |
| SUB-231 | (copied unchanged: not in documents or out of scope) | | |
| SUB-232 | (copied unchanged: not in documents or out of scope) | | |
| SUB-233 | (copied unchanged: not in documents or out of scope) | | |
| SUB-234 | (copied unchanged: not in documents or out of scope) | | |
| SUB-235 | (copied unchanged: not in documents or out of scope) | | |
| SUB-236 | (copied unchanged: not in documents or out of scope) | | |
| SUB-237 | (copied unchanged: not in documents or out of scope) | | |

## Findings and known limits (for @senior-underwriter, @head-of-underwriting, @model-risk)

1. **Words, not meaning (the rule file's case 15 ceiling) is wider than two phrases.** Any class word anywhere in the answer counts: "small office" (4 of the 5 misses), customer words ("sells to retail shops", "to restaurants and offices"), tenants ("therapy"), and the alcohol word "bar" ("full bar", "full liquor bar"). Fail closed, as the rule demands, so these score as misses. Options, each needing a rule decision and a new proposal: mask alcohol-service phrases (`full bar`, `bar service`, `bar snacks`) and ancillary phrases (`small office`) before the class read; or accept the lower operations hit rate. I did not tune the scorer to the T-108 answers (D-020 spirit).
2. **`bar` in a gold alcohol item collides with the class reader.** The lint caught it on the first run (SUB-211, SUB-222: the perfect answer `... full bar` read as `bar_pub`). Gold writes `full liquor` (a listed trigger) instead. T-117 gold writers need this written into the rule.
3. **The rule file's own example `Friday and Saturday nights` as a scored item fits no slot.** The v10 hours reader reads clock times only, so it is a gold error ("move to notes"). Same for `until midnight`, `buildings` and `stories` (table rows 5, 6), `no bar`, `no hot work`, `ansul` (table rows 9, 10, 16). Either the rule file moves them to notes, or a later proposal teaches the reader the days, midnight, buildings and stories. I changed none of this (v10 reader unchanged, per the task).
4. **Case 14 of the rule is read both ways.** "not a bar, restaurant": the scorer keeps `restaurant` (a negated class never masks another), so it hits gold `restaurant` and misses gold `bar_pub`. The rule's first sentence for case 14 lists it as a miss for gold restaurant; its last sentence says the opposite. I followed the last sentence.
5. **Two cooking values in one answer.** The v10 reader keeps `light` over `none` when an answer holds both "cold prep" and "no cooking" (207). Gold holds `none`. A faithful answer to this kind of card misses; the rule routes the ambiguity to gold-fix, not the scorer.
6. **`other_class` is "no listed word found".** An answer with no class word in it reads as `other_class`, so a vague answer can hit a gold `other_class`. Only `laundromat` (169, not in the T-108 scored set) uses it in the dev gold.
7. **Plural forms are only those listed.** "contractors" is listed, "contratistas" is not. The vocabulary is exactly the rule file's.
8. `workbench` import error in pyright is the same as v10's (a path-only warning); no new pyright finding on v11, the lint or `migrate_gold.py`.

## Not done / still open for T-116

- @model-risk check (High only) and the freeze record in `team/NEXT-SESSION.md` (code-under-test commit, prompt hash, scorer sha256). Nothing is committed.
- No model-risk or hold-out run was made; v11 was scored only on a dev re-score from cache.
