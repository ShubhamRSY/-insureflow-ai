# Roadmap — Sanger & Altgelt underwriting pipeline

- Author: @pm
- Date: 2026-10-09
- Status: Accepted by @head-of-underwriting (T-013)
- Replaces the carrier/MGA charter (T-001 cancelled, D-003 superseded by D-004)

## Goal

Automate preparation of small commercial submissions for Sanger & Altgelt underwriters. The agency places business with carriers. It does not write the policy.

The underwriter approves, edits, or declines every account. The system does not auto-decline and does not auto-bind.

## Users

Agency underwriters and account managers.

## Pilot

Texas only. BOP, property, and general liability. Carriers are placeholders A, B, and C until the real panel is confirmed. All data in this repo is synthetic.

## Success metrics (from D-004)

| Metric | What we will count |
|---|---|
| Underwriter time per submission | Touch time from workbench open to decision |
| Auto-prepared with no corrections | Share of submissions where the underwriter changes no extracted field |
| Carrier first-pass acceptance | Share of packages a placeholder carrier would accept on the rules we wrote (real hit rate waits on the real panel) |
| Quote turnaround | Intake to carrier package ready for the underwriter to release |

Loss ratio is not a headline metric. We do not file rates.

## Pipeline

| Step | Who acts | Owner | Sprint |
|---|---|---|---|
| 1. Intake | AI | @software-engineer | Build 1 (T-014) |
| 2. Extraction with citations | AI | @ai-engineer | Build 1 (T-015) |
| 3. Completeness and missing-info request | AI | @ai-engineer | Build 1 (T-016) |
| 4. Risk score and reason codes | AI recommends | @data-scientist | After T-007 (T-017) |
| 5. Appetite and carrier match | AI recommends | @head-of-underwriting | T-018 |
| 6. Workbench | Underwriter decides | @software-engineer | T-019, started under D-009 |
| 7. Carrier package and quote tracking | AI, after the user types send to carrier SUB-### | @software-engineer | T-020, started under D-009 |
| 8. Feedback from decisions | AI | @ml-engineer | T-021 |

## Out of scope

- Binding coverage, issuing a declination to an applicant, or choosing the carrier without the underwriter.
- A protection-class vendor.
- A rate manual or a model price.
- Any carrier other than placeholders A/B/C.
- Real applicant data.

## Cancelled

T-001, T-002, T-005, T-006, T-010, T-011. Reasons are on the board.
