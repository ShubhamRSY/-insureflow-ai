# Agency regulatory register — Sanger & Altgelt pipeline

- Author: @compliance
- Date: 2026-10-09
- Status: Accepted (T-022)
- Replaces T-005 for control purposes. The old register assumed we were the writing company.
- Simulated memo, not a legal opinion.

| ID | Requirement | Applies | How v1 complies | Confirmation |
|---|---|---|---|---|
| A-01 | Texas agent / agency conduct. We are not the insurer. | Yes | The system prepares a submission. It does not bind, decline for a carrier, or tell the applicant they are rejected. | **[NEEDS LEGAL CONFIRMATION]** agency license and Jefferson Bank affiliation limits |
| A-02 | Misrepresentation to a carrier | Yes | Carrier package is built only after the underwriter approves step 6. Extracted fields keep citations. | — |
| A-03 | NAIC AI bulletin (insurer duty) | Maybe, through carriers we place with | We keep an audit trail (input, version, human decision). We do not claim the bulletin is our filing. | **[NEEDS LEGAL CONFIRMATION]** whether an agency tool is in scope in Texas |
| A-04 | Rate / rule filing | No | We do not make a rate. D-004. | — |
| A-05 | FCRA / consumer reports | No in v1 | No credit pull. Protection-class vendor is not used. | Reopen if a vendor is added |
| A-06 | Unfair discrimination | Yes, in how we recommend | Recommendations use class, construction, losses, size, and Texas location. Not race, religion, or a name as a feature. | @responsible-ai test plan |
| A-07 | Privacy of submission data | Yes | Synthetic data in this build. Real submissions later: underwriting the account only, no training until a new decision. | **[NEEDS LEGAL CONFIRMATION]** before any real file is stored |
| A-08 | Declination notices | Not by us | A carrier's decline is the carrier's notice. Our underwriter's "decline" means we will not place it. The reason is stored for the agency file. Do not send applicant-facing adverse-action letters from this system. | **[NEEDS LEGAL CONFIRMATION]** if the agency itself refuses to place and a notice is required |

## Veto still in force

I will veto any build that binds, that sends a decline to an applicant, or that calls a protection-class or credit vendor.
