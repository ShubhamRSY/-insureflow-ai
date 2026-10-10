# Regulatory requirements register — US small commercial P&C pilot

- Author: @compliance
- Date: 2026-10-09
- Status: Draft for review (@head-of-underwriting, @responsible-ai)
- Scope assumption: US admitted carrier or MGA writing admitted small commercial package (property + GL). Not a lender. Not personal lines. **[NEEDS LEGAL CONFIRMATION]** on the actual writing company, surplus-lines status, and pilot states.

This is a simulated compliance memo, not a legal opinion.

## Register

| ID | Requirement | Source | Applies | How we comply in v1 | Evidence | Owner |
|---|---|---|---|---|---|---|
| C-01 | Unfair discrimination in underwriting | State insurance unfair-trade-practice statutes (NAIC Model Act framework; state versions differ) | Yes | Declines and referrals use class, territory, construction, protection, losses, and size only. No race, religion, national origin, sex, or proxies smuggled in via "owner profile." | Appetite guide + authority matrix + feature review (T-012) | @head-of-underwriting / @responsible-ai |
| C-02 | AI governance by insurers | NAIC Model Bulletin: Use of Artificial Intelligence Systems by Insurers (adopted Dec 2023; state adoption varies) | Yes, where adopted. Treat as applicable in every pilot state until confirmed. | Written use case, human accountability, audit trail, vendor oversight, and validation before use. | This register, T-008 standards, future governance memo | @compliance |
| C-03 | External consumer data and algorithms | Colorado SB21-169 and Regulation 10-1-1 (unfair discrimination in insurance practices that use external consumer data) | **[NEEDS LEGAL CONFIRMATION]** if any pilot state is Colorado, or if we later add external consumer data anywhere | v1 uses no external consumer data and no credit. If Colorado is a pilot state, do not turn the system on until a governance report path exists. | Data-use review T-012 | @compliance |
| C-04 | External data in underwriting | NYDFS Circular Letter No. 1 (2019) on use of external consumer data and information sources in underwriting and pricing; related NY unfair-discrimination law | Only if we write NY or use those sources | Same ban as C-03 for v1. | T-012 | @compliance |
| C-05 | Rate and rule filings | State rate-regulatory laws; policy form filings | Yes | The system quotes the **filed rate and filed rules** only. No schedule credit/debit from the model. A rules change (new knock-out) is a filing project, not a config change. | Filed manual citation on every quote **[NEEDS LEGAL CONFIRMATION]** which manual and which entity files | @actuary / @compliance |
| C-06 | Adverse action / consumer reports | FCRA, if a consumer report is used (credit, some investigative reports) | Not in v1, **if** we keep the ban on credit and consumer reports | Do not call a consumer-report vendor. Loss runs from the **carrier**, obtained via the broker, are underwriting files, not a reason to skip this analysis if a vendor bureau is added later. | Vendor list in T-004 must mark any consumer-report source | @compliance |
| C-07 | Declination notices | State declination / cancellation-nonrenewal rules differ; many require a specific reason and timing | Yes when we decline | Human sends the notice. Reason must be a rule id on the prohibited or knock-out list. No free-text "AI declined." | Notice procedure — template is **not** written yet (follow-up) | @compliance |
| C-08 | Privacy and GLBA | GLBA and state insurance privacy (NAIC privacy model; state variants) | Yes | Applicant data used for underwriting the submission only. No training on customer data until a separate permitted-use decision. | T-004 inventory + T-012 | @data-engineer / @compliance |
| C-09 | Record retention | State market-conduct and record-retention rules; NAIC AI bulletin documentation expectations | Yes | Retain submission, extraction, rule version, recommendation, human decision, and notice for the statutory period. **[NEEDS LEGAL CONFIRMATION]** of the longest pilot-state period; use 7 years as the working assumption until confirmed. | Audit-trail requirement in architecture (T-006) | @software-engineer |
| C-10 | Producer compensation / rebating | State anti-rebating laws | Only if the pilot changes commission or gives agents a tool that is a valuable inducement | Pilot does not change commission. | Out of scope statement in roadmap | @pm |
| C-11 | Unfair claims practices | State unfair claims settlement acts | No — this project does not handle claims decisions | Do not extend the system into claims without a new register entry. | Roadmap out-of-scope | @pm |
| C-12 | MGA authority | Appointment and underwriting-authority agreements | **[NEEDS LEGAL CONFIRMATION]** if the operating entity is an MGA | Auto-quote authority cannot exceed the MGA agreement or the carrier's filed rules. | Authority matrix signed against the agreement | @head-of-underwriting |

## Allowed with conditions

- Deterministic knock-out rules that match a **filed** underwriting guideline, with a human sending any decline notice (C-05, C-07).
- LLM extraction used as a draft, with the source span stored, and a human or a deterministic check before the value hits a quote (C-02).
- Currently valued carrier loss runs supplied for the submission (not a consumer-reporting agency pull).

## Prohibited in v1

- Auto-decline with no human confirming the reason (C-07). @head-of-underwriting's matrix already says this. I am holding that line.
- Credit, criminal history, telematics on officers, social-media scores, and any vendor "business health" score (C-03, C-04, C-06).
- Model-set price, schedule credit, or schedule debit (C-05).
- Training foundation or vendor models on identifiable submission data before T-012 (C-08).

## Items that need a real lawyer

Every row marked **[NEEDS LEGAL CONFIRMATION]**. Highest priority: writing entity and pilot states (changes C-03 and C-12), which rate manual we are bound to (C-05), and declination content by those states (C-07).

## Objection standing

I am not vetoing the appetite draft. I will veto any build that (1) sends a decline without a human and an on-list reason, or (2) introduces external consumer data before C-03/C-04 are closed.
