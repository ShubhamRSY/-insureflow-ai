"""Per-product underwriting overrides for the RAG corpus generator.

The category rules in ``rag_knowledge_base.py`` are the line/class default a
product inherits. This module layers product-specific content on top for every
product whose cover, perils, exclusions, limits, rating, or authority diverge
from that default. Keys are ``"<lob>/<product_id>"``; each value lists only the
fields that differ, and a listed field replaces the category value entirely.
"""

from __future__ import annotations

PRODUCT_OVERRIDES: dict[str, dict[str, list[str]]] = {
    # =====================================================================
    # COMMERCIAL — PROPERTY
    # =====================================================================
    "commercial/business_interruption": {
        "market": "Insureds whose income depends on the continued operation of an insured location or its supply chain.",
        "exclusions": [
            "No direct physical damage to the insured's own property (time-element cover only)",
            "Loss from utilities, denial of access, or a supplier/customer unless endorsed",
            "Loss of market, cash, and non-continuing expenses",
            "Ordinary payroll unless specifically insured",
        ],
        "endorsements": [
            "Contingent Business Interruption",
            "Civil Authority / Denial of Access",
            "Extra Expense",
            "Extended Period of Indemnity",
            "Ordinary Payroll",
        ],
        "limits": [
            "12-month indemnity period with a 72-hour waiting period",
            "Monthly limit = projected gross earnings plus continuing expenses",
            "Extended period of indemnity 30–90 days",
        ],
        "rating": [
            "Realism of the business-income worksheet (revenue, continuing expenses, extra expense)",
            "Continuing-expenses and ordinary-payroll election",
            "Indemnity period vs realistic restoration time",
            "Dependent suppliers/customers and civil-authority exposure",
        ],
        "refer": [
            "Indemnity period above 12 months",
            "Single-customer dependency above 30% of revenue",
        ],
    },
    "commercial/builders_risk": {
        "market": "Owners, general contractors, and developers insuring a project under construction or renovation.",
        "eligible": [
            "Defined project with a construction schedule and completed value",
            "Contractor with relevant experience and no unresolved defects claims",
        ],
        "exclusions": [
            "Existing structures unless the project is a renovation",
            "Wear, tear, and faulty workmanship",
            "Testing/commissioning and performance failure unless endorsed",
            "Contractors' tools and equipment (separate cover)",
            "Soft costs and delay unless endorsed",
        ],
        "endorsements": [
            "Soft Costs / Delay in Completion",
            "Design-Build Professional",
            "Expediting Expense",
            "Water Damage — testing",
            "Maintenance period extension",
        ],
        "limits": [
            "Completed value of the project plus soft costs",
            "Soft costs 10–25% of hard costs",
            "Delay-in-completion 3–12 months",
            "Per-location and catastrophe sub-limits",
        ],
        "rating": [
            "Project value, duration, and type (new vs renovation)",
            "Location CAT and flood-zone exposure",
            "Contractor experience and use of wraps",
            "Off-site storage and transit exposure",
        ],
        "refer": [
            "Project value above $50M",
            "Renovation of an occupied high-rise",
            "Delay-in-completion above 12 months",
        ],
    },
    "commercial/inland_marine": {
        "market": "Property in transit, mobile equipment, and floating/unscheduled property used in business.",
        "exclusions": [
            "Inherent vice and wear",
            "Unexplained or mysterious disappearance unless perils are specified",
            "Voluntary parting with property",
            "Employee dishonesty (crime form)",
        ],
        "endorsements": [
            "Motor Truck Cargo",
            "EDP / Computer Equipment",
            "Scheduled Property Floater",
            "Installation / Builder's Equipment",
        ],
        "limits": [
            "Per-conveyance and per-location limits",
            "Scheduled vs blanket item limits",
            "Deductibles by class of property",
        ],
        "rating": [
            "Property class and mode of transit",
            "Territory and hauling radius",
            "Value at risk and catastrophe exposure",
        ],
    },
    "commercial/ocean_marine": {
        "market": "Cargo in international transit and ocean-going hull/vessel exposures.",
        "exclusions": [
            "Inherent vice and ordinary leakage",
            "Insufficiency of packing unless D/B/U is insured",
            "War and strikes unless included",
            "Delay and loss of market",
        ],
        "endorsements": [
            "War & Strikes",
            "Duty and Brand (D/B/U)",
            "Annual Declaration / Sales Turnover",
            "Classification / ISO warranty",
        ],
        "limits": [
            "Cargo: CIF/invoice value plus 10%",
            "Hull: agreed value subject to Institute warranties",
        ],
        "rating": [
            "Commodity, packing, and route",
            "Conveyance type and ICC(A/B/C) basis",
            "Voyage vs annual declaration volume",
        ],
        "refer": [
            "Hull vessel value above $10M",
            "War-zone or sanctioned-trade voyages",
        ],
    },
    "commercial/equipment_breakdown": {
        "market": "Owners of boilers, pressure vessels, mechanical/electrical equipment, and HVAC systems.",
        "eligible": ["Equipment with a current inspection/boiler certificate where required"],
        "exclusions": [
            "Normal wear, tear, corrosion, and gradual deterioration",
            "Obsolescence and rebuilding to code unless endorsed",
            "Loss from water/process not attributable to an equipment breakdown",
            "Terrorism unless endorsed",
        ],
        "endorsements": [
            "Spoilage",
            "Utility Services / Service Interruption",
            "Data Restoration",
            "Hazardous Substances cleanup",
        ],
        "limits": [
            "Per-item equipment sub-limits",
            "Spoilage 10–25% of the limit",
            "Extra expense and business income for 12 months",
            "Hazardous-substances cleanup sub-limit",
        ],
        "rating": [
            "Age, condition, and type of equipment",
            "Boiler/pressure-vessel inspection history",
            "Spoilage and utility-service exposure",
        ],
        "refer": ["Aged pressure vessels without inspection", "Spoilage values above $1M"],
    },
    "commercial/flood_commercial": {
        "market": "Commercial property owners/tenants needing standalone flood cover (private or excess over NFIP).",
        "exclusions": [
            "War and nuclear perils",
            "Wear, tear, and gradual deterioration",
            "Earth movement (separate earthquake cover)",
            "Perils insured by the companion property policy",
        ],
        "endorsements": ["Contents-only", "Excess Flood over NFIP", "Basement Contents", "Terrorism"],
        "limits": [
            "Building and contents limits per schedule",
            "Basement/contents sub-limits",
            "Maximum per-location program capacity",
            "30-day waiting period for newly added coverage",
        ],
        "rating": [
            "FEMA flood zone and elevation certificate",
            "Occupancy and lowest-floor elevation",
            "NFIP vs private placement",
            "Community Rating System (CRS) credit",
        ],
        "refer": [
            "Any building in a V-zone or below base flood elevation without mitigation",
            "TIV above program flood capacity",
        ],
    },
    "commercial/earthquake_commercial": {
        "market": "Commercial property with earthquake exposure, standalone or as a DIC layer.",
        "exclusions": [
            "War and nuclear perils",
            "Wear, tear, and gradual deterioration",
            "Flood (separate cover)",
        ],
        "endorsements": ["Sprinkler Leakage — Earthquake", "Excess of primary EQ", "Business income extension"],
        "limits": [
            "Percentage deductibles 2–5% of TIV",
            "Per-location and aggregate limits",
            "Sprinkler-leakage sub-limit",
        ],
        "rating": [
            "Seismic zone and site/soil conditions",
            "Construction type and building age",
            "Retrofit credits (bracing, anchorage)",
            "Loss history",
        ],
        "refer": ["Unreinforced masonry in a high seismic zone", "Single-schedule TIV above $50M"],
    },
    "commercial/crime": {
        "market": "Businesses exposing money, securities, and other property to employee dishonesty and fraud.",
        "exclusions": [
            "Indirect or consequential loss",
            "Legal fees and fines",
            "War and nuclear perils",
            "Loss discovered beyond the policy's discovery period",
        ],
        "endorsements": [
            "Computer Fraud",
            "Funds Transfer Fraud",
            "Employee Benefit Plan (ERISA) coverage",
            "Client/third-party property",
        ],
        "limits": [
            "Employee dishonesty per-employee and aggregate limits",
            "Forgery or alteration limit",
            "Computer/funds-transfer fraud sub-limits",
            "ERISA fidelity bond limits",
        ],
        "rating": [
            "Number of employees and revenue",
            "Internal controls and segregation of duties",
            "Prior fidelity losses",
        ],
        "refer": ["Employee dishonesty limits above $1M", "Any prior unrecovered dishonesty loss"],
    },
    "commercial/ordinance_or_law": {
        "market": "Owners of older buildings where code upgrades trigger post-loss reconstruction costs.",
        "exclusions": [
            "Contamination and pollution cleanup",
            "Demolition not required by code",
            "Loss to the undamaged portion unless endorsed",
        ],
        "endorsements": ["Undamaged portion of the building", "Demolition Cost", "BI period-of-restoration coordination"],
        "limits": [
            "Increased Cost of Construction 5–25% of the limit",
            "Demolition cost sub-limit",
            "Combined ICC + demolition cap",
        ],
        "rating": ["Building age and code adoption date", "Jurisdiction code enforcement", "Total insured value"],
        "refer": ["Pre-code buildings in strict jurisdictions", "ICC limits above 25% of TIV"],
    },
    "commercial/rent_loss_of_rents": {
        "market": "Landlords and owners exposing rental income to a covered physical loss.",
        "exclusions": [
            "Loss where there is no physical damage to the premises",
            "Lease cancellation or non-renewal",
            "Rent-control or regulatory changes",
            "Consequential loss",
        ],
        "endorsements": ["Extended Period of Indemnity", "Civil Authority / Denial of Access", "Lease cancellation sub-limit"],
        "limits": ["Monthly gross rent × indemnity period", "12-month default indemnity", "Fair rental value basis"],
        "rating": ["Rental value and occupancy", "Tenant concentration and lease terms", "Indemnity period"],
        "refer": ["Single-tenant dependency above 50% of income", "Indemnity period above 18 months"],
    },
    "commercial/dic_excess_flood": {
        "market": "Insureds filling gaps between a primary property program and an uninsured peril (flood, quake).",
        "exclusions": [
            "Every peril already covered by the primary property policy (DIC responds only where the primary does not)",
            "War and nuclear perils",
            "Wear, tear, and gradual deterioration",
            "Loss within the primary deductible",
        ],
        "endorsements": ["Flood buy-back", "Earthquake buy-back", "Difference in deductibles"],
        "limits": [
            "DIC attachment above the primary limit",
            "Flood and earthquake sub-limits",
            "Combined single limit over the primary",
        ],
        "rating": ["Structure of the primary program and the gaps to fill", "CAT-zone exposure", "Retention/deductible gaps"],
        "refer": ["Any new CAT-zone schedule", "Attachment/deductible gaps not articulated by the broker"],
    },
    # =====================================================================
    # COMMERCIAL — LIABILITY
    # =====================================================================
    "commercial/product_liability": {
        "market": "Manufacturers, distributors, and importers with products-completed-operations exposure.",
        "exclusions": [
            "Contractual liability assumed beyond tort",
            "Recall and withdrawal expense",
            "Damage to the insured's own product",
            "Impaired property and unsold stock",
        ],
        "endorsements": ["Limited Recall", "Vendors endorsement", "Foreign products territory"],
        "limits": ["Products-completed operations aggregate", "Recall/withdrawal sub-limit", "Per-occurrence limit"],
        "rating": [
            "Product type and annual receipts",
            "Distribution geography and foreign exposure",
            "Quality-control and testing program",
            "Loss history",
        ],
        "refer": ["Foreign (US/Canada) distribution", "Any prior recall or product lawsuit"],
    },
    "commercial/errors_omissions": {
        "market": "Professional-service firms and consultants selling advice or services for a fee.",
        "exclusions": [
            "Intentional/dishonest acts",
            "Fines and penalties",
            "Fee refunds",
            "Bodily injury/property damage unless endorsed",
            "Prior acts before the retroactive date",
        ],
        "endorsements": [
            "Extended Reporting Period",
            "Retroactive date change",
            "Defence costs outside the limit",
            "Subcontracted professional services",
        ],
        "limits": ["Claims-made per-claim/aggregate", "Defence inside the limit (or first-dollar)", "Extended reporting period 90–365 days"],
        "rating": [
            "Professional fee income and class",
            "Retroactive date and claims history",
            "Territory/jurisdiction",
            "Sub-limit and defence-cost structure",
        ],
        "refer": ["US/Canada jurisdiction exposure", "Any known circumstance or prior claim", "Fee income above $10M"],
    },
    "commercial/architects_engineers": {
        "market": "Design professionals — architects, engineers, and design-build firms.",
        "exclusions": [
            "Professional liability assumed by contract beyond the standard of care",
            "Insured vs insured",
            "Fee refunds",
            "Joint ventures unless endorsed",
            "Prior acts before the retroactive date",
        ],
        "endorsements": ["Design-build professional", "Joint venture", "Extended Reporting Period", "Retroactive date change"],
        "limits": ["Claims-made per-claim/aggregate", "PL/MPL structure", "Defence inside the limit"],
        "rating": [
            "Fee income and discipline (structural, geotechnical, etc.)",
            "Project type and size",
            "Retro date and claims",
            "Subconsultant exposure",
        ],
        "refer": ["Tunnel/bridge/marine structural work", "Any condo or defect claim", "Fee income above $5M"],
    },
    "commercial/miscellaneous_professional": {
        "market": "Unclassified professional-service classes not written on a dedicated E&O form.",
        "exclusions": [
            "Professional services outside the declared class",
            "Intentional acts",
            "Fee refunds",
            "Bodily injury/property damage",
        ],
        "endorsements": ["Retroactive date change", "Extended Reporting Period", "Additional named insureds"],
        "limits": ["Claims-made per-claim/aggregate", "Defence inside the limit", "Retroactive-date clarity required at inception"],
        "rating": ["Class of profession and fee income", "Retro date and claims", "Territory"],
        "refer": ["Classes resembling healthcare or construction design", "Any known circumstance"],
    },
    "commercial/directors_officers": {
        "market": "Public and private company directors and officers, and the entity, against management liability.",
        "exclusions": [
            "Fraud or dishonesty after final adjudication",
            "Prior acts/pending litigation before inception",
            "Insured vs insured (except carve-backs)",
            "Personal profit or advantage",
            "Fines and penalties where uninsurable",
        ],
        "endorsements": [
            "Side A DIC",
            "Entity securities coverage",
            "Defence costs outside the limit",
            "Broad-form extensions",
        ],
        "limits": ["Side A/B/C limits with a Side A DIC tower", "Per-claim/aggregate", "Retention tiers by security type"],
        "rating": [
            "Market cap and financial strength",
            "Industry sector and IPO/SPAC status",
            "Prior securities claims",
            "Retention and limit structure",
        ],
        "refer": ["Any prior securities class action", "IPO/SPAC within 24 months", "Financial restatement"],
    },
    "commercial/epli": {
        "market": "Employers seeking cover for employment-practices claims (discrimination, harassment, wrongful termination).",
        "exclusions": [
            "Wage-and-hour / FLSA unless endorsed",
            "Intentional or pre-existing HR policies",
            "Contractual obligations",
            "Fines and penalties",
            "Third-party claims unless endorsed",
        ],
        "endorsements": ["Third-party (customer) coverage", "Wage-and-hour sub-limit", "Defence costs outside the limit", "ADA/EEOC stop-gap"],
        "limits": ["Per-claim/aggregate", "Third-party coverage up to 1/3 of the limit", "Defence inside the limit"],
        "rating": ["Headcount and turnover", "Industry and prior EPL claims", "HR controls and handbook", "Retention"],
        "refer": ["Any pending EEOC/DFEH charge", "Headcount above 5,000", "Wage-and-hour class exposure"],
    },
    "commercial/fiduciary_liability": {
        "market": "Plan sponsors and fiduciaries of employee benefit plans (ERISA).",
        "exclusions": ["Non-fiduciary acts", "Benefits due under the plan", "Fines/penalties where uninsurable", "Insured vs insured"],
        "endorsements": ["Extended Reporting Period", "Employee Benefit Plan coverage", "Outside-limit defence"],
        "limits": ["Per-claim/aggregate", "Defence inside the limit"],
        "rating": ["Plan assets and participants", "Plan type (DB/DC/ESOP)", "Prior claims and fiduciary controls"],
        "refer": ["ESOP or multi-employer plan", "Any prior DOL investigation"],
    },
    "commercial/cyber_liability": {
        "market": "Businesses with network, privacy, and technology exposures seeking first- and third-party cyber cover.",
        "exclusions": [
            "Betterment and prior known incidents",
            "War and state-sponsored attacks",
            "Bodily injury and property damage that is not data",
            "Infrastructure/utility failure",
            "Unencrypted portable-device losses unless reported",
        ],
        "endorsements": [
            "Social Engineering / Impersonation Fraud",
            "Systemic/Catastrophe sub-limit",
            "Third-party service provider",
            "Reputational and notification extensions",
        ],
        "limits": [
            "Separate liability and first-party limits with sub-limits",
            "Cyber-extortion / funds-transfer-fraud sub-limits",
            "Retention tiers by revenue",
        ],
        "rating": ["Revenue, records, and industry", "Controls: MFA, backups, EDR, patch status", "Prior incidents", "Retention and sub-limits"],
        "refer": ["No MFA/offline backups or unsupported systems", "Any prior unremediated breach", "Regulated data at scale"],
    },
    "commercial/umbrella": {
        "market": "Insureds needing excess limits over scheduled primary policies (auto, GL, employers' liability).",
        "exclusions": [
            "Every exposure not covered by the scheduled underlying policies (unless self-maintained)",
            "The retention of the underlying",
            "War and nuclear perils",
            "Uninsurable fines and penalties",
        ],
        "endorsements": ["Self-maintained/non-owned underlying", "Extended reporting for claims-made underlying", "Follow-form (or broader) wording"],
        "limits": ["Occurrence and aggregate on top of underlying", "Self-insured retention where no underlying exists", "Drop-down where the underlying is exhausted"],
        "rating": ["Underlying limits and coverage breadth", "Attachment point vs the underlying", "Catastrophe and class exposure"],
        "refer": ["Umbrella limits above $5M", "Unresolved gaps between underlying forms", "Non-standard self-maintained underlying"],
    },
    "commercial/pollution": {
        "market": "Contractors, manufacturers, and handlers with environmental liability and cleanup exposure.",
        "exclusions": [
            "Known/preexisting conditions before inception",
            "Fines and penalties (unless insurable)",
            "Asbestos/lead abatement unless declared",
            "Contractual liability beyond tort",
            "Products pollution unless declared",
        ],
        "endorsements": ["Contractor's pollution (CPL)", "Products/completed-ops pollution", "Transportation pollution", "Extended Reporting Period"],
        "limits": [
            "Claims-made with third-party, cleanup, and defence sub-limits",
            "Cleanup per-incident and aggregate",
            "Defence inside the limit (or first-dollar)",
        ],
        "rating": ["Industry, operations, and storage", "Volume/throughput and containment", "Prior incidents and regulatory history", "Cleanup and defence sub-limits"],
        "refer": ["Any regulatory citation or open cleanup", "Underground storage tanks at scale", "Cumulative limits above $10M"],
    },
    "commercial/liquor_liability": {
        "market": "Bars, taverns, restaurants, and venues serving or furnishing alcohol.",
        "exclusions": [
            "Injury to the insured/employees in the course of employment",
            "Serving visibly intoxicated persons where prohibited by statute",
            "Assault and battery unless endorsed",
            "Statutory dram-shop penalties",
        ],
        "endorsements": ["Assault and Battery", "Additional insured (landlord)", "Defence costs"],
        "limits": ["Per common-cause and aggregate", "Assault-and-battery buy-back sub-limit"],
        "rating": ["Receipts, hours, and establishment type", "Training/certification (e.g., TIPS)", "Assault-and-battery history", "Prior liquor claims"],
        "refer": ["Late-night/high-volume venues", "Any assault-and-battery history", "BYOB or unlicensed service"],
    },
    "commercial/media_liability": {
        "market": "Media, publishers, broadcasters, and content creators exposing defamation and content liability.",
        "exclusions": [
            "Knowingly false or malicious content",
            "Contractual obligations",
            "Prior acts before the retro date",
            "Failure to perform professional services",
            "Fines and penalties",
        ],
        "endorsements": ["Prior acts extension", "Extended Reporting Period", "Advertising/online content"],
        "limits": ["Claims-made per-claim/aggregate", "Defence inside the limit", "Advertising-injury and content sub-limits"],
        "rating": ["Media type, reach, and content", "Prior libel/defamation claims", "Retro date and jurisdictions"],
        "refer": ["Investigative journalism exposure", "Any prior defamation claim"],
    },
    # =====================================================================
    # COMMERCIAL — WORKFORCE (non-WC benefits)
    # =====================================================================
    "commercial/employers_liability": {
        "market": "Employers needing standalone employer's liability where WC is monopolistic or separately placed.",
        "exclusions": ["WC benefits (differently covered)", "Intentional acts", "Federal employment classes unless extended"],
        "endorsements": ["Waiver of subrogation", "US Longshore & Harbor Workers' extension"],
        "limits": ["$1M / $1M / $1M or state-specific"],
        "rating": ["Class and payroll", "State benefit levels", "Loss history"],
        "refer": ["Multi-state payroll", "Heavy loss history"],
    },
    "commercial/group_health": {
        "market": "Employers offering group medical benefits to employees.",
        "exclusions": ["No health-status underwriting within the group", "Not a substitute for individual major medical on termination"],
        "endorsements": ["Dental/vision", "Stop-loss (self-funded)", "COBRA administration"],
        "limits": ["ACA essential health benefits and out-of-pocket caps", "Stop-loss attachment points (self-funded)"],
        "rating": ["Participation and contribution", "Demographics and SIC class", "Region and carrier network"],
        "refer": ["Self-funded without stop-loss", "Minimum-participation waivers"],
    },
    "commercial/group_life": {
        "market": "Employers providing group term life and AD&D to employees.",
        "exclusions": ["Suicide within two years (varies)", "Material misrepresentation"],
        "endorsements": ["AD&D", "Dependent life", "Portability/convertibility"],
        "limits": ["Flat or multiple-of-salary benefit schedules", "Guaranteed-issue / evidence-of-insurability limits"],
        "rating": ["Age/gender census", "Benefit schedule", "Participation"],
        "refer": ["Benefit above $500K without EOI", "Adverse census mortality"],
    },
    "commercial/group_disability": {
        "market": "Employers providing short- and long-term group disability income.",
        "exclusions": ["Pre-existing condition period", "Self-inflicted injury; war"],
        "endorsements": ["Own-occupation (2-year) for select classes", "COLA", "Return-to-work incentive"],
        "limits": ["Monthly benefit to 60% of income (integrated with other income)", "Maximum benefit period to SSNRA"],
        "rating": ["Industry and job class", "Participation and integration offset", "Prior claims"],
        "refer": ["High-income/high-benefit populations", "Adverse disability claims experience"],
    },
    "commercial/key_person": {
        "market": "Businesses insuring a key owner/executive whose death would disrupt operations.",
        "exclusions": ["Suicide within two years", "Material misrepresentation"],
        "endorsements": ["Accelerated Death Benefit", "Waiver of Premium"],
        "limits": ["Face amount tied to the documented value of the key person", "Financial underwriting per role"],
        "rating": ["Age/health/tobacco of the key person", "Financial justification", "Product type (term/permanent)"],
        "refer": ["Face above the supported key-person value", "Cross-purchase/buy-sell without an agreement"],
    },
    "commercial/business_overhead": {
        "market": "Small businesses and professionals needing ongoing expense cover during an owner's disability.",
        "exclusions": ["Pre-existing condition period", "Expenses not listed in the schedule", "Self-inflicted injury; war"],
        "endorsements": ["COLA", "Residual disability", "Future increase option"],
        "limits": ["Monthly overhead benefit capped at actual continuing expenses", "Benefit period 12–24 months"],
        "rating": ["Fixed monthly expenses", "Occupation class", "Elimination/benefit periods"],
        "refer": ["Benefit exceeding documented overhead", "High-risk occupations"],
    },
    "commercial/voluntary_benefits": {
        "market": "Employers offering employee-paid worksite benefits (critical illness, accident, hospital indemnity, etc.).",
        "exclusions": ["Pre-existing condition periods where applicable", "Self-inflicted injury"],
        "endorsements": ["Payroll deduction", "Portability", "Family tiering"],
        "limits": ["Benefit tiers per product elected", "Guaranteed-issue volumes"],
        "rating": ["Census demographics", "Enrollment percentage", "Product mix"],
        "refer": ["Low enrollment projections", "Adverse claim experience on the block"],
    },
    # =====================================================================
    # COMMERCIAL — AUTO
    # =====================================================================
    "commercial/fleet": {
        "market": "Businesses operating multiple power units under DOT or state authority.",
        "eligible": ["DOT compliance file and driver-qualification files", "MVR monitoring program"],
        "exclusions": ["Pollution from cargo unless endorsed", "Livery use without endorsement", "Intentional damage"],
        "endorsements": ["Hired/Non-Owned", "Pollution buy-back (truckers)", "Scheduled/unscheduled units", "Employee-driver endorsements"],
        "limits": ["CSL $1M–$5M by fleet size", "Physical damage by schedule", "Hired/NNO $1M"],
        "rating": ["Fleet size, radius, and commodity", "Driver MVR and experience", "Loss history and preventable-accident review"],
        "refer": ["Fleet above 25 units", "Any fatality or hazmat incident", "Radioactive handling"],
    },
    "commercial/hnoa": {
        "market": "Businesses with no owned autos but hired and non-owned auto exposure.",
        "exclusions": ["Autos owned by the insured", "Livery/rideshare unless endorsed", "Pollution"],
        "endorsements": ["Employee Hired Auto", "Physical damage for hired autos"],
        "limits": ["CSL $1M", "Hired-physical-damage sub-limit"],
        "rating": ["Payroll, number of drivers, and territory", "Use (delivery, sales, service)"],
        "refer": ["Delivery/rideshare exposure", "Any owned unit (write a fleet instead)"],
    },
    "commercial/motor_truck_cargo": {
        "market": "Motor carriers insuring goods in transit while under their control.",
        "exclusions": [
            "Inherent vice and ordinary leakage",
            "Insufficient packing unless endorsed",
            "Unattended-vehicle theft beyond the warranty",
            "Pollution and war risks unless endorsed",
        ],
        "endorsements": ["Broadened named perils", "Refrigeration breakdown", "Warehouse legal liability", "Driver security warranty"],
        "limits": ["Per-load and per-conveyance limits", "Deductible by commodity"],
        "rating": ["Commodity type and value", "Radius and route", "Security and unattended-vehicle controls"],
        "refer": ["High-value electronics/pharma loads", "Any unrecovered in-transit theft"],
    },
    "commercial/garage_liability": {
        "market": "Auto dealers, service/repair shops, and parking operations.",
        "exclusions": ["Customer property beyond the garagekeeper's legal liability (separate forms)", "Defective workmanship", "Racing"],
        "endorsements": ["Garagekeepers", "Dealers' drive-away", "Loaner/rental vehicles", "Auto inventory physical damage"],
        "limits": ["CSL by garagekeeper exposure", "Garagekeepers legal liability per customer vehicle"],
        "rating": ["Type of operation and sales volume", "Number of service bays/loaned vehicles", "Loss history"],
        "refer": ["Any fraud/misrepresentation history", "High-value exotic inventory"],
    },
    "commercial/non_trucking_liability": {
        "market": "Owner-operators under lease to a carrier for non-trucking (bobtail) use.",
        "exclusions": ["Any use under the carrier's authority (deadhead under dispatch)", "Owned-trailer liability unless endorsed", "Cargo"],
        "endorsements": ["Trailer interchange", "Non-owned trailer"],
        "limits": ["CSL $1M", "Non-owned trailer sub-limit"],
        "rating": ["Radius and lease terms", "Unit type", "Driver MVR"],
        "refer": ["Ambiguity over when dispatch begins/ends", "Any recent collision"],
    },
    # =====================================================================
    # COMMERCIAL — FINANCIAL
    # =====================================================================
    "commercial/surety_bonds": {
        "market": "Contractors and principals needing contract, performance, or commercial surety bonds.",
        "exclusions": ["Bond terms govern coverage; typically no third-party liability", "Obligations outside the bonded contract"],
        "endorsements": ["Maintenance/guarantee bonds", "Supply bonds", "Subdivision/land-obligation bonds"],
        "limits": ["Bond penalty up to 100% of the contract value", "Aggregate surety program capacity"],
        "rating": ["Principal's balance sheet, working capital, and backlog", "Bond type and obligee", "Indemnity and collateral"],
        "refer": ["Single bond above the surety's single-bond capacity", "Adverse financial trends or unbonded prior defaults"],
    },
    "commercial/political_risk": {
        "market": "Investors with cross-border assets exposed to expropriation, inconvertibility, and political violence.",
        "exclusions": ["War/confiscation unless endorsed", "Ordinary trade credit risk", "Currency devaluation (varies)"],
        "endorsements": ["Currency inconvertibility", "Sabotage/terrorism", "Arbitration award default"],
        "limits": ["Investment value per country and project", "Aggregate by peril"],
        "rating": ["Country risk rating", "Investment type and tenor", "Sanctions and governmental nexus"],
        "refer": ["Sanctioned or high-risk jurisdictions", "Any government-owned counterparty"],
    },
    "commercial/representations_warranties": {
        "market": "Buyers/sellers in M&A seeking breach-of-representation protection.",
        "exclusions": ["Known/pre-existing breach", "Fraud/concealment", "Forward-looking and data-security representations unless scheduled"],
        "endorsements": ["Seller-side policy", "Specific-issue/known-breach buy-back", "Non-recourse structuring"],
        "limits": ["Typically 10% of deal value (5–20% range)", "Retention 0.5–1% of deal value"],
        "rating": ["Deal size and sector", "Diligence quality and reps", "Buyer/seller leverage and retention"],
        "refer": ["Any known breach", "Deals without audited financials"],
    },
    "commercial/legal_expense": {
        "market": "Individuals/businesses insuring the cost of legal defense for covered proceedings.",
        "exclusions": ["Fines and penalties", "Affirmative claims and counterclaims unless endorsed", "Intentional/fraudulent acts"],
        "endorsements": ["Employment proceedings", "Contract disputes", "Identity-theft recovery"],
        "limits": ["Per-claim/aggregate legal-cost limits", "Panel vs free-choice counsel"],
        "rating": ["Exposure type and territory", "Panel vs free choice", "Prior proceedings"],
        "refer": ["Any ongoing proceeding", "Jurisdictions dominated by fee-shifting"],
    },
    # =====================================================================
    # COMMERCIAL — SPECIALTY
    # =====================================================================
    "commercial/tech_eo_cyber": {
        "market": "Technology companies (SaaS, IT services, hardware) needing combined tech E&O and cyber.",
        "exclusions": ["Deliberate refusal or non-performance of an agreed service (not a wrongful act)", "Bodily injury/property damage", "Prior known incidents", "War/state-sponsored attacks"],
        "endorsements": ["Network security (first-party)", "Privacy liability", "Media liability", "Contractual liability"],
        "limits": ["Technology E&O and cyber each with sub-limits", "Claims-made for the E&O section"],
        "rating": ["Revenue and service mix", "Controls and prior incidents", "Contractual exposure and jurisdictions"],
        "refer": ["Regulated data or critical infrastructure", "Any prior breach or system failure claim"],
    },
    "commercial/construction": {
        "market": "General contractors and construction managers, including wrap-up projects.",
        "exclusions": ["Professional/design liability (separate cover)", "Pollution unless endorsed", "Damage to the insured's own work", "Residential construction beyond program limits"],
        "endorsements": ["Additional insured (owners/contractors)", "Waiver of subrogation", "Completed-operations extension", "Wrap-up (OCIP/CCIP)"],
        "limits": ["$1M/$2M per project; higher for wrap-ups", "Per-project aggregates for wrap-ups"],
        "rating": ["Type of work and subcontractor percentage", "Revenue and payroll", "Safety and loss history", "Project size and height"],
        "refer": ["Residential construction above program limits", "Any wrap-up above $50M", "Defect/latent-injury history"],
    },
    "commercial/aviation": {
        "market": "Owners/operators of aircraft — hull and liability, private and commercial.",
        "eligible": ["Current airworthiness certificate and crew certification", "Pilot experience within open-pilot requirements"],
        "exclusions": ["War/hijacking unless endorsed", "Wear, tear, and gradual deterioration", "Use outside the declared purpose"],
        "endorsements": ["Non-owned aircraft", "Premises liability", "Search-and-rescue", "Hangarkeepers"],
        "limits": ["Hull on agreed value", "Liability CSL per occurrence", "Passenger sub-limits"],
        "rating": ["Aircraft make/model/value", "Crew experience and hours", "Use (private, charter, instruction)", "Territory"],
        "refer": ["Any operator without current certification", "Commercial charter use", "Hull value above $10M"],
    },
    "commercial/event_insurance": {
        "market": "Organizers of public events needing cancellation and liability cover.",
        "exclusions": ["Weather unless endorsed", "Change of mind/known circumstances at inception", "War/terrorism unless endorsed"],
        "endorsements": ["Adverse weather", "Non-appearance of performers", "Terrorism", "Public liability"],
        "limits": ["Cancellation up to the budget/revenue at risk", "Liability limits separate"],
        "rating": ["Event type, attendance, and venue", "Duration and lead time", "Cancel/peril endorsements"],
        "refer": ["Attendance above venue capacity", "Events outside permitted venues", "Short lead time"],
    },
    "commercial/intellectual_property": {
        "market": "Companies enforcing or defending IP rights (patents, trademarks, copyrights).",
        "exclusions": ["Known infringement/invalidity before inception", "Intentional infringement", "Fines and penalties"],
        "endorsements": ["Defense-cost-only", "Enforcement (abatement) cover", "Multi-jurisdiction"],
        "limits": ["Per-claim/aggregate with defense sub-limits", "Enforcement expense sub-limit"],
        "rating": ["Portfolio strength and jurisdictions", "Litigation history and freedom-to-operate", "Industry"],
        "refer": ["Any known dispute or opinion of counsel", "NPE/high-litigation sectors"],
    },
    "commercial/kidnap_ransom": {
        "market": "Companies and executives with personal security exposure (travel, high-profile roles).",
        "exclusions": ["War and government-ordered seizure", "Ransom or response expenses not incurred with the insurer's prior consent", "Bodily injury/property damage"],
        "endorsements": ["Crisis-response services", "Extortion/detention", "Evacuation and repatriation"],
        "limits": ["$1M–$10M per occurrence typical", "Consultant and response-cost sub-limits"],
        "rating": ["Travel patterns and jurisdictions", "Industry and profile", "Security controls"],
        "refer": ["High-risk jurisdictions", "Any prior incident or threat"],
    },
    "commercial/terrorism": {
        "market": "Property/BI exposures in TRIA-eligible or high-target locations.",
        "exclusions": ["Nuclear/radiological/biological/chemical unless the free-standing cover responds", "War (non-certified acts)"],
        "endorsements": ["TRIA certified / non-certified", "Standalone terrorism over a property program"],
        "limits": ["Per-occurrence and annual aggregate", "Schedule-wide catastrophe limits"],
        "rating": ["Target attractiveness and occupancy", "Location and concentration", "TRIA program structure"],
        "refer": ["Iconic/trophy-property schedules", "Aggregate exposure above program capacity"],
    },
    "commercial/product_recall": {
        "market": "Food, consumer-goods, and auto-parts manufacturers with recall/withdrawal exposure.",
        "exclusions": ["Fines and penalties", "Intentional/criminal acts", "Loss of market share unless endorsed", "Non-accidental contamination"],
        "endorsements": ["First-party recall costs", "Third-party recall liability", "Rehabilitation expense", "Consultant costs"],
        "limits": ["$5M typical with a 12-month discovery period", "Recall/consultant sub-limits"],
        "rating": ["Product type and distribution", "Quality/food-safety controls", "Recall history"],
        "refer": ["Any prior recall", "Products with catastrophic (botulism/allergen) exposure"],
    },
    "commercial/supply_chain": {
        "market": "Manufacturers/retailers with concentrated supplier or logistics dependencies.",
        "exclusions": ["Loss of market", "Unnamed suppliers unless scheduled", "Financial default of a supplier"],
        "endorsements": ["Named-supplier cover", "Imports/exports disruption", "Contingent BI"],
        "limits": ["Per-supplier and aggregate limits", "Waiting period and indemnity period"],
        "rating": ["Supplier concentration and geography", "Substitutability of inputs", "Indemnity period"],
        "refer": ["Single-supplier dependency above 30%", "Suppliers in high CAT or political-risk zones"],
    },
    "commercial/crop_insurance": {
        "market": "Agricultural producers needing crop/revenue protection for specified crops.",
        "exclusions": ["Non-notified crops/areas", "Malicious damage by the insured", "War/nuclear"],
        "endorsements": ["Revenue/whole-farm option", "Prevented planting"],
        "limits": ["Coverage level (50–85%) × approved yield × price", "Per-crop limits"],
        "rating": ["Crop, county, and approved yield (APH)", "Coverage level and unit structure", "Producer loss history"],
        "refer": ["New producers without APH history", "High-loss units"],
    },
    "commercial/livestock_bloodstock": {
        "market": "Owners of livestock and bloodstock (horses, cattle) with mortality exposure.",
        "exclusions": ["Theft without a police report", "Intentional slaughter", "Conditions not disclosed at inception"],
        "endorsements": ["Prospective foal", "Surgical/procedural extension", "Herd cover"],
        "limits": ["Agreed value per animal", "Herd aggregate limits"],
        "rating": ["Species, breed, age, and value", "Health/veterinary report", "Use (racing, breeding, commercial)"],
        "refer": ["High-value bloodstock above $1M", "Pre-existing/performance-affecting conditions"],
    },
    # =====================================================================
    # COMMERCIAL — PACKAGE
    # =====================================================================
    "commercial/cpp": {
        "market": "Mid-market accounts needing property and liability combined with line-specific forms under one policy.",
        "exclusions": ["Property and CGL exclusions apply line by line", "Professional liability (separate)", "Auto and WC (separate forms)"],
        "endorsements": ["Hired/Non-Owned Auto", "Business Income", "Equipment Breakdown", "Employee Dishonesty", "Spoilage"],
        "limits": ["Structured by coverage; higher than BOP", "CGL $1M/$2M with per-line sub-limits"],
        "rating": ["Loss cost × exposure by coverage", "Package credit", "Territory and protection class"],
        "refer": ["Values above CPP program capacity", "Any manuscript coverage", "Mixed habitational exposure"],
    },
    # =====================================================================
    # COMMERCIAL — ALTERNATIVE RISK
    # =====================================================================
    "commercial/captive_insurance": {
        "market": "Mid-to-large organizations forming a captive insurer or protected cell to retain and finance their own risk.",
        "eligible": [
            "Captive feasibility study and actuarial funding in place",
            "Board-approved risk-retention policy and domicile selection",
        ],
        "exclusions": [
            "Risks outside the captive's approved business plan",
            "Losses exceeding the captive's policy limits and aggregate",
            "Punitive or exemplary damages where uninsurable",
        ],
        "limits": [
            "Retention funded to the actuarial loss picks",
            "Fronted admitted limits of $1M–$5M over the captive",
            "Aggregate stop-loss attachment per the funding study",
        ],
        "rating": [
            "Captive domicile and regulatory capital requirements",
            "Actuarial loss picks and funding adequacy",
            "Fronting fee and collateral structure",
        ],
        "refer": [
            "Any new captive domicile to the program",
            "Funding below the actuarial central estimate",
        ],
    },
    "commercial/sir_fronting": {
        "market": "Insureds using a large self-insured retention with admitted fronting paper for certificates and regulatory compliance.",
        "eligible": [
            "Demonstrated financial capacity for the retained layer",
            "Fronting carrier with A-rated admitted paper and collateral",
        ],
        "exclusions": [
            "Losses within the self-insured retention (retained by the insured)",
            "Risks outside the fronted coverage grant",
            "Punitive or exemplary damages where uninsurable",
        ],
        "limits": [
            "SIR $100K–$5M per occurrence, aggregate where specified",
            "Fronted admitted policy limits typically $1M–$5M",
            "Collateral equal to a multiple of the retained layer",
        ],
        "rating": [
            "Size and funding of the self-insured retention",
            "Loss-pick assumptions and collateral (LOC/trust)",
            "Fronting fee (typically 5–10% of SG&A)",
        ],
        "refer": [
            "SIR above $1M without actuarial sign-off",
            "Insufficient collateral for the retained layer",
        ],
    },
    # =====================================================================
    # LIFE — TERM VARIANTS
    # =====================================================================
    "life/decreasing_term": {
        "market": "Coverage matched to a declining balance — mortgages, loans, and amortizing debt.",
        "exclusions": ["Suicide within two years", "Material misrepresentation", "Misstatement of the debt balance or amortization schedule"],
        "endorsements": ["Return of Premium", "Waiver of Premium", "Disability Income"],
        "limits": ["Face declines on a schedule matching the amortization of the debt", "Non-convertible"],
        "rating": ["Age/sex/tobacco and health class", "Schedule of decrease and term", "Mortgage/loan nexus"],
        "refer": ["Face above the documented debt balance", "Table 3+ or multiple impairments"],
    },
    "life/mortgage_life": {
        "market": "Borrowers using term cover that tracks a mortgage balance (often creditor-arranged).",
        "exclusions": ["Suicide within two years", "Misrepresentation", "Misstatement of the mortgage balance, term, or borrower details"],
        "endorsements": ["Waiver of premium (disability)", "Return of premium"],
        "limits": ["Face tracks the reducing mortgage balance", "Non-convertible"],
        "rating": ["Age/sex/tobacco", "Mortgage term and original balance", "Simplified vs full underwriting"],
        "refer": ["Simplified-issue amounts above the limit", "Adverse health disclosure"],
    },
    "life/increasing_term": {
        "market": "Coverage stepped to hedge inflation or rising liabilities.",
        "exclusions": ["Suicide within two years", "Misrepresentation", "Scheduled increases not exercised within the option window"],
        "endorsements": ["Cost-of-living increase option", "Waiver of premium"],
        "limits": ["Face increases on a defined schedule (e.g., 3–5%/yr)", "Non-convertible"],
        "rating": ["Age/sex/tobacco", "Increase schedule and cap", "Term"],
        "refer": ["Large scheduled increases without underwriting", "Table ratings"],
    },
    "life/renewable_term": {
        "market": "Short-term cover with guaranteed renewability without new evidence.",
        "exclusions": ["Suicide within two years", "Misrepresentation", "Renewal beyond the guaranteed renewable age"],
        "endorsements": ["Convertibility option", "Waiver of premium"],
        "limits": ["Renewable to age 80–95 at increasing premiums", "May offer a conversion window"],
        "rating": ["Age/sex/tobacco", "Renewal structure and premium schedule", "Term"],
        "refer": ["Renewal-rate shock for older issue ages", "Table ratings"],
    },
    "life/convertible_term": {
        "market": "Term buyers wanting the option to convert to permanent without new evidence.",
        "exclusions": ["Suicide within two years", "Misrepresentation", "Conversion requested outside the conversion window or to an ineligible plan"],
        "endorsements": ["Conversion to permanent (attained or original age)", "Waiver of premium"],
        "limits": ["Conversion window and target permanent products", "No new medical evidence if exercised in time"],
        "rating": ["Age/sex/tobacco", "Conversion window and products", "Term"],
        "refer": ["Exercised conversion near the window end", "Table ratings"],
    },
    "life/rop_term": {
        "market": "Buyers who want premiums returned if the term expires without a claim.",
        "exclusions": ["Suicide within two years", "Misrepresentation", "Return of premium forfeited on surrender before the end of the term"],
        "endorsements": ["Return of Premium at term end", "Waiver of premium"],
        "limits": ["ROP typically 100% of premiums if no claim to term", "Premium higher than level term"],
        "rating": ["Age/sex/tobacco", "ROP percentage and term", "Funded vs non-funded ROP"],
        "refer": ["Non-funded ROP with aggressive illustrations", "Table ratings"],
    },
    "life/group_term_life": {
        "market": "Employers/programs providing group term life without individual medical underwriting.",
        "exclusions": ["Suicide within two years (varies)", "Active-at-work requirement"],
        "endorsements": ["AD&D", "Dependent life", "Portability/convertibility"],
        "limits": ["Flat or multiple-of-salary schedule", "Guaranteed-issue limit; EOI above"],
        "rating": ["Census age/gender", "Benefit schedule and participation", "Industry"],
        "refer": ["Adverse census mortality", "Benefit above the GI limit"],
    },
    "life/credit_life": {
        "market": "Creditors providing life/disability cover tied to a loan balance.",
        "exclusions": ["Suicide within two years", "Misrepresentation", "Pre-existing conditions within the initial period"],
        "endorsements": ["Disability cover", "Joint credit life"],
        "limits": ["Face tracks the outstanding loan balance", "Usually simplified/deemed issue"],
        "rating": ["Loan type and average balance", "Simplified underwriting", "Portfolio loss experience"],
        "refer": ["Adverse portfolio mortality", "High average balances"],
    },
    # =====================================================================
    # LIFE — WHOLE LIFE VARIANTS
    # =====================================================================
    "life/limited_pay_whole_life": {
        "market": "Permanent cover funded over a fixed period (10/20-pay) for estate and legacy needs.",
        "exclusions": ["Suicide and contestability for two years", "Material misrepresentation", "Non-payment of a scheduled limited-pay premium"],
        "endorsements": ["Paid-Up Additions (PUA)", "Waiver of Premium", "Accelerated Death Benefit"],
        "limits": ["Premiums paid over 10/20 years; coverage for life", "Funding verified for higher premiums"],
        "rating": ["Issue age/sex/tobacco", "Pay period and face band", "Dividend option (par)"],
        "refer": ["Premium above $100K/yr", "Complex ownership (ILIT/trust)"],
    },
    "life/single_premium_whole_life": {
        "market": "Single-deposit permanent cover for estate liquidity and legacy planning.",
        "exclusions": ["Suicide and contestability for two years", "Material misrepresentation", "Single premium must not create MEC status"],
        "limits": ["Single premium avoids MEC; face set by funding", "Source-of-funds review required"],
        "rating": ["Issue age/sex/tobacco", "Single-premium amount and face", "MEC testing"],
        "refer": ["Single premium above $1M", "Foreign national/nexus", "Complex ownership"],
    },
    "life/participating_whole_life": {
        "market": "Permanent cover from a mutual-style insurer paying dividends.",
        "exclusions": ["Suicide and contestability for two years", "Material misrepresentation", "Dividends are not guaranteed and may be reduced"],
        "endorsements": ["Paid-Up Additions (PUA)", "Guaranteed Insurability", "Dividend option election"],
        "limits": ["Face plus PUAs; dividends not guaranteed", "Illustrations must reflect current scale"],
        "rating": ["Issue age/sex/tobacco", "Dividend option and current scale", "Financial strength of the insurer"],
        "refer": ["Aggressive dividend illustrations", "Large PUA funding"],
    },
    "life/non_participating_whole_life": {
        "market": "Permanent cover with guaranteed premiums and values, no dividends.",
        "exclusions": ["Suicide and contestability for two years", "Material misrepresentation", "Guaranteed values only; no dividend participation"],
        "endorsements": ["Paid-Up Additions where offered", "Waiver of Premium", "Term rider"],
        "limits": ["Guaranteed face and cash values", "No dividends"],
        "rating": ["Issue age/sex/tobacco", "Face band and payment mode", "Guaranteed values"],
        "refer": ["Large face without financial justification", "Table ratings"],
    },
    "life/modified_whole_life": {
        "market": "Permanent cover with reduced early premiums (step-rated).",
        "exclusions": ["Suicide and contestability for two years", "Material misrepresentation", "Non-payment of the stepped premium after the initial period"],
        "endorsements": ["Waiver of Premium", "Accelerated Death Benefit"],
        "limits": ["Lower premium in years 1–N, then step up", "Face level throughout"],
        "rating": ["Issue age/sex/tobacco", "Step-premium schedule", "Face band"],
        "refer": ["Premium-step shock for affordability", "Table ratings"],
    },
    "life/graded_guaranteed_issue_whole_life": {
        "market": "Simplified/guaranteed-issue permanent cover for ages 50–85 with health impairments.",
        "eligible": ["Guaranteed issue within stated age/amount bands", "No medical exam; health questions only (or none)"],
        "exclusions": ["Graded death benefit in years 1–2 (return of premium + interest)", "Material misrepresentation"],
        "limits": ["Face capped per GI band (e.g., $25K)", "Graded benefit schedule at issue"],
        "rating": ["Issue age and GI band", "State GI rules", "Face amount"],
        "refer": ["Face above the GI cap", "Residency/age outside the program"],
    },
    # =====================================================================
    # LIFE — UNIVERSAL LIFE VARIANTS
    # =====================================================================
    "life/indexed_universal_life": {
        "market": "Permanent cover with cash value credited by an equity index, with a floor.",
        "exclusions": ["Index losses (floor protects, cap limits upside)", "Suicide/contestability"],
        "endorsements": ["No-lapse guarantee", "Indexed strategy options (caps/participation/floor)", "Overloan protection"],
        "limits": ["Caps 9–12%, participation rates, and a 0% floor", "Target premium vs minimum premium"],
        "rating": ["Health class", "Funding level and lapse risk", "Index strategy and charges"],
        "refer": ["Target above 3% of account value", "Single/limited funding", "Aggressive loan usage"],
    },
    "life/variable_universal_life": {
        "market": "Permanent cover with separate-account (market) cash value.",
        "eligible": ["Registered representative and suitability review", "Prospectus delivered"],
        "exclusions": ["Investment losses borne by the owner", "Suicide/contestability"],
        "endorsements": ["Guaranteed minimum death benefit", "ROP rider", "Automatic rebalancing"],
        "limits": ["Premium loads, COI, and fund fees per the prospectus", "Minimum premium to keep in force"],
        "rating": ["Mortality per class and subaccount fees", "Suitability of the allocation", "Funding level"],
        "refer": ["Aggressive or concentrated allocations", "Non-registered solicitation", "Churning"],
    },
    "life/current_assumption_universal_life": {
        "market": "Flexible permanent cover credited at a current (non-guaranteed) interest rate.",
        "exclusions": ["Credited rate may decline to the guaranteed minimum", "Suicide/contestability"],
        "endorsements": ["No-lapse guarantee", "Overloan protection", "Waiver of Monthly Deductions"],
        "limits": ["Current vs guaranteed crediting rate", "Minimum premium and no-lapse guarantee period"],
        "rating": ["Health class", "Funding and assumed rate", "Policy charges"],
        "refer": ["Minimum-funded GUL-like designs", "Loans above 90% of account value"],
    },
    # =====================================================================
    # LIFE — ENDOWMENT
    # =====================================================================
    "life/full_endowment": {
        "market": "Savings plans maturing for a lump sum at a fixed term (with-profit variant).",
        "exclusions": ["Suicide and contestability", "Surrender-charge schedules", "Non-payment of scheduled premiums forfeits the maturity guarantee"],
        "endorsements": ["Paid-up additions", "Surrender-value guarantees"],
        "limits": ["Maturity value at a defined term", "Reversionary/terminal bonuses (par)"],
        "rating": ["Sex/age/tobacco mortality", "Guaranteed interest and bonus scale", "Payment term"],
        "refer": ["Non-standard bonus illustrations", "Jumbo funding"],
    },
    "life/guaranteed_fixed_endowment": {
        "market": "Guaranteed maturity value at a fixed term, with no bonus discretion.",
        "exclusions": ["Suicide and contestability", "Surrender-charge schedules", "Guaranteed maturity only if all scheduled premiums are paid"],
        "endorsements": ["Surrender-value guarantees"],
        "limits": ["Guaranteed maturity value per the schedule", "Fixed surrender table"],
        "rating": ["Mortality and guaranteed interest assumption", "Payment term and frequency"],
        "refer": ["Non-standard structures", "Large single funding"],
    },
    # =====================================================================
    # LIFE — ULIP / VUL VARIANTS
    # =====================================================================
    "life/regular_premium_ulip": {
        "market": "Regular-premium market-linked life (US-equivalent VUL) for long-term savings.",
        "eligible": ["Registered representative and suitability", "Prospectus delivered"],
        "exclusions": ["Investment losses borne by the owner", "Suicide/contestability", "Fund-switch limits and premium-redirection restrictions"],
        "endorsements": ["ROP rider", "Pension/retirement rider", "Guaranteed minimum death benefit"],
        "limits": ["Premium load, COI, and fund fees per prospectus", "Minimum premium to keep in force"],
        "rating": ["Mortality per class and fund fees", "Allocation suitability", "Charges"],
        "refer": ["Aggressive allocations", "High front-end loads", "Non-resident aliens"],
    },
    "life/ulip_type_i": {
        "market": "Market-linked cover where the death benefit is the higher of sum assured or fund value.",
        "exclusions": ["Investment losses borne by the owner", "Suicide/contestability", "No death-benefit floor beyond the higher-of guarantee"],
        "endorsements": ["ROP rider", "Pension rider"],
        "limits": ["Death benefit = higher of sum assured or fund value", "Fund-management charges"],
        "rating": ["Mortality and fund-management charges", "Allocation suitability", "Sum-assured vs fund-value design"],
        "refer": ["Aggressive allocations", "Churning"],
    },
    "life/ulip_type_ii": {
        "market": "Market-linked cover where the death benefit is sum assured plus fund value.",
        "exclusions": ["Investment losses borne by the owner", "Suicide/contestability", "Higher COI erodes fund value in adverse markets"],
        "endorsements": ["ROP rider", "Pension rider"],
        "limits": ["Death benefit = sum assured plus fund value", "Higher COI relative to Type I"],
        "rating": ["Higher cost-of-insurance relative to Type I", "Allocation suitability", "Sum-assured plus fund-value design"],
        "refer": ["Aggressive allocations", "Long-duration underfunding"],
    },
    "life/pension_ulip": {
        "market": "Retirement-oriented market-linked cover with an annuity/withdrawal phase.",
        "exclusions": ["Investment losses borne by the owner", "Early-withdrawal restrictions"],
        "endorsements": ["Retirement phase (annuitization)", "Guaranteed withdrawal"],
        "limits": ["Qualified/non-qualified contribution limits", "Lock-in and withdrawal rules"],
        "rating": ["Mortality and charges", "Allocation and annuity factors"],
        "refer": ["Suitability for near-retirees", "Aggressive allocations near the lock-in"],
    },
    "life/child_ulip": {
        "market": "Market-linked cover/savings funding a child's future education or milestones.",
        "exclusions": ["Investment losses borne by the owner", "Suicide/contestability", "Payout restricted to the defined milestones; limited early liquidity"],
        "endorsements": ["Waiver of Premium (payer)", "Milestone payout rider"],
        "limits": ["Fund-value-based payouts at milestones", "Payer waiver on death/disability"],
        "rating": ["Payer mortality and charges", "Allocation and fund fees"],
        "refer": ["Aggressive allocations", "Short horizon vs equity exposure"],
    },
    # =====================================================================
    # LIFE — MONEY-BACK VARIANTS
    # =====================================================================
    "life/with_profit_money_back": {
        "market": "Savings cover returning premiums at intervals with profit participation.",
        "exclusions": ["Surrender penalties", "Suicide/contestability", "Survival benefits forfeited if the policy lapses before the scheduled payout"],
        "endorsements": ["Paid-up additions", "Survival-benefit schedule"],
        "limits": ["Scheduled survival benefits (e.g., 20% of SA every 5 years)", "Maturity value on survival"],
        "rating": ["Mortality and plan term", "Bonus scale", "Premium mode"],
        "refer": ["Non-standard bonus illustrations", "Large face"],
    },
    "life/children_money_back": {
        "market": "Savings/cover for a child's education milestones.",
        "exclusions": ["Surrender penalties", "Suicide/contestability", "Payouts restricted to the defined education milestones"],
        "endorsements": ["Waiver of Premium (payer)", "Milestone payouts"],
        "limits": ["Scheduled milestone payouts", "Maturity on survival to the term"],
        "rating": ["Payer mortality and plan term", "Premium mode"],
        "refer": ["Aggressive bonus illustrations", "Large face for a minor"],
    },
    # =====================================================================
    # LIFE — ANNUITY VARIANTS
    # =====================================================================
    "life/immediate_annuity": {
        "market": "Retirees converting a lump sum into immediate guaranteed income.",
        "exclusions": ["No liquidity after annuitization (irrevocable)", "Market risk (fixed immediate)"],
        "endorsements": ["Life with period certain", "Joint-and-survivor", "Cash refund"],
        "limits": ["Income based on premium, age, and payout option", "No accumulation phase"],
        "rating": ["Age/sex and payout option", "Current annuity factors", "Premium"],
        "refer": ["Suitability for liquidity needs", "Non-qualified vs qualified treatment"],
    },
    "life/deferred_annuity": {
        "market": "Long-horizon retirement accumulation with tax deferral.",
        "exclusions": ["Surrender charges", "Market risk (variable/indexed)"],
        "endorsements": ["GLWB", "GMIB", "Death-benefit rider"],
        "limits": ["Accumulation then income election", "Surrender schedule"],
        "rating": ["Current crediting/index strategy", "Rider charges", "Surrender schedule"],
        "refer": ["Suitability for near-retirees", "Aggressive riders with high costs"],
    },
    "life/fixed_annuity": {
        "market": "Guaranteed-rate accumulation/income with no market exposure.",
        "exclusions": ["Surrender charges; opportunity cost vs equities", "No inflation adjustment unless rider"],
        "endorsements": ["Market-value adjustment", "GLWB"],
        "limits": ["Guaranteed minimum rate and current rate", "Surrender schedule"],
        "rating": ["Guaranteed vs current crediting rate", "Term and surrender charges", "Insurer credit"],
        "refer": ["Long surrender periods vs liquidity need", "Carrier credit concerns"],
    },
    "life/variable_annuity": {
        "market": "Market-linked accumulation/income held in separate accounts.",
        "eligible": ["Registered representative and suitability; prospectus delivered"],
        "exclusions": ["Investment losses borne by the owner", "Surrender charges"],
        "endorsements": ["GLWB", "GMIB", "Death-benefit rider under separate accounts"],
        "limits": ["Fee layers per prospectus (M&E, fund, rider)", "Allocation limits by age"],
        "rating": ["Subaccount fees and mortality/expense charges", "Rider cost", "Allocation suitability"],
        "refer": ["Aggressive allocations near retirement", "Non-registered solicitation"],
    },
    "life/indexed_annuity": {
        "market": "Accumulation/income with index-linked crediting and a floor.",
        "exclusions": ["Cap/participation limit upside", "Surrender charges"],
        "endorsements": ["GLWB", "Index strategy options"],
        "limits": ["Caps, participation rates, and a 0% floor", "Surrender schedule"],
        "rating": ["Index strategy, caps, and floor", "Rider charges", "Surrender schedule"],
        "refer": ["Complex rider stacking", "Suitability for shorter horizons"],
    },
    "life/life_annuity": {
        "market": "Life-contingent income (straight life or with guarantees).",
        "exclusions": ["No payments after death (straight life)", "Limited liquidity"],
        "endorsements": ["Period certain", "Cash refund", "Joint-and-survivor"],
        "limits": ["Income for life based on age/sex and option", "Higher payout than period-certain"],
        "rating": ["Age/sex and payout option", "Annuity factors", "Premium"],
        "refer": ["Applicant with impaired longevity", "Estate/beneficiary objectives"],
    },
    "life/joint_survivor_annuity": {
        "market": "Couples wanting income continuing until the second death (estate planning).",
        "exclusions": ["Reduced payout vs single life", "Limited liquidity"],
        "endorsements": ["Period certain", "Reduced survivor percentage"],
        "limits": ["Income to the last survivor", "Survivor percentage options"],
        "rating": ["Both lives' ages and health", "Survivor percentage", "Premium"],
        "refer": ["Second-to-die estate planning without an ILIT", "Large premium"],
    },
    "life/qlac": {
        "market": "Qualified Longevity Annuity Contracts deferring IRA income to a later age.",
        "eligible": ["IRA/qualified funds within the IRS dollar limit", "Deferral to age 80–85"],
        "exclusions": ["Limited liquidity; RMD relief only", "No cash value (varies)"],
        "endorsements": ["Death benefit (return of premium)", "Cost-of-living adjustment"],
        "limits": ["Premium capped at the IRS QLAC limit", "Income begins at the elected age"],
        "rating": ["Deferral age and current factors", "Death-benefit option", "Premium"],
        "refer": ["Funding above the IRS limit", "Suitability vs other retirement assets"],
    },
    "life/structured_settlement_annuity": {
        "market": "Periodic payments funding a court-approved settlement.",
        "eligible": ["Court-approved settlement documents", "Defined periodic-payment schedule"],
        "exclusions": ["Non-transferable/restricted commutation", "Terms fixed by the settlement"],
        "endorsements": ["Cost-of-living adjustment", "Guaranteed period"],
        "limits": ["Payments per the settlement schedule", "Optional COLA"],
        "rating": ["Settlement schedule and factors", "Guarantee period", "Carrier credit"],
        "refer": ["Any factoring/transfer request", "Settlement without court documents"],
    },
    # =====================================================================
    # HEALTH — INDIVIDUAL VARIANTS
    # =====================================================================
    "health/off_exchange_major_medical": {
        "market": "ACA-compliant major medical sold off-exchange (no premium tax credit).",
        "exclusions": ["No PTC subsidy; still no health-status underwriting", "Non-EHB and out-of-network care except emergencies"],
        "limits": ["ACA out-of-pocket maximum; no annual/lifetime caps", "Metal-tier deductibles"],
        "rating": ["Age curve, family composition, tobacco", "Rating area", "No APTC subsidy"],
        "refer": ["Household expecting APTC", "Multi-state coverage needs"],
    },
    "health/short_term_limited_duration": {
        "market": "Short-duration, non-ACA major medical for coverage gaps.",
        "eligible": ["Health-questionnaire underwriting", "Duration within state limits (often < 3–12 months)"],
        "exclusions": ["Pre-existing conditions excluded (not ACA-compliant)", "No EHB guarantee; limited benefits", "Maternity and mental health often excluded"],
        "limits": ["Fixed benefit maximum and duration", "No guaranteed renewability"],
        "rating": ["Health questionnaire and age", "State duration rules", "Benefit design"],
        "refer": ["Any pre-existing condition", "Applicant needing ACA-compliant coverage"],
    },
    "health/hdhp_hsa_qualified": {
        "market": "High-deductible health plans paired with an HSA.",
        "exclusions": ["No coverage until the IRS minimum deductible is met", "First-dollar benefits limited by HSA rules"],
        "limits": ["IRSH-defined minimum deductible and maximum OOP", "HSA contribution limits"],
        "rating": ["Age curve and tobacco", "Rating area", "HSA contribution eligibility"],
        "refer": ["Applicant covered by a non-HDHP", "Disqualifying coverage for HSA"],
    },
    "health/catastrophic_plan": {
        "market": "ACA catastrophic plans for eligible individuals (under 30 or hardship exemption).",
        "eligible": ["Under age 30 or with a hardship exemption"],
        "exclusions": ["Limited to catastrophic-cost protection", "3 primary-care visits before the deductible"],
        "limits": ["ACA out-of-pocket maximum; high deductible", "No premium tax credit"],
        "rating": ["Age and eligibility for the plan", "Rating area"],
        "refer": ["Applicant over 30 without an exemption", "Needs pre-deductible coverage"],
    },
    # =====================================================================
    # HEALTH — FAMILY VARIANTS
    # =====================================================================
    "health/family_hdhp_hsa_qualified": {
        "market": "Family high-deductible plan with a family HSA.",
        "exclusions": ["No coverage until the family deductible is met", "HSA rules limit first-dollar benefits"],
        "limits": ["Family IRS minimum deductible and maximum OOP", "Family HSA contribution limit"],
        "rating": ["Ages and tobacco of members", "Rating area", "Family HSA eligibility"],
        "refer": ["Members with disqualifying coverage", "Mixed HSA eligibility"],
    },
    "health/family_extended_dependents": {
        "market": "Family plans covering extended dependents (adult/disabled children).",
        "eligible": ["Dependents meeting ACA/plan dependency rules", "Disability documentation where applicable"],
        "exclusions": ["Dependents not meeting tax/dependency rules", "Coverage to age limits where not disabled"],
        "limits": ["Family aggregate deductible and OOP", "Dependent-age limits"],
        "rating": ["Ages of all covered members", "Rating area", "Dependency documentation"],
        "refer": ["Disabled adult dependents without documentation", "Dependents across state lines"],
    },
    # =====================================================================
    # HEALTH — CRITICAL ILLNESS VARIANTS
    # =====================================================================
    "health/disease_specific_critical_illness": {
        "market": "Lump-sum cover for a single disease (cancer, cardiac, diabetes/kidney).",
        "exclusions": ["Pre-existing condition waiting period", "Self-inflicted injury; war", "Benign/early-stage variants where defined"],
        "limits": ["Benefit per the covered disease", "Early-stage multiple (e.g., 25%)"],
        "rating": ["Age/tobacco and family history of the disease", "Benefit amount", "Occupation class"],
        "refer": ["Any history of the covered disease", "High-risk occupation"],
    },
    "health/critical_illness_rider": {
        "market": "Critical-illness acceleration attached to a life or health base policy.",
        "exclusions": ["Pre-existing waiting period", "Benefits reduce the base sum assured"],
        "limits": ["Rider benefit (e.g., 25–100% of the base)", "Single trigger only unless staged"],
        "rating": ["Base policy class and rider amount", "Age and tobacco"],
        "refer": ["Rider above the base policy limits", "Multiple riders stacking CI exposure"],
    },
    "health/critical_illness_multistage": {
        "market": "Multi-stage critical illness paying at early and advanced stages.",
        "exclusions": ["Pre-existing waiting period", "Self-inflicted; war", "Conditions diagnosed in the first 90–180 days"],
        "limits": ["Early-stage multiple (e.g., 25%) then advanced stage adds a further multiple", "Aggregate cap"],
        "rating": ["Age/tobacco and family history", "Benefit amount and number of stages", "Occupation"],
        "refer": ["History of a covered condition", "Multiple prior claims"],
    },
    # =====================================================================
    # HEALTH — SENIOR VARIANTS
    # =====================================================================
    "health/medicare_advantage": {
        "market": "Medicare Part C — privatized Medicare benefits (HMO/PPO).",
        "eligible": ["Enrolled in Medicare Part A and B", "Lives in the plan service area"],
        "exclusions": ["No coverage outside the network except emergencies/urgent care", "No underwriting (annual election)"],
        "endorsements": ["SNP care coordination (if applicable)", "Rx (Part D) integration"],
        "limits": ["In-network/combined maximum out-of-pocket per CMS", "Annual enrollment windows"],
        "rating": ["County service area", "Plan design", "CMS star ratings"],
        "refer": ["Dual-eligible (route to SNP)", "ESRD (limited plans)"],
    },
    "health/medigap_high_deductible_plan_g": {
        "market": "Medigap Plan G with a high deductible.",
        "exclusions": ["No coverage until the high deductible is met", "No benefits beyond Medicare-covered items"],
        "limits": ["Annual high deductible per CMS", "Plan G benefit schedule after the deductible"],
        "rating": ["Issue-age vs attained-age rating", "County and household discounts", "Guaranteed-issue eligibility"],
        "refer": ["Underwriting outside OE/GI", "Applicant with ESRD"],
    },
    "health/medicare_advantage_snp": {
        "market": "Special Needs Plans for dual-eligible, chronic, or institutional members.",
        "eligible": ["Meets SNP category (dual-eligible, chronic condition, institutional)"],
        "exclusions": ["Limited to the SNP target population", "Network and service-area restrictions"],
        "endorsements": ["Care coordination", "Dual-eligible (D-SNP) integration"],
        "limits": ["MOOP per CMS; coordination with Medicaid", "Enrollment windows"],
        "rating": ["County service area", "SNP category", "CMS rules"],
        "refer": ["Members not meeting SNP eligibility", "Out-of-area members"],
    },
    "health/medicare_part_d": {
        "market": "Standalone Medicare prescription-drug coverage.",
        "eligible": ["Medicare-eligible and enrolled in Part A or B"],
        "exclusions": ["Non-formulary drugs unless excepted", "No medical coverage (Rx only)"],
        "endorsements": ["Formulary tiers", "Coverage gap discount"],
        "limits": ["Annual deductible, initial coverage, coverage gap, catastrophic threshold per CMS"],
        "rating": ["Region", "Formulary and tier structure", "CMS parameters"],
        "refer": ["Members needing drug exceptions", "Low-income-subsidy coordination"],
    },
    # =====================================================================
    # HEALTH — GROUP VARIANTS
    # =====================================================================
    "health/large_group_health": {
        "market": "ERISA large-group plans (51+) fully insured or self-funded.",
        "exclusions": ["Self-funded: stop-loss terms define exclusions", "No health-status underwriting within the group"],
        "endorsements": ["Self-funded stop-loss (specific/aggregate)", "Dental/vision/life/disability"],
        "limits": ["Aggregate and specific stop-loss attachment points", "ACA EHB/OOP caps"],
        "rating": ["Experience rating", "Demographics and industry", "Region and participation"],
        "refer": ["Self-funded without stop-loss", "Multi-employer/union trusts"],
    },
    "health/association_health_plan": {
        "market": "Group health offered through a bona fide association of employers/members.",
        "eligible": ["Bona fide association meeting DOL/ACA tests", "Minimum participation"],
        "exclusions": ["Non-bona-fide association arrangements (MEWA concerns)", "No health-status underwriting within the group"],
        "endorsements": ["Dental/vision", "Stop-loss (self-funded)"],
        "limits": ["Group plan limits and stop-loss attachment", "ACA EHB/OOP caps"],
        "rating": ["Association size and participation", "Demographics", "Region"],
        "refer": ["Association formed primarily to sell insurance", "Low participation"],
    },
    "health/public_sector_group_health": {
        "market": "Government/municipal employer group health plans.",
        "exclusions": ["No health-status underwriting within the group", "Plan-specific exclusions per the state plan"],
        "endorsements": ["Retiree coverage", "Dental/vision", "Stop-loss (self-funded)"],
        "limits": ["Plan limits and stop-loss attachment", "ACA EHB/OOP caps"],
        "rating": ["Census and participation", "Region", "Plan richness"],
        "refer": ["Public-safety retiree liabilities", "Self-funded without stop-loss"],
    },
    "health/level_funded_group_health": {
        "market": "Self-funded group health using level-funded premiums.",
        "exclusions": ["Stop-loss terms define exclusions", "No health-status underwriting within the group"],
        "endorsements": ["Specific/aggregate stop-loss", "Renewal refund/credit"],
        "limits": ["Monthly level premium and stop-loss attachment", "ACA EHB/OOP caps"],
        "rating": ["Census and prior claims", "Industry and region", "Participation"],
        "refer": ["Adverse claims experience", "Low participation", "Renewal shock"],
    },
    # =====================================================================
    # HEALTH — TOP-UP / GAP
    # =====================================================================
    "health/hospital_indemnity": {
        "market": "Fixed cash benefit for hospital admissions/stays.",
        "exclusions": ["Pre-existing condition period", "Self-inflicted injury; war", "No coordination beyond fixed benefits"],
        "limits": ["Fixed per-day or per-admission benefit", "Annual maximum days/benefit"],
        "rating": ["Age and benefit level", "Family tier", "Occupation"],
        "refer": ["Any recent hospitalization", "Benefit stacking across policies"],
    },
    # =====================================================================
    # HEALTH — ACCIDENT
    # =====================================================================
    "health/standalone_add": {
        "market": "Standalone Accidental Death & Dismemberment cover.",
        "exclusions": ["Suicide/self-inflicted", "Disease/illness", "War; flight other than as a common-carrier passenger"],
        "limits": ["Capital sum insured and dismemberment schedule", "No weekly income (that is the AD&D/indemnity product)"],
        "rating": ["Age and occupation class", "Capital sum", "Family vs single"],
        "refer": ["Hazardous occupation class", "Capital sum far above income"],
    },
    # =====================================================================
    # HEALTH — DISABILITY VARIANTS
    # =====================================================================
    "health/long_term_disability": {
        "market": "Long-term disability income with a longer elimination period.",
        "exclusions": ["Pre-existing condition period", "Self-inflicted; war", "Normal pregnancy where excluded"],
        "endorsements": ["Own-occupation definition (2-year)", "Residual/partial", "COLA", "Future increase option"],
        "limits": ["Monthly benefit to 60% of income (integrated)", "Benefit period to SSNRA"],
        "rating": ["Age, income, and occupation class", "Elimination and benefit period", "Rider selections"],
        "refer": ["Benefit above 60% of income", "Own-occ for high-risk occupations", "High-income financial underwriting"],
    },
    "health/disability_ptd": {
        "market": "Lump-sum or income benefit on Permanent Total Disability.",
        "exclusions": ["Pre-existing conditions", "Self-inflicted; war", "Partial disability (not covered)"],
        "limits": ["Defined total of payments or a lump sum", "Strict total-disability definition"],
        "rating": ["Occupation class and age", "Benefit amount and payment structure"],
        "refer": ["Impaired health or hazardous occupation", "Aggressive total-disability definitions"],
    },
    "health/disability_ppd": {
        "market": "Benefit for Permanent Partial Disability (dismemberment/loss of use schedules).",
        "exclusions": ["Pre-existing conditions", "Self-inflicted; war"],
        "limits": ["Scheduled percentages of the capital sum per member", "Aggregate cap"],
        "rating": ["Occupation class and age", "Capital sum and schedule"],
        "refer": ["Any pre-existing impairment", "Hazardous occupation"],
    },
    # =====================================================================
    # GENERAL — MOTOR VARIANTS
    # =====================================================================
    "general/car_tp": {
        "market": "Private-car statutory third-party liability only.",
        "exclusions": ["No own-damage cover (private car, TP only)", "Driving without a valid license; DUI", "Use outside India; war/nuclear"],
        "endorsements": ["Personal accident cover for owner-driver (statutory)"],
        "limits": ["Statutory third-party (unlimited for death/disability; INR 15L property)", "Owner-driver PA per tariff"],
        "rating": ["Vehicle class/cc and zone", "Driver age/experience", "No IDV (no own damage)"],
        "refer": ["Expired RC/DL", "Commercial use under a private policy"],
    },
    "general/tw_tp": {
        "market": "Two-wheeler statutory third-party liability only.",
        "exclusions": ["No own-damage cover (two-wheeler, TP only)", "Driving without a valid license; DUI", "Use outside India; war/nuclear"],
        "endorsements": ["Owner-driver PA cover (statutory)"],
        "limits": ["Statutory third-party limits (two-wheeler)", "Owner-driver PA per tariff"],
        "rating": ["Engine cc and zone", "Driver age and experience"],
        "refer": ["Expired RC/DL", "Use inconsistent with the class"],
    },
    "general/tw_comprehensive": {
        "market": "Two-wheeler own-damage plus third-party cover.",
        "exclusions": ["Driving without a valid license; DUI", "Wear and tear; mechanical/electrical breakdown (two-wheeler)", "Use outside India; war/nuclear"],
        "endorsements": ["Zero Depreciation", "Engine protection", "Roadside assistance", "Helmet cover"],
        "limits": ["IDV on age-based depreciation", "NCB 20–50% on OD premium", "Statutory TP limits"],
        "rating": ["Engine cc, age, IDV, zone", "Driver age/experience and NCB", "Add-ons"],
        "refer": ["Lapsed cover beyond 90 days without inspection", "High-claims/salvage"],
    },
    "general/cv_tp": {
        "market": "Commercial-vehicle statutory third-party liability only.",
        "exclusions": ["No own-damage cover (commercial vehicle, TP only)", "Driving without a valid license; DUI", "Use outside India; war/nuclear"],
        "endorsements": ["Owner-driver PA cover"],
        "limits": ["Statutory third-party limits (commercial vehicle)", "Owner-driver PA per tariff"],
        "rating": ["GVW/passenger class and zone", "Driver/crew records"],
        "refer": ["Expired fitness/RC/permit", "Overloading or prohibited use"],
    },
    "general/cv_comprehensive": {
        "market": "Commercial-vehicle own-damage plus third-party cover.",
        "exclusions": ["Driving without a valid license; DUI", "Wear and tear; mechanical/electrical breakdown (commercial vehicle)", "Use outside India; war/nuclear"],
        "endorsements": ["Zero Depreciation", "Engine protection", "Roadside assistance", "Consumables"],
        "limits": ["IDV on age-based depreciation", "NCB on OD premium", "Statutory TP limits"],
        "rating": ["GVW/passenger class, age, IDV, zone", "Driver/crew records and NCB", "Add-ons"],
        "refer": ["Lapsed cover without inspection", "Heavy-claims or salvage history"],
    },
    # =====================================================================
    # GENERAL — HOME VARIANTS
    # =====================================================================
    "general/home_structure": {
        "market": "Residential building structure-only cover for owners.",
        "exclusions": ["No contents cover (structure only)", "War/nuclear; wear and tear; inherent defect", "Flood/EQ unless selected"],
        "endorsements": ["Terrorism", "Flood/EQ add-ons", "Alternative accommodation"],
        "limits": ["Sum insured = reconstruction cost", "80% average clause applies"],
        "rating": ["Construction, age, zone, sum insured", "Loss experience"],
        "refer": ["High-value premises", "Coastal/EQ zones; heritage structures"],
    },
    "general/home_contents": {
        "market": "Residential contents-only cover for owners/tenants.",
        "exclusions": ["No structure cover (contents only)", "War/nuclear; wear and tear", "Flood/EQ unless selected"],
        "endorsements": ["Specified valuable articles", "Flood/EQ add-ons", "Terrorism"],
        "limits": ["Sum insured = contents value", "Sub-limits for valuables/electronics"],
        "rating": ["Contents value and category", "Zone", "Loss experience"],
        "refer": ["High-value contents/valuables", "Coastal/EQ zones"],
    },
    # =====================================================================
    # GENERAL — TRAVEL VARIANTS
    # =====================================================================
    "general/travel_domestic": {
        "market": "Domestic travel within the country (medical, baggage, delay).",
        "exclusions": ["Pre-existing conditions unless declared", "Hazardous sports unless added", "Travel against medical advice"],
        "endorsements": ["Adventure sports", "Trip delay/cancellation", "Baggage delay"],
        "limits": ["Medical sum insured per domestic plan", "Baggage/delay sub-limits"],
        "rating": ["Age, plan, trip duration", "Family vs individual"],
        "refer": ["Senior travelers", "High medical sums"],
    },
    # =====================================================================
    # GENERAL — MARINE
    # =====================================================================
    "general/marine_hull": {
        "market": "Vessel owners insuring the hull and machinery.",
        "exclusions": ["Inherent vice; wear and tear", "War/strikes unless included", "Unseaworthiness"],
        "endorsements": ["War & Strikes", "Increased value", "Loss of hire"],
        "limits": ["Agreed value of the vessel", "Institute warranties apply"],
        "rating": ["Vessel type, age, value, and flag", "Trade/route and class", "Loss history"],
        "refer": ["High-value hull", "War-zone or sanctioned trade"],
    },
    # =====================================================================
    # GENERAL — FIRE
    # =====================================================================
    "general/fire_residential": {
        "market": "Residential standard fire and allied perils (SFSP).",
        "exclusions": ["War/nuclear; wear and tear", "Own faulty design; neglect", "Flood/EQ unless allied perils selected"],
        "endorsements": ["Terrorism", "Earthquake/flood", "Removal of debris"],
        "limits": ["Sum insured on reinstatement value", "80% average clause"],
        "rating": ["Construction, occupancy, zone", "Loss history", "LTA discount"],
        "refer": ["High-value residences", "Coastal/EQ zones"],
    },
    # =====================================================================
    # GENERAL — LIABILITY
    # =====================================================================
    "general/public_liability_gi": {
        "market": "Businesses and premises exposing third-party bodily injury/property damage.",
        "exclusions": ["Injury to the insured's own employees (WC)", "Contractual liability beyond tort", "Fines and penalties"],
        "endorsements": ["Additional insured", "Waiver of subrogation", "Worldwide jurisdiction"],
        "limits": ["Indemnity plus defence (aggregate)", "Per-occurrence structure"],
        "rating": ["Occupancy/footfall and turnover", "Territory", "Loss history"],
        "refer": ["High-footfall/hazardous premises", "Any large public-liability claim"],
    },
    "general/product_liability_gi": {
        "market": "Manufacturers/importers exposing product-related injury/damage liability.",
        "exclusions": ["Recall costs unless covered", "Contractual liability beyond tort", "Fines and penalties"],
        "endorsements": ["Recall sub-limit", "Foreign territory", "Vendors endorsement"],
        "limits": ["Products aggregate and per-occurrence", "Recall sub-limit"],
        "rating": ["Product type, turnover, and exports", "Quality controls", "Loss history"],
        "refer": ["Export/US jurisdiction", "Any prior product claim or recall"],
    },
    # =====================================================================
    # GENERAL — CYBER
    # =====================================================================
    "general/cyber_ransomware": {
        "market": "Businesses needing cyberattack/ransomware first-party cover (BI + restoration).",
        "exclusions": ["No privacy/third-party liability (that is the data-breach cover)", "Betterment; prior known incidents", "War/state-sponsored attacks"],
        "endorsements": ["Cyber extortion / ransom cover", "System restoration", "Business interruption", "Forensic/PR costs"],
        "limits": ["First-party limit with extortion/restoration sub-limits", "Waiting period and retention"],
        "rating": ["Controls: MFA, offline backups, EDR, patch status", "Revenue and record count", "Prior incidents"],
        "refer": ["No offline backups or unsupported systems", "Any prior ransomware incident"],
    },
    # =====================================================================
    # GENERAL — CROP
    # =====================================================================
    "general/crop_weather": {
        "market": "Producers using parametric weather-index cover (rainfall/temperature).",
        "eligible": ["Defined weather station and parameter near the plot", "Reliable historical weather data"],
        "exclusions": ["No yield-based indemnity (parametric only)", "Areas without reliable station data", "War/nuclear"],
        "endorsements": ["Payout trigger levels", "Multiple-station indices"],
        "limits": ["Payout per trigger (parametric) × sum insured", "Sum insured per hectare"],
        "rating": ["Station selection and index design", "Trigger thresholds and payout rate", "Crop and season"],
        "refer": ["Pilot indices with thin data", "Large single-station concentration"],
    },
    # =====================================================================
    # GENERAL — ANIMAL
    # =====================================================================
    "general/pet_insurance": {
        "market": "Companion-pet owners insuring veterinary and liability costs.",
        "eligible": ["Microchipped/identified pet with vaccination records", "Age within the plan band"],
        "exclusions": ["Pre-existing/hereditary conditions", "Congenital conditions where excluded", "Cosmetic procedures"],
        "endorsements": ["Surgery/illness cover", "Third-party liability", "Wellness add-on"],
        "limits": ["Annual vet-fee limit and per-illness caps", "Third-party liability sub-limit"],
        "rating": ["Species, breed, age, and location", "Vaccination/health status", "Plan tier"],
        "refer": ["Brachycephalic/high-risk breeds", "Any pre-existing condition"],
    },
    # =====================================================================
    # GENERAL — EVENT
    # =====================================================================
    "general/wedding_insurance": {
        "market": "Couples/planners insuring wedding cancellation and liability.",
        "exclusions": ["Weather unless endorsed", "Change of mind; known circumstances", "War/terrorism unless endorsed"],
        "endorsements": ["Adverse weather", "Vendor non-appearance", "Public liability"],
        "limits": ["Cancellation up to the wedding budget", "Liability separate"],
        "rating": ["Budget, venue, and date", "Lead time and guest count", "Peril endorsements"],
        "refer": ["Outdoor/peak-season weddings", "Short lead time"],
    },
    # =====================================================================
    # GENERAL — PROVIDER
    # =====================================================================
    "general/insurer_psu": {
        "market": "Purchase-KYC for government/PSU-insurer products (identity/address norms).",
        "exclusions": ["Retail product exclusions apply per the underlying PSU/GIC cover", "KYC incompleteness prevents issuance"],
        "limits": ["Per the underlying retail product purchased", "PSU product limits"],
        "rating": ["Per the underlying PSU/GIC product", "Tariff-driven filed rates"],
        "refer": ["KYC mismatch or unverifiable identity", "Non-standard provider KYC"],
    },
    "general/insurer_private": {
        "market": "Purchase-KYC for private-insurer products (identity/address norms).",
        "exclusions": ["Retail product exclusions apply per the underlying private-insurer cover", "KYC incompleteness prevents issuance"],
        "limits": ["Per the underlying private-insurer product", "Private-insurer product limits"],
        "rating": ["Per the underlying private-insurer product", "Provider-specific filed rates with underwriting flexibility"],
        "refer": ["KYC mismatch or unverifiable identity", "Non-standard provider KYC"],
    },
}

# ---------------------------------------------------------------------------
# Merge the per-product differentiation layer. It supplies the product-specific
# decline, endorsement, and refer content and is authoritative for exactly
# those three sections; every other field keeps whatever was authored above.
# This guarantees no two products in a category share identical decline,
# endorsement, or refer content.
# ---------------------------------------------------------------------------
from rag_product_differentiation import PRODUCT_DIFFERENTIATION  # noqa: E402

_DIFFERENTIATED_FIELDS = ("decline", "endorsements", "refer")

for _key, _fields in PRODUCT_DIFFERENTIATION.items():
    _target = PRODUCT_OVERRIDES.setdefault(_key, {})
    for _field, _values in _fields.items():
        if _field in _DIFFERENTIATED_FIELDS:
            _target[_field] = _values
        else:
            _target.setdefault(_field, _values)

del _key, _fields, _target, _field, _values
