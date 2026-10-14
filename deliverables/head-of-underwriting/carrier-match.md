# Carrier match — class lists and caps (T-082)

- Author: @head-of-underwriting
- Date: 2026-10-13
- Status: IN_REVIEW — revised after the four 2026-10-13 reviews. The class lists and the routing rules are decided by D-041 and revised by D-042; the Carrier B and Carrier C caps are **provisional** and are @actuary's to confirm; the @responsible-ai fairness veto is **open**. These class lists, caps, and the Carrier B wording are the rules for T-083, but T-083 must not be coded against the lists until the fairness veto is resolved. The match is a recommendation; the underwriter chooses.
- Source: `deliverables/head-of-underwriting/carrier-appetite.md` (the guide the carriers shared). Carriers A, B, and C are placeholders. Synthetic only.
- Task: T-082. Line 4 of `team/DEMO-BLOCKERS.md`. Reviewed by @senior-underwriter, @actuary, @compliance, and @responsible-ai (decision rights, below). No code is changed by this task.

The match is a recommendation. The underwriter picks the carrier. **No class is an automatic decline, and `no_match` is not a decline to the producer.** The system must not send a package because a rule matched, and must not email the producer a decline.

## How the rule matches

- A class word matches only as a **whole word**; a class phrase matches only as the **exact phrase**. `bar` does not match `barber shop` or `barbecue`; `taco` does not match `tacos`, so both spellings are listed.
- The lists are **language-neutral**. Each class token also matches the Spanish and spelling variants listed beside it, so a Spanish-language submission matches the same carrier a reader of the English would pick. No class is sent to `hold` or `no_match` because of the language it is written in. (@responsible-ai H1.)
- Prohibited classes are checked first and win over every other rule.
- **Collision check before routing.** If the read class or operations match class words of **two or more carriers**, the result is a **senior referral / `hold`** — never silently the earlier carrier in the order below. Example: "office with kitchen" is an office (Carrier A); `kitchen` is not a class word, so it does not pull the file to Carrier B. A genuine two-class file (for example, an office that also prepares food for sale) is a senior referral. (@senior-underwriter H2.)
- If the class is not readable (no operations or class text), the result is `hold`, never `no_match`.
- **Residual unmatched class.** A readable class that matches no Carrier A, B, or C list, is not prohibited, and is within every cap is `no_match` — **not a decline**. `no_match` is the "no placeholder market" state and the file stays with a person. There is no fourth routing bucket. (@senior-underwriter H1.)
- A cap is **inclusive**: a file at exactly the cap still matches that carrier; one dollar over does not.
- Order, after the collision check and the prohibited check: Carrier B (restaurant / light contractor) → Carrier A (office / retail / wholesale) → Carrier C (broader fallback) → `no_match` if it is over every cap, matches no list, or both.

## Carrier A — offices, dry retail, light wholesale

Whole-word class list:

- `office`, `offices` (`oficina`, `oficinas`)
- `retail`, `retail store`, `storefront`, `dry retail` (`tienda`, `tienda minorista`, `comercio`, `local`, `escaparate`)
- `wholesale`, `light wholesale`, `warehouse` (light storage only) (`mayoreo`, `mayorista`, `almacén`, `bodega`)
- Low-hazard personal services: `barber shop`, `barbershop`, `hair salon`, `beauty salon`, `nail salon`, `tailor`, `shoe repair`, `dry cleaner` (drop-off and pickup only) (`barbería`, `peluquería`, `salón de belleza`, `salón de uñas`, `sastrería`, `reparación de calzado`, `lavandería`, `tintorería`)

Not Carrier A: any `restaurant` or food service, any `contractor` or `roofing`, any `habitational`, and any prohibited class.

Cap: **TIV up to and including $5,000,000.** At exactly $5,000,000 the file still matches Carrier A. Over $5,000,000 it is not Carrier A; an office between $5,000,000 and Carrier C's cap is recommended Carrier C (senior referral).

## Carrier B — restaurants and light contractors

Whole-word class list:

- Food service: `restaurant`, `restaurants`, `cafe`, `coffee shop`, `diner`, `deli`, `bakery`, `pizzeria`, `pizza`, `steakhouse`, `barbecue`, `bbq`, `taqueria`, `tacos`, `taco` (`restaurante`, `cafetería`, `café`, `comedor`, `lonchería`, `panadería`, `pastelería`, `pizzería`, `asador`, `parrilla`, `asadero`, `taquería`, `antojitos`). **`kitchen` was removed** — it is a facility word, not a class, and it pulled an "office with kitchen" to Carrier B; `cocina` is not added for the same reason. A file is food service only when its operations name a food-service **class**, not a room.
- Light contractors (no roofing): `light contractor`, `handyman`, `painter`, `painting`, `carpenter`, `carpentry`, `flooring`, `tile`, `drywall`, `insulation`, `janitorial`, `cleaning`, `landscaping`, `lawn care`, `pest control`, `locksmith`, `sign installation` (`contratista`, `albañil`, `pintor`, `pintura`, `carpintero`, `carpintería`, `pisos`, `azulejo`, `tablaroca`, `aislamiento`, `limpieza`, `jardinería`, `control de plagas`, `cerrajería`, `rotulación`)

The food-service words identify a **class** only; they are not a cooking-hazard score. Cooking points are P-015's, not this file's.

Not Carrier B: `roofing` and `roofer` (roofing is not light contracting); any office, retail, or wholesale; any habitational; any prohibited class.

Loss gate: **3 clean loss years**, satisfied **only** by a read, verifiable carrier loss run with a valued-through date that shows no claim inside 3 years. While no such run has been read, the card shows Carrier B with the words **"3 clean years not checked"**. A missing loss run, or a **no-known-loss letter, never satisfies the gate** — a letter is an assertion, not a loss run. If a loss run is later read and shows a claim inside 3 years, the recommendation moves off Carrier B to Carrier C (senior referral). No automatic decline. T-083 must enforce the gate on the **presence of a read loss run**, never on the absence of a claim: the gate cannot pass on an empty or missing loss-history field. (@actuary H2; the loss-run reading rule is T-033.)

Cap: **TIV up to and including $2,000,000 — provisional.** The number is a placeholder working cap, **pending @actuary's signoff**; it is not a priced or filed figure and @actuary may confirm or correct it. At exactly $2,000,000 it still matches Carrier B. Over $2,000,000 it is not Carrier B; it is recommended Carrier C (also provisional).

## Carrier C — broader appetite, higher price

Whole-word class list:

- Habitational **with sprinklers**: `apartment`, `apartments`, `habitational`, `flats`, `multifamily`, `duplex`, `triplex`, `fourplex` (`apartamento`, `apartamentos`, `habitacional`, `departamento`, `departamentos`, `multifamiliar`, `dúplex`, `tríplex`). Sprinklers must read `yes` from the sprinkler field. Habitational with no sprinkler answer is `hold` (missing answer), not a decline. Habitational with sprinklers read `no` is **not Carrier C** — it is a **senior referral**, never a silent match and never a decline.
- Roofing and non-light trade contractors: `roofing`, `roofer`, `roofing contractor` (`techado`, `techador`, `impermeabilización`, `contratista de techos`)
- Offices, retail, and wholesale over Carrier A's $5,000,000 cap and up to Carrier C's cap
- Restaurants and light contractors over Carrier B's $2,000,000 cap, or whose read loss run is not clean

Not Carrier C: any prohibited class; anything over Carrier C's cap.

Cap: **TIV up to and including $10,000,000 — provisional.** The number is a placeholder working cap, **pending @actuary's signoff**; @actuary may confirm or correct it. At exactly $10,000,000 it still matches Carrier C. Over $10,000,000 it is `no_match` (outside the placeholder panel). Carrier C is **not priced**: no price or rate is set here, and none may be set until a filing exists. (@actuary H1.)

Carrier C is the fallback. It is not a substitute for Carrier A or B when those fit: Carrier A first for offices / retail / wholesale, Carrier B first for restaurants / light contractors.

## No match for all three (not a decline)

`no_match` for Carrier A, B, and C:

- `fireworks`, `explosives` (`fuegos artificiales`, `explosivos`)
- `cannabis`, `dispensary`, `marijuana`, `dispensario`, `marihuana` (dispensary, retail, cultivation, any cannabis business)
- `armed security`, `armed guard` (`seguridad armada`, `guardia armado`)
- `student housing`, `fraternity housing`, `sorority housing` (`alojamiento estudiantil`) — see the proxy review below
- `subsidized housing` (`vivienda subsidiada`) — see the proxy review below
- `bar`, `bars`, `nightclub`, `tavern` (`cantina`, `taberna`, `antro`, `discoteca`)
- any risk over $10,000,000 TIV
- **any readable class that matches no Carrier A, B, or C list**, is not prohibited, and is within every cap (the residual branch above)

Say `no_match`. **Do not email the producer a decline.** The file stays with a person.

### Proxy review — housing classes (@responsible-ai H2)

`subsidized housing`, `student housing`, `fraternity housing`, and `sorority housing` are on the no-match list for a **class-based business reason**, not a person one: in this pilot we do not write the occupancy, turnover, and loss profile of those housing classes, and they are not in any carrier's placeholder appetite. The rule reads a **class word**, never a person or a protected characteristic, and the match is a recommendation a human can override.

That entry is not enough by itself. Because those class words can track race, national origin, familial status, disability, and source of income, the resolution @responsible-ai named is a **recommendation-mix test by housing class** in the fairness test (T-067), run before these lists ship. The **fairness veto stands until @responsible-ai resolves it**; T-083 must not be coded against these lists until then. The other resolution @responsible-ai named — routing `subsidized housing` to Carrier C with sprinklers — is a **wider-appetite trade-off that is @actuary's and mine**; I am not taking it unilaterally here, and it stays open for @actuary to price and for me to decide with @actuary.

## Hold (not `no_match`, not a decline)

`hold` when the class or a required answer is missing: no readable operations or class text; habitational with no sprinkler answer. A hold is a missing-information state, not an appetite decision.

## The eight cases

| Case | Class | Answer | Why |
|---|---|---|---|
| cannabis dispensary retail | prohibited | `no_match` | cannabis is prohibited for all three; `retail` does not save it. (Today's code: `carrier_a` — wrong.) |
| armed security office | prohibited | `no_match` | armed security is prohibited; `office` does not save it. (Today: `carrier_a` — wrong.) |
| sprinklered student housing | prohibited | `no_match` | student housing is prohibited even with sprinklers; it is not Carrier C habitational. (Today: `carrier_c` — wrong.) |
| roofing contractor | non-light trade | `carrier_c` | roofing is not light contracting, so not B; Carrier C is the broader market (senior referral). (Today: `carrier_b` — wrong.) |
| an $8,000,000 office | office over cap | `carrier_c` | over Carrier A's $5,000,000 cap, within Carrier C's $10,000,000 cap. (Today: `carrier_a` — wrong.) |
| barbecue restaurant | food service | `carrier_b` + `3 clean years not checked` | a restaurant, not a bar; `barbecue` is a whole word, `bar` is not inside it. (Today: `no_match` — wrong.) |
| barber shop | personal service | `carrier_a` | low-hazard retail / personal service; `barber` is not `bar`. (Today: `no_match` — wrong.) |
| taqueria | food service | `carrier_b` + `3 clean years not checked` | a food-service restaurant. (Today: `hold` — wrong.) |

## Caps at a glance

| Carrier | Cap (TIV) | At exactly the cap | Over the cap |
|---|---|---|---|
| A | $5,000,000 | still matches Carrier A | not A; an office $5M–$10M is recommended Carrier C |
| B | $2,000,000 **provisional** | still matches Carrier B | not B; recommended Carrier C |
| C | $10,000,000 **provisional** | still matches Carrier C | `no_match` (outside the placeholder panel) |

The Carrier B and Carrier C caps are **placeholder working caps pending @actuary's signoff** and are not priced. Carrier C carries no price and may not be priced until a filing exists (D-041; @actuary H1).

## Consultation and review (decision rights)

Risk appetite and underwriting rules are mine to decide; @senior-underwriter and @actuary must be consulted. On 2026-10-13 four reviewers returned **APPROVE WITH CHANGES**; their findings are addressed below.

- **@senior-underwriter — replied and recorded.** On file, T-019 High-3: whole-word class lists, the no-match classes, roofing, the $5M cap, "3 clean years not checked" beside Carrier B, one test each. Adopted. Its 2026-10-13 T-082 reply is recorded in `team/DISCUSSION.md`; its two High findings (the residual unmatched-class branch and `kitchen`) are closed in this revision.
- **@actuary — cap signoff still pending; this is the one open consultation.** On file, T-018 review: "Three clean loss years is the gate for Carrier B, not a vibe. A letter is not three clean years. Do not price Carrier C's 'higher price' until there is a filing, which we do not have." Adopted, and its H2 (verifiable loss run) is now stated in the loss gate. Its H1 is open on this file: the Carrier B and Carrier C caps ($2,000,000 and $10,000,000) are **placeholder working caps**, now marked **provisional pending @actuary's signoff**; @actuary has not yet confirmed or corrected them. **Criterion 5 stays unticked until @actuary's cap reply is recorded in `team/DISCUSSION.md`** (@compliance Medium-1).
- **@compliance — no misrepresentation risk; guardrails kept.** Its Medium-1 is this consultation record; the non-decline guardrails it named are unchanged.
- **@responsible-ai — fairness veto standing on H1 and H2.** H1 is addressed by the language-neutral lists (Spanish and spelling variants) plus the required EN-vs-ES counterfactual in T-067; H2 is addressed by the housing proxy-review entry plus the required recommendation-mix test. The **veto is lifted only by @responsible-ai** and is not lifted here.

## Changes from the accepted T-018 text (recorded as D-041)

- Added whole-word / exact-phrase class lists for Carrier A, B, and C.
- Added a TIV cap to Carrier B ($2,000,000) and Carrier C ($10,000,000). T-018 stated only the $5M cap (Carrier A).
- Carrier C's "broader appetite" is read to include roofing / non-light trade contractors and offices of $5,000,000–$10,000,000. T-018 named only sprinklered habitational for Carrier C.
- Fixed the Carrier B line to "3 clean years not checked".
- No change to the no-match list and no change to "no automatic decline".

## This revision — review changes (recorded as D-042)

From the four 2026-10-13 reviews, documentation only:

- **Residual unmatched-class branch defined** (@senior-underwriter High-1): a readable class on no list, not prohibited, within every cap → `no_match`, not a decline.
- **`kitchen` removed** from Carrier B and a **collision rule** added (@senior-underwriter High-2): a class matching two carriers is a senior referral / `hold`, never silently the earlier carrier.
- **Language-neutral lists** (@responsible-ai High-1): Spanish and spelling variants added to every class token; a Spanish submission matches the same carrier as the English. The EN-vs-ES counterfactual is required in T-067.
- **Housing proxy-review entry** (@responsible-ai High-2) plus the recommendation-mix test routed to T-067; the veto stays open.
- **Caps marked provisional** (@actuary High-1) and the **loss gate tightened to a verifiable read loss run** (@actuary High-2).
- **Consultation record** (@compliance Medium-1): @senior-underwriter's reply recorded; @actuary's cap reply still pending, so criterion 5 stays unticked.

## What I will not defend (unchanged)

- Submitting to a carrier without the workbench decision.
- Treating Carrier B as if it refused restaurants.
- A `no_match` emailed to the producer as a decline.
