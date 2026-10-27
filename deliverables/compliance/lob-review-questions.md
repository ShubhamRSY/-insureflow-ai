# LOB review questions — @compliance

- Author: @compliance (written in OpenCode, not independently reviewed). Date: 2026-10-21.
- **No verdicts today.** This is the question list each LOB must answer before real data or a pilot. Synthetic data only.
- Standing: no real applicant data reaches the model host until the data-handling question is answered; the T-027 veto stands. This list does not replace the agency and regulatory registers.

## 1. Questions that apply to every LOB

1. **Lawful basis and notice**: what notice and authorization cover the documents sent to the model host (Groq free tier, D-011/D-012)?
2. **Data minimisation**: which fields are necessary for this LOB, and can the rest be redacted before extraction?
3. **PII in prompts**: names, addresses, dates of birth, medical data, financial account data — what is allowed, and what must never leave the agency?
4. **Retention**: how long are documents, saved runs, prompts, replies, caches and logs kept, and where?
5. **Access**: who may see the output (authenticated underwriter/account manager only), and is every view logged (C4/C5)?
6. **Model host**: is the host acceptable for this data class; is any training on submitted data excluded by contract/settings?
7. **Synthetic-only team artifacts**: no real applicant data in `deliverables/`, `team/`, screenshots or outboxes (C4/L1).
8. **Producer/agency licensing**: does this LOB require a licensed producer or surplus-lines filing in the pilot state?
9. **State variation**: which states are in appetite, and are forms/rates state-approved?
10. **Recordkeeping**: are decisions, corrections and refusals retained with the identity of the underwriter?
11. **Fairness**: does the LOB use any protected or proxy characteristic, and does it need @responsible-ai review?
12. **Third-party data**: MVR, credit, medical, sanctions or cat data — what is the permissible purpose and the source licence?
13. **Consumer disclosures**: does this LOB trigger adverse-action, FCRA, GLBA or state consumer notices?
14. **Vendor/carrier data**: does a placeholder carrier become a real carrier, and has its data-use terms been reviewed?

## 2. Per-LOB questions

| LOB | Questions |
|---|---|
| business_owners_policy | Baseline commercial data; confirm the agency notice covers property/GL documents and loss runs. |
| commercial_property | Are inspection reports and loss runs third-party data with a permitted use? Any state property-form filing? |
| general_liability | Are payroll/sales figures personal or business data; any class-code regulatory filing? |
| commercial_package | Same as property + GL; confirm one notice covers both sections. |
| umbrella | Underlying declarations may name other insureds and carriers; what notice and minimisation apply? |
| inland_marine | Item schedules may include serial numbers and locations; are they personal data? |
| builders_risk | Project and contractor data; lien/bond notices? |
| commercial_auto | VINs and driver data; MVR is a consumer report — permissible purpose and FCRA notice? |
| workers_comp | Employee payroll and injury data; state WC filing and privacy rules; medical data in loss runs? |
| crime | Employee and financial-control data; fidelity bond notices; financial-statement confidentiality. |
| surety_bonds | Financial statements, indemnitors and personal guarantees — personal data and consumer-report rules. |
| personal_homeowners | Consumer data, mortgagee, inspection; state homeowners forms and cancellation notices. |
| personal_auto | Consumer driver/vehicle data, MVR/FCRA, state auto rules and rating factors. |
| directors_and_officers | Board/ownership data; securities-related disclosures; public-company data. |
| errors_and_omissions | Professional services and claims data; claims-made notices. |
| cyber_liability | Security-control answers are sensitive; breach-data handling and state breach laws. |
| trade_credit | Buyer/obligor data, credit reporting, cross-border transfer. |
| key_person | Financial and health data about a key individual; life-insurance privacy rules. |
| legal_expense | Matter data and privilege; panel-counsel terms. |
| pollution_liability | Environmental site data; state environmental reporting. |
| kidnap_ransom | Travel/territory and potentially sensitive personal data; sanctions screening. |
| political_risk | Country/obligor data; sanctions and anti-boycott rules. |
| flood_commercial | Flood-zone and elevation data; NFIP/private flood rules and disclosures. |
| earthquake_commercial | Seismic data; state cat disclosures. |
| terrorism | Aggregation data; federal terrorism backstop (TRIA) rules. |
| aviation | Pilot records and aircraft data; FAA/medical privacy. |
| life | Medical, financial and mortality data; HIPAA/state privacy, MIB/FCRA, fairness review. |
| health | PHI/plan data; HIPAA, ACA/parity, state DOI; fairness review. |
| general | Triage only; what notice applies when the LOB is unknown and a person reads the file? |

## 3. Evidence expected before real data

- Data-handling note for the model host, signed by @compliance, naming the data classes allowed.
- Notice/authorization text used by the agency.
- Retention and access design; audit-log evidence.
- State-by-state appetite and filing table for the LOB.
- Third-party data licences and permissible purposes (MVR, credit, medical, sanctions).
- Fairness review where section 1 item 12 applies.
- Confirmation that no real data is in team artifacts or screenshots.

## 4. What this list is not

Not a verdict, not a legal opinion and not a waiver of any register entry. A LOB without answers to sections 1–2 does not go to real data, whatever its score.
