"""Comprehensive Underwriting Memo Template Generator.

Generates a production-ready underwriting evaluation memo for Level Term
Life Insurance submissions (ACORD 100 package), covering all 6 sections
plus legal safeguards and reinstatement rules.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from insureflow.models.agents import UWDecision


def generate_memo(
    *,
    bundle_id: str,
    product_type: str = "Level Term Life Insurance",
    face_amount: float = 0.0,
    term_years: int = 20,
    uw_class: str = "standard",
    table_index: int = 0,
    flat_extras: float = 0.0,
    bmi: float | None = None,
    income: float = 0.0,
    net_worth: float = 0.0,
    age: int | None = None,
    decision: UWDecision = UWDecision.ACCEPT,
    checklist: dict[str, Any] | None = None,
    screening: dict[str, Any] | None = None,
    medical: dict[str, Any] | None = None,
    financial: dict[str, Any] | None = None,
    reinsurance: dict[str, Any] | None = None,
    retention: dict[str, Any] | None = None,
    state_code: str = "",
    insured_name: str = "[Applicant Name]",
    dob: str = "[DOB / Age]",
    **kwargs: Any,
) -> str:
    """Generate a formatted underwriting evaluation memo."""
    now = datetime.now(timezone.utc).strftime("%B %d, %Y")
    policy_id = bundle_id.upper()

    # Checklist section
    cl = checklist or {}
    cl_items = []
    cl_items.append(f"  Gov-Issued Photo ID: {'Verified (Pass)' if 'photo_id' in (cl.get('passed') or []) else 'MISSING'}")
    cl_items.append(f"  SSN Validation: {'Clear / Verified' if screening and screening.get('ssn_verified') else 'Pending'}")
    cl_items.append(f"  Proof of Address: {'Verified' if 'proof_of_address' in (cl.get('passed') or []) else 'Missing'}")
    cl_items.append(f"  HIPAA & MIB Auth: {'Signed & Filed' if 'hipaa_auth' in (cl.get('passed') or []) else 'MISSING'}")
    cl_items.append(f"  Rx Database Check: {'Checked (No adverse flags)' if screening and screening.get('rx_clear') else 'Pending'}")
    cl_items.append(f"  Beneficiary Details: {'Complete' if 'beneficiary' in (cl.get('passed') or []) else 'Incomplete'}")
    cl_items.append(f"  Income Proof: {'Verified via W-2 / Tax Returns' if 'income_proof' in (cl.get('passed') or []) else 'Not submitted'}")
    cl_items.append(f"  Paramedical Exam: {'Received & Filed' if medical and medical.get('paramed_required') else 'Not required / Pending'}")

    # Financial section
    fin = financial or {}
    hlv = fin.get("hlv", {})
    max_ceiling = hlv.get("max_face_high", 0)
    income_mult = hlv.get("multiplier_high", "N/A")
    insurable_pass = "PASS" if face_amount <= max_ceiling * 1.05 else "EXCEEDS CEILING — REFER"

    # Medical section
    med = medical or {}
    bmi_val = bmi or med.get("bmi")
    vitals_section = []
    if med.get("medical_decision") and med["medical_decision"].get("vitals"):
        v = med["medical_decision"]["vitals"]
        if v.get("bp_systolic") and v.get("bp_diastolic"):
            vitals_section.append(f"  Blood Pressure: {v['bp_systolic']:.0f}/{v['bp_diastolic']:.0f} mmHg")
        if v.get("cholesterol"):
            vitals_section.append(f"  Cholesterol: {v['cholesterol']:.0f} mg/dL")
        if v.get("a1c"):
            vitals_section.append(f"  A1C: {v['a1c']:.1f}%")

    # Decision section
    disp_map = {
        UWDecision.ACCEPT: "[X] ISSUE AS APPLIED",
        UWDecision.CONDITIONAL_ACCEPT: "[X] ISSUE WITH AMENDMENTS / RATED",
        UWDecision.REFER: "[ ] POSTPONE / PENDING REQUIREMENTS",
        UWDecision.DECLINE: "[ ] DECLINE",
    }
    decision_line = disp_map.get(decision, "[ ] REVIEW REQUIRED")

    # Reinsurance section
    reins = reinsurance or {}
    retained = reins.get("retained_in_house", face_amount)
    cession = reins.get("cessation_amount", 0)
    requires_fac = reins.get("requires_facultative", False)

    # Legal safeguards
    state_rules = kwargs.get("state_regulatory", {})
    contestability_years = state_rules.get("contestability_period_years", 2)
    suicide_years = state_rules.get("suicide_period_years", 2)
    free_look_days = state_rules.get("free_look_days", 10)

    memo = f"""
================================================================================
                       UNDERWRITING EVALUATION MEMO
================================================================================
CASE ID / POLICY #: {policy_id}              DATE: {now}
PRODUCT TYPE: {product_type} ({term_years}-Year)   FACE AMOUNT: ${face_amount:,.0f}
STATE: {state_code or "N/A"}
================================================================================

1. APPLICANT IDENTIFICATION & SUBMISSION CHECKLIST (ACORD 100)
--------------------------------------------------------------------------------
{chr(10).join(cl_items)}

2. FINANCIAL UNDERWRITING & NEEDS ANALYSIS
--------------------------------------------------------------------------------
  Annual Earned Income: ${income:,.0f}                 Net Worth: ${net_worth:,.0f}
  Max Face Multiplier Applied (Age Bracket: {income_mult}×): ${max_ceiling:,.0f} ceiling.
  Requested Face Amount (${face_amount:,.0f}) vs. Financial Justification: {insurable_pass}.
  Insurable interest {"is fully established" if insurable_pass == "PASS" else "requires review"};
  {"No" if insurable_pass == "PASS" else "Potential"} over-insurance {"not " if insurable_pass == "PASS" else ""}detected.

3. MEDICAL & RISK ASSESSMENT
--------------------------------------------------------------------------------
  BMI: {f"{bmi_val:.1f}" if bmi_val else "Not calculated"} ({med.get("bmi_tier", "Unknown")})
{chr(10).join(vitals_section) if vitals_section else "  Vitals: Pending paramedical exam"}
  Underwriting Class: {uw_class.replace("_", " ").title()}
  Table Rating: {"Table " + chr(ord("A") + table_index - 1) + f" ({(0.25 * table_index * 100):.0f}% surcharge)" if table_index > 0 else "Standard Base (No Surcharge)"}
  Flat Extra: {f"${flat_extras:.0f}/1,000" if flat_extras > 0 else "None required"}

4. UNDERWRITING CLASSIFICATION & PRICING
--------------------------------------------------------------------------------
  Assigned Underwriting Class: {uw_class.replace("_", " ").upper()}
  Final Premium Multiplier: {(1 + 0.25 * table_index):.2f}× standard
  {"Table Rating / Surcharge: Table " + chr(ord('A') + table_index - 1) + f" / {(0.25 * table_index * 100):.0f}% surcharge" if table_index > 0 else "Table Rating / Surcharge: Standard Base"}
  Flat Extra: {f"${flat_extras:.0f}/1,000" if flat_extras > 0 else "None required"}

5. RETENTION & REINSURANCE MANAGEMENT
--------------------------------------------------------------------------------
  Requested Face Amount: ${face_amount:,.0f}
  Company Retention Limit (Preferred Class): ${retained:,.0f}
  Action: {"Retained 100% in-house. No facultative reinsurance cession required." if not requires_fac else f"Facultative cession required: ${cession:,.0f} ceded to reinsurer."}

6. FINAL UNDERWRITING DECISION & DISPOSITION
--------------------------------------------------------------------------------
{decision_line} ({uw_class.replace("_", " ").title()}, Level {term_years}-Year Term)
{"[ ] ISSUE WITH AMENDMENTS / RATED" if decision != UWDecision.CONDITIONAL_ACCEPT else ""}
{"[ ] POSTPONE / PENDING REQUIREMENTS" if decision not in (UWDecision.REFER, UWDecision.DECLINE) else ""}
{"[ ] DECLINE" if decision not in (UWDecision.DECLINE,) else ""}

Underwriter Signature: ___________________________   Date: {now}

================================================================================
                       LEGAL SAFEGUARDS & COMPLIANCE
================================================================================

Incontestability Clause ({contestability_years} Years):
  After the policy has been in force for {contestability_years} years during the
  insured's lifetime, the insurer cannot contest or void the contract based on
  misstatements or omissions made on the initial application.

Suicide Provision ({suicide_years} Years):
  If the insured dies by suicide within the first {suicide_years} years of the policy,
  the insurer's liability is limited strictly to returning the premiums paid.

Free Look Period ({free_look_days} Days):
  The policyholder may return the policy within {free_look_days} days of receipt
  for a full refund of premiums paid.

1035 Exchange Compliance (if applicable):
  If this policy replaces an existing policy via a 1035 tax-free exchange,
  a signed replacement notice and 1035 assignment form must be on file.
  The suitability review ensures the client is not harmed by the exchange
  (e.g., losing a lower locked-in age rate or triggering surrender charges).

Reinstatement Rules (If Policy Lapses):
  Window: 3–5 years from lapse date.
  Requirements:
    - Evidence of Insurability (EOI): Short-form health questionnaire and
      potentially a new paramedical exam if lapse is prolonged.
    - Overdue Premium: Back-premiums plus accumulated interest (typically
      5–6% compounded annually).

================================================================================
                       UNDERWRITING FORMULAS REFERENCE
================================================================================

Human Life Value (HLV) & Income Multiples:
  Max Face Amount = Annual Earned Income × Age Multiplier
  Ages 18–30: 25× to 30×  |  Ages 31–40: 20× to 25×
  Ages 41–50: 15× to 20×  |  Ages 51–60: 10× to 15×
  Ages 60+: 5× or tied to net worth / estate needs

Body Mass Index (BMI):
  BMI = (Weight in lbs / Height in inches²) × 703
  Preferred Plus: BMI ≤ 25  |  Preferred: BMI ≤ 27.5
  Standard Plus: BMI ≤ 30   |  Table A: BMI ≤ 35

Table Rating Premium Surcharge:
  Final Premium = Standard Premium × (1 + 0.25 × Table Index)
  Table A = +25%  |  Table B = +50%  |  Table C = +75%  |  Table D = +100%

Net Worth Multiple (Estate Cases):
  Max Estate Face Amount = Estimated Net Worth × 15% (typical tax/liquidity %)

Facultative Cession:
  Facultative Cession = Requested Face Amount − Company Retention Limit

================================================================================
"""
    return memo.strip()
