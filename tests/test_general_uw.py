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


def test_fire_commercial_requires_fire_safety_residential_does_not():
    res = underwrite_general(_bundle(KYC + " Sale deed ownership. Valuation report. Photograph."), product_id="fire_residential")
    comm = underwrite_general(_bundle("GST company registration. Lease factory. Valuation machinery."), product_id="fire_commercial")
    assert "fire_safety" not in res.gates
    assert comm.gates.get("fire_safety") == "fail"
    assert comm.metadata.get("occupancy") == "commercial_industrial"


def test_pi_license_vs_public_gst_vs_product_mfg():
    pi = underwrite_general(_bundle(KYC), product_id="professional_indemnity_gi")
    pub = underwrite_general(_bundle("Nature of business retail store."), product_id="public_liability_gi")
    prod = underwrite_general(_bundle("GST company registration. Product catalog SKU. Recall history."), product_id="product_liability_gi")
    assert pi.gates.get("license") == "fail"
    assert "license" not in pub.gates
    assert "license" not in prod.gates
    assert pub.gates.get("gst") == "fail"
    assert prod.gates.get("mfg_license") == "fail"
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


def test_general_product_terms_distinct():
    tp = general_product_terms("car_tp")
    comp = general_product_terms("car_comprehensive")
    cargo = general_product_terms("marine_cargo")
    re = general_product_terms("reinsurance_treaty")
    assert tp["benefit_type"] == "motor_third_party"
    assert comp["benefit_type"] == "motor_comprehensive"
    assert cargo["benefit_type"] == "marine_cargo"
    assert re["benefit_type"] == "reinsurance_b2b"
