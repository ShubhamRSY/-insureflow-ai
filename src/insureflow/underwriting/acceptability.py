"""Class acceptability codes + required authority levels.

Chapter 2 describes the "other types of underwriting guides": a table listing
each class of business with an acceptability code (the desirability of the loss
exposure) and the level of authority required to write the class. This module
makes that table structured, org-scoped data so line underwriters and the
automation can look up, for a class + line + territory, whether the class is
preferred/standard/conditional/substandard, whether it must be referred or
declined, and which authority tier is needed to bind it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from insureflow.underwriting.authority import AuthorityTier

ACCEPTABILITY_NS = "acceptability"


class AcceptabilityCode(str, Enum):
    PREFERRED = "preferred"  # actively sought; low hazard
    STANDARD = "standard"  # written on the filed rate
    CONDITIONAL = "conditional"  # written only with conditions / improvements
    SUBSTANDARD = "substandard"  # written only with a rate loading
    REFER = "refer"  # underwriter approval required before writing
    DECLINE = "decline"  # not written


_TIER_RANK: dict[AuthorityTier, int] = {
    AuthorityTier.JUNIOR: 0,
    AuthorityTier.SENIOR: 1,
    AuthorityTier.MGA: 2,
    AuthorityTier.CUO: 3,
}


@dataclass
class ClassAcceptability:
    class_code: str  # NAICS, NCCI, or ISO class code
    line: str  # line of business (commercial_property, general_liability, ...)
    acceptability: AcceptabilityCode
    min_authority: AuthorityTier = AuthorityTier.SENIOR
    territory: str = ""  # empty = all territories
    conditions: list[str] = field(default_factory=list)
    guideline_id: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "class_code": self.class_code,
            "line": self.line,
            "acceptability": self.acceptability.value,
            "min_authority": self.min_authority.value,
            "territory": self.territory,
            "conditions": list(self.conditions),
            "guideline_id": self.guideline_id,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ClassAcceptability:
        return cls(
            class_code=data["class_code"],
            line=data.get("line", ""),
            acceptability=AcceptabilityCode(data.get("acceptability", AcceptabilityCode.REFER.value)),
            min_authority=AuthorityTier(data.get("min_authority", AuthorityTier.SENIOR.value)),
            territory=data.get("territory", ""),
            conditions=list(data.get("conditions", [])),
            guideline_id=data.get("guideline_id", ""),
            notes=data.get("notes", ""),
        )


class AcceptabilityMatrix:
    """Org-scoped class → acceptability → authority-level table.

    Mirrors ``AuthorityMatrix`` persistence: seeded defaults, refreshed from the
    durable job store on read, admin edits persisted. Lookups that miss fall back
    to ``REFER`` / ``SENIOR`` so unlisted classes are never silently accepted.
    """

    def __init__(self) -> None:
        self._entries: dict[tuple[str, str, str], ClassAcceptability] = {}
        self._cached_org: str | None = None

    def _store(self) -> Any:
        from insureflow.storage.job_store import get_job_store

        return get_job_store()

    def _seed(self) -> list[ClassAcceptability]:
        # Mirrors carrier-appetite guideline APT-001 NAICS preferences.
        return [
            ClassAcceptability("44", "commercial_property", AcceptabilityCode.PREFERRED, AuthorityTier.JUNIOR, guideline_id="APT-001", notes="Retail trade — preferred"),
            ClassAcceptability("45", "commercial_property", AcceptabilityCode.PREFERRED, AuthorityTier.JUNIOR, guideline_id="APT-001", notes="Retail trade — preferred"),
            ClassAcceptability("54", "general_liability", AcceptabilityCode.PREFERRED, AuthorityTier.JUNIOR, guideline_id="APT-001", notes="Professional services"),
            ClassAcceptability("53", "commercial_property", AcceptabilityCode.STANDARD, AuthorityTier.JUNIOR, guideline_id="APT-001", notes="Real estate"),
            ClassAcceptability("62", "general_liability", AcceptabilityCode.STANDARD, AuthorityTier.SENIOR, guideline_id="APT-001", notes="Healthcare — senior review"),
            ClassAcceptability(
                "72", "general_liability", AcceptabilityCode.CONDITIONAL, AuthorityTier.SENIOR, guideline_id="APT-001", notes="Accommodation/food excluding casinos; conditions on occupancy"
            ),  # noqa: E501
            ClassAcceptability("7211", "commercial_property", AcceptabilityCode.DECLINE, AuthorityTier.CUO, guideline_id="APT-001", notes="Casinos — excluded"),
            ClassAcceptability("1133", "general_liability", AcceptabilityCode.DECLINE, AuthorityTier.CUO, guideline_id="APT-001", notes="Logging — excluded"),
            ClassAcceptability("2131", "general_liability", AcceptabilityCode.DECLINE, AuthorityTier.CUO, guideline_id="APT-001", notes="Mining support — excluded"),
            ClassAcceptability("4821", "general_liability", AcceptabilityCode.DECLINE, AuthorityTier.CUO, guideline_id="APT-001", notes="Rail transport — excluded"),
            ClassAcceptability("9211", "general_liability", AcceptabilityCode.DECLINE, AuthorityTier.CUO, guideline_id="APT-001", notes="Military — excluded"),
        ]

    def _ensure_loaded(self, org_id: str) -> None:
        if self._cached_org == org_id:
            return
        cached: dict[tuple[str, str, str], ClassAcceptability] = {}
        for e in self._seed():
            cached[(e.class_code, e.line, e.territory)] = e
        raw = self._store().get(ACCEPTABILITY_NS, "matrix", org_id=org_id)
        if raw:
            for rec in raw.get("entries", []):
                try:
                    e = ClassAcceptability.from_dict(rec)
                except (KeyError, ValueError):
                    continue
                cached[(e.class_code, e.line, e.territory)] = e
        self._entries = cached
        self._cached_org = org_id

    def _persist(self, org_id: str) -> None:
        data = {"entries": [e.to_dict() for e in self._entries.values()]}
        self._store().set(ACCEPTABILITY_NS, "matrix", data, org_id=org_id)

    def lookup(
        self,
        class_code: str,
        line: str = "",
        territory: str = "",
        org_id: str = "default",
    ) -> Optional[ClassAcceptability]:
        self._ensure_loaded(org_id)
        # Exact (class, line, territory) → (class, line) → (class, "", "")
        for key in (
            (class_code, line, territory),
            (class_code, line, ""),
            (class_code, "", ""),
        ):
            if key in self._entries:
                return self._entries[key]
        return None

    def required_authority(
        self,
        class_code: str,
        line: str = "",
        territory: str = "",
        org_id: str = "default",
    ) -> AuthorityTier:
        entry = self.lookup(class_code, line, territory, org_id=org_id)
        return entry.min_authority if entry else AuthorityTier.SENIOR

    def acceptability(
        self,
        class_code: str,
        line: str = "",
        territory: str = "",
        org_id: str = "default",
    ) -> AcceptabilityCode:
        entry = self.lookup(class_code, line, territory, org_id=org_id)
        return entry.acceptability if entry else AcceptabilityCode.REFER

    def evaluate(
        self,
        class_code: str,
        acting_tier: AuthorityTier,
        line: str = "",
        territory: str = "",
        org_id: str = "default",
    ) -> tuple[bool, AcceptabilityCode, str]:
        """Can ``acting_tier`` bind this class? Returns (allowed, code, reason)."""
        entry = self.lookup(class_code, line, territory, org_id=org_id)
        if entry is None:
            return False, AcceptabilityCode.REFER, f"Class {class_code} not listed in the acceptability table — senior UW review required"
        if entry.acceptability == AcceptabilityCode.DECLINE:
            return False, entry.acceptability, f"Class {class_code} is declined (guideline {entry.guideline_id})"
        required = entry.min_authority
        if _TIER_RANK[acting_tier] < _TIER_RANK[required]:
            return False, entry.acceptability, f"Class {class_code} requires {required.value} authority; acting tier is {acting_tier.value} — refer"
        if entry.acceptability == AcceptabilityCode.CONDITIONAL and entry.conditions:
            return True, entry.acceptability, f"Class {class_code} admissible subject to conditions: {'; '.join(entry.conditions)}"
        return True, entry.acceptability, f"Class {class_code} is {entry.acceptability.value} — within {required.value} authority"

    def upsert(self, entry: ClassAcceptability, org_id: str = "default") -> ClassAcceptability:
        self._ensure_loaded(org_id)
        self._entries[(entry.class_code, entry.line, entry.territory)] = entry
        self._persist(org_id)
        return entry

    def remove(self, class_code: str, line: str = "", territory: str = "", org_id: str = "default") -> bool:
        self._ensure_loaded(org_id)
        key = (class_code, line, territory)
        if key not in self._entries:
            return False
        del self._entries[key]
        self._persist(org_id)
        return True

    def list_all(self, org_id: str = "default") -> list[ClassAcceptability]:
        self._ensure_loaded(org_id)
        return list(self._entries.values())

    def coverage(self, org_id: str = "default") -> dict[str, int]:
        self._ensure_loaded(org_id)
        counts: dict[str, int] = {}
        for e in self._entries.values():
            counts[e.acceptability.value] = counts.get(e.acceptability.value, 0) + 1
        return counts


_acceptability_matrix: AcceptabilityMatrix | None = None


def get_acceptability_matrix() -> AcceptabilityMatrix:
    global _acceptability_matrix
    if _acceptability_matrix is None:
        _acceptability_matrix = AcceptabilityMatrix()
    return _acceptability_matrix


def reset_acceptability_matrix() -> None:
    global _acceptability_matrix
    _acceptability_matrix = None
