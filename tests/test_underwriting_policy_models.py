"""Tests for the underwriting policy data model additions.

Covers: the worksheet records on the memo (communications log + reinsurance
requests), versioned/effective-dated guidelines, pricing-linked surcharge rules
with the additive cap, and the class acceptability / authority tables.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from insureflow.models.agents import UnderwritingMemo
from insureflow.rag.guidelines import (
    Guideline,
    GuidelineCategory,
    GuidelineSource,
    GuidelineStatus,
    UnderwritingGuidelines,
)
from insureflow.rating.surcharges import (
    SurchargeBasis,
    SurchargeRule,
    builtin_commercial_auto_surcharges,
    evaluate_surcharges,
    rules_for_guideline,
)
from insureflow.underwriting.acceptability import (
    AcceptabilityCode,
    ClassAcceptability,
    get_acceptability_matrix,
    reset_acceptability_matrix,
)
from insureflow.underwriting.authority import AuthorityTier

# ── 1. Underwriting worksheet on the memo ─────────────────────────────────

def test_memo_communications_log():
    memo = UnderwritingMemo(bundle_id="b1")
    entry = memo.add_communication(
        direction="inbound",
        channel="phone",
        party="Acme Broker",
        party_role="broker",
        summary="Chased loss runs",
    )
    assert len(memo.communications_log) == 1
    assert entry.entry_id.startswith("comm-")
    assert entry.party_role == "broker"
    # round-trips through model_dump so the worksheet persists with the memo
    dumped = memo.model_dump()
    assert dumped["communications_log"][0]["summary"] == "Chased loss runs"


def test_memo_reinsurance_requests():
    memo = UnderwritingMemo(bundle_id="b1")
    req = memo.add_reinsurance_request(
        structure="excess_of_loss",
        layer_limit=5_000_000,
        attachment_point=2_000_000,
        market="Swiss Re",
    )
    assert len(memo.reinsurance_requests) == 1
    assert req.request_id.startswith("re-")
    assert req.attachment_point == 2_000_000
    assert req.status == "requested"
    dumped = memo.model_dump()
    assert dumped["reinsurance_requests"][0]["market"] == "Swiss Re"


def test_memo_worksheet_defaults_empty():
    memo = UnderwritingMemo(bundle_id="b1")
    assert memo.communications_log == []
    assert memo.reinsurance_requests == []


# ── 2. Versioned / effective-dated guidelines ──────────────────────────────

def _guideline(
    gid: str,
    *,
    version: str = "1.0",
    status: GuidelineStatus = GuidelineStatus.ACTIVE,
    effective: datetime | None = None,
    expiration: datetime | None = None,
    supersedes: str = "",
    states: list[str] | None = None,
) -> Guideline:
    return Guideline(
        id=gid,
        category=GuidelineCategory.GENERAL,
        source=GuidelineSource.COMPANY,
        title=gid,
        content=f"content of {gid}",
        version=version,
        status=status,
        effective_date=effective,
        expiration_date=expiration,
        supersedes=supersedes,
        states=states or [],
    )


def test_active_as_of_filters_status_and_dates():
    now = datetime.now()
    coll = UnderwritingGuidelines(
        guidelines=[
            _guideline("G1"),
            _guideline("G1b", version="2.0", supersedes="G1"),
            _guideline("G-sup", status=GuidelineStatus.SUPERSEDED),
            _guideline("G-future", effective=now + timedelta(days=30)),
            _guideline("G-expired", expiration=now - timedelta(days=1)),
        ]
    )
    coll.guidelines[1].status = GuidelineStatus.ACTIVE
    coll.guidelines[2].status = GuidelineStatus.SUPERSEDED
    active_ids = {g.id for g in coll.active_as_of()}
    assert active_ids == {"G1", "G1b"}


def test_resolve_supersession():
    coll = UnderwritingGuidelines(
        guidelines=[
            _guideline("G1"),
            _guideline("G1b", version="2.0", supersedes="G1"),
        ]
    )
    coll.guidelines[1].status = GuidelineStatus.ACTIVE
    assert coll.resolve_supersession() == {"G1": "G1b"}


def test_for_states_filters_by_state():
    now = datetime.now()
    coll = UnderwritingGuidelines(
        guidelines=[
            _guideline("G-FL", states=["FL"]),
            _guideline("G-TX", states=["TX"]),
            _guideline("G-ALL"),
        ]
    )
    fl = coll.for_states(["FL"], as_of=now)
    assert {g.id for g in fl} == {"G-FL", "G-ALL"}


def test_guideline_is_active_on_window():
    now = datetime.now()
    g = _guideline("G-window", effective=now - timedelta(days=1), expiration=now + timedelta(days=1))
    assert g.is_active_on(now)
    assert not g.is_active_on(now - timedelta(days=2))
    assert not g.is_active_on(now + timedelta(days=2))


# ── 3. Pricing-linked surcharge rules + additive cap ───────────────────────

def test_additive_cap_clamps_to_max_pct():
    rules = builtin_commercial_auto_surcharges()
    liability = [r for r in rules if r.basis == SurchargeBasis.LIABILITY]
    assert liability, "expected built-in liability surcharges"
    res = evaluate_surcharges(liability, premium_by_basis={SurchargeBasis.LIABILITY: 1000.0})
    # additive ceiling of 25% on the liability premium
    assert res.total_surcharge <= 250.0 + 1e-6
    assert res.capped_basis == ["liability"]
    assert res.clamped_rules
    assert all(a.clamped for a in res.applied if a.code in set(res.clamped_rules))


def test_no_cap_when_within_limit():
    res = evaluate_surcharges(
        [SurchargeRule(code="A", name="Small", basis=SurchargeBasis.LIABILITY, pct=5.0)],
        premium_by_basis={SurchargeBasis.LIABILITY: 1000.0},
    )
    assert res.total_surcharge == 50.0
    assert res.capped_basis == []
    assert res.clamped_rules == []


def test_tiered_mileage_surcharge():
    rules = builtin_commercial_auto_surcharges()
    mileage = next(r for r in rules if r.code == "SUR-MILEAGE")
    res = evaluate_surcharges(
        [mileage],
        premium_by_basis={SurchargeBasis.VEHICLE: 1000.0},
        exposures={"annual_mileage": 65_000},
    )
    assert res.applied[0].pct == 15.0
    assert res.applied[0].amount == 150.0


def test_tiered_additional_insured_fee():
    rules = builtin_commercial_auto_surcharges()
    ai = next(r for r in rules if r.code == "SUR-AI")
    res = evaluate_surcharges(
        [ai],
        premium_by_basis={SurchargeBasis.UNIT: 0.0},
        exposures={"additional_insureds": 12},
    )
    assert res.applied[0].amount == 200.0
    assert res.applied[0].tier_label == "11-15"


def test_flat_and_equipment_rules():
    rules = builtin_commercial_auto_surcharges()
    equip = next(r for r in rules if r.code == "SUR-EQUIP")
    res = evaluate_surcharges(
        [equip],
        premium_by_basis={SurchargeBasis.EXPOSURE_VALUE: 50_000.0},
    )
    # 4% of separately stated added-equipment value, non-additive (multiplicative)
    assert res.applied[0].amount == 2_000.0
    assert res.applied[0].reason == "multiplicative"


def test_rules_for_guideline_linkage():
    rules = builtin_commercial_auto_surcharges()
    linked = rules_for_guideline(rules, "COM-AUTO-SUR-001")
    assert [r.code for r in linked] == ["SUR-001"]


# ── 4. Class acceptability + authority tables ──────────────────────────────

def _reset() -> None:
    reset_acceptability_matrix()


def test_acceptability_lookup_and_evaluate():
    _reset()
    mat = get_acceptability_matrix()
    ok, code, reason = mat.evaluate("44", AuthorityTier.JUNIOR, "commercial_property")
    assert ok
    assert code == AcceptabilityCode.PREFERRED
    # decline class cannot be bound by any tier
    ok2, code2, _ = mat.evaluate("4821", AuthorityTier.CUO, "general_liability")
    assert not ok2
    assert code2 == AcceptabilityCode.DECLINE


def test_acceptability_authority_gate():
    _reset()
    mat = get_acceptability_matrix()
    # healthcare (NAICS 62) requires senior; junior is denied
    ok, code, reason = mat.evaluate("62", AuthorityTier.JUNIOR, "general_liability")
    assert not ok
    assert code == AcceptabilityCode.STANDARD
    assert "senior" in reason
    ok2, _, _ = mat.evaluate("62", AuthorityTier.SENIOR, "general_liability")
    assert ok2


def test_unlisted_class_defaults_to_refer():
    _reset()
    mat = get_acceptability_matrix()
    ok, code, reason = mat.evaluate("99999", AuthorityTier.CUO)
    assert not ok
    assert code == AcceptabilityCode.REFER
    assert "not listed" in reason


def test_upsert_and_remove_persist():
    _reset()
    mat = get_acceptability_matrix()
    entry = ClassAcceptability(
        class_code="56",
        line="general_liability",
        acceptability=AcceptabilityCode.CONDITIONAL,
        min_authority=AuthorityTier.SENIOR,
        conditions=["MVR review required"],
    )
    mat.upsert(entry, org_id="test-org")
    ok, code, reason = mat.evaluate("56", AuthorityTier.SENIOR, "general_liability", org_id="test-org")
    assert ok
    assert "subject to conditions" in reason
    assert mat.remove("56", "general_liability", org_id="test-org")
    assert mat.lookup("56", "general_liability", org_id="test-org") is None
