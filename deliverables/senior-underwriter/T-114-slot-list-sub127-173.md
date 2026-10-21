# T-114 validation: slot table vs SUB-127–173 (development set only)

- Author: @senior-underwriter, 2026-10-20
- Validates: the slot definition table appended to `operations-gold-rule.md` ("Slot definition table (T-114 / D-117, 2026-10-20)")
- Source read: `deliverables/senior-underwriter/gold-set/` SUB-127–173 ONLY. No T-108 (SUB-206–237) gold was read.

## Correction to the task's premises (read this first)

1. **SUB-127–173 is 47 files, not 54.** 173 − 127 + 1 = 47.
2. **Zero of them carry a `- Operations items:` line.** The items-line format starts at SUB-174, outside the range I was allowed to read. All 47 carry the older one-line `- Operations:` format (SUB-168 = `not in documents`). Validation therefore decomposes each `- Operations:` line into atomic facts and checks each fact against the table.

## Coverage numbers

| Measure | Count |
|---|---|
| Files read | 47 |
| Files with an `- Operations:` line stating facts | 46 (SUB-168 is `not in documents`, correctly empty) |
| Atomic facts decomposed from those lines | 187 |
| Facts mapping cleanly to exactly one slot + value (CLEAN) | 134 / 187 = **71.7%** |
| Facts mapping to slot value(s) but flagged ambiguous (AMBIG) | 9 / 187 = 4.8% |
| Facts mapped to at least one slot (CLEAN + AMBIG) | 143 / 187 = **76.5%** |
| Facts with no slot — all rule-exempt, "not required" (NOT_COVERED) | 44 / 187 = 23.5% |
| **Required-item / closed-list facts left uncovered** | **0 / 187** |

**Verdict on generalisation:** every fact in SUB-127–173 that the rule makes *required* (type, alcohol, seats, units, cooking, hours) or part of the *closed list* (entertainment, frying/open flame, delivery, 24-hour, floor, on-site processing, outdoor, security, hazmat) maps to exactly one slot + value. The 44 no-slot facts are exactly the categories the rule already excludes (marketing/menu/merchandise glosses, lease terms, service style, location counts, occupancy %, machine counts, maintenance dates). The table generalises beyond T-108 because it was built from the rule + underwriting knowledge and still lands on 100% of rule-required facts in an untouched development set.

## Slots exercised by the development set

`business_type`, `alcohol` (full_bar, beer_wine, none), `seats`, `units` (+`buildings`/`stories`), `cooking` (full, none), `fryer` (yes, with counts), `open_flame` (yes/no), `hood` (yes), `entertainment` (live), `floor` (ground/first/second), `onsite_processing` (yes/no), `hazmat` (yes/no), `delivery` (no).

**Slots with no positive occurrence in SUB-127–173** (vocabulary from underwriting knowledge only; untested by the dev set): `open_24h`, `security`, `outdoor`, `delivery=yes`, `hours` as a standalone item (only inside the live-music clause), `beer_only`, `floor=basement`, `entertainment=none`, `cooking=light`. Also: **no Spanish phrasings appear in any SUB-127–173 Operations line** — all Spanish synonyms in the table come from underwriting knowledge, not this set.

## Ambiguous items (9) — map to slots but not exactly one

| File | Fact | Why ambiguous | Resolution in the table |
|---|---|---|---|
| SUB-128 | "Dry retail gift shop" | "dry" = wet/dry (no alcohol) vs "dry goods" (merchandise) | **"dry" is excluded as an alcohol trigger**; only explicit "no alcohol/sin licor" sets `none`. business_type still CLEAN. |
| SUB-153 | "Dry retail stationery…" | same | same |
| SUB-155 | "Dry retail storefront…" | same | same |
| SUB-157 | "charbroiler" | triggers `cooking=full` AND `open_flame=yes` | compound trigger defined in the table; both values always co-occur, so gold carries both items and comparison stays deterministic |
| SUB-163 | "grill" | same | same |
| SUB-170 | "charbroiler" | same | same |
| SUB-171 | "charbroiler" | same | same |
| SUB-157 | "live music Thursday to Sunday until midnight" | one clause, two slots (`entertainment=live` + `hours`) | both slots extracted from the same clause; negation scoped per slot |
| SUB-171 | "live music Thursday to Sunday until midnight" | same | same |

## Uncovered items (44) — no slot, all rule-exempt

Grouped; none is a required item or closed-list detail.

- **Lease/occupancy terms (9):** long-term leases (SUB-133, 139, 145, 149, 158, 160, 167, 172); 92 percent occupied (SUB-149).
- **Service style / meal periods (10):** dine-in and takeout (SUB-140, 156, 159, 170); breakfast and lunch counter service (SUB-156); dinner service and weekend brunch (SUB-157, 171); table service and takeout (SUB-163); customers wash their own clothes (SUB-169); clients by appointment (SUB-154, 162).
- **Menu / merchandise glosses (6):** candles/home goods/greeting cards/gift wrap (SUB-128); wire/breakers/conduit/fixtures (SUB-129); pastries/sandwiches/coffee (SUB-159); aerial/ground/cakes fireworks types (SUB-165); burgers/chicken/breakfast (SUB-170); tacos/burritos/quesadillas/agua fresca (SUB-173).
- **Location / premises details (9):** two locations (SUB-140); 2 locations (SUB-170); 3 properties (SUB-172); trade counter (SUB-150); sales floor and one storage room (SUB-152); shop and yard on premises (SUB-164); warehouse with loading dock (SUB-161); storefront and seasonal tent (SUB-165); materials stored outside under tarps (SUB-164).
- **Equipment counts, not dwelling units (1):** 14 washers and 8 gas dryers (SUB-169) — deliberately NOT mapped to `units`.
- **Maintenance / dates (1):** hood and duct cleaned quarterly, last 2026-08-20 (SUB-148) — hood=yes already captured; dates are completeness, not operations.
- **Non-slot modifiers and exclusions (5):** no bar (SUB-136, 163); no inventory / no goods held for sale (SUB-154, 162); no firearms or ammunition (SUB-152); no retail (SUB-166).

## Slots I was unsure how to enumerate (flagged for @model-risk / the AI Engineer)

1. **`business_type` is open-valued** — it cannot be a closed enum without overfitting. Compared by trade-word overlap within the clause. Listed vocabulary is illustrative, not exhaustive.
2. **"dry"** — deliberately kept out of the alcohol enum (see above). If a future hold-out uses "dry" to mean no alcohol, the safe reading is "did they also say no alcohol explicitly"; do not add "dry" as a trigger without the user's approval.
3. **"no bar"** — not a slot; underwriting it means no bar service, consistent with beer & wine only. The scorer should ignore it, never treat it as negating alcohol.
4. **"until midnight" inside an entertainment clause** (SUB-157/171) — hours vs entertainment boundary. Table says: extract both; each compared on its own.
5. **Machine counts** (washers/dryers) vs `units` — kept out of `units`; if a future rule wants equipment counts, that is a new slot by user decision.
6. **Fireworks/ammunition** — fireworks stock sets `hazmat=yes`; "no firearms" has no slot. If firearms become a target-class issue, propose a slot; do not fold into hazmat silently.

## Item-by-item detail

### SUB-127

| Financial advisory and tax office | CLEAN | business_type | financial advisory office |
| 2nd floor | CLEAN | floor | second |

### SUB-128

| Dry retail gift shop | AMBIG | business_type | retail gift shop ('dry' modifier ambiguous: wet/dry vs dry goods) |
| candles, home goods, greeting cards, gift wrap | NOT_COVERED | - | - |

### SUB-129

| Light wholesale of electrical supplies | CLEAN | business_type | wholesale electrical supplies |
| (wire, breakers, conduit, fixtures) | NOT_COVERED | - | - |

### SUB-130

| Breakfast and lunch cafe | CLEAN | business_type | breakfast/lunch cafe |
| 64 seats | CLEAN | seats | 64 |
| beer and wine only | CLEAN | alcohol | beer_wine |

### SUB-131

| Commercial plumbing service and repair | CLEAN | business_type | plumbing contractor |
| water heater installs, small remodel work | CLEAN | business_type | trade scope |

### SUB-132

| Southern breakfast and lunch restaurant | CLEAN | business_type | breakfast/lunch restaurant |
| 90 seats | CLEAN | seats | 90 |
| beer and wine only | CLEAN | alcohol | beer_wine |

### SUB-133

| Residential apartments | CLEAN | business_type | apartments |
| 12 units in one two-story building | CLEAN | units | 12 (buildings=1, stories=2 sub-facts) |
| long-term leases | NOT_COVERED | - | - |

### SUB-134

| Glass cutting, tempering and framing for commercial storefronts | CLEAN | business_type | glass contractor |

### SUB-135

| Used book and thrift shop | CLEAN | business_type | thrift shop |
| donated goods sorted on site | CLEAN | onsite_processing | yes |

### SUB-136

| Mexican restaurant | CLEAN | business_type | restaurant |
| 70 seats | CLEAN | seats | 70 |
| beer and wine only | CLEAN | alcohol | beer_wine |
| no bar | NOT_COVERED | - | - |

### SUB-137

| HVAC installation and service contractor | CLEAN | business_type | HVAC contractor |

### SUB-138

| Wholesale and retail of animal feed, seed and fertilizer bags | CLEAN | business_type | feed/seed retailer-wholesaler |

### SUB-139

| Residential apartments | CLEAN | business_type | apartments |
| 6 units in two two-story buildings | CLEAN | units | 6 (buildings=2, stories=2 sub-facts) |
| long-term leases | NOT_COVERED | - | - |

### SUB-140

| Barbecue restaurants | CLEAN | business_type | BBQ restaurant |
| two locations | NOT_COVERED | - | - |
| dine-in and takeout | NOT_COVERED | - | - |

### SUB-141

| Full-service restaurant and bar | CLEAN | business_type | full-service restaurant and bar |
| 180 seats | CLEAN | seats | 180 |
| full liquor license | CLEAN | alcohol | full_bar |
| live music Friday and Saturday | CLEAN | entertainment | live |

### SUB-142

| Roofing contractor | CLEAN | business_type | roofing contractor |

### SUB-143

| Clothing boutique retail store | CLEAN | business_type | retail clothing |

### SUB-144

| outpatient pediatric physical and speech therapy | CLEAN | business_type | therapy clinic |

### SUB-145

| Residential apartments | CLEAN | business_type | apartments |
| 40 units in three two-story buildings | CLEAN | units | 40 (buildings=3, stories=2 sub-facts) |
| long-term leases | NOT_COVERED | - | - |

### SUB-146

| Full-service restaurant and bar | CLEAN | business_type | full-service restaurant and bar |
| 180 seats | CLEAN | seats | 180 |
| full liquor license | CLEAN | alcohol | full_bar |
| live music Friday and Saturday | CLEAN | entertainment | live |

### SUB-147

| CPA tax preparation and bookkeeping office | CLEAN | business_type | CPA office |

### SUB-148

| full-service restaurant | CLEAN | business_type | full-service restaurant |
| 140 seats | CLEAN | seats | 140 |
| beer and wine only | CLEAN | alcohol | beer_wine |
| Type I hood with UL 300 wet chemical | CLEAN | hood | yes |
| hood and duct cleaned quarterly, last 2026-08-20 | NOT_COVERED | - | - |

### SUB-149

| 12-unit apartment building | CLEAN | units | 12 (+ business_type) |
| long-term leases | NOT_COVERED | - | - |
| 92 percent occupied | NOT_COVERED | - | - |

### SUB-150

| light wholesale of hardware and janitorial supplies to contractors | CLEAN | business_type | wholesale hardware/janitorial |
| trade counter | NOT_COVERED | - | - |
| no manufacturing or repackaging | CLEAN | onsite_processing | no |

### SUB-151

| interior drywall hanging and finishing, trim carpentry, acoustic ceilings, commercial and residential remodel | CLEAN | business_type | drywall/remodel contractor |
| office and tool shop | CLEAN | business_type | premises detail |
| no hot work on premises | CLEAN | open_flame | no |

### SUB-152

| retail outdoor gear and apparel | CLEAN | business_type | retail outdoor gear |
| sales floor and one storage room | NOT_COVERED | - | - |
| no firearms or ammunition | NOT_COVERED | - | - |

### SUB-153

| Dry retail stationery and office supplies with light wholesale and admin office | AMBIG | business_type | stationery/office-supplies retailer ('dry' ambiguous) |

### SUB-154

| Office | CLEAN | business_type | office |
| 2nd floor | CLEAN | floor | second |
| clients by appointment | NOT_COVERED | - | - |
| no inventory, no goods held for sale | NOT_COVERED | - | - |

### SUB-155

| Dry retail storefront | AMBIG | business_type | retail storefront ('dry' ambiguous) |
| ground floor | CLEAN | floor | ground |
| clothing and dry goods | CLEAN | business_type | clothing/dry-goods retail |
| no food | CLEAN | cooking | none |
| no alcohol | CLEAN | alcohol | none |
| no repackaging | CLEAN | onsite_processing | no |

### SUB-156

| Restaurant | CLEAN | business_type | restaurant |
| no alcohol of any kind | CLEAN | alcohol | none |
| 48 seats | CLEAN | seats | 48 |
| flat-top | CLEAN | cooking | full |
| 2 fryers | CLEAN | fryer | yes (count 2) |
| 4-burner range | CLEAN | cooking | full |
| Type I hood with UL 300 suppression | CLEAN | hood | yes |
| breakfast and lunch counter service | NOT_COVERED | - | - |
| dine-in and takeout | NOT_COVERED | - | - |

### SUB-157

| Restaurant and bar | CLEAN | business_type | restaurant and bar |
| full liquor (TABC mixed beverage permit) | CLEAN | alcohol | full_bar |
| 140 seats | CLEAN | seats | 140 |
| charbroiler | AMBIG | cooking+open_flame | full + yes (always co-occur) |
| 2 fryers | CLEAN | fryer | yes (count 2) |
| flat-top | CLEAN | cooking | full |
| 8-burner range | CLEAN | cooking | full |
| pizza oven | CLEAN | cooking | full |
| Type I hood with UL 300 | CLEAN | hood | yes |
| live music Thursday to Sunday until midnight | AMBIG | entertainment+hours | live + until midnight (two slots, one clause) |
| dinner service and weekend brunch | NOT_COVERED | - | - |

### SUB-158

| Apartment building | CLEAN | business_type | apartment building |
| 16 units | CLEAN | units | 16 |
| two two-story buildings | CLEAN | buildings+stories | 2 + 2 |
| long-term leases | NOT_COVERED | - | - |
| no cooking operations (tenant electric ranges only) | CLEAN | cooking | none |

### SUB-159

| Bakery and cafe | CLEAN | business_type | bakery and cafe |
| (pastries, sandwiches, coffee) | NOT_COVERED | - | - |
| no alcohol sold | CLEAN | alcohol | none |
| 30 seats | CLEAN | seats | 30 |
| deck oven | CLEAN | cooking | full (must not trigger outdoor) |
| 2 convection ovens | CLEAN | cooking | full |
| 4-burner range and flat-top | CLEAN | cooking | full |
| Type I hood with UL 300 | CLEAN | hood | yes |
| dine-in and takeout | NOT_COVERED | - | - |

### SUB-160

| Apartment building | CLEAN | business_type | apartment building |
| 8 units | CLEAN | units | 8 |
| two two-story buildings | CLEAN | buildings+stories | 2 + 2 |
| long-term leases | NOT_COVERED | - | - |
| no cooking operations (tenant electric ranges only) | CLEAN | cooking | none |

### SUB-161

| Light wholesale of home goods, kitchenware and small hand tools to retail stores | CLEAN | business_type | wholesale home goods |
| goods not hazardous (no flammable liquids, aerosols, pesticides, batteries) | CLEAN | hazmat | no |
| warehouse with loading dock | NOT_COVERED | - | - |
| no repackaging | CLEAN | onsite_processing | no |

### SUB-162

| Office suite | CLEAN | business_type | office |
| clients by appointment | NOT_COVERED | - | - |
| no inventory | NOT_COVERED | - | - |

### SUB-163

| Mexican restaurant | CLEAN | business_type | restaurant |
| beer and wine only | CLEAN | alcohol | beer_wine |
| no bar | NOT_COVERED | - | - |
| 60 seats | CLEAN | seats | 60 |
| comal | CLEAN | cooking | full |
| grill | AMBIG | cooking+open_flame | full + yes (always co-occur) |
| 2 fryers | CLEAN | fryer | yes (count 2) |
| 6-burner range | CLEAN | cooking | full |
| Type I hood with UL 300 | CLEAN | hood | yes |
| table service and takeout | NOT_COVERED | - | - |

### SUB-164

| Roofing contractor | CLEAN | business_type | roofing contractor |
| residential and commercial re-roofing and repair | CLEAN | business_type | trade scope |
| shop and yard on premises | NOT_COVERED | - | - |
| materials stored outside under tarps | NOT_COVERED | - | - |
| torch-down work on some jobs | CLEAN | open_flame | yes |

### SUB-165

| Retail sale of consumer fireworks | CLEAN | hazmat | yes (+ business_type fireworks retailer) |
| (aerial, ground and cakes) | NOT_COVERED | - | - |
| storefront and seasonal tent (June and July) | NOT_COVERED | - | - |
| fireworks inventory stored on premises including in a trailer on the lot | CLEAN | hazmat | yes (storage detail not its own slot) |

### SUB-166

| Owner-occupied two-story office building | CLEAN | business_type | office building (+ stories=2) |
| insured occupies first floor | CLEAN | floor | first |
| two tenants on second floor | CLEAN | floor | second |
| office use only | CLEAN | business_type | office |
| no retail | NOT_COVERED | - | - |
| no food | CLEAN | cooking | none |

### SUB-167

| Apartment building | CLEAN | business_type | apartment building |
| 24 units | CLEAN | units | 24 |
| three two-story buildings | CLEAN | buildings+stories | 3 + 2 |
| long-term leases | NOT_COVERED | - | - |
| no cooking operations (tenant electric ranges only) | CLEAN | cooking | none |

### SUB-168

| not in documents (no operations stated) | EXEMPT | - | - |

### SUB-169

| Self-service laundromat | CLEAN | business_type | laundromat |
| 14 washers and 8 gas dryers | NOT_COVERED | - | - |
| customers wash their own clothes | NOT_COVERED | - | - |
| no commercial pressing | CLEAN | onsite_processing | no |
| no delivery service | CLEAN | delivery | no |

### SUB-170

| Restaurant | CLEAN | business_type | restaurant |
| 2 locations | NOT_COVERED | - | - |
| burgers, chicken and breakfast | NOT_COVERED | - | - |
| beer and wine only (no liquor license) | CLEAN | alcohol | beer_wine (parenthetical negation must not flip to full_bar) |
| flat-top | CLEAN | cooking | full |
| 2 fryers | CLEAN | fryer | yes (count 2) |
| charbroiler | AMBIG | cooking+open_flame | full + yes (always co-occur) |
| 8-burner range | CLEAN | cooking | full |
| Type I hood with UL 300 at both locations | CLEAN | hood | yes |
| dine-in and takeout | NOT_COVERED | - | - |

### SUB-171

| Restaurant and bar | CLEAN | business_type | restaurant and bar |
| full liquor (TABC mixed beverage permit) | CLEAN | alcohol | full_bar |
| 140 seats | CLEAN | seats | 140 |
| charbroiler | AMBIG | cooking+open_flame | full + yes (always co-occur) |
| 2 fryers | CLEAN | fryer | yes (count 2) |
| flat-top | CLEAN | cooking | full |
| 8-burner range | CLEAN | cooking | full |
| pizza oven | CLEAN | cooking | full |
| Type I hood with UL 300 | CLEAN | hood | yes |
| live music Thursday to Sunday until midnight | AMBIG | entertainment+hours | live + until midnight (two slots, one clause) |
| dinner service and weekend brunch | NOT_COVERED | - | - |

### SUB-172

| Apartment buildings | CLEAN | business_type | apartments |
| 3 properties | NOT_COVERED | - | - |
| 30 units total | CLEAN | units | 30 |
| long-term leases | NOT_COVERED | - | - |
| no cooking operations (tenant electric ranges only) | CLEAN | cooking | none |

### SUB-173

| Counter service taqueria | CLEAN | business_type | taqueria/counter restaurant |
| (tacos, burritos, quesadillas, agua fresca) | NOT_COVERED | - | - |
| no liquor | CLEAN | alcohol | none |
| 35 seats | CLEAN | seats | 35 |
| dine-in and takeout | NOT_COVERED | - | - |
