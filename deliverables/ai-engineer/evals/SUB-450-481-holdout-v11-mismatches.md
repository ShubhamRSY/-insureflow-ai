# T-120 mismatches (v11), SUB-450 to SUB-481 — read only, nothing fixed

Read back from a temp copy of the run's cache through `prepare.process_submission` with the model call disabled (no call, nothing written in the repo; replayed status matched the scored status on 32/32). Not a re-score.

| SUB | Mark | Gold | System | Class |
|---|---|---|---|---|
| 475 | leak; detection recall (crit 2) | out of scope, multi-location ("two stores"; Corpus and Rockport) | in scope (scope-v4 found no reason), extracted, status complete — review pending; operations "Bicycle retail and repair, two stores, no cooking" | **safety: scope detector misses a second location stated in words + the email** |
| 451 | route | carrier_a (R14/R17) | senior_referral; operations answer "Clothing retail storefront, racks and fitting rooms, open 10 to 8, no cooking" carries email words ("racks", "fitting", "rooms", "open") that are not R17 allow-list words | safe direction (R17 strictness on model-added words) |
| 458 | operations; route | business_type=office; senior_referral | operations empty: the value was rejected ("value is not in the cited text (translated or reworded)") and held as an open `operations` conflict, plus the planted `suite_count` conflict; route hold | safe (flagged, not silent; C2 counts it as not silent) |
| 461 | conflict (excluded, D-136) | open cooking conflict | open cooking conflict raised and held | v11-unmeasurable (no figure) |
| 463 | conflict (excluded, D-136) | open cooking conflict | open cooking conflict raised and held; operations names the fryer | v11-unmeasurable (no figure) |
| 450–453, 457, 464–467 | status | complete | complete — review pending | by design (P-076, D-134); not an error |

Notes for @model-risk (no action taken):
- 10 of 20 operations rows carry the reason "value is not in the cited text (translated or reworded)" while the value is a v11 hit. The C2 counter treats it as a specific reason (D-136), so it never makes a miss silent; it is generic, not item-naming. SUB-458 is the only file where it blanked the value.
- M4 (B-484): the direct Carrier A files were built with allow-list operations lines, so 3/4 measures copying, not occupancy reading.
- M5 (B-484): SUB-464 email "kitchen" — no effect: SUB-464 operations hit.
