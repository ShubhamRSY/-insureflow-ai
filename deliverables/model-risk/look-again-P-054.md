# Look-again of check-P-054 H1 and H2 (D-100, P-054): @model-risk, 2026-10-16

**Verdict: APPROVE. H1 and H2 are closed, and I found no new High.** From @model-risk's side, D-100 item 2 (freeze the code, build T-103) can go ahead. An approved P-054 is not a production approval. The T-027 veto still stands.

## What I re-ran (ai-team at 8d3e4f0, fixes in 3557e4a, on a temp copy made with git archive, no model calls, no tracked file changed)
- `workbench.py --self-check` printed `workbench ok`. `package.py` printed `package ok`.
- ai-team now holds the P-054 commits (9320666, cbd097c, 3557e4a, 8d3e4f0). The GCP commits 6d8907e and 0cc87ae are not on it, and only `package.py` and `workbench.py` changed outside `team/` and `deliverables/` since 3ebbf23. **Old M3 is closed.**
- I recomputed the dev re-score from the JSON. It ran at commit 3557e4a with nothing uncommitted. All 20 replies came from the cache. Route is 16/20, with 0 unsafe routes and 0 false completes. The 4 misses are SUB-127, 128, 129 and 135, all in the safe direction. These figures match the .md.

## H1: CLOSED
- **Real data.** I used the actual `simulation/inbox/SUB-147/email.md` with the operations "Downtown office, CPA and bookkeeping". The file routes to senior_referral with Carrier A suggested, and `excluded_carriers` now returns `carrier_a`, quoting "...coming to you guys from Carrier A, they are not renewing...". Carrier A can no longer be confirmed on that file.
- **Each item in the resolution:**
  - Case. The carrier letter now matches in any case ("carrier a declined", "CARRIER A DECLINED", "Carrier-A", "CarrierA" and "carrier_a" are all excluded). The guard ("carrier a few times", "a lot of") still holds.
  - Same-sentence rule. A carrier is excluded when it is named in the same sentence as a decline word. Every word I asked for is in `DECLINE`. All 10 phrasings that were missed before are now excluded.
  - Self-check. The SUB-147 email and those phrasings are in the self-check (SUB-4400 to 4413), with a negative case (SUB-4499: a loss run plus "carrier a few times").
- **Rules file.** carrier-match.md, "Senior-referral market confirm", states the rule and its scope (PDFs and scans are read only through their extracted fields).
- **Sweep of the real inbox.** I ran `excluded_carriers` over every folder in `simulation/inbox/`. SUB-147 is the only exclusion, so it raised no false exclusions on real files.

## H2: CLOSED
- "cooking" is off `NEUTRAL`. "office with cooking", "office, cooking", "office, back room cooking" and "retail store, cooking on the ground floor" all go to senior_referral with Carrier A suggested.
- "office building. Cooking: none", "Office (cooking: none)" and "cooking operations - none" stay carrier_a. "cook", "cooks", "grill", "microwave", "coffee", "kitchen", "catering" and "cocina" all go to senior_referral.
- These cases are in the workbench self-check. R17 now names the label forms and says "cooking" anywhere else is an occupancy word.

## Medium / Low (backlog, one line each)
- M5 (new): `DECLINE` still misses some phrasings. "non renewal" (with a space), "Carrier A's no-renewal", "did not renew", "terminated", "out of appetite", "no quote", "unable to quote" / "couldn't quote", "said no", "Carrier\nA declined" (a line break inside the name), and a decline in the next sentence ("Carrier A wrote it five years. They declined to renew.") are not excluded. Fix: `non[\s-]?renew`, `no-?renewal`, `(?:did ?n[o']t|not) renew`, `terminat`, `appetite`, `no quote`, `(?:unable to|can(?:no|')t|couldn't) (?:quote|offer|write)`, `\s` inside the name, and check each sentence together with the one after it.
- L4 (new): it over-excludes in the safe direction. "We have never had a loss with Carrier A" and "please do not cancel the Carrier A quote request" exclude Carrier A, and nobody can fix a producer email at source. The card quotes the sentence, so a senior can see why.
- L5 (new): "office, no; cooking" routes to carrier_a because "no cooking" is matched after the punctuation is dropped. This is unlikely in real text.
- Old M1 is closed: the vacancy phrasings are now W2e and are in the self-check.
- Still open: old M2 (PDF and scan text is not read for excludes), old M4 (the dev gold predates R17, so the T-103 gold must be written under R17 as amended), old L1 (W2e reads only the operations text) and old L2 ("vacancy rate" over-refers).
