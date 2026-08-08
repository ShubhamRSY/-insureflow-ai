"""Commercial LOB checklist flags + combined-risk scenario engine."""

from __future__ import annotations

from insureflow.models.agents import UWDecision
from insureflow.models.submissions import SubmissionBundle, UnstructuredSubmission
from insureflow.rating.models import InsuranceLine
from insureflow.underwriting.commercial_checklists import evaluate_commercial_checklist


def _bundle(text: str) -> SubmissionBundle:
    return SubmissionBundle(
        bundle_id="checklist-test",
        unstructured=[
            UnstructuredSubmission(
                submission_id="d1",
                source="app.md",
                raw_text=text,
                document_type="supplemental",
            )
        ],
    )


def _codes(result) -> set[str]:
    return {s.code for s in result.scenarios}


def _flag_codes(result) -> set[str]:
    return {f.code for f in result.flags}


def test_property_system_ages_and_flood_flag() -> None:
    text = "Commercial property. Roof age: 25 years. HVAC age: 22 years. Flood zone AE. Occupancy warehouse."
    result = evaluate_commercial_checklist(_bundle(text), InsuranceLine.COMMERCIAL_PROPERTY)
    flags = _flag_codes(result)
    assert "PROP_ROOF_AGE" in flags
    assert "PROP_HVAC_AGE" in flags
    assert "PROP_FLOOD_NO_ELEV" in flags
    assert "PROP_OCCUPANCY_HAZARD" in flags
    assert result.story


def test_property_fire_scenario() -> None:
    text = "Warehouse occupancy. No sprinkler system. Flammable chemical storage. Prior fire claim in 2024. Protection class: 9."
    result = evaluate_commercial_checklist(_bundle(text), InsuranceLine.COMMERCIAL_PROPERTY)
    assert "PROP_FIRE_SCENARIO" in _codes(result)
    assert result.decision == UWDecision.REFER
    assert result.premium_mod_pct >= 18.0
    action_types = {a.action_type.value for a in result.actions}
    assert "require_mitigation" in action_types
    assert "higher_deductible" in action_types
    assert "price_up" in action_types
    assert "fire" in result.story.lower() or "PROP_FIRE" in result.story


def test_do_distress_scenario() -> None:
    text = "D&O application. Down round completed Q1. Layoffs of 40 staff. Vacant board seat. Cash runway: 6 months. Burn rate: 250000."
    result = evaluate_commercial_checklist(_bundle(text), InsuranceLine.DIRECTORS_AND_OFFICERS)
    assert "DO_DISTRESS_SCENARIO" in _codes(result)
    assert "DO_DOWN_ROUND" in _flag_codes(result)
    assert "DO_LAYOFFS" in _flag_codes(result)
    assert result.decision == UWDecision.REFER
    assert any(a.action_type.value == "add_exclusion" for a in result.actions)
    assert result.premium_mod_pct >= 25.0


def test_wc_safety_scenario() -> None:
    text = "Workers compensation. Experience modification: 1.35. Open claims: 3. Injury frequency rising. Employee turnover: 45%."
    result = evaluate_commercial_checklist(_bundle(text), InsuranceLine.WORKERS_COMP)
    assert "WC_HIGH_EMOD" in _flag_codes(result)
    assert "WC_OPEN_CLAIMS" in _flag_codes(result)
    assert "WC_SAFETY_MISSING" in _flag_codes(result)
    assert "WC_SAFETY_SCENARIO" in _codes(result)
    assert result.decision == UWDecision.REFER
    assert any(a.action_type.value == "require_mitigation" for a in result.actions)
    assert result.premium_mod_pct >= 20.0


def test_trade_credit_concentration_geo_scenario() -> None:
    text = "Trade credit. Accounts receivable aging attached. Top buyer concentration: 55%. Buyer in emerging market with political risk. DSO: 75."
    result = evaluate_commercial_checklist(_bundle(text), InsuranceLine.TRADE_CREDIT)
    assert "TC_HIGH_CONCENTRATION" in _flag_codes(result)
    assert "TC_GEO_RISK" in _flag_codes(result)
    assert "TC_CONCENTRATION_SCENARIO" in _codes(result)
    assert "TC_CONCENTRATION_GEO_SCENARIO" in _codes(result)
    action_types = {a.action_type.value for a in result.actions}
    assert "cap_coverage" in action_types
    assert "require_doc" in action_types
    assert result.decision in (UWDecision.REFER, UWDecision.CONDITIONAL_ACCEPT)


def test_eo_contract_industry_claims_scenario() -> None:
    text = "E&O application. Guarantee of results in client contracts. New industry fintech crypto exposure. Prior claim malpractice claim 2023. Subcontractor reliance high."
    result = evaluate_commercial_checklist(_bundle(text), InsuranceLine.ERRORS_AND_OMISSIONS)
    assert "EO_CONTRACT_INDUSTRY_CLAIMS_SCENARIO" in _codes(result)
    assert result.decision in (UWDecision.REFER, UWDecision.CONDITIONAL_ACCEPT)
    action_types = {a.action_type.value for a in result.actions}
    assert "add_exclusion" in action_types or "require_mitigation" in action_types or "require_doc" in action_types


def test_key_person_succession_medical_scenario() -> None:
    text = "Key person insurance. Insured age: 64. Cardiac history heart attack. BMI: 34. Smoker. Revenue dependency: 55%. No succession plan. Face amount: $2,000,000."
    result = evaluate_commercial_checklist(_bundle(text), InsuranceLine.KEY_PERSON)
    assert "KP_SUCCESSION_MEDICAL_SCENARIO" in _codes(result)
    assert result.decision in (UWDecision.REFER, UWDecision.CONDITIONAL_ACCEPT)
    action_types = {a.action_type.value for a in result.actions}
    assert "enhanced_review" in action_types or "price_up" in action_types
    assert result.premium_mod_pct > 0
    assert "story" in result.to_summary_dict()


def test_clean_property_no_fire_scenario() -> None:
    text = "Commercial property office building. Sprinklered. Roof age: 8 years. Protection class: 3."
    result = evaluate_commercial_checklist(_bundle(text), InsuranceLine.COMMERCIAL_PROPERTY)
    assert "PROP_FIRE_SCENARIO" not in _codes(result)
    assert result.decision in (UWDecision.ACCEPT, UWDecision.CONDITIONAL_ACCEPT)


def test_summary_dict_shape() -> None:
    result = evaluate_commercial_checklist(
        _bundle("Trade credit. Accounts receivable aging. Top buyer concentration: 10%."),
        InsuranceLine.TRADE_CREDIT,
    )
    summary = result.to_summary_dict()
    assert summary["line"] == "trade_credit"
    assert "decision" in summary
    assert "flag_codes" in summary
    assert "scenario_codes" in summary
    assert "story" in summary
