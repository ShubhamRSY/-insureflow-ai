# Rytera™ — Data Processing Agreement (Template)

**Status:** Template for carrier / bank customer negotiation — not executed legal advice.  
**Product:** Rytera underwriting platform (`insureflow-ai`)

## 1. Parties

This Data Processing Agreement (“DPA”) is entered into between **Customer** (Controller) and **Rytera, Inc.** (Processor).

## 2. Scope of processing

Processor provides AI-assisted underwriting document ingestion, reconciliation, decision support, audit packaging, and related API/dashboard services for insurance, mortgage, and lending workflows.

## 3. Categories of data

May include: insured/borrower identifiers, financial statements, credit-related attributes, property details, ACORD submissions, loss history, and underwriter annotations. Customer shall not send data it is not authorized to process.

## 4. Processor obligations

- Process personal data only on documented instructions from Customer
- Maintain confidentiality and RBAC on platform accounts
- Implement encryption in transit (TLS) and at rest (application Fernet / cloud KMS)
- Notify Customer without undue delay after becoming aware of a personal data breach
- Assist with data subject requests reasonably within product capabilities
- Delete or return Customer data at end of services per retention schedule (default examiner retention ~7 years for sealed audit artifacts unless instructed otherwise)

## 5. Subprocessors

Customer authorizes use of infrastructure subprocessors (e.g., AWS regions contracted by Customer or Rytera hosting) and optional AI providers (OpenAI/Anthropic) when Customer configures API keys. A current subprocessor list will be maintained in the Customer security pack.

## 6. Security measures

Aligned with `docs/BANK_LANDING_ZONE.md` and `legal/SOC2_QUESTIONNAIRE.md`: VPC isolation, Secrets Manager, CloudTrail, WAF, encrypted RDS, WORM audit option, LangSmith for AI eval governance (no substitute for infrastructure logging).

## 7. Governing law

To be completed with Customer counsel.

---
© Rytera, Inc. Template only.
