# RAG Corpus: Personal Homeowners

Homeowners Underwriting Guide · Version 3.0 · Effective 2026-01-01

## LOB metadata
- LOB slug: personal_homeowners
- Products: 4
- Categories: 0
- Standards: ISO HO-3/HO-5 forms, CLUE, state DOI filed rules
- Underwriting authority: Field authority to program limits; refer coastal/wildfire zones, aged roofs, and excessive CLUE losses.

## How to use for RAG
- Index each `documents/<product>.md` as one or more chunks (split on the `##` sections).
- Bias retrieval to this LOB (or category) when the submission's line is known.
- The sections map to likely underwriter questions: eligibility, decline, documents, coverages, exclusions, limits, rating, authority.

## Product catalog

| product_id | name | category | status | docs | coverages | forms |
|---|---|---|---|---|---|---|
| personal_homeowners_0 | Homeowners application | personal_homeowners | filed | 2 | 0 | 0 |
| personal_homeowners_1 | Dwelling inspection | personal_homeowners | filed | 2 | 0 | 0 |
| personal_homeowners_2 | Claims history / CLUE | personal_homeowners | filed | 2 | 0 | 0 |
| personal_homeowners_3 | Declarations / prior policy | personal_homeowners | filed | 1 | 0 | 0 |

## Product summaries

### personal_homeowners_0 — Homeowners application
- Full guide entry: `documents/personal_homeowners_0.md`

### personal_homeowners_1 — Dwelling inspection
- Full guide entry: `documents/personal_homeowners_1.md`

### personal_homeowners_2 — Claims history / CLUE
- Full guide entry: `documents/personal_homeowners_2.md`

### personal_homeowners_3 — Declarations / prior policy
- Full guide entry: `documents/personal_homeowners_3.md`

## Notes
- Personal-lines program limits apply; refer non-standard risks.
