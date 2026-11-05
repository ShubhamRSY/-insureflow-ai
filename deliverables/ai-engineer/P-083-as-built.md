> **DROPPED 2026-11-05 (D-165).** Never merged; code reverted. Kept as the record of why: the second code review found address forms the "only address" check missed. B-525 stays open.

# P-083 as built (T-131, D-164, B-525) — scope-v8

## Rule
`scope._place_words` (A3) is unchanged and still runs first. When it reaches two places, `_one_highway_place(docs)` can overrule it (in scope) only when **all** of these hold across every document:
- every highway or Spur match ("4400 FM 1960", "12 State Highway 6", "800 I-35", "100 Spur 5") is read together with the street matches that start inside it ("4400 FM 1960 Rd", "35 Frontage Rd"); a street match that adds a digit past the highway ends the check (manual intake);
- every mention, with the words after the road up to the first comma or sentence end ("Rd W"), is written exactly the same way (case and spacing aside): "Rd" vs "Road", W vs E, or 1960 vs 1961 is manual intake;
- every city written after a mention ("…, Houston") is the same city;
- outside those mentions, no text in any document looks like an address: a street-type word (St, Rd, Ave, Street, Road, Suite, Box, FM, RM, RR, CR, SH, US, I-35 …, even run together as "WacoBox", "StNote"), or a number followed by a capitalised word ("9 Oak", "12A Main"). Mailing, prior, agent and landlord addresses count too.

Otherwise the v7 result stands. Sheets (`_addresses`), numbered labels and application premises lists (`_codes`) are untouched.

## Evidence (deliverables/ai-engineer/evals/T-131/)
- (a)/(b) self-check in `scope.py`: five highway premises are in scope alone; each stays manual intake with any of 22 second-address shapes added (code-review shapes included: other direction or city, RM roads, Post Office Box / Box / RR Box, 12A Main St, One Main Street, 9 Oak, glued text).
- (c) `scope-v7-vs-v8-sweep.json`: 380 folders, 380 identical; **newly in scope: none** (no existing file has the B-525 shape); newly manual intake: none. Dev 12 unchanged.
- (d) SUB-475, SUB-533, 534, 535, 536, 537 and DEV-06/07/12 (two highways): manual intake.
- (e) `diff-v7-v8.py` → `diff-v7-v8.txt`: 201,408 generated cases; v7 fires and v8 does not in 3,001; **0** of those name anything but one highway premises.
- tests/pipeline 94 passed (fingerprint re-pinned for scope-v8); pyright 31 → 31. Quick set not re-run: the change is scope-only and the sweep shows every folder's scope result unchanged (same basis as the T-130 H1 fix).
- What's new line; screenshot `deliverables/software-engineer/screenshots/T-131-P-083-whats-new.png` (temp copy, D-069).
