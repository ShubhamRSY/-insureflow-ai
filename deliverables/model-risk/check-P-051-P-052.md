# Check of D-098: P-051 (allow-list routing) and P-052 (senior market confirm) — @model-risk, 2026-10-16

**Verdict: OBJECTION on P-051 (H1 open). P-052: APPROVE WITH CHANGES (no High of its own; M2, M3 to backlog).** Item 3 dev re-check: accepted as a dev result only. An approved P-051/P-052 is not a production approval; the T-027 veto stands.

## What I re-ran (HEAD d53e250, no model calls, no real file changed: `git status` same before and after)
- `.venv/bin/python underwriting_pipeline/app/workbench.py --self-check`: `workbench ok`. `.venv/bin/python underwriting_pipeline/app/package.py`: `package ok`.
- The four P-049 H1 phrases, the thrift shop and the clothing store route as asked (4 x senior_referral, 2 x carrier_a), and the self-checks include them.
- A probe of 36 operations phrases not in the self-checks, through `workbench.match()` on a complete file with TIV $1,000,000.
- Dev re-score JSON: 20/20 routes, 0 unsafe, 0 false completes; gold split 5 carrier_a / 14 senior_referral / 1 no_match. I could not recompute routes from saved runs here (`read_saved_run` finds none outside the eval's cache copy), so the numbers are taken from the committed JSON.

## High findings
**H1 — R14 is still a trigger-word list with a closed deny-list for second operations, not an allow-list (D-098 1a, 1b).** Carrier A is returned whenever the text has one allow-list word and no W1, W2 or OTHER_OPS word. Any occupancy not on those lists passes. The code says so itself (`workbench.py` line 130: "a word not here still reaches Carrier A"), which contradicts carrier-match.md R14 ("Every class not on the list never reaches Carrier A"). Probe results, all **carrier_a**: "office and warehouse", "office and auto body shop", "retail and tattoo parlor", "retail and pawn shop", "office with veterinary practice", "office with indoor shooting range", "office and data center", "office and kennel", "office and casino", "retail with bowling alley", "retail and brewery taproom", "retail and winery tasting room", "retail and cbd", "retail smoke shop", "retail - vape shop", "office tenants; second floor event hall", "office and storage of tires". AG:31 says "Wholesale: light", but any "wholesale" passes: "lumber wholesale", "steel wholesale", "scrap metal wholesale", "tire wholesale", "wholesale firearms" are all carrier_a. 27 of the 36 probes reached Carrier A, and none of those 27 is a single allow-list class. The 20/20 dev result does not show this because the rules were built on that set.
**Resolve (one of these, chosen by @user / @head-of-underwriting):**
(i) Carrier A only when the operations text holds nothing except allow-list phrases and a closed list of neutral words (floors, tenants, "no food", "no alcohol", goods named under AG:30). Any other noun goes to senior_referral. Wholesale goes to Carrier A only when it says "light" or names goods on a closed light-goods list; plain "wholesale" goes to senior_referral. Or
(ii) no direct Carrier A route: allow-list files go to senior_referral with Carrier A as the suggested market, confirmed through the P-052 path.
Either way, add every carrier_a probe above to the self-check as senior_referral, and keep the SUB-127/128/129/135/143 operations as carrier_a.

## Medium / Low (backlog, one line each)
- M1: vacancy synonyms reach Carrier A: "office, no tenants", "retail, building empty", "office, utilities shut off", "office, power disconnected", "office, under renovation" (AG:40). Extend W2e, or let resolution (i) cover them.
- M2: a senior can confirm any carrier, including carrier_a, on a W2e "no utilities" or vacant file, and AG:51 lists both as prohibited. @head-of-underwriting / @user to rule whether W2e files may be confirmed.
- M3: the senior identity is self-asserted (an underwriter_id picked from a dropdown, no CSRF). Already B-383. Must be fixed before pilot, because P-052's "only a senior" rests on it.
- L1: "office, not vacant" goes to senior_referral because the negation is not read. Safe direction, but noisy.
- L2: "office and nightclub" goes to senior_referral (R16) while "office and cannabis" goes to no_match. Both are W1 under AG:46-47; this follows D-098 1b, but the rules file should say why the two differ.
- L3: the dev scorer recomputes routes with live code (D-098 item 3 is already in the backlog). Until that is fixed, the route column measures current code, not the saved run.
