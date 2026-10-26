"""Per-product differentiation for the RAG corpus generator.

The category rules in ``rag_knowledge_base.py`` carry line-level decline
criteria, endorsements, and refer-authority rules. Those line rules are
genuinely shared, but a line-level decline list is frequently wrong for an
outlier product (an umbrella does not decline "bars and taverns"; an annuity
does not decline on occupational class).

This module supplies the product-specific ``decline``, ``endorsements``, and
``refer`` content that makes each product entry self-consistent. It is merged
into ``PRODUCT_OVERRIDES`` additively: a field already authored in
``rag_product_overrides.py`` always wins, and this module only fills the gaps.
Keys are ``"<lob>/<product_id>"``.
"""

from __future__ import annotations

PRODUCT_DIFFERENTIATION: dict[str, dict[str, list[str]]] = {
    # =====================================================================
    # COMMERCIAL — PROPERTY
    # =====================================================================
    "commercial/property_bi": {
        "decline": [
            "Unprotected frame (ISO Class 10) construction with no sprinkler or hydrant credit",
            "Heavy manufacturing with unrated combustible dust or flammable-liquid storage",
            "Vacant or unrepaired buildings carried beyond the vacancy provision",
            "Coastal wind or brush exposures without a companion wind/flood policy",
        ],
        "endorsements": [
            "Replacement Cost / Extended Replacement Cost",
            "Agreed Value",
            "Coinsurance waiver",
            "Blanket limits across scheduled locations",
            "Spoilage and Equipment Breakdown (where applicable)",
        ],
        "refer": [
            "Named windstorm in coastal tier 1/2",
            "Aggregate TIV above $50M",
            "Locations with an unsatisfactory COPE survey",
        ],
    },
    "commercial/business_interruption": {
        "decline": [
            "No underlying property policy in force",
            "Business-income worksheet that cannot be reconciled to financial statements",
            "Dependence on a single supplier or customer with no contingency plan",
            "Start-up with no trading history to support projected income",
        ],
    },
    "commercial/builders_risk": {
        "decline": [
            "Projects with no defined completion date, budget, or completed value",
            "Frame construction above four storeys without a fire plan",
            "Renovation over 50% of an occupied building with no hot-work permit process",
            "Existing structures included without a valued COPE survey",
        ],
    },
    "commercial/inland_marine": {
        "decline": [
            "Cargo without a bill of lading or shipping documentation",
            "Overland transit through territories with active conflict",
            "Project cargo above $5M without an engineering stowage plan",
            "Recurring losses attributed to inadequate packing",
        ],
        "refer": [
            "Project cargo above $5M",
            "Annual transit programs above $2M",
            "Unusual commodities (livestock, fine art, explosives)",
        ],
    },
    "commercial/ocean_marine": {
        "decline": [
            "Vessels trading to sanctioned ports (OFAC/ITAR)",
            "Hull older than 25 years without a current survey",
            "Bulk or liquid cargo without a formal stowage and stability plan",
            "Trades outside the agreed trading warranty",
        ],
    },
    "commercial/equipment_breakdown": {
        "decline": [
            "Equipment with no maintenance records or manufacturer schedule",
            "Boilers or pressure vessels without a current inspection certificate",
            "Assets beyond economic repair (obsolete, parts unavailable)",
            "High-voltage switchgear without thermographic surveys",
        ],
    },
    "commercial/flood_commercial": {
        "decline": [
            "Property in a special flood hazard area rated without an elevation certificate",
            "Lowest-floor elevation below base flood elevation",
            "Prior repeated flood losses with no mitigation",
            "Unanchored or manufactured structures in the floodplain",
        ],
    },
    "commercial/earthquake_commercial": {
        "decline": [
            "Masonry or non-ductile concrete with no seismic retrofit",
            "High-seismic-zone risk without a probable-maximum-loss study",
            "Probable maximum loss above appetite",
            "Contents-only request with no building resilience data",
        ],
    },
    "commercial/crime": {
        "decline": [
            "No segregation of duties or dual controls over funds",
            "Unsigned or unverified employee background checks",
            "Prior fidelity loss attributable to weak internal controls",
            "Paper-based payments with no reconciliations",
        ],
    },
    "commercial/ordinance_or_law": {
        "decline": [
            "Building that is not code-compliant with the local jurisdiction",
            "Requested limit exceeds the available building coverage limit",
            "No valuation of demolition and undamaged-portion costs",
            "Post-loss reconstruction that triggers a zoning non-conformity",
        ],
    },
    "commercial/rent_loss_of_rents": {
        "decline": [
            "No lease or rent-roll documentation",
            "Vacancy or rent roll that cannot be verified",
            "Rent loss requested beyond the property indemnity period",
            "Tenant-default risk treated as covered",
        ],
    },
    "commercial/dic_excess_flood": {
        "decline": [
            "Underlying primary flood policy not in force",
            "Attachment below the underlying flood limit",
            "Property in a special flood hazard area without primary flood cover",
            "Requested DIC limit beyond qualified aggregate capacity",
        ],
    },
    # =====================================================================
    # COMMERCIAL — LIABILITY
    # =====================================================================
    "commercial/general_liability": {
        "decline": [
            "Bars, taverns, and late-night alcohol classes (write liquor liability)",
            "Asbestos or lead abatement contractors",
            "Ongoing pollution exposure without a pollution policy",
            "Unlicensed or unregulated operations",
        ],
        "endorsements": [
            "Additional Insured (owners, lessors, contractors)",
            "Waiver of Subrogation",
            "Primary & Non-Contributory",
            "Designated Premises / Products-Completed Operations",
            "Hired & Non-Owned Auto",
        ],
        "refer": [
            "Products-completed operations above $1M",
            "Hazardous classes (demolition, roofing above three storeys)",
            "Residential or HOA exposures",
        ],
    },
    "commercial/product_liability": {
        "decline": [
            "Products with known defect litigation history",
            "Pharmaceutical or medical devices without a recall-history review",
            "Products sold into sanctioned markets",
            "Dietary or cosmetic products with unsubstantiated claims",
        ],
    },
    "commercial/errors_omissions": {
        "decline": [
            "Professionals with lapsed licensure or discipline actions",
            "Firms with a pattern of large claims or pending litigation",
            "Revenue that cannot be reconciled to tax filings",
            "New ventures with no operating track record",
        ],
    },
    "commercial/architects_engineers": {
        "decline": [
            "Firms doing structural work without certified engineers of record",
            "Undisclosed prior design litigation",
            "Design-build projects outside the firm's demonstrated competence",
            "Firms without peer-review or QA procedures",
        ],
    },
    "commercial/miscellaneous_professional": {
        "decline": [
            "Contractors providing medical or legal advice without a licensed principal",
            "Home-inspection firms offering structural certifications",
            "Any class with known prior professional liability claims",
            "Revenue from prohibited referral-fee arrangements",
        ],
    },
    "commercial/directors_officers": {
        "decline": [
            "Public companies without audited financials or a completed D&O questionnaire",
            "Companies in bankruptcy or insolvency at inception",
            "Serial IPO/SPAC sponsors with regulatory findings",
            "Undisclosed SEC or DOJ investigations",
        ],
    },
    "commercial/epli": {
        "decline": [
            "Any pending or threatened employment claim at inception",
            "Employers with prior EPLI losses or EEOC/state agency charges",
            "Workforce reductions without a documented process",
            "Worker misclassification with no remediation plan",
        ],
    },
    "commercial/fiduciary_liability": {
        "decline": [
            "Plans not in ERISA or statutory compliance",
            "Unbonded plan fiduciaries where bonding is required",
            "Prohibited transactions under the plan documents",
            "Plans with frozen or terminated status in dispute",
        ],
    },
    "commercial/cyber_liability": {
        "decline": [
            "No multi-factor authentication on remote access or email",
            "Production endpoints without endpoint detection and response",
            "Known unpatched critical vulnerabilities",
            "An unremediated prior breach",
        ],
    },
    "commercial/umbrella": {
        "decline": [
            "No underlying primary policies in force at the required limits",
            "Underlying classes excluded by the primary program",
            "Gaps between the underlying coverages and the umbrella attachment",
            "Risks for which the required underlying cover cannot be purchased",
        ],
    },
    "commercial/pollution": {
        "decline": [
            "Known contamination with an active remediation order",
            "Underground storage tanks without leak detection",
            "Friable asbestos without an operations-and-maintenance plan",
            "Ongoing environmental violations at inception",
        ],
    },
    "commercial/liquor_liability": {
        "decline": [
            "Premises with prior alcohol-related injury claims",
            "No server-training or age-verification procedures",
            "Late-night venues with drink-special promotions",
            "Prior license suspensions or dram-shop violations",
        ],
    },
    "commercial/media_liability": {
        "decline": [
            "Content with known defamatory or infringing material",
            "Firms with a pattern of large media claims",
            "Prohibited content categories (adult, hate, gambling)",
            "No content-review or rights-clearance procedure",
        ],
    },
    # =====================================================================
    # COMMERCIAL — WORKFORCE
    # =====================================================================
    "commercial/workers_comp": {
        "decline": [
            "Non-compliant or unlicensed operations",
            "Classes with unfunded prior workers' compensation liability (successor liability unresolved)",
            "Employee-leasing/PEO arrangements without a concurrent employee agreement",
            "Exposures not permissible in the applicable state plan",
        ],
        "endorsements": [
            "Waiver of Subrogation",
            "Increased Employers Liability limits",
            "Alternate Employer",
            "Voluntary Compensation",
            "USL&H (where applicable)",
        ],
        "refer": [
            "Employers with unfunded prior compensation liability",
            "Experience modification above 1.30",
            "New operations in monopolistic states",
        ],
    },
    "commercial/employers_liability": {
        "decline": [
            "Employee versus independent-contractor misclassification disputes",
            "Intentional or retaliatory-act allegations at inception",
            "Workforces in states with exclusive-remedy exceptions",
            "Monopolistic-state compensation where EL must be separately placed",
        ],
    },
    "commercial/group_health": {
        "decline": [
            "Groups below the minimum participation or enrollment percentage",
            "Groups where a single member is a disproportionate share of the book",
            "No evidence of 12 months of continuous prior coverage",
            "ERISA or PPACA non-compliant plan documents",
        ],
    },
    "commercial/group_life": {
        "decline": [
            "Groups with no genuine employer-employee relationship (affinity abuse)",
            "Participation below the minimum for guarantee issue",
            "Members brought in without evidence-of-insurability eligibility screening",
            "Imputed-cost or Section 79 compliance issues",
        ],
    },
    "commercial/group_disability": {
        "decline": [
            "Groups without 12 months of payroll and class data",
            "High-turnover classes priced with no credible experience",
            "No statutory-disability integration established",
            "Reduced-hours or partial-disability classes without a plan design",
        ],
    },
    "commercial/key_person": {
        "decline": [
            "No documentation of the key person's value or replacement cost",
            "Business with no continuity or succession plan",
            "Overlapping key-person arrangements exceeding the firm's demonstrated value",
            "Insurable interest not established",
        ],
    },
    "commercial/business_overhead": {
        "decline": [
            "No verifiable fixed-expense schedule",
            "Overhead coverage that duplicates other partners' arrangements",
            "Overhead period longer than the realistic recovery time",
            "Non-continuing or personal expenses requested",
        ],
    },
    "commercial/voluntary_benefits": {
        "decline": [
            "Employees not eligible under the group's class definitions",
            "No employer subsidy or payroll-deduction capability",
            "Guarantee-issue limits exceeded without underwriting",
            "State-mandated benefits omitted from the plan",
        ],
    },
    # =====================================================================
    # COMMERCIAL — AUTO
    # =====================================================================
    "commercial/commercial_auto": {
        "decline": [
            "Drivers with DUI or felony convictions in the last five years",
            "Long-haul trucking without DOT compliance",
            "Racing or dealer exposures without a garage policy",
            "Interstate carriers without MC/DOT authority",
        ],
        "endorsements": [
            "Hired & Non-Owned Auto",
            "Drive-Other-Car",
            "Additional Insured / Waiver of Subrogation",
            "Garagekeepers (where applicable)",
            "Named-Driver exclusion",
        ],
        "refer": [
            "Fleets above 25 vehicles or any DOT long-haul",
            "Drivers with serious MVR violations",
            "Hazardous or flammable cargo",
        ],
    },
    "commercial/fleet": {
        "decline": [
            "Fleets above 25 units without telematics or a driver-safety program",
            "MVR/CSA scores above the underwriting threshold",
            "Heavy-truck fleets without maintenance and DOT files",
            "Unresolved large-loss history",
        ],
    },
    "commercial/hnoa": {
        "decline": [
            "Autos frequently rented but not declared on the policy",
            "Drivers without a valid license or below the minimum age",
            "High-value or collector vehicles not scheduled",
            "Excluded-driver endorsements not signed",
        ],
    },
    "commercial/motor_truck_cargo": {
        "decline": [
            "Long-haul operations without DOT compliance monitoring",
            "High-theft cargo (electronics, liquor) without escorts or locks",
            "Reefer cargo without temperature and maintenance logs",
            "Cargo handled by unvetted third-party logistics providers",
        ],
    },
    "commercial/garage_liability": {
        "decline": [
            "Dealerships with unresolved title or odometer issues",
            "Service or repair shops without customer-vehicle key control",
            "Sales lots in flood-prone or non-conforming zones",
            "No bailee-custody guidelines",
        ],
    },
    "commercial/non_trucking_liability": {
        "decline": [
            "For-hire carriers operating outside the intrastate radius",
            "Truckers hauling hazardous or oversize loads without endorsements",
            "Owner-operators without a written lease",
            "Uninsured or underinsured subcontractors",
        ],
    },
    # =====================================================================
    # COMMERCIAL — FINANCIAL
    # =====================================================================
    "commercial/trade_credit": {
        "decline": [
            "Buyers without credit history or audited financials",
            "Obligors in sanctioned or embargoed countries",
            "Single-buyer concentration above appetite",
            "Transactions without documentary shipping evidence",
        ],
        "endorsements": [
            "Whole-turnover endorsement",
            "Specific-account endorsement",
            "Discretionary credit-limit increase",
            "Extended-terms cover",
        ],
        "refer": [
            "Single-buyer limits above $500K",
            "Emerging-market obligors",
            "Policies exceeding 90-day credit terms",
        ],
    },
    "commercial/surety_bonds": {
        "decline": [
            "Principals with prior bond defaults or unsatisfied judgments",
            "Insufficient working capital relative to the bonded backlog",
            "Single-job backlog above the program multiple of net worth",
            "Unresolved tax liens",
        ],
    },
    "commercial/political_risk": {
        "decline": [
            "Exposures in sanctioned countries (OFAC)",
            "No sovereign transfer or convertibility guarantee",
            "Confiscation exposure with no bilateral investment treaty",
            "Unrated counterparties in the host country",
        ],
    },
    "commercial/representations_warranties": {
        "decline": [
            "Targets in a sanctioned jurisdiction",
            "Known, undisclosed breaches or earn-out disputes",
            "Transactions without a signed SPA and diligence report",
            "No escrow or retention structure against the R&W limit",
        ],
    },
    "commercial/legal_expense": {
        "decline": [
            "Matters already in litigation at inception",
            "Disputes excluded from the policy master agreement",
            "Costs not recoverable under the underlying contract",
            "Claims with no reasonable prospect of success",
        ],
    },
    # =====================================================================
    # COMMERCIAL — SPECIALTY
    # =====================================================================
    "commercial/tech_eo_cyber": {
        "decline": [
            "Firms with known unpatched critical vulnerabilities",
            "No incident-response or backup process",
            "Revenue from prohibited content or data-scraping",
            "Prior breach claims not disclosed",
        ],
    },
    "commercial/construction": {
        "decline": [
            "Contractors without licensed or bonded status",
            "Wrap-up or captive projects without an engineering report",
            "Design-defect or legacy claims from prior projects",
            "Projects in distressed or delay-prone jurisdictions",
        ],
    },
    "commercial/aviation": {
        "decline": [
            "Operators without a current airworthiness certificate",
            "Crew without type ratings or valid medical certification",
            "Operations in sanctioned airspace",
            "Fleets with open NTSB or incident investigations",
        ],
    },
    "commercial/event_insurance": {
        "decline": [
            "Events without required permits or safety plans",
            "High-risk elements (pyrotechnics, motorsport, crowd above capacity)",
            "Outdoor events without a weather-contingency plan",
            "Cancellation of a key act already in breach",
        ],
    },
    "commercial/intellectual_property": {
        "decline": [
            "Patents with known invalidity or prior-art challenges",
            "Trademarks with pending oppositions",
            "IP held in a sanctioned jurisdiction",
            "No freedom-to-operate analysis",
        ],
    },
    "commercial/kidnap_ransom": {
        "decline": [
            "Travel to sanctioned or high-risk countries without a security plan",
            "Insureds with a history of abduction claims",
            "No reliance on a specialist security or crisis-response firm",
            "Requested coverage for non-permitted parties under the definitions",
        ],
    },
    "commercial/terrorism": {
        "decline": [
            "Government-pool eligible risks (TRIA) not carved out",
            "Assets clustered in a single high-profile location",
            "Conventional war or cyber-terror exposures",
            "NBCR (nuclear, biological, chemical, radiological) exposures",
        ],
    },
    "commercial/product_recall": {
        "decline": [
            "Products with known contamination at inception",
            "Undeclared allergens or regulatory non-compliance",
            "Products already subject to a recall order",
            "Unapproved overseas manufacturing",
        ],
    },
    "commercial/supply_chain": {
        "decline": [
            "Single-source suppliers with no contingency plan",
            "Suppliers in sanction-affected or conflict regions",
            "No contractual or insurance protection downstream",
            "Tier-2/3 suppliers unidentified",
        ],
    },
    "commercial/crop_insurance": {
        "decline": [
            "Acreage reported after the acreage-reporting deadline",
            "Crops grown outside the approved practice or plan",
            "Farms with no documented yield history",
            "Prohibited uses of the land",
        ],
    },
    "commercial/livestock_bloodstock": {
        "decline": [
            "Animals without veterinary or disease-free certification",
            "Herd located in a quarantined area",
            "No mortality records or agreed valuation basis",
            "Bloodstock without pedigree or training data",
        ],
    },
    # =====================================================================
    # COMMERCIAL — ALTERNATIVE RISK
    # =====================================================================
    "commercial/captive_insurance": {
        "decline": [
            "Feeder or participant programs without a feasibility study",
            "Captive domicile without regulatory licensing",
            "Risks outside the captive's approved class",
            "No actuarial funding study",
        ],
        "endorsements": [
            "Excess-of-loss reinsurance",
            "Aggregate stop-loss",
            "Cash-flow / loss-funding plan",
            "Domicile regulatory-reporting endorsement",
        ],
    },
    "commercial/sir_fronting": {
        "decline": [
            "Fronting without a licensed fronting carrier",
            "Collateral or trust not funded to the self-insured-retention level",
            "Unrated or captive reinsurers without collateral",
            "Regulatory fronting limits exceeded",
        ],
        "endorsements": [
            "Collateral/trust funding schedule",
            "Fronting-fee structure",
            "Claims-handling authority",
            "Reinsurance-recoverables endorsement",
        ],
    },
    # =====================================================================
    # COMMERCIAL — PACKAGE
    # =====================================================================
    "commercial/bop": {
        "decline": [
            "Classes outside the eligible BOP list (bars, contractors above threshold)",
            "Buildings with habitational or heavy-manufacturing uses",
            "Revenue or building value above the BOP caps",
            "Unprotected coastal or wind exposures",
        ],
        "endorsements": [
            "Business Income / Extra Expense",
            "Equipment Breakdown",
            "Employee Dishonesty",
            "Hired & Non-Owned Auto",
            "Additional Insured endorsement",
        ],
        "refer": [
            "Any class outside the BOP eligibility list",
            "Revenue above the BOP threshold",
            "Properties in coastal or wildfire tiers",
        ],
    },
    "commercial/cpp": {
        "decline": [
            "Unsupported combinations of coverages not filed together",
            "Property and liability at different insured entities without a scheduled endorsement",
            "Risks requiring mono-line specialty treatment",
            "Unlisted locations beyond the schedule",
        ],
    },
    # =====================================================================
    # LIFE — TERM
    # =====================================================================
    "life/level_term": {
        "decline": [
            "Terminal illness or life expectancy under 12 months",
            "Active substance abuse without 24 months of documented sobriety",
            "Uncontrolled serious cardiac or oncologic condition",
            "Multiple declines or flat extras above $10/$1,000",
        ],
        "endorsements": [
            "Accidental Death Benefit",
            "Waiver of Premium",
            "Critical Illness rider",
            "Child Term rider",
            "Disability Income rider",
        ],
        "refer": [
            "Sum assured above $1M or the financial-underwriting threshold",
            "Rated class or flat extra above the field limit",
            "Attained age outside the field issue band",
        ],
    },
    "life/decreasing_term": {
        "decline": [
            "Mortgage or loan balance not documented",
            "Non-standard mortgage products without an amortization schedule",
            "No insurable interest in the underlying property or loan",
            "Sum assured above the outstanding loan balance",
        ],
    },
    "life/mortgage_life": {
        "decline": [
            "No mortgage or loan documentation",
            "Borrower without insurable interest",
            "Sum assured exceeding the amortizing balance",
            "Loan already in default at inception",
        ],
    },
    "life/increasing_term": {
        "decline": [
            "No documented future earnings or commitment basis",
            "Increases exceeding the selected annual step cap",
            "Income projection not supportable by financials",
            "No evidence of continued insurable interest at increase",
        ],
    },
    "life/renewable_term": {
        "decline": [
            "Renewal requested beyond the guaranteed renewal age",
            "Non-renewal due to a withdrawn class",
            "Coverage lapsed beyond the grace period",
            "Health deterioration at renewal with no rated offering available",
        ],
    },
    "life/convertible_term": {
        "decline": [
            "Conversion requested beyond the conversion period",
            "Conversion to a product not offered in the state",
            "Attained age outside the converted product's issue limits",
            "Request to convert a lapsed policy without reinstatement",
        ],
    },
    "life/rop_term": {
        "decline": [
            "Policy lapsed beyond the reinstatement window",
            "Surrender-value request without policy surrender",
            "Misrepresented age or residency at issuance",
            "Sum assured on non-earning lives beyond the limit",
        ],
    },
    "life/group_term_life": {
        "decline": [
            "Group without a genuine employer-employee relationship",
            "Participation below the minimum for the offered benefit",
            "Members outside the eligible class",
            "Adverse selection without evidence-of-insurability screening",
        ],
    },
    "life/credit_life": {
        "decline": [
            "Credit balance not documented",
            "Borrower outside the eligible loan product or class",
            "Loan already in default at inception",
            "Attained age outside the credit-life band",
        ],
    },
    # =====================================================================
    # LIFE — WHOLE
    # =====================================================================
    "life/traditional_whole_life": {
        "decline": [
            "Terminal illness or life expectancy under 12 months",
            "Uncontrolled serious cardiac or oncologic condition",
            "Active substance abuse without documented sobriety",
            "Non-forfeiture values not understood or signed",
        ],
        "endorsements": [
            "Accelerated Death Benefit",
            "Waiver of Premium",
            "Guaranteed Insurability Option",
            "Paid-Up Additions",
            "Child Term rider",
        ],
        "refer": [
            "Sum assured above the financial-underwriting threshold",
            "Rated class or flat extra above the field limit",
            "Non-resident or residency outside the filed states",
        ],
    },
    "life/limited_pay_whole_life": {
        "decline": [
            "Premium-paying period beyond the product maximum",
            "Unresolved ratings or flat extras",
            "Insurable interest not established",
            "Attained age outside the issue band",
        ],
    },
    "life/single_premium_whole_life": {
        "decline": [
            "Single premium below the product minimum",
            "Source of funds not evidenced (AML)",
            "Modified-endowment-contract limits exceeded",
            "No insurable interest in the insured",
        ],
        "endorsements": [
            "Accelerated Death Benefit",
            "Long-Term Care rider",
            "Terminal Illness rider",
            "Charitable or gifting transfer",
        ],
    },
    "life/participating_whole_life": {
        "decline": [
            "Requested illustrations relying on non-guaranteed dividends",
            "Paid-up additions not supportable by the dividend scale",
            "Product withdrawn or not filed in the state",
            "Attained age outside the issue band",
        ],
    },
    "life/non_participating_whole_life": {
        "decline": [
            "Requested illustrations quoting non-guaranteed elements",
            "No guaranteed cash-value schedule available",
            "Product withdrawn in the state",
            "Attained age outside the issue limits",
        ],
    },
    "life/modified_whole_life": {
        "decline": [
            "Graded period beyond the regulatory maximum",
            "Non-forfeiture options not understood or signed",
            "Cash value below the required minimums",
            "Reduced benefits not fully disclosed",
        ],
    },
    "life/graded_guaranteed_issue_whole_life": {
        "decline": [
            "Attained age outside the guaranteed-issue band",
            "Notional amounts beyond the guaranteed-issue maximum",
            "State where the guaranteed-issue product is not filed",
            "Requested benefits outside the graded schedule",
        ],
        "endorsements": [
            "Accelerated Death Benefit",
            "Terminal Illness rider",
            "Waiver of Premium (where available)",
        ],
    },
    # =====================================================================
    # LIFE — UNIVERSAL
    # =====================================================================
    "life/guaranteed_universal_life": {
        "decline": [
            "No-lapse guarantee premium schedule that cannot be funded",
            "Attained age beyond the GUL issue limits",
            "Premium shortfall against the no-lapse schedule",
            "Riders outside the product's filing",
        ],
        "endorsements": [
            "Accelerated Death Benefit",
            "Waiver of Monthly Deductions",
            "Rider sum increases",
            "Overloan protection",
        ],
        "refer": [
            "Requested funding below the no-lapse schedule",
            "Rider or death-benefit-option changes",
            "Attained age near the GUL maximum",
        ],
    },
    "life/indexed_universal_life": {
        "decline": [
            "Projections relying on non-guaranteed index returns",
            "Floor, cap, or participation rate not confirmed in the state",
            "Requested overfunding above guideline limits",
            "Market-value adjustment not disclosed",
        ],
    },
    "life/variable_universal_life": {
        "decline": [
            "No registered representative or broker-dealer relationship",
            "Prospectus and risk disclosures not delivered",
            "Subaccount allocation outside the product",
            "Suitability not documented",
        ],
    },
    "life/current_assumption_universal_life": {
        "decline": [
            "Excessive current-assumption projections",
            "No minimum death-benefit-guarantee disclosure",
            "Premium below the cost-of-insurance corridor",
            "Attained age outside the issue limits",
        ],
    },
    # =====================================================================
    # LIFE — ENDOWMENT
    # =====================================================================
    "life/pure_endowment": {
        "decline": [
            "Maturity age beyond the plan term",
            "Premiums not payable over the full term",
            "Sum assured on non-earning lives beyond the limit",
            "Insurable interest not established",
        ],
        "endorsements": [
            "Accidental Death Benefit",
            "Waiver of Premium",
            "Guaranteed Insurability Option",
            "Back-end benefit rider",
        ],
        "refer": [
            "Sum assured above the financial-underwriting threshold",
            "Rated class or flat extra above the field limit",
            "Attained age outside the field issue band",
        ],
    },
    "life/full_endowment": {
        "decline": [
            "Coverage extended beyond the maximum maturity age",
            "Full surrender value not calculable",
            "Riders beyond the product schedule",
            "Attained age outside the issue limits",
        ],
    },
    "life/guaranteed_fixed_endowment": {
        "decline": [
            "Guaranteed maturity proceeds not supportable by the pricing basis",
            "Premiums outside the guaranteed schedule",
            "Product not filed in the jurisdiction",
            "Attained age outside the issue band",
        ],
    },
    # =====================================================================
    # LIFE — ULIP
    # =====================================================================
    "life/single_premium_ulip": {
        "decline": [
            "Single premium below the minimum",
            "Lock-in period not observed",
            "Source of funds not evidenced (AML)",
            "Attained age outside the ULIP band",
        ],
        "endorsements": [
            "Partial-withdrawal facility",
            "Fund switching",
            "Waiver of Premium",
            "Critical Illness rider",
        ],
        "refer": [
            "Single premium above the product maximum",
            "Fund-allocation or switching requests",
            "Attained age near the product band",
        ],
    },
    "life/regular_premium_ulip": {
        "decline": [
            "Premium below the minimum annual amount",
            "No allocation-charge disclosure on file",
            "Lock-in period not respected",
            "Lock-in not respected on early surrender",
        ],
    },
    "life/ulip_type_i": {
        "decline": [
            "Sum assured on the type-I basis outside the product limits",
            "No fund allocation selected",
            "Lock-in period not respected",
            "Attained age outside the issue band",
        ],
        "endorsements": [
            "Level sum assured fixed at inception",
            "Accidental Death Benefit rider",
            "Partial withdrawal (after lock-in)",
        ],
    },
    "life/ulip_type_ii": {
        "decline": [
            "Type-II sum assured not supportable at the attained age",
            "No fund selection made",
            "Lock-in period not respected",
            "Premium below the product minimum",
        ],
        "endorsements": [
            "Increasing sum assured aligned to fund value",
            "Return-of-Premium rider",
            "Top-up premium facility",
        ],
    },
    "life/pension_ulip": {
        "decline": [
            "Premium below the minimum for the pension plan",
            "Lock-in or vesting age not respected",
            "No annuity/vesting option selected",
            "Attained age outside the product band",
        ],
    },
    "life/child_ulip": {
        "decline": [
            "No parent-child insurable interest",
            "Child beyond the eligible age band",
            "Premium below the product minimum",
            "Payout structure outside the product schedule",
        ],
    },
    # =====================================================================
    # LIFE — MONEY-BACK
    # =====================================================================
    "life/traditional_money_back": {
        "decline": [
            "Survival-benefit intervals outside the plan schedule",
            "Premiums not payable over the full term",
            "Insurable interest not established",
            "Attained age outside the issue band",
        ],
        "endorsements": [
            "Accidental Death Benefit",
            "Waiver of Premium",
            "Critical Illness rider",
            "Guaranteed Insurability Option",
        ],
        "refer": [
            "Sum assured above the financial-underwriting threshold",
            "Rated class or flat extra above the field limit",
            "Attained age outside the field issue band",
        ],
    },
    "life/with_profit_money_back": {
        "decline": [
            "Requested illustrations relying on non-guaranteed bonuses",
            "Paid-up additions not supportable by the bonus scale",
            "Product withdrawn or not filed in the state",
            "Attained age outside the issue band",
        ],
    },
    "life/children_money_back": {
        "decline": [
            "No parent-child insurable interest",
            "Child beyond the maximum eligible age",
            "Premium-waiver requirement not elected where mandatory",
            "Attained age outside the product band",
        ],
    },
    # =====================================================================
    # LIFE — ANNUITY
    # =====================================================================
    "life/immediate_annuity": {
        "decline": [
            "No lump sum or liquidity evidence",
            "Annuitant age below the minimum for immediate payout",
            "Guarantee period beyond the product's actuarial limits",
            "Non-qualified status issues for a qualified-only product",
        ],
    },
    "life/deferred_annuity": {
        "decline": [
            "Premiums or deferral period outside the product terms",
            "No beneficiary designation",
            "Qualified/non-qualified status not established",
            "Surrender-charge schedule not disclosed",
        ],
    },
    "life/fixed_annuity": {
        "decline": [
            "Declared interest-rate guarantee not supportable",
            "Maturity beyond the product term",
            "Product not filed in the state",
            "Qualified/non-qualified status issues",
        ],
    },
    "life/variable_annuity": {
        "decline": [
            "No broker-dealer or registered-representative relationship",
            "Suitability not documented",
            "Subaccounts not available in the product",
            "Prospectus not delivered",
        ],
    },
    "life/indexed_annuity": {
        "decline": [
            "Crediting method not filed in the state",
            "No floor/cap/participation disclosure",
            "Market-value adjustment not disclosed",
            "Attained age outside the product band",
        ],
    },
    "life/life_annuity": {
        "decline": [
            "No life or lives certification",
            "Beneficiary not named",
            "Annuitant age outside the product limits",
            "Payment mode not selected",
        ],
    },
    "life/joint_survivor_annuity": {
        "decline": [
            "Joint annuitants without insurable interest or relationship proof",
            "No surviving-annuitant percentage selected",
            "Attained ages outside the product band",
            "No secondary beneficiary",
        ],
    },
    "life/qlac": {
        "decline": [
            "QLAC premium above the IRS dollar or percentage limit",
            "Income start date before the required age",
            "Not held within a qualified plan or IRA",
            "No RMD-offset documentation",
        ],
    },
    "life/structured_settlement_annuity": {
        "decline": [
            "No court-approved settlement order",
            "Assignment not recognized",
            "Payments not guaranteed by the obligor",
            "No qualified-assignment election",
        ],
    },
    # =====================================================================
    # HEALTH — INDIVIDUAL
    # =====================================================================
    "health/aca_marketplace_plan": {
        "decline": [
            "Not lawfully present (where a subsidy is claimed)",
            "Outside the open or special enrollment window",
            "Residency outside the plan's service area",
            "Non-compliant (non-ACA) plan characteristics",
        ],
        "endorsements": [
            "Pediatric dental/vision (essential benefit)",
            "Cost-sharing-reduction variant",
            "Premium tax-credit reconciliation",
            "Standardized plan option",
        ],
        "refer": [
            "Subsidy or immigration documentation issues",
            "Special-enrollment-eligibility disputes",
            "Out-of-state residency",
        ],
    },
    "health/off_exchange_major_medical": {
        "decline": [
            "Applicant outside the eligible age band",
            "Residency outside the filed states",
            "State where the product is not filed",
            "Requested benefit design outside the filed schedule",
        ],
        "endorsements": [
            "Maternity add-on module",
            "Dental/vision riders",
            "Prescription-management benefit",
            "Telehealth",
        ],
    },
    "health/short_term_limited_duration": {
        "decline": [
            "Medical condition requiring ongoing treatment",
            "Requested duration beyond the state maximum",
            "Pregnancy or expected maternity",
            "Requested in a state that bans short-term limited-duration plans",
        ],
        "endorsements": [
            "Accident add-on",
            "Fixed hospital-indemnity rider",
            "Telehealth",
        ],
    },
    "health/hdhp_hsa_qualified": {
        "decline": [
            "Plan design that is not a qualified high-deductible health plan",
            "HSA-ineligibility conflicts (other coverage, Medicare enrollment)",
            "Deductible below the IRS minimum",
            "Out-of-pocket maximum above the IRS limit",
        ],
        "endorsements": [
            "HSA contribution rider",
            "Preventive-care first-dollar benefit",
            "Telehealth",
        ],
    },
    "health/catastrophic_plan": {
        "decline": [
            "Applicant under 30 without a hardship exemption",
            "Non-qualified catastrophic plan design",
            "Enrollment outside the open or special window",
            "Income above the subsidy threshold where a subsidy is claimed",
        ],
        "endorsements": [
            "Preventive-care benefit",
            "Telehealth",
            "Pediatric add-on",
        ],
    },
    # =====================================================================
    # HEALTH — FAMILY FLOATER
    # =====================================================================
    "health/family_health_plan": {
        "decline": [
            "Dependents without proof of relationship",
            "Members resident outside the service area",
            "Late enrollment without a qualifying event",
            "Non-compliant plan design",
        ],
        "endorsements": [
            "Maternity module",
            "Pediatric dental/vision",
            "Telehealth",
            "Dependent student extension",
        ],
        "refer": [
            "Late enrollees without a qualifying event",
            "Non-standard dependent relationships",
            "Members requiring medical underwriting",
        ],
    },
    "health/family_hdhp_hsa_qualified": {
        "decline": [
            "Plan design that is not a qualified HDHP",
            "HSA-ineligible members included in the plan",
            "Deductible or out-of-pocket outside IRS limits",
            "First-dollar coverage that disqualifies the HSA",
        ],
        "endorsements": [
            "HSA deposit feature",
            "Preventive first-dollar benefit",
            "Telehealth",
        ],
    },
    "health/family_extended_dependents": {
        "decline": [
            "Dependents beyond the eligible age or relationship",
            "Missing disabled-dependent documentation",
            "Missing student-status verification",
            "Non-qualifying dependents added to the plan",
        ],
        "endorsements": [
            "Dependent student extension",
            "Disabled-dependent continuation",
            "Maternity module",
        ],
    },
    # =====================================================================
    # HEALTH — CRITICAL ILLNESS
    # =====================================================================
    "health/critical_illness_standalone": {
        "decline": [
            "Pre-existing critical illness within the waiting period",
            "Diagnosis not matching the policy's defined conditions",
            "Survival period not satisfied",
            "Condition excluded by the policy",
        ],
        "endorsements": [
            "Second-event benefit",
            "Waiver of Premium",
            "Return-of-premium option",
        ],
        "refer": [
            "Claims within the waiting period",
            "Pre-existing diagnosis near inception",
            "High-value claims above the auto-pay limit",
        ],
    },
    "health/disease_specific_critical_illness": {
        "decline": [
            "Diagnosis outside the defined condition",
            "Waiting period or survival period not satisfied",
            "Pre-existing diagnosis at inception",
            "No medical evidence of the qualifying diagnosis",
        ],
        "endorsements": [
            "Multiple-claim option",
            "Waiver of Premium",
            "Health-screening benefit",
        ],
    },
    "health/critical_illness_rider": {
        "decline": [
            "No base policy in force",
            "Rider not available at the attained age",
            "Condition onset before the rider effective date",
            "Rider sum outside the base-policy limits",
        ],
        "endorsements": [
            "Waiver of Premium",
            "Accelerated-benefit coordination",
            "Second-event option",
        ],
    },
    "health/critical_illness_multistage": {
        "decline": [
            "Stage outside the defined severity bands",
            "No progressive-stage medical evidence",
            "Waiting period not satisfied",
            "Duplicate claim for the same event",
        ],
        "endorsements": [
            "Second-event benefit",
            "Angioplasty/early-stage benefit",
            "Return-of-premium",
        ],
    },
    # =====================================================================
    # HEALTH — SENIOR
    # =====================================================================
    "health/medicare_supplement": {
        "decline": [
            "Not enrolled in Medicare Part A and Part B",
            "Under 65 without a qualifying disability",
            "Residency outside the plan's service area",
            "Requested during a closed enrollment with no guaranteed-issue right",
        ],
        "endorsements": [
            "Foreign-travel emergency",
            "Skilled-nursing coinsurance",
            "High-deductible variant",
        ],
        "refer": [
            "Enrollment outside guaranteed-issue windows",
            "Rated or declined in underwriting states",
            "Foreign-travel benefit requests",
        ],
    },
    "health/medicare_advantage": {
        "decline": [
            "Not entitled to Medicare Part A and Part B",
            "End-stage renal disease (in most circumstances)",
            "Out-of-network provider dependence",
            "Residency outside the plan service area",
        ],
    },
    "health/medigap_high_deductible_plan_g": {
        "decline": [
            "Plan not standardized in the state",
            "Deductible structure non-compliant with the standard plan",
            "Enrollment outside the guaranteed-issue window",
            "Not Medicare-eligible",
        ],
        "endorsements": [
            "Foreign-travel emergency",
            "Part B coinsurance",
            "Preventive-care benefit",
        ],
    },
    "health/medicare_advantage_snp": {
        "decline": [
            "No qualifying chronic or special-needs condition",
            "Not dual-eligible where the SNP requires it",
            "Residency outside the plan service area",
            "No Medicare Part A and Part B entitlement",
        ],
    },
    "health/medicare_part_d": {
        "decline": [
            "Not enrolled in Medicare",
            "Drugs not covered by the formulary",
            "Outside a valid enrollment period",
            "Non-qualified plan design",
        ],
    },
    # =====================================================================
    # HEALTH — GROUP
    # =====================================================================
    "health/small_group_health": {
        "decline": [
            "Group below the minimum participation",
            "No employer contribution toward premium",
            "Group outside the eligible size or state requirement",
            "Non-qualifying association treated as a small group",
        ],
        "endorsements": [
            "Dental/vision",
            "Life/disability bundle",
            "Employee-assistance program",
            "Telehealth",
        ],
        "refer": [
            "Group below minimum participation",
            "Non-standard class definitions",
            "Late entrants from a prior carrier",
        ],
    },
    "health/large_group_health": {
        "decline": [
            "Group outside the eligible size band",
            "Experience rating not supportable by credible data",
            "Non-compliant self-funded plan",
            "ERISA non-compliance",
        ],
    },
    "health/association_health_plan": {
        "decline": [
            "Association that is not a bona fide group",
            "Members outside the association's class",
            "No commonality of interest among members",
            "State where the arrangement is restricted (MEWA rules)",
        ],
    },
    "health/public_sector_group_health": {
        "decline": [
            "Entity that is not a qualified public employer",
            "Non-appropriation or funding issues",
            "Collectively bargained terms not evidenced",
            "Out-of-state participants outside the pool",
        ],
    },
    "health/level_funded_group_health": {
        "decline": [
            "Reserves not actuarially certified",
            "Group outside the level-funding criteria",
            "No credible claims experience",
            "Termination liability not addressed",
        ],
    },
    # =====================================================================
    # HEALTH — TOP-UP
    # =====================================================================
    "health/supplemental_gap_coverage": {
        "decline": [
            "No underlying primary coverage in force",
            "Benefits exceeding the primary's gaps",
            "Duplicate coverage for the same expense",
            "Non-compliant coordination-of-benefits design",
        ],
        "endorsements": [
            "Maternity gap module",
            "Prescription gap benefit",
            "Telehealth",
        ],
        "refer": [
            "Coordination-of-benefits disputes",
            "Claims exceeding the primary's gap",
            "Pre-existing conditions",
        ],
    },
    "health/hospital_indemnity": {
        "decline": [
            "No hospitalization evidence for a claim",
            "Benefit exceeding the policy's daily maximum",
            "Pre-existing hospitalization",
            "Coverage not in force on admission",
        ],
        "endorsements": [
            "Surgical-indemnity rider",
            "Critical-illness rider",
            "Maternity benefit",
        ],
    },
    # =====================================================================
    # HEALTH — PERSONAL ACCIDENT
    # =====================================================================
    "health/add_accident_indemnity": {
        "decline": [
            "No accidental event per the policy definition",
            "Injury from an excluded hazardous activity",
            "Benefits exceeding the scheduled indemnity",
            "Claim outside the coverage period",
        ],
        "endorsements": [
            "Hospital-indemnity rider",
            "Fracture/dislocation benefit",
            "Waiver of Premium",
        ],
        "refer": [
            "Claims near the exclusion boundary",
            "High-value or multiple claims",
            "Occupational or avocational exclusions",
        ],
    },
    "health/standalone_add": {
        "decline": [
            "Injury from an excluded activity or occupation",
            "No medical evidence of accidental injury",
            "Pre-existing conditions",
            "Attained age outside the product limits",
        ],
        "endorsements": [
            "Accidental death & dismemberment",
            "Hospital-indemnity rider",
            "Fracture/dislocation benefit",
        ],
    },
    # =====================================================================
    # HEALTH — DISABILITY
    # =====================================================================
    "health/short_term_disability": {
        "decline": [
            "Elimination period not satisfied",
            "Medical evidence not supporting the disability",
            "Self-inflicted or excluded conditions",
            "Occupation outside the product's class",
        ],
        "endorsements": [
            "Return-to-work benefit",
            "Waiver of Premium",
            "Hospital-confiner benefit",
        ],
        "refer": [
            "Benefit periods beyond the standard",
            "Occupational classes requiring rating",
            "Overlapping coverage",
        ],
    },
    "health/long_term_disability": {
        "decline": [
            "No qualifying total disability",
            "Pre-existing conditions within the look-back",
            "Occupation-based exclusions",
            "Attained age outside the product limits",
        ],
    },
    "health/disability_ptd": {
        "decline": [
            "No evidence of total and permanent disability",
            "Ability to work in any occupation not ruled out",
            "Excluded conditions",
            "Survival or waiting period not satisfied",
        ],
        "endorsements": [
            "Return-to-work incentive",
            "Waiver of Premium",
            "Cost-of-living adjustment",
        ],
    },
    "health/disability_ppd": {
        "decline": [
            "No permanent partial impairment per the schedule",
            "Impairment percentage not medically assessed",
            "Excluded causes",
            "Claim beyond the policy term",
        ],
        "endorsements": [
            "Recurrent-disability benefit",
            "Waiver of Premium",
            "Rehabilitation benefit",
        ],
    },
    # =====================================================================
    # GENERAL — MOTOR
    # =====================================================================
    "general/car_tp": {
        "decline": [
            "Unroadworthy or unsafe vehicle",
            "Invalid or unlicensed drivers",
            "Commercial use outside the private-car class",
            "Vehicle registered outside the state",
        ],
    },
    "general/car_comprehensive": {
        "decline": [
            "Pre-existing damage not disclosed",
            "Vehicle beyond the insured's insurable interest",
            "Heavily modified or racing vehicles",
            "Vehicles with a prior total-loss record",
        ],
        "endorsements": [
            "Zero-depreciation (Nil-dep) add-on",
            "Engine and gearbox protection",
            "Roadside assistance",
            "Consumables cover",
            "Towing & storage",
        ],
        "refer": [
            "Vehicles above the IDV threshold",
            "Heavily modified vehicles",
            "Vehicles with a total-loss history",
        ],
    },
    "general/tw_tp": {
        "decline": [
            "Two-wheeler used for hire or delivery outside the declared class",
            "Unlicensed riders",
            "Unroadworthy vehicle",
            "Invalid registration",
        ],
    },
    "general/tw_comprehensive": {
        "decline": [
            "Modified or racing two-wheelers",
            "Pre-existing damage",
            "No insurable interest",
            "Vehicle beyond the accepted age limit",
        ],
    },
    "general/cv_tp": {
        "decline": [
            "Commercial vehicle outside the permitted class",
            "Overloading beyond the registered capacity",
            "Invalid permits or licences",
            "Unroadworthy commercial vehicle",
        ],
    },
    "general/cv_comprehensive": {
        "decline": [
            "Commercial vehicle used outside the declared class",
            "Pre-existing damage",
            "No valid permit or fitness certificate",
            "Vehicles beyond the IDV schedule",
        ],
    },
    # =====================================================================
    # GENERAL — HOME
    # =====================================================================
    "general/home_structure": {
        "decline": [
            "Dwelling unoccupied beyond the permitted period",
            "Unrepaired prior damage",
            "Construction outside the accepted classes",
            "Coastal or wind zones without the wind endorsement",
        ],
    },
    "general/home_contents": {
        "decline": [
            "Contents without a valuation or inventory",
            "High-value items beyond the schedule",
            "Business or professional stock kept in the home",
            "Secondhand or undocumented items beyond limits",
        ],
    },
    "general/home_comprehensive": {
        "decline": [
            "Combined structure and contents beyond the sum insured",
            "Excluded perils (flood/earthquake) not endorsed",
            "Vacancy beyond the permitted period",
            "Unrepaired prior damage",
        ],
        "endorsements": [
            "Flood/earthquake extension",
            "Valuable-articles schedule",
            "Rent-receipt cover",
            "Public-liability link",
            "Emergency accommodation",
        ],
        "refer": [
            "Coastal, wind, and flood zones",
            "High-value contents above the schedule",
            "Aged roofs or unrepaired damage",
        ],
    },
    # =====================================================================
    # GENERAL — TRAVEL
    # =====================================================================
    "general/travel_domestic": {
        "decline": [
            "Travel outside the domestic territory",
            "Pre-existing conditions within the look-back",
            "Travel against medical advice",
            "Trip beyond the policy duration",
        ],
    },
    "general/travel_international": {
        "decline": [
            "Travel to sanctioned or high-risk destinations",
            "Travel against medical advice",
            "No valid visa or travel documents",
            "Activities excluded by the plan (extreme sports)",
        ],
        "endorsements": [
            "Adventure-sports extension",
            "Annual multi-trip option",
            "Rental-car damage excess",
            "Flight-delay cover",
            "Political-evacuation/natural-disaster cover",
        ],
        "refer": [
            "Travel to sanctioned or high-risk countries",
            "Pre-existing conditions within the look-back",
            "High-value trip-cost plans",
        ],
    },
    # =====================================================================
    # GENERAL — MARINE
    # =====================================================================
    "general/marine_cargo": {
        "decline": [
            "Cargo without shipping documents",
            "Inadequate packing or stowage",
            "Sanctioned trade",
            "Recurring losses from the same cause",
        ],
        "endorsements": [
            "Warehouse-to-warehouse extension",
            "War & strikes cover",
            "General-average contribution",
            "Debt-protection",
        ],
        "refer": [
            "Single transits above $5M",
            "High-theft or hazardous commodities",
            "Sanctioned trade routes",
        ],
    },
    "general/marine_hull": {
        "decline": [
            "Unseaworthy vessel",
            "No classification-society certificate",
            "Older hull without a current survey",
            "Owner without a maintenance program",
        ],
    },
    # =====================================================================
    # GENERAL — FIRE
    # =====================================================================
    "general/fire_residential": {
        "decline": [
            "Unoccupied or abandoned dwelling",
            "Unrepaired prior damage",
            "Unremediated electrical or wiring hazards",
            "Flammable storage in the home",
        ],
    },
    "general/fire_commercial": {
        "decline": [
            "Unprotected (Class 10) construction",
            "Combustible or flammable storage without controls",
            "Non-compliant fire or safety systems",
            "Unrepaired prior fire damage",
        ],
        "endorsements": [
            "Reinstatement of sum insured",
            "Removal-of-debris cover",
            "Loss-of-rent extension",
            "Business-interruption link",
        ],
        "refer": [
            "Unprotected construction or high-hazard occupancy",
            "TIV above the authority limit",
            "Non-compliant fire systems",
        ],
    },
    # =====================================================================
    # GENERAL — LIABILITY
    # =====================================================================
    "general/professional_indemnity_gi": {
        "decline": [
            "Professionals with lapsed licensure",
            "Prior professional-negligence claims",
            "Firms outside the accepted professions",
            "Revenue not reconcilable to filings",
        ],
        "endorsements": [
            "Retroactive cover",
            "Defence-costs cover",
            "Sub-contractor cover",
        ],
        "refer": [
            "Professions outside the accepted list",
            "Retroactive-cover requests",
            "Prior claims or litigation disclosure",
        ],
    },
    "general/public_liability_gi": {
        "decline": [
            "Hazardous operations outside the accepted class",
            "Premises with unresolved safety hazards",
            "No public-access controls",
            "Premises with prior public-injury claims",
        ],
    },
    "general/product_liability_gi": {
        "decline": [
            "Products with known defects or recalls",
            "Products sold into sanctioned markets",
            "Unlabelled or uncertified products",
            "Products with prior product-liability claims",
        ],
    },
    # =====================================================================
    # GENERAL — CYBER
    # =====================================================================
    "general/cyber_data_breach": {
        "decline": [
            "No security controls (multi-factor authentication, backups)",
            "Prior breach not remediated",
            "Storing data without a lawful basis",
            "Inability to accept the nation-state/APT exclusion",
        ],
        "endorsements": [
            "Business-interruption extension",
            "Regulatory-defence cover",
            "PCI fines & penalties",
            "Restoration/data-recovery cover",
        ],
        "refer": [
            "Any prior breach or ransomware event",
            "Data volumes above the threshold",
            "Nation-state/APT attribution",
        ],
    },
    "general/cyber_ransomware": {
        "decline": [
            "No offline or immutable backups",
            "No endpoint-detection-and-response protection",
            "Prior ransomware event at inception",
            "Ransom payment that would breach OFAC sanctions",
        ],
    },
    # =====================================================================
    # GENERAL — CROP
    # =====================================================================
    "general/crop_yield": {
        "decline": [
            "Acreage reported after the acreage-reporting deadline",
            "Crops grown outside the approved practice",
            "No actual-production-history or yield records",
            "Land in a prohibited conservation use",
        ],
        "endorsements": [
            "Replanting benefit",
            "Yield-adjustment option",
            "Post-harvest cover",
        ],
        "refer": [
            "Acreage above the delegated threshold",
            "Non-standard crops or practices",
            "Claims with an acreage-reporting dispute",
        ],
    },
    "general/crop_weather": {
        "decline": [
            "Weather-index cover without the required weather data",
            "Crop outside the covered region or index",
            "No insurable interest",
            "Backdated coverage",
        ],
    },
    # =====================================================================
    # GENERAL — ANIMAL
    # =====================================================================
    "general/livestock_cattle": {
        "decline": [
            "Animals without health or vaccination certification",
            "Herd in a disease-control zone",
            "No ownership or valuation records",
            "Mortality beyond the covered causes",
        ],
        "endorsements": [
            "Mortality extension",
            "Theft cover",
            "Transit cover",
            "Veterinary-fee benefit",
        ],
        "refer": [
            "Herd value above the delegated limit",
            "Disease-quarantine zones",
            "Theft-cover requests in high-crime areas",
        ],
    },
    "general/pet_insurance": {
        "decline": [
            "Pre-existing conditions",
            "Attained age outside the eligible band",
            "Animals used for breeding, fighting, or farming",
            "No veterinary records",
        ],
    },
    # =====================================================================
    # GENERAL — EVENT
    # =====================================================================
    "general/wedding_insurance": {
        "decline": [
            "Event without a signed venue or vendor contract",
            "No defined cancellation or postponement dates",
            "Pre-existing cancellation reason",
            "Vendor no-show treated as covered without endorsement",
        ],
    },
    "general/concert_event_insurance": {
        "decline": [
            "No public-authority permit or safety plan",
            "Crowd beyond venue capacity",
            "Key performer already in breach",
            "Adverse-weather exposure without a contingency plan",
        ],
        "endorsements": [
            "Adverse-weather cover",
            "Non-appearance extension",
            "Key-performer abandonment",
            "Cancellation/postponement",
        ],
        "refer": [
            "Crowd above venue capacity",
            "Pyro/stunt/high-risk elements",
            "Key-performer non-appearance",
        ],
    },
    # =====================================================================
    # GENERAL — TITLE
    # =====================================================================
    "general/title_insurance_gi": {
        "decline": [
            "Known title defects or tax liens",
            "Chain-of-title gaps",
            "Fraudulent or forged deeds",
            "Jurisdiction where the product is not filed",
        ],
        "endorsements": [
            "Survey cover",
            "Encumbrance/defect endorsement",
            "Builder/developer endorsement",
        ],
        "refer": [
            "Known title defects or liens",
            "Chain-of-title gaps",
            "Survey or encroachment issues",
        ],
    },
    # =====================================================================
    # GENERAL — MORTGAGE
    # =====================================================================
    "general/mortgage_insurance_gi": {
        "decline": [
            "No mortgage or loan documentation",
            "Loan already in default at inception",
            "Property outside the accepted region",
            "Borrower without insurable interest",
        ],
        "endorsements": [
            "Disability-linked cover",
            "Unemployment extension",
            "Critical-illness rider",
        ],
        "refer": [
            "Loan in default or arrears",
            "Borrower with no insurable interest",
            "Non-standard property types",
        ],
    },
    # =====================================================================
    # GENERAL — PROVIDER
    # =====================================================================
    "general/insurer_psu": {
        "decline": [
            "KYC mismatch or unverifiable identity",
            "No valid proof of identity/address for a PSU-underwritten product",
            "Politically exposed persons without enhanced due diligence",
        ],
        "endorsements": [
            "Provider/insurer-specific product schedule",
            "Nominee and assignment endorsement",
            "KYC-documentation endorsement",
        ],
        "refer": [
            "Non-standard provider KYC",
            "PEP or enhanced-due-diligence cases",
            "Proposals routed to a PSU insurer outside the filed product list",
        ],
    },
    "general/insurer_private": {
        "decline": [
            "KYC mismatch or unverifiable identity",
            "No valid proof of identity/address for a private-insurer product",
            "Application against a withdrawn private-insurer tariff",
        ],
        "endorsements": [
            "Provider/insurer-specific product schedule",
            "Nominee and assignment endorsement",
            "Underwriting-flexibility clause (private insurer)",
        ],
        "refer": [
            "Non-standard provider KYC",
            "Risk outside the private insurer's filed tariff",
            "Any proposal requiring private-insurer underwriting flexibility",
        ],
    },
    "general/reinsurance_treaty": {
        "decline": [
            "Unlicensed ceding insurer",
            "New ceding relationship without loss data",
            "Cross-border layer without regulatory/AML clearance",
        ],
        "endorsements": [
            "Treaty/facultative terms",
            "Portfolio withdrawal and cession rights",
            "Profit-share and sliding-scale commission",
        ],
        "refer": [
            "Any cross-border reinsurance layer",
            "New ceding relationship without loss data",
            "Aggregate exposures above the treaty capacity",
        ],
    },
}
