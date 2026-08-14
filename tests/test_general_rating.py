"""General rating via filed rate manuals — liability + cyber."""

from __future__ import annotations

from insureflow.models.submissions import SubmissionBundle, UnstructuredSubmission
from insureflow.rating.models import InsuranceLine
from insureflow.rating.personal.general_rating import rate_general


def _bundle(text: str) -> SubmissionBundle:
    return SubmissionBundle(
        bundle_id="gi-rate",
        unstructured=[
            UnstructuredSubmission(
                submission_id="d1",
                source="general_application",
                document_type="general_application",
                raw_text=text,
            )
        ],
    )


def test_cyber_breach_rates_from_filed_manual():
    q = rate_general(
        _bundle("Revenue 20000000. Indemnity limit 10000000. Hospital healthcare data records."),
        product_id="cyber_data_breach",
    )
    assert q.eligible is True
    assert q.line == InsuranceLine.GENERAL
    assert q.adjusted_premium > 0
    assert q.metadata["rating_engine"] == "general_cyber_filing"
    assert q.metadata["filed"] is True
    assert q.metadata["indemnity_limit"] == 10_000_000
    assert q.metadata["exposure"] == 20_000_000
    assert q.metadata["risk_class"] == "high"


def test_cyber_ransomware_rates_from_filed_manual():
    q = rate_general(
        _bundle("Revenue 30000000. Indemnity limit 10000000. Cloud managed service provider."),
        product_id="cyber_ransomware",
    )
    assert q.eligible is True
    assert q.adjusted_premium > 0
    assert q.metadata["rating_engine"] == "general_cyber_filing"
    assert q.metadata["risk_class"] == "high"
    q_low = rate_general(
        _bundle("Revenue 30000000. Indemnity limit 10000000. Small office general services."),
        product_id="cyber_ransomware",
    )
    assert q_low.metadata["risk_class"] == "low"
    assert q.adjusted_premium > q_low.adjusted_premium


def test_cyber_limit_exceeds_revenue_cap_ineligible():
    q = rate_general(_bundle("Revenue 1000000. Indemnity limit 10000000."), product_id="cyber_data_breach")
    assert q.eligible is False
    assert q.adjusted_premium == 0.0
    assert any("2.0x filing cap" in r for r in q.ineligibility_reasons)


def test_cyber_missing_limit_is_ineligible_without_invented_premium():
    q = rate_general(_bundle("Revenue 5000000. E-commerce."), product_id="cyber_ransomware")
    assert q.eligible is False
    assert q.adjusted_premium == 0.0
    assert any("limit not declared" in r for r in q.ineligibility_reasons)


def test_marine_cargo_rates_on_cargo_value():
    q = rate_general(
        _bundle("Cargo value 10000000. Sum insured 10000000. General merchandise stationery. Sea freight."),
        product_id="marine_cargo",
    )
    assert q.eligible is True
    assert q.line == InsuranceLine.GENERAL
    assert q.adjusted_premium > 0
    assert q.metadata["rating_engine"] == "general_marine_filing"
    assert q.metadata["filed"] is True
    assert q.metadata["exposure"] == 10_000_000
    assert q.metadata["risk_class"] == "low"
    q_high = rate_general(
        _bundle("Cargo value 10000000. Sum insured 10000000. Hazardous chemicals perishable seafood."),
        product_id="marine_cargo",
    )
    assert q_high.metadata["risk_class"] == "high"
    assert q_high.adjusted_premium > q.adjusted_premium


def test_marine_hull_rates_on_hull_value():
    q = rate_general(
        _bundle("Revenue 20000000. Sum insured 15000000. Container vessel well-classed. Year built 2018."),
        product_id="marine_hull",
    )
    assert q.eligible is True
    assert q.adjusted_premium > 0
    assert q.metadata["rating_engine"] == "general_marine_filing"
    assert q.metadata["risk_class"] == "low"
    q_high = rate_general(
        _bundle("Revenue 20000000. Sum insured 15000000. Fishing vessel wooden hull inland waterways."),
        product_id="marine_hull",
    )
    assert q_high.metadata["risk_class"] == "high"
    assert q_high.adjusted_premium > q.adjusted_premium


def test_marine_missing_value_is_ineligible_without_invented_premium():
    q = rate_general(_bundle("Cargo of textiles. Air freight."), product_id="marine_cargo")
    assert q.eligible is False
    assert q.adjusted_premium == 0.0
    assert any("limit not declared" in r for r in q.ineligibility_reasons)


def test_fire_residential_rates_from_filed_manual():
    q = rate_general(
        _bundle("Property value 5000000. Sum insured 5000000. RCC concrete construction. Year built 2018."),
        product_id="fire_residential",
    )
    assert q.eligible is True
    assert q.line == InsuranceLine.GENERAL
    assert q.adjusted_premium > 0
    assert q.metadata["rating_engine"] == "general_fire_filing"
    assert q.metadata["filed"] is True
    assert q.metadata["exposure"] == 5_000_000
    assert q.metadata["risk_class"] == "low"
    q_old = rate_general(
        _bundle("Property value 5000000. Sum insured 5000000. Wooden construction thatched. Year built 1975."),
        product_id="fire_residential",
    )
    assert q_old.metadata["risk_class"] == "high"
    assert q_old.adjusted_premium > q.adjusted_premium


def test_fire_commercial_rates_from_filed_manual():
    q = rate_general(
        _bundle("Asset value 20000000. Sum insured 20000000. Office software services."),
        product_id="fire_commercial",
    )
    assert q.eligible is True
    assert q.adjusted_premium > 0
    assert q.metadata["rating_engine"] == "general_fire_filing"
    assert q.metadata["risk_class"] == "low"
    q_high = rate_general(
        _bundle("Asset value 20000000. Sum insured 20000000. Textiles paper chemicals factory."),
        product_id="fire_commercial",
    )
    assert q_high.metadata["risk_class"] == "high"
    assert q_high.adjusted_premium > q.adjusted_premium


def test_fire_missing_sum_insured_is_ineligible():
    q = rate_general(_bundle("Property value 3000000. RCC construction."), product_id="fire_residential")
    assert q.eligible is False
    assert q.adjusted_premium == 0.0
    assert any("limit not declared" in r for r in q.ineligibility_reasons)


def test_travel_domestic_rates_with_duration_factor():
    q = rate_general(
        _bundle("Sum insured 10000000. Medical cover 10000000. Trip duration 21 days. Trip cost 50000. Traveling to Jaipur."),
        product_id="travel_domestic",
    )
    assert q.eligible is True
    assert q.line == InsuranceLine.GENERAL
    assert q.adjusted_premium > 0
    assert q.metadata["rating_engine"] == "general_travel_filing"
    assert q.metadata["filed"] is True
    assert q.metadata["duration_days"] == 21
    assert any(comp.name == "trip_duration" for comp in q.schedule_modifications)
    q_short = rate_general(
        _bundle("Sum insured 10000000. Medical cover 10000000. Trip duration 3 days. Trip cost 30000. Traveling to Delhi."),
        product_id="travel_domestic",
    )
    assert q_short.metadata["duration_days"] == 3
    assert q.adjusted_premium > q_short.adjusted_premium


def test_travel_international_rates_with_destination_class():
    q = rate_general(
        _bundle("Sum insured 10000000. Medical limit 10000000. Trip duration 14 days. Trip cost 200000. Traveling to USA."),
        product_id="travel_international",
    )
    assert q.eligible is True
    assert q.adjusted_premium > 0
    assert q.metadata["rating_engine"] == "general_travel_filing"
    assert q.metadata["risk_class"] == "high"
    q_low = rate_general(
        _bundle("Sum insured 10000000. Medical limit 10000000. Trip duration 14 days. Trip cost 100000. Traveling to Thailand."),
        product_id="travel_international",
    )
    assert q_low.metadata["risk_class"] == "low"
    assert q.adjusted_premium > q_low.adjusted_premium


def test_travel_missing_medical_limit_is_ineligible():
    q = rate_general(_bundle("Trip duration 7 days. Trip cost 40000. Traveling to Goa."), product_id="travel_domestic")
    assert q.eligible is False
    assert q.adjusted_premium == 0.0
    assert any("limit not declared" in r for r in q.ineligibility_reasons)


def test_home_three_leaves_rating_distinctness():
    struct = rate_general(
        _bundle("Sum insured 20000000. Building sum insured 20000000. Property value 30000000. RCC construction. Coastal location."),
        product_id="home_structure",
    )
    contents = rate_general(
        _bundle("Sum insured 10000000. Contents sum insured 10000000. Declared contents value 12000000. Jewellery and electronics."),
        product_id="home_contents",
    )
    comp = rate_general(
        _bundle("Sum insured 30000000. Comprehensive cover 30000000. Property value 40000000. Alarm installed."),
        product_id="home_comprehensive",
    )
    assert struct.eligible is True and contents.eligible is True and comp.eligible is True
    assert struct.metadata["rating_engine"] == "general_home_filing"
    assert contents.metadata["rating_engine"] == "general_home_filing"
    assert comp.metadata["rating_engine"] == "general_home_filing"
    assert struct.metadata["filed"] is True
    assert struct.metadata["risk_class"] == "high"
    assert contents.metadata["risk_class"] == "high"
    assert comp.metadata["risk_class"] == "low"
    assert contents.adjusted_premium / 10.0 > struct.adjusted_premium / 20.0
    assert comp.adjusted_premium > 0


def test_home_structure_above_replacement_value_ineligible():
    q = rate_general(
        _bundle("Sum insured 50000000. Property value 20000000. RCC construction."),
        product_id="home_structure",
    )
    assert q.eligible is False
    assert any("filing cap" in r for r in q.ineligibility_reasons)


def test_home_contents_missing_sum_insured_ineligible():
    q = rate_general(_bundle("Declared contents value 5000000. Jewellery."), product_id="home_contents")
    assert q.eligible is False
    assert any("limit not declared" in r for r in q.ineligibility_reasons)


def test_motor_six_leaves_rating_distinctness():
    limits = {
        "car_tp": 10000000,
        "car_comprehensive": 10000000,
        "tw_tp": 10000000,
        "tw_comprehensive": 10000000,
        "cv_tp": 10000000,
        "cv_comprehensive": 10000000,
    }
    quotes = {}
    for pid, lim in limits.items():
        q = rate_general(_bundle(f"Sum insured {lim}. Cover limit {lim}. Registration certificate. Vehicle."), product_id=pid)
        assert q.eligible is True, pid
        assert q.metadata["rating_engine"] == "general_motor_filing"
        assert q.metadata["filed"] is True
        quotes[pid] = q.adjusted_premium
    assert quotes["cv_comprehensive"] > quotes["car_comprehensive"]
    assert quotes["car_comprehensive"] > quotes["tw_comprehensive"]
    assert quotes["cv_tp"] > quotes["car_tp"]
    assert quotes["car_tp"] > quotes["tw_tp"]
    assert quotes["car_comprehensive"] > quotes["car_tp"]
    assert quotes["tw_comprehensive"] > quotes["tw_tp"]
    assert quotes["cv_comprehensive"] > quotes["cv_tp"]


def test_motor_risk_class_escalates_premium():
    low = rate_general(
        _bundle("Sum insured 10000000. IDV 10000000. Hatchback city car. Registration certificate."),
        product_id="car_comprehensive",
    )
    high = rate_general(
        _bundle("Sum insured 10000000. IDV 10000000. Luxury imported sports car. Registration certificate."),
        product_id="car_comprehensive",
    )
    assert low.metadata["risk_class"] == "low"
    assert high.metadata["risk_class"] == "high"
    assert high.adjusted_premium > low.adjusted_premium


def test_motor_tw_high_cc_rates_high():
    scooter = rate_general(
        _bundle("Sum insured 1000000. Cover limit 1000000. Scooter gearless 100cc. RC of vehicle."),
        product_id="tw_tp",
    )
    superbike = rate_general(
        _bundle("Sum insured 1000000. Cover limit 1000000. Superbike 650cc. RC of vehicle."),
        product_id="tw_tp",
    )
    assert scooter.metadata["risk_class"] == "low"
    assert superbike.metadata["risk_class"] == "high"
    assert superbike.adjusted_premium > scooter.adjusted_premium


def test_motor_comprehensive_idv_cap_vs_tp_no_cap():
    comp = rate_general(
        _bundle("Sum insured 20000000. Vehicle value 10000000. Registration certificate."),
        product_id="car_comprehensive",
    )
    tp = rate_general(
        _bundle("Sum insured 20000000. Vehicle value 10000000. Registration certificate."),
        product_id="car_tp",
    )
    assert comp.eligible is False
    assert any("filing cap" in r for r in comp.ineligibility_reasons)
    assert tp.eligible is True


def test_motor_cv_comprehensive_requires_limit():
    q = rate_general(_bundle("Registration certificate. Fitness certificate. Permit."), product_id="cv_comprehensive")
    assert q.eligible is False
    assert any("limit not declared" in r for r in q.ineligibility_reasons)


def test_specialty_leaves_all_rate():
    quotes = {
        pid: rate_general(_bundle(f"Sum insured 10000000. Cover limit 10000000. {kw}"), product_id=pid)
        for pid, kw in {
            "crop_yield": "Khasra paddy irrigated",
            "crop_weather": "IMD weather station grape",
            "livestock_cattle": "Animal value 12000000. Jersey breed",
            "pet_insurance": "Pet value. Pedigree dog",
            "wedding_insurance": "Event budget 15000000. Venue banquet",
            "concert_event_insurance": "Event budget 20000000. Outdoor arena",
            "title_insurance_gi": "Property value 30000000. Clean title registered sale deed",
            "mortgage_insurance_gi": "Loan outstanding 25000000. Salaried first loan",
            "insurer_psu": "Government backing. Sum insured 10000000",
            "insurer_private": "Private insurer. Sum insured 10000000",
            "reinsurance_treaty": "Treaty limit. Established cedant",
        }.items()
    }
    for pid, q in quotes.items():
        assert q.eligible is True, pid
        assert q.metadata["rating_engine"] == "general_specialty_filing"
        assert q.metadata["filed"] is True
        assert q.adjusted_premium > 0
    assert quotes["reinsurance_treaty"].adjusted_premium > quotes["livestock_cattle"].adjusted_premium
    assert quotes["livestock_cattle"].adjusted_premium > quotes["pet_insurance"].adjusted_premium
    assert quotes["crop_yield"].adjusted_premium > quotes["crop_weather"].adjusted_premium
    assert quotes["concert_event_insurance"].adjusted_premium > quotes["wedding_insurance"].adjusted_premium
    assert quotes["mortgage_insurance_gi"].adjusted_premium > quotes["title_insurance_gi"].adjusted_premium
    assert quotes["insurer_private"].adjusted_premium > quotes["insurer_psu"].adjusted_premium


def test_specialty_risk_class_escalates():
    clean = rate_general(
        _bundle("Sum insured 10000000. Property value 20000000. Registered sale deed clean title marketable title."),
        product_id="title_insurance_gi",
    )
    dispute = rate_general(
        _bundle("Sum insured 10000000. Property value 20000000. Litigation dispute forged encumbrance defective title."),
        product_id="title_insurance_gi",
    )
    assert clean.metadata["risk_class"] == "low"
    assert dispute.metadata["risk_class"] == "high"
    assert dispute.adjusted_premium > clean.adjusted_premium


def test_specialty_indemnity_cap_and_missing_limit():
    over = rate_general(
        _bundle("Sum insured 50000000. Loan outstanding 20000000. Salaried."),
        product_id="mortgage_insurance_gi",
    )
    assert over.eligible is False
    assert any("filing cap" in r for r in over.ineligibility_reasons)
    no_limit = rate_general(_bundle("Jersey breed. Animal health certificate."), product_id="livestock_cattle")
    assert no_limit.eligible is False
    assert any("limit not declared" in r for r in no_limit.ineligibility_reasons)


def test_pi_rates_from_filed_manual():
    q = rate_general(
        _bundle("Gross fees 5000000. Indemnity limit 10000000. Software technology consulting."),
        product_id="professional_indemnity_gi",
    )
    assert q.eligible is True
    assert q.line == InsuranceLine.GENERAL
    assert q.adjusted_premium > 0
    assert q.metadata["rating_engine"] == "general_liability_filing"
    assert q.metadata["filed"] is True
    assert q.metadata["indemnity_limit"] == 10_000_000
    assert q.metadata["exposure"] == 5_000_000
    assert q.metadata["risk_class"] == "medium"
    assert any(comp.name == "risk_class" for comp in q.schedule_modifications)


def test_pi_high_risk_class_loads_premium():
    base = rate_general(
        _bundle("Gross fees 5000000. Indemnity limit 10000000. Software technology consulting."),
        product_id="professional_indemnity_gi",
    )
    high = rate_general(
        _bundle("Gross fees 5000000. Indemnity limit 10000000. Lawyer advocate litigation."),
        product_id="professional_indemnity_gi",
    )
    assert high.metadata["risk_class"] == "high"
    assert high.adjusted_premium > base.adjusted_premium


def test_pi_limit_exceeds_fees_cap_ineligible():
    q = rate_general(_bundle("Gross fees 1000000. Indemnity limit 10000000."), product_id="professional_indemnity_gi")
    assert q.eligible is False
    assert any("5.0x filing cap" in r for r in q.ineligibility_reasons)


def test_public_liability_rates_on_limit():
    q = rate_general(
        _bundle("Turnover 20000000. Indemnity limit 10000000. Office administration."),
        product_id="public_liability_gi",
    )
    assert q.eligible is True
    assert q.metadata["risk_class"] == "low"
    assert q.adjusted_premium > 0
    q_high = rate_general(
        _bundle("Turnover 20000000. Indemnity limit 10000000. Fireworks storage event."),
        product_id="public_liability_gi",
    )
    assert q_high.metadata["risk_class"] == "high"
    assert q_high.adjusted_premium > q.adjusted_premium


def test_product_liability_rates_on_declared_sales():
    q = rate_general(
        _bundle("Declared sales 20000000. Indemnity limit 2000000. Stationery packaging."),
        product_id="product_liability_gi",
    )
    assert q.eligible is True
    assert q.metadata["exposure"] == 20_000_000
    assert q.adjusted_premium > 0
    q_high = rate_general(
        _bundle("Declared sales 20000000. Indemnity limit 2000000. Food and beverage."),
        product_id="product_liability_gi",
    )
    assert q_high.metadata["risk_class"] == "high"
    assert q_high.adjusted_premium > q.adjusted_premium


def test_missing_limit_is_ineligible_without_invented_premium():
    q = rate_general(_bundle("Turnover 5000000. Office."), product_id="public_liability_gi")
    assert q.eligible is False
    assert q.adjusted_premium == 0.0
    assert any("limit not declared" in r for r in q.ineligibility_reasons)


def test_non_filed_general_product_stays_catalog_only():
    q = rate_general(_bundle("Yield crop insurance. Khasra certificate."), product_id="bogus_product")
    assert q.eligible is False
    assert q.adjusted_premium == 0.0
    assert q.metadata["rating_engine"] == "catalog_only"
    assert any("catalog-only" in r for r in q.ineligibility_reasons)
