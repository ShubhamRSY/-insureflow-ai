"""Per-leaf general UW — car TP ≠ comprehensive ≠ CV; cargo ≠ hull; etc."""

from __future__ import annotations

from insureflow.insurance.general_lobs import GENERAL_LINES
from insureflow.models.agents import UWDecision
from insureflow.models.submissions import SubmissionBundle, UnstructuredSubmission
from insureflow.underwriting.general_uw import (
    general_product_terms,
    registered_general_uw_products,
    underwrite_general,
)

KYC = "Identity proof Aadhaar. Address proof utility bill. ID + address proof of owner. Age: 34."


def _bundle(text: str, doc_type: str = "general_application") -> SubmissionBundle:
    return SubmissionBundle(
        bundle_id="gi-uw",
        unstructured=[
            UnstructuredSubmission(
                submission_id="d1",
                source="general_application",
                document_type=doc_type,
                raw_text=text,
            ),
        ],
    )


def test_every_general_leaf_has_dedicated_uw_handler():
    registered = registered_general_uw_products()
    missing = [ln["id"] for ln in GENERAL_LINES if ln["id"] not in registered]
    assert missing == [], missing
    assert len(registered) == len(GENERAL_LINES)


def test_car_tp_does_not_require_inspection_or_invoice():
    text = KYC + " Registration certificate RC of vehicle. Driving license. Chassis number ABC Engine number 123."
    tp = underwrite_general(_bundle(text), product_id="car_tp")
    comp = underwrite_general(_bundle(text + " Pre-owned used vehicle lapse."), product_id="car_comprehensive")
    assert tp.product_family == "car_tp"
    assert comp.product_family == "car_comprehensive"
    assert "inspection_if_used" not in tp.gates
    assert "invoice_if_new" not in tp.gates
    assert "chassis_engine" in tp.gates
    assert comp.gates.get("inspection_if_used") == "fail"
    assert tp.decision != UWDecision.DECLINE
    assert any("third" in c.lower() or "tp" in c.lower() or "own-damage" in c.lower() for c in tp.conditions)


def test_cv_requires_fitness_permit_puc_car_does_not():
    motor_kyc = KYC + " Registration certificate RC. Driving license."
    car = underwrite_general(_bundle(motor_kyc + " Chassis engine number."), product_id="car_tp")
    cv = underwrite_general(_bundle(motor_kyc), product_id="cv_tp")
    assert "fitness" not in car.gates
    assert "permit" not in car.gates
    assert "puc" not in car.gates
    assert cv.gates.get("fitness") == "fail"
    assert cv.gates.get("permit") == "fail"
    assert cv.gates.get("puc") == "fail"
    assert cv.decision == UWDecision.REFER


def test_home_structure_requires_deed_contents_does_not():
    kyc_only = _bundle(KYC)
    structure = underwrite_general(kyc_only, product_id="home_structure")
    contents = underwrite_general(kyc_only, product_id="home_contents")
    assert structure.gates.get("ownership") == "fail"
    assert "ownership" not in contents.gates
    assert contents.gates.get("inventory") == "fail"
    assert contents.metadata.get("requires_deed") is False
    assert structure.decision == UWDecision.REFER
    assert contents.decision == UWDecision.REFER


def test_home_three_leaves_domain_distinctness():
    struct = underwrite_general(
        _bundle(KYC + " Sale deed. Property valuation. Property tax receipt. Photographs of property. RCC construction. Built in year 2018. Coastal location. No prior claims."),
        product_id="home_structure",
    )
    contents = underwrite_general(
        _bundle(
            KYC + " List of insured items with values including jewelry and electronics."
            " Purchase invoices of high-value items. Photographs of contents."
            " Total contents value 800000. Locks and alarm. No prior claims."
        ),
        product_id="home_contents",
    )
    comp = underwrite_general(
        _bundle(
            KYC + " Sale deed. Property valuation. List + invoices of insured contents."
            " Property tax receipt. Interior and exterior photographs."
            " Built in year 2015. Alarm. Coastal location. No prior claims."
        ),
        product_id="home_comprehensive",
    )
    assert struct.gates.get("construction_type") == "pass"
    assert "construction_type" not in contents.gates
    assert "inventory" not in struct.gates
    assert struct.metadata["subject"] == "building"
    assert "declared_value" in contents.gates
    assert "property_tax" not in contents.gates
    assert contents.metadata["subject"] == "contents"
    assert "inventory" in comp.gates and "property_tax" in comp.gates
    assert comp.metadata["subject"] == "building_and_contents"
    assert "construction_type" not in comp.gates
    assert "security_measures" in comp.gates
    assert struct.gates.get("catastrophe_exposure") == "fail"
    assert struct.metadata["building_age"] == 8
    assert struct.metadata["coastal"] is True
    assert struct.decision == UWDecision.CONDITIONAL_ACCEPT
    assert contents.decision == UWDecision.ACCEPT
    assert comp.decision == UWDecision.CONDITIONAL_ACCEPT


def test_home_structure_catastrophe_conditional():
    struct = underwrite_general(
        _bundle(KYC + " Sale deed. Valuation. Property tax. Photos. Brick construction. Built in year 2000. Flood-prone location. No prior claims."),
        product_id="home_structure",
    )
    assert struct.gates.get("catastrophe_exposure") == "fail"
    assert struct.metadata["coastal"] is True
    assert struct.decision == UWDecision.CONDITIONAL_ACCEPT


def test_home_contents_high_value_conditional():
    contents = underwrite_general(
        _bundle(KYC + " List of insured items with values. Purchase invoices. Photos. Total contents value 2000000. Jewellery worth 1500000 and cash. No security measures declared. No prior claims."),
        product_id="home_contents",
    )
    assert contents.metadata["high_value_items"] == "high"
    assert contents.gates.get("security_measures") == "fail"
    assert contents.decision == UWDecision.CONDITIONAL_ACCEPT


def test_travel_intl_passport_critical_domestic_does_not():
    text = KYC + " Age proof. Travel itinerary / ticket. Photograph."
    domestic = underwrite_general(_bundle(text), product_id="travel_domestic")
    intl = underwrite_general(_bundle(text), product_id="travel_international")
    assert domestic.product_family == "travel_domestic"
    assert intl.product_family == "travel_international"
    assert "passport" not in domestic.gates
    assert intl.gates.get("passport") == "fail"
    assert intl.decision == UWDecision.DECLINE
    assert domestic.decision != UWDecision.DECLINE
    assert domestic.metadata.get("requires_passport") is False
    assert intl.metadata.get("requires_passport") is True


def test_travel_intl_passport_size_photo_is_not_a_passport():
    text = KYC + " Passport-size photograph. Age proof. Travel itinerary flight ticket. Visa copy."
    intl = underwrite_general(_bundle(text), product_id="travel_international")
    assert intl.gates.get("passport") == "fail"
    assert intl.decision == UWDecision.DECLINE


def test_travel_domestic_vs_international_distinctness():
    dom = underwrite_general(
        _bundle("Aadhaar identity. Address proof. Age proof. Itinerary ticket PNR. Trip duration 6 days. Traveling to Jaipur. No pre-existing conditions. Photograph."),
        product_id="travel_domestic",
    )
    intl = underwrite_general(
        _bundle("Aadhaar identity. Address proof. Age proof. Passport. Visa copy. Itinerary flight ticket. Trip duration 10 days. Traveling to USA. No pre-existing conditions. Photograph."),
        product_id="travel_international",
    )
    assert dom.product_family == "travel_domestic"
    assert intl.product_family == "travel_international"
    assert "passport" not in dom.gates
    assert "visa" not in dom.gates
    assert intl.gates.get("passport") == "pass"
    assert intl.gates.get("visa") == "pass"
    assert "adventure_activities" in dom.gates or dom.metadata.get("adventure_activities") is not None
    assert "high_cost_destination" not in dom.gates
    assert intl.metadata["destination_cost_class"] == "high"
    assert intl.metadata["requires_passport"] is True
    assert dom.metadata["requires_passport"] is False


def test_travel_domestic_adventure_activities_conditional():
    adv = underwrite_general(
        _bundle("Aadhaar. Address proof. Age proof. Itinerary. Trip duration 5 days. Traveling to Himachal for trekking. No pre-existing conditions. Photograph."),
        product_id="travel_domestic",
    )
    assert adv.gates.get("adventure_activities") == "fail"
    assert adv.metadata["adventure_activities"] is True
    assert adv.metadata["travel_risk_class"] == "high"
    assert adv.decision == UWDecision.CONDITIONAL_ACCEPT


def test_travel_intl_high_cost_destination_conditional():
    intl = underwrite_general(
        _bundle("Aadhaar. Address proof. Age proof. Passport valid until 2030. Visa. Itinerary flight. Trip duration 21 days. Traveling to Switzerland. No pre-existing conditions. Photograph."),
        product_id="travel_international",
    )
    assert intl.gates.get("high_cost_destination") == "fail"
    assert intl.metadata["destination_cost_class"] == "high"
    assert intl.gates.get("passport_validity") == "pass"
    assert intl.decision == UWDecision.CONDITIONAL_ACCEPT


def test_travel_intl_ignores_domestic_domain():
    dom_text = "Aadhaar. Address proof. Age proof. Itinerary. Trip duration 4 days. Traveling to Mumbai. No pre-existing. Photograph."
    intl = underwrite_general(_bundle(dom_text), product_id="travel_international")
    assert intl.gates.get("passport") == "fail"
    assert "adventure_activities" not in intl.gates
    assert "destination_cost_class" in intl.metadata


def test_crop_yield_vs_weather_distinctness():
    yield_text = "Khasra khatauni 7-12 extract. Aadhaar identity. Bank account IFSC. Sowing certificate. Survey number 12 acreage 2 hectares. Crop loan KCC. Paddy irrigated."
    weather_text = "Khasra land ownership. Aadhaar. Bank account. Sowing certificate. Nearest weather station IMD Rajahmundry. Grape polyhouse."
    y = underwrite_general(_bundle(yield_text), product_id="crop_yield")
    w = underwrite_general(_bundle(weather_text), product_id="crop_weather")
    assert y.gates.get("acreage") == "pass"
    assert "acreage" not in w.gates
    assert y.gates.get("loan_if_any") == "pass"
    assert "loan_if_any" not in w.gates
    assert w.gates.get("weather_station") == "pass"
    assert "weather_station" not in y.gates
    assert y.metadata["index"] == "yield"
    assert w.metadata["index"] == "weather"


def test_livestock_vs_pet_distinctness():
    live = underwrite_general(
        _bundle("Identity Aadhaar. Animal health certificate from veterinarian. Tag number 123. Purchase receipt ownership proof. Valuation certificate by valuer. Photograph of animal."),
        product_id="livestock_cattle",
    )
    pet = underwrite_general(
        _bundle("Identity Aadhaar. Vaccination record. Medical history health certificate. Breed and age proof adoption papers. Photograph of pet."),
        product_id="pet_insurance",
    )
    assert live.gates.get("valuation") == "pass"
    assert "valuation" not in pet.gates
    assert "animal_id" in live.gates
    assert pet.gates.get("vaccination") == "pass"
    assert "vaccination" not in live.gates
    assert live.metadata["subject"] == "livestock"
    assert pet.metadata["subject"] == "pet"


def test_wedding_vs_concert_distinctness():
    wedding = underwrite_general(
        _bundle("Identity. Address proof. Wedding date 12 Dec venue banquet. Budget breakdown. Vendor contracts caterer decorator. Advance payment receipts."),
        product_id="wedding_insurance",
    )
    concert = underwrite_general(
        _bundle("GST registration. Venue booking agreement. Event license from local authority. Artist contracts. Ticket sales projection budget."),
        product_id="concert_event_insurance",
    )
    assert wedding.gates.get("vendors") == "pass"
    assert "gst" not in wedding.gates
    assert "permit" not in wedding.gates
    assert concert.gates.get("gst") == "pass"
    assert concert.gates.get("permit") == "pass"
    assert concert.gates.get("budget") == "pass"
    assert wedding.metadata["event_type"] == "wedding"
    assert concert.metadata["event_type"] == "public_concert"


def test_title_requires_full_legal_history():
    t = underwrite_general(
        _bundle("Identity Aadhaar. Address proof. Sale deed title deed. Ownership chain 30 year records. Encumbrance certificate. Property tax receipts. Survey site plan. Legal title search report."),
        product_id="title_insurance_gi",
    )
    assert t.gates.get("chain") == "pass"
    assert t.gates.get("encumbrance") == "pass"
    assert t.gates.get("title_search") == "pass"
    assert t.gates.get("survey") == "pass"
    assert t.decision == UWDecision.ACCEPT


def test_mortgage_requires_sanction_income_and_statement():
    m = underwrite_general(
        _bundle("Identity. Address proof. Loan sanction letter from bank. Property documents linked to mortgage. Income proof salary ITR. Age proof. Loan account statement."),
        product_id="mortgage_insurance_gi",
    )
    assert m.gates.get("sanction") == "pass"
    assert m.gates.get("income") == "pass"
    assert m.gates.get("loan_stmt") == "pass"
    assert m.decision == UWDecision.ACCEPT


def test_provider_channel_distinctness():
    psu = underwrite_general(
        _bundle("Identity. Address proof. Age proof. Photograph. Aadhaar-linked verification. Category certificate for subsidy scheme."),
        product_id="insurer_psu",
    )
    private = underwrite_general(
        _bundle("Identity. Address proof. Age proof. Photograph. e-KYC via Aadhaar PAN. Income proof for high sum insured product."),
        product_id="insurer_private",
    )
    rei = underwrite_general(
        _bundle(
            "Ceding insurer registration license. Treaty facultative reinsurance agreement. Risk portfolio details. Loss history claims data. Solvency financial statements. IRDAI regulatory approval."
        ),
        product_id="reinsurance_treaty",
    )
    assert psu.gates.get("aadhaar_link") == "pass"
    assert "aadhaar_link" not in private.gates
    assert psu.gates.get("category_if_subsidy") == "pass"
    assert private.gates.get("ekyc") == "pass"
    assert private.gates.get("income_if_high_si") == "pass"
    assert rei.gates.get("treaty") == "pass"
    assert rei.gates.get("ceding_license") == "pass"
    assert rei.gates.get("solvency") == "pass"
    assert rei.gates.get("regulator") == "pass"
    assert psu.metadata["channel"] == "psu"
    assert private.metadata["channel"] == "private"


def test_marine_cargo_vs_hull():
    cargo = underwrite_general(_bundle("Commercial invoice of goods. GST certificate."), product_id="marine_cargo")
    hull = underwrite_general(_bundle("GST company registration."), product_id="marine_hull")
    assert cargo.product_family == "marine_cargo"
    assert hull.product_family == "marine_hull"
    assert "kyc_identity" not in cargo.gates
    assert "kyc_identity" not in hull.gates
    assert cargo.gates.get("bl_awb") == "fail"
    assert hull.gates.get("vessel_reg") == "fail"
    assert "vessel_reg" not in cargo.gates
    assert "bl_awb" not in hull.gates
    assert "cargo_value" in cargo.gates
    assert "vessel_age" in hull.gates
    assert "cargo_value" not in hull.gates
    assert "vessel_age" not in cargo.gates


def test_marine_cargo_hazardous_and_perishable_gates():
    haz = underwrite_general(
        _bundle("Commercial invoice of goods. Bill of lading. Packing list. Hazardous flammable chemicals. Cargo value 5000000. Sea freight to Rotterdam."),
        product_id="marine_cargo",
    )
    assert haz.gates.get("hazardous_cargo") == "fail"
    assert haz.metadata["hazardous"] is True
    assert haz.metadata["cargo_risk_class"] == "high"
    clean = underwrite_general(
        _bundle("Commercial invoice of goods. Airway bill. Packing list. General merchandise stationery. Cargo value 3000000. Port of loading Mundra, destination Jebel Ali."),
        product_id="marine_cargo",
    )
    assert clean.gates.get("hazardous_cargo") is None
    assert clean.gates.get("perishable_cargo") is None
    assert clean.metadata["cargo_risk_class"] == "low"
    assert clean.gates.get("cargo_value") == "pass"
    assert clean.gates.get("transit_route") == "pass"


def test_marine_hull_age_and_laid_up_gates():
    hull = underwrite_general(
        _bundle("Vessel registration IMO number. Hull valuation 8000000. Classification society certificate. Vessel ownership. Year built 2015. Trading area coastal. No prior claims."),
        product_id="marine_hull",
    )
    assert hull.gates.get("vessel_age") == "pass"
    assert hull.metadata["vessel_age"] == 11
    assert hull.gates.get("class_cert") == "pass"
    assert hull.gates.get("hull_history") == "pass"
    laid = underwrite_general(
        _bundle(
            "Vessel registration. Hull valuation 5000000. Seaworthiness certificate. Vessel ownership. "
            "Crew list. GST company registration. Vessel laid up at mooring. Year built 2010. Coastal voyage. No losses."
        ),
        product_id="marine_hull",
    )
    assert laid.gates.get("laid_up_warranty") == "fail"
    assert laid.metadata["laid_up"] is True
    assert laid.decision == UWDecision.CONDITIONAL_ACCEPT
    old = underwrite_general(
        _bundle("Ship registration. Hull valuation 3000000. Class certificate. Year built 1995. River barge inland waterways. No claims."),
        product_id="marine_hull",
    )
    assert old.metadata["vessel_age"] == 31
    assert old.metadata["hull_risk_class"] == "high"


def test_marine_cargo_ignores_hull_domain():
    hull_text = "Vessel registration IMO number. Classification society. Hull valuation 9000000. Year built 2012. Crew list. Trading area coastal."
    cargo = underwrite_general(_bundle(hull_text), product_id="marine_cargo")
    assert cargo.gates.get("bl_awb") == "fail"
    assert "vessel_age" not in cargo.gates
    assert "class_cert" not in cargo.gates
    assert "crew" not in cargo.gates


def test_fire_commercial_requires_fire_safety_residential_does_not():
    res = underwrite_general(_bundle(KYC + " Sale deed ownership. Valuation report. Photograph."), product_id="fire_residential")
    comm = underwrite_general(_bundle("GST company registration. Lease factory. Valuation machinery."), product_id="fire_commercial")
    assert "fire_safety" not in res.gates
    assert comm.gates.get("fire_safety") == "fail"
    assert comm.metadata.get("occupancy") == "commercial_industrial"


def test_fire_residential_kyc_and_construction_gates():
    res = underwrite_general(
        _bundle(
            "Aadhaar identity. Address proof. Sale deed ownership. Property valuation 5000000. RCC construction. "
            "Owner occupied. Year built 2018. Fire extinguishers installed. No prior fire claims. Photograph."
        ),
        product_id="fire_residential",
    )
    assert res.gates.get("kyc_identity") == "pass"
    assert res.gates.get("construction_type") == "pass"
    assert res.gates.get("protection_measures") == "pass"
    assert res.metadata["building_age"] == 8
    assert res.metadata["fire_risk_class"] == "low"
    old = underwrite_general(
        _bundle("Aadhaar. Address proof. Sale deed. Property valuation 3000000. Wooden construction thatched roof. Year built 1975. Owner occupied. Fire extinguisher. No claims."),
        product_id="fire_residential",
    )
    assert old.metadata["building_age"] == 51
    assert old.metadata["fire_risk_class"] == "high"


def test_fire_commercial_combustible_stock_gate():
    comm = underwrite_general(
        _bundle(
            "GST company registration. Factory lease. Asset valuation building machinery stock 10000000. "
            "Fire safety NOC. Stock inventory statement. Textiles plastic chemicals. Sprinkler and hydrant system. No fire losses."
        ),
        product_id="fire_commercial",
    )
    assert comm.gates.get("fire_safety") == "pass"
    assert comm.gates.get("suppression_system") == "pass"
    assert comm.gates.get("combustible_storage") is None
    assert comm.metadata["combustible_storage"] is True
    assert comm.metadata["fire_risk_class"] == "high"
    exposed = underwrite_general(
        _bundle("GST company registration. Factory lease. Asset valuation 10000000. Stock of paper and chemicals. No sprinklers."),
        product_id="fire_commercial",
    )
    assert exposed.gates.get("combustible_storage") == "fail"
    assert exposed.gates.get("fire_safety") == "fail"


def test_fire_residential_ignores_commercial_domain():
    comm_text = "GST company registration. Lease factory. Asset valuation machinery. Fire safety NOC. Stock inventory statement. Fire sprinklers."
    res = underwrite_general(_bundle(comm_text), product_id="fire_residential")
    assert res.gates.get("construction_type") == "fail"
    assert "fire_safety" not in res.gates
    assert "stock" not in res.gates
    assert "suppression_system" not in res.gates


def test_pi_license_vs_public_gst_vs_product_mfg():
    pi = underwrite_general(_bundle(KYC), product_id="professional_indemnity_gi")
    pub = underwrite_general(_bundle("Nature of business retail store."), product_id="public_liability_gi")
    prod = underwrite_general(_bundle("GST company registration. Product catalog SKU. Recall history."), product_id="product_liability_gi")
    assert pi.gates.get("license") == "fail"
    assert "license" not in pub.gates
    assert "license" not in prod.gates
    assert pub.gates.get("company_registration") == "fail"
    assert prod.gates.get("manufacturing_license") == "fail"
    assert prod.gates.get("open_recall") == "fail"


def test_cyber_breach_vs_ransomware():
    breach = underwrite_general(_bundle("GST company registration."), product_id="cyber_data_breach")
    ransom = underwrite_general(_bundle("GST company registration."), product_id="cyber_ransomware")
    assert breach.product_family == "cyber_data_breach"
    assert ransom.product_family == "cyber_ransomware"
    assert breach.gates.get("data_volume") == "fail"
    assert "data_volume" not in ransom.gates
    assert ransom.gates.get("controls") == "fail"
    assert "controls" not in breach.gates
    assert "company_registration" in breach.gates
    assert "business_registration" in ransom.gates
    assert "company_registration" not in ransom.gates
    assert "business_registration" not in breach.gates


def test_cyber_breach_sensitive_data_and_severity_gates():
    sensitive = underwrite_general(
        _bundle("GST company registration. Handles medical records of 250000 patients. Data security policy in place."),
        product_id="cyber_data_breach",
    )
    assert sensitive.gates.get("sensitive_data_controls") == "fail"
    assert sensitive.metadata["sensitive_data"] is True
    assert sensitive.metadata["data_volume_records"] == 250000
    clean = underwrite_general(
        _bundle("GST company registration. Data security policy in place. Handles 50000 records. Encryption and DPDP consent controls in place. No prior breach."),
        product_id="cyber_data_breach",
    )
    assert clean.gates.get("sensitive_data_controls") == "pass"
    assert clean.gates.get("data_policy") == "pass"
    severe = underwrite_general(
        _bundle("GST company registration. Data volume 100000 records. Prior breach critical incident with customer data leaked. Encryption in place."),
        product_id="cyber_data_breach",
    )
    assert severe.gates.get("breach_severity") == "fail"
    assert severe.metadata["breach_severity"] == "critical"


def test_cyber_ransom_remote_access_and_backups_gates():
    exposed = underwrite_general(
        _bundle("GST company registration. IT infrastructure details. MFA and EDR controls. RDP exposed to internet. No prior attack."),
        product_id="cyber_ransomware",
    )
    assert exposed.gates.get("remote_access_exposure") == "fail"
    assert exposed.metadata["has_remote_access"] is True
    protected = underwrite_general(
        _bundle("GST company registration. Network details. EDR MFA firewall. Offline immutable 3-2-1 backups. No incident history."),
        product_id="cyber_ransomware",
    )
    assert protected.gates.get("backup_discipline") == "pass"
    assert protected.gates.get("controls") == "pass"
    assert "remote_access_exposure" not in protected.gates
    prior = underwrite_general(
        _bundle("GST company registration. Network details. MFA EDR. Backups. Prior ransomware extortion demand multiple incidents."),
        product_id="cyber_ransomware",
    )
    assert prior.gates.get("ransom_severity") == "fail"
    assert prior.metadata["ransom_severity"] == "critical"


def test_cyber_breach_ignores_ransom_domain():
    ransom_text = "GST company registration. IT infrastructure RDP exposed. MFA EDR controls. Ransomware attack history."
    breach = underwrite_general(_bundle(ransom_text), product_id="cyber_data_breach")
    assert breach.gates.get("data_volume") == "fail"
    assert "remote_access_exposure" not in breach.gates
    assert "controls" not in breach.gates


def test_crop_yield_acreage_vs_weather_station():
    land = "Land ownership khasra khatauni. Aadhaar identity. Bank account IFSC. Sowing certificate crop sown."
    yield_uw = underwrite_general(_bundle(land), product_id="crop_yield")
    weather = underwrite_general(_bundle(land), product_id="crop_weather")
    assert yield_uw.gates.get("acreage") == "fail"
    assert "weather_station" not in yield_uw.gates
    assert weather.gates.get("weather_station") == "fail"
    assert "acreage" not in weather.gates
    assert "kyc_identity" not in yield_uw.gates


def test_livestock_vet_tag_vs_pet_vaccination():
    owner = KYC
    livestock = underwrite_general(_bundle(owner), product_id="livestock_cattle")
    pet = underwrite_general(_bundle(owner), product_id="pet_insurance")
    assert livestock.gates.get("vet_health") == "fail"
    assert livestock.gates.get("animal_id") == "fail"
    assert "vaccination" not in livestock.gates
    assert pet.gates.get("vaccination") == "fail"
    assert "animal_id" not in pet.gates


def test_wedding_vs_concert_permit():
    wedding = underwrite_general(_bundle(KYC + " Wedding date venue budget breakdown."), product_id="wedding_insurance")
    concert = underwrite_general(_bundle("GST business registration. Venue booking agreement. Artist vendor contract. Ticket sales budget projection."), product_id="concert_event_insurance")
    assert wedding.product_family == "wedding_insurance"
    assert concert.product_family == "concert_event"
    assert "permit" not in wedding.gates
    assert concert.gates.get("permit") == "fail"
    assert "kyc_identity" not in concert.gates


def test_title_encumbrance_and_search():
    title = underwrite_general(_bundle(KYC + " Sale deed title deed."), product_id="title_insurance_gi")
    assert title.gates.get("encumbrance") == "fail"
    assert title.gates.get("title_search") == "fail"
    assert title.gates.get("chain") == "fail"


def test_mortgage_requires_sanction():
    gi = underwrite_general(_bundle(KYC + " Income proof salary slips ITR. Age proof."), product_id="mortgage_insurance_gi")
    assert gi.gates.get("sanction") == "fail"
    assert gi.gates.get("loan_stmt") == "fail"


def test_psu_aadhaar_vs_private_ekyc_vs_reinsurance_b2b():
    no_aadhaar = "Identity proof PAN card. Address proof utility bill. ID + address proof of owner. Age: 34."
    psu = underwrite_general(_bundle(no_aadhaar + " Photograph. Age proof."), product_id="insurer_psu")
    private = underwrite_general(_bundle(KYC + " Photograph. Age proof. Digital e-KYC PAN."), product_id="insurer_private")
    re = underwrite_general(_bundle("Ceding insurer IRDAI license. Treaty facultative reinsurance agreement."), product_id="reinsurance_treaty")
    assert psu.gates.get("aadhaar_link") == "fail"
    assert private.gates.get("ekyc") == "pass"
    assert "kyc_identity" not in re.gates
    assert re.gates.get("treaty") == "pass"
    assert re.gates.get("ceding_license") == "pass"
    assert re.gates.get("solvency") == "fail"
    assert any("b2b" in c.lower() or "not individual" in c.lower() for c in re.conditions)


def test_liability_handlers_use_disjoint_domain_gates():
    pi = underwrite_general(
        _bundle(KYC + " Professional license. Practice registration. No claims. Gross fees 1000000. Indemnity limit 2000000."),
        product_id="professional_indemnity_gi",
    )
    pub = underwrite_general(
        _bundle("GST. Lease premises. Nature of business office. No claims. Turnover 5000000. Indemnity limit 2000000."),
        product_id="public_liability_gi",
    )
    prod = underwrite_general(
        _bundle("GST. Product catalog. Manufacturing license. ISO. No recall. No claims."),
        product_id="product_liability_gi",
    )
    assert pi.decision == UWDecision.ACCEPT
    assert pub.decision == UWDecision.ACCEPT
    assert prod.decision == UWDecision.ACCEPT
    assert not (set(pi.gates) & set(pub.gates))
    assert not (set(pi.gates) & set(prod.gates))
    assert not (set(pub.gates) & set(prod.gates))
    assert pi.metadata["profession_risk_class"] == "low"
    assert pub.metadata["occupancy_hazard_class"] == "low"
    assert prod.metadata["product_risk_class"] == "low"


def test_pi_high_risk_profession_refers():
    text = KYC + " Professional license bar council. Practice registration GST. No claims. Gross fees 1000000. Indemnity limit 2000000. Lawyer advocate litigation."
    d = underwrite_general(_bundle(text), product_id="professional_indemnity_gi")
    assert d.gates.get("profession_risk_class") == "fail"
    assert d.metadata["profession_risk_class"] == "high"
    assert d.decision == UWDecision.REFER


def test_pi_limit_exceeds_fees_capacity_band():
    text = KYC + " Professional license. Practice registration. No claims. Gross fees 500000. Indemnity limit 5000000."
    d = underwrite_general(_bundle(text), product_id="professional_indemnity_gi")
    assert d.gates.get("limit_vs_fees") == "fail"
    assert d.metadata["limit_fees_ratio"] == 10.0
    assert d.decision == UWDecision.REFER


def test_pi_staff_without_supervision_conditional():
    text = KYC + " Professional license. Practice registration. No claims. Gross fees 1000000. Indemnity limit 2000000. Associates and staff employees."
    d = underwrite_general(_bundle(text), product_id="professional_indemnity_gi")
    assert d.gates.get("staff_supervision") == "fail"
    assert d.decision == UWDecision.CONDITIONAL_ACCEPT


def test_public_liability_hazard_and_crowd_refer():
    text = "GST. Lease premises. Nature of business fireworks storage and event management. No claims. Turnover 10000000. Indemnity limit 2000000."
    d = underwrite_general(_bundle(text), product_id="public_liability_gi")
    assert d.gates.get("occupancy_hazard_class") == "fail"
    assert d.gates.get("crowd_operations") == "fail"
    assert d.decision == UWDecision.REFER


def test_public_liability_retail_footfall_conditional():
    text = "GST. Lease premises. Nature of business retail showroom open to public. No claims. Turnover 5000000. Indemnity limit 2000000."
    d = underwrite_general(_bundle(text), product_id="public_liability_gi")
    assert d.gates.get("public_access_exposure") == "fail"
    assert d.gates.get("safety_controls") == "fail"
    assert d.decision == UWDecision.CONDITIONAL_ACCEPT


def test_public_liability_claims_severity_refer():
    text = "GST. Lease premises. Nature of business restaurant. Claims history with bodily injury claim. Turnover 5000000. Indemnity limit 2000000."
    d = underwrite_general(_bundle(text), product_id="public_liability_gi")
    assert d.gates.get("third_party_claims_severity") == "fail"
    assert d.decision == UWDecision.REFER


def test_product_liability_open_recall_declines():
    text = "GST. Product catalog SKU. Manufacturing license. Recall history unresolved recall pending."
    d = underwrite_general(_bundle(text), product_id="product_liability_gi")
    assert d.gates.get("open_recall") == "fail"
    assert d.decision == UWDecision.DECLINE


def test_product_liability_high_risk_class_refers():
    text = "GST. Product catalog SKU. Manufacturing license FSSAI. Food and beverage products. No recall. No claims."
    d = underwrite_general(_bundle(text), product_id="product_liability_gi")
    assert d.gates.get("product_risk_class") == "fail"
    assert d.metadata["product_risk_class"] == "high"
    assert d.decision == UWDecision.REFER


def test_product_liability_retail_distribution_conditional():
    text = "GST. Product catalog. Manufacturing license. ISO. No recall. No claims. Products sold at retail to consumers."
    d = underwrite_general(_bundle(text), product_id="product_liability_gi")
    assert d.gates.get("distribution_channel") == "fail"
    assert d.metadata["distribution"] == "retail"
    assert d.decision == UWDecision.CONDITIONAL_ACCEPT


def test_general_product_terms_distinct():
    tp = general_product_terms("car_tp")
    comp = general_product_terms("car_comprehensive")
    cargo = general_product_terms("marine_cargo")
    re = general_product_terms("reinsurance_treaty")
    assert tp["benefit_type"] == "motor_third_party"
    assert comp["benefit_type"] == "motor_comprehensive"
    assert cargo["benefit_type"] == "marine_cargo"
    assert re["benefit_type"] == "reinsurance_b2b"
