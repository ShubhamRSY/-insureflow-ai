# P-088 — Neutral business reason for the housing rule

- Author: @head-of-underwriting. Date: 2026-11-05.
- Re: P-088, T-082 item 5, D-169 item 5, D-170. Answers @responsible-ai finding F2 (`deliverables/responsible-ai/proxy-review.md`).
- Status: statement only. Documentation only. No code, prompt, scorer, gold, or frozen file changed. Not a production approval and not a loss basis.

## Final one-sentence reason (card wording)

> **Habitational fire and liability severity depends on construction, protection, sprinklers, cooking, unit count and loss history, and the class label alone does not show those facts, so a senior underwriter must review the file before any market is selected.**

This is the reason to **refer**, not a reason to decline. The card note adds: *"The housing program and its occupants are not a reason to decline."*

## Risk facts it relies on

| Risk fact | Why it drives a referral | Appetite-guide source |
|---|---|---|
| It is habitational risk, at any unit count | All habitational risk is senior referral and never auto-quote; it is not a target class. | AG:37, AG:62 |
| Cooking inside individual units, and sprinkler status | Habitational + cooking + no sprinklers is a knock-out candidate a person decides, never an automatic outcome. | AG:61 (KO 5), AG:62 |
| Construction, protection class, year built and TIV | If any is unknown, refer; do not auto-quote. Building age must be known. | AG:60 (KO 4), AG:19 |
| Loss history | A liability loss in 5 years, or a property loss over $25,000, is a referral; missing loss runs are incomplete, not a decline. | AG:41, AG:59 (KO 3) |
| The label does not supply the building or loss facts above | A class is in appetite only if a decline can be explained in one sentence a regulator can read; the label alone cannot carry that sentence. | AG:9 |

## What it does NOT rely on

- **Not the class name.** "Student housing" / "subsidized housing" and their Spanish equivalents are labels, not reasons. AG:45 lists them and AG:57 says "reason = class name"; that is the basis F2 rejects.
- **Not the occupants.** It does not rely on age, student status, income, funding source, race, national origin, familial status, disability or source of income (`proxy-review.md` §2).
- **Not a loss basis.** @actuary states none exists (`deliverables/actuary/P-088-housing-loss-basis.md`). This is a risk-fact and information-gap reason, not loss experience.
- **Not price.** Price is a referral to @actuary, not a decline reason (AG:53).
- **Not a carrier prohibition.** No carrier appetite source is cited for these two classes.

## Route it supports

- `senior_referral` with the reason documented on the card.
- No carrier direct. Carrier C may be suggested as on R12, but only a senior underwriter may confirm a market (P-052/D-098).
- No auto-decline and no auto-bind; a person decides. Removing these words from W1 removes the never-overridable `no_match`.

## Limit / condition

- **D-170 condition:** not used in any pilot until the real company compliance/legal function signs the rule and this reason. The team's simulated @compliance sign-off does not count for real applicants.
- Any decline must cite a neutral risk fact, not the class or the tenants; a decline citing either is refused (`proxy-review.md` §7, condition 3).
- Monitor referral and decline rates once pilot data exists; a referral that always ends in a decline is a de facto prohibition (`proxy-review.md` §7, condition 4).
- This reason does not create a loss basis, does not approve production, and does not change any code.

## Draft wording in `deliverables/ai-engineer/proposal-P-088.md`

**Corrected.** The draft was: *"Housing program or student housing (P-088): habitational underwriting by a person — occupancy, sprinklers, building age and condition; the program or the occupants are not a reason to decline."* It led with the class name, "occupancy" was not a specific risk fact, and it omitted cooking, unit count and loss history. The disclaimer is kept. The proposal's note is updated to the final wording above.
