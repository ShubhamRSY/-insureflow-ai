# RAG Corpus: Commercial Insurance (P&C)

Commercial Lines Underwriting Guide · Version 3.0 · Effective 2026-01-01

## LOB metadata
- LOB slug: commercial
- Products: 59
- Categories: 8
- Standards: ISO commercial lines forms, ACORD applications, NCCI (workers comp), AAIS (inland marine)
- Underwriting authority: Field authority to $250K premium / $5M TIV; above refers to the Commercial Desk. Any decline requires a written reason on the file.

## How to use for RAG
- Index each `documents/<product>.md` as one or more chunks (split on the `##` sections).
- Bias retrieval to this LOB (or category) when the submission's line is known.
- The sections map to likely underwriter questions: eligibility, decline, documents, coverages, exclusions, limits, rating, authority.

## Categories

| id | name | summary |
|---|---|---|
| property | Property Insurance | Buildings, contents, BI, marine, catastrophe, crime, and equipment risks. |
| liability | Liability Insurance | Third-party bodily injury, property damage, professional, management, and cyber liability. |
| workforce | Workforce / Employee Insurance | Workers' compensation, employer liability, and group / key-person benefits. |
| auto | Auto / Transportation Insurance | Commercial auto, fleet, cargo, hired/non-owned, and garage risks. |
| financial | Financial / Credit Insurance | Trade credit, surety bonds, and political risk. |
| specialty | Specialty / Industry-Specific Insurance | Construction wrap-ups, aviation, agribusiness, event, IP, K&R, terrorism, recall, and supply chain. |
| alternative | Alternative Risk Transfer | Captives, self-insured retention, and fronting arrangements for complex insureds. |
| package | Package / Bundled Policies | BOP and commercial package policies combining multiple lines. |

## Product catalog

| product_id | name | category | status | docs | coverages | forms |
|---|---|---|---|---|---|---|
| property_bi | Commercial Property Insurance | property | live | 10 | 5 | 2 |
| business_interruption | Business Interruption (Business Income) Insurance | property | live | 8 | 4 | 3 |
| builders_risk | Builder's Risk Insurance | property | live | 8 | 0 | 3 |
| inland_marine | Inland Marine Insurance | property | live | 8 | 4 | 2 |
| ocean_marine | Ocean Marine Insurance | property | live | 8 | 3 | 2 |
| equipment_breakdown | Equipment Breakdown (Boiler & Machinery) Insurance | property | live | 8 | 0 | 2 |
| flood_commercial | Flood Insurance (Commercial) | property | live | 8 | 0 | 2 |
| earthquake_commercial | Earthquake Insurance (Commercial) | property | live | 8 | 0 | 2 |
| crime | Crime Insurance | property | live | 8 | 4 | 2 |
| ordinance_or_law | Ordinance or Law Coverage | property | live | 8 | 3 | 2 |
| rent_loss_of_rents | Rent / Loss of Rents Insurance | property | live | 8 | 0 | 2 |
| dic_excess_flood | Difference in Conditions (DIC) / Excess Flood | property | live | 8 | 2 | 2 |
| general_liability | General Liability (CGL) | liability | live | 8 | 3 | 2 |
| product_liability | Product Liability Insurance | liability | live | 8 | 0 | 2 |
| errors_omissions | Professional Liability / E&O | liability | live | 8 | 5 | 1 |
| architects_engineers | Architects & Engineers (A&E) Professional Liability | liability | live | 8 | 2 | 1 |
| miscellaneous_professional | Miscellaneous Professional Liability (MPL) | liability | live | 8 | 0 | 1 |
| directors_officers | Directors & Officers (D&O) Liability | liability | live | 12 | 3 | 1 |
| epli | Employment Practices Liability (EPLI) | liability | live | 8 | 3 | 1 |
| fiduciary_liability | Fiduciary Liability Insurance | liability | live | 8 | 0 | 1 |
| cyber_liability | Cyber Liability Insurance | liability | live | 9 | 2 | 1 |
| umbrella | Umbrella / Excess Liability Insurance | liability | live | 8 | 0 | 2 |
| pollution | Pollution / Environmental Liability | liability | live | 8 | 3 | 1 |
| liquor_liability | Liquor Liability Insurance | liability | live | 8 | 0 | 2 |
| media_liability | Media Liability Insurance | liability | live | 8 | 0 | 1 |
| workers_comp | Workers' Compensation Insurance | workforce | live | 10 | 0 | 1 |
| employers_liability | Employer's Liability Insurance | workforce | live | 9 | 0 | 2 |
| group_health | Group Health Insurance | workforce | live | 8 | 3 | 1 |
| group_life | Group Life Insurance | workforce | live | 8 | 0 | 1 |
| group_disability | Group Disability Insurance | workforce | live | 8 | 2 | 1 |
| key_person | Key Person Insurance | workforce | live | 8 | 0 | 1 |
| business_overhead | Business Overhead Expense Insurance | workforce | live | 8 | 0 | 1 |
| voluntary_benefits | Voluntary / Supplemental Benefits | workforce | live | 8 | 3 | 1 |
| commercial_auto | Commercial Auto Insurance | auto | live | 8 | 3 | 2 |
| fleet | Fleet Insurance | auto | live | 10 | 0 | 2 |
| hnoa | Hired & Non-Owned Auto (HNOA) | auto | live | 8 | 0 | 2 |
| motor_truck_cargo | Motor Truck Cargo Insurance | auto | live | 8 | 0 | 1 |
| garage_liability | Garage Liability Insurance | auto | live | 8 | 0 | 2 |
| non_trucking_liability | Non-Trucking Liability ("Bobtail") Insurance | auto | live | 8 | 0 | 2 |
| trade_credit | Trade Credit Insurance | financial | live | 10 | 2 | 1 |
| surety_bonds | Surety Bonds | financial | live | 8 | 4 | 1 |
| political_risk | Political Risk Insurance | financial | live | 8 | 0 | 1 |
| representations_warranties | Representations & Warranties Insurance (R&W) | financial | live | 8 | 2 | 1 |
| legal_expense | Legal Expense / Litigation Insurance | financial | live | 8 | 0 | 1 |
| tech_eo_cyber | Technology E&O / Cyber (Industry-Specific) | specialty | live | 8 | 0 | 1 |
| construction | Construction / Contractor's Insurance | specialty | live | 8 | 2 | 3 |
| aviation | Aviation Insurance | specialty | live | 8 | 0 | 1 |
| event_insurance | Event Insurance | specialty | live | 8 | 2 | 1 |
| intellectual_property | Intellectual Property Insurance | specialty | live | 8 | 0 | 1 |
| kidnap_ransom | Kidnap & Ransom (K&R) Insurance | specialty | live | 8 | 0 | 1 |
| terrorism | Terrorism Insurance | specialty | live | 8 | 0 | 1 |
| product_recall | Product Recall Insurance | specialty | live | 8 | 0 | 1 |
| supply_chain | Supply Chain Insurance | specialty | live | 8 | 0 | 1 |
| crop_insurance | Crop Insurance | specialty | live | 8 | 0 | 1 |
| livestock_bloodstock | Livestock / Bloodstock Insurance | specialty | live | 8 | 2 | 1 |
| captive_insurance | Captive Insurance Programs | alternative | live | 8 | 2 | 1 |
| sir_fronting | Self-Insured Retention (SIR) / Fronting Arrangements | alternative | live | 8 | 2 | 1 |
| bop | Business Owner's Policy (BOP) | package | live | 8 | 1 | 4 |
| cpp | Commercial Package Policy (CPP) | package | live | 8 | 1 | 2 |

## Product summaries

### property_bi — Commercial Property Insurance
Building, contents, and related property coverages for commercial locations.
- Full guide entry: `documents/property_bi.md`

### business_interruption — Business Interruption (Business Income) Insurance
Covers lost income and extra expense after a covered property loss.
- Full guide entry: `documents/business_interruption.md`

### builders_risk — Builder's Risk Insurance
Covers buildings and materials during construction or renovation.
- Full guide entry: `documents/builders_risk.md`

### inland_marine — Inland Marine Insurance
Mobile property, equipment, installation, transit, and specialty floaters.
- Full guide entry: `documents/inland_marine.md`

### ocean_marine — Ocean Marine Insurance
Hull, cargo, and P&I for ocean and coastal marine exposures.
- Full guide entry: `documents/ocean_marine.md`

### equipment_breakdown — Equipment Breakdown (Boiler & Machinery) Insurance
Sudden and accidental breakdown of boilers, machinery, and critical equipment.
- Full guide entry: `documents/equipment_breakdown.md`

### flood_commercial — Flood Insurance (Commercial)
Commercial flood coverage — NFIP and/or private market excess flood.
- Full guide entry: `documents/flood_commercial.md`

### earthquake_commercial — Earthquake Insurance (Commercial)
Earthquake shake and related earth-movement coverage for commercial risks.
- Full guide entry: `documents/earthquake_commercial.md`

### crime — Crime Insurance
Employee dishonesty, forgery, burglary/robbery, and computer/funds-transfer fraud.
- Full guide entry: `documents/crime.md`

### ordinance_or_law — Ordinance or Law Coverage
Covers the cost of rebuilding to current code after a loss (endorsement or standalone).
- Full guide entry: `documents/ordinance_or_law.md`

### rent_loss_of_rents — Rent / Loss of Rents Insurance
Standalone business-income style cover for landlords — lost rental income after a covered loss.
- Full guide entry: `documents/rent_loss_of_rents.md`

### dic_excess_flood — Difference in Conditions (DIC) / Excess Flood
Fills gaps between primary property and named-peril exclusions (flood, quake, and other DIC perils).
- Full guide entry: `documents/dic_excess_flood.md`

### general_liability — General Liability (CGL)
Premises/operations, products & completed operations, and personal/advertising injury.
- Full guide entry: `documents/general_liability.md`

### product_liability — Product Liability Insurance
Liability arising from manufactured, distributed, or sold products.
- Full guide entry: `documents/product_liability.md`

### errors_omissions — Professional Liability / E&O
Professional liability for services and advice — profession-specific applications.
- Full guide entry: `documents/errors_omissions.md`

### architects_engineers — Architects & Engineers (A&E) Professional Liability
Design professional liability distinct from general E&O — architects, engineers, and related design firms.
- Full guide entry: `documents/architects_engineers.md`

### miscellaneous_professional — Miscellaneous Professional Liability (MPL)
Catch-all professional liability for professions not otherwise classified (consultants, HR firms, etc.).
- Full guide entry: `documents/miscellaneous_professional.md`

### directors_officers — Directors & Officers (D&O) Liability
Management liability for directors and officers — private or public company.
- Full guide entry: `documents/directors_officers.md`

### epli — Employment Practices Liability (EPLI)
Wrongful termination, discrimination/harassment, and retaliation claims.
- Full guide entry: `documents/epli.md`

### fiduciary_liability — Fiduciary Liability Insurance
Liability for ERISA and employee-benefit plan fiduciaries.
- Full guide entry: `documents/fiduciary_liability.md`

### cyber_liability — Cyber Liability Insurance
First-party breach response / BI and third-party liability for cyber events.
- Full guide entry: `documents/cyber_liability.md`

### umbrella — Umbrella / Excess Liability Insurance
Excess limits over primary GL, auto, and employer liability schedules.
- Full guide entry: `documents/umbrella.md`

### pollution — Pollution / Environmental Liability
Contractor's, site, and storage-tank environmental liability.
- Full guide entry: `documents/pollution.md`

### liquor_liability — Liquor Liability Insurance
Liability arising from selling, serving, or furnishing alcoholic beverages.
- Full guide entry: `documents/liquor_liability.md`

### media_liability — Media Liability Insurance
Defamation, privacy, IP, and content-related liability for media/publishers.
- Full guide entry: `documents/media_liability.md`

### workers_comp — Workers' Compensation Insurance
Employee injury coverage with payroll class codes, e-mod, and safety programs.
- Full guide entry: `documents/workers_comp.md`

### employers_liability — Employer's Liability Insurance
Employer liability for employee injury claims outside workers' compensation exclusivity.
- Full guide entry: `documents/employers_liability.md`

### group_health — Group Health Insurance
Employer-sponsored medical benefits — fully insured or self-funded.
- Full guide entry: `documents/group_health.md`

### group_life — Group Life Insurance
Employer-sponsored group term life and AD&D benefits.
- Full guide entry: `documents/group_life.md`

### group_disability — Group Disability Insurance
Short-term and long-term group disability income benefits.
- Full guide entry: `documents/group_disability.md`

### key_person — Key Person Insurance
Life / disability on a critical individual whose loss would financially hurt the business.
- Full guide entry: `documents/key_person.md`

### business_overhead — Business Overhead Expense Insurance
Covers fixed business expenses if an owner/professional is disabled.
- Full guide entry: `documents/business_overhead.md`

### voluntary_benefits — Voluntary / Supplemental Benefits
Employee-paid dental, vision, accident, and critical illness benefits.
- Full guide entry: `documents/voluntary_benefits.md`

### commercial_auto — Commercial Auto Insurance
Liability, collision, and comprehensive for business-owned autos.
- Full guide entry: `documents/commercial_auto.md`

### fleet — Fleet Insurance
Program coverage for larger commercial vehicle fleets.
- Full guide entry: `documents/fleet.md`

### hnoa — Hired & Non-Owned Auto (HNOA)
Liability for hired vehicles and employee-owned autos used in business.
- Full guide entry: `documents/hnoa.md`

### motor_truck_cargo — Motor Truck Cargo Insurance
Cargo in transit for motor carriers and private fleets.
- Full guide entry: `documents/motor_truck_cargo.md`

### garage_liability — Garage Liability Insurance
Auto dealer / repair garage liability and garagekeepers coverage.
- Full guide entry: `documents/garage_liability.md`

### non_trucking_liability — Non-Trucking Liability ("Bobtail") Insurance
Liability for owner-operators driving without a load (bobtail / non-trucking).
- Full guide entry: `documents/non_trucking_liability.md`

### trade_credit — Trade Credit Insurance
Protects receivables against buyer default — domestic and export exposures.
- Full guide entry: `documents/trade_credit.md`

### surety_bonds — Surety Bonds
Contract, commercial, fidelity, and court bonds.
- Full guide entry: `documents/surety_bonds.md`

### political_risk — Political Risk Insurance
Expropriation, currency inconvertibility, political violence, and related PRI covers.
- Full guide entry: `documents/political_risk.md`

### representations_warranties — Representations & Warranties Insurance (R&W)
M&A deal insurance covering breaches of reps and warranties in the purchase agreement.
- Full guide entry: `documents/representations_warranties.md`

### legal_expense — Legal Expense / Litigation Insurance
Covers legal defense costs and related litigation expense — including after-the-event and litigation funding-style covers.
- Full guide entry: `documents/legal_expense.md`

### tech_eo_cyber — Technology E&O / Cyber (Industry-Specific)
Combined technology professional liability and cyber for tech companies.
- Full guide entry: `documents/tech_eo_cyber.md`

### construction — Construction / Contractor's Insurance
Contractor's GL and wrap-up (OCIP/CCIP) construction programs.
- Full guide entry: `documents/construction.md`

### aviation — Aviation Insurance
Aircraft hull and liability for owned, leased, or operated aircraft.
- Full guide entry: `documents/aviation.md`

### event_insurance — Event Insurance
Event cancellation and event liability for organizers and venues.
- Full guide entry: `documents/event_insurance.md`

### intellectual_property — Intellectual Property Insurance
IP infringement defense/abatement and related intellectual property covers.
- Full guide entry: `documents/intellectual_property.md`

### kidnap_ransom — Kidnap & Ransom (K&R) Insurance
Kidnap, ransom, extortion, and related crisis-response coverage.
- Full guide entry: `documents/kidnap_ransom.md`

### terrorism — Terrorism Insurance
Certified and/or non-certified terrorism property and liability covers.
- Full guide entry: `documents/terrorism.md`

### product_recall — Product Recall Insurance
First-party recall costs and related product contamination covers.
- Full guide entry: `documents/product_recall.md`

### supply_chain — Supply Chain Insurance
Non-damage and contingent supply-chain interruption covers.
- Full guide entry: `documents/supply_chain.md`

### crop_insurance — Crop Insurance
Agribusiness crop coverage — acreage, crop type, and yield-based underwriting.
- Full guide entry: `documents/crop_insurance.md`

### livestock_bloodstock — Livestock / Bloodstock Insurance
Mortality and related covers for livestock herds and bloodstock (horses, etc.).
- Full guide entry: `documents/livestock_bloodstock.md`

### captive_insurance — Captive Insurance Programs
Self-owned insurance subsidiaries writing parent/affiliate risks — requires actuarial and regulatory feasibility.
- Full guide entry: `documents/captive_insurance.md`

### sir_fronting — Self-Insured Retention (SIR) / Fronting Arrangements
Large-deductible / SIR programs and fronted policies requiring collateral and claims administration.
- Full guide entry: `documents/sir_fronting.md`

### bop — Business Owner's Policy (BOP)
Bundles property + general liability for eligible small businesses.
- Full guide entry: `documents/bop.md`

### cpp — Commercial Package Policy (CPP)
Customizable bundle: property + liability + crime + auto and related sections.
- Full guide entry: `documents/cpp.md`
