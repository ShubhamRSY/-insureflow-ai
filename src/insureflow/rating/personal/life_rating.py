"""Term life filing-style premium calculation."""

from __future__ import annotations

from typing import Any

from insureflow.models.submissions import SubmissionBundle
from insureflow.rating.models import InsuranceLine, QuoteResult, RateComponent
from insureflow.rating.personal.manuals import life_manual, nearest_key
from insureflow.underwriting.life_medical import underwrite_life
from insureflow.underwriting.personal_lines import extract_life_factors


def rate_life(bundle: SubmissionBundle) -> QuoteResult:
    manual = life_manual()
    factors = extract_life_factors(bundle)
    medical = underwrite_life(bundle)

    face = factors.face_amount
    if face <= 0:
        return QuoteResult(
            bundle_id=bundle.bundle_id,
            line=InsuranceLine.LIFE,
            base_premium=0.0,
            adjusted_premium=0.0,
            eligible=False,
            ineligibility_reasons=["Face amount missing — cannot rate"],
            metadata={"filing_id": manual.get("filing_id"), "tiv_unknown": True, "medical": medical.to_metadata()},
        )

    age = factors.age or 40
    sex = factors.sex if factors.sex in ("male", "female") else "unknown"
    sex_key = "female" if sex == "female" else "male"
    mort_table = (manual.get("mortality_per_1000") or {}).get(sex_key) or {}
    q = float(mort_table.get(nearest_key(mort_table, age), 1.5))

    class_factors = manual.get("underwriting_class_factors") or {}
    class_f = float(class_factors.get(medical.underwriting_class, class_factors.get("standard", 1.0)))
    sex_f = float((manual.get("sex_factors") or {}).get(sex, 1.0))
    tobacco_f = float(manual.get("tobacco_factor", 1.85)) if medical.tobacco else 1.0

    base_premium = (face / 1000.0) * q
    adjusted = base_premium * class_f * sex_f * tobacco_f
    adjusted += (face / 1000.0) * medical.flat_extras_per_1000
    adjusted += float(manual.get("policy_fee", 60.0))
    adjusted = max(adjusted, float(manual.get("minimum_premium", 250.0)))
    adjusted = round(adjusted, 2)

    eligible = medical.decision.value != "decline"
    reasons = list(medical.reasons) if not eligible else list(medical.reasons)

    components = [
        RateComponent(name="mortality_per_1000", amount=q, basis=f"age={age}/{sex_key}"),
        RateComponent(name="underwriting_class", amount=class_f, basis=medical.underwriting_class),
        RateComponent(name="sex_factor", amount=sex_f, basis=sex),
        RateComponent(name="tobacco_factor", amount=tobacco_f, basis="tobacco" if medical.tobacco else "non_tobacco"),
        RateComponent(name="flat_extras", amount=medical.flat_extras_per_1000, basis="per_1000"),
        RateComponent(name="policy_fee", amount=float(manual.get("policy_fee", 60.0)), basis="policy"),
    ]

    meta: dict[str, Any] = {
        "filing_id": manual.get("filing_id"),
        "product": manual.get("product"),
        "rating_engine": "life_filing",
        "face_amount": face,
        "medical": medical.to_metadata(),
        "personal_factors": {k: v for k, v in factors.__dict__.items() if k != "findings"},
        "tiv": face,
        "insurance_line": InsuranceLine.LIFE.value,
        "personal_lines": True,
        "uw_decision_hint": medical.decision.value,
        "conditions": [],
    }
    if medical.require_aps:
        meta["conditions"].append("APS (attending physician statement) required before bind")
    if medical.require_paramed:
        meta["conditions"].append("Paramedical exam required")
    if medical.decision == medical.decision.CONDITIONAL_ACCEPT or medical.require_aps:
        pass

    return QuoteResult(
        bundle_id=bundle.bundle_id,
        line=InsuranceLine.LIFE,
        base_premium=round(base_premium, 2),
        adjusted_premium=adjusted,
        schedule_modifications=components,
        rate_per_100_tiv=round(adjusted / (face / 100.0), 4),
        eligible=eligible,
        ineligibility_reasons=[] if eligible else reasons,
        metadata=meta,
    )
