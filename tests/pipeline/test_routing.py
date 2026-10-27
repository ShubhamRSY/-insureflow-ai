from __future__ import annotations

import prepare
import workbench


def report(ops: str, tiv: str | None = "$1,000,000", **kw):
    fields = [{"field_id": "operations", "value": ops}]
    if tiv is not None:
        fields.append({"field_id": "tiv_building", "value": tiv})
    return {"complete": True, "status": "complete", "fields": fields, **kw}


def test_a_plain_office_routes_to_carrier_a():
    assert workbench.route(report("office building, no cooking")) == "carrier_a"


def test_a_restaurant_is_a_senior_referral_with_carrier_b():
    match = workbench.match(report("Barbecue Restaurant"))
    assert match["route"] == "senior_referral"
    assert match["suggested"] == "carrier_b"
    assert "R10" in match["note"]


def test_unsprinklered_habitational_is_a_senior_referral_to_carrier_c():
    match = workbench.match(report("habitational, 8 units, no commercial cooking", sprinklers="no"))
    assert match["route"] == "senior_referral"
    assert match["suggested"] == "carrier_c"
    assert "no sprinklers" in match["note"] and match["overridable"] is False


def test_a_missing_sprinkler_answer_holds_habitational():
    assert workbench.route(report("habitational, 8 units, no commercial cooking", sprinklers=None)) == "hold"


def test_a_missing_tiv_holds_the_file_and_gives_a_provisional_route():
    match = workbench.match(report("Roofing contractor, 5 employees, shop and yard", tiv=None, complete=False, status="incomplete"))
    assert match["route"] == "hold"
    assert match["provisional"] == "senior_referral"
    assert match["provisional_label"] == workbench.PROVISIONAL_TIV


def test_a_prohibited_word_is_no_match_and_overridable():
    match = workbench.match(report("barber shop"))
    assert match["route"] == "no_match"
    assert match["overridable"] is True
    assert "R8" in match["note"]


def test_a_vacant_building_is_a_senior_referral():
    assert workbench.route(report("vacant office building")) == "senior_referral"


def test_a_negated_referral_word_does_not_refer():
    assert workbench.route(report("office, no liquor")) == "carrier_a"


def test_a_tiv_over_the_pilot_limit_is_a_senior_referral():
    match = workbench.match(report("accounting office", tiv="$8,000,000"))
    assert match["route"] == "senior_referral"
    assert "R13" in match["note"]


def test_two_allow_list_groups_are_a_senior_referral():
    match = workbench.match(report("office and retail store"))
    assert match["route"] == "senior_referral"
    assert "R16" in match["note"]


def test_manual_intake_has_no_carrier_route():
    match = workbench.match({"status": prepare.MANUAL_INTAKE, "fields": [], "scope": {"in_scope": False, "reasons": [{"code": "scanned_application", "text": "Manual intake: scanned application"}]}})
    assert match["route"] == "manual_intake"
    assert "suggested" not in match or not match["suggested"]
    assert match["overridable"] is False
