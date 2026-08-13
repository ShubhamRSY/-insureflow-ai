"""General / Non-Life + specialty catalog: taxonomy, document packs, UW workflow.

India-style motor, home, travel, marine, fire, liability, cyber, crop, livestock,
pet, event, title, mortgage GI, and insurer/reinsurer channel overlays.
US commercial GL/cyber/marine stay on the commercial hub; this hub is the
retail + specialty tree with per-leaf checklists. Catalog until filed rates exist.
"""

from __future__ import annotations

import re
from typing import Any

from insureflow.insurance.commercial_lobs import _coverage, _normalize_coverages, flatten_line_documents
from insureflow.underwriting.general_product import LIVE_GENERAL_PRODUCT_IDS

GENERAL_UW_RESPONSIBILITIES: list[dict[str, str]] = [
    {"id": "eligibility", "title": "Eligibility & KYC / entity KYC", "summary": "Verify proposer identity or company registration before peril UW."},
    {"id": "subject", "title": "Subject-matter proof", "summary": "Vehicle RC, property title, cargo docs, land records, animal ID — whatever the leaf requires."},
    {"id": "peril", "title": "Peril & cover type", "summary": "TP vs comprehensive, structure vs contents, yield vs weather, breach vs ransomware."},
    {"id": "history", "title": "Prior cover & claims", "summary": "NCB transfer, lapse inspection, loss history, cyber incidents, product recalls."},
    {"id": "decision", "title": "Decision", "summary": "Accept, condition, refer, or decline. Catalog products are not auto-rated."},
]

GENERAL_CATEGORIES: list[dict[str, str]] = [
    {"id": "motor", "name": "Motor Insurance", "summary": "Car, two-wheeler, and commercial vehicle — TP-only vs comprehensive."},
    {"id": "home", "name": "Home / Property Insurance", "summary": "Structure-only, contents-only, and comprehensive home."},
    {"id": "travel", "name": "Travel Insurance", "summary": "Domestic vs international (passport/visa/itinerary)."},
    {"id": "marine", "name": "Marine Insurance", "summary": "Cargo (goods in transit) vs hull (vessel)."},
    {"id": "fire", "name": "Fire Insurance", "summary": "Residential SFSP vs commercial/industrial fire."},
    {"id": "liability", "name": "Liability Insurance", "summary": "Professional indemnity, public liability, product liability."},
    {"id": "cyber", "name": "Cyber Insurance", "summary": "Data breach vs cyberattack / ransomware."},
    {"id": "crop", "name": "Crop Insurance", "summary": "Yield-based (PMFBY-type) vs weather-index."},
    {"id": "animal", "name": "Livestock & Pet", "summary": "Cattle/livestock vs companion pet."},
    {"id": "event", "name": "Event Insurance", "summary": "Wedding vs concert / public event."},
    {"id": "title", "name": "Title Insurance", "summary": "Legal title chain, encumbrance, title search."},
    {"id": "mortgage_gi", "name": "Mortgage Insurance", "summary": "Lender-linked cover on the mortgaged property / loan."},
    {"id": "provider", "name": "By Provider Type", "summary": "PSU vs private purchase KYC, and B2B reinsurance (not individual KYC)."},
]


def _line(
    *,
    id: str,
    slug: str,
    name: str,
    short_name: str,
    category_id: str,
    checklist_lob: str,
    description: str,
    uw_focus: str,
    documents: list[str],
    coverages: list[dict[str, Any]] | None = None,
    base_packet: list[str] | None = None,
) -> dict[str, Any]:
    docs = [str(d).strip() for d in documents if str(d).strip()]
    base = list(base_packet or [])
    covs = _normalize_coverages(coverages)
    return {
        "id": id,
        "slug": slug,
        "name": name,
        "short_name": short_name,
        "category_id": category_id,
        "checklist_lob": checklist_lob,
        "insurance_line": "general",
        "rating_line": "general",
        "description": description,
        "uw_focus": uw_focus,
        "acord_forms": [],
        "documents": docs,
        "additional_documents": [d for d in docs if d not in base],
        "base_packet": base,
        "coverages": covs,
        "status": "catalog",
    }


def _cov(cid: str, name: str, *docs: str) -> dict[str, Any]:
    return _coverage(cid, name, *docs)


GENERAL_LINES: list[dict[str, Any]] = [
    # ── 1. Motor ──────────────────────────────────────────────────────────
    _line(
        id="car_tp",
        slug="car-tp",
        name="Car Insurance — Third-Party Only",
        short_name="Car TP",
        category_id="motor",
        checklist_lob="car_tp",
        description="Statutory third-party motor — RC, owner KYC, DL. No own-damage inspection.",
        uw_focus="RC + DL + owner KYC. Chassis/engine on RC. Prior policy only if renewal.",
        documents=[
            "RC (Registration Certificate) of vehicle",
            "ID + address proof of owner",
            "Driving license",
            "Previous insurance policy copy (if renewal)",
            "Vehicle chassis / engine number details",
        ],
        coverages=[_cov("car_tp_std", "Car Third-Party Only", "Vehicle chassis / engine number details")],
    ),
    _line(
        id="car_comprehensive",
        slug="car-comprehensive",
        name="Car Insurance — Comprehensive",
        short_name="Car Comprehensive",
        category_id="motor",
        checklist_lob="car_comprehensive",
        description="Own-damage + TP. NCB needs prior policy; lapse/pre-owned needs inspection; new vehicle needs invoice.",
        uw_focus="NCB only with prior policy. Inspection if pre-owned or lapsed. Invoice if new.",
        documents=[
            "RC of vehicle",
            "ID + address proof",
            "Driving license",
            "Previous policy copy (for no-claim bonus transfer)",
            "Vehicle inspection report / photos (for pre-owned / renewal after lapse)",
            "Invoice copy (for new vehicle)",
        ],
        coverages=[
            _cov("car_comp_new", "New Car Comprehensive", "Invoice copy (for new vehicle)"),
            _cov("car_comp_used", "Pre-owned / Lapsed Comprehensive", "Vehicle inspection report / photos (for pre-owned / renewal after lapse)", "Previous policy copy (for no-claim bonus transfer)"),
        ],
    ),
    _line(
        id="tw_tp",
        slug="two-wheeler-tp",
        name="Two-Wheeler Insurance — Third-Party Only",
        short_name="Two-Wheeler TP",
        category_id="motor",
        checklist_lob="tw_tp",
        description="Statutory TP for motorcycle / scooter.",
        uw_focus="RC + DL + owner KYC. No OD inspection on TP-only.",
        documents=[
            "RC of vehicle",
            "ID + address proof",
            "Driving license",
            "Previous policy copy (if renewal)",
        ],
        coverages=[_cov("tw_tp_std", "Two-Wheeler Third-Party Only", "Previous policy copy (if renewal)")],
    ),
    _line(
        id="tw_comprehensive",
        slug="two-wheeler-comprehensive",
        name="Two-Wheeler Insurance — Comprehensive",
        short_name="Two-Wheeler Comprehensive",
        category_id="motor",
        checklist_lob="tw_comprehensive",
        description="Two-wheeler OD + TP. NCB + photos/invoice as applicable.",
        uw_focus="NCB from prior policy. Photos if used; invoice if new.",
        documents=[
            "RC of vehicle",
            "ID + address proof",
            "Driving license",
            "Previous policy copy (NCB transfer)",
            "Vehicle photos / inspection (if applicable)",
            "Invoice copy (for new vehicle)",
        ],
        coverages=[
            _cov("tw_comp_new", "New Two-Wheeler Comprehensive", "Invoice copy (for new vehicle)"),
            _cov("tw_comp_used", "Used Two-Wheeler Comprehensive", "Vehicle photos / inspection (if applicable)", "Previous policy copy (NCB transfer)"),
        ],
    ),
    _line(
        id="cv_tp",
        slug="commercial-vehicle-tp",
        name="Commercial Vehicle Insurance — Third-Party Only",
        short_name="CV TP",
        category_id="motor",
        checklist_lob="cv_tp",
        description="Goods/passenger CV statutory TP — fitness, permit, PUC.",
        uw_focus="Fitness + permit + PUC are mandatory. Do not rate as private car TP.",
        documents=[
            "RC of vehicle",
            "Fitness certificate",
            "Permit copy (national / state permit)",
            "ID + address proof of owner",
            "Driving license of driver",
            "PUC (Pollution Under Control) certificate",
        ],
        coverages=[_cov("cv_tp_std", "Commercial Vehicle Third-Party Only", "Fitness certificate", "Permit copy (national / state permit)", "PUC (Pollution Under Control) certificate")],
    ),
    _line(
        id="cv_comprehensive",
        slug="commercial-vehicle-comprehensive",
        name="Commercial Vehicle Insurance — Comprehensive",
        short_name="CV Comprehensive",
        category_id="motor",
        checklist_lob="cv_comprehensive",
        description="CV OD + TP. Fitness, permit, PUC, NCB, inspection.",
        uw_focus="Same statutory pack as CV TP plus NCB + inspection. Occupation/use affects OD.",
        documents=[
            "RC of vehicle",
            "Fitness certificate",
            "Permit copy",
            "ID + address proof",
            "Driving license",
            "PUC certificate",
            "Previous policy copy (NCB transfer)",
            "Vehicle inspection report",
        ],
        coverages=[_cov("cv_comp_std", "Commercial Vehicle Comprehensive", "Previous policy copy (NCB transfer)", "Vehicle inspection report")],
    ),
    # ── 2. Home ───────────────────────────────────────────────────────────
    _line(
        id="home_structure",
        slug="home-structure",
        name="Home Structure-only Cover",
        short_name="Home Structure",
        category_id="home",
        checklist_lob="home_structure",
        description="Building only — ownership, valuation, tax, exterior photos.",
        uw_focus="Sale deed / registry required. No contents schedule on this leaf.",
        documents=[
            "Property ownership proof (sale deed / registry)",
            "ID + address proof",
            "Property valuation report / construction cost estimate",
            "Property tax receipt",
            "Photographs of property",
        ],
        coverages=[_cov("home_structure_std", "Structure Only", "Property ownership proof (sale deed / registry)", "Property valuation report / construction cost estimate")],
    ),
    _line(
        id="home_contents",
        slug="home-contents",
        name="Home Contents-only Cover",
        short_name="Home Contents",
        category_id="home",
        checklist_lob="home_contents",
        description="Movables only — inventory + invoices for high-value items. No deed required.",
        uw_focus="Item schedule + invoices for jewelry/electronics. Do not require sale deed.",
        documents=[
            "ID + address proof",
            "List of insured items with value (jewelry, electronics, furniture)",
            "Purchase invoices / bills of high-value items",
            "Photographs of contents",
        ],
        coverages=[_cov("home_contents_std", "Contents Only", "List of insured items with value (jewelry, electronics, furniture)", "Purchase invoices / bills of high-value items")],
    ),
    _line(
        id="home_comprehensive",
        slug="home-comprehensive",
        name="Structure + Contents (Comprehensive Home)",
        short_name="Home Comprehensive",
        category_id="home",
        checklist_lob="home_comprehensive",
        description="Building + contents — deed, valuation, inventory, tax, interior + exterior photos.",
        uw_focus="Both ownership and contents schedule. Interior + exterior photos.",
        documents=[
            "Property ownership proof",
            "ID + address proof",
            "Property valuation report",
            "List + invoices of insured contents",
            "Property tax receipt",
            "Photographs (interior + exterior)",
        ],
        coverages=[_cov("home_comp_std", "Structure + Contents", "Property ownership proof", "List + invoices of insured contents")],
    ),
    # ── 3. Travel ─────────────────────────────────────────────────────────
    _line(
        id="travel_domestic",
        slug="travel-domestic",
        name="Domestic Travel Insurance",
        short_name="Domestic Travel",
        category_id="travel",
        checklist_lob="travel_domestic",
        description="India travel — itinerary/ticket. Passport not required.",
        uw_focus="Itinerary/ticket dates. Do not require passport/visa.",
        documents=[
            "ID + address proof",
            "Age proof",
            "Travel itinerary / ticket",
            "Photograph",
        ],
        coverages=[_cov("travel_domestic_std", "Domestic Travel", "Travel itinerary / ticket")],
    ),
    _line(
        id="travel_international",
        slug="travel-international",
        name="International Travel Insurance",
        short_name="International Travel",
        category_id="travel",
        checklist_lob="travel_international",
        description="Overseas trip — passport mandatory, visa + itinerary.",
        uw_focus="Passport knockout if missing. Cover follows itinerary dates.",
        documents=[
            "Passport (mandatory)",
            "Visa copy",
            "Travel itinerary / flight ticket",
            "ID + address proof (home country)",
            "Age proof",
            "Photograph",
        ],
        coverages=[_cov("travel_intl_std", "International Travel", "Passport (mandatory)", "Visa copy", "Travel itinerary / flight ticket")],
    ),
    # ── 4. Marine ─────────────────────────────────────────────────────────
    _line(
        id="marine_cargo",
        slug="marine-cargo",
        name="Marine Cargo Insurance",
        short_name="Marine Cargo",
        category_id="marine",
        checklist_lob="marine_cargo",
        description="Goods in transit — invoice, B/L or AWB, packing list, IEC, GST. Not individual KYC-only.",
        uw_focus="Invoice + bill of lading/AWB + packing list. IEC + GST for exporter/importer.",
        documents=[
            "Invoice of goods being shipped",
            "Bill of lading / airway bill",
            "Packing list",
            "Importer / exporter code (IEC certificate)",
            "Letter of credit (if applicable)",
            "Company registration / GST certificate",
        ],
        coverages=[_cov("marine_cargo_std", "Cargo in Transit", "Invoice of goods being shipped", "Bill of lading / airway bill", "Packing list")],
        base_packet=[],
    ),
    _line(
        id="marine_hull",
        slug="marine-hull",
        name="Marine Hull Insurance",
        short_name="Marine Hull",
        category_id="marine",
        checklist_lob="marine_hull",
        description="Vessel hull — registration, class/seaworthiness, valuation, crew, owner company.",
        uw_focus="Classification society certificate is seaworthiness. Do not rate as cargo.",
        documents=[
            "Ship / vessel registration certificate",
            "Vessel valuation report",
            "Classification society certificate (seaworthiness)",
            "Ownership proof of vessel",
            "Crew list & certification",
            "Company registration documents (of ship owner)",
        ],
        coverages=[_cov("marine_hull_std", "Hull & Machinery", "Classification society certificate (seaworthiness)", "Crew list & certification")],
        base_packet=[],
    ),
    # ── 5. Fire ───────────────────────────────────────────────────────────
    _line(
        id="fire_residential",
        slug="fire-residential",
        name="Standard Fire & Allied Perils (Residential)",
        short_name="Fire Residential",
        category_id="fire",
        checklist_lob="fire_residential",
        description="SFSP on a dwelling — ownership, valuation, photos.",
        uw_focus="Residential fire, not industrial occupancy. Ownership + valuation.",
        documents=[
            "Property ownership proof",
            "ID + address proof",
            "Property valuation report",
            "Photographs of property",
        ],
        coverages=[_cov("fire_res_std", "Residential SFSP", "Property ownership proof", "Property valuation report")],
    ),
    _line(
        id="fire_commercial",
        slug="fire-commercial",
        name="Fire Insurance — Commercial / Industrial",
        short_name="Fire Commercial",
        category_id="fire",
        checklist_lob="fire_commercial",
        description="Factory/commercial fire — GST, asset valuation, fire safety cert, stock.",
        uw_focus="Fire safety compliance + stock/inventory. Occupancy is industrial/commercial.",
        documents=[
            "Property / factory ownership or lease documents",
            "Company registration / GST certificate",
            "Asset valuation report (building + machinery + stock)",
            "Fire safety compliance certificate",
            "Stock / inventory statement",
            "Photographs of premises",
        ],
        coverages=[_cov("fire_comm_std", "Commercial / Industrial Fire", "Fire safety compliance certificate", "Stock / inventory statement")],
        base_packet=[],
    ),
    # ── 6. Liability ──────────────────────────────────────────────────────
    _line(
        id="professional_indemnity_gi",
        slug="professional-indemnity",
        name="Professional Indemnity Insurance",
        short_name="Professional Indemnity",
        category_id="liability",
        checklist_lob="professional_indemnity_gi",
        description="PI for licensed professionals (medical / legal / CA).",
        uw_focus="Professional license is mandatory. Services offered + claims history.",
        documents=[
            "Professional license / registration certificate (e.g. medical / legal / CA license)",
            "ID + address proof",
            "Business / practice registration proof",
            "Details of services offered",
            "Past claims history (if any)",
        ],
        coverages=[_cov("pi_std", "Professional Indemnity", "Professional license / registration certificate (e.g. medical / legal / CA license)", "Details of services offered")],
    ),
    _line(
        id="public_liability_gi",
        slug="public-liability",
        name="Public Liability Insurance",
        short_name="Public Liability",
        category_id="liability",
        checklist_lob="public_liability_gi",
        description="Premises/public liability — GST, premises, nature of business, safety, claims.",
        uw_focus="Nature of business + premises. Safety certs if applicable.",
        documents=[
            "Company registration / GST certificate",
            "Business premises ownership / lease proof",
            "Nature of business declaration",
            "Safety compliance certificates (if applicable)",
            "Past claims history",
        ],
        coverages=[_cov("public_liab_std", "Public Liability", "Nature of business declaration", "Business premises ownership / lease proof")],
        base_packet=[],
    ),
    _line(
        id="product_liability_gi",
        slug="product-liability-gi",
        name="Product Liability Insurance",
        short_name="Product Liability",
        category_id="liability",
        checklist_lob="product_liability_gi",
        description="Product liability — catalog, manufacturing license, ISO/BIS, recall history.",
        uw_focus="Manufacturing license + product catalog. Recall history is a knockout/refer.",
        documents=[
            "Company registration / GST certificate",
            "Product details / catalog",
            "Manufacturing license",
            "Quality certification (ISO / BIS, if applicable)",
            "Past claims / product recall history",
        ],
        coverages=[_cov("prod_liab_std", "Product Liability", "Manufacturing license", "Product details / catalog")],
        base_packet=[],
    ),
    # ── 7. Cyber ──────────────────────────────────────────────────────────
    _line(
        id="cyber_data_breach",
        slug="cyber-data-breach",
        name="Cyber Insurance — Data Breach Cover",
        short_name="Data Breach",
        category_id="cyber",
        checklist_lob="cyber_data_breach",
        description="First/third-party data breach — security policy, data volume, incident history.",
        uw_focus="Data volume + security policy. Audit optional; incident history drives refer.",
        documents=[
            "Company registration / GST certificate",
            "IT infrastructure details / data security policy",
            "Details of data handled (customer / employee data volume)",
            "Past cyber incident history (if any)",
            "Cybersecurity audit report (if available)",
        ],
        coverages=[_cov("cyber_breach_std", "Data Breach", "IT infrastructure details / data security policy", "Details of data handled (customer / employee data volume)")],
        base_packet=[],
    ),
    _line(
        id="cyber_ransomware",
        slug="cyber-ransomware",
        name="Cyber Insurance — Cyberattack / Ransomware Cover",
        short_name="Ransomware",
        category_id="cyber",
        checklist_lob="cyber_ransomware",
        description="Ransomware / cyberattack — network details, existing controls, incident history.",
        uw_focus="Existing cybersecurity measures. Do not treat as data-breach-only wording.",
        documents=[
            "Company registration / GST certificate",
            "IT infrastructure & network details",
            "Existing cybersecurity measures declaration",
            "Past incident / breach history",
            "Cybersecurity audit report (if available)",
        ],
        coverages=[_cov("cyber_ransom_std", "Cyberattack / Ransomware", "Existing cybersecurity measures declaration", "IT infrastructure & network details")],
        base_packet=[],
    ),
    # ── 8. Crop ───────────────────────────────────────────────────────────
    _line(
        id="crop_yield",
        slug="crop-yield",
        name="Yield-based Crop Insurance (PMFBY-type)",
        short_name="Crop Yield",
        category_id="crop",
        checklist_lob="crop_yield",
        description="Yield/PMFBY-style — land record, Aadhaar, bank, sowing, acreage, crop-loan link.",
        uw_focus="Land + sowing + survey/acreage. Bank for subsidy/payout. Loan account if crop loan.",
        documents=[
            "Land ownership / tenancy proof (khasra / khatauni / 7-12 extract)",
            "ID + address proof (Aadhaar mandatory in most schemes)",
            "Bank account details (for subsidy / payout credit)",
            "Sowing certificate (proof of crop sown)",
            "Land area details (survey number, acreage)",
            "Loan account details (if farmer has crop loan, insurance often auto-linked)",
        ],
        coverages=[_cov("crop_yield_std", "Yield-based / PMFBY-type", "Sowing certificate (proof of crop sown)", "Land area details (survey number, acreage)")],
        base_packet=[],
    ),
    _line(
        id="crop_weather",
        slug="crop-weather",
        name="Weather-based Crop Insurance",
        short_name="Crop Weather",
        category_id="crop",
        checklist_lob="crop_weather",
        description="Weather-index — land, KYC, bank, sowing, nearest weather station reference.",
        uw_focus="Weather station reference is the index. Do not require yield history.",
        documents=[
            "Land ownership / tenancy proof",
            "ID + address proof",
            "Bank account details",
            "Sowing certificate",
            "Nearest weather station reference (for indexed payout)",
        ],
        coverages=[_cov("crop_weather_std", "Weather-index Crop", "Nearest weather station reference (for indexed payout)", "Sowing certificate")],
        base_packet=[],
    ),
    # ── 9. Animal ─────────────────────────────────────────────────────────
    _line(
        id="livestock_cattle",
        slug="livestock-cattle",
        name="Livestock / Cattle Insurance",
        short_name="Livestock / Cattle",
        category_id="animal",
        checklist_lob="livestock_cattle",
        description="Cattle/livestock — vet health cert, tag/photo/microchip, ownership, valuation.",
        uw_focus="Animal ID + vet health + valuation. Not pet companion wording.",
        documents=[
            "ID + address proof of owner",
            "Animal health certificate (from veterinarian)",
            "Animal identification (tag number / photo / microchip if applicable)",
            "Ownership proof of animal (purchase receipt)",
            "Valuation certificate (by vet or authorized valuer)",
            "Photographs of animal",
        ],
        coverages=[_cov("livestock_std", "Livestock / Cattle", "Animal health certificate (from veterinarian)", "Animal identification (tag number / photo / microchip if applicable)")],
    ),
    _line(
        id="pet_insurance",
        slug="pet-insurance",
        name="Pet Insurance",
        short_name="Pet",
        category_id="animal",
        checklist_lob="pet_insurance",
        description="Companion pet — vaccination, medical history, breed/age, photo.",
        uw_focus="Vaccination record + breed/age. Do not require livestock tag/valuation.",
        documents=[
            "ID + address proof of owner",
            "Pet's vaccination record",
            "Pet's medical history / health certificate",
            "Breed & age proof (vet certificate / adoption papers)",
            "Photograph of pet",
        ],
        coverages=[_cov("pet_std", "Companion Pet", "Pet's vaccination record", "Breed & age proof (vet certificate / adoption papers)")],
    ),
    # ── 10. Event ─────────────────────────────────────────────────────────
    _line(
        id="wedding_insurance",
        slug="wedding-insurance",
        name="Wedding Insurance",
        short_name="Wedding",
        category_id="event",
        checklist_lob="wedding_insurance",
        description="Wedding cancellation/liability — date/venue/budget, vendor contracts, advances.",
        uw_focus="Event date + vendor contracts + advance receipts for cancellation cover.",
        documents=[
            "ID + address proof of proposer",
            "Event details (date, venue, budget breakdown)",
            "Vendor contracts (venue, caterer, decorator)",
            "Advance payment receipts (for cancellation cover)",
        ],
        coverages=[_cov("wedding_std", "Wedding Event", "Event details (date, venue, budget breakdown)", "Vendor contracts (venue, caterer, decorator)")],
    ),
    _line(
        id="concert_event_insurance",
        slug="concert-event",
        name="Concert / Public Event Insurance",
        short_name="Concert / Public Event",
        category_id="event",
        checklist_lob="concert_event_insurance",
        description="Public event — organizer GST, venue, local permit, artist contracts, ticket projection.",
        uw_focus="Event license/permit from local authority. Ticket projection for attendance risk.",
        documents=[
            "Event organizer's business registration / GST",
            "Venue booking agreement",
            "Event license / permit from local authority",
            "Artist / vendor contracts",
            "Estimated budget & ticket sales projection",
        ],
        coverages=[_cov("concert_std", "Concert / Public Event", "Event license / permit from local authority", "Venue booking agreement")],
        base_packet=[],
    ),
    # ── 11. Title ─────────────────────────────────────────────────────────
    _line(
        id="title_insurance_gi",
        slug="title-insurance",
        name="Title Insurance",
        short_name="Title",
        category_id="title",
        checklist_lob="title_insurance_gi",
        description="Legal title risk — deed chain, encumbrance, tax, survey, title search. Not motor/health KYC pattern.",
        uw_focus="Encumbrance certificate + title search report are core. Ownership chain 12–30 years.",
        documents=[
            "Property sale deed / title deed",
            "Property ownership chain documents (past 12–30 years records)",
            "Encumbrance certificate",
            "Property tax receipts",
            "Survey / site plan of property",
            "ID + address proof of owner",
            "Legal title search report (by insurer's lawyer / title company)",
        ],
        coverages=[
            _cov(
                "title_std",
                "Title / Legal Defect",
                "Encumbrance certificate",
                "Legal title search report (by insurer's lawyer / title company)",
                "Property ownership chain documents (past 12–30 years records)",
            )
        ],
    ),
    # ── 12. Mortgage GI ───────────────────────────────────────────────────
    _line(
        id="mortgage_insurance_gi",
        slug="mortgage-insurance-gi",
        name="Mortgage Insurance",
        short_name="Mortgage GI",
        category_id="mortgage_gi",
        checklist_lob="mortgage_insurance_gi",
        description="Cover linked to a housing loan — sanction letter, property, income, loan statement.",
        uw_focus="Loan sanction + loan account. Distinct from the mortgage-lending vertical.",
        documents=[
            "ID + address proof",
            "Loan sanction letter (from bank / lender)",
            "Property documents (linked to the mortgage)",
            "Income proof (salary slips / ITR)",
            "Age proof",
            "Loan account statement",
        ],
        coverages=[_cov("mortgage_gi_std", "Mortgage / Lender-linked", "Loan sanction letter (from bank / lender)", "Loan account statement")],
    ),
    # ── 13. Provider overlays ─────────────────────────────────────────────
    _line(
        id="insurer_psu",
        slug="insurer-psu",
        name="Public Sector Insurer (Government-backed) — Purchase KYC",
        short_name="PSU Insurer KYC",
        category_id="provider",
        checklist_lob="insurer_psu",
        description="Govt-format KYC overlay — Aadhaar-linked verification; category cert if subsidy scheme.",
        uw_focus="Aadhaar-linked KYC. Category certificate when scheme has caste/income subsidy (e.g. crop).",
        documents=[
            "ID + address proof (govt-format KYC compliance)",
            "Age proof",
            "Photograph",
            "Aadhaar-linked verification (often mandatory for govt schemes / subsidies)",
            "Category certificate (if scheme has caste / income-based subsidy, e.g. crop insurance)",
        ],
        coverages=[_cov("psu_kyc_std", "PSU Purchase KYC", "Aadhaar-linked verification (often mandatory for govt schemes / subsidies)")],
    ),
    _line(
        id="insurer_private",
        slug="insurer-private",
        name="Private Insurer — Purchase KYC",
        short_name="Private Insurer KYC",
        category_id="provider",
        checklist_lob="insurer_private",
        description="Private-market KYC — income proof for higher SI; digital e-KYC via Aadhaar/PAN.",
        uw_focus="Income proof when SI is high. e-KYC increasingly standard.",
        documents=[
            "ID + address proof",
            "Age proof",
            "Photograph",
            "Income proof (for higher sum insured products)",
            "Digital KYC (e-KYC via Aadhaar / PAN)",
        ],
        coverages=[_cov("private_kyc_std", "Private Purchase KYC", "Income proof (for higher sum insured products)", "Digital KYC (e-KYC via Aadhaar / PAN)")],
    ),
    _line(
        id="reinsurance_treaty",
        slug="reinsurance-treaty",
        name="Reinsurance (B2B — insurer buying cover)",
        short_name="Reinsurance",
        category_id="provider",
        checklist_lob="reinsurance_treaty",
        description="Not individual KYC. Ceding license, treaty/fac, portfolio, loss history, solvency, regulator clearance.",
        uw_focus="Company-to-company. Decline if treated as retail KYC. Treaty + solvency + claims data.",
        documents=[
            "Ceding company's (primary insurer's) registration & license details",
            "Treaty / facultative reinsurance agreement",
            "Risk portfolio details of ceding insurer (policies being reinsured)",
            "Loss history / claims data of ceding insurer",
            "Solvency & financial statements of ceding insurer",
            "Regulatory approval documents (IRDAI or relevant regulator clearance)",
        ],
        coverages=[
            _cov("re_treaty", "Treaty Reinsurance", "Treaty / facultative reinsurance agreement", "Risk portfolio details of ceding insurer (policies being reinsured)"),
            _cov("re_facultative", "Facultative Reinsurance", "Treaty / facultative reinsurance agreement", "Risk portfolio details of ceding insurer (policies being reinsured)"),
        ],
        base_packet=[],
    ),
]

for _ln in GENERAL_LINES:
    _ln["status"] = "live" if _ln["id"] in LIVE_GENERAL_PRODUCT_IDS else "catalog"


def list_general_categories() -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    live_counts: dict[str, int] = {}
    for line in GENERAL_LINES:
        cid = line["category_id"]
        counts[cid] = counts.get(cid, 0) + 1
        if line.get("status") == "live":
            live_counts[cid] = live_counts.get(cid, 0) + 1
    return [{**cat, "product_count": counts.get(cat["id"], 0), "live_count": live_counts.get(cat["id"], 0)} for cat in GENERAL_CATEGORIES]


def list_general_lines(*, category_id: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in GENERAL_LINES:
        if category_id and line["category_id"] != category_id:
            continue
        if status and line.get("status") != status:
            continue
        coverages = _normalize_coverages(line.get("coverages"))
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
                "additional_document_count": len(line["additional_documents"]),
                "coverage_count": len(coverages),
                "coverages": coverages,
                "all_documents": flatten_line_documents({**line, "coverages": coverages}),
                "acord_forms": list(line["acord_forms"]),
                "status": line.get("status") or "catalog",
            }
        )
    return rows


def general_taxonomy_tree() -> list[dict[str, Any]]:
    by_cat: dict[str, list[dict[str, Any]]] = {c["id"]: [] for c in GENERAL_CATEGORIES}
    for row in list_general_lines():
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
    return [{**cat, "products": by_cat.get(cat["id"], [])} for cat in list_general_categories()]


def get_general_line(line_id_or_slug: str) -> dict[str, Any] | None:
    raw = (line_id_or_slug or "").strip().lower()
    if not raw:
        return None
    variants = {raw, raw.replace("_", "-"), raw.replace("-", "_")}
    for line in GENERAL_LINES:
        candidates = {
            line["id"],
            line["slug"],
            line["checklist_lob"],
            line["insurance_line"],
            line["id"].replace("_", "-"),
            line["checklist_lob"].replace("_", "-"),
        }
        if variants & candidates:
            coverages = _normalize_coverages(line.get("coverages"))
            return {
                **line,
                "coverages": coverages,
                "all_documents": flatten_line_documents({**line, "coverages": coverages}),
                "base_packet": list(line.get("base_packet") or []),
                "uw_responsibilities": list(GENERAL_UW_RESPONSIBILITIES),
                "uw_question": "Is this subject eligible for the selected general/non-life cover, with the leaf-specific proofs complete?",
            }
    return None


def resolve_general_checklist_lob(identifier: str | None) -> str | None:
    if not identifier:
        return None
    target = re.sub(r"[\s_-]+", " ", str(identifier).strip().lower())
    if not target:
        return None
    for line in GENERAL_LINES:
        lob = str(line.get("checklist_lob") or "").strip()
        if not lob:
            continue
        candidates = {
            re.sub(r"[\s_-]+", " ", str(line.get("id") or "").strip().lower()),
            re.sub(r"[\s_-]+", " ", str(line.get("slug") or "").strip().lower()),
            re.sub(r"[\s_-]+", " ", str(line.get("name") or "").strip().lower()),
            re.sub(r"[\s_-]+", " ", str(line.get("short_name") or "").strip().lower()),
            re.sub(r"[\s_-]+", " ", lob.lower()),
        }
        if target in candidates:
            return lob
        for cov in line.get("coverages") or []:
            if not isinstance(cov, dict):
                continue
            cov_ids = {
                re.sub(r"[\s_-]+", " ", str(cov.get("id") or "").strip().lower()),
                re.sub(r"[\s_-]+", " ", str(cov.get("name") or "").strip().lower()),
            }
            if target in cov_ids:
                return lob
    return None


def get_general_coverage(
    product_id: str | None = None,
    coverage_id: str | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    from insureflow.insurance.commercial_lobs import get_line_coverage

    line = get_general_line(product_id or "") if product_id else None
    if line is None and coverage_id:
        key = (coverage_id or "").strip().lower().replace("-", "_").replace(" ", "_")
        for candidate in GENERAL_LINES:
            for cov in candidate.get("coverages") or []:
                if not isinstance(cov, dict):
                    continue
                cid = str(cov.get("id") or "").strip().lower().replace("-", "_").replace(" ", "_")
                if cid == key:
                    return get_general_line(str(candidate.get("id") or "")), cov
        return None, None
    if line is None:
        return None, None
    return line, get_line_coverage(line, coverage_id)


def detect_general_product(text_blob: str = "") -> str | None:
    blob = re.sub(r"[^a-z0-9 ]", " ", (text_blob or "").lower())
    if not blob.strip():
        return None
    best: str | None = None
    best_score = 0
    for line in GENERAL_LINES:
        score = 0
        for part in (line.get("name"), line.get("short_name"), line.get("checklist_lob")):
            phrase = re.sub(r"[^a-z0-9 ]", " ", str(part or "").lower()).strip()
            if len(phrase) >= 6 and phrase in blob:
                score += 2
        if score > best_score:
            best = str(line.get("checklist_lob") or "").strip() or None
            best_score = score
    return best if best_score >= 2 else None


def general_hub_payload() -> dict[str, Any]:
    lines = list_general_lines()
    live = [ln for ln in lines if ln["status"] == "live"]
    return {
        "segment": "general_non_life",
        "title": "General / Non-Life Insurance",
        "summary": (
            "Motor, home, travel, marine, fire, liability, cyber, crop, livestock, pet, event, "
            "title, mortgage GI, and PSU/private/reinsurance KYC overlays. Each leaf has its own "
            "document pack and UW gates. Catalog until a filed general rate manual is imported."
        ),
        "base_packet": [],
        "uw_responsibilities": list(GENERAL_UW_RESPONSIBILITIES),
        "categories": list_general_categories(),
        "taxonomy": general_taxonomy_tree(),
        "lines": lines,
        "live_lines": live,
        "production_lines": ["general"],
        "stats": {
            "category_count": len(GENERAL_CATEGORIES),
            "product_count": len(GENERAL_LINES),
            "live_count": len(live),
            "catalog_count": max(0, len(lines) - len(live)),
            "lob_model_count": 0,
        },
    }
