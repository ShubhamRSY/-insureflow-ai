"""Tests for line and staff underwriter desks."""

from __future__ import annotations

from insureflow.auth import Role
from insureflow.underwriting.line_desk import (
    assist_coverage,
    get_line_service_desk,
    reset_line_service_desk,
)
from insureflow.underwriting.roles import (
    UnderwriterDesk,
    capabilities_overview,
    desk_for_role,
    role_supports_staff_desk,
)
from insureflow.underwriting.staff_desk import (
    evaluate_experience,
    get_staff_desk,
    reset_staff_desk,
)


def test_desk_for_role_mapping():
    assert desk_for_role(Role.UNDERWRITER) == UnderwriterDesk.LINE
    assert desk_for_role(Role.STAFF_UW) == UnderwriterDesk.STAFF
    assert desk_for_role(Role.ADMIN) == UnderwriterDesk.BOTH
    assert desk_for_role(Role.CUO) == UnderwriterDesk.STAFF
    assert role_supports_staff_desk(Role.STAFF_UW)
    assert role_supports_staff_desk(Role.LICENSED_UW)
    assert not role_supports_staff_desk(Role.UNDERWRITER)
    assert not role_supports_staff_desk(Role.VIEWER)


def test_capabilities_overview_has_line_and_staff():
    overview = capabilities_overview()
    assert "line" in overview["desks"]
    assert "staff" in overview["desks"]
    assert len(overview["desks"]["line"]["capabilities"]) >= 3
    assert len(overview["desks"]["staff"]["capabilities"]) >= 6


def test_coverage_assist_broadens_transit_for_manufacturing():
    result = assist_coverage(
        applicant="Acme Manufacturing",
        occupancy="manufacturing",
        operations_description="Ships finished goods; property in transit weekly.",
    )
    actions = {r.action.value for r in result.recommendations}
    assert "broaden" in actions
    titles = " ".join(r.title.lower() for r in result.recommendations)
    assert "inland marine" in titles or "transit" in titles


def test_coverage_assist_narrows_coastal():
    result = assist_coverage(
        applicant="Coastal Condo",
        occupancy="coastal residential",
        operations_description="Hurricane and flood exposure on barrier island.",
    )
    assert any(r.action.value == "narrow" for r in result.recommendations)


def test_line_service_tickets(tmp_path, monkeypatch):
    monkeypatch.setenv("JOB_STORE_BACKEND", "file")
    monkeypatch.setenv("JOB_STORE_PATH", str(tmp_path / "job_store"))
    reset_line_service_desk()
    desk = get_line_service_desk()
    ticket = desk.create_ticket(
        request_type="certificate",
        subject="COI for landlord",
        requester="policyholder",
        requester_name="Acme LLC",
        policy_number="POL-1",
        created_by="junderwood",
        org_id="test-org",
    )
    assert ticket["ticket_id"].startswith("svc-")
    listed = desk.list_tickets(org_id="test-org")
    assert len(listed) == 1
    updated = desk.update_ticket(
        ticket["ticket_id"],
        status="completed",
        resolution_notes="Issued",
        org_id="test-org",
    )
    assert updated["status"] == "completed"
    reset_line_service_desk()


def test_staff_experience_tighten_when_worse_than_industry():
    result = evaluate_experience(
        earned_premium=1_000_000,
        incurred_losses=800_000,
        industry_loss_ratio=0.65,
    )
    assert result["strategy"] == "tighten"
    assert result["loss_ratio"] == 0.8


def test_staff_desk_guides_and_audits():
    reset_staff_desk()
    desk = get_staff_desk()
    overview = desk.overview(org_id="staff-test")
    assert "tasks" in overview
    assert overview["counts"]["guides"] >= 1

    guide = desk.upsert_guide(
        title="GL Guide",
        line_of_business="general_liability",
        body="Prefer contractors with safety programs.",
        status="published",
        author="aparker",
        org_id="staff-test",
    )
    assert guide["status"] == "published"

    audit = desk.conduct_audit(
        office="Southwest",
        auditor="aparker",
        scope="Selection vs guide",
        files_reviewed=10,
        findings=[{"severity": "major", "category": "selection", "detail": "Outside guide class bound"}],
        org_id="staff-test",
    )
    assert audit["audit_id"].startswith("audit-")
    assert audit["files_reviewed"] == 10

    note = desk.add_market_research(
        title="Expand to NM",
        topic="state_expansion",
        summary="Evaluate filing and agency force.",
        org_id="staff-test",
    )
    assert note["note_id"].startswith("mkt-")
    reset_staff_desk()


def test_staff_uw_role_exists():
    assert Role.STAFF_UW.value == "staff_uw"
    from insureflow.auth import ROLE_HIERARCHY

    assert ROLE_HIERARCHY[Role.STAFF_UW] == ROLE_HIERARCHY[Role.UNDERWRITER]
