# P-049 — Write down or remove the carrier-match rules the code applies without a written source
- Date / Owner: 2026-10-15 / proposed by @head-of-underwriting; decided by @user (approve change P-049)
- Source: D-095 item 2 (B-364); list from deliverables/senior-underwriter/B-364-gold-check.md. AG = appetite-guide.md, CAG = simulation/carriers.md.
- This file changes no code and no guide. On approval, I edit the guide; @ai-engineer-assistant changes code only for items 7, 9, 10 (each needs the user's exact `approve change P-049`).

## Gold check (D-095 item 2)
- SUB-134 gold carrier_c -> no_match: AGREE. No guide gives light manufacturing to any carrier. D-060: readable class on no list = no_match, overridable.
- SUB-139 gold no_match -> senior_referral (hold first on the loss run): AGREE. AG:37 and AG:62 send all habitational to senior referral; unsprinklered is not prohibited. Label "AG:61" is wrong (see item 10).
- Provisional routes on 129, 131, 135, 136, 137, 139, 140, 142, 144, 145; 138 and 143 left as hold: AGREE. Item 7 and 9 rulings below do not change them (none is a restaurant or a sprinklered habitational with a route recorded as carrier match; re-check 136 and 140 only if either is a restaurant).

## Option A (recommended) — WRITE IT DOWN: 11 rules; plus RULE on 3 conflicts
| # | Rule | Exact text to add | Goes in |
|---|---|---|---|
| 1 | pub, lounge are bars | Prohibited, line "Bars, nightclubs, hookah..." becomes "Bars, pubs, lounges, taverns, nightclubs, hookah, adult entertainment; liquor receipts > 50%." | AG Prohibited |
| 2 | Spanish class words | New line: "Spanish names for a sourced class (cantina, taberna, antro, discoteca, dispensario, etc.) are read as that class. The word list lives in carrier-match.md; @responsible-ai review is required before pilot (D-060)." | AG Prohibited, after the list |
| 3 | synonyms | "Armed guard = armed security; marijuana, dispensary = cannabis; explosive(s) = explosives." | AG Prohibited |
| 4 | Carrier B cap $2,000,000 | "Carrier B TIV cap $2,000,000 per location, inclusive. PROVISIONAL until @actuary signs; over cap = senior referral." | CAG (simulation/carriers.md and the deliverables copy) |
| 5 | contractor word list | "Contractor = any trade contractor: roofing, handyman, painter, drywall, plumbing, electrician, HVAC, glazier, mason, carpentry, concrete, landscaping. The list only helps the reader; any trade not listed is still a contractor and goes to senior referral." Code adds HVAC, glazier, mason. | AG Restricted |
| 6 | Class A words | "Carrier A class words: office, retail, storefront, wholesale. A match is a suggestion; the underwriter confirms: not restaurant, liquor <= 10% of receipts, wholesale light with no cold storage and no hazardous goods, no lab or medical." (The code does not check the exclusions; it must show 'verify' on the route until a later P-### builds them.) | AG Target classes |
| 8 | habitational words | "Habitational = apartments, condos, duplex, triplex, fourplex, flats, any building with residential units for rent, 1 unit or more." | AG Restricted |
| 11 | two classes match | "If two classes match, senior referral; never pick one silently." | AG Knock-out 7 |
| 12 | class on no list | "A readable class on no list is no_match (a recommendation, never a decline); the underwriter may override with a reason." | AG Knock-out 8 |
| 13 | TIV missing | "TIV missing, blank or unreadable: hold." Add to Knock-out 4 list. | AG Knock-out 4 |
| 14 | TIV over $5M | Change AG:16 wording from "out of pilot" to "senior referral, reason: outside pilot TIV limit (AG:16)", as D-060 ruled. | AG Size |

Rulings (code change needed, one P-049 build):
- 7 AG:39 vs CAG restaurant conflict. RULING: AG wins on authority, CAG wins on market. A restaurant or cooking occupancy routes to senior_referral with Carrier B shown as the suggested market, the same shape D-060 used for contractors. Never an auto carrier_b match. D-078 (generic restaurant evidence) stays; only the route changes. Add the sentence to CAG: "Carrier B is the suggested market for restaurants; the route is always senior referral (AG:39)."
- 9 Habitational with sprinklers yes and TIV <= 5M -> carrier_c with no review. Same conflict (AG:37/62 and Knock-out 6 say senior referral, CAG:7 names C). RULING: senior_referral with Carrier C as the suggested market. Cooking knock-out (AG:61): when the file shows cooking and sprinklers no, the code flags "AG:61 knock-out candidate, human decides" and does not decline. If no cooking field is readable, hold-to-ask, not silent pass.
- 10 / AG:61 label on SUB-139. Unsprinklered habitational without cooking is a senior referral citing "AG:37, AG:62". AG:61 is the decline knock-out and only applies with cooking. Also correct the same wrong citation in D-059 item 6 (note on the decision, no rewrite). Code change: the label text only.

## Option B — REMOVE FROM THE CODE: 7 rules (1, 2, 3, 4, 5, 6, 8)
Each word list or cap is deleted. Effects: pub, lounge, Spanish words, synonyms stop matching the bar no_match (they fall to hold or no_match as unreadable class); no Carrier B cap; contractors are caught only by the AG:38 phrase "contractor"; Class A and habitational words need exact guide terms. Rules 11-14 are approved decisions and are not removable without a new decision; they should be written (Option A). Items 7, 9, 10 need the rulings above in either option. I do not recommend B: it weakens the bar and contractor catch and raises hold counts.

## Count
- Option A: 11 rules written down + 3 rulings (7, 9, 10) = 14 changes.
- Option B: 7 rules removed + the same 3 rulings = 10 changes (rules 11-14 still need writing).
- Not in P-049: item 15 (written, not applied: territory, locations 4-10, premium and revenue gates, loss-history referral AG:41, liquor > 10%). That is a code gap against written rules; I ask for it as a backlog item and a follow-up P-###, priority after the demo. Territory is the first: Tier 1 wind counties are not even defined in the guide (Beaumont, SUB-134); I will define the list in the guide once @actuary names the counties.

## Dissent / sign-offs owed
@actuary on item 4 cap; @responsible-ai on item 2 (Spanish) and housing proxy (backlogged, D-060); @compliance if the user wants any Spanish word used in a producer notice.
