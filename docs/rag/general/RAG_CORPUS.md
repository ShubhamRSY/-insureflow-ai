# RAG Corpus: General / Non-Life

General Insurance Underwriting Guide · Version 3.0 · Effective 2026-01-01

## LOB metadata
- LOB slug: general
- Products: 31
- Categories: 13
- Standards: IRDAI (Protection of Policyholders' Interests) Regulations, All India Fire Tariff, Motor Tariff, ICC (marine)
- Underwriting authority: Catalog products are underwritten manually. Accept within filed product terms; refer any non-standard term, add-on, or sum insured above the product limit.

## How to use for RAG
- Index each `documents/<product>.md` as one or more chunks (split on the `##` sections).
- Bias retrieval to this LOB (or category) when the submission's line is known.
- The sections map to likely underwriter questions: eligibility, decline, documents, coverages, exclusions, limits, rating, authority.

## Categories

| id | name | summary |
|---|---|---|
| motor | Motor Insurance | Car, two-wheeler, and commercial vehicle — TP-only vs comprehensive. |
| home | Home / Property Insurance | Structure-only, contents-only, and comprehensive home. |
| travel | Travel Insurance | Domestic vs international (passport/visa/itinerary). |
| marine | Marine Insurance | Cargo (goods in transit) vs hull (vessel). |
| fire | Fire Insurance | Residential SFSP vs commercial/industrial fire. |
| liability | Liability Insurance | Professional indemnity, public liability, product liability. |
| cyber | Cyber Insurance | Data breach vs cyberattack / ransomware. |
| crop | Crop Insurance | Yield-based (PMFBY-type) vs weather-index. |
| animal | Livestock & Pet | Cattle/livestock vs companion pet. |
| event | Event Insurance | Wedding vs concert / public event. |
| title | Title Insurance | Legal title chain, encumbrance, title search. |
| mortgage_gi | Mortgage Insurance | Lender-linked cover on the mortgaged property / loan. |
| provider | By Provider Type | PSU vs private purchase KYC, and B2B reinsurance (not individual KYC). |

## Product catalog

| product_id | name | category | status | docs | coverages | forms |
|---|---|---|---|---|---|---|
| car_tp | Car Insurance — Third-Party Only | motor | live | 5 | 1 | 0 |
| car_comprehensive | Car Insurance — Comprehensive | motor | live | 6 | 2 | 0 |
| tw_tp | Two-Wheeler Insurance — Third-Party Only | motor | live | 4 | 1 | 0 |
| tw_comprehensive | Two-Wheeler Insurance — Comprehensive | motor | live | 6 | 2 | 0 |
| cv_tp | Commercial Vehicle Insurance — Third-Party Only | motor | live | 6 | 1 | 0 |
| cv_comprehensive | Commercial Vehicle Insurance — Comprehensive | motor | live | 8 | 1 | 0 |
| home_structure | Home Structure-only Cover | home | live | 5 | 1 | 0 |
| home_contents | Home Contents-only Cover | home | live | 4 | 1 | 0 |
| home_comprehensive | Structure + Contents (Comprehensive Home) | home | live | 6 | 1 | 0 |
| travel_domestic | Domestic Travel Insurance | travel | live | 4 | 1 | 0 |
| travel_international | International Travel Insurance | travel | live | 6 | 1 | 0 |
| marine_cargo | Marine Cargo Insurance | marine | live | 6 | 1 | 0 |
| marine_hull | Marine Hull Insurance | marine | live | 6 | 1 | 0 |
| fire_residential | Standard Fire & Allied Perils (Residential) | fire | live | 4 | 1 | 0 |
| fire_commercial | Fire Insurance — Commercial / Industrial | fire | live | 6 | 1 | 0 |
| professional_indemnity_gi | Professional Indemnity Insurance | liability | live | 5 | 1 | 0 |
| public_liability_gi | Public Liability Insurance | liability | live | 5 | 1 | 0 |
| product_liability_gi | Product Liability Insurance | liability | live | 5 | 1 | 0 |
| cyber_data_breach | Cyber Insurance — Data Breach Cover | cyber | live | 5 | 1 | 0 |
| cyber_ransomware | Cyber Insurance — Cyberattack / Ransomware Cover | cyber | live | 5 | 1 | 0 |
| crop_yield | Yield-based Crop Insurance (PMFBY-type) | crop | live | 6 | 1 | 0 |
| crop_weather | Weather-based Crop Insurance | crop | live | 5 | 1 | 0 |
| livestock_cattle | Livestock / Cattle Insurance | animal | live | 6 | 1 | 0 |
| pet_insurance | Pet Insurance | animal | live | 5 | 1 | 0 |
| wedding_insurance | Wedding Insurance | event | live | 4 | 1 | 0 |
| concert_event_insurance | Concert / Public Event Insurance | event | live | 5 | 1 | 0 |
| title_insurance_gi | Title Insurance | title | live | 7 | 1 | 0 |
| mortgage_insurance_gi | Mortgage Insurance | mortgage_gi | live | 6 | 1 | 0 |
| insurer_psu | Public Sector Insurer (Government-backed) — Purchase KYC | provider | live | 5 | 1 | 0 |
| insurer_private | Private Insurer — Purchase KYC | provider | live | 5 | 1 | 0 |
| reinsurance_treaty | Reinsurance (B2B — insurer buying cover) | provider | live | 6 | 2 | 0 |

## Product summaries

### car_tp — Car Insurance — Third-Party Only
Statutory third-party motor — RC, owner KYC, DL. No own-damage inspection.
- Full guide entry: `documents/car_tp.md`

### car_comprehensive — Car Insurance — Comprehensive
Own-damage + TP. NCB needs prior policy; lapse/pre-owned needs inspection; new vehicle needs invoice.
- Full guide entry: `documents/car_comprehensive.md`

### tw_tp — Two-Wheeler Insurance — Third-Party Only
Statutory TP for motorcycle / scooter.
- Full guide entry: `documents/tw_tp.md`

### tw_comprehensive — Two-Wheeler Insurance — Comprehensive
Two-wheeler OD + TP. NCB + photos/invoice as applicable.
- Full guide entry: `documents/tw_comprehensive.md`

### cv_tp — Commercial Vehicle Insurance — Third-Party Only
Goods/passenger CV statutory TP — fitness, permit, PUC.
- Full guide entry: `documents/cv_tp.md`

### cv_comprehensive — Commercial Vehicle Insurance — Comprehensive
CV OD + TP. Fitness, permit, PUC, NCB, inspection.
- Full guide entry: `documents/cv_comprehensive.md`

### home_structure — Home Structure-only Cover
Building only — ownership, valuation, tax, exterior photos.
- Full guide entry: `documents/home_structure.md`

### home_contents — Home Contents-only Cover
Movables only — inventory + invoices for high-value items. No deed required.
- Full guide entry: `documents/home_contents.md`

### home_comprehensive — Structure + Contents (Comprehensive Home)
Building + contents — deed, valuation, inventory, tax, interior + exterior photos.
- Full guide entry: `documents/home_comprehensive.md`

### travel_domestic — Domestic Travel Insurance
India travel — itinerary/ticket. Passport not required.
- Full guide entry: `documents/travel_domestic.md`

### travel_international — International Travel Insurance
Overseas trip — passport mandatory, visa + itinerary.
- Full guide entry: `documents/travel_international.md`

### marine_cargo — Marine Cargo Insurance
Goods in transit — invoice, B/L or AWB, packing list, IEC, GST. Not individual KYC-only.
- Full guide entry: `documents/marine_cargo.md`

### marine_hull — Marine Hull Insurance
Vessel hull — registration, class/seaworthiness, valuation, crew, owner company.
- Full guide entry: `documents/marine_hull.md`

### fire_residential — Standard Fire & Allied Perils (Residential)
SFSP on a dwelling — ownership, valuation, photos.
- Full guide entry: `documents/fire_residential.md`

### fire_commercial — Fire Insurance — Commercial / Industrial
Factory/commercial fire — GST, asset valuation, fire safety cert, stock.
- Full guide entry: `documents/fire_commercial.md`

### professional_indemnity_gi — Professional Indemnity Insurance
PI for licensed professionals (medical / legal / CA).
- Full guide entry: `documents/professional_indemnity_gi.md`

### public_liability_gi — Public Liability Insurance
Premises/public liability — GST, premises, nature of business, safety, claims.
- Full guide entry: `documents/public_liability_gi.md`

### product_liability_gi — Product Liability Insurance
Product liability — catalog, manufacturing license, ISO/BIS, recall history.
- Full guide entry: `documents/product_liability_gi.md`

### cyber_data_breach — Cyber Insurance — Data Breach Cover
First/third-party data breach — security policy, data volume, incident history.
- Full guide entry: `documents/cyber_data_breach.md`

### cyber_ransomware — Cyber Insurance — Cyberattack / Ransomware Cover
Ransomware / cyberattack — network details, existing controls, incident history.
- Full guide entry: `documents/cyber_ransomware.md`

### crop_yield — Yield-based Crop Insurance (PMFBY-type)
Yield/PMFBY-style — land record, Aadhaar, bank, sowing, acreage, crop-loan link.
- Full guide entry: `documents/crop_yield.md`

### crop_weather — Weather-based Crop Insurance
Weather-index — land, KYC, bank, sowing, nearest weather station reference.
- Full guide entry: `documents/crop_weather.md`

### livestock_cattle — Livestock / Cattle Insurance
Cattle/livestock — vet health cert, tag/photo/microchip, ownership, valuation.
- Full guide entry: `documents/livestock_cattle.md`

### pet_insurance — Pet Insurance
Companion pet — vaccination, medical history, breed/age, photo.
- Full guide entry: `documents/pet_insurance.md`

### wedding_insurance — Wedding Insurance
Wedding cancellation/liability — date/venue/budget, vendor contracts, advances.
- Full guide entry: `documents/wedding_insurance.md`

### concert_event_insurance — Concert / Public Event Insurance
Public event — organizer GST, venue, local permit, artist contracts, ticket projection.
- Full guide entry: `documents/concert_event_insurance.md`

### title_insurance_gi — Title Insurance
Legal title risk — deed chain, encumbrance, tax, survey, title search. Not motor/health KYC pattern.
- Full guide entry: `documents/title_insurance_gi.md`

### mortgage_insurance_gi — Mortgage Insurance
Cover linked to a housing loan — sanction letter, property, income, loan statement.
- Full guide entry: `documents/mortgage_insurance_gi.md`

### insurer_psu — Public Sector Insurer (Government-backed) — Purchase KYC
Govt-format KYC overlay — Aadhaar-linked verification; category cert if subsidy scheme.
- Full guide entry: `documents/insurer_psu.md`

### insurer_private — Private Insurer — Purchase KYC
Private-market KYC — income proof for higher SI; digital e-KYC via Aadhaar/PAN.
- Full guide entry: `documents/insurer_private.md`

### reinsurance_treaty — Reinsurance (B2B — insurer buying cover)
Not individual KYC. Ceding license, treaty/fac, portfolio, loss history, solvency, regulator clearance.
- Full guide entry: `documents/reinsurance_treaty.md`
