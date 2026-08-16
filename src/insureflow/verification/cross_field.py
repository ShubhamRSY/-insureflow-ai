"""Cross-field logic and conditional range bounds.

Related facts have to agree. A number that is legal in isolation can still be
impossible next to another field on the same file:

- Chronology: a driver license issued after the policy starts, or an expiration
  before the effective date.
- Payroll vs headcount: millions of payroll with zero employees.
- Size vs replacement cost: a small dwelling claiming a warehouse rebuild value.
- Deductible vs limit: the customer cannot pay more first than the policy pays.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Mapping, Sequence

from insureflow.models.submissions import ExtractedField, VerificationIssue
from insureflow.verification.common import SEVERITY_ERROR, SEVERITY_WARNING, make_issue, to_number

_DATE_FORMATS = (
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m/%d/%y",
    "%d-%b-%Y",
    "%b %d, %Y",
    "%B %d, %Y",
)


def _parse_date(value: str) -> date | None:
    text = str(value).strip()
    if not text:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _first_matching(
    fields: Mapping[str, Sequence[ExtractedField]],
    pattern: re.Pattern[str],
) -> tuple[str, ExtractedField] | None:
    for key, entries in fields.items():
        if not entries:
            continue
        if pattern.search(key):
            return key, entries[0]
    return None


def _first_number(
    fields: Mapping[str, Sequence[ExtractedField]],
    pattern: re.Pattern[str],
) -> tuple[str, float] | None:
    hit = _first_matching(fields, pattern)
    if hit is None:
        return None
    key, field = hit
    num = to_number(field.value)
    if num is None:
        return None
    return key, num


def _first_date(
    fields: Mapping[str, Sequence[ExtractedField]],
    pattern: re.Pattern[str],
) -> tuple[str, date] | None:
    hit = _first_matching(fields, pattern)
    if hit is None:
        return None
    key, field = hit
    parsed = _parse_date(field.value)
    if parsed is None:
        return None
    return key, parsed


_LICENSE_DATE = re.compile(r"license_issue|dl_issue|driver_license_issue|licence_issue", re.I)
_EFFECTIVE = re.compile(r"effective_date|policy_start|inception_date|policy_effective", re.I)
_EXPIRATION = re.compile(r"expir(?:y|ation)|policy_end|policy_expiration", re.I)
_PAYROLL = re.compile(r"payroll", re.I)
_EMPLOYEES = re.compile(r"employees|headcount|fte|number_of_employee", re.I)
_SQFT = re.compile(r"sq_?ft|square_feet|square_footage|building_area|dwelling_area|floor_area|living_area", re.I)
_REPLACEMENT = re.compile(
    r"replacement_cost|\brcv\b|total_insured_value|\btiv\b|building_value|dwelling_coverage|coverage_a",
    re.I,
)
_DEDUCTIBLE = re.compile(r"deductible", re.I)
_LIMIT = re.compile(r"(?<!sub)limit|coverage_limit", re.I)

# Small dwellings claiming warehouse-scale rebuild values.
_SMALL_DWELLING_SQFT = 2_500.0
_SMALL_DWELLING_REPLACEMENT_ERROR = 5_000_000.0
_HIGH_COST_PER_SQFT = 2_500.0
# Payroll with nobody to pay.
_PAYROLL_WITHOUT_HEADCOUNT = 500_000.0
_PAYROLL_PER_EMPLOYEE_WARN = 2_000_000.0


def chronological_dates(fields: Mapping[str, Sequence[ExtractedField]]) -> list[VerificationIssue]:
    """Flags dates that cannot happen in that order."""
    issues: list[VerificationIssue] = []
    license_hit = _first_date(fields, _LICENSE_DATE)
    effective_hit = _first_date(fields, _EFFECTIVE)
    expiration_hit = _first_date(fields, _EXPIRATION)

    if license_hit and effective_hit and license_hit[1] > effective_hit[1]:
        issues.append(
            make_issue(
                "date_order",
                SEVERITY_ERROR,
                f"{license_hit[0]}={license_hit[1].isoformat()} is after {effective_hit[0]}={effective_hit[1].isoformat()} — a license cannot be issued after the policy starts",
                fields,
                license_hit[0],
            )
        )
    if effective_hit and expiration_hit and expiration_hit[1] < effective_hit[1]:
        issues.append(
            make_issue(
                "date_order",
                SEVERITY_ERROR,
                f"{expiration_hit[0]}={expiration_hit[1].isoformat()} is before {effective_hit[0]}={effective_hit[1].isoformat()} — the policy cannot end before it starts",
                fields,
                expiration_hit[0],
            )
        )
    return issues


def payroll_vs_headcount(fields: Mapping[str, Sequence[ExtractedField]]) -> list[VerificationIssue]:
    """Flags payroll that cannot exist without people (and the reverse extreme)."""
    payroll = _first_number(fields, _PAYROLL)
    employees = _first_number(fields, _EMPLOYEES)
    if payroll is None or employees is None:
        return []
    pay_key, pay = payroll
    emp_key, headcount = employees
    issues: list[VerificationIssue] = []
    if headcount <= 0 and pay >= _PAYROLL_WITHOUT_HEADCOUNT:
        issues.append(
            make_issue(
                "payroll_without_employees",
                SEVERITY_ERROR,
                f"{pay_key}={pay:,.0f} with {emp_key}={headcount:g} — payroll that large cannot have zero employees",
                fields,
                pay_key,
            )
        )
    elif headcount > 0 and pay / headcount > _PAYROLL_PER_EMPLOYEE_WARN:
        issues.append(
            make_issue(
                "payroll_per_employee",
                SEVERITY_WARNING,
                f"{pay_key}={pay:,.0f} across {emp_key}={headcount:g} is {pay / headcount:,.0f} per person — unusual, review",
                fields,
                pay_key,
            )
        )
    return issues


def replacement_cost_vs_area(fields: Mapping[str, Sequence[ExtractedField]]) -> list[VerificationIssue]:
    """Flags a small building claiming a rebuild cost that only fits a large risk."""
    area = _first_number(fields, _SQFT)
    cost = _first_number(fields, _REPLACEMENT)
    if area is None or cost is None:
        return []
    area_key, sqft = area
    cost_key, replacement = cost
    if sqft <= 0:
        return []
    per_sqft = replacement / sqft
    issues: list[VerificationIssue] = []
    if sqft <= _SMALL_DWELLING_SQFT and replacement >= _SMALL_DWELLING_REPLACEMENT_ERROR:
        issues.append(
            make_issue(
                "replacement_vs_area",
                SEVERITY_ERROR,
                f"{area_key}={sqft:,.0f} sq ft with {cost_key}={replacement:,.0f} — a small dwelling cannot support a warehouse-scale rebuild cost",
                fields,
                cost_key,
            )
        )
    elif per_sqft > _HIGH_COST_PER_SQFT:
        issues.append(
            make_issue(
                "replacement_per_sqft",
                SEVERITY_WARNING,
                f"{cost_key} is {per_sqft:,.0f} per sq ft on {area_key}={sqft:,.0f} — far above a typical rebuild; review the figure",
                fields,
                cost_key,
            )
        )
    return issues


def deductible_vs_limit(fields: Mapping[str, Sequence[ExtractedField]]) -> list[VerificationIssue]:
    """The amount paid first cannot exceed what the policy would pay."""
    deductible = _first_number(fields, _DEDUCTIBLE)
    limit = _first_number(fields, _LIMIT)
    if deductible is None or limit is None:
        return []
    ded_key, ded = deductible
    lim_key, lim = limit
    if lim > 0 and ded > lim:
        return [
            make_issue(
                "deductible_exceeds_limit",
                SEVERITY_ERROR,
                f"{ded_key}={ded:,.0f} is greater than {lim_key}={lim:,.0f} — the deductible cannot exceed the limit",
                fields,
                ded_key,
            )
        ]
    return []


def cross_field_checks(fields: Mapping[str, Sequence[ExtractedField]]) -> list[VerificationIssue]:
    """Run every cross-field and conditional-range check."""
    issues: list[VerificationIssue] = []
    issues.extend(chronological_dates(fields))
    issues.extend(payroll_vs_headcount(fields))
    issues.extend(replacement_cost_vs_area(fields))
    issues.extend(deductible_vs_limit(fields))
    return issues
