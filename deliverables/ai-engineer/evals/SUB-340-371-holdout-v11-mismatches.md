# T-119 mismatches, as-is (SUB-340 to SUB-371, scorer v11, D-130)

Recorded after the single official run on 2026-10-24 (run id `20261024T000318-70195`). Nothing was fixed and nothing was re-scored. Source: `SUB-340-371-holdout-v11.json` and the saved replies in `underwriting_pipeline/cache/T-119-live/`. Answers were read back from those saved replies with no model call (copy of the cache in a temp folder).

Every field mark that is not a plain `hit` is listed (27: operations 11 miss, status 11 miss, conflict 3 miss, conflict 2 flagged). `source` is the file the stored value came from; a derived mark (conflict, status) has no single source and shows `—`. A `flagged` conflict mark is not a miss (the documents disagree and the AI stored both sides).

| File | Field | Mark | Source | Answer (as stored) | Gold |
|---|---|---|---|---|---|
| SUB-340 | operations | miss | application.md | Office (needs_review=True) | Office; no cooking / items: business_type=office; no cooking |
| SUB-340 | status | miss | — | complete — review pending | complete |
| SUB-341 | operations | miss | application.md | Clothing retail storefront (needs_review=True) | Clothing retail storefront; no cooking / items: business_type=retail; no cooking |
| SUB-341 | status | miss | — | complete — review pending | complete |
| SUB-342 | operations | miss | application.md | Dry goods retail store (needs_review=True) | Dry goods retail store; no cooking / items: business_type=retail; no cooking |
| SUB-342 | status | miss | — | complete — review pending | complete |
| SUB-343 | operations | miss | application.md | Thrift store (needs_review=True) | Thrift store; no cooking / items: business_type=retail; no cooking |
| SUB-343 | status | miss | — | complete — review pending | complete |
| SUB-344 | operations | miss | application.pdf | Electrical contracting, office and shop (needs_review=True) | Electrical contracting, office and shop; 6 vans; no cooking / items: business_type=contractor; no cooking |
| SUB-344 | conflict | flagged | — | open conflicts: [{"field": "square_feet", "values": [{"value": "3200", "source": "application.pdf", "quote": "Square footage: 3,200"}, {"value": "2450", "source": "email.md", "quote": "2,450 square feet"}], "resolution": "unresolved", "resolved_value": null, "resolved_by": null}] | square footage: 3200 (application) vs 2450 (schedule) |
| SUB-345 | conflict | miss | — | open conflicts: [] | sales: 1240000 (application) vs 1420000 (email, 'about $1.42 million'; the application figure was the budget) |
| SUB-346 | operations | miss | email.md | Lessor of office building, 9 suites, professional tenants (needs_review=True) | Lessor of office building, 8 suites, professional tenants; no cooking / items: business_type=office; no cooking |
| SUB-346 | conflict | flagged | — | open conflicts: [{"field": "suite_count", "values": [{"value": "9", "source": "email.md", "quote": "Lessor of office building, 9 suites, professional tenants"}, {"value": "8", "source": "application.md", "quote": "Operations: Lessor of office building, 8 suites, professional tenants"}], "resolution": "unresolved", "resolved_value": null, "resolved_by": null}] | suites: 8 (application) vs 9 (email, the last suite just rented to a title company; the application is from before the lease) |
| SUB-347 | operations | miss | application.md | Lessor of office building, 6 suites, professional tenants (needs_review=True) | Lessor of office building, 6 suites, professional tenants; no cooking / items: business_type=office; no cooking |
| SUB-347 | status | miss | — | complete — review pending | complete |
| SUB-348 | conflict | miss | — | open conflicts: [] | cooking: none (application) vs stove top and flat grill (email, hot food all day) |
| SUB-349 | conflict | miss | — | open conflicts: [] | cooking: none (application) vs yes (schedule) and griddle (email) |
| SUB-350 | operations | miss | application.md | Wholesale plumbing supplies, warehouse, counter pickup, no cooking (needs_review=False) | Wholesale plumbing supplies, warehouse, counter pickup; no cooking / items: business_type=wholesale; no cooking |
| SUB-352 | operations | miss | application.pdf | Pub with full bar and kitchen, ground floor; office suites, second floor; fryer, flat top, hood (needs_review=True) | Two operations: pub with full bar and kitchen on the ground floor, fryer, flat top, hood; two office suites on the second floor / items: business_type=bar_pub; business_type=office; full liquor; fryer; flat top; hood |
| SUB-352 | status | miss | — | complete — review pending | complete |
| SUB-353 | status | miss | — | incomplete | complete |
| SUB-354 | status | miss | — | complete — review pending | complete |
| SUB-355 | operations | miss | email.md | Hookah lounge, lounge seating, beer and wine, tea, energy drinks, open to 1 am (needs_review=True) | Hookah lounge, lounge seating; beer and wine; open to 1 am; cooking none / items: business_type=hookah_adult; business_type=lounge_nightclub; beer and wine; open to 1 am; no cooking |
| SUB-355 | status | miss | — | complete — review pending | complete |
| SUB-357 | status | miss | — | incomplete | complete |
| SUB-358 | status | miss | — | complete — review pending | complete |
| SUB-359 | operations | miss | application.md | Flooring installation, hardwood, tile and vinyl (needs_review=True) | Flooring installation, hardwood, tile and vinyl; five crew, two trucks; no cooking / items: business_type=contractor; no cooking |

## Not mismatches (for completeness)
- Leakage 0 of 12; detection recall 12/12; false manual intake 0 of 20; false completes 0; unsafe routes 0; call_failed 0; retries 1 (SUB-340, rate_limit_429).
- Silent error: 1 of 180, operations on SUB-350 (stored 'Wholesale plumbing supplies, warehouse, counter pickup, no cooking', not flagged for review; the v11 checklist wants the business_type=wholesale slot).
