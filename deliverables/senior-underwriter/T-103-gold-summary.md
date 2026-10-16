# T-103 gold summary, SUB-154 to SUB-173 (2026-10-16, @senior-underwriter)

Written by hand from simulation/inbox/SUB-154 to SUB-173 (scans and the image-only PDF rendered and read) and the written rules only: carrier-match.md R1-R17, W1, W2; operations-gold-rule.md; M5. No pipeline, extraction, scorer, workbench or code was run or read. Not committed. Fictional.

| File | Business | Loss run | Gold route (suggested market) | Expected status |
|---|---|---|---|---|
| SUB-154 | office | Carrier A typed PDF | carrier_a (R14, R17 pass) | complete |
| SUB-155 | dry retail storefront | Carrier A typed .md, no-claims line | carrier_a (R14, R17 pass) | complete |
| SUB-156 | breakfast/lunch restaurant, no alcohol | Carrier B typed PDF | senior_referral (carrier_b), R10 | complete |
| SUB-157 | restaurant and bar, full liquor | Carrier B typed .md | senior_referral (none), R2 | complete |
| SUB-158 | apartments, sprinklered, 16 units | Carrier C typed PDF | senior_referral (carrier_c), R12 | complete |
| SUB-159 | bakery cafe | Carrier B JPG greyscale | senior_referral (carrier_b), R10 | complete — review pending |
| SUB-160 | apartments, unsprinklered, 8 units | Carrier C JPG colour, rotated | senior_referral (carrier_c), R12 | complete — review pending |
| SUB-161 | light wholesale, goods stated non-hazardous | Carrier A image-only PDF | senior_referral (carrier_a), R17 | complete — review pending |
| SUB-162 | office suite | owner letter | carrier_a (R14, R17 pass), hold: carrier run missing | incomplete |
| SUB-163 | Mexican restaurant (Spanish), beer and wine | Spanish owner letter | senior_referral (carrier_b), R10, hold: carrier run missing | incomplete |
| SUB-164 | roofing contractor | applicant note under copied Carrier A header ("Fwd:", "> ") | senior_referral (carrier_b), R11, hold: carrier run missing | incomplete |
| SUB-165 | fireworks retail | agency summary | no_match, R1 (W1) | incomplete |
| SUB-166 | office building, TIV 5.85M | JPG: Carrier B header plus insured's note, no table | senior_referral (none), R13 | incomplete |
| SUB-167 | apartments, sprinklers blank | Carrier C typed, no valued line | hold, R12 | incomplete |
| SUB-168 | email only, operations not stated | none | hold, R5 | incomplete |
| SUB-169 | laundromat (Spanish email only) | none | no_match, R8, hold: TIV missing | incomplete |
| SUB-170 | restaurant, 2 locations, scanned app, loc 2 value conflict | none | senior_referral (carrier_b), R10, hold: conflict and runs | incomplete |
| SUB-171 | resend of SUB-157 | none | senior_referral (none), R2 | incomplete |
| SUB-172 | apartments, 3 locations, sprinklered | none | senior_referral (carrier_c), R12, hold: runs not requested | incomplete |
| SUB-173 | taqueria, cuisine words only | none | no_match, R8 (D-078), hold: runs missing | incomplete |

## Counts
- Route (after the producer's wording change to 154, 155, 162): senior_referral 12, carrier_a 3 (154, 155, 162), no_match 3 (165, 169, 173), hold 2 (167, 168), carrier_b 0, carrier_c 0. 162 is carrier_a with a hold on the carrier run.
- Suggested market on the 12 senior_referral files: carrier_a 1 (161), carrier_b 5 (156, 159, 163, 164, 170), carrier_c 3 (158, 160, 172), none 3 (157, 166, 171).
- Status: complete 5 (154-158), complete — review pending 3 (159-161), incomplete 12 (162-173). This is the planned 8 gold-complete and 12 gold-incomplete.
- Loss runs: 8 carrier-format (A 154, 155, 161; B 156, 157, 159; C 158, 160), 6 non-carrier (162, 163, 164, 165, 166, 167), 6 none (168-173). Formats: 3 typed PDF (154, 156, 158), 2 typed .md (155, 157), 2 JPG (159, 160), 1 image-only PDF (161). One typed run uses the no-claims line (155). No banner line, no xlsx.

## T-103 criteria the files do not meet
1. "Every route appears in gold": now met for the addendum's version (carrier_a, senior_referral, no_match, hold). carrier_a has 3 gold files (154, 155, 162); only 154 and 155 are complete, 162 carries a hold. carrier_b and carrier_c have no direct gold: under R10, R11, R12 they are suggested markets only, which the addendum accepts. Limit: 2 complete direct-route files (154, 155) say little about direct-route precision (reported, no files added).
2. "Files 1-5 have no other planned gap": met. Files 154-158 are complete with no conflict.
3. The map of the plan to files is: 1=154, 2=155, 3=156, 4=157, 5=158, 6=159, 7=160, 8=161, 9=162, 10=163, 11=164, 12=165, 13=166, 14=167, 15=168, 16=169, 17=170, 18=171, 19=172, 20=173. File 13 (166) is the JPG applicant note, as the addendum asked; file 11 (164) states a TIV (240000).

## Ambiguous documents (a person or @head-of-underwriting should confirm)
- SUB-161: the application names "flammable liquids" and "pesticides" in a negation ("no ..."). If the match reads W2a words without dropping the negation, the route is senior_referral with no suggested market, not Carrier A. The route is the same either way; only the suggested market differs. Not helped by the scan.
- SUB-173: "Line of business: retail food" contains "retail" (an R14 Retail word) and no restaurant word. If that line is read, the match may read retail plus "food" instead of R8. I used the Operations line only: cuisine words, no cooking stated, so no_match (R8, D-078). A real underwriter would treat a taqueria as cooking occupancy (the recommendation says so).
- SUB-167: R12 says sprinkler missing is a hold. I did not give a provisional senior_referral. If the plan wanted one, change the route line to senior_referral, suggested market carrier_c — hold.
- SUB-166: "No retail, no food" in operations: "retail" is an allow-list word, so R16 (two groups) may fire, but R13 gives senior_referral either way. Gold TIV is the building value; the scan has no claims table, so it is not a recognised run.
- SUB-156: the email says the grease fire was "last winter"; the run says 2024-12-03. Recorded as no conflict (vague, not a different figure).
- SUB-154, SUB-155, SUB-162: the three business names still carry words (Tax, Candle, Bookkeeping); read as not operations text, per the coordinator. If the match reads the name, they go to senior_referral.
- SUB-155: the email says "A loss run is attached, they never had a claim". M1's "never" rule (look-again L4) may exclude Carrier A from the market list. This affects the market confirm, not the route.
- SUB-170: the TIV gold is the application total (1,040,000 + 465,000); the schedule gives 546,000 for loc 2. The conflict field carries both.
- SUB-164, SUB-166: both carry an owner's note under a copied carrier header. SUB-164 states a valued-as-of date, so the P-044 gate is reached; SUB-166 has no claims table or no-claims line.
- SUB-171 carries the SUB-157 header ("Submission: SUB-157"), like SUB-146 and SUB-141.
