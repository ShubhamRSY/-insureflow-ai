"""Underwriting knowledge base for the RAG corpus generator.

Category-level underwriting content (market, eligibility, decline criteria,
exclusions, endorsements, limits, rating factors, refer triggers, red flags)
that the generator merges with the live product catalogs in
``src/insureflow/insurance/*.py`` to produce full-depth underwriting guide
entries. Content is authored per line of business and category, matching how a
carrier organizes an underwriting manual (line rules + per-product notes).
"""

from __future__ import annotations

from rag_product_overrides import PRODUCT_OVERRIDES

LOB_META: dict[str, dict[str, object]] = {
    "commercial": {
        "title": "Commercial Insurance (P&C)",
        "guide": "Commercial Lines Underwriting Guide",
        "standards": "ISO commercial lines forms, ACORD applications, NCCI (workers comp), AAIS (inland marine)",
        "authority": "Field authority to $250K premium / $5M TIV; above refers to the Commercial Desk. Any decline requires a written reason on the file.",
    },
    "life": {
        "title": "Life Insurance",
        "guide": "Life Underwriting Guide",
        "standards": "ACORD 100 series, MIB, HIPAA authorizations, NAIC model regs, IRC 7702 / 101(g)",
        "authority": "Field authority to $1M face / Table 2; above, or any flat extra > $5/$1,000, refers to the Life Chief Underwriter.",
    },
    "health": {
        "title": "Health Insurance",
        "guide": "Health & Employee Benefits Underwriting Guide",
        "standards": "ACA (PHSA §2702/2704), NAIC model regs, CMS Medicare guidance, state DOI rate filing",
        "authority": "Major medical is guaranteed-issue. Supplemental lines carry medical/occupational authority to $100K benefit; above refers.",
    },
    "general": {
        "title": "General / Non-Life",
        "guide": "General Insurance Underwriting Guide",
        "standards": "IRDAI (Protection of Policyholders' Interests) Regulations, All India Fire Tariff, Motor Tariff, ICC (marine)",
        "authority": "Catalog products are underwritten manually. Accept within filed product terms; refer any non-standard term, add-on, or sum insured above the product limit.",
    },
    "personal_auto": {
        "title": "Personal Auto",
        "guide": "Personal Auto Underwriting Guide",
        "standards": "ISO Personal Auto Program (PAP), state financial-responsibility limits, NAIC",
        "authority": "Field authority to program limits; refer non-standard drivers, high-value vehicles, and SR-22/FR filings.",
    },
    "personal_homeowners": {
        "title": "Personal Homeowners",
        "guide": "Homeowners Underwriting Guide",
        "standards": "ISO HO-3/HO-5 forms, CLUE, state DOI filed rules",
        "authority": "Field authority to program limits; refer coastal/wildfire zones, aged roofs, and excessive CLUE losses.",
    },
}

DEFAULT_STATE_NOTE = (
    "Rates, rules, and forms are state-filed. Confirm the issue state's mandated benefits, "
    "rating restrictions, and any surplus-lines or stamping requirements before binding."
)

KNOWLEDGE_BASE: dict[str, dict[str, dict[str, list[str] | str]]] = {
    "commercial": {
        "property": {
            "market": "Commercial real estate owners and tenants, manufacturers, warehousers, retail, and hospitality seeking all-risk or named-peril property programs.",
            "eligible": [
                "ISO construction classes 1–6 (frame through fire-resistive) in good repair",
                "Protected risks within 1,000 ft of a hydrant and 5 road-miles of a responding fire station",
                "Owner-occupied and investment (tenant) occupancies supported by a current valuation",
                "Habitational risks only where mitigated and outside designated CAT zones",
            ],
            "decline": [
                "Unprotected ISO frame (class 10) or risks with an adverse fire history",
                "Vacancy exceeding 60 days without a vacancy permit",
                "Prohibited wildfire / hurricane zones without documented mitigation",
                "Condemned structures, active code violations, or unrepaired prior damage",
            ],
            "exclusions": [
                "Flood and earthquake (written separately or via a DIC form)",
                "Wear, tear, deterioration, and inherent vice",
                "Mold to the extent of the sub-limit",
                "Employee dishonesty (crime form)",
                "Ordinance or law unless endorsed",
                "Utility services interruption unless endorsed",
            ],
            "endorsements": [
                "Ordinance or Law (ISO CP 04 05)",
                "Equipment Breakdown",
                "Utility Services — Direct Damage and Time Element",
                "Spoilage / Peak Season",
                "Builder's Risk for renovation periods",
                "Agreed Value and Inflation Guard",
            ],
            "limits": [
                "Building and BPP on a replacement-cost basis; coinsurance 80–100%",
                "Debris removal 25% of the loss plus $25K",
                "Mold $10K–$50K sub-limit",
                "Business income 12-month default extended period",
                "Spoilage $5K–$25K",
            ],
            "rating": [
                "COPE — construction, occupancy, protection, and exposure",
                "Rating territory and public protection class",
                "Age and condition of roof, wiring, plumbing, and HVAC",
                "Three-to-five-year loss history and loss ratio",
                "Deductible selection (AOP standard; separate wind/hail)",
            ],
            "refer": [
                "Total insured value above $25M or any CAT-zone schedule",
                "Three-year loss ratio above 60%",
                "Roof age over 20 years on frame construction",
                "Five or more locations outside the issue state",
            ],
        },
        "liability": {
            "market": "Contractors, manufacturers, distributors, service operations, and professional firms needing CGL and liability limits up to $2M/$4M.",
            "eligible": [
                "Standard ISO CGL classes with under 30% subcontracted revenue",
                "Products-completed-operations exposure under $10M annual receipts",
                "Residential construction not exceeding three stories",
                "Confirmed loss-control program for higher-hazard classes",
            ],
            "decline": [
                "Excluded NAICS industries (per appetite rule APT-001)",
                "Ongoing environmental/pollution exposure without a standalone pollution policy",
                "Asbestos or lead abatement operations",
                "Bars and taverns (write under liquor liability)",
            ],
            "exclusions": [
                "Expected or intended injury",
                "Contractual liability other than insured contracts",
                "Absolute pollution exclusion unless amended",
                "Damage to your work and product recall",
                "Professional / E&O exposures (separate form)",
            ],
            "endorsements": [
                "Additional Insured — Owners, Lessees, Contractors (CG 20 10 / 20 11 / 20 37)",
                "Waiver of Subrogation",
                "Primary and Non-Contributory wording",
                "Limited pollution buy-back",
                "Hired and Non-Owned Auto",
                "Mold / communicable disease sub-limit",
            ],
            "limits": [
                "$1M / $2M general aggregate as the default",
                "Products-completed-operations aggregate (shared or separate)",
                "Fire legal liability $50K–$300K",
                "Damage to premises rented to you $100K",
                "Employee benefits and employers' liability where applicable",
            ],
            "rating": [
                "Class codes with payroll, sales, or area exposures",
                "Experience modification where applicable",
                "Deductible or SIR election",
                "Territory and state catastrophe loading",
            ],
            "refer": [
                "Gross receipts above $25M",
                "Assault-and-battery, habitational, or adult-entertainment exposure",
                "Umbrella stacking above $5M",
                "New ventures with under two years operating history",
            ],
        },
        "workforce": {
            "market": "Employers of all sizes for workers' compensation, employer's liability, and group workforce benefits.",
            "eligible": [
                "State-governed workers' compensation for eligible employment classes",
                "Captive or self-insured groups for qualifying industries",
                "Documented safety program for high-hazard classes",
            ],
            "decline": [
                "Non-compliant or unlicensed operations",
                "Classes with unfunded prior workers' compensation liability",
                "Employee-leasing/PEO arrangements without a concurrent control agreement",
            ],
            "exclusions": [
                "Employment-practice penalties (written under EPLI)",
                "Domestic employees (separate policy)",
                "Federal employment classes (Longshore, FELA) unless extended",
            ],
            "endorsements": [
                "Waiver of Subrogation",
                "Voluntary Compensation",
                "Alternate Employer",
                "US Longshore and Harbor Workers' extension",
            ],
            "limits": [
                "Statutory workers' compensation benefits",
                "Employer's liability $100K/$500K/$100K — raise to $1M/$1M/$1M",
                "Employer's liability policy aggregate",
            ],
            "rating": [
                "Class rate per $100 of payroll",
                "Experience Modification Factor (EMR)",
                "Schedule and premium credits",
                "State assessments and surcharges",
            ],
            "refer": [
                "EMR above 1.25",
                "High-hazard classification with new operations",
                "Multi-state payroll",
                "Heavy loss history or prior litigation",
            ],
        },
        "auto": {
            "market": "Commercial auto fleets, owner-operators, and monoline hired/non-owned auto exposures.",
            "eligible": [
                "Private-passenger-to-commercial (classes 3–6), light/medium trucks, and tractors",
                "Drivers with valid CDL/MVR within program thresholds",
                "Garaged in an eligible state",
            ],
            "decline": [
                "Drivers with DUI or felony convictions in the last five years",
                "Long-haul trucking without DOT compliance",
                "Prohibited classes such as racing or dealer exposures without a garage policy",
            ],
            "exclusions": [
                "Racing and operation off public roads",
                "Expected or intended damage",
                "Pollution from cargo unless endorsed",
                "Livery use without an endorsement",
            ],
            "endorsements": [
                "Hired Auto Physical Damage",
                "Employee Hired and Named Drivers",
                "Individual Named Insured",
                "Truckers — pollution buy-back",
                "Audio, visual, and electronic equipment",
            ],
            "limits": [
                "Combined single limit $1M default; higher for DOT/fleet",
                "Physical damage on ACV or stated-amount basis",
                "Medical payments / PIP optional where required",
                "Hired and non-owned CSL of $1M",
            ],
            "rating": [
                "Vehicle class, weight, radius, and territory",
                "MVR, driver age, experience, and years licensed",
                "Use (service, retail, trucking) and annual mileage",
                "Fleet size and loss history",
            ],
            "refer": [
                "Haulage beyond a 300-mile radius without a DOT file",
                "Three or more at-fault claims or two major violations in three years",
                "Hazmat or long-haul trucking",
                "Fleet above 25 power units",
            ],
        },
        "financial": {
            "market": "Financial and credit exposures — trade credit, surety bonds, political risk, representations & warranties, and legal expense.",
            "eligible": [
                "Acceptable obligor/buyer credit ratings",
                "Bonded principals with demonstrated capacity and collateral",
                "M&A transactions with vetted, audited financials",
            ],
            "decline": [
                "Principals with prior bond defaults or unsatisfied judgments",
                "Obligors in sanctioned countries (political risk)",
                "Transactions without audited financial statements",
            ],
            "exclusions": [
                "Fraud or concealment by the insured",
                "Known pre-existing breach (R&W)",
                "War and confiscation unless endorsed (political risk)",
            ],
            "endorsements": [
                "Restoration of limit (trade credit)",
                "Increased economic-downturn waiver",
                "Non-cancellable extensions",
                "Currency-convertibility extensions",
            ],
            "limits": [
                "Discretionary credit limit per buyer",
                "Bond penalty up to 100% of contract value",
                "Aggregate indemnity cap (R&W typically 10% of deal value)",
            ],
            "rating": [
                "Buyer/obligor credit rating",
                "Industry sector and country risk",
                "Transaction tenor, deductible, and retention",
                "Book loss experience",
            ],
            "refer": [
                "Single exposure above $2M or any unbounded guarantee",
                "Political-risk sanctions exposure",
                "Transactions in distressed sectors",
            ],
        },
        "specialty": {
            "market": (
                "Non-standard and industry-specific perils requiring manuscript or specialized forms — "
                "construction wrap-ups, aviation, event, IP, K&R, terrorism, recall, supply chain, crop, and livestock."
            ),
            "eligible": [
                "Operators holding class-specific certification and licensing",
                "Documented risk-management programs and contingency plans",
            ],
            "decline": [
                "Aviation operators without current airworthiness or crew certification",
                "Events without required public-authority permits",
                "Sanctioned trade (terrorism / political risk)",
            ],
            "exclusions": [
                "War, nuclear, and radioactive contamination (TRIA excludes certified acts)",
                "Wear, tear, and gradual deterioration",
                "Professional negligence unless the form responds",
                "Consequential or economic loss unless endorsed",
            ],
            "endorsements": [
                "Terrorism (TRIA certified and non-certified)",
                "Extended cancellation / abandonment (event)",
                "Crisis-response services (K&R)",
                "Recall rehabilitation expenses",
                "Country and territory extensions",
            ],
            "limits": [
                "Event cancellation: full gross revenue at risk",
                "K&R: $1M–$10M per occurrence typical",
                "Recall: $5M with a 12-month discovery period",
                "Construction wrap-up: per-project aggregate",
            ],
            "rating": [
                "Exposure base — attendance, revenue, receipts, headcount",
                "Peril and catastrophe zoning",
                "Risk-management credits and debits",
                "Duration and radius of the exposure",
            ],
            "refer": [
                "Any manuscript non-standard form",
                "Sum insured above $10M on specialty perils",
                "Air, water, or military exposure",
                "Any sanctioned territory",
            ],
        },
        "alternative": {
            "market": "Large or complex insureds using captives, self-insured retentions, and fronting arrangements to retain risk.",
            "eligible": [
                "Captive feasibility study and actuarial funding in place",
                "Fronting carrier with A-rated admitted paper and collateral",
                "Board-approved risk-retention policy",
            ],
            "decline": [
                "Insufficient capital or funding for the retained layer",
                "No actuarial support for loss picks",
                "Jurisdictions that do not permit the captive structure",
            ],
            "exclusions": [
                "Risks outside the captive's approved plan",
                "Losses exceeding policy limits and aggregate",
                "Punitive or exemplary damages where uninsurable",
            ],
            "endorsements": [
                "SIR (loss-sensitive) endorsement",
                "Aggregate stop-loss",
                "Collateral and who-owns-what schedules",
                "TRIA compliance",
            ],
            "limits": [
                "SIR $100K–$5M per occurrence, aggregate where specified",
                "Fronted policy limits typically $1M–$5M",
                "Aggregate stop-loss attachment per the funding study",
            ],
            "rating": [
                "Loss-pick assumptions (actuarial)",
                "Funding and letter-of-credit collateral",
                "Fronting fee (typically 5–10% of SG&A)",
                "Credit quality of the captive",
            ],
            "refer": [
                "Any captive domicile new to the program",
                "SIR above $1M without actuarial sign-off",
                "Fronting without admitted paper",
            ],
        },
        "package": {
            "market": "Small commercial and mid-market accounts bundling property and liability under one BOP or CPP.",
            "eligible": [
                "Eligible occupancy combined with property and liability cover",
                "Building and BPP values within program limits",
                "Revenue and payroll within BOP/CPP thresholds",
            ],
            "decline": [
                "Occupancies on the BOP ineligible list (bars, auto repair, restaurants without hood suppression)",
                "Values exceeding CPP program capacity",
                "High-hazard manufacturing",
            ],
            "exclusions": [
                "Property and CGL exclusions apply line by line",
                "Professional liability",
                "Auto and workers' compensation (separate forms required)",
            ],
            "endorsements": [
                "Business Income and Extra Expense",
                "Employee Dishonesty",
                "Equipment Breakdown",
                "Hired and Non-Owned Auto (CPP)",
                "Spoilage, Signs, and Outdoor Property",
            ],
            "limits": [
                "Building and BPP per the BOP/CPP program schedule",
                "CGL $1M/$2M with 12-month business income",
                "$10K/$25K deductibles typical",
            ],
            "rating": [
                "Loss cost × exposure by coverage",
                "Package credit and multi-coverage discount",
                "Territory and protection class",
                "Deductible selection",
            ],
            "refer": [
                "Any account needing manuscript coverage",
                "Values exceeding BOP/CPP capacity",
                "Mixed-use with habitational exposure",
            ],
        },
    },
    "life": {
        "term": {
            "market": "Pure protection for income replacement, mortgage and debt cover, and business obligations.",
            "eligible": [
                "Issue ages 18–75 with standard through preferred classes",
                "Face amounts $100K–$5M (financial underwriting above thresholds)",
                "US residents; non-US citizens require a documented US nexus",
            ],
            "decline": [
                "Active cancer or high-risk recent diagnoses within postponement windows",
                "Chronic organ failure or recent MI/stroke within the waiting period",
                "Foreign residence in a restricted country; uninsurable avocations",
            ],
            "exclusions": [
                "Suicide within the first two policy years",
                "Material misrepresentation within the two-year contestable period",
                "War or hazardous aviation unless excluded-rated",
            ],
            "endorsements": [
                "Waiver of Premium",
                "Accelerated Death Benefit (terminal illness)",
                "Child Rider",
                "Disability Income rider",
                "Return of Premium (ROP)",
            ],
            "limits": [
                "Face of 10–20× income for financial underwriting",
                "Convertible to permanent while the term is in force",
                "Renewable annually to age 80–95 depending on the form",
            ],
            "rating": [
                "Attained age, sex, and tobacco status",
                "Health class (preferred plus through rated tables)",
                "Face-amount band and term duration",
                "Avocation and motor-vehicle records",
            ],
            "refer": [
                "Face above $5M or above 20× income",
                "Rated Table 3+ or multiple impairments",
                "Residency in a restricted country",
            ],
        },
        "whole": {
            "market": "Permanent, guaranteed death benefit with cash value for estate, legacy, and estate-planning needs.",
            "eligible": [
                "Issue ages 0–85 depending on the product and premium structure",
                "Funding capacity verified for higher-premium plans",
            ],
            "decline": [
                "Uninsurable impairments",
                "Foreign residence or active-duty combat zones",
            ],
            "exclusions": [
                "Suicide and contestability for two years",
                "Material misrepresentation",
            ],
            "endorsements": [
                "Paid-Up Additions (PUA)",
                "Guaranteed Insurability",
                "Term Rider",
                "Accelerated Death Benefit",
                "Long-Term Care rider (hybrid)",
            ],
            "limits": [
                "Face amount per financial underwriting; avoid MEC status",
                "Single-premium and limited-pay require source-of-funds review",
            ],
            "rating": [
                "Issue age, sex, and tobacco",
                "Face band and dividend option (par policies)",
                "Payment mode and guarantee period",
            ],
            "refer": [
                "Premium above $100K/year or single premium above $1M",
                "Foreign national or nexus",
                "Complex ownership (ILIT, trust)",
            ],
        },
        "universal": {
            "market": "Flexible permanent coverage — guaranteed universal life, current-assumption, indexed (IUL), and variable (VUL).",
            "eligible": [
                "Issue ages 18–85 with adequate funding for the no-lapse guarantee",
                "Registered representative and prospectus for VUL (FINRA/SEC)",
            ],
            "decline": [
                "Impairments as per whole-life underwriting",
                "VUL without a registered representative and suitability file",
            ],
            "exclusions": [
                "Suicide and contestability for two years",
                "For VUL: market risk is borne by the owner",
            ],
            "endorsements": [
                "No-lapse guarantee rider",
                "Indexed crediting strategies (caps and participation rates)",
                "Waiver of Monthly Deductions",
                "Overloan protection",
                "Accelerated Death Benefit",
            ],
            "limits": [
                "GUL: guaranteed death benefit with a minimum premium",
                "IUL caps 9–12% with participation rates and a floor",
                "VUL separate accounts with a delivered prospectus",
            ],
            "rating": [
                "Health class; funding level affects lapse risk",
                "Interest/index assumptions and policy charges",
                "Rider loadings",
            ],
            "refer": [
                "IUL targets above 3% of account value",
                "VUL with aggressive subaccount allocations",
                "Single or limited funding of a GUL",
            ],
        },
        "endowment": {
            "market": "Scheduled maturity payouts (largely legacy / US-equivalent) for defined savings goals.",
            "eligible": [
                "Defined term with guaranteed maturity value",
                "Verified funding capacity",
            ],
            "decline": [
                "Uninsurable where a mortality cover is included",
                "Insufficient funding for the guaranteed maturity value",
            ],
            "exclusions": [
                "Suicide and contestability",
                "Surrender-charge schedules",
            ],
            "endorsements": [
                "Paid-up benefits",
                "Surrender-value guarantees",
            ],
            "limits": [
                "Maturity value per the funding schedule",
                "Surrender-charge tables by duration",
            ],
            "rating": [
                "Sex, age, and tobacco mortality",
                "Guaranteed interest assumption",
                "Payment term and frequency",
            ],
            "refer": [
                "Non-standard structures",
                "Jumbo funding",
            ],
        },
        "ulip": {
            "market": "US-equivalent variable universal life — market-linked cash value for retirement or legacy with insurance.",
            "eligible": [
                "Registered representative and suitability review; prospectus delivered",
                "Issue ages 18–75 with adequate funding",
            ],
            "decline": [
                "Unsuitable risk tolerance or stated purpose",
                "Uninsurable health; restricted residence",
            ],
            "exclusions": [
                "Investment losses borne by the owner",
                "Suicide and contestability",
            ],
            "endorsements": [
                "Return-of-Premium (ROP) rider",
                "Child and pension riders",
                "Guaranteed minimum death benefit",
            ],
            "limits": [
                "Premium loads, cost of insurance, and fund fees per the prospectus",
                "Minimum premium to keep the policy in force",
            ],
            "rating": [
                "Mortality per class and subaccount fees",
                "Suitability of the allocation",
            ],
            "refer": [
                "Concentrated or aggressive allocations",
                "Short surrender-period churning",
                "Non-resident aliens",
            ],
        },
        "money_back": {
            "market": "Return-of-premium protection — coverage with premium refunds at defined intervals.",
            "eligible": [
                "Ages and targets per the plan",
                "Income proof for the premium commitment",
            ],
            "decline": [
                "Uninsurable health",
                "Insufficient funding for guaranteed refunds",
            ],
            "exclusions": [
                "Suicide and contestability",
                "Partial-surrender penalties",
            ],
            "endorsements": [
                "Rider-based ROP",
                "Paid-up additions",
            ],
            "limits": [
                "Refund schedule per the plan",
                "Tax treatment (non-zero basis) documented",
            ],
            "rating": [
                "Age, sex, and tobacco",
                "Plan term and premium mode",
            ],
            "refer": [
                "Large-face ROP",
                "Foreign nexus",
            ],
        },
        "annuity": {
            "market": "Income and retirement products — immediate, deferred, fixed, indexed, variable, QLAC, and structured settlements.",
            "eligible": [
                "Single and flexible premium within product ages",
                "Suitability review for all; registered representative and prospectus for variable",
            ],
            "decline": [
                "Unsuitable for a near-term liquidity need",
                "Structured settlements without court-approved documents",
            ],
            "exclusions": [
                "Surrender charges",
                "Market risk (variable and indexed products)",
                "Non-qualified contribution limits",
            ],
            "endorsements": [
                "Guaranteed Lifetime Withdrawal Benefit (GLWB)",
                "Guaranteed Minimum Income Benefit (GMIB)",
                "Death-benefit riders",
                "Deferred income (QLAC)",
            ],
            "limits": [
                "QLAC limited to the IRS-qualified amount",
                "Structured settlements pay defined periodic amounts",
                "Allocation caps by age for GLWB",
            ],
            "rating": [
                "Current crediting rate, caps, and floors",
                "Mortality and expense charges; rider costs",
                "Surrender schedule",
            ],
            "refer": [
                "Suitability concerns at age 70+ with a liquidity need",
                "Structured settlement without court documents",
                "Variable annuity without a registered representative",
            ],
        },
    },
    "health": {
        "individual": {
            "market": "ACA Marketplace metal-tier (Bronze/Silver/Gold/Platinum) and off-exchange major medical.",
            "eligible": [
                "US citizens or lawfully present residents",
                "Open enrollment or a qualifying special enrollment period",
                "Metal tier matched to household income and subsidy",
            ],
            "decline": [
                "Submission outside open/special enrollment without an SEP",
                "Non-admitted immigrant status",
            ],
            "exclusions": [
                "No pre-existing-condition exclusion (ACA guaranteed issue)",
                "Non-EHB services and out-of-network care except emergencies",
            ],
            "endorsements": [
                "Plan-design and network changes only (no medical endorsements)",
            ],
            "limits": [
                "Out-of-pocket maximum per ACA; no annual or lifetime caps",
                "Deductibles by metal tier with embedded family deductibles",
            ],
            "rating": [
                "Age curve, family composition, tobacco loading",
                "Rating area (geography) and APTC subsidy",
                "Community rating within age bands",
            ],
            "refer": [
                "Multi-state households with tax-dependency complexity",
                "Mixed eligibility (Medicare / CHIP / Medicaid)",
            ],
        },
        "family_floater": {
            "market": "A single policy covering the household under one aggregate family deductible.",
            "eligible": [
                "Two or more household members",
                "ACA-compliant family enrollment",
            ],
            "decline": [
                "Members who are not tax dependents",
                "Split households",
            ],
            "exclusions": [
                "Exclusions per the plan; no health-status exclusions",
            ],
            "endorsements": [
                "Network and plan-design options",
            ],
            "limits": [
                "Family aggregate deductible with an embedded individual OOP max",
                "Metal-tier out-of-pocket caps",
            ],
            "rating": [
                "Age of each member, tobacco, rating area",
                "Family-tier rating adjustments",
            ],
            "refer": [
                "Mixed citizenship/residency within the household",
            ],
        },
        "critical_illness": {
            "market": "Lump-sum on first diagnosis of covered conditions (cancer, cardiac, stroke, etc.) and disease-specific cover.",
            "eligible": [
                "Issue ages 18–65 on a health-questionnaire basis",
                "Covered-condition list matched to the insured's risk profile",
            ],
            "decline": [
                "Prior diagnosis of a covered condition",
                "Terminal illness within the cancer/heart history windows",
            ],
            "exclusions": [
                "Pre-existing waiting period (90–180 days)",
                "First-30-day exclusion for selected conditions",
                "Self-inflicted injury and war",
            ],
            "endorsements": [
                "Multi-stage (early and advanced) benefits",
                "Cancer-specific acceleration",
                "Juvenile/child cover",
            ],
            "limits": [
                "Benefit per condition ($25K–$250K), independent or shared",
                "25% early-stage payout with a reduced multiple",
            ],
            "rating": [
                "Age, tobacco, and family history",
                "Benefit amount and number of covered conditions",
                "Occupation class",
            ],
            "refer": [
                "History of any covered condition",
                "High-risk avocation without an exclusion",
            ],
        },
        "senior": {
            "market": "Medicare Supplement (Medigap Plans A/G/N) and Medicare Advantage (MA/SNP).",
            "eligible": [
                "Age 65+ or under-65 disability Medicare-eligible",
                "Guaranteed-issue window (six months around Part B) where applicable",
            ],
            "decline": [
                "Medigap medical underwriting outside guaranteed-issue for non-GI plans",
                "ESRD unless within a qualifying SEP",
            ],
            "exclusions": [
                "Pre-existing waiting (up to six months) if not guaranteed-issue",
                "No coverage beyond Medicare-covered benefits (Medigap)",
            ],
            "endorsements": [
                "Plan N copays; high-deductible Plan G",
                "SNP care-coordination features",
            ],
            "limits": [
                "Medigap Plan-specific benefit table (A/G/N/F)",
                "MA maximum out-of-pocket (in-network or combined) per CMS",
            ],
            "rating": [
                "Issue-age, attained-age, or community rating",
                "Household and smoker discounts",
                "County / rating area",
            ],
            "refer": [
                "Underwriting outside OE/GI windows",
                "Dual-eligible (Medicare/Medicaid) — SNP routing",
                "Foreign residence",
            ],
        },
        "group": {
            "market": "ERISA large-group (fully insured or self-funded) and ACA small-group (community-rated).",
            "eligible": [
                "Bona fide employer groups meeting minimum participation",
                "Small group 1–50 (state variation); large group 51+",
            ],
            "decline": [
                "Groups below minimum participation/contribution",
                "Non-bona-fide associations (MEWA concerns)",
            ],
            "exclusions": [
                "Self-funded: stop-loss terms define exclusions",
                "No health-status underwriting within a group",
            ],
            "endorsements": [
                "Dental, vision, life, and disability add-ons",
                "Stop-loss for self-funded plans",
            ],
            "limits": [
                "Aggregate and specific stop-loss attachment points",
                "ACA essential health benefits and out-of-pocket caps",
            ],
            "rating": [
                "Community rating (small group) and experience rating (large)",
                "Participation, contribution, and workforce demographics",
                "SIC class loadings",
            ],
            "refer": [
                "Self-funded without stop-loss",
                "Minimum-participation waivers",
                "Multi-employer or union trusts",
            ],
        },
        "top_up": {
            "market": "Super top-up / gap coverage above a high-deductible base plan (per-incident or annual aggregate deductible).",
            "eligible": [
                "Insured maintains an underlying base health plan",
                "Deductible selected (for example a $100K aggregate)",
            ],
            "decline": [
                "No underlying base plan",
                "Cashless-only expectations without network participation",
            ],
            "exclusions": [
                "Claims already paid by the base plan (indemnity coordination)",
                "Pre-existing waiting where applicable",
            ],
            "endorsements": [
                "Aggregate vs per-incident deductible structure",
            ],
            "limits": [
                "Top-up deductible (annual aggregate) between base and top-up",
                "Sum insured per top-up",
            ],
            "rating": [
                "Base-plan sum insured and deductible",
                "Age and family size",
            ],
            "refer": [
                "Non-standard base coverage",
                "Coordination-of-benefits issues",
            ],
        },
        "personal_accident": {
            "market": "Accidental Death & Dismemberment (AD&D) and accident indemnity — individual, family, and group.",
            "eligible": [
                "Issue ages 18–70 (varies); no medical underwriting for AD&D",
                "Occupational class within appetite",
            ],
            "decline": [
                "Occupations above the risk class (mining, armed-forces combat)",
                "Prior disabling disability where indemnity applies",
            ],
            "exclusions": [
                "Suicide and self-inflicted injury",
                "Disease or illness; war; flight other than as a common-carrier passenger",
            ],
            "endorsements": [
                "Weekly indemnity and capital sum",
                "Dismemberment schedule",
                "Family and child cover",
            ],
            "limits": [
                "Capital sum insured and weekly indemnity",
                "AD&D principal-sum multiples per limb/sight schedule",
            ],
            "rating": [
                "Age, occupation class, and sums insured",
                "Family vs single; group participation",
            ],
            "refer": [
                "Hazardous occupation class",
                "High sums relative to income",
            ],
        },
        "disability": {
            "market": "Short- and long-term disability income replacement.",
            "eligible": [
                "Earned-income based with occupation class within limits",
                "Elimination and benefit periods selected",
            ],
            "decline": [
                "Occupations above class; no verifiable income",
                "Pre-existing conditions within the look-back",
            ],
            "exclusions": [
                "Pre-existing condition period (3/12 or 6/12)",
                "Self-inflicted injury; war; normal pregnancy where excluded",
            ],
            "endorsements": [
                "Own-occupation definition",
                "Residual/partial disability",
                "Cost-of-Living Adjustment (COLA)",
                "Future Increase Option",
            ],
            "limits": [
                "Monthly benefit to 60–70% of income (taxable or non-taxable)",
                "Maximum benefit period to age 65 / SSNRA",
            ],
            "rating": [
                "Age, sex, occupation class, and income",
                "Elimination and benefit periods",
                "Rider selections",
            ],
            "refer": [
                "Benefit above 70% of income; high-income financial underwriting",
                "Own-occupation for high-risk occupations",
            ],
        },
    },
    "general": {
        "motor": {
            "market": "Private cars and two-wheelers — statutory third-party and comprehensive own-damage.",
            "eligible": [
                "Valid RC, driving license, and PUC certificate",
                "Vehicle within age and IDV norms",
                "Insured discloses the previous policy and any NCB",
            ],
            "decline": [
                "Expired or forged RC/DL",
                "Vehicles used for prohibited purposes (racing, commercial use under a private policy)",
                "Total-loss or salvage vehicles without reinstatement",
            ],
            "exclusions": [
                "Driving without a valid license; DUI",
                "Wear and tear; mechanical or electrical breakdown",
                "Use outside India; war and nuclear perils; contractual liability",
            ],
            "endorsements": [
                "Zero Depreciation",
                "Engine and Gearbox protection",
                "Roadside Assistance",
                "Consumables cover",
                "NCB protection",
            ],
            "limits": [
                "IDV on age-based depreciation (5–50%)",
                "Third-party limits statutory (unlimited for death/disability; INR 15L property)",
                "NCB 20–50% of the own-damage premium",
            ],
            "rating": [
                "Vehicle class, age, and engine capacity; IDV and zone",
                "Driver age/experience and voluntary deductible",
                "Add-on selections",
            ],
            "refer": [
                "High-value, luxury, or imported vehicles",
                "Lapsed cover beyond 90 days without inspection",
                "Salvage or heavy-claims history",
            ],
        },
        "home": {
            "market": "Residential structure and contents — structure-only, contents-only, and comprehensive (Bharat Griha Raksha-type).",
            "eligible": [
                "Owner-occupier or tenant per the cover type; clear title where the structure is insured",
                "Sum insured based on reconstruction cost",
            ],
            "decline": [
                "Unoccupied beyond 30–60 days without endorsement",
                "Illegal construction or encroachment",
            ],
            "exclusions": [
                "War and nuclear perils; wear and tear; inherent defect",
                "Flood and earthquake unless selected as add-ons",
            ],
            "endorsements": [
                "Terrorism",
                "Flood/inundation and earthquake add-ons",
                "Alternative accommodation",
                "Specified contents and valuable articles",
            ],
            "limits": [
                "Sum insured = reconstruction cost (structure) + contents value",
                "80% average clause on the structure to avoid underinsurance",
            ],
            "rating": [
                "Construction type, age of building, zone, and sum insured",
                "Loss experience and add-on selection",
            ],
            "refer": [
                "High-value premises (sum insured above INR 1 crore)",
                "Coastal or earthquake zones; older or heritage structures",
            ],
        },
        "travel": {
            "market": "Domestic and international travel — medical, baggage, and cancellation.",
            "eligible": [
                "Valid passport/visa and itinerary (international)",
                "Age within the policy band",
            ],
            "decline": [
                "Pre-existing conditions not disclosed or within the look-back",
                "Travel to excluded or sanctioned countries",
            ],
            "exclusions": [
                "Pre-existing conditions unless declared",
                "Travel against medical advice; hazardous sports unless added",
                "War and sanctions; pregnancy beyond the stated week",
            ],
            "endorsements": [
                "Adventure sports",
                "Automatic extension on delay",
                "Document loss",
                "Home caretaker",
            ],
            "limits": [
                "Medical sum insured ($50K–$1M international)",
                "Baggage and delay sub-limits",
                "Age-based plan bands",
            ],
            "rating": [
                "Age, plan, trip duration/destination, and deductible",
                "Family/multi-trip vs single-trip",
            ],
            "refer": [
                "Senior travelers and higher medical sums insured",
                "Frequent/multi-trip with pre-existing conditions",
            ],
        },
        "marine": {
            "market": "Cargo (goods in transit) and hull (vessel) — domestic and import/export.",
            "eligible": [
                "Insurable interest in the goods or vessel; declared consignments",
                "ICC(A/B/C) basis selected for cargo",
            ],
            "decline": [
                "Prohibited or contraband goods; unseaworthy vessel",
                "Incoterms assigning risk outside the insured",
            ],
            "exclusions": [
                "Inherent vice and ordinary leakage/breakage (ICC C)",
                "Insufficiency or poor packing unless D/B/U is insured",
                "War and strikes unless included",
            ],
            "endorsements": [
                "War and Strikes",
                "Brand/ISO classification",
                "Duty and brand insurance (D/B/U)",
                "Sales-turnover/annual declaration",
            ],
            "limits": [
                "Sum insured = CIF/invoice value plus 10%",
                "Hull per agreed value with Institute warranties",
            ],
            "rating": [
                "Commodity type, packing, and route",
                "Carrier/conveyance type and ICC basis",
                "Annual turnover or declared volume",
            ],
            "refer": [
                "Project or heavy-lift cargo; unusual routes",
                "High-value hull; war-zone voyages",
            ],
        },
        "fire": {
            "market": "Residential (SFSP) and commercial/industrial fire with allied perils.",
            "eligible": [
                "Clear occupancy, construction, and risk class",
                "Sum insured on a reinstatement-value basis",
            ],
            "decline": [
                "Prohibited occupancies (e.g., firecracker storage) without specialist terms",
                "Repeated losses or fraud history",
            ],
            "exclusions": [
                "War and nuclear perils; wear and tear",
                "Own pollution; faulty design; neglect",
            ],
            "endorsements": [
                "Terrorism, earthquake, and flood via allied perils",
                "Sprinkler leakage; removal of debris",
                "Long-Term Agreement (LTA) discount",
            ],
            "limits": [
                "Sum insured on reinstatement value; 80% average clause",
                "Debris-removal and architect-fee sub-limits",
            ],
            "rating": [
                "Occupancy/risk class, construction, and protection (sprinklers)",
                "Loss history and long-term agreement discount",
            ],
            "refer": [
                "High-hazard occupancies (chemicals, plastics)",
                "Cumulative values beyond retention; catastrophe zones",
            ],
        },
        "liability": {
            "market": "Professional indemnity, public liability, and product liability (monoline liability).",
            "eligible": [
                "Professionals qualified and registered",
                "Products with quality controls and regulatory approvals",
                "Adequate turnover/headcount declaration",
            ],
            "decline": [
                "Firms with known large claims or regulatory action",
                "Products without the required regulatory approvals",
            ],
            "exclusions": [
                "Fines and penalties; punitive damages",
                "Contractual liability assumed beyond tort",
                "Recall costs unless covered",
                "Loss of goodwill / economic loss unless endorsed",
            ],
            "endorsements": [
                "Retroactive date change",
                "Worldwide jurisdiction (suit inside/outside)",
                "Defence costs inside the limit (or first-dollar)",
                "Extended reporting period",
            ],
            "limits": [
                "Indemnity plus defence costs (aggregate), INR 25L–INR 5Cr",
                "Per-occurrence/aggregate structure with sub-limits by peril",
            ],
            "rating": [
                "Turnover, fee income, and profession/class",
                "Claims experience and deductibles",
                "Territory and jurisdiction",
            ],
            "refer": [
                "Turnover above threshold or any known circumstance",
                "AI/GenAI, clinical, and construction professions",
                "US/Canada jurisdiction exposure",
            ],
        },
        "cyber": {
            "market": "Data breach (privacy liability and response) and cyberattack/ransomware (business interruption and restoration).",
            "eligible": [
                "Completed security questionnaire with MFA, EDR, and backups in place",
                "Revenue and records volume declared",
            ],
            "decline": [
                "No MFA, no offline backups, or unsupported software/OS",
                "Regulated data at scale with no controls",
            ],
            "exclusions": [
                "Betterment; prior known incidents",
                "War and state-sponsored attacks (market-dependent)",
                "Non-cyber business interruption; unencrypted portable-device losses",
            ],
            "endorsements": [
                "Social engineering / impersonation fraud",
                "Reputational and notification-cost extensions",
                "Systemic/catastrophe event sub-limit",
                "Third-party service provider",
            ],
            "limits": [
                "Separate liability and first-party limits with sub-limits",
                "Cyber-extortion / funds-transfer-fraud sub-limits",
                "Retention tiers by revenue",
            ],
            "rating": [
                "Revenue, record count, industry, and controls maturity",
                "Prior incidents; retention and sub-limits",
            ],
            "refer": [
                "No MFA/backups or unsupported systems",
                "Third-party processor concentration",
                "High-profile or regulated targets",
            ],
        },
        "crop": {
            "market": "Yield-based (PMFBY-type) and weather-index (parametric) crop cover.",
            "eligible": [
                "Notified crops and areas for the season; loanee and non-loanee",
                "Weather-index for a defined station and parameter",
            ],
            "decline": [
                "Areas or crops not notified; non-farm activity",
                "Parametric where no reliable weather-station data exists",
            ],
            "exclusions": [
                "Losses from war or nuclear perils",
                "Malicious damage by the insured",
                "Yield loss below the indemnity/deductible level",
            ],
            "endorsements": [
                "Prevented sowing / mid-season adversity (yield)",
                "Payout triggers for weather-index",
            ],
            "limits": [
                "Sum insured = scale of finance / loan value",
                "Index payout per trigger (parametric) or yield shortfall",
            ],
            "rating": [
                "Crop, season, area, and sum insured; PMFBY premium subsidy",
                "Index parameters, trigger thresholds, and payout rate",
            ],
            "refer": [
                "Pilot/parametric with limited data",
                "Large exposure in a single crop or geography",
            ],
        },
        "animal": {
            "market": "Livestock (cattle) and companion pet insurance.",
            "eligible": [
                "Animal identification (ear-tag/microchip) and health certificate",
                "Cattle used for farming/dairy; pet with vaccination records",
            ],
            "decline": [
                "No identification or health certificate; prohibited use",
                "Age outside eligibility; pre-existing/hereditary conditions (pet)",
            ],
            "exclusions": [
                "Death from pregnancy complications unless covered; theft without a police report",
                "Pre-existing/congenital conditions (pet); intentional slaughter",
            ],
            "endorsements": [
                "Pet surgery/illness cover and third-party liability",
                "Herd/package cover; ex-gratia for epidemics (cattle)",
            ],
            "limits": [
                "Sum insured = market value (cattle) / breed value (pet)",
                "Vet-fee limits and per-illness caps (pet)",
            ],
            "rating": [
                "Species, breed, age, location, and use",
                "Health/vaccination status; number covered",
            ],
            "refer": [
                "High-value stud or pedigree animals",
                "Group/herd with epidemic exposure",
            ],
        },
        "event": {
            "market": "Wedding and concert/public event cancellation/delay and liability.",
            "eligible": [
                "Event date, venue, and attendance confirmed; permits in place",
                "Budget/revenue declared",
            ],
            "decline": [
                "Events without required public-authority permission",
                "Prohibited or phantom events; unverifiable budgets",
            ],
            "exclusions": [
                "Weather unless an adverse-weather endorsement is purchased",
                "Change of mind; known circumstances at inception",
                "War and terrorism unless endorsed",
            ],
            "endorsements": [
                "Adverse weather",
                "Non-appearance of performers",
                "Terrorism and public liability for injury",
            ],
            "limits": [
                "Sum insured = total budget/revenue at risk",
                "Cancellation/postponement cover; liability is separate",
            ],
            "rating": [
                "Event type, duration, venue, attendance, and sum insured",
                "Peril endorsements and loss history",
            ],
            "refer": [
                "Outdoor or mega events; attendance near venue capacity",
                "Short lead time between purchase and the event date",
            ],
        },
        "title": {
            "market": "Legal title chain, encumbrance, and title-search insurance.",
            "eligible": [
                "Title search/abstract showing marketable title",
                "Registered documents with a clear chain and encumbrance statement",
            ],
            "decline": [
                "Known litigation or defects in title",
                "Forged or unregistered documents; unresolved benami/patta issues",
            ],
            "exclusions": [
                "Known defects and encumbrances at inception",
                "Government acquisitions/reservations if disclosed",
                "Illegal construction or unauthorized layout",
            ],
            "endorsements": [
                "Right-of-way / easement cover",
                "Post-policy title-cure extensions",
            ],
            "limits": [
                "Sum insured = property value or loan amount",
                "Cumulative / property-value cap",
            ],
            "rating": [
                "Property value, loan amount, and locality",
                "Title-search depth and cleared encumbrances",
            ],
            "refer": [
                "Any known title defect or pending litigation",
                "High-value properties; agricultural land",
            ],
        },
        "mortgage_gi": {
            "market": "Lender-linked cover on the mortgaged property/loan (fire and allied perils, sometimes housing-loan protection).",
            "eligible": [
                "Loan sanctioned and property mortgaged to the lender",
                "Sum insured aligned to the loan or reconstruction value",
            ],
            "decline": [
                "Property with clear violations; loan not sanctioned",
                "Non-standard or unapproved layouts without review",
            ],
            "exclusions": [
                "War and nuclear perils; wear and tear",
                "Wilful default or loss; tsunami/flood where not selected",
            ],
            "endorsements": [
                "Lender loss-payee clause",
                "Earthquake/flood add-ons and terrorism",
            ],
            "limits": [
                "Sum insured = outstanding loan or reconstruction value",
                "Lender's interest per schedule",
            ],
            "rating": [
                "Loan amount, term, and property value",
                "Zone and peril add-ons",
            ],
            "refer": [
                "Underinsurance relative to loan value",
                "Coastal/seismic zones with large sums",
            ],
        },
        "provider": {
            "market": "Provider-type purchase KYC (PSU vs private) and B2B reinsurance (insurer buying cover).",
            "eligible": [
                "Retail: KYC per provider type (PSU/GIC vs private insurers)",
                "Reinsurance: ceding insurer's registration, portfolio, and loss data",
            ],
            "decline": [
                "Unlicensed ceding insurer (reinsurance)",
                "KYC mis-match or unverifiable identity",
            ],
            "exclusions": [
                "Treaty terms and exclusions govern the reinsurance",
                "Retail exclusions per the underlying product",
            ],
            "endorsements": [
                "Treaty/facultative terms",
                "Portfolio withdrawal and cession rights",
            ],
            "limits": [
                "Retention, cession percentages, and aggregate ceilings (reinsurance)",
                "PI sum insured per treaty layer",
            ],
            "rating": [
                "Ceding company's loss experience and portfolio profile",
                "Treaty structure, commission, and profit-share",
            ],
            "refer": [
                "Any cross-border reinsurance layer",
                "New ceding relationship without loss data",
            ],
        },
    },
    "personal_auto": {
        "auto": {
            "market": "US personal auto (PAP) for private-passenger vehicles.",
            "eligible": [
                "Valid license and MVR within program guidelines",
                "Garaged vehicle with permitted use",
                "At least state-minimum liability",
            ],
            "decline": [
                "DUI or two or more at-fault accidents in three years",
                "Commercial or livery use under a private policy",
            ],
            "exclusions": [
                "Racing and intentional acts",
                "Delivery/rideshare use unless endorsed",
                "Regular availability of non-listed vehicles",
            ],
            "endorsements": [
                "Rideshare (TNC) endorsement",
                "Comprehensive and collision",
                "Uninsured/Underinsured Motorist",
                "Roadside assistance and rental reimbursement",
            ],
            "limits": [
                "State-minimum liability and UM/UIM",
                "Comprehensive/collision with deductible tiers",
            ],
            "rating": [
                "Age, gender, marital status, territory, and vehicle symbol",
                "MVR violations, prior insurance, and credit-based score where allowed",
            ],
            "refer": [
                "High-value or collectible vehicles",
                "Non-standard drivers and SR-22/FR filings",
            ],
        },
    },
    "personal_homeowners": {
        "home": {
            "market": "US homeowners (HO-3/HO-5 forms) for owner-occupied dwellings.",
            "eligible": [
                "Owner-occupied 1–4 family dwellings",
                "Updates and roof condition acceptable; CLUE acceptable",
                "Replacement cost within program",
            ],
            "decline": [
                "Uninsurable roof, knob-and-tube wiring, or unsafe conditions",
                "Vacant/for-sale; excessive CLUE losses",
            ],
            "exclusions": [
                "Flood and earthquake (separate)",
                "Wear, tear, and neglect",
                "Ordinance/law; business and rental exposures beyond permitted",
            ],
            "endorsements": [
                "Water backup and sump overflow",
                "Replacement cost on contents",
                "Scheduled personal property",
                "Separate wind/hail deductible",
            ],
            "limits": [
                "Coverage A/B/C/D with typical HO-3 limits",
                "AOP and separate wind/hail deductibles",
            ],
            "rating": [
                "Construction, age, roof, protection class, and territory",
                "CLUE/MVR; replacement cost vs ACV",
            ],
            "refer": [
                "Coastal/wind or wildfire zones",
                "Roof age over 20 years; prior water losses",
            ],
        },
    },
}

DOC_PURPOSE_RULES: list[tuple[tuple[str, ...], str]] = [
    # Loss, claims and litigation history ---------------------------------
    (
        ("loss run", "claims history", "claim history", "claims experience", "claims data", "loss history",
         "prior claims", "past claims", "prior recall", "recall history", "prior pollution", "prior event",
         "prior terrorism", "prior ip", "prior defamation", "prior bond", "prior r&w", "prior std",
         "prior fiduciary", "prior-year claims", "large claim", "shock loss", "historical interruption", "clue",
         "bad debt", "write-off", "prior epli", "prior pri"),
        "Establishes prior loss frequency and severity for experience rating and acceptability.",
    ),
    (
        ("litigation", "regulatory action", "regulatory compliance history", "eeoc", "cease-and-desist",
         "pleadings", "complaint", "charge history", "attorney", "counsel", "court order", "legal due diligence",
         "pending / past", "past litigation"),
        "Discloses prior or pending claims, litigation, or regulatory actions for acceptability.",
    ),
    # Continuity -----------------------------------------------------------
    (
        ("previous policy", "prior policy", "previous insurance", "prior carrier", "prior marine policy",
         "p&i club", "existing disability", "existing retirement", "rate history", "renewal package", "dec page",
         "declaration", "ncb", "no-claim", "no claim"),
        "Confirms cover continuity, prior terms, and any no-claim/loss-free entitlement.",
    ),
    # Securities / suitability --------------------------------------------
    (
        ("prospectus", "finra", "suitability", "risk profil", "investment objective", "securities account",
         "broker-dealer", "sub-account", "fund allocation", "retirement goal", "net worth", "investment structure",
         "retirement account"),
        "Confirms investment suitability, SEC/FINRA disclosure, and the securities-account setup.",
    ),
    # Medical --------------------------------------------------------------
    (
        ("hipaa", "mib", "aps", "paramedical", "medical exam", "medical record", "health questionnaire",
         "medical declaration", "medical questionnaire", "medical test", "medical history", "family medical history",
         "rx database", "physician statement", "chronic condition", "diagnosis or dual", "medical"),
        "Supports medical underwriting, class assignment, and rating.",
    ),
    # Financial ------------------------------------------------------------
    (
        ("financial statement", "financials", "p&l", "profit", "balance sheet", "tax return", "income proof",
         "w-2", "pay stub", "scale of finance", "turnover", "financial projection", "audited", "due diligence",
         "quality of earnings", "cap table", "funding round", "investor rights", "term sheet", "sec filings",
         "10-k", "def 14a", "8-k", "capitalization", "surplus plan", "collateral", "letter of credit",
         "bank reference", "credit line", "company financial", "source of funds", "funding source", "1098-q",
         "payroll", "class code", "ncci", "gross sales", "surety", "bond", "actuarial", "business income",
         "bi worksheet", "accounts receivable", "backlog", "work-on-hand", "e-mod", "experience modification",
         "emr", "audit", "cpa", "credit management", "monthly expense"),
        "Supports valuation, financial underwriting, and premium-affordability assessment.",
    ),
    # Ownership / lender interest -----------------------------------------
    (
        ("lease", "title deed", "title", "encumbrance", "rent roll", "ownership", "sale deed", "registry",
         "property tax", "land ownership", "tenancy", "khasra", "khatauni", "7-12", "property document",
         "loan", "mortgage", "lender", "sanction letter", "credit account", "loan account", "financing"),
        "Confirms insurable interest, ownership, and the lender's interest.",
    ),
    # Values / valuation ---------------------------------------------------
    (
        ("sov", "statement of values", "cope", "appraisal", "valuation", "replacement cost", "reconstruction",
         "building spec", "building and contents", "location schedule", "tiv", "equipment schedule", "asset list",
         "stock / inventory", "inventory statement", "customer vehicle values", "insured items"),
        "Validates the sum insured, valuation basis, and limit adequacy.",
    ),
    # Invoice / condition --------------------------------------------------
    (
        ("invoice", "purchase receipt", "depreciation schedule", "age and service", "manufacturer spec",
         "warranty document"),
        "Documents the value, age, and condition of the insured property/equipment.",
    ),
    (("acord",), "Standardized application and underwriting data for the line."),
    # Cyber / security controls -------------------------------------------
    (
        ("cyber", "security questionnaire", "incident", "soc 2", "penetration test", "vulnerability",
         "backup and disaster", "disaster recovery", "continuity plan", "it infrastructure", "data inventory",
         "details of data", "data handled", "network &", "network details", "mfa", "edr", "security measures",
         "security protocols", "security / id-check", "background check", "cash handling", "internal control",
         "breach", "political violence", "security and travel", "crime controls"),
        "Assesses control maturity and cyber/security exposure quality.",
    ),
    # Inspection / quality / protection -----------------------------------
    (
        ("inspection", "photos", "survey", "peer review", "qa/qc", "quality control", "quality certification",
         "quality / risk management", "risk management procedures", "traceability", "lot-tracking",
         "manufacturing/quality", "fire protection", "sprinkler", "alarm", "hydrant", "fact-check",
         "certificates of compliance", "warning label", "sds", "technician certification"),
        "Confirms condition, occupancy, and protection exactly as rated.",
    ),
    # Catastrophe zone -----------------------------------------------------
    (
        ("flood zone", "elevation certificate", "fema", "seismic", "fault line", "flood / wind", "retrofit",
         "reinforcement", "aggregation"),
        "Confirms the catastrophe zone, siting, and mitigation for rating.",
    ),
    # Identity / KYC -------------------------------------------------------
    (
        ("photo id", "identity", "address proof", "proof of address", "ssn", "social security", "passport",
         "date-of-birth", "dob", "photo", "kyc", "aadhaar", "pan card", "pan number", "e-kyc", "nominee id"),
        "KYC / identity verification and anti-fraud.",
    ),
    # Dependency / relationship -------------------------------------------
    (
        ("birth certificate", "marriage certificate", "proof of relationship", "dependent", "disability certification",
         "nominee", "spouse", "beneficiary"),
        "Verifies dependency, relationship, and the beneficiary arrangement.",
    ),
    (("age proof", "proof of age"), "Confirms the insured's age for rating and eligibility."),
    # Operator / motor / subject matter ------------------------------------
    (
        ("driving license", "driving licence", "driver's license", "driver licence", "driving record", "mvr",
         "driving", "delivery / sales driver", "driver count", "hired auto", "personal auto"),
        "Verifies licensing and the driving exposure/experience of the operator.",
    ),
    (
        ("aircraft", "pilot", "crew", "hangar", "airworthiness", "n-number"),
        "Confirms the aircraft, crew, and aviation exposure.",
    ),
    (
        ("vessel", "hull", "p&i", "cargo", "bill of lading", "airway bill", "packing list", "cargo manifest",
         "commodity list", "voyage", "route plan", "refrigeration", "importer / exporter", "iec certificate",
         "classification society", "seaworthiness"),
        "Confirms the goods/vessel, route, and transit documentation.",
    ),
    (
        ("rc ", "rc of", "registration certificate", "chassis", "engine number", "fitness certificate", "permit copy",
         "puc", "dealer plate", "vehicle schedule", "vin", "garaging", "power units", "auto / fleet", "fleet schedule",
         "radius", "lane information", "usage description", "use description", "geographic limits", "usage/location"),
        "Establishes the subject-matter identity and road-legality (motor) and the operating radius.",
    ),
    # Crop / animal --------------------------------------------------------
    (
        ("weather", "index", "station", "notified", "crop", "sowing", "production record", "rma", "aph", "yield",
         "farming"),
        "Confirms the notified crop/area or the parametric weather-index basis.",
    ),
    (
        ("vaccination", "health certificate", "ear-tag", "microchip", "breed", "veterinary", "biosecurity",
         "husbandry", "livestock", "identification"),
        "Verifies animal identity, health, and value.",
    ),
    # Event / travel -------------------------------------------------------
    (
        ("budget", "itinerary", "visa", "permit", "event description", "venue", "booking agreement", "vendor",
         "artist", "host contract", "concession", "travel schedule", "alcohol", "server training", "tips",
         "servsafe", "advance payment"),
        "Confirms the event/travel exposure, authority, and itinerary.",
    ),
    # Subcontractor / COI --------------------------------------------------
    (
        ("subcontractor", "1099", "certificate of insurance", "coi requirement", "additional insured", "subcontracted"),
        "Confirms subcontractor insurance and risk-transfer via certificates of insurance (COI).",
    ),
    # Construction / project ----------------------------------------------
    (
        ("construction", "project", "wrap-up", "ocip", "ccip", "site plan", "blueprint", "structural", "soil report",
         "building code", "code requirement", "building age", "ordinance", "contractor", "design contract"),
        "Confirms the project scope, schedule, and construction risk.",
    ),
    # Environmental --------------------------------------------------------
    (
        ("environmental", "phase i", "phase ii", "esa", "waste disposal", "chemicals", "hazardous", "pollution",
         "epa", "site assessment"),
        "Assesses environmental and pollution exposure and controls.",
    ),
    # Safety / maintenance -------------------------------------------------
    (
        ("safety", "osha", "maintenance", "return-to-work", "absence management", "telematics", "fleet safety",
         "crisis / recall response", "recall response", "response plan", "theft prevention", "gps", "lot security",
         "keys control"),
        "Confirms safety, maintenance, and loss-prevention/risk-management programs.",
    ),
    # Equipment breakdown --------------------------------------------------
    (
        ("boiler", "pressure vessel", "equipment breakdown", "hvac"),
        "Confirms equipment condition, age, and inspection/maintenance history.",
    ),
    # Underlying / excess --------------------------------------------------
    (
        ("underlying", "self-maintained", "attachment", "fronting", "proposed sir", "deductible schedule"),
        "Documents the primary/underlying program, limits, and attachment point.",
    ),
    # Benefits / group plan ------------------------------------------------
    (
        ("plan document", "form 5500", "erisa", "plan asset", "plan administrator", "trustee", "participation",
         "benefit schedule", "current plan", "plan design", "stop-loss", "contribution", "eligibility rules",
         "voluntary benefits", "rfp", "evidence of insurability", "census", "roster", "employee count",
         "insured persons", "service certificate"),
        "Documents the benefit-plan design, participation, and funding structure.",
    ),
    # Corporate / authority ------------------------------------------------
    (
        ("license", "entity formation", "organizational chart", "organization chart", "registration",
         "operating authority", "authorization", "bureau", "articles of incorporation", "bylaws",
         "corporate resolution", "governance", "board", "bios", "resumes", "corporate structure",
         "ownership structure", "corporate", "government employer verification", "regulatory approval",
         "ip portfolio", "freedom-to-operate", "take-down", "retraction", "consultant"),
        "Confirms legal capacity, licensing, ownership, and authority to bind.",
    ),
    # Reinsurance / cession ------------------------------------------------
    (("treaty", "facultative", "ceding", "reinsurance", "cession", "expected premium volume", "portfolio profile"),
     "Documents the reinsurance structure and the ceding insurer's profile."),
    # Banking / payout -----------------------------------------------------
    (("bank account", "ach", "custodian transfer", "payout", "wire instruction", "direct deposit"),
     "Provides payout, premium-payment, and settlement instructions."),
    # Disclosure / options -------------------------------------------------
    (("illustration acknowledgment", "dividend option", "bonus option", "graded benefit disclosure",
      "premium waiver rider disclosure", "election form", "disclosure"),
     "Acknowledges product disclosures and elected policy options."),
    # Contracts ------------------------------------------------------------
    (("contract", "engagement letter", "msa", "sla", "sale / payment terms", "terms of sale", "force-majeure",
      "buy-sell", "purchase / merger", "merger & acquisition", "disclosure letter", "disclosure schedule",
      "sample client", "employment contract", "handbook", "hr polic", "indemnity", "vendor/third-party"),
     "Reviews contractual obligations, indemnities, and risk-transfer terms."),
    # Operations / exposure description ------------------------------------
    (
        ("description of operations", "operations description", "description of services", "details of services",
         "operations mix", "occupancy", "revenue by", "revenue breakdown", "business description",
         "product / saas", "product / technology description", "product details", "product list", "products by",
         "service line", "description of", "sales by", "sku", "supplier", "supply chain", "contingent", "customer",
         "marketing materials", "requested coverage", "sales breakdown", "gl operations", "competitor",
         "hours of operation", "content description", "sourcing", "supply-chain"),
        "Describes the operations, products, and exposures being underwritten.",
    ),
    # Catch-all application ------------------------------------------------
    (("application", "proposal form"), "Standard application; establishes the risk, requested cover, and applicant disclosures."),
    # Eligibility / subsidy ------------------------------------------------
    (("household income", "tax credit", "coverage details", "enrollment", "special enrollment", "affordability exemption"),
     "Verifies eligibility, subsidy, and enrollment-period compliance."),
]


def doc_purpose(doc: str) -> str:
    text = f" {doc.lower()} "
    for keys, purpose in DOC_PURPOSE_RULES:
        for key in keys:
            if key in text:
                return purpose
    return "Required to assess eligibility, pricing, and terms for this line."


def get_category_rules(
    lob_slug: str, category_id: str, product_id: str | None = None
) -> dict[str, list[str] | str]:
    lob = KNOWLEDGE_BASE.get(lob_slug, {})
    rules = lob.get(category_id)
    if rules is None:
        for value in lob.values():
            if value.get("category_ids") and category_id in value["category_ids"]:
                rules = value
                break
    if rules is None:
        rules = {
            "market": "Standard eligible submissions for this line of business.",
            "eligible": ["Meets the filed product eligibility rules and program appetite."],
            "decline": ["Any risk on the carrier exclusion or decline list."],
            "exclusions": ["Standard policy exclusions apply; refer to the filed form."],
            "endorsements": ["Only filed endorsements may be attached."],
            "limits": ["Limits per the filed product schedule and program capacity."],
            "rating": ["Filed rate/rule for the class plus applicable debits and credits."],
            "refer": ["Any non-standard term or exposure outside filed rules."],
        }
    else:
        rules = dict(rules)
    if product_id:
        override = PRODUCT_OVERRIDES.get(f"{lob_slug}/{product_id}")
        if override:
            rules.update(override)
    return rules
