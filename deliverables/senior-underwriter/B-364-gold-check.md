# B-364 gold check (D-095 item 2) — @senior-underwriter, 2026-10-15

Written sources only: simulation/carriers.md (CAG), deliverables/head-of-underwriting/appetite-guide.md (AG, cited by line), D-059, D-060, D-078, D-079.

## SUB-134 (glass and mirror shop)
Gold carrier_c -> no_match. No written source gives light manufacturing to any carrier; C is "broader appetite" (carriers.md) but D-059 item 4 / CAG:7 define C as sprinklered habitational. D-060: readable class on no list = no_match, overridable. The code is right. Carrier C is an override a human may choose. Open: Beaumont may be a "Tier 1 wind county" (AG Territory); the guide does not define the list and the code does not check territory.

## SUB-139 (habitational, no sprinklers)
Gold no_match -> senior_referral (hold on the missing loss run first). AG lines 37 and 62 and D-059 item 6 (approved D-060): habitational is a senior referral; sprinklers "no" is a senior referral. Not prohibited. The code route is right but cites AG:61, which is the knock-out "habitational AND cooking AND no sprinklers" (decline); this file has no cooking. The citation is wrong; the label should cite AG:37/D-059 item 6.

## Provisional routes added to held gold (SUB-127..146)
129 carrier_a; 131 senior_referral; 135 carrier_a; 136 carrier_b; 137 senior_referral; 139 senior_referral; 140 carrier_b; 142 senior_referral; 144 no_match; 145 senior_referral.
Left as hold: 138 (fertilizer may be a hazardous commodity, AG line 31; documents do not say), 143 (no TIV, Carrier A cap cannot be checked).
Watch: 135 ops text has no word "retail" and 144 is read from an image, so the code may differ from gold for class-word reasons. Gold follows the rules, not the code.

## Rules the code applies that no appetite or referral source writes
1. Pub and lounge are bar words (BAR_WORDS, "pub", "lounge"): AG:46 lists bars, nightclubs, hookah, not pub or lounge. D-079 approved the list, but the guide itself was never edited.
2. PROHIBITED Spanish words (cantina, taberna, antro, discoteca, dispensario, ...): D-060 allows Spanish only as translations of sourced classes; list is not in any guide (B-197 owed).
3. PROHIBITED "armed guard", "marijuana", "dispensary", "explosive" variants: synonyms, not in the guide text; minor.
4. CAP_B = 2,000,000 (over cap -> senior_referral): D-060 provisional, no guide cites it, @actuary signoff owed.
5. Contractor word list (roofing, handyman, painter, drywall, plumbing, electrician, ...): AG:38 says "all contractors" with no list; the list is code only. Missing: HVAC, glazier, mason; SUB-137 depends on it.
6. Class A words "retail", "storefront", "wholesale" as a match, with "light" not tested: AG:31 says light wholesale, no cold storage, no hazardous commodities; the code checks none of those exclusions (cold storage, hazardous goods, liquor over 10%, lab or medical).
7. Class B "kitchen", "cooking equipment present" as restaurant evidence (D-078): approved, but AG:39 sends all restaurants and cooking occupancy to senior referral while carriers.md gives them to B. Two written rules conflict; the code follows carriers.md (carrier_b) and never the senior referral. Needs a head-of-underwriting ruling.
8. Habitational "duplex, triplex, fourplex, flats" word list: no source.
9. Habitational with sprinklers yes and TIV <= 5M -> carrier_c with no cap: D-060 removed the C cap; consistent, but nothing checks unit count or the AG:61 cooking knock-out (no cooking field is read for habitational).
10. Habitational unsprinklered -> senior_referral labelled "AG:61": wrong citation (see SUB-139).
11. Two classes matching -> senior_referral: D-059 item 7, approved; no guide source (own rule).
12. "readable class on no list" -> no_match: D-059 item 5, approved; no guide source.
13. TIV missing/unreadable -> hold: AG rule 4 covers construction, protection and year built, not TIV; D-061 approved.
14. Over 5M TIV -> senior_referral for every class: D-060 approved, AG:16 says "out of pilot".
15. Not checked at all by the code though written: territory (AG Territory), locations 4-10 refer (AG:17), premium and revenue gates (AG:15, 18), loss-history referral (AG:41, any liability loss or property loss > $25,000 in 5 years), liquor over 10% retail.

Count: items 1, 2, 4, 5, 6, 8, 10 are applied in code with no written source or a wrong source (7). Items 11-14 are approved decisions (D-059/D-060/D-061) but have no appetite-guide text. Item 7 is a written conflict. Item 15 is written but not applied.
Proposal needed (P-### from @head-of-underwriting): write 1, 4, 5, 6, 8 into the appetite guide or remove them; fix the 10 label; rule on 7.
