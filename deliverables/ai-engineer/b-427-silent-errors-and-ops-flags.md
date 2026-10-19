# B-427: the 9 dev silent errors and the operations flag drop (5/16 → 1/41)

Author: @ai-engineer-assistant (orchestrator session). Dev data only; not a hold-out; not a production approval (T-027 veto stands).
Method: scorer v5 read-only re-score of SUB-154–173 from the saved B-415 replies, 0 model calls (`HOLDOUT_RESCORE=1`, temp cache copy in `LLM_CACHE_DIR`, temp `HOLDOUT_OUT`). Reproduced the B-415 row exactly (silent 9/180, automation 64.4%). The old-reply column was reproduced with `llm_extract.PROMPT_VERSION` set to the pre-P-059 `b025802c0dfa` in a temp script; `llm_extract._post` denied so no call can happen. Worktree git status clean (D-069).

## 1. The 9 silent errors — all are the `operations` field, all are (a)

All nine are `operations`: SUB-156, 157, 158, 159, 160, 165, 167, 171, 173 (9 of 20 files, 9 of 180 scored values). Silent = a value is shown, the scorer counts it wrong, and nothing flags it.

Dev gold SUB-154–173 has **no `- Operations items:` line**, so scorer v5 scores these files by the v4 word rule: *every gold word must appear in the answer*. That is the pre-D-103 convention. Under the current rules (`operations-gold-rule.md`, "Operations checklist", D-103 item 3) an items line is written and **connectors ("under") and business words the documents do not use ("taqueria", "apartment building") are not items**. Every answer below carries every item the documents state; only the gold's own wording differs.

| SUB | gold word(s) not in the answer | documents say | why the scorer calls it wrong | why no flag fired |
|---|---|---|---|---|
| SUB-156 | `under` | "Flat-top, 2 fryers, 4-burner range, Type I hood with UL 300 suppression" | connector, required by the v4 word rule, not an item | check correctly found no rule item missing |
| SUB-157 | `under` | "…pizza oven. Type I hood with UL 300 system, serviced 2026-08." | connector | same |
| SUB-159 | `under` | "Deck oven, 2 convection ovens, 4-burner range, flat-top, Type I hood with UL 300" | connector | same |
| SUB-171 | `under` | (same shape as SUB-157, resend) | connector | same |
| SUB-158 | `apartment`, `building`, `operations` | Line of business "habitational"; Operations "Residential apartments, 16 units in two two-story buildings, long-term leases. Occupancy 93 percent."; Cooking "None (tenant electric ranges only)" | gold says "Apartment building … no cooking operations"; the documents say "Residential apartments" and "None" | check correctly found no rule item missing |
| SUB-160 | `apartment`, `building`, `operations` | same shape, 8 units, occupancy 88 percent | same | same |
| SUB-167 | `apartment`, `building`, `operations` | same shape, 24 units, occupancy 90 percent | same | same |
| SUB-173 | `taqueria` | Line of business "retail food"; Operations "Counter service. Tacos, burritos, quesadillas and agua fresca…" | gold says "Counter service taqueria"; the documents never say "taqueria" | check correctly found no rule item missing |
| SUB-165 | `june`, `july` | Operations "…storefront and seasonal tent." ; the months are in `email.md` ("seasonal tent June and July") | gold adds "(June and July)"; months are not a required item or on the closed list ("Anything not on this list is not required") | check correctly found no rule item missing |

Concrete answers (shown values, from the new replies):

- SUB-156 `Restaurant. Breakfast and lunch counter service, 48 seats, dine-in and takeout. No alcohol of any kind. Flat-top, 2 fryers, 4-burner range, Type I hood with UL 300 suppression, hood cleaned 2026-07` — gold: `Restaurant, no alcohol of any kind, 48 seats, flat-top, 2 fryers and 4-burner range under Type I hood with UL 300 suppression, breakfast and lunch counter service, dine-in and takeout`.
- SUB-158 `Residential apartments, 16 units in two two-story buildings, long-term leases. Occupancy 93 percent. No cooking (tenant electric ranges only).` — gold: `Apartment building, 16 units in two two-story buildings, long-term leases, no cooking operations (tenant electric ranges only)`.
- SUB-165 `Retail sale of consumer fireworks (aerial, ground and cakes), storefront and seasonal tent. Fireworks inventory stored on premises, including in a trailer on the lot. No cooking.` — gold: `…storefront and seasonal tent (June and July)…`.
- SUB-173 `Counter service. Tacos, burritos, quesadillas and agua fresca, 35 seats, dine-in and takeout. No liquor.` — gold: `Counter service taqueria (tacos, burritos, quesadillas, agua fresca), no liquor, 35 seats, dine-in and takeout`.

**Class: 9 of 9 are (a) dev gold out of date with the current rules** (gold written before the D-102/D-103 operations-items convention, so the v4-words fallback requires connectors, reworded business words and non-listed details). **0 are (b) real check gaps**: in every case the P-059 whole-document check (`ops_missing_all`) correctly found nothing missing.

This matches the rule's own examples: `operations-gold-rule.md` names exactly "under", "taqueria" and "apartment building" as things that must not be items.

## 2. The operations flag drop (5/16 → 1/41)

The flag is `prepare.check_operations`: operations gets `needs_review` with "operations may be missing: …" when a labeled line or rule item in the cited document is absent from the answer.

| Set | Flagged files | Reason |
|---|---|---|
| Old replies, the 16 files with an old reply (SUB-027 + 15 of SUB-154–173 that call) | **5 of 16**: SUB-154, 161, 162, 164, 165 | "operations may be missing: no cooking" |
| New replies, same 16 | **0 of 16** | — |
| New replies, all 41 files that call (quick 5 + dev 36) | **1 of 41**: SUB-134 | "operations may be missing: on-site processing" |

Cause of the drop: the old prompt answered with the "Operations:" line only, so the extractor dropped the **"Cooking operations: None"** statement, and the check fired on each such file. P-059 now carries the labeled cooking/hood/LOB lines: every old-flag file's answer gained `No cooking.` and the flag cleared. Example (SUB-162): old `Office suite. Clients by appointment. No inventory.` → new `… No inventory. No cooking.`

The one remaining flag, SUB-134, is a **true positive, safe direction**: the Line of business line says "light manufacturing" and the answer says "Glass cutting, tempering and framing for commercial storefronts…" without the word manufacturing/processing, so the check asks for a human look. Flagging is the conservative side; it is not a gap.

Note: the B-415 report's new-reply column read "1 of 16". Measured, the 16-file column is **0 of 16**; the 1 is SUB-134, which is outside that 16 and is the only flag across all 41 new files. The 1/41 figure stands; the "of 16" label in that cell is a wording slip now corrected here.

## 3. Conclusion for this session

No real gap in operations, so **no P-### is needed** and step 3 (build T-105) may proceed. The operations silent errors are dev-gold-age artifacts; the check behaved correctly in all 9. The dev gold for SUB-154–173 is not rewritten (D-020: published data is never rewritten); the lesson goes to the next gold set, which T-105 writes under the current checklist convention.
