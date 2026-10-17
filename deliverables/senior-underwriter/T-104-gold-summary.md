# T-104 gold summary, SUB-174 to SUB-205 (rewritten 2026-10-17 after the producer rebuild, D-107; @senior-underwriter)

Written by hand from the rebuilt simulation/inbox/SUB-174 to SUB-205 (both scanned loss runs and the scanned applications rendered and read; typed PDFs and xlsx read with pdfplumber and openpyxl) and the written rules only: proposal-P-055.md criteria 1-4, carrier-match.md, operations-gold-rule.md (D-102 and the v5 checklist), carrier-loss-run-formats.md, required-fields.md. No pipeline, scope detector, extraction, OCR script or scorer was run or read. Not committed. Fictional. Every card has a `- Scope:` line and an `- Operations items:` line; empty fields say `not in documents`; no route is "hold".

What changed in the first rebuild: 174 and 175 loss-run scans, 182-187 loss runs and several applications now carry Carrier A, B or C layouts (and Carrier A, B, C expiring carriers); SUB-185 is a new business (Sierra Vista Apartments, 6 units); SUB-199 is a new business (Brazos Valley Plumbing Supply, 2 locations). 188-198 were re-checked against their documents and match their earlier gold (no change except 199).

| File | Business | Scope label | Gold route (suggested market) | Status |
|---|---|---|---|---|
| SUB-174 | executive office suites | in scope (boundary: Carrier A scan run) | senior_referral (carrier_a) | complete — review pending |
| SUB-175 | bakery and cafe | in scope (boundary: Carrier B image-only PDF run) | senior_referral (carrier_b) R10 | complete — review pending |
| SUB-176 | pet grooming | in scope (boundary: Spanish email) | senior_referral (carrier_a) R17 | incomplete |
| SUB-177 | tortilleria | in scope (boundary: Spanish name, 1-row schedule) | senior_referral (carrier_b) R10 | incomplete |
| SUB-178 | auto glass repair | in scope (boundary: 1-row schedule) | no_match R8 | incomplete |
| SUB-179 | office (insurance/tax name) | in scope (boundary: PO box mailing, 1-row schedule) | carrier_a (R14, R17 pass) | complete |
| SUB-180 | pottery studio | in scope (boundary: prior address) | senior_referral (carrier_a) R17 | incomplete |
| SUB-181 | tire and lube | in scope (1-row schedule) | no_match R8 | incomplete |
| SUB-182 | sub shop and deli | in scope | senior_referral (carrier_b) R10 | complete |
| SUB-183 | self storage | in scope (1-row xlsx schedule) | senior_referral (none) R16 | complete |
| SUB-184 | insurance office | in scope (typed PDF app) | carrier_a (R14, R17 pass) | complete |
| SUB-185 | 6-unit apartments | in scope (boundary: 1-row schedule) | senior_referral (carrier_c) R12 | complete |
| SUB-186 | restaurant with bar | in scope (typed PDF app) | senior_referral (none) R2 | complete |
| SUB-187 | 7-unit apartments | in scope | senior_referral (carrier_c) R12 | complete |
| SUB-188 | optical retail and exams | out of scope: 1 | none, manual intake | manual intake |
| SUB-189 | feed and seed | out of scope: 1 | none, manual intake | manual intake |
| SUB-190 | dental, 2 offices | out of scope: 1, 2 | none, manual intake | manual intake |
| SUB-191 | sign shop, 2 locations | out of scope: 2 | none, manual intake | manual intake |
| SUB-192 | hardware and lumber | out of scope: 2 | none, manual intake | manual intake |
| SUB-193 | auto body (Spanish app) | out of scope: 3 | none, manual intake | manual intake |
| SUB-194 | bakery, 2 locations (Spanish) | out of scope: 2, 3 | none, manual intake | manual intake |
| SUB-195 | auto repair (scanned Spanish app) | out of scope: 1, 3 | none, manual intake | manual intake |
| SUB-196 | grocery (Spanish typed PDF) | out of scope: 3 | none, manual intake | manual intake |
| SUB-197 | boutique, email only | out of scope: 4 | none, manual intake | manual intake |
| SUB-198 | restaurant, email only | out of scope: 4 | none, manual intake | manual intake |
| SUB-199 | plumbing supply, 2 locations | out of scope: 2 | none, manual intake | manual intake |
| SUB-200 | roofing contractor | in scope | senior_referral (carrier_b) R11 | incomplete |
| SUB-201 | nightclub and lounge | in scope | no_match R1 | incomplete |
| SUB-202 | physical therapy | in scope (1-row schedule) | senior_referral (none) W2b | incomplete |
| SUB-203 | coffee roaster and cafe | in scope (1-row schedule) | senior_referral (carrier_b) R10 | incomplete |
| SUB-204 | pool and patio supply | in scope | senior_referral (none) W2a | incomplete |
| SUB-205 | seafood market and boil | in scope | senior_referral (none) W2a | incomplete |

## Counts
- Scope: 20 in scope (SUB-174 to 187, 200 to 205), 12 out of scope (SUB-188 to 199).
- Out of scope per criterion (a file counts under each): criterion 1 scanned application 4 (188, 189, 190, 195); criterion 2 multi-location 5 (190, 191, 192, 194, 199); criterion 3 non-English 4 (193, 194, 195, 196); criterion 4 application not identifiable 2 (197, 198).
- Files matching two criteria: 3 (190 = 1+2, 194 = 2+3, 195 = 1+3). Counted once in the 12.
- Criterion-4 files: 2 (197, 198, both email-only, labelled out of scope).
- Near-pass forms: criterion 1 clean scan (188); criterion 2 only on the application (191), only in the schedule (192) or both (199); criterion 3 Spanish application with an English email (193, 196).
- In-scope boundary cases: scanned or image-only carrier loss run with a typed application 2 (174, 175); Spanish email or Spanish business name beside an English application 2 (176, 177); one-row schedule 8 (177, 178, 179, 181, 183, 185, 202, 203); mailing or prior address 2 (179, 180); typed PDF applications 2 (184, 186).
- In-scope status (20): complete 7 (179, 182, 183, 184, 185, 186, 187), complete — review pending 2 (174, 175), incomplete 11 (176, 177, 178, 180, 181, 200, 201, 202, 203, 204, 205). Out of scope: manual intake 12.
- In-scope routes (20): carrier_a 2 (179, 184), senior_referral 15, no_match 3 (178, 181, 201), hold 0. Suggested market on the 15 senior_referral: carrier_a 3 (174, 176, 180), carrier_b 5 (175, 177, 182, 200, 203), carrier_c 2 (185, 187), none 5 (183, 186, 202, 204, 205). Out of scope: no route (12).
- Recognised carrier-format loss runs (A, B or C layout): 9 in scope (174, 175 scans; 179, 182, 183, 184, 185, 186, 187 typed). The rest are Redbud, Brazos or Caprock tables or owner letters ("not a recognised carrier loss run": 177, 178, 181, 200-204; owner letter: 176, 180) or missing (205).

## Files whose scope is unclear under P-055's written criteria
- None. SUB-199 is now clear (schedule plus a location list). Judgment points: SUB-192 schedule row 2 has no street number ("Hwy 57 lumber yard, 0.4 mi west") and is counted as an address row; SUB-188 is a clean scan and is out under criterion 1 as the near-pass test.

## Route and status judgments to confirm (not scope)
- Second rebuild (D-107): documents changed in 175, 177, 179, 182, 184, 185, 186, 187, 203; the other 23 folders were diffed and match. SUB-184 is now Keller Insurance Services PA (an office, no longer chiropractic) and routes carrier_a; SUB-179 now says "Office. Clients by appointment. No food, no alcohol." with a Carrier A run and routes carrier_a. Both are the direct-route files; the earlier set had none.
- Restaurant files now state a hood inspection date (175, 177, 182, 186, 203), so the restaurant hold is gone. 177 and 203 stay incomplete for other reasons (non-carrier loss run; 203 also a square-footage conflict, 3200 vs 2850).
- SUB-185 and SUB-187 now say 2 stories (the stories conflict is gone); 185 also has a one-row schedule and is sprinklered. Both complete, suggested market carrier_c.
- SUB-182: the operations sentence "no fryer, no hood suppression unknown" is still garbled, but the application gives the hood inspection date 2026-07-28. I read it as no conflict and the file complete. If the pipeline treats the garbled sentence as unresolved, it would hold.
- SUB-174: the email says "with Redbud for years" while the application and the run say Carrier A. I recorded it as a side remark, not a field conflict, so the file is complete — review pending (Carrier A scan). If the pipeline treats the prior carrier as a conflict it would hold.
- Carrier A direct routes (179, 184) depend on the business name being ignored ("Tax & Accounting", "Insurance Services") and on R17 reading only the operations text. SUB-174: "office" appears only in the line of business or name, not in the operations text; if the match reads only operations the route may be R8 no_match. I gave senior_referral with Carrier A suggested.
- SUB-176 and SUB-180: "retail" is the only R14 word in a pet grooming and a pottery studio; R8 no_match is the alternative.
- SUB-177: R10 (cooking equipment) vs R16 (manufacturing plus retail). SUB-203: R10 vs R7 (cafe plus wholesale). SUB-178: R8 vs R11 (glass work as a glazier trade).
- SUB-188: "optical dispensary" contains the W1 word "dispensary"; any rule read of the text would call it a prohibited class wrongly (it is manual intake anyway).
- Other conflicts and gaps recorded in the cards: SUB-190, 192, 194 application-vs-schedule TIV; SUB-204 sales (1100000 vs 940000 by phone); SUB-180 five-year letter for a 3-year business; SUB-202 year built missing.
