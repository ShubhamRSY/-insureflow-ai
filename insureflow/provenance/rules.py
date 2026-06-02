from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass(frozen=True)
class VerificationRule:
    name: str
    field_path: str
    description: str
    priority: int = 0
    fn: Optional[Callable[[list[Any]], bool]] = None
    tolerance: Optional[float] = None

    def verify(self, values: list[Any]) -> tuple[bool, str]:
        if not values:
            return False, "no_values"

        if self.fn:
            try:
                result = self.fn(values)
                return result, "custom_rule_passed" if result else "custom_rule_failed"
            except Exception as e:
                return False, f"rule_error: {e}"

        unique = set(str(v) for v in values)
        if len(unique) == 1:
            return True, "exact_match"

        if self.tolerance is not None:
            numeric_values: list[float] = []
            for v in values:
                try:
                    numeric_values.append(float(v))
                except (ValueError, TypeError):
                    continue
            if len(numeric_values) >= 2:
                max_val = max(numeric_values)
                min_val = min(numeric_values)
                if max_val > 0:
                    deviation = abs(max_val - min_val) / max_val
                    if deviation <= self.tolerance:
                        return True, f"within_tolerance_{deviation:.3f}"

        return False, f"mismatch: {unique}"


@dataclass
class VerificationRuleSet:
    rules: list[VerificationRule] = field(default_factory=list)

    def add_rule(self, rule: VerificationRule) -> None:
        self.rules.append(rule)

    def get_rule(self, field_path: str) -> Optional[VerificationRule]:
        for rule in self.rules:
            if rule.field_path == field_path:
                return rule
        return None

    @classmethod
    def default_rules(cls) -> VerificationRuleSet:
        return cls(
            rules=[
                VerificationRule(
                    name="legal_name_match",
                    field_path="named_insured.legal_name",
                    description="Named insured legal name must match across sources",
                    priority=1,
                ),
                VerificationRule(
                    name="effective_date_match",
                    field_path="policy_period.effective_date",
                    description="Policy effective date must be consistent",
                    priority=1,
                ),
                VerificationRule(
                    name="construction_type_match",
                    field_path="risk_profile.construction_type",
                    description="Construction type must be consistent",
                    priority=2,
                ),
                VerificationRule(
                    name="square_footage_tolerance",
                    field_path="location.0.square_footage",
                    description="Square footage must be within 10% tolerance",
                    priority=2,
                    tolerance=0.10,
                ),
                VerificationRule(
                    name="protection_class_match",
                    field_path="risk_profile.protection_class",
                    description="Protection class must match",
                    priority=2,
                ),
                VerificationRule(
                    name="occupancy_type_match",
                    field_path="risk_profile.occupancy_type",
                    description="Occupancy type must be consistent",
                    priority=2,
                ),
                VerificationRule(
                    name="year_built_match",
                    field_path="location.0.year_built",
                    description="Year built must match",
                    priority=2,
                    tolerance=0.01,
                ),
                VerificationRule(
                    name="stories_match",
                    field_path="risk_profile.number_of_stories",
                    description="Number of stories must match",
                    priority=2,
                ),
                VerificationRule(
                    name="coverage_limit_tolerance",
                    field_path="coverage.0.limit",
                    description="Coverage limits within 5% tolerance",
                    priority=3,
                    tolerance=0.05,
                ),
            ]
        )
