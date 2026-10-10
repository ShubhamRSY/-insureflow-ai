# Data inventory (draft)

- Author: @data-engineer
- Date: 2026-10-09
- Status: Draft for review (T-004)
- Reviewers: @compliance, @data-scientist, @ai-engineer
- Permitted-use column is **pending compliance** until T-012. I am not approving any use.

Synthetic examples only. No live applicant records are in this repo.

## Sources

| ID | Source | What we need | Refresh | Permitted use |
|---|---|---|---|---|
| S-01 | Submission documents (ACORD 125/126/140, SOV, broker email) | Insured, locations, values, operations, class | Per submission | Pending compliance. Working assumption: underwrite this submission only. Not for model training. |
| S-02 | Carrier loss runs (PDF via the broker) | 5-year valued losses, open flag, date, amount, coverage | Per submission | Pending compliance. Underwrite this submission. A "no known loss" letter is a different source (S-03), not a substitute. |
| S-03 | No-known-loss letter | Document type only | Per submission | Pending compliance. May support Incomplete. Must not support "zero claims." |
| S-04 | Internal policy and claims admin | Our own prior policy and claims for the same insured | Nightly, once a system of record exists | Pending compliance. Not connected in the pilot environment yet. |
| S-05 | Protection class vendor | — | — | **Not used in v1 (D-004).** Do not call. A protection class printed on an ACORD is still just a field on S-01. |
| S-06 | Geocoder | Premises lat/long, to apply the coastal exclusion | Per location | Pending compliance. Location only. |
| S-07 | Cat / coast flag (wind pool, Tier 1 wind counties) | In or out of the coastal exclusion | Per location, reference list we maintain | Pending compliance. Underwriting territory rule, not a demographic score. |
| S-08 | Credit, criminal, social, "business health," web scrape | — | — | **Do not ingest.** Listed so a pipeline cannot add them quietly. |

No consumer-reporting agency is in the pilot design.

## Lineage

Raw object (hash) → page → extraction candidate (model version, span) → canonical field (null, value, or conflict). The feature table used for triage does not include person name.

## What is not here

A historical training extract. @data-scientist cannot build a loss model from this inventory yet. @model-risk's Tier 1 bar (historical files, not synthetic-only) is unmet.
