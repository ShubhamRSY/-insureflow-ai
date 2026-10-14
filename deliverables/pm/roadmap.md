# Roadmap — Sanger & Altgelt underwriting pipeline

- Author: @pm
- Date: 2026-10-09
- Status: Accepted by @head-of-underwriting (T-013)
- Replaces the carrier/MGA charter (T-001 cancelled, D-003 superseded by D-004)
- See also: deliverables/pm/requirements.md (T-097), the functional and non-functional requirements register for this pilot.

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

## Order of work to the demo (2026-10-11, @pm)

From D-030, D-031 item 2, D-033, D-034, D-035, and D-037. One turn at a time. The numbered lines of team/DEMO-BLOCKERS.md are fixed in the user's order. Reviews of each build go to its reviewers as it lands.

Before every scored run the code is committed and the hash is written in the memo (D-034). Who makes the commit is the user's to say.

1. Work with no code in it, first, so approvals and inputs are ready before their turn: T-084 (proposal P-015), T-080 (proposal P-016), T-088 (proposal P-017), T-082 (carrier class lists), T-069 (saved-file keys), T-089 (model inventory), T-090 (memo lines).
2. T-078, build P-014. Then the reviews that are still owed: T-065, T-073, T-074, T-075, T-078; a second look at T-060 and T-063.
3. Commit. T-064, the quick-set baseline. T-061 takes its count from it.
4. Blocker 1: T-070, then T-071. The three T-059 reviewers look again. T-072 (P-011) follows T-070. The P-017 build follows T-072, if approved.
5. Blocker 2: T-079.
6. Blocker 3: the P-016 build, if approved, then the quick set. T-081.
7. Blocker 4: T-083.
8. Blocker 5: the P-015 build, if approved.
9. Blocker 6: T-085. Blocker 7: T-086. Blocker 8: T-087. Then T-020 goes back to @compliance and @senior-underwriter, T-017 to its three reviewers, T-019 and T-027 to theirs.
10. T-062 (P-006), then T-068. This is the last change to extraction.
11. Freeze and commit. Blocker 9: T-091, T-092, T-093. No code changes between the gold and the published score.
12. T-066, the variance test. T-067, the fairness test.
13. T-076, demo prep.

If a proposal is not approved when its line is reached, work stops there and @pm asks the user; the order is not changed by @pm. Nothing in this order depends on something later in it.
