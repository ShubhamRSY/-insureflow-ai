"""Pricing-linked underwriting rules: additive surcharges with a cap.

The underwriting guide (Chapter 2) is full of pricing instructions: percentage
surcharges applied additively up to a ceiling ("Surcharges may be applied up to
25% in addition to any other surcharges, in an additive manner"), flat fees for
endorsements, and tiered fees by exposure count. This module makes those rules
structured data that is linked back to the guide rule (``guideline_id`` /
``pricing_rule_codes`` on ``rag.guidelines.Guideline``) and evaluated
deterministically so the premium is reproducible and auditable.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SurchargeBasis(str, Enum):
    """The premium component (or exposure measure) a surcharge applies to."""

    PREMIUM = "premium"
    LIABILITY = "liability"
    PHYSICAL_DAMAGE = "physical_damage"
    COMPREHENSIVE = "comprehensive"
    COLLISION = "collision"
    UNIT = "unit"  # per-unit exposure (e.g. additional insureds on the account)
    VEHICLE = "vehicle"  # per-vehicle rating basis
    EXPOSURE_VALUE = "exposure_value"  # dollar exposure (e.g. added-equipment value)


class SurchargeRuleType(str, Enum):
    PERCENTAGE = "percentage"  # pct of the basis premium
    FLAT = "flat"  # flat dollar amount
    TIERED = "tiered"  # value selected from a band by an exposure measure


class SurchargeTier(BaseModel):
    label: str = ""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    value: float = 0.0


class SurchargeRule(BaseModel):
    code: str
    name: str
    guideline_id: str = ""  # link back to the guide rule that drives this price
    basis: SurchargeBasis = SurchargeBasis.PREMIUM
    rule_type: SurchargeRuleType = SurchargeRuleType.PERCENTAGE
    pct: float = 0.0
    flat_amount: float = 0.0
    tiered: list[SurchargeTier] = Field(default_factory=list)
    tier_exposure_key: str = ""  # which exposure measure the tiers are keyed on
    tier_value_is_pct: bool = True  # False = tier value is a flat dollar amount
    additive: bool = True  # False = multiplicative, applied outside the additive cap
    coverage: str = ""  # which coverage(s) the surcharge applies to
    description: str = ""


class SurchargeCap(BaseModel):
    """Additive ceiling for a basis, mirroring the guide's "up to 25%" rule."""

    basis: SurchargeBasis
    max_pct: float = 25.0
    applies_to: list[str] = Field(default_factory=list)  # coverage names; empty = all
    note: str = ""


class AppliedSurcharge(BaseModel):
    code: str
    name: str
    basis: SurchargeBasis
    rule_type: SurchargeRuleType
    pct: float = 0.0
    amount: float = 0.0
    tier_label: str = ""
    clamped: bool = False
    reason: str = ""


class SurchargeResult(BaseModel):
    premium_by_basis: dict[str, float] = Field(default_factory=dict)
    applied: list[AppliedSurcharge] = Field(default_factory=list)
    total_surcharge: float = 0.0
    capped_basis: list[str] = Field(default_factory=list)
    clamped_rules: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return self.model_dump(mode="json")


def _select_tier(rule: SurchargeRule, value: float) -> Optional[SurchargeTier]:
    for tier in rule.tiered:
        lo_ok = tier.min_value is None or value >= tier.min_value
        hi_ok = tier.max_value is None or value < tier.max_value
        if lo_ok and hi_ok:
            return tier
    return None


def evaluate_surcharges(
    rules: list[SurchargeRule],
    *,
    premium_by_basis: dict[SurchargeBasis, float],
    exposures: Optional[dict[str, float]] = None,
    caps: Optional[list[SurchargeCap]] = None,
    default_max_additive_pct: float = 25.0,
) -> SurchargeResult:
    """Apply pricing-linked surcharge rules to per-basis premiums.

    Additive percentage rules are summed per basis and clamped to the basis cap
    (default 25%, matching the guide's additive ceiling). When the cap binds, the
    additive amounts for that basis are scaled down pro rata and flagged. Flat and
    tiered rules are applied independently; multiplicative (non-additive) rules are
    applied on top without entering the additive pool.
    """
    cap_map: dict[SurchargeBasis, float] = {}
    for cap in caps or []:
        cap_map[cap.basis] = cap.max_pct

    applied: list[AppliedSurcharge] = []
    per_basis_additive: dict[SurchargeBasis, list[AppliedSurcharge]] = {}

    def basis_premium(basis: SurchargeBasis) -> float:
        return float(premium_by_basis.get(basis, 0.0))

    for rule in rules:
        base = basis_premium(rule.basis)

        if rule.rule_type == SurchargeRuleType.FLAT:
            applied.append(
                AppliedSurcharge(
                    code=rule.code,
                    name=rule.name,
                    basis=rule.basis,
                    rule_type=rule.rule_type,
                    amount=round(rule.flat_amount, 2),
                    reason="flat fee",
                )
            )
            continue

        if rule.rule_type == SurchargeRuleType.TIERED:
            exp_value = exposures.get(rule.tier_exposure_key) if exposures else None
            if exp_value is None:
                continue
            tier = _select_tier(rule, exp_value)
            if tier is None:
                continue
            amount = tier.value if not rule.tier_value_is_pct else round(base * tier.value / 100.0, 2)
            applied.append(
                AppliedSurcharge(
                    code=rule.code,
                    name=rule.name,
                    basis=rule.basis,
                    rule_type=rule.rule_type,
                    pct=tier.value if rule.tier_value_is_pct else 0.0,
                    amount=amount,
                    tier_label=tier.label,
                    reason=f"{rule.tier_exposure_key}={exp_value:g}",
                )
            )
            continue

        # Percentage
        if rule.additive:
            entry = AppliedSurcharge(
                code=rule.code,
                name=rule.name,
                basis=rule.basis,
                rule_type=rule.rule_type,
                pct=rule.pct,
                amount=round(base * rule.pct / 100.0, 2),
                reason="additive",
            )
            per_basis_additive.setdefault(rule.basis, []).append(entry)
            applied.append(entry)
        else:
            applied.append(
                AppliedSurcharge(
                    code=rule.code,
                    name=rule.name,
                    basis=rule.basis,
                    rule_type=rule.rule_type,
                    pct=rule.pct,
                    amount=round(base * rule.pct / 100.0, 2),
                    reason="multiplicative",
                )
            )

    capped_basis: list[str] = []
    clamped_rules: list[str] = []
    for basis, entries in per_basis_additive.items():
        raw_sum = sum(e.pct for e in entries)
        max_pct = cap_map.get(basis, default_max_additive_pct)
        if raw_sum <= max_pct:
            continue
        scale = max_pct / raw_sum
        capped_basis.append(basis.value)
        for e in entries:
            e.pct = round(e.pct * scale, 4)
            e.amount = round(e.amount * scale, 2)
            e.clamped = True
            clamped_rules.append(e.code)

    total = round(sum(a.amount for a in applied), 2)
    return SurchargeResult(
        premium_by_basis={k.value: v for k, v in premium_by_basis.items()},
        applied=applied,
        total_surcharge=total,
        capped_basis=capped_basis,
        clamped_rules=clamped_rules,
    )


def rules_for_guideline(rules: list[SurchargeRule], guideline_id: str) -> list[SurchargeRule]:
    """Surcharge rules driven by a specific underwriting-guide rule."""
    return [r for r in rules if r.guideline_id == guideline_id]


def builtin_commercial_auto_surcharges() -> list[SurchargeRule]:
    """Structured form of the guide's commercial-auto pricing instructions.

    Mirrors the Chapter 2 example guide: the eight enumerated surcharges
    (additive, capped at 25%), the new-venture and contractual-liability
    surcharges, the mileage tiered surcharge, the tiered additional-insured
    fees, and the added-equipment charge (4% of separately stated value).
    """
    return [
        SurchargeRule(
            code="SUR-001",
            name="Owners not active in management",
            guideline_id="COM-AUTO-SUR-001",
            basis=SurchargeBasis.LIABILITY,
            pct=10.0,
            additive=True,
            coverage="liability",
            description="Owners of the business do not take an active part in management; owners/managers have not previously been in this business.",
        ),
        SurchargeRule(
            code="SUR-002",
            name="Loading and unloading exposure",
            guideline_id="COM-AUTO-SUR-002",
            basis=SurchargeBasis.LIABILITY,
            pct=5.0,
            additive=True,
            coverage="liability",
            description="Loading/unloading of the vehicle creates an unusual exposure to parties other than insured drivers.",
        ),
        SurchargeRule(
            code="SUR-003",
            name="Dual-purpose vehicles",
            guideline_id="COM-AUTO-SUR-003",
            basis=SurchargeBasis.LIABILITY,
            pct=10.0,
            additive=True,
            coverage="liability",
            description="Vehicles have a dual purpose beyond normal business use (e.g. desert recreation on weekends).",
        ),
        SurchargeRule(
            code="SUR-004",
            name="Immobile operation exposure",
            guideline_id="COM-AUTO-SUR-004",
            basis=SurchargeBasis.LIABILITY,
            pct=10.0,
            additive=True,
            coverage="liability",
            description="Operation while immobile creates additional risk (cranes, cherry pickers, custom stationary exposures).",
        ),
        SurchargeRule(
            code="SUR-005",
            name="Hauled trailers or equipment",
            guideline_id="COM-AUTO-SUR-005",
            basis=SurchargeBasis.LIABILITY,
            pct=15.0,
            additive=True,
            coverage="liability",
            description="Trailers/equipment hauled that create additional exposure (cement pumps, hot tar, double/triple trailers).",
        ),
        SurchargeRule(
            code="SUR-006",
            name="Off-road use",
            guideline_id="COM-AUTO-SUR-006",
            basis=SurchargeBasis.PHYSICAL_DAMAGE,
            pct=10.0,
            additive=True,
            coverage="physical_damage",
            description="Off-road use that creates additional exposure.",
        ),
        SurchargeRule(
            code="SUR-007",
            name="Occupancy use of vehicle/trailer",
            guideline_id="COM-AUTO-SUR-007",
            basis=SurchargeBasis.LIABILITY,
            pct=10.0,
            additive=True,
            coverage="liability",
            description="Trailer or vehicle used for office or other occupancy (mobile medical trailer, dog washing, library).",
        ),
        SurchargeRule(
            code="SUR-008",
            name="Deleted exclusion",
            guideline_id="COM-AUTO-SUR-008",
            basis=SurchargeBasis.PREMIUM,
            pct=10.0,
            additive=True,
            coverage="affected_coverage",
            description="Deleting an exclusion at the insured's request, not to exceed one exclusion.",
        ),
        SurchargeRule(
            code="SUR-NV",
            name="New venture surcharge",
            guideline_id="COM-AUTO-SUR-009",
            basis=SurchargeBasis.LIABILITY,
            pct=10.0,
            additive=True,
            coverage="liability",
            description="Proprietors not in business for 6 months; dropped at renewal unless loss ratio exceeds 50%.",
        ),
        SurchargeRule(
            code="SUR-CONTR",
            name="Contractual liability endorsement",
            guideline_id="COM-AUTO-SUR-010",
            basis=SurchargeBasis.LIABILITY,
            pct=5.0,
            additive=True,
            coverage="liability",
            description="Contractual Liability Endorsement request results in a surcharge of 5% of the liability premium.",
        ),
        SurchargeRule(
            code="SUR-MILEAGE",
            name="Annual mileage surcharge",
            guideline_id="COM-AUTO-SUR-011",
            basis=SurchargeBasis.VEHICLE,
            rule_type=SurchargeRuleType.TIERED,
            tier_exposure_key="annual_mileage",
            tier_value_is_pct=True,
            additive=True,
            coverage="vehicle",
            description="Mileage surcharge applied to the designated vehicle when estimated annual mileage exceeds bands.",
            tiered=[
                SurchargeTier(label="<=50k", min_value=None, max_value=50_000, value=0.0),
                SurchargeTier(label="50k-60k", min_value=50_000, max_value=60_000, value=10.0),
                SurchargeTier(label="60k-70k", min_value=60_000, max_value=70_000, value=15.0),
                SurchargeTier(label="70k+", min_value=70_000, max_value=None, value=20.0),
            ],
        ),
        SurchargeRule(
            code="SUR-AI",
            name="Additional insured fees",
            guideline_id="COM-AUTO-SUR-012",
            basis=SurchargeBasis.UNIT,
            rule_type=SurchargeRuleType.TIERED,
            tier_exposure_key="additional_insureds",
            tier_value_is_pct=False,
            additive=True,
            coverage="liability",
            description="Tiered fees for additional insured endorsements.",
            tiered=[
                SurchargeTier(label="0-2", min_value=None, max_value=3, value=0.0),
                SurchargeTier(label="3-6", min_value=3, max_value=7, value=50.0),
                SurchargeTier(label="7-10", min_value=7, max_value=11, value=100.0),
                SurchargeTier(label="11-15", min_value=11, max_value=16, value=200.0),
                SurchargeTier(label="16+", min_value=16, max_value=None, value=300.0),
            ],
        ),
        SurchargeRule(
            code="SUR-EQUIP",
            name="Added equipment on vehicles",
            guideline_id="COM-AUTO-SUR-013",
            basis=SurchargeBasis.EXPOSURE_VALUE,
            pct=4.0,
            additive=False,
            coverage="physical_damage",
            description="Premium is 4% times the value of separately stated added equipment.",
        ),
    ]
