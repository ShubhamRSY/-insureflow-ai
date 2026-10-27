# @compliance look-again: P-052 H1 (AG:51 market confirm) and M1 (excluded carrier), D-099

Date: 2026-10-16. Reviewer: @compliance (simulated advisor). Code at 8c985da on ai-team (e5326dc and 454b2fc are ancestors). Read `package.py` (`confirm_problem`, `excluded_carriers`, `market_confirmation`, `confirm_market`, self-check), `workbench.py` (`VACANT`, `NO_UTILITIES`, `_has`, `confirm_html`, self-check), `carrier-match.md` (section "Senior-referral market confirm", W2e). Self-checks run with `.venv/bin/python`: `package ok`, `workbench ok`. `git status` on `team/`, `deliverables/`, `simulation/`, `underwriting_pipeline/` was unchanged by the runs (D-069). Probes were run in memory only.

## Verdict: H1 RESOLVED. M1 RESOLVED. APPROVE, no High.

This closes my OBJECTION in check-P-051-P-052.md. It is not a production approval, and the T-027 veto stands.

## H1, criterion by criterion
1. **Met.** `confirm_problem()` checks `VACANT` (vacant, vacío, unoccupied, plus all four `NO_UTILITIES` phrases) on the normalized text and on the raw operations text (value, quote, context), before the negation drop. "not vacant" also blocks, which is the safe direction. `confirm_market()` raises the same reason, and `confirm_html()` puts it on the card: "No market confirm and no send from this screen: vacant, unoccupied or no utilities ... (AG:51) ...".
2. **Met.** The package self-check loops over the four phrases and asserts "AG:51" in each refusal.
3. **Met in code.** No AG:40 exception path exists, and the refusal says a renovation under a signed GC contract "needs its own rule". (L1 below: the rules file does not say this yet.)

## M1, against the user's words (D-099 item 4)
**Met.** `excluded_carriers()` reads "not Carrier X" from the route note. The card's carrier list leaves the carrier out and says why ("Not offered: carrier_a. The carrier match note excludes it (...). Pick another market, or fix the note at source and re-run the file."). A posted confirm for it is refused with that reason. `market_confirmation()` ignores a logged confirm for an excluded carrier, so a row written into the log directly does not count either. The workbench self-check covers all three on SUB-961 and checks that the R17 "Carrier A suggested" case (SUB-962) is not excluded.

## Medium / Low (backlog, one line each)
- M1: the vacancy word list misses close variants: "vacancy", "vacía", "vacio" (no accent), "desocupado", "utilities shut off", "power disconnected", "sin servicios". Each goes to provisional senior_referral with no AG:51 block, so a confirm would be offered. Fix: @head-of-underwriting extends W2e as a P-###.
- M2: M1 reads only the route note. A producer remark such as "declined by Carrier A" is not read. [NEEDS USER CONFIRMATION] that "the file's notes" in D-099 item 4 means the route note.
- L1: carrier-match.md "Senior-referral market confirm" does not list the W2e/AG:51 confirm block or the AG:40 own-rule condition. Add one line.
- L2: the exclusion regex only matches "not carrier X". A future note such as "not Carrier A or B" would miss B. Add a self-check when a note excludes any carrier other than A.
- L3: the vacancy refusal is self-checked in package.py only. No workbench card render covers it.
