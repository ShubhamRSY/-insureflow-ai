# P-084 as built (T-132, D-165) — scope-v8, stricter only

## Rule
`scope._place_words` A3 is now `_second_address(docs, ()) or _second_address(docs, EXTRA_ADDRESS)`. The first call is the v7 code unchanged, so v8 fires wherever v7 fires. The second pass adds new address forms only where no other match covers the text (longest first):
- **Any letter case** (`STREET_ANY_CASE`): all capitals ("1200 ELM DR, WACO") or all lower case ("9 oak way, Waco"); a comma and a city must follow; words such as lane, hour, mile, spaces, vans, near, off are never street names.
- **Texas route codes** (`ROUTE_ANY`, upper case): IH, SL, FM, RM, RR, CR, SH, US, LOOP, SPUR, HWY, TX-n, I-n, with an optional "Frontage/Service Rd"; never after a date or claim number ("03/15/2022 TX 2,500").
- **Mailboxes** (`MAILBOX`): "PMB 123"; "General Delivery, <city> TX".
- **Spanish format** (`SPANISH_ADDRESS`): Calle / Avenida / Av. / Carretera / Camino / Privada / Callejón / Prolongación + capitalised name + number, then a comma and a city ("Calle Roble 12, Laredo", "Av. 16 de Septiembre 1234, Laredo"); "Av." does not end a sentence in this pass.
- A role label ("Mailing address:") hides a new-form match that starts its value, and a PMB anywhere in it; the line-above label works as in v7.
- In this pass, road aliases count as one road (IH 35 = I-35, TX-71 = SH 71, SL 1604 = Loop 1604, Avenida = Av.).
- City-only mentions are left to the model location count (D-165). `prepare.py` still uses the v7 STREET_WORDS / HIGHWAY.

## Evidence (deliverables/ai-engineer/evals/T-132/)
- Sweep `scope-v7-vs-v8-sweep.json`: 380 folders, 380 identical. **Newly in scope: none. Newly manual intake: none** (no inbox file has the new shapes). Dev 12 unchanged: DEV-01–05 near-misses in scope, DEV-06–12 multi-location (incl. 475, 533 shapes, two highways) manual intake. SUB-475, SUB-533–537 manual intake.
- Generated comparison `diff-v7-v8.py` → `diff-v7-v8.txt`: 200,924 cases; v7 fires and v8 does not (place words or detect): **0**; v8 adds a hit: 37,753.
- Self-check (`python scope.py`): every D-165 example form is caught as a second address; the one-place texts from both review passes (mailing labels, PMB after a street, loss-run rows with TX, capitals without a comma, prose with numbers, AV/Camino business names, General Delivery as a service, road aliases) stay in scope.
- Two code-review passes (2026-11-05): no loosening; all near-miss findings fixed and added to the self-check. Not changed: the second pass re-reads the documents (about 2–3× the A3 time on very long lines).
- tests/pipeline 94 passed (fingerprint re-pinned for scope-v8); pyright 31 → 31.
- What's new line; screenshot `deliverables/software-engineer/screenshots/T-132-P-084-whats-new.png` (temp copy, D-069).
- Quick set (temp copy, 17 paced live calls, run 20261105T001930-81236): 17 ok, 0 failed (one Groq 503 retried and recovered); every band identical to T-130 `quick17-p082.json` (the only difference is the retry record); silent 26/138 = 0.188, automation 0.565 (`evals/T-132/quick17-p084.json`).

## @model-risk check-T-132: APPROVE (no High)
- M1 fixed: the What's new line now says the any-case and Spanish forms need a comma and a city after them. Known limit (B-527): "1200 ELM DR WACO TX", the two-line postal layout, "9 oak st waco tx" and "Calle Roble 12 Laredo" are not caught (v7 did not catch them either; the model location count is the backstop).
- L1–L4, L7 → B-528. L5/L6: inventory C-4 now says scope-v8 = P-084 (D-165) only; the dropped P-083 build never shipped.
