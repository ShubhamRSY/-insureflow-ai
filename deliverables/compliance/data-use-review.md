# Permitted-use review — sources in the data inventory

- Author: @compliance
- Date: 2026-10-09
- Status: Draft for review (T-012)
- Input: `deliverables/data-engineer/data-inventory.md`
- Reviewers: @responsible-ai, @data-engineer
- Not a legal opinion. Rows marked below still need counsel where the register says so.

Training use is **not** underwriting use. Nothing here approves training a model on customer submissions.

## Decisions

| Source | Underwriting this submission | Training / vendor model fit | Decision |
|---|---|---|---|
| S-01 Submission documents | Allowed | Prohibited until a separate written decision | **Approved** for underwriting only |
| S-02 Carrier loss runs via the broker | Allowed | Prohibited, same as S-01 | **Approved** for underwriting only |
| S-03 No-known-loss letter | Allowed only to mark the file Incomplete | Prohibited | **Restricted** |
| S-04 Our policy and claims systems | Allowed for the same insured, once connected | Prohibited until T-012 is revised | **Approved** for underwriting, not connected yet |
| S-05 Protection class vendor | Not allowed | Not allowed | **Not used in v1 (D-004).** Do not build the connector. |
| S-06 Geocoder | Allowed to place the premises for the coastal rule and the filed territory | Prohibited | **Restricted** to location. Do not attach neighborhood scores. |
| S-07 Coastal / wind-pool list we maintain | Allowed as the appetite exclusion | n/a (our list) | **Approved** as a territory rule. This is wind, not a demographic factor. @responsible-ai still tests impact. |
| S-08 Credit, criminal, social, business-health, web scrape | Not allowed | Not allowed | **Prohibited.** Do not build the connector. |

## Conditions on every approved source

- Use is for the submission in front of us, plus the audit record (register C-08, C-09).
- The LLM may see S-01 and S-02 text. It may not see S-08, because S-08 must not be in the building.
- A pipeline change that adds a source is a new row in this review, not a deploy note.

## Veto

I will veto any build that calls S-08 or that treats S-03 as zero losses.
