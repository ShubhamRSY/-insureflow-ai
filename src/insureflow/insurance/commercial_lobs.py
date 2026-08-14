"""Business / Commercial Insurance LOB catalog: taxonomy + document packs + UW workflow.

Source of truth for the Commercial Insurance hub UI and LOB-aware package checklists.
Organized as categories → products → coverages for underwriter navigation.
"""

from __future__ import annotations

from typing import Any

# Shared base packet expected across nearly every commercial line
BASE_PACKET: list[str] = [
    "Completed ACORD application(s) relevant to the line(s) requested",
    "Financial statements — last 2–3 years (P&L, balance sheet)",
    "Loss run reports from prior carrier(s) — typically 3–5 years",
    "Business license / entity formation documents",
    "Organizational chart",
    "Description of business operations",
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

COMMERCIAL_CATEGORIES: list[dict[str, str]] = [
    {
        "id": "property",
        "name": "Property Insurance",
        "summary": "Buildings, contents, BI, marine, catastrophe, crime, and equipment risks.",
    },
    {
        "id": "liability",
        "name": "Liability Insurance",
        "summary": "Third-party bodily injury, property damage, professional, management, and cyber liability.",
    },
    {
        "id": "workforce",
        "name": "Workforce / Employee Insurance",
        "summary": "Workers' compensation, employer liability, and group / key-person benefits.",
    },
    {
        "id": "auto",
        "name": "Auto / Transportation Insurance",
        "summary": "Commercial auto, fleet, cargo, hired/non-owned, and garage risks.",
    },
    {
        "id": "financial",
        "name": "Financial / Credit Insurance",
        "summary": "Trade credit, surety bonds, and political risk.",
    },
    {
        "id": "specialty",
        "name": "Specialty / Industry-Specific Insurance",
        "summary": "Construction wrap-ups, aviation, agribusiness, event, IP, K&R, terrorism, recall, and supply chain.",
    },
    {
        "id": "alternative",
        "name": "Alternative Risk Transfer",
        "summary": "Captives, self-insured retention, and fronting arrangements for complex insureds.",
    },
    {
        "id": "package",
        "name": "Package / Bundled Policies",
        "summary": "BOP and commercial package policies combining multiple lines.",
    },
]


def _docs(*items: str) -> list[str]:
    return list(items)


def _coverage(cov_id: str, name: str, *documents: str) -> dict[str, Any]:
    return {"id": cov_id, "name": name, "documents": list(documents)}


def _normalize_coverages(coverages: list[Any] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, cov in enumerate(coverages or []):
        if isinstance(cov, dict):
            docs = list(cov.get("documents") or [])
            out.append(
                {
                    "id": str(cov.get("id") or f"coverage_{i}"),
                    "name": str(cov.get("name") or cov.get("id") or f"Coverage {i + 1}"),
                    "documents": docs,
                    "document_count": len(docs),
                }
            )
        else:
            out.append(
                {
                    "id": f"coverage_{i}",
                    "name": str(cov),
                    "documents": [],
                    "document_count": 0,
                }
            )
    return out


def flatten_line_documents(line: dict[str, Any]) -> list[str]:
    """Product docs + all coverage docs, de-duplicated, order preserved."""
    seen: set[str] = set()
    out: list[str] = []
    for doc in list(line.get("documents") or []):
        text = str(doc).strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    for cov in line.get("coverages") or []:
        docs = cov.get("documents") if isinstance(cov, dict) else []
        for doc in docs or []:
            text = str(doc).strip()
            if text and text not in seen:
                seen.add(text)
                out.append(text)
    return out


def _coverage_key(value: str | None) -> str:
    return (value or "").strip().lower().replace("-", "_").replace(" ", "_")


def get_line_coverage(line: dict[str, Any] | None, coverage_id: str | None) -> dict[str, Any] | None:
    """Return the coverage dict on ``line`` matching ``coverage_id``, if any."""
    if not line or not coverage_id:
        return None
    key = _coverage_key(coverage_id)
    if not key:
        return None
    for cov in line.get("coverages") or []:
        if not isinstance(cov, dict):
            continue
        if _coverage_key(str(cov.get("id") or "")) == key:
            return cov
    return None


def flatten_coverage_documents(line: dict[str, Any], coverage_id: str | None) -> list[str]:
    """Product base docs + only the selected coverage (not sibling coverages).

    Unknown / missing coverage_id falls back to the full product flatten so
    callers without a taxonomy picker stay backward compatible.
    """
    match = get_line_coverage(line, coverage_id)
    if match is None:
        return flatten_line_documents(line)
    seen: set[str] = set()
    out: list[str] = []
    for doc in list(line.get("documents") or []):
        text = str(doc).strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    for doc in match.get("documents") or []:
        text = str(doc).strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _line(
    *,
    id: str,
    slug: str,
    name: str,
    short_name: str,
    category_id: str,
    checklist_lob: str,
    insurance_line: str,
    description: str,
    uw_focus: str,
    documents: list[str],
    acord_forms: list[str] | None = None,
    coverages: list[dict[str, Any]] | None = None,
    status: str = "live",
    rating_line: str | None = None,
) -> dict[str, Any]:
    covs = _normalize_coverages(coverages)
    return {
        "id": id,
        "slug": slug,
        "name": name,
        "short_name": short_name,
        "category_id": category_id,
        "checklist_lob": checklist_lob,
        "insurance_line": insurance_line,
        "rating_line": rating_line or insurance_line,
        "description": description,
        "uw_focus": uw_focus,
        "acord_forms": list(acord_forms or []),
        "documents": list(documents),
        "coverages": covs,
        "status": status,  # live = full UW + LOB-scoped ML path; catalog retained only for legacy rows
    }


# ---------------------------------------------------------------------------
# Full commercial product catalog
# ---------------------------------------------------------------------------

COMMERCIAL_LINES: list[dict[str, Any]] = [
    # ===== 1. PROPERTY =====================================================
    _line(
        id="property_bi",
        slug="property-bi",
        name="Commercial Property Insurance",
        short_name="Property",
        category_id="property",
        checklist_lob="property",
        insurance_line="commercial_property",
        status="live",
        description="Building, contents, and related property coverages for commercial locations.",
        uw_focus="Evaluate construction, fire protection, location hazards (flood/earthquake), valuation adequacy, and COPE + SOV quality.",
        acord_forms=["ACORD 125 — Commercial Applicant Info", "ACORD 140 — Property Section"],
        documents=_docs(
            "Statement of Values (SOV) — per-location address, construction, occupancy, protection, exposure (COPE)",
            "ACORD 140 (Property Section)",
            "Property appraisal / replacement cost valuation",
            "Building specs: year built, construction type, roof age/type, square footage",
            "Fire protection report: sprinklers, alarms, hydrant distance, fire dept. response time",
            "Photos of exterior, roof, electrical panel, and any hazard storage areas",
            "Loss run reports (3–5 years)",
            "Lease agreement (tenant) or title deed (owner)",
            "Flood zone certificate / elevation certificate",
            "Financial statements (for BPP/contents valuation)",
        ),
        coverages=[
            _coverage(
                "building_structure",
                "Building/Structure Coverage",
                "Structure replacement cost appraisal",
                "Construction class / ISO construction type documentation",
            ),
            _coverage(
                "bpp",
                "Business Personal Property (BPP)",
                "Inventory/asset list with values",
                "Equipment purchase receipts or depreciation schedule",
            ),
            _coverage(
                "tib",
                "Tenant Improvements & Betterments",
                "Lease agreement showing tenant responsibility for improvements",
                "Itemized cost of improvements made",
            ),
            _coverage(
                "rc_vs_acv",
                "Replacement Cost vs. ACV Policies",
                "Independent appraisal supporting valuation basis chosen",
            ),
            _coverage(
                "named_vs_special",
                "Named Perils vs. All-Risk (Special Form)",
                "Peril-specific exposure data (e.g., wind/hail history for named-storm perils)",
            ),
        ],
    ),
    _line(
        id="business_interruption",
        slug="business-interruption",
        name="Business Interruption (Business Income) Insurance",
        short_name="BI / Income",
        category_id="property",
        checklist_lob="business_interruption",
        insurance_line="business_interruption",
        rating_line="commercial_property",
        description="Covers lost income and extra expense after a covered property loss.",
        uw_focus="Validate BI worksheet realism, dependent properties, indemnity period, and civil authority exposure.",
        acord_forms=["ACORD 125", "ACORD 140", "Business income worksheet"],
        documents=_docs(
            "Business Income worksheet (projected revenue, continuing expenses, extra expense)",
            "Financial statements — 2–3 years (P&L, balance sheet)",
            "Tax returns (sometimes requested to verify revenue)",
            "Supply chain/vendor dependency list (for contingent BI)",
            "Lease/rent obligations during interruption period",
            "Loss run reports (BI / property)",
            "Prior BI / property declarations",
            "Disaster recovery / continuity plan",
        ),
        coverages=[
            _coverage(
                "gross_earnings",
                "Gross Earnings Form",
                "Detailed gross earnings calculation worksheet",
            ),
            _coverage(
                "extra_expense",
                "Extra Expense Coverage",
                "Projected extra expense budget (temp location costs, equipment rental)",
            ),
            _coverage(
                "contingent_bi",
                "Contingent Business Interruption (supplier/customer dependency)",
                "List of key suppliers/customers and % revenue dependency",
                "Supplier financial health/credit reports",
            ),
            _coverage(
                "civil_authority",
                "Civil Authority Coverage",
                "Description of surrounding exposures that could trigger government-ordered closure",
            ),
        ],
    ),
    _line(
        id="builders_risk",
        slug="builders-risk",
        name="Builder's Risk Insurance",
        short_name="Builder's Risk",
        category_id="property",
        checklist_lob="builders_risk",
        insurance_line="builders_risk",
        rating_line="builders_risk",
        description="Covers buildings and materials during construction or renovation.",
        uw_focus="Assess construction type, project duration, site security, hot-work controls, and soft-cost exposure.",
        acord_forms=["ACORD 125", "ACORD 140", "Builder's risk supplemental"],
        documents=_docs(
            "Construction contract",
            "Project budget/cost breakdown",
            "Construction timeline/schedule",
            "General contractor's license and insurance certificates",
            "Site plans and blueprints",
            "Soil reports (for structural risk)",
            "Builder's risk application / supplemental",
            "Flood / wind / quake exposure for jobsite",
        ),
        coverages=[],
    ),
    _line(
        id="inland_marine",
        slug="inland-marine",
        name="Inland Marine Insurance",
        short_name="Inland Marine",
        category_id="property",
        checklist_lob="inland_marine",
        insurance_line="inland_marine",
        rating_line="inland_marine",
        description="Mobile property, equipment, installation, transit, and specialty floaters.",
        uw_focus="Review scheduled values, mobility/theft controls, transit routes, and installation exposure windows.",
        acord_forms=["ACORD 125", "ACORD 146 — Inland Marine"],
        documents=_docs(
            "Equipment schedule with serial numbers and values",
            "Purchase invoices/receipts",
            "Usage/location patterns (where equipment travels)",
            "Loss run reports specific to equipment theft/damage",
            "Inland marine application",
            "Storage / security / GPS tracking details",
            "Prior inland marine declarations",
            "Appraisals for scheduled specialty items",
        ),
        coverages=[
            _coverage(
                "contractors_equipment",
                "Contractor's Equipment Floater",
                "Equipment list with make/model/serial number/value",
            ),
            _coverage(
                "installation",
                "Installation Floater",
                "Installation contract and project value",
            ),
            _coverage(
                "transit_cargo",
                "Transit/Cargo Floater",
                "Shipping routes and typical cargo value per shipment",
            ),
            _coverage(
                "fine_arts",
                "Fine Arts/Valuable Papers Floater",
                "Itemized appraisal of each item/document",
            ),
        ],
    ),
    _line(
        id="ocean_marine",
        slug="ocean-marine",
        name="Ocean Marine Insurance",
        short_name="Ocean Marine",
        category_id="property",
        checklist_lob="ocean_marine",
        insurance_line="ocean_marine",
        rating_line="commercial_property",
        description="Hull, cargo, and P&I for ocean and coastal marine exposures.",
        uw_focus="Evaluate vessel class, trading limits, cargo types, crew experience, and P&I club arrangements.",
        acord_forms=["Marine application (carrier-specific)", "ACORD 125"],
        documents=_docs(
            "Vessel documentation (registration, survey report)",
            "Voyage/route plans",
            "Cargo manifests",
            "Crew certification records",
            "Marine application (hull / cargo / P&I)",
            "Loss runs and casualty history",
            "P&I club or prior marine policy history",
            "Prior ocean marine declarations",
        ),
        coverages=[
            _coverage("hull", "Hull Insurance", "Vessel survey/condition report"),
            _coverage("cargo", "Cargo Insurance", "Bill of lading, cargo value declaration"),
            _coverage("pi", "Protection & Indemnity (P&I)", "Crew list and employment records"),
        ],
    ),
    _line(
        id="equipment_breakdown",
        slug="equipment-breakdown",
        name="Equipment Breakdown (Boiler & Machinery) Insurance",
        short_name="Equip. Breakdown",
        category_id="property",
        checklist_lob="equipment_breakdown",
        insurance_line="equipment_breakdown",
        rating_line="commercial_property",
        description="Sudden and accidental breakdown of boilers, machinery, and critical equipment.",
        uw_focus="Review equipment age/maintenance, inspection certificates, and business interruption from outage.",
        acord_forms=["ACORD 125", "Equipment breakdown supplemental"],
        documents=_docs(
            "Equipment inspection/maintenance records",
            "Age and service history of covered equipment",
            "Manufacturer specs and warranty documents",
            "Prior EB loss runs",
            "Equipment schedule with values",
            "Financial statements",
            "Prior policy declarations",
            "Equipment breakdown application",
        ),
        coverages=[],
    ),
    _line(
        id="flood_commercial",
        slug="flood-commercial",
        name="Flood Insurance (Commercial)",
        short_name="Flood",
        category_id="property",
        checklist_lob="flood",
        insurance_line="flood_commercial",
        rating_line="commercial_property",
        description="Commercial flood coverage — NFIP and/or private market excess flood.",
        uw_focus="Confirm flood zone, elevation, prior flood losses, and contents vs. building values.",
        acord_forms=["Flood application", "Elevation certificate"],
        documents=_docs(
            "FEMA Flood Zone determination",
            "Elevation certificate",
            "Prior flood loss history",
            "Building and contents values",
            "Photos of lowest floor / utilities",
            "Lease or ownership proof",
            "Existing NFIP or private flood declarations",
            "ACORD / flood application",
        ),
        coverages=[],
    ),
    _line(
        id="earthquake_commercial",
        slug="earthquake-commercial",
        name="Earthquake Insurance (Commercial)",
        short_name="Earthquake",
        category_id="property",
        checklist_lob="earthquake",
        insurance_line="earthquake_commercial",
        rating_line="commercial_property",
        description="Earthquake shake and related earth-movement coverage for commercial risks.",
        uw_focus="Assess seismic zone, construction/retrofit, soil, and deductible/attachment structure.",
        acord_forms=["Earthquake supplemental", "ACORD 140"],
        documents=_docs(
            "Seismic zone/fault line proximity report",
            "Building retrofit/reinforcement documentation",
            "Structural engineering report",
            "SOV with construction and soil details",
            "Prior quake / earth-movement loss history",
            "Building and contents values",
            "Financial statements",
            "Prior earthquake declarations",
        ),
        coverages=[],
    ),
    _line(
        id="crime",
        slug="crime",
        name="Crime Insurance",
        short_name="Crime",
        category_id="property",
        checklist_lob="crime",
        insurance_line="crime",
        rating_line="crime",
        description="Employee dishonesty, forgery, burglary/robbery, and computer/funds-transfer fraud.",
        uw_focus="Review internal controls, dual authorization, inventory/cash handling, and prior fidelity losses.",
        acord_forms=["ACORD 125", "Crime / fidelity application"],
        documents=_docs(
            "Internal control procedures document",
            "Employee background check policy",
            "Cash handling procedures",
            "Loss history related to theft/fraud",
            "Crime / fidelity application",
            "Prior crime policy declarations",
            "Employee count and roles with financial authority",
            "Audit / CPA management letter (if any)",
        ),
        coverages=[
            _coverage(
                "employee_dishonesty",
                "Employee Dishonesty/Fidelity Coverage",
                "List of bonded positions/employees with access to funds",
            ),
            _coverage(
                "forgery",
                "Forgery & Alteration Coverage",
                "Check-signing authorization policy",
            ),
            _coverage(
                "burglary_robbery",
                "Burglary & Robbery Coverage",
                "Security system documentation (alarms, cameras, safes)",
            ),
            _coverage(
                "computer_fraud",
                "Computer Fraud/Funds Transfer Fraud",
                "IT security policy, dual-authorization protocols for wire transfers",
            ),
        ],
    ),
    _line(
        id="ordinance_or_law",
        slug="ordinance-or-law",
        name="Ordinance or Law Coverage",
        short_name="Ordinance or Law",
        category_id="property",
        checklist_lob="ordinance_or_law",
        insurance_line="ordinance_or_law",
        rating_line="commercial_property",
        description="Covers the cost of rebuilding to current code after a loss (endorsement or standalone).",
        uw_focus="Compare building age and construction to current code; quantify undamaged portion, demolition, and increased cost of construction.",
        acord_forms=["ACORD 140", "Ordinance or law supplemental"],
        documents=_docs(
            "Ordinance or law coverage application / endorsement request",
            "Building age vs. current code requirements analysis",
            "Construction type, stories, and occupancy details",
            "Replacement cost appraisal and demolition cost estimate",
            "Local building code / jurisdiction summary",
            "Prior property loss runs",
            "SOV for subject location(s)",
            "Prior property / ordinance or law declarations",
        ),
        coverages=[
            _coverage(
                "undamaged_portion",
                "Coverage for Undamaged Portion",
                "Estimate of value of undamaged portion that may require demolition",
            ),
            _coverage(
                "demolition_cost",
                "Demolition Cost",
                "Demolition and debris removal cost estimate",
            ),
            _coverage(
                "increased_cost_construction",
                "Increased Cost of Construction",
                "Code-upgrade cost differential vs. like-kind rebuild",
            ),
        ],
    ),
    _line(
        id="rent_loss_of_rents",
        slug="rent-loss-of-rents",
        name="Rent / Loss of Rents Insurance",
        short_name="Loss of Rents",
        category_id="property",
        checklist_lob="rent_loss_of_rents",
        insurance_line="rent_loss_of_rents",
        rating_line="commercial_property",
        description="Standalone business-income style cover for landlords — lost rental income after a covered loss.",
        uw_focus="Validate rent roll quality, lease terms, vacancy, and indemnity period realism.",
        acord_forms=["Business income / rents worksheet", "ACORD 140"],
        documents=_docs(
            "Loss of rents / rental income application",
            "Lease agreements for all units / tenants",
            "Current rent roll (tenant, rent, term, escalations)",
            "Historical occupancy / vacancy rates",
            "Property SOV and location details",
            "Prior property / rents loss runs",
            "Financial statements showing rental income",
            "Prior loss of rents / property declarations",
        ),
        coverages=[],
    ),
    _line(
        id="dic_excess_flood",
        slug="dic-excess-flood",
        name="Difference in Conditions (DIC) / Excess Flood",
        short_name="DIC / Excess Flood",
        category_id="property",
        checklist_lob="dic_excess_flood",
        insurance_line="dic_excess_flood",
        rating_line="commercial_property",
        description="Fills gaps between primary property and named-peril exclusions (flood, quake, and other DIC perils).",
        uw_focus="Review primary policy exclusions specifically; structure excess flood/quake attachments and DIC peril scope.",
        acord_forms=["DIC / excess flood application", "Primary policy schedule"],
        documents=_docs(
            "DIC / excess flood application",
            "Primary property policy declarations and exclusion schedule",
            "Flood zone / elevation certificate (for excess flood)",
            "Earthquake / seismic exposure notes (if quake DIC)",
            "SOV with TIV by location and peril",
            "Prior flood / quake / DIC loss history",
            "Underlying deductibles and sublimits schedule",
            "Prior DIC / excess flood declarations",
        ),
        coverages=[
            _coverage(
                "excess_flood",
                "Excess Flood",
                "NFIP or primary flood declarations and requested excess limit/attachment",
            ),
            _coverage(
                "dic_all_risk_gaps",
                "DIC All-Risk Gap Cover",
                "Marked-up primary policy exclusions the DIC is intended to fill",
            ),
        ],
    ),
    # ===== 2. LIABILITY ====================================================
    _line(
        id="general_liability",
        slug="general-liability",
        name="General Liability (CGL)",
        short_name="CGL",
        category_id="liability",
        checklist_lob="general_liability",
        insurance_line="general_liability",
        status="live",
        description="Premises/operations, products & completed operations, and personal/advertising injury.",
        uw_focus="Evaluate operations hazard class, contractual risk transfer, products exposure, and loss history.",
        acord_forms=["ACORD 125", "ACORD 126 — Commercial General Liability"],
        documents=_docs(
            "ACORD 126 (General Liability Section)",
            "Description of operations",
            "Revenue by class of business",
            "Loss run reports (3–5 years)",
            "Subcontractor agreements & their Certificates of Insurance (COI)",
            "Safety program documentation",
            "Prior GL policy declarations",
            "Financial statements — last 2–3 years",
        ),
        coverages=[
            _coverage(
                "premises_ops",
                "Premises/Operations Liability",
                "Site visit/inspection report",
                "Foot traffic estimates (for slip-and-fall exposure)",
            ),
            _coverage(
                "products_completed",
                "Products & Completed Operations",
                "Product description and manufacturing process",
                "Quality control procedures",
                "Product recall history",
            ),
            _coverage(
                "personal_advertising",
                "Personal & Advertising Injury",
                "Marketing materials/advertising samples",
                "Website content review (for defamation/IP exposure)",
            ),
        ],
    ),
    _line(
        id="product_liability",
        slug="product-liability",
        name="Product Liability Insurance",
        short_name="Product Liability",
        category_id="liability",
        checklist_lob="product_liability",
        insurance_line="product_liability",
        rating_line="general_liability",
        description="Liability arising from manufactured, distributed, or sold products.",
        uw_focus="Scrutinize product type, recalls, warnings/labels, distribution geography, and claims severity.",
        acord_forms=["ACORD 126", "Products liability supplemental"],
        documents=_docs(
            "Product specifications and safety testing reports",
            "Manufacturing/quality control documentation",
            "Product liability claims history",
            "Certificates of compliance (UL, CE, etc.)",
            "Products liability application / supplemental",
            "Product list with sales by SKU / category",
            "Warning labels / IFU / SDS samples",
            "Prior product liability declarations",
        ),
        coverages=[],
    ),
    _line(
        id="errors_omissions",
        slug="eo",
        name="Professional Liability / E&O",
        short_name="E&O",
        category_id="liability",
        checklist_lob="eo",
        insurance_line="errors_and_omissions",
        status="live",
        description="Professional liability for services and advice — profession-specific applications.",
        uw_focus="Scrutinize nature of services, past claims, contract quality, revenue mix by service line, and risk-management procedures.",
        acord_forms=["ACORD 126 or carrier E&O application (profession-specific)"],
        documents=_docs(
            "Description of services offered",
            "Sample client contracts/engagement letters",
            "Professional licenses/certifications",
            "Loss run reports",
            "Quality control/risk management procedures",
            "E&O application (ACORD 126 / carrier)",
            "Prior E&O policy declarations",
            "Revenue breakdown by service line",
        ),
        coverages=[
            _coverage(
                "medical_malpractice",
                "Medical Malpractice",
                "Medical license and board certification",
                "Hospital privileges documentation",
                "Patient volume/procedure mix data",
                "NPDB report",
            ),
            _coverage(
                "legal_malpractice",
                "Legal Malpractice",
                "Bar admission/license verification",
                "Practice area breakdown",
                "Conflict-check procedures document",
            ),
            _coverage(
                "technology_eo",
                "Technology E&O",
                "Service/product description (SaaS, consulting, etc.)",
                "Client contract templates with liability caps",
                "Data handling/security policy",
            ),
            _coverage(
                "real_estate_eo",
                "Real Estate E&O",
                "Real estate license",
                "Transaction volume/value history",
                "Errors/complaint history",
            ),
            _coverage(
                "agents_brokers_eo",
                "Insurance Agents/Brokers E&O",
                "E&O license and appointment letters",
                "Book of business summary",
                "Carrier contracts",
            ),
        ],
    ),
    _line(
        id="architects_engineers",
        slug="architects-engineers",
        name="Architects & Engineers (A&E) Professional Liability",
        short_name="A&E Professional",
        category_id="liability",
        checklist_lob="architects_engineers",
        insurance_line="architects_engineers",
        rating_line="errors_and_omissions",
        description="Design professional liability distinct from general E&O — architects, engineers, and related design firms.",
        uw_focus="Review design contracts, project portfolio hazard mix, peer review processes, and prior design-defect claims.",
        acord_forms=["A&E professional liability application"],
        documents=_docs(
            "A&E professional liability application",
            "Design contracts / professional services agreements",
            "Project portfolio (types, values, geographies, 3–5 years)",
            "Peer review / QA/QC process documentation",
            "Professional licenses and firm registrations",
            "Loss runs — design professional claims",
            "Revenue by discipline (architecture, civil, structural, MEP, etc.)",
            "Prior A&E / professional liability declarations",
        ),
        coverages=[
            _coverage(
                "design_contracts",
                "Design Contract Review",
                "Sample design contracts with limitation of liability and indemnity clauses",
            ),
            _coverage(
                "peer_review",
                "Peer Review Processes",
                "Written peer review / independent design review procedures",
            ),
        ],
    ),
    _line(
        id="miscellaneous_professional",
        slug="miscellaneous-professional",
        name="Miscellaneous Professional Liability (MPL)",
        short_name="MPL",
        category_id="liability",
        checklist_lob="miscellaneous_professional",
        insurance_line="miscellaneous_professional",
        rating_line="errors_and_omissions",
        description="Catch-all professional liability for professions not otherwise classified (consultants, HR firms, etc.).",
        uw_focus="Define services precisely, review engagement letters, and assess claim patterns for the specific profession.",
        acord_forms=["MPL / miscellaneous professional application"],
        documents=_docs(
            "MPL application with detailed services description",
            "Sample client contracts / engagement letters",
            "Revenue breakdown by service type",
            "Professional licenses / certifications (if any)",
            "Quality control / risk management procedures",
            "Loss runs — professional liability",
            "Marketing materials / website service claims",
            "Prior MPL / E&O declarations",
        ),
        coverages=[],
    ),
    _line(
        id="directors_officers",
        slug="do",
        name="Directors & Officers (D&O) Liability",
        short_name="D&O",
        category_id="liability",
        checklist_lob="do",
        insurance_line="directors_and_officers",
        status="live",
        description="Management liability for directors and officers — private or public company.",
        uw_focus="Assess governance quality, litigation exposure, financial stability, board composition, and pending/past regulatory or M&A activity.",
        acord_forms=["ACORD or carrier-specific D&O application"],
        documents=_docs(
            "Audited/reviewed financial statements",
            "Articles of Incorporation, Bylaws",
            "Cap table / ownership structure",
            "Board & officer bios/resumes",
            "Litigation and regulatory action disclosure",
            "Prior D&O policy + loss runs",
            "SEC filings (if public): 10-K, DEF 14A, 8-K",
            "D&O application (ACORD or carrier-specific)",
            "Organizational chart",
            "Merger & acquisition activity disclosure (past/planned)",
            "For private companies: funding round details, investor rights, term sheets",
            "Pending / past litigation disclosure statement",
        ),
        coverages=[
            _coverage("side_a", "Side A (individual protection)", "Indemnification agreement copies"),
            _coverage("side_b", "Side B (company reimbursement)", "Corporate indemnification bylaws"),
            _coverage(
                "side_c",
                "Side C (entity/securities coverage)",
                "Securities offering documents (if applicable)",
            ),
        ],
    ),
    _line(
        id="epli",
        slug="epli",
        name="Employment Practices Liability (EPLI)",
        short_name="EPLI",
        category_id="liability",
        checklist_lob="epli",
        insurance_line="epli",
        rating_line="errors_and_omissions",
        description="Wrongful termination, discrimination/harassment, and retaliation claims.",
        uw_focus="Review HR policies, employee handbook, prior EEOC/claims, and workforce demographics.",
        acord_forms=["EPLI application (carrier-specific)"],
        documents=_docs(
            "Employee handbook",
            "HR policies (hiring, termination, discipline)",
            "EEOC/charge history",
            "Prior EPLI claims",
            "Employee headcount and turnover rate",
            "EPLI application",
            "Financial statements",
            "Prior EPLI declarations",
        ),
        coverages=[
            _coverage(
                "wrongful_termination",
                "Wrongful Termination",
                "Termination policy/procedure documentation",
            ),
            _coverage(
                "discrimination_harassment",
                "Discrimination/Harassment",
                "Anti-harassment training records",
                "Complaint/investigation procedures",
            ),
            _coverage(
                "retaliation",
                "Retaliation Claims",
                "Whistleblower policy documentation",
            ),
        ],
    ),
    _line(
        id="fiduciary_liability",
        slug="fiduciary-liability",
        name="Fiduciary Liability Insurance",
        short_name="Fiduciary",
        category_id="liability",
        checklist_lob="fiduciary",
        insurance_line="fiduciary_liability",
        rating_line="directors_and_officers",
        description="Liability for ERISA and employee-benefit plan fiduciaries.",
        uw_focus="Assess plan assets, Form 5500, prior fiduciary claims, and investment committee governance.",
        acord_forms=["Fiduciary liability application"],
        documents=_docs(
            "Plan documents (401(k), pension, health plan)",
            "Form 5500 filings",
            "Plan administrator/trustee list",
            "ERISA compliance documentation",
            "Fiduciary liability application",
            "Plan asset values and investment policy",
            "Prior fiduciary / ERISA claims",
            "Prior fiduciary policy declarations",
        ),
        coverages=[],
    ),
    _line(
        id="cyber_liability",
        slug="cyber",
        name="Cyber Liability Insurance",
        short_name="Cyber",
        category_id="liability",
        checklist_lob="cyber",
        insurance_line="cyber_liability",
        rating_line="cyber_liability",
        description="First-party breach response / BI and third-party liability for cyber events.",
        uw_focus="Evaluate security controls, MFA, backups, ransomware readiness, and PII/PHI volume.",
        acord_forms=["Cyber application (carrier-specific)"],
        documents=_docs(
            "Network security questionnaire (extensive — often 20-50 questions)",
            "IT infrastructure diagram",
            "Data inventory (types of PII/PHI held, volume of records)",
            "Incident response plan",
            "Penetration test/vulnerability scan results",
            "Prior breach history",
            "Vendor/third-party risk management policy",
            "Employee cybersecurity training records",
            "Backup and disaster recovery documentation",
        ),
        coverages=[
            _coverage(
                "first_party",
                "First-Party Coverage (data breach response, business interruption)",
                "Business interruption estimate from system downtime",
                "Data restoration cost estimates",
            ),
            _coverage(
                "third_party",
                "Third-Party Coverage (liability to affected parties)",
                "Client/customer data volume and sensitivity classification",
            ),
        ],
    ),
    _line(
        id="umbrella",
        slug="umbrella",
        name="Umbrella / Excess Liability Insurance",
        short_name="Umbrella",
        category_id="liability",
        checklist_lob="umbrella",
        insurance_line="umbrella",
        status="live",
        description="Excess limits over primary GL, auto, and employer liability schedules.",
        uw_focus="Verify underlying limits/schedules, drop-down triggers, and high-severity exposure classes.",
        acord_forms=["ACORD 131 — Umbrella", "Underlying schedule"],
        documents=_docs(
            "Underlying policy declarations pages (GL, Auto, Employer's Liability)",
            "Loss run reports across all underlying lines",
            "Confirmation of underlying limits maintained",
            "Umbrella / excess application (ACORD 131)",
            "Schedule of underlying policies and limits",
            "Operations description and exposure summary",
            "Financial statements",
            "Prior umbrella / excess declarations",
        ),
        coverages=[],
    ),
    _line(
        id="pollution",
        slug="pollution",
        name="Pollution / Environmental Liability",
        short_name="Pollution",
        category_id="liability",
        checklist_lob="pollution",
        insurance_line="pollution_liability",
        rating_line="general_liability",
        description="Contractor's, site, and storage-tank environmental liability.",
        uw_focus="Review site history, Phase I/II ESAs, tank inventory, and remediation / claims history.",
        acord_forms=["Pollution / environmental application"],
        documents=_docs(
            "Environmental site assessment (Phase I/II ESA)",
            "List of chemicals/hazardous materials stored or used",
            "Waste disposal records and manifests",
            "Regulatory compliance history (EPA violations, if any)",
            "Pollution / environmental application",
            "Prior pollution claims and regulatory actions",
            "Financial statements",
            "Prior pollution policy declarations",
        ),
        coverages=[
            _coverage(
                "contractors_pollution",
                "Contractor's Pollution Liability",
                "Scope of work involving soil/groundwater exposure",
                "Subcontractor pollution exposure",
            ),
            _coverage(
                "site_pollution",
                "Site Pollution Liability",
                "Site history/prior use report",
                "Remediation records (if any)",
            ),
            _coverage(
                "storage_tank",
                "Storage Tank Liability",
                "Tank registration and inspection records",
                "Leak detection system documentation",
            ),
        ],
    ),
    _line(
        id="liquor_liability",
        slug="liquor-liability",
        name="Liquor Liability Insurance",
        short_name="Liquor",
        category_id="liability",
        checklist_lob="liquor",
        insurance_line="liquor_liability",
        rating_line="general_liability",
        description="Liability arising from selling, serving, or furnishing alcoholic beverages.",
        uw_focus="Assess alcohol sales mix, training (TIPS), hours, prior dram-shop claims, and security.",
        acord_forms=["Liquor liability supplemental", "ACORD 126"],
        documents=_docs(
            "Liquor license copy",
            "Alcohol sales as % of total revenue",
            "Server training certification (e.g., TIPS/ServSafe)",
            "Incident/claims history",
            "Liquor liability application / supplemental",
            "Hours of operation and entertainment description",
            "Security / ID-check procedures",
            "Prior liquor liability declarations",
        ),
        coverages=[],
    ),
    _line(
        id="media_liability",
        slug="media-liability",
        name="Media Liability Insurance",
        short_name="Media",
        category_id="liability",
        checklist_lob="media",
        insurance_line="media_liability",
        rating_line="errors_and_omissions",
        description="Defamation, privacy, IP, and content-related liability for media/publishers.",
        uw_focus="Review content types, clearance procedures, prior IP/defamation claims, and distribution reach.",
        acord_forms=["Media liability application"],
        documents=_docs(
            "Content description (publishing, broadcast, digital media)",
            "Editorial review/fact-checking process documentation",
            "Prior defamation/IP infringement claims",
            "Media liability application",
            "Revenue by content type",
            "Sample contracts with freelancers / talent",
            "Take-down / retraction policy",
            "Prior media liability declarations",
        ),
        coverages=[],
    ),
    # ===== 3. WORKFORCE ====================================================
    _line(
        id="workers_comp",
        slug="workers-comp",
        name="Workers' Compensation Insurance",
        short_name="Workers' Comp",
        category_id="workforce",
        checklist_lob="workers_comp",
        insurance_line="workers_comp",
        status="live",
        description="Employee injury coverage with payroll class codes, e-mod, and safety programs.",
        uw_focus="Review safety programs, injury history, industry hazard class, payroll by NCCI class, and experience modification.",
        acord_forms=["ACORD 130 — Workers Compensation Application"],
        documents=_docs(
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
        ),
        coverages=[],
    ),
    _line(
        id="employers_liability",
        slug="employers-liability",
        name="Employer's Liability Insurance",
        short_name="Employer's Liability",
        category_id="workforce",
        checklist_lob="employers_liability",
        insurance_line="employers_liability",
        rating_line="workers_comp",
        description="Employer liability for employee injury claims outside workers' compensation exclusivity.",
        uw_focus="Coordinate with WC, review dual-capacity / third-party-over exposure, and EL limits adequacy.",
        acord_forms=["ACORD 130", "Employers liability limits schedule"],
        documents=_docs(
            "Application form (ACORD 130)",
            "Payroll records by job classification code (NCCI class codes)",
            "Employee census: headcount, job titles, states of operation",
            "Experience Modification Rating (e-mod) worksheet",
            "Loss run reports — 3–5 years",
            "OSHA 300 and 300A logs",
            "Safety manual / written safety program",
            "Employment contracts",
            "Prior WC/EL declarations",
        ),
        coverages=[],
    ),
    _line(
        id="group_health",
        slug="group-health",
        name="Group Health Insurance",
        short_name="Group Health",
        category_id="workforce",
        checklist_lob="group_health",
        insurance_line="group_health",
        rating_line="key_person",
        description="Employer-sponsored medical benefits — fully insured or self-funded.",
        uw_focus="Review census demographics, claims experience, plan design, and stop-loss attachment (if self-funded).",
        acord_forms=["Group health application / RFP"],
        documents=_docs(
            "Group health application / RFP",
            "Employee census (age, tier, ZIP, status)",
            "Current plan design and rates",
            "Claims experience (24–36 months)",
            "Large claim / shock loss listing",
            "Contribution strategy and eligibility rules",
            "Stop-loss policy (if self-funded)",
            "Prior carrier renewal package",
        ),
        coverages=[
            _coverage(
                "hmo_ppo",
                "HMO/PPO Plans",
                "Network access / provider directory summary",
                "Plan benefit summary (SBC)",
            ),
            _coverage(
                "hdhp",
                "High-Deductible Health Plans (HDHP)",
                "HSA eligibility and contribution design",
                "Deductible / out-of-pocket schedule",
            ),
            _coverage(
                "self_funded",
                "Self-Funded Plans",
                "Stop-loss policy and attachment points",
                "Claims administration (TPA) agreement",
            ),
        ],
    ),
    _line(
        id="group_life",
        slug="group-life",
        name="Group Life Insurance",
        short_name="Group Life",
        category_id="workforce",
        checklist_lob="group_life",
        insurance_line="group_life",
        rating_line="key_person",
        description="Employer-sponsored group term life and AD&D benefits.",
        uw_focus="Assess census ages, benefit multiples, participation, and high-face exceptions.",
        acord_forms=["Group life application"],
        documents=_docs(
            "Group life application",
            "Employee census with salaries / face amounts",
            "Benefit schedule (basic + voluntary)",
            "Participation / enrollment report",
            "Prior claims experience",
            "Evidence of insurability procedures",
            "Prior group life declarations",
            "Company financials / stability notes",
        ),
        coverages=[],
    ),
    _line(
        id="group_disability",
        slug="group-disability",
        name="Group Disability Insurance",
        short_name="Group Disability",
        category_id="workforce",
        checklist_lob="group_disability",
        insurance_line="group_disability",
        rating_line="key_person",
        description="Short-term and long-term group disability income benefits.",
        uw_focus="Review occupation mix, elimination periods, benefit %, and prior LTD claim duration.",
        acord_forms=["Group disability application"],
        documents=_docs(
            "Group disability application (STD/LTD)",
            "Census with occupations and salaries",
            "Plan design (elimination, benefit %, max)",
            "Prior STD/LTD claims experience",
            "Return-to-work / absence management program",
            "Participation rates",
            "Prior disability declarations",
            "Financial statements",
        ),
        coverages=[
            _coverage(
                "std",
                "Short-Term Disability (STD)",
                "STD plan design (elimination period, benefit duration)",
                "Prior STD claims experience",
            ),
            _coverage(
                "ltd",
                "Long-Term Disability (LTD)",
                "LTD plan design (elimination, benefit %, max)",
                "Prior LTD claims duration and offsets",
            ),
        ],
    ),
    _line(
        id="key_person",
        slug="key-person",
        name="Key Person Insurance",
        short_name="Key Person",
        category_id="workforce",
        checklist_lob="key_person",
        insurance_line="key_person",
        status="live",
        description="Life / disability on a critical individual whose loss would financially hurt the business.",
        uw_focus="Evaluate the individual's health, financial impact on the business, coverage justification, and corporate authorization / buy-sell structure.",
        acord_forms=["Application + medical questionnaire for the insured individual"],
        documents=_docs(
            "Application form + medical questionnaire for the insured individual",
            "Paramedical exam / medical records (often required for larger amounts)",
            "Financial statements showing revenue / profit attributable to the key person",
            "Job description and valuation / justification of coverage amount",
            "Corporate resolution authorizing the policy purchase",
            "Buy-sell agreement (if policy funds a buyout)",
            "Loan / financing documents (if policy is collateral)",
            "Beneficiary designation form (usually the company itself)",
        ),
        coverages=[],
    ),
    _line(
        id="business_overhead",
        slug="business-overhead",
        name="Business Overhead Expense Insurance",
        short_name="BOE",
        category_id="workforce",
        checklist_lob="business_overhead",
        insurance_line="business_overhead_expense",
        rating_line="key_person",
        description="Covers fixed business expenses if an owner/professional is disabled.",
        uw_focus="Validate fixed expense schedule, elimination period, and alignment with disability policy.",
        acord_forms=["BOE / disability overhead application"],
        documents=_docs(
            "Business overhead expense application",
            "Schedule of fixed monthly expenses",
            "Financial statements / P&L",
            "Medical questionnaire for insured owner",
            "Job description and ownership %",
            "Existing disability / key person policies",
            "Lease and loan payment documentation",
            "Prior BOE declarations (if any)",
        ),
        coverages=[],
    ),
    _line(
        id="voluntary_benefits",
        slug="voluntary-benefits",
        name="Voluntary / Supplemental Benefits",
        short_name="Voluntary Benefits",
        category_id="workforce",
        checklist_lob="voluntary_benefits",
        insurance_line="voluntary_benefits",
        rating_line="key_person",
        description="Employee-paid dental, vision, accident, and critical illness benefits.",
        uw_focus="Review census participation assumptions, plan designs, and employer contribution (if any).",
        acord_forms=["Voluntary benefits RFP / applications"],
        documents=_docs(
            "Voluntary benefits RFP / applications",
            "Employee census",
            "Current dental / vision / accident plan designs",
            "Participation history",
            "Rate history and claims (if experience-rated)",
            "Enrollment communications samples",
            "Prior carrier schedules",
            "Employer contribution policy",
        ),
        coverages=[
            _coverage("dental", "Dental", "Dental plan design and network summary"),
            _coverage("vision", "Vision", "Vision plan design and exam/frame schedule"),
            _coverage(
                "accident_ci",
                "Accident/Critical Illness",
                "Accident / critical illness benefit schedule",
            ),
        ],
    ),
    # ===== 4. AUTO / TRANSPORTATION ========================================
    _line(
        id="commercial_auto",
        slug="commercial-auto",
        name="Commercial Auto Insurance",
        short_name="Commercial Auto",
        category_id="auto",
        checklist_lob="commercial_auto",
        insurance_line="commercial_auto",
        rating_line="commercial_auto",
        description="Liability, collision, and comprehensive for business-owned autos.",
        uw_focus="Review vehicle mix, driver MVRs, radius, cargo, and loss frequency/severity.",
        acord_forms=["ACORD 127 — Business Auto", "ACORD 137 / 163 as needed"],
        documents=_docs(
            "Application form (ACORD 127 / 137 / 163 as applicable)",
            "Vehicle schedule (VIN, year, make, model, GVW, garaging ZIP)",
            "Driver schedule (name, DOB, license #, state, years experience)",
            "MVRs for all listed drivers",
            "Loss runs — 3–5 years",
            "Radius of operation / usage description",
            "Maintenance / safety program documentation",
            "Prior commercial auto declarations",
        ),
        coverages=[
            _coverage(
                "liability",
                "Liability Coverage",
                "Driver MVRs and motor carrier filings (if applicable)",
            ),
            _coverage(
                "collision",
                "Collision Coverage",
                "Vehicle values and deductible elections",
            ),
            _coverage(
                "comprehensive",
                "Comprehensive Coverage",
                "Garaging / theft-protection documentation",
            ),
        ],
    ),
    _line(
        id="fleet",
        slug="fleet",
        name="Fleet Insurance",
        short_name="Fleet",
        category_id="auto",
        checklist_lob="fleet",
        insurance_line="fleet",
        rating_line="commercial_auto",
        description="Program coverage for larger commercial vehicle fleets.",
        uw_focus="Assess fleet size growth, telematics, driver hiring standards, and catastrophic loss potential.",
        acord_forms=["ACORD 127", "Fleet schedule"],
        documents=_docs(
            "Application form (ACORD 127 / 137 / 163 as applicable)",
            "Vehicle schedule (VIN, year, make, model, GVW, garaging ZIP)",
            "Driver schedule (name, DOB, license #, state, years experience)",
            "MVRs for all listed drivers",
            "Loss runs — 3–5 years",
            "Radius of operation / usage description",
            "Maintenance / safety program documentation",
            "Prior commercial auto declarations",
            "Fleet safety / telematics program summary",
            "Driver hiring and MVR monitoring policy",
        ),
        coverages=[],
    ),
    _line(
        id="hnoa",
        slug="hnoa",
        name="Hired & Non-Owned Auto (HNOA)",
        short_name="HNOA",
        category_id="auto",
        checklist_lob="hnoa",
        insurance_line="hnoa",
        rating_line="commercial_auto",
        description="Liability for hired vehicles and employee-owned autos used in business.",
        uw_focus="Quantify employee personal-auto use, delivery exposure, and primary vs. excess structure.",
        acord_forms=["ACORD 127 HNOA section", "HNOA supplemental"],
        documents=_docs(
            "HNOA / business auto application",
            "Estimate of hired auto spend and employee vehicle use",
            "Delivery / sales driver counts",
            "Personal auto insurance requirements for employees",
            "Loss runs — auto / HNOA",
            "Contracts requiring auto liability",
            "Prior HNOA / BA declarations",
            "Operations description",
        ),
        coverages=[],
    ),
    _line(
        id="motor_truck_cargo",
        slug="motor-truck-cargo",
        name="Motor Truck Cargo Insurance",
        short_name="Motor Truck Cargo",
        category_id="auto",
        checklist_lob="motor_truck_cargo",
        insurance_line="motor_truck_cargo",
        rating_line="inland_marine",
        description="Cargo in transit for motor carriers and private fleets.",
        uw_focus="Review commodities, limit per load, theft controls, and reefer / high-theft exposures.",
        acord_forms=["Motor truck cargo application"],
        documents=_docs(
            "Motor truck cargo application",
            "Commodity list and average/max load values",
            "Radius and lane information",
            "Theft prevention / GPS / team-driver procedures",
            "Refrigeration / special-handling notes",
            "Loss runs — cargo",
            "Bills of lading / contract samples",
            "Prior cargo declarations",
        ),
        coverages=[],
    ),
    _line(
        id="garage_liability",
        slug="garage-liability",
        name="Garage Liability Insurance",
        short_name="Garage",
        category_id="auto",
        checklist_lob="garage",
        insurance_line="garage_liability",
        rating_line="general_liability",
        description="Auto dealer / repair garage liability and garagekeepers coverage.",
        uw_focus="Assess repair vs. dealer operations, lot security, customer vehicle values, and tech training.",
        acord_forms=["Garage liability application", "ACORD 127"],
        documents=_docs(
            "Garage liability application",
            "Operations mix (sales, repair, body, storage)",
            "Average / max customer vehicle values on lot",
            "Lot security and keys control",
            "Technician certifications",
            "Loss runs — garage / GL / auto",
            "Dealer plate / inventory notes",
            "Prior garage declarations",
        ),
        coverages=[],
    ),
    _line(
        id="non_trucking_liability",
        slug="non-trucking-liability",
        name='Non-Trucking Liability ("Bobtail") Insurance',
        short_name="Bobtail / NTL",
        category_id="auto",
        checklist_lob="non_trucking_liability",
        insurance_line="non_trucking_liability",
        rating_line="commercial_auto",
        description="Liability for owner-operators driving without a load (bobtail / non-trucking).",
        uw_focus="Review lease agreements with motor carriers, deadhead/bobtail exposure, and primary vs. excess structure.",
        acord_forms=["Non-trucking / bobtail application", "ACORD 127"],
        documents=_docs(
            "Non-trucking liability (bobtail) application",
            "Lease agreements with motor carriers",
            "Owner-operator / independent contractor schedule",
            "Vehicle schedule (power units)",
            "Driver MVRs",
            "Loss runs — auto / bobtail",
            "Radius and deadhead/bobtail usage description",
            "Prior non-trucking / bobtail declarations",
        ),
        coverages=[],
    ),
    # ===== 5. FINANCIAL / CREDIT ===========================================
    _line(
        id="trade_credit",
        slug="trade-credit",
        name="Trade Credit Insurance",
        short_name="Trade Credit",
        category_id="financial",
        checklist_lob="trade_credit",
        insurance_line="trade_credit",
        status="live",
        description="Protects receivables against buyer default — domestic and export exposures.",
        uw_focus="Analyze buyer creditworthiness, customer concentration, AR aging, credit policy, and historical bad-debt experience.",
        acord_forms=["Carrier-specific trade credit application"],
        documents=_docs(
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
        ),
        coverages=[
            _coverage(
                "whole_turnover",
                "Whole Turnover Coverage",
                "Full AR book aging and buyer concentration report",
            ),
            _coverage(
                "single_buyer",
                "Single Buyer/Key Account Coverage",
                "Key account financials and credit limit request",
            ),
        ],
    ),
    _line(
        id="surety_bonds",
        slug="surety-bonds",
        name="Surety Bonds",
        short_name="Surety",
        category_id="financial",
        checklist_lob="surety",
        insurance_line="surety_bonds",
        rating_line="surety_bonds",
        description="Contract, commercial, fidelity, and court bonds.",
        uw_focus="Underwrite contractor/principal financial strength, work-on-hand, and completion capacity.",
        acord_forms=["Surety application / indemnity agreement"],
        documents=_docs(
            "Surety questionnaire / bond application",
            "Personal and corporate indemnity agreement",
            "Financial statements (CPA-prepared preferred)",
            "Work-on-hand / backlog schedule",
            "Bank references and credit lines",
            "Prior bond / claim history",
            "Contract documents for subject bond",
            "Resumes of key principals",
        ),
        coverages=[
            _coverage(
                "contract_bonds",
                "Contract Bonds (bid, performance, payment bonds)",
                "Bid documents / contract and bond forms",
            ),
            _coverage(
                "commercial_bonds",
                "Commercial/License & Permit Bonds",
                "License/permit requirements and bond penalty amount",
            ),
            _coverage(
                "fidelity_bonds",
                "Fidelity Bonds",
                "Employee fidelity exposure schedule",
            ),
            _coverage(
                "court_bonds",
                "Court Bonds",
                "Court order / case caption and bond amount",
            ),
        ],
    ),
    _line(
        id="political_risk",
        slug="political-risk",
        name="Political Risk Insurance",
        short_name="Political Risk",
        category_id="financial",
        checklist_lob="political_risk",
        insurance_line="political_risk",
        rating_line="trade_credit",
        description="Expropriation, currency inconvertibility, political violence, and related PRI covers.",
        uw_focus="Evaluate country risk, investment structure, host-government relations, and tenor.",
        acord_forms=["Political risk application"],
        documents=_docs(
            "Political risk application",
            "Country / project exposure schedule",
            "Investment structure and ownership docs",
            "Host contracts / concession agreements",
            "Currency and repatriation plan",
            "Security / political violence assessment",
            "Financial projections for insured investment",
            "Prior PRI policy / claims (if any)",
        ),
        coverages=[],
    ),
    _line(
        id="representations_warranties",
        slug="representations-warranties",
        name="Representations & Warranties Insurance (R&W)",
        short_name="R&W",
        category_id="financial",
        checklist_lob="representations_warranties",
        insurance_line="representations_warranties",
        rating_line="directors_and_officers",
        description="M&A deal insurance covering breaches of reps and warranties in the purchase agreement.",
        uw_focus="Review the full deal due diligence file, purchase agreement, financial statements, and disclosure schedules.",
        acord_forms=["R&W insurance application / binder submission"],
        documents=_docs(
            "R&W insurance application",
            "Purchase / merger agreement (including reps & warranties)",
            "Full deal due diligence file / data room index",
            "Disclosure schedules and disclosure letter",
            "Target and buyer audited financial statements",
            "Quality of earnings / financial due diligence report",
            "Legal due diligence summary / issues list",
            "Prior R&W claims or known breaches (if any)",
        ),
        coverages=[
            _coverage(
                "buyer_side",
                "Buyer-Side R&W",
                "Buyer-side policy form request and retention / limit structure",
            ),
            _coverage(
                "seller_side",
                "Seller-Side R&W",
                "Seller-side policy form request and escrow interaction notes",
            ),
        ],
    ),
    _line(
        id="legal_expense",
        slug="legal-expense",
        name="Legal Expense / Litigation Insurance",
        short_name="Legal Expense",
        category_id="financial",
        checklist_lob="legal_expense",
        insurance_line="legal_expense",
        rating_line="errors_and_omissions",
        description="Covers legal defense costs and related litigation expense — including after-the-event and litigation funding-style covers.",
        uw_focus="Review case merits, opposing counsel, litigation budget, and probability/cost of adverse outcome.",
        acord_forms=["Legal expense / litigation insurance application"],
        documents=_docs(
            "Legal expense / litigation insurance application",
            "Case summary and merits assessment from counsel",
            "Opposing counsel and jurisdiction information",
            "Litigation budget / cost projection",
            "Pleadings / complaint / key filings",
            "Prior related litigation history",
            "Insured financial statements (ability to fund retention)",
            "Prior legal expense / ATE declarations (if any)",
        ),
        coverages=[],
    ),
    # ===== 6. SPECIALTY ====================================================
    _line(
        id="tech_eo_cyber",
        slug="tech-eo-cyber",
        name="Technology E&O / Cyber (Industry-Specific)",
        short_name="Tech E&O / Cyber",
        category_id="specialty",
        checklist_lob="tech_eo_cyber",
        insurance_line="tech_eo_cyber",
        rating_line="cyber_liability",
        description="Combined technology professional liability and cyber for tech companies.",
        uw_focus="Assess SaaS/product liability, SLA exposure, security posture, and contract limitation of liability.",
        acord_forms=["Tech E&O + cyber application"],
        documents=_docs(
            "Technology E&O / cyber application",
            "Product / SaaS description and customer tiers",
            "Sample MSA / SLA / limitation of liability",
            "Security questionnaire and SOC 2 / ISO evidence",
            "Revenue by product line",
            "Prior E&O and cyber claims",
            "Incident response plan",
            "Prior tech E&O / cyber declarations",
        ),
        coverages=[],
    ),
    _line(
        id="construction",
        slug="construction",
        name="Construction / Contractor's Insurance",
        short_name="Construction",
        category_id="specialty",
        checklist_lob="construction",
        insurance_line="construction",
        rating_line="general_liability",
        description="Contractor's GL and wrap-up (OCIP/CCIP) construction programs.",
        uw_focus="Review trade mix, subcontracted %, height/depth work, wrap structure, and project safety.",
        acord_forms=["ACORD 125/126", "Construction supplemental", "Wrap-up application"],
        documents=_docs(
            "Contractor's application / construction supplemental",
            "Trade mix and % subcontracted",
            "Project list (values, duration, location)",
            "Safety manual and EMR / OSHA logs",
            "Subcontractor insurance requirements",
            "Wrap-up (OCIP/CCIP) structure docs if applicable",
            "Loss runs — GL / WC / auto",
            "Prior contractor / wrap declarations",
        ),
        coverages=[
            _coverage(
                "contractors_gl",
                "Contractor's General Liability",
                "Trade mix and subcontracted cost percentage",
                "Project list with values and locations",
            ),
            _coverage(
                "wrap_up",
                "Wrap-Up (OCIP/CCIP) Policies",
                "Wrap-up structure / enrolled parties schedule",
                "Safety program and EMR documentation",
            ),
        ],
    ),
    _line(
        id="aviation",
        slug="aviation",
        name="Aviation Insurance",
        short_name="Aviation",
        category_id="specialty",
        checklist_lob="aviation",
        insurance_line="aviation",
        rating_line="umbrella",
        description="Aircraft hull and liability for owned, leased, or operated aircraft.",
        uw_focus="Evaluate aircraft type, pilot experience/hours, hangar, and use (private vs. commercial).",
        acord_forms=["Aviation application"],
        documents=_docs(
            "Aviation hull & liability application",
            "Aircraft schedule (N-number, make, year, value)",
            "Pilot experience forms (hours, ratings)",
            "Use description and geographic limits",
            "Hangar / airport details",
            "Maintenance program",
            "Loss / incident history",
            "Prior aviation declarations",
        ),
        coverages=[],
    ),
    _line(
        id="event_insurance",
        slug="event-insurance",
        name="Event Insurance",
        short_name="Event",
        category_id="specialty",
        checklist_lob="event",
        insurance_line="event_insurance",
        rating_line="general_liability",
        description="Event cancellation and event liability for organizers and venues.",
        uw_focus="Review event type, attendance, weather contingency, artists/vendors, and cancellation triggers.",
        acord_forms=["Event cancellation / liability application"],
        documents=_docs(
            "Event insurance application",
            "Event description, date(s), venue, attendance",
            "Budget and non-refundable expenses",
            "Artist / vendor / venue contracts",
            "Weather / contingency plans",
            "Security and alcohol service notes",
            "Prior event claims",
            "COI requirements from venue",
        ),
        coverages=[
            _coverage(
                "cancellation",
                "Event Cancellation",
                "Non-refundable expense schedule and cancellation triggers",
            ),
            _coverage(
                "event_liability",
                "Event Liability",
                "Attendance estimates, security plan, and alcohol service notes",
            ),
        ],
    ),
    _line(
        id="intellectual_property",
        slug="intellectual-property",
        name="Intellectual Property Insurance",
        short_name="IP",
        category_id="specialty",
        checklist_lob="intellectual_property",
        insurance_line="intellectual_property",
        rating_line="errors_and_omissions",
        description="IP infringement defense/abatement and related intellectual property covers.",
        uw_focus="Assess patent/trademark portfolio, freedom-to-operate, litigation history, and industry litigiousness.",
        acord_forms=["IP insurance application"],
        documents=_docs(
            "IP insurance application",
            "IP portfolio schedule (patents, marks, copyrights)",
            "Freedom-to-operate / clearance opinions (if any)",
            "Prior IP litigation / cease-and-desist history",
            "Product / technology description",
            "Competitor landscape notes",
            "Revenue tied to insured IP",
            "Prior IP policy declarations",
        ),
        coverages=[],
    ),
    _line(
        id="kidnap_ransom",
        slug="kidnap-ransom",
        name="Kidnap & Ransom (K&R) Insurance",
        short_name="K&R",
        category_id="specialty",
        checklist_lob="kidnap_ransom",
        insurance_line="kidnap_ransom",
        rating_line="umbrella",
        description="Kidnap, ransom, extortion, and related crisis-response coverage.",
        uw_focus="Review travel patterns to high-risk countries, executive profile, and security protocols.",
        acord_forms=["K&R application"],
        documents=_docs(
            "K&R / extortion application",
            "Travel schedule to high-risk regions",
            "List of insured persons / roles",
            "Security and travel protocols",
            "Prior extortion / K&R incidents",
            "Corporate structure and ownership",
            "Response consultant preferences",
            "Prior K&R declarations",
        ),
        coverages=[],
    ),
    _line(
        id="terrorism",
        slug="terrorism",
        name="Terrorism Insurance",
        short_name="Terrorism",
        category_id="specialty",
        checklist_lob="terrorism",
        insurance_line="terrorism",
        rating_line="commercial_property",
        description="Certified and/or non-certified terrorism property and liability covers.",
        uw_focus="Assess location attractiveness, aggregation, and TRIPRA vs. stand-alone needs.",
        acord_forms=["Terrorism coverage election / application"],
        documents=_docs(
            "Terrorism coverage application / election form",
            "Location schedule with TIV",
            "Occupancy and public access description",
            "Security measures at key locations",
            "Existing property / liability declarations",
            "Prior terrorism losses (if any)",
            "Broker modeling / aggregation notes",
            "Financial statements",
        ),
        coverages=[],
    ),
    _line(
        id="product_recall",
        slug="product-recall",
        name="Product Recall Insurance",
        short_name="Product Recall",
        category_id="specialty",
        checklist_lob="product_recall",
        insurance_line="product_recall",
        rating_line="general_liability",
        description="First-party recall costs and related product contamination covers.",
        uw_focus="Review product type, recall history, traceability, and crisis-communication readiness.",
        acord_forms=["Product recall / contamination application"],
        documents=_docs(
            "Product recall application",
            "Product list and sales by category",
            "Traceability / lot-tracking procedures",
            "Prior recalls and FDA/USDA actions",
            "Crisis / recall response plan",
            "Quality control documentation",
            "Supply-chain dependency notes",
            "Prior recall policy declarations",
        ),
        coverages=[],
    ),
    _line(
        id="supply_chain",
        slug="supply-chain",
        name="Supply Chain Insurance",
        short_name="Supply Chain",
        category_id="specialty",
        checklist_lob="supply_chain",
        insurance_line="supply_chain",
        rating_line="commercial_property",
        description="Non-damage and contingent supply-chain interruption covers.",
        uw_focus="Map critical suppliers/customers, single points of failure, and BI dependency values.",
        acord_forms=["Supply chain / contingent BI application"],
        documents=_docs(
            "Supply chain / contingent BI application",
            "Critical supplier and customer map",
            "Spend / dependency values by supplier",
            "Alternate sourcing plans",
            "Historical interruption events",
            "BI worksheet for dependent properties",
            "Contracts with force-majeure clauses",
            "Prior supply-chain / CBI declarations",
        ),
        coverages=[],
    ),
    _line(
        id="crop_insurance",
        slug="crop-insurance",
        name="Crop Insurance",
        short_name="Crop",
        category_id="specialty",
        checklist_lob="crop_insurance",
        insurance_line="crop_insurance",
        rating_line="commercial_property",
        description="Agribusiness crop coverage — acreage, crop type, and yield-based underwriting.",
        uw_focus="Review acreage, crop type, historical yield data, and weather/peril exposure by county.",
        acord_forms=["Crop insurance application / acreage report"],
        documents=_docs(
            "Crop insurance application",
            "Acreage report by crop and field/county",
            "Crop type and planting / intended use details",
            "Historical yield data (typically 4–10 years APH)",
            "FSA / RMA production records (if applicable)",
            "Farm maps / GPS field boundaries",
            "Prior crop loss history",
            "Prior crop insurance declarations",
        ),
        coverages=[],
    ),
    _line(
        id="livestock_bloodstock",
        slug="livestock-bloodstock",
        name="Livestock / Bloodstock Insurance",
        short_name="Livestock / Bloodstock",
        category_id="specialty",
        checklist_lob="livestock_bloodstock",
        insurance_line="livestock_bloodstock",
        rating_line="commercial_property",
        description="Mortality and related covers for livestock herds and bloodstock (horses, etc.).",
        uw_focus="Review veterinary records, herd/animal valuation, mortality history, and biosecurity practices.",
        acord_forms=["Livestock / bloodstock application"],
        documents=_docs(
            "Livestock / bloodstock application",
            "Veterinary records for insured animals",
            "Herd / animal valuation schedule",
            "Animal identification (tags, microchips, registration papers)",
            "Mortality / loss history",
            "Biosecurity and husbandry practices",
            "Purchase invoices or appraisal for high-value animals",
            "Prior livestock / bloodstock declarations",
        ),
        coverages=[
            _coverage(
                "livestock_mortality",
                "Livestock Mortality",
                "Herd inventory with ages, sexes, and values",
            ),
            _coverage(
                "bloodstock",
                "Bloodstock",
                "Registration papers and veterinary certificate of health",
            ),
        ],
    ),
    # ===== 7. ALTERNATIVE RISK TRANSFER ====================================
    _line(
        id="captive_insurance",
        slug="captive-insurance",
        name="Captive Insurance Programs",
        short_name="Captive",
        category_id="alternative",
        checklist_lob="captive_insurance",
        insurance_line="captive_insurance",
        rating_line="umbrella",
        description="Self-owned insurance subsidiaries writing parent/affiliate risks — requires actuarial and regulatory feasibility.",
        uw_focus="Review actuarial feasibility study, captive business plan, domicile, capitalization, and fronting/reinsurance structure.",
        acord_forms=["Captive feasibility / formation package"],
        documents=_docs(
            "Actuarial feasibility study",
            "Captive business plan and pro forma financials",
            "Domicile selection / regulatory application materials",
            "Capitalization and surplus plan",
            "Fronting carrier and reinsurance structure diagram",
            "Lines of business and expected premium volume",
            "Parent / affiliate financial statements",
            "Governance / board and service-provider agreements",
        ),
        coverages=[
            _coverage(
                "single_parent",
                "Single-Parent Captive",
                "Parent risk profile and expected loss funding analysis",
            ),
            _coverage(
                "group_captive",
                "Group / Association Captive",
                "Member roster, homogeneity analysis, and joining criteria",
            ),
        ],
    ),
    _line(
        id="sir_fronting",
        slug="sir-fronting",
        name="Self-Insured Retention (SIR) / Fronting Arrangements",
        short_name="SIR / Fronting",
        category_id="alternative",
        checklist_lob="sir_fronting",
        insurance_line="sir_fronting",
        rating_line="umbrella",
        description="Large-deductible / SIR programs and fronted policies requiring collateral and claims administration.",
        uw_focus="Review collateral agreements, claims administration contracts, loss forecasts, and fronting carrier terms.",
        acord_forms=["Large deductible / SIR / fronting submission"],
        documents=_docs(
            "SIR / fronting program application",
            "Collateral agreements (LOC, trust, cash)",
            "Claims administration (TPA) contracts",
            "Historical loss runs and loss forecast / actuarial analysis",
            "Proposed SIR / deductible schedule by line",
            "Fronting carrier policy form and fees",
            "Insured financial statements / credit profile",
            "Prior large-deductible / SIR program declarations",
        ),
        coverages=[
            _coverage(
                "sir",
                "Self-Insured Retention",
                "SIR amount by line and aggregate stop-loss request",
            ),
            _coverage(
                "fronting",
                "Fronting Arrangement",
                "Fronting fee schedule and certificate / filing requirements",
            ),
        ],
    ),
    # ===== 8. PACKAGE ======================================================
    _line(
        id="bop",
        slug="bop",
        name="Business Owner's Policy (BOP)",
        short_name="BOP",
        category_id="package",
        checklist_lob="bop",
        insurance_line="business_owners_policy",
        status="live",
        description="Bundles property + general liability for eligible small businesses.",
        uw_focus="Confirm BOP eligibility (size/class), property COPE, and GL operations fit.",
        acord_forms=["ACORD 125", "ACORD 126", "ACORD 140", "BOP application"],
        documents=_docs(
            "BOP application (ACORD 125/126/140 as required)",
            "Location schedule with COPE details",
            "Description of operations",
            "Gross sales / payroll",
            "Loss runs — property and liability",
            "Prior BOP / package declarations",
            "Lease or ownership proof",
            "Financial statements (if requested)",
        ),
        coverages=[
            _coverage(
                "property_gl_bundle",
                "Property + General Liability (small business focus)",
                "Property SOV / COPE for BOP locations",
                "GL operations and sales summary",
            ),
        ],
    ),
    _line(
        id="cpp",
        slug="cpp",
        name="Commercial Package Policy (CPP)",
        short_name="CPP",
        category_id="package",
        checklist_lob="cpp",
        insurance_line="commercial_package",
        rating_line="commercial_package",
        description="Customizable bundle: property + liability + crime + auto and related sections.",
        uw_focus="Coordinate multi-section exposures, shared limits, and package eligibility vs. monoline.",
        acord_forms=["ACORD 125", "Section forms for each included line"],
        documents=_docs(
            "CPP / package application",
            "Requested coverage sections checklist",
            "Property SOV / COPE",
            "GL operations and sales",
            "Crime controls questionnaire (if included)",
            "Auto / fleet schedules (if included)",
            "Loss runs for all included lines",
            "Prior package declarations",
        ),
        coverages=[
            _coverage(
                "custom_bundle",
                "Customizable bundle: Property + Liability + Crime + Auto, etc.",
                "Section selection worksheet for included lines",
                "Combined loss runs for package sections",
            ),
        ],
    ),
]

# Only products with a dedicated rater (or true property TIV+COPE) are live.
# Extended taxonomy leaves (aviation, catastrophe, pollution, K&R, political risk,
# terrorism, legal expense) rate from their carrier leaf filings. Pure parent-line
# proxies that remain catalog are crop / captive / E&S specialties.
LIVE_COMMERCIAL_PRODUCT_IDS = frozenset(
    {
        "property_bi",
        "business_interruption",
        "builders_risk",
        "inland_marine",
        "crime",
        "ordinance_or_law",
        "rent_loss_of_rents",
        "equipment_breakdown",
        "general_liability",
        "product_liability",
        "errors_omissions",
        "architects_engineers",
        "miscellaneous_professional",
        "directors_officers",
        "epli",
        "fiduciary_liability",
        "cyber_liability",
        "umbrella",
        "workers_comp",
        "employers_liability",
        "key_person",
        "commercial_auto",
        "fleet",
        "trade_credit",
        "surety_bonds",
        "tech_eo_cyber",
        "construction",
        "bop",
        "cpp",
        "aviation",
        "flood_commercial",
        "earthquake_commercial",
        "pollution",
        "kidnap_ransom",
        "political_risk",
        "terrorism",
        "legal_expense",
    }
)
for _ln in COMMERCIAL_LINES:
    _ln["status"] = "live" if _ln["id"] in LIVE_COMMERCIAL_PRODUCT_IDS else "catalog"


def list_commercial_categories() -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    live_counts: dict[str, int] = {}
    for line in COMMERCIAL_LINES:
        cid = line["category_id"]
        counts[cid] = counts.get(cid, 0) + 1
        if line.get("status") == "live":
            live_counts[cid] = live_counts.get(cid, 0) + 1
    return [
        {
            **cat,
            "product_count": counts.get(cat["id"], 0),
            "live_count": live_counts.get(cat["id"], 0),
        }
        for cat in COMMERCIAL_CATEGORIES
    ]


def _serialize_coverages(coverages: list[Any] | None) -> list[dict[str, Any]]:
    return _normalize_coverages(coverages)


def list_commercial_lines(*, category_id: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in COMMERCIAL_LINES:
        if category_id and line["category_id"] != category_id:
            continue
        if status and line.get("status") != status:
            continue
        coverages = _serialize_coverages(line.get("coverages"))
        all_docs = flatten_line_documents(line)
        rows.append(
            {
                "id": line["id"],
                "slug": line["slug"],
                "name": line["name"],
                "short_name": line["short_name"],
                "category_id": line["category_id"],
                "checklist_lob": line["checklist_lob"],
                "insurance_line": line["insurance_line"],
                "rating_line": line.get("rating_line") or line["insurance_line"],
                "description": line["description"],
                "document_count": len(line["documents"]),
                "coverage_count": len(coverages),
                "coverages": coverages,
                "all_documents": all_docs,
                "acord_forms": list(line["acord_forms"]),
                "status": line.get("status") or "catalog",
            }
        )
    return rows


def commercial_taxonomy_tree() -> list[dict[str, Any]]:
    """Nested categories → products → coverages for UW navigation."""
    by_cat: dict[str, list[dict[str, Any]]] = {c["id"]: [] for c in COMMERCIAL_CATEGORIES}
    for row in list_commercial_lines():
        by_cat.setdefault(row["category_id"], []).append(
            {
                "id": row["id"],
                "slug": row["slug"],
                "name": row["name"],
                "short_name": row["short_name"],
                "insurance_line": row["insurance_line"],
                "checklist_lob": row["checklist_lob"],
                "status": row["status"],
                "document_count": row["document_count"],
                "all_documents": list(row.get("all_documents") or []),
                "coverages": [
                    {
                        "id": cov["id"],
                        "name": cov["name"],
                        "documents": list(cov.get("documents") or []),
                        "document_count": int(cov.get("document_count") or len(cov.get("documents") or [])),
                    }
                    for cov in row.get("coverages") or []
                ],
            }
        )
    return [
        {
            **cat,
            "products": by_cat.get(cat["id"], []),
        }
        for cat in list_commercial_categories()
    ]


def _line_payload(line: dict[str, Any]) -> dict[str, Any]:
    coverages = _serialize_coverages(line.get("coverages"))
    return {
        **line,
        "coverages": coverages,
        "all_documents": flatten_line_documents({**line, "coverages": coverages}),
        "base_packet": list(BASE_PACKET),
        "uw_responsibilities": list(UW_CORE_RESPONSIBILITIES),
        "uw_question": ("If I take on this risk, what's the probability and cost of it going wrong, and what price makes that bet worthwhile for the insurer?"),
    }


def get_commercial_line(line_id_or_slug: str) -> dict[str, Any] | None:
    raw = (line_id_or_slug or "").strip().lower()
    if not raw:
        return None
    dashed = raw.replace("_", "-")
    underscored = raw.replace("-", "_")
    variants = {raw, dashed, underscored}

    # 1) Direct identifiers — id / slug / checklist_lob / insurance_line.
    #    rating_line is a shared grouping key (e.g. several workforce lines map to
    #    "key_person"), so it must NOT outrank the product's own identifiers.
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
        if variants & candidates:
            return _line_payload(line)

    # 2) Fallback — rating_line alias for callers resolving a rating key.
    for line in COMMERCIAL_LINES:
        rating = (line.get("rating_line") or "").replace("_", "-")
        if variants & {rating}:
            return _line_payload(line)

    return None


def resolve_checklist_lob(line_id_or_slug: str | None, default: str = "property") -> str:
    """Map any commercial line id/slug/insurance_line to a package checklist key."""
    if not line_id_or_slug:
        return default
    line = get_commercial_line(line_id_or_slug)
    if line:
        return str(line.get("checklist_lob") or default)
    return default


def insurance_line_labels() -> dict[str, str]:
    """Display labels keyed by insurance_line (and common aliases)."""
    labels: dict[str, str] = {}
    for line in COMMERCIAL_LINES:
        labels[line["insurance_line"]] = line["name"]
        labels[line["id"]] = line["name"]
        labels[line["slug"].replace("-", "_")] = line["name"]
        labels[line["checklist_lob"]] = line["name"]
    return labels


def list_production_insurance_lines() -> list[str]:
    """Distinct insurance_line values for all production commercial products."""
    seen: set[str] = set()
    out: list[str] = []
    for line in COMMERCIAL_LINES:
        key = str(line["insurance_line"])
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def commercial_hub_payload() -> dict[str, Any]:
    lines = list_commercial_lines()
    live = [ln for ln in lines if ln["status"] == "live"]
    try:
        from insureflow.rating.leaf_filings import carrier_book_status

        carrier_book = carrier_book_status()
    except Exception:  # noqa: BLE001
        carrier_book = {"filings": 0, "coverage_pct": 0.0}
    return {
        "segment": "business_commercial",
        "title": "Business / Commercial Insurance",
        "summary": (
            "Production commercial underwriting across property, liability, workforce, auto, financial, "
            "specialty, and package lines — each with line-specific document packs, LOB-scoped ML models, "
            "and UW workflow."
        ),
        "base_packet": list(BASE_PACKET),
        "uw_responsibilities": list(UW_CORE_RESPONSIBILITIES),
        "categories": list_commercial_categories(),
        "taxonomy": commercial_taxonomy_tree(),
        "lines": lines,
        "live_lines": live,
        "production_lines": list_production_insurance_lines(),
        "carrier_book": carrier_book,
        "stats": {
            "category_count": len(COMMERCIAL_CATEGORIES),
            "product_count": len(COMMERCIAL_LINES),
            "live_count": len(live),
            "catalog_count": max(0, len(lines) - len(live)),
            "lob_model_count": len(list_production_insurance_lines()) * 4,
            "leaf_filings": carrier_book.get("filings", 0),
            "leaf_coverage_pct": carrier_book.get("coverage_pct", 0.0),
        },
    }
