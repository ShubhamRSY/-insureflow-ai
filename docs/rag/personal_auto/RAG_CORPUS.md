# RAG Corpus: Personal Auto

Personal Auto Underwriting Guide · Version 3.0 · Effective 2026-01-01

## LOB metadata
- LOB slug: personal_auto
- Products: 4
- Categories: 0
- Standards: ISO Personal Auto Program (PAP), state financial-responsibility limits, NAIC
- Underwriting authority: Field authority to program limits; refer non-standard drivers, high-value vehicles, and SR-22/FR filings.

## How to use for RAG
- Index each `documents/<product>.md` as one or more chunks (split on the `##` sections).
- Bias retrieval to this LOB (or category) when the submission's line is known.
- The sections map to likely underwriter questions: eligibility, decline, documents, coverages, exclusions, limits, rating, authority.

## Product catalog

| product_id | name | category | status | docs | coverages | forms |
|---|---|---|---|---|---|---|
| personal_auto_0 | Auto application | personal_auto | filed | 2 | 0 | 0 |
| personal_auto_1 | MVR / driving record | personal_auto | filed | 1 | 0 | 0 |
| personal_auto_2 | Vehicle declarations | personal_auto | filed | 2 | 0 | 0 |
| personal_auto_3 | Claims / loss history | personal_auto | filed | 2 | 0 | 0 |

## Product summaries

### personal_auto_0 — Auto application
- Full guide entry: `documents/personal_auto_0.md`

### personal_auto_1 — MVR / driving record
- Full guide entry: `documents/personal_auto_1.md`

### personal_auto_2 — Vehicle declarations
- Full guide entry: `documents/personal_auto_2.md`

### personal_auto_3 — Claims / loss history
- Full guide entry: `documents/personal_auto_3.md`

## Notes
- Personal-lines program limits apply; refer non-standard risks.
