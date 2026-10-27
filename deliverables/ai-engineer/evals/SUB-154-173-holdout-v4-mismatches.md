# T-103 SUB-154–173: gold vs pipeline, as-is

- Source: the scored live run's saved replies (run 20261016T151351-65695), replayed from a temp copy of the cache with the model call blocked: 0 model calls, nothing in the repo written by the replay. Commit 2c6b2d9 (pipeline 3557e4a), gold 33e399a.
- Data only, no reading of it. Scores are in SUB-154-173-holdout-v4.md/.json; that file governs where they differ.
- Route lines: gold route, route scored (provisional route of a held file), workbench.match route and provisional, pipeline status vs gold status.
- Loss-run lines: one per file: the value the pipeline kept, needs_review, its reason, and the gold "Expected loss run".
- Mismatch lines: every field, conflict and status mark that is not a hit, with the pipeline value and the gold line (cut at 140 characters).

```
## Routes
SUB-154 gold carrier_a | used carrier_a | match.route carrier_a prov None | status complete gold-status complete | hit
SUB-155 gold carrier_a | used carrier_a | match.route carrier_a prov None | status complete gold-status complete | hit
SUB-156 gold senior_referral | used senior_referral | match.route senior_referral prov None | status complete gold-status complete | hit
SUB-157 gold senior_referral | used senior_referral | match.route senior_referral prov None | status complete gold-status complete | hit
SUB-158 gold senior_referral | used senior_referral | match.route senior_referral prov None | status complete — review pending gold-status complete | hit
SUB-159 gold senior_referral | used senior_referral | match.route hold prov senior_referral | status incomplete gold-status complete | hit
SUB-160 gold senior_referral | used senior_referral | match.route hold prov senior_referral | status incomplete gold-status complete | hit
SUB-161 gold senior_referral | used senior_referral | match.route hold prov senior_referral | status incomplete gold-status complete | hit
SUB-162 gold carrier_a | used carrier_a | match.route hold prov carrier_a | status incomplete gold-status incomplete | hit
SUB-163 gold senior_referral | used hold | match.route hold prov None | status incomplete gold-status incomplete | miss
SUB-164 gold senior_referral | used senior_referral | match.route senior_referral prov None | status complete — review pending gold-status incomplete | hit
SUB-165 gold no_match | used no_match | match.route no_match prov None | status incomplete gold-status incomplete | hit
SUB-166 gold senior_referral | used senior_referral | match.route hold prov senior_referral | status incomplete gold-status incomplete | hit
SUB-167 gold hold | used senior_referral | match.route hold prov senior_referral | status incomplete gold-status incomplete | miss
SUB-168 gold hold | used hold | match.route hold prov None | status incomplete gold-status incomplete | hit
SUB-169 gold no_match | used senior_referral | match.route hold prov senior_referral | status incomplete gold-status incomplete | miss
SUB-170 gold senior_referral | used hold | match.route hold prov None | status incomplete gold-status incomplete | miss
SUB-171 gold senior_referral | used senior_referral | match.route hold prov senior_referral | status incomplete gold-status incomplete | hit
SUB-172 gold senior_referral | used senior_referral | match.route hold prov senior_referral | status incomplete gold-status incomplete | hit
SUB-173 gold no_match | used no_match | match.route hold prov no_match | status incomplete gold-status incomplete | hit
Counter({('senior_referral', 'senior_referral'): 10, ('carrier_a', 'carrier_a'): 3, ('senior_referral', 'hold'): 2, ('no_match', 'no_match'): 2, ('hold', 'senior_referral'): 1, ('hold', 'hold'): 1, ('no_match', 'senior_referral'): 1})
## Loss runs
SUB-154 value 2026-09-30 needs_review False reason  | gold: 2026-09-30 accepted | check hit
SUB-155 value 2026-09-30 needs_review False reason  | gold: 2026-09-30 accepted | check hit
SUB-156 value 2026-09-30 needs_review False reason  | gold: 2026-09-30 accepted | check hit
SUB-157 value 2026-09-30 needs_review False reason  | gold: 2026-09-30 accepted | check hit
SUB-158 value 2026-09-30 needs_review False reason  | gold: 2026-09-30 accepted | check hit
SUB-159 value None needs_review True reason  | gold: needs review — loss run from scan/spreadsheet: check it | check miss
SUB-160 value None needs_review True reason  | gold: needs review — loss run from scan/spreadsheet: check it | check miss
SUB-161 value None needs_review True reason  | gold: needs review — loss run from scan/spreadsheet: check it | check miss
SUB-162 value None needs_review True reason  | gold: missing — a no-known-loss letter is not a loss run (P-040) | check not_credited
SUB-163 value None needs_review True reason  | gold: missing — a no-known-loss letter is not a loss run (P-040) | check not_credited
SUB-164 value 2026-09-30 needs_review True reason loss run says it is not the carrier's own (loss-runs.md: "Losses are valued as of 2026-09-30 from our own books, not from A."); check it | gold: needs review — not a recognised carrier loss run | check miss
SUB-165 value None needs_review True reason  | gold: needs review — not a recognised carrier loss run | check not_credited
SUB-166 value None needs_review True reason  | gold: needs review — not a recognised carrier loss run | check not_credited
SUB-167 value None needs_review True reason loss run found but no valued-as-of date; ask the producer for a dated carrier loss run (loss-runs.md) | gold: missing — loss run found but no valued-as-of date; ask the producer for a dated carrier loss run | check not_credited
SUB-168 value None needs_review True reason  | gold: missing — no loss run provided | check not_credited
SUB-169 value None needs_review True reason  | gold: missing — no loss run provided | check not_credited
SUB-170 value None needs_review True reason  | gold: missing — no loss run provided | check not_credited
SUB-171 value None needs_review True reason  | gold: missing — no loss run provided | check not_credited
SUB-172 value None needs_review True reason  | gold: missing — no loss run provided | check not_credited
SUB-173 value None needs_review True reason  | gold: missing — no loss run provided | check not_credited
## Mismatches as-is
SUB-156 operations miss | pipeline: 'Restaurant. Breakfast and lunch counter service, 48 seats, dine-in and takeout. No alcohol of any kind. Cooking operations: Flat-top, 2 fry | gold: Restaurant, no alcohol of any kind, 48 seats, flat-top, 2 fryers and 4-burner range under Type I hood with UL 300 suppression, breakfast and
SUB-156 conflict miss | open: [] | gold: none (the email's 'last winter' is vague, not a different figure; the carrier run governs)
SUB-157 operations miss | pipeline: 'Restaurant and bar. Full liquor (TABC mixed beverage permit), 140 seats, live music Thursday to Sunday until midnight. Dinner service and w | gold: Restaurant and bar, full liquor (TABC mixed beverage permit), 140 seats, charbroiler, 2 fryers, flat-top, 8-burner range and pizza oven unde
SUB-158 operations miss | pipeline: 'Residential apartments, 16 units in two two-story buildings, long-term leases. Occupancy 93 percent. No cooking operations (tenant electric | gold: Apartment building, 16 units in two two-story buildings, long-term leases, no cooking operations (tenant electric ranges only)
SUB-158 status miss | pipeline: complete — review pending | None | gold: complete
SUB-159 operations miss | pipeline: 'Bakery and cafe. Pastries, sandwiches, coffee. 30 seats, dine-in and takeout. No alcohol sold. Deck oven, 2 convection ovens, 4-burner rang | gold: Bakery and cafe (pastries, sandwiches, coffee), no alcohol sold, 30 seats, deck oven, 2 convection ovens, 4-burner range and flat-top under 
SUB-159 loss_run_valued_through miss | pipeline: None | gold: valued through 2026-09-30, 1 claim, Carrier B run read from a scan
SUB-159 status miss | pipeline: incomplete | None | gold: complete
SUB-160 operations miss | pipeline: 'Residential apartments, 8 units in two two-story buildings, long-term leases. Occupancy 88 percent. No cooking operations (tenant electric  | gold: Apartment building, 8 units in two two-story buildings, long-term leases, no cooking operations (tenant electric ranges only)
SUB-160 loss_run_valued_through miss | pipeline: None | gold: valued through 2026-09-30, 1 claim, Carrier C run read from a rotated scan
SUB-160 status miss | pipeline: incomplete | None | gold: complete
SUB-161 loss_run_valued_through miss | pipeline: None | gold: valued through 2026-09-30, 1 claim, Carrier A run read from an image-only PDF
SUB-161 status miss | pipeline: incomplete | None | gold: complete
SUB-162 loss_run_valued_through not_credited | pipeline: None | gold: missing, only an owner's signed no-claims letter (not a loss run)
SUB-163 operations miss | pipeline: None | gold: Mexican restaurant, beer and wine only, no bar, 60 seats, comal, grill, 2 fryers and 6-burner range under Type I hood with UL 300, table ser
SUB-163 loss_run_valued_through not_credited | pipeline: None | gold: missing, only an owner's Spanish no-claims letter (not a loss run)
SUB-164 loss_run_valued_through miss | pipeline: '2026-09-30' | gold: missing, applicant's own note under a copied Carrier A header (not a carrier loss run)
SUB-165 operations miss | pipeline: 'Retail sale of consumer fireworks (aerial, ground and cakes), storefront and seasonal tent. Fireworks inventory stored on premises, includi | gold: Retail sale of consumer fireworks (aerial, ground and cakes), storefront and seasonal tent (June and July), fireworks inventory stored on pr
SUB-165 loss_run_valued_through not_credited | pipeline: None | gold: missing, agency summary only, not a carrier loss run
SUB-166 loss_run_valued_through not_credited | pipeline: None | gold: missing, scan of a Carrier B header with the insured's own note and no carrier claims table or no-claims line (not a carrier loss run)
SUB-167 operations miss | pipeline: 'Residential apartments, 24 units in three two-story buildings, long-term leases. Occupancy 90 percent. No cooking operations (tenant electr | gold: Apartment building, 24 units in three two-story buildings, long-term leases, no cooking operations (tenant electric ranges only)
SUB-167 loss_run_valued_through not_credited | pipeline: None | gold: missing, Carrier C layout with no valued-as-of date, term to 2026-07-01
SUB-168 premises_address miss | pipeline: '800 Eighth St Wichita Falls 76301' | gold: 800 Eighth St, Wichita Falls, TX 76301
SUB-168 effective_date miss | pipeline: None | gold: 2027-04-01
SUB-168 sales_or_payroll miss | pipeline: None | gold: missing, not given
SUB-168 tiv_building miss | pipeline: None | gold: missing, no values given
SUB-168 construction miss | pipeline: None | gold: missing, not given
SUB-168 year_built miss | pipeline: None | gold: missing, not given
SUB-168 loss_run_valued_through not_credited | pipeline: None | gold: missing, none provided (from Carrier B, not yet sent)
SUB-169 premises_address miss | pipeline: None | gold: Pharr, TX (street address not given)
SUB-169 effective_date miss | pipeline: None | gold: 2027-05-01
SUB-169 operations miss | pipeline: 'Self-service laundry with 14 washers and 8 gas dryers; customers wash their own clothes; no commercial ironing; no delivery service' | gold: Self-service laundromat, 14 washers and 8 gas dryers, customers wash their own clothes, no commercial pressing, no delivery service
SUB-169 sales_or_payroll miss | pipeline: None | gold: missing, not given
SUB-169 tiv_building miss | pipeline: None | gold: missing, no values given
SUB-169 construction miss | pipeline: None | gold: missing, not given
SUB-169 year_built miss | pipeline: None | gold: missing, not given
SUB-169 loss_run_valued_through not_credited | pipeline: None | gold: missing, none provided
SUB-170 named_insured miss | pipeline: None | gold: Bluebonnet Kitchen Co LLC
SUB-170 premises_address miss | pipeline: None | gold: 4808 Slide Rd, Lubbock, TX 79414
SUB-170 effective_date miss | pipeline: None | gold: 2027-03-01
SUB-170 operations miss | pipeline: None | gold: Restaurant, 2 locations, burgers, chicken and breakfast, beer and wine only (no liquor license), flat-top, 2 fryers, charbroiler and 8-burne
SUB-170 sales_or_payroll miss | pipeline: None | gold: 3300000
SUB-170 tiv_building miss | pipeline: None | gold: 1505000
SUB-170 construction miss | pipeline: None | gold: Masonry / Metal
SUB-170 year_built miss | pipeline: None | gold: 2004 / 1998
SUB-170 loss_run_valued_through not_credited | pipeline: None | gold: missing, none provided (Carrier B, slow to send)
SUB-170 conflict miss | open: [{"field": "construction", "values": [{"value": "Masonry", "source": "application.jpg", "start": 749, "end": 765, "quote": "Masonry {loc ape", "needs_review": false, "reason": null, "confidence": 0.9}, {"value": "Metal", "source": "application.jpg", "start": 766, "end": 779, "quote": "metal {Loc 2)" | gold: building value at location 2, both 465000 (application) and 546000 (schedule); total 1505000 vs 1586000
SUB-170 status not_credited | pipeline: incomplete | None | gold: incomplete
SUB-171 operations miss | pipeline: 'Restaurant and bar. Full liquor (TABC mixed beverage permit), 140 seats, live music Thursday to Sunday until midnight. Dinner service and w | gold: Restaurant and bar, full liquor (TABC mixed beverage permit), 140 seats, charbroiler, 2 fryers, flat-top, 8-burner range and pizza oven unde
SUB-171 loss_run_valued_through not_credited | pipeline: None | gold: missing, none provided (the email says the Carrier B run came with another email)
SUB-172 premises_address miss | pipeline: None | gold: 1100 Cypress Pointe Dr, Denton, TX 76205
SUB-172 operations miss | pipeline: 'Residential apartments, 3 properties, 30 units total, long-term leases. Occupancy 95 percent. No cooking operations (tenant electric ranges | gold: Apartment buildings, 3 properties, 30 units total, long-term leases, no cooking operations (tenant electric ranges only)
SUB-172 year_built miss | pipeline: None | gold: 2012 / 2015 / 2017
SUB-172 loss_run_valued_through not_credited | pipeline: None | gold: missing, not yet requested
SUB-172 conflict miss | open: [{"field": "premises_address", "values": [{"value": "1100 Cypress Pointe Dr, Denton, TX 76205", "source": "application.md", "start": 238, "end": 286, "quote": "1100 Cypress Pointe Dr, Denton, TX 76205 (loc 1)", "needs_review": false, "reason": null, "confidence": 1.0}, {"value": "2450 Trimmier Rd, K | gold: none
SUB-173 operations miss | pipeline: 'Counter service. Tacos, burritos, quesadillas and agua fresca, 35 seats, dine-in and takeout. No liquor.' | gold: Counter service taqueria (tacos, burritos, quesadillas, agua fresca), no liquor, 35 seats, dine-in and takeout
SUB-173 loss_run_valued_through not_credited | pipeline: None | gold: missing, none provided (from the old agent, coming)
```
