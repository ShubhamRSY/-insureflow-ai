# UI check D-099 (P-053, @compliance M1): @senior-underwriter

Verdict: APPROVE, no High. Reviewed: workbench.py confirm_html and _match (commit 454b2fc), both screenshots, WHATS_NEW lines. No code run, no real page or log written (D-069).

## Against the user's words
- "Any other word -> senior_referral with Carrier A suggested; wholesale never direct": SUB-962 ("office and casino") shows senior_referral, "words not on the Carrier A allow-list: casino", Suggested market carrier_a, recommendation only. The unlisted word is named, so I can see why. Wholesale note says whether it is light is a person's call. Met.
- "Senior cannot confirm a carrier the notes exclude; show the reason on the card": SUB-961 ("office with a medical clinic") shows red "Not offered: carrier_a. The carrier match note excludes it (...). Pick another market, or fix the note at source and re-run the file." carrier_a is removed from the dropdown; a posted confirm is refused with plain text (self-check). Send line still says a senior must confirm first. Met.
- D-065: refusal reasons plain; two What's new lines dated 2026-10-16 (M1, P-053) present.

## Backlog (one line each)
- M1 (concur with @model-risk M1): neutral words shop/store/gift/home let "office and shop" or "home office" go direct to Carrier A; underwriters read that as a second operation. Fix before pilot.
- M2: SUB-961 shows "Suggested market: none" but the dropdown pre-selects carrier_b (first in list); add a blank "choose" option so a click is not a market pick by default.
- M3: "casino" is a gaming occupancy; the card lets a senior confirm Carrier A with only a reason. Ask @head-of-underwriting whether gaming words belong on the prohibited list (AG:46).
- L1: card shows ids "carrier_a"; use "Carrier A" for readers.
- L2: if every carrier were excluded the form would show an empty dropdown; add a line "no market can be confirmed".
- L3: "fix the note at source" is jargon; name where (the operations field on the application) and who (producer or account manager).
