"""Legal remedies for misrepresentation, concealment, and warranty breach.

Doctrinal mapping: concealment → voidance (the contract is void from the start);
material misrepresentation → rescission (treat the policy as if it never
existed) or claim denial; breached warranty → claim denial for claims arising
from the breach (or rescission for a promissory warranty when serious).
"""

from __future__ import annotations

from insureflow.models.policy import DisclosureAssessment, LegalRemedy, LegalRemedyType


def determine_remedy(disclosure: DisclosureAssessment) -> LegalRemedy:
    """Map a disclosure failure to the insurer's remedy, most severe first."""
    if disclosure.concealment:
        basis = "concealment"
        detail = "Policy void ab initio — the insured concealed material facts and the contract never validly formed"
        return LegalRemedy(remedy=LegalRemedyType.VOIDANCE, basis=basis, detail=detail)

    if disclosure.material_misrepresentation:
        basis = "material_misrepresentation"
        detail = "Policy rescinded — the contract may be unwound and claims denied because a material fact was misrepresented"
        return LegalRemedy(remedy=LegalRemedyType.RESCISSION, basis=basis, detail=detail)

    if disclosure.warranty_breach:
        basis = "warranty_breach"
        detail = "Claims arising from the breached warranty may be denied; repeated or severe breaches can support rescission"
        return LegalRemedy(remedy=LegalRemedyType.CLAIM_DENIAL, basis=basis, detail=detail)

    return LegalRemedy(remedy=LegalRemedyType.NONE, basis="", detail="No misrepresentation, concealment, or warranty breach found")


def remedy_matrix(disclosure: DisclosureAssessment) -> dict[str, object]:
    """Human-readable mapping of which failures trigger which remedies."""
    remedy = determine_remedy(disclosure)
    return {
        "remedy": remedy.remedy.value,
        "basis": remedy.basis,
        "detail": remedy.detail,
        "material_misrepresentation": disclosure.material_misrepresentation,
        "concealment": disclosure.concealment,
        "warranty_breach": disclosure.warranty_breach,
    }
