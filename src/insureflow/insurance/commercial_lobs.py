"""Business / Commercial Insurance LOB catalog: document packs + UW workflow.

This is the product source of truth for the Commercial Insurance hub UI and
LOB-aware package checklists.
"""

from __future__ import annotations

from typing import Any

# Shared base packet expected across nearly every commercial line
BASE_PACKET: list[str] = [
    "Last 2–3 years of financial statements (P&L, balance sheet)",
    "Loss run reports from prior carriers (3–5 years typical)",
    "Completed ACORD application(s) relevant to the line",
    "Business licenses / entity formation documents",
    "Organizational chart",
]

UW_CORE_RESPONSIBILITIES: list[dict[str, str]] = [
    {
        "id": "risk_assessment",
        "title": "Risk assessment",
        "summary": "Review the submission package and judge how risky the business is to insure for this line.",
    },
    {
        "id": "pricing",
        "title": "Pricing (rating)",
        "summary": "Calculate indicated premium using loss costs, experience, and UW judgment on top of the formula.",
    },
    {
        "id": "terms",
        "title": "Terms & conditions",
        "summary": "Set limits, retentions/deductibles, exclusions, endorsements, and any carve-outs.",
    },
    {
        "id": "decision",
        "title": "Decision",
        "summary": "Accept as submitted, accept with modifications, or decline — never leave ACCEPT contradicting critical findings.",
    },
    {
        "id": "portfolio",
        "title": "Portfolio fit",
        "summary": "Check how the risk fits the book (concentration by geography, industry, and peril).",
    },
    {
        "id": "monitoring",
        "title": "Renewal / monitoring",
        "summary": "At renewal, reassess on updated financials, claims, and material business changes.",
    },
]

COMMERCIAL_LINES: list[dict[str, Any]] = [
    {
        "id": "property_bi",
        "slug": "property-bi",
        "name": "Property & Business Interruption",
        "short_name": "Property / BI",
        "checklist_lob": "property",
        "insurance_line": "commercial_property",
        "description": "Building, contents, and business interruption coverage for commercial locations.",
        "uw_focus": ("Evaluate construction, fire protection, location hazards (flood/earthquake), valuation adequacy, and BI worksheet realism (COPE + SOV)."),
        "acord_forms": ["ACORD 125 — Commercial Applicant Info", "ACORD 140 — Property Section"],
        "documents": [
            "Application form (ACORD 125; ACORD 140 Property Section)",
            "Statement of Values (SOV) — address, construction, occupancy, protection, exposure (COPE) per location",
            "Property appraisal / valuation report (replacement cost)",
            "Building specifications: year built, construction type, roof type/age, square footage",
            "Fire protection details: sprinklers, alarms, fire department proximity",
            "Financial statements — last 2–3 years (P&L, balance sheet)",
            "Business Interruption worksheet (projected revenue, continuing expenses, extra expenses)",
            "Loss run reports — 3–5 years of prior claims history",
            "Equipment / machinery list with values",
            "Lease agreement (if tenant) or title deed (if owner)",
            "Flood zone certification / earthquake exposure (if applicable)",
            "Business continuity / disaster recovery plan",
        ],
    },
    {
        "id": "directors_officers",
        "slug": "do",
        "name": "Directors & Officers (D&O)",
        "short_name": "D&O",
        "checklist_lob": "do",
        "insurance_line": "directors_and_officers",
        "description": "Management liability for directors and officers — private or public company.",
        "uw_focus": ("Assess governance quality, litigation exposure, financial stability, board composition, and pending/past regulatory or M&A activity."),
        "acord_forms": ["ACORD or carrier-specific D&O application"],
        "documents": [
            "Application form (ACORD or carrier-specific D&O application)",
            "Audited or reviewed financial statements (last 2–3 years)",
            "Articles of Incorporation / Certificate of Formation",
            "Bylaws / Operating Agreement",
            "Organizational chart and cap table",
            "Board of Directors and officer résumés / bios",
            "Prior D&O policy declarations page (if renewing/replacing)",
            "Loss runs — claims history (5 years typical)",
            "Pending / past litigation disclosure statement",
            "Regulatory investigation disclosures (if any)",
            "For public companies: 10-K, proxy (DEF 14A), 8-K filings",
            "For private companies: funding round details, investor rights, term sheets",
            "Merger & acquisition activity disclosure (past/planned)",
        ],
    },
    {
        "id": "workers_comp",
        "slug": "workers-comp",
        "name": "Workers' Compensation",
        "short_name": "Workers' Comp",
        "checklist_lob": "workers_comp",
        "insurance_line": "workers_comp",
        "description": "Employee injury coverage with payroll class codes, e-mod, and safety programs.",
        "uw_focus": ("Review safety programs, injury history, industry hazard class, payroll by NCCI class, and experience modification."),
        "acord_forms": ["ACORD 130 — Workers Compensation Application"],
        "documents": [
            "Application form (ACORD 130)",
            "Payroll records by job classification code (NCCI class codes)",
            "Employee census: headcount, job titles, states of operation",
            "Experience Modification Rating (e-mod) worksheet",
            "Loss run reports — 3–5 years",
            "OSHA 300 and 300A logs",
            "Safety manual / written safety program",
            "Prior policy declarations page",
            "Subcontractor / 1099 usage details and their COIs",
            "Return-to-work program documentation (if any)",
        ],
    },
    {
        "id": "trade_credit",
        "slug": "trade-credit",
        "name": "Trade Credit Insurance",
        "short_name": "Trade Credit",
        "checklist_lob": "trade_credit",
        "insurance_line": "trade_credit",
        "description": "Protects receivables against buyer default — domestic and export exposures.",
        "uw_focus": ("Analyze buyer creditworthiness, customer concentration, AR aging, credit policy, and historical bad-debt experience."),
        "acord_forms": ["Carrier-specific trade credit application"],
        "documents": [
            "Application form (carrier-specific)",
            "Accounts Receivable Aging Report (current)",
            "Buyer / customer list with individual credit exposure amounts",
            "Historical bad debt / write-off report (3–5 years)",
            "Audited financial statements",
            "Credit management policy document (how limits are set/monitored)",
            "Domestic vs. export sales breakdown",
            "Top 10–20 customer concentration report",
            "Existing credit insurance policy (if renewing) and claims history",
            "Terms of sale / payment terms documentation",
        ],
    },
    {
        "id": "errors_omissions",
        "slug": "eo",
        "name": "Errors & Omissions (E&O)",
        "short_name": "E&O",
        "checklist_lob": "eo",
        "insurance_line": "errors_and_omissions",
        "description": "Professional liability for services and advice — profession-specific applications.",
        "uw_focus": ("Scrutinize nature of services, past claims, contract quality, revenue mix by service line, and risk-management procedures."),
        "acord_forms": ["ACORD 126 or carrier E&O application (profession-specific)"],
        "documents": [
            "Application form (profession-specific — e.g. ACORD 126 or carrier E&O app)",
            "Description of services / products and scope of operations",
            "Revenue breakdown by service line",
            "Sample client contracts / engagement letter template",
            "Loss run reports — 3–5 years",
            "Professional licenses and certifications",
            "Quality control / risk management procedures document",
            "Subcontractor / vendor agreements (if work is outsourced)",
            "Client complaint or grievance history",
            "Prior E&O policy declarations page (if renewing)",
        ],
    },
    {
        "id": "key_person",
        "slug": "key-person",
        "name": "Key Person Insurance",
        "short_name": "Key Person",
        "checklist_lob": "key_person",
        "insurance_line": "key_person",
        "description": "Life / disability on a critical individual whose loss would financially hurt the business.",
        "uw_focus": ("Evaluate the individual's health, financial impact on the business, coverage justification, and corporate authorization / buy-sell structure."),
        "acord_forms": ["Application + medical questionnaire for the insured individual"],
        "documents": [
            "Application form + medical questionnaire for the insured individual",
            "Paramedical exam / medical records (often required for larger amounts)",
            "Financial statements showing revenue / profit attributable to the key person",
            "Job description and valuation / justification of coverage amount",
            "Corporate resolution authorizing the policy purchase",
            "Buy-sell agreement (if policy funds a buyout)",
            "Loan / financing documents (if policy is collateral)",
            "Beneficiary designation form (usually the company itself)",
        ],
    },
]


def list_commercial_lines() -> list[dict[str, Any]]:
    return [
        {
            "id": line["id"],
            "slug": line["slug"],
            "name": line["name"],
            "short_name": line["short_name"],
            "checklist_lob": line["checklist_lob"],
            "insurance_line": line["insurance_line"],
            "description": line["description"],
            "document_count": len(line["documents"]),
            "acord_forms": list(line["acord_forms"]),
        }
        for line in COMMERCIAL_LINES
    ]


def get_commercial_line(line_id_or_slug: str) -> dict[str, Any] | None:
    raw = (line_id_or_slug or "").strip().lower()
    if not raw:
        return None
    dashed = raw.replace("_", "-")
    underscored = raw.replace("-", "_")
    for line in COMMERCIAL_LINES:
        candidates = {
            line["id"],
            line["slug"],
            line["checklist_lob"],
            line["insurance_line"],
            line["id"].replace("_", "-"),
            line["checklist_lob"].replace("_", "-"),
            line["insurance_line"].replace("_", "-"),
        }
        if raw in candidates or dashed in candidates or underscored in candidates:
            return {
                **line,
                "base_packet": list(BASE_PACKET),
                "uw_responsibilities": list(UW_CORE_RESPONSIBILITIES),
                "uw_question": ("If I take on this risk, what's the probability and cost of it going wrong, and what price makes that bet worthwhile for the insurer?"),
            }
    return None


def commercial_hub_payload() -> dict[str, Any]:
    return {
        "segment": "business_commercial",
        "title": "Business / Commercial Insurance",
        "summary": ("Commercial underwriting for property & BI, D&O, workers' compensation, trade credit, E&O, and key person — with line-specific document packs and UW workflow."),
        "base_packet": list(BASE_PACKET),
        "uw_responsibilities": list(UW_CORE_RESPONSIBILITIES),
        "lines": list_commercial_lines(),
    }
