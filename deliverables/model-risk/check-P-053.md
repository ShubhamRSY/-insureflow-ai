# Check of D-099: P-053 (strict Carrier A words; resolves check-P-051-P-052 H1) — @model-risk, 2026-10-16

**Verdict: APPROVE WITH CHANGES. No High finding. check-P-051-P-052 H1 is closed.** M1 and M2 go to the backlog. M1 must be fixed before the pilot. An approved P-053 is not a production approval, and the T-027 veto stands.

## What I re-ran (HEAD 8c985da, no model calls, `git status` the same before and after)
- `.venv/bin/python underwriting_pipeline/app/workbench.py --self-check`: `workbench ok`. `package.py`: `package ok`.
- Code (`_unlisted`, `NEUTRAL`, `NEUTRAL_NO`, `_match`) matches carrier-match.md R14 and R17 word for word. `_match` line 271 is the only direct `carrier_a` return. It runs only after W1, W2, R16, the TIV cap and the wholesale stop, and only when `_unlisted(raw)` is empty. `raw` is value + quote + context, read before the negation drop. No other module returns a carrier route.
- The self-check holds all 27 of my carrier_a probes plus "Light wholesale of electrical supplies". Each one asserts senior_referral, suggested carrier_a, and P-053 in the note. Wholesale never routes directly: plain, light and Spanish wholesale all go to senior_referral with Carrier A suggested.
- A fresh probe of 53 phrases the author has not seen. No named non-target occupancy reached Carrier A: casino (also with a zero-width space between words), guns, "no casino", "casino-free", "100% occupied" and "oficina y tienda" all go to senior_referral, and ammunition goes to no_match.
- Dev re-score (8c985da): 0 unsafe routes, route 19/20, 0 false completes. The one miss is SUB-129, light wholesale, now senior_referral (a safe miss). Gold and scorer were not touched in either commit.
- My own H1 text said to keep SUB-129 as carrier_a. The user's later "wholesale never routes directly" (D-099) overrides it, so the SUB-129 change is correct.
- Screenshot D-099-P-053-carrier-a-suggested.png shows the reason ("words not on the Carrier A allow-list: casino"), Carrier A as the suggested market, and the send refusal in plain language.

## High findings
None.

## Medium / Low (backlog, one line each)
- M1 (owner @head-of-underwriting / @ai-engineer-assistant): "shop", "store", "gift" and "home" are neutral words, so an unnamed second operation routes straight to carrier_a: "office and shop", "office with back shop", "office and store", "office and gift shop", "office and book store", "home office". "Office and retail" goes to R16 instead. Fix: let these words count only next to a retail allow-list phrase (or treat them as the retail group, so R16 catches office plus shop), and drop "home" except inside "home goods". Add the six phrases to the self-check as senior_referral.
- M2: the AG:30 neutral words (candles, greeting, wrap, donated, sorted, held) were taken from the SUB-127/128/135 text, so 4/4 carrier_a on the dev set is an in-sample result. The next hold-out is the first real test of R17.
- L1: the acceptance text says "the 36 @model-risk phrases", but the self-check holds 28. My check-P-051-P-052 named only the 27 that reached Carrier A, so the other 9 cannot be added from that file. This gap is mine; I will list the 9 in the next check.
- L2: noisy but safe: "retail store, no food or alcohol" goes to senior_referral because "alcohol" is not read after "or". "officé" and "office_casino" go to no_match (R8), not senior_referral.
- L3 (carried over): the dev scorer recomputes routes with live code, so the route column measures current code, not the saved run.
