"""ISO / NCCI form schedules attached to quotes — not a live ISO forms library.

These are the standard policy jackets and common endorsements a UW expects to
see on the worksheet. They do not constitute a filed form edition or SERFF
form schedule until the carrier book supplies edition dates.
"""

from __future__ import annotations

from typing import Any

from insureflow.rating.models import InsuranceLine

_FORMS: dict[str, list[dict[str, str]]] = {
    InsuranceLine.COMMERCIAL_PROPERTY.value: [
        {"number": "CP 00 10", "title": "Building and Personal Property Coverage Form", "edition": "carrier"},
        {"number": "CP 00 30", "title": "Business Income (and Extra Expense)", "edition": "carrier"},
        {"number": "CP 10 30", "title": "Causes of Loss — Special Form", "edition": "carrier"},
    ],
    InsuranceLine.GENERAL_LIABILITY.value: [
        {"number": "CG 00 01", "title": "Commercial General Liability Coverage Form", "edition": "carrier"},
        {"number": "CG 21 47", "title": "Employment-Related Practices Exclusion", "edition": "carrier"},
    ],
    InsuranceLine.UMBRELLA.value: [
        {"number": "CU 00 01", "title": "Commercial Liability Umbrella Coverage Form", "edition": "carrier"},
    ],
    InsuranceLine.COMMERCIAL_AUTO.value: [
        {"number": "CA 00 01", "title": "Business Auto Coverage Form", "edition": "carrier"},
        {"number": "CA 99 03", "title": "Auto Medical Payments", "edition": "carrier"},
    ],
    InsuranceLine.WORKERS_COMP.value: [
        {"number": "WC 00 00 00 A", "title": "Workers Compensation and Employers Liability", "edition": "NCCI"},
    ],
    InsuranceLine.CYBER.value: [
        {"number": "CY 00 01", "title": "Cyber Incident Response / Liability (manuscript/ISO cyber)", "edition": "carrier"},
    ],
    InsuranceLine.CRIME.value: [
        {"number": "CR 00 20", "title": "Commercial Crime Coverage Form", "edition": "carrier"},
    ],
    InsuranceLine.INLAND_MARINE.value: [
        {"number": "CM 00 01", "title": "Commercial Inland Marine Conditions", "edition": "carrier"},
    ],
    InsuranceLine.BUILDERS_RISK.value: [
        {"number": "CP 00 20", "title": "Builders Risk Coverage Form", "edition": "carrier"},
    ],
    InsuranceLine.BOP.value: [
        {"number": "BP 00 03", "title": "Businessowners Coverage Form", "edition": "carrier"},
    ],
    InsuranceLine.COMMERCIAL_PACKAGE.value: [
        {"number": "IL 00 17", "title": "Common Policy Conditions", "edition": "carrier"},
        {"number": "CP 00 10", "title": "Building and Personal Property Coverage Form", "edition": "carrier"},
        {"number": "CG 00 01", "title": "Commercial General Liability Coverage Form", "edition": "carrier"},
    ],
    InsuranceLine.DIRECTORS_AND_OFFICERS.value: [
        {"number": "DO 00 01", "title": "Directors & Officers Liability (manuscript)", "edition": "carrier"},
    ],
    InsuranceLine.ERRORS_AND_OMISSIONS.value: [
        {"number": "PR 00 01", "title": "Professional Liability / E&O (manuscript)", "edition": "carrier"},
    ],
    InsuranceLine.SURETY.value: [
        {"number": "SURETY", "title": "Surety Bond Form (penal sum / obligee)", "edition": "carrier"},
    ],
    InsuranceLine.LIFE.value: [
        {"number": "LIFE APP", "title": "Life application + illustration / NAIC disclosure", "edition": "state"},
    ],
}


def iso_form_schedule(
    line: InsuranceLine | str,
    *,
    coverage_id: str | None = None,
    product_id: str | None = None,
) -> list[dict[str, Any]]:
    key = line.value if isinstance(line, InsuranceLine) else str(line or "").strip().lower()
    forms = [dict(f) for f in _FORMS.get(key, [])]
    cov = (coverage_id or "").lower()
    if "products" in cov:
        forms.append({"number": "CG 24 04", "title": "Waiver of Transfer of Rights of Recovery", "edition": "carrier"})
    if product_id == "liquor_liability":
        forms.append({"number": "CG 24 08", "title": "Liquor Liability Coverage", "edition": "carrier"})
    if not forms:
        forms.append(
            {
                "number": "MANUSCRIPT",
                "title": f"No ISO jacket mapped for {key or product_id or 'unknown'} — catalog / manuscript only",
                "edition": "unmapped",
            }
        )
    return forms


def attach_iso_forms(meta: dict[str, Any], line: InsuranceLine | str, *, coverage_id: str | None = None, product_id: str | None = None) -> dict[str, Any]:
    out = dict(meta or {})
    out["iso_forms"] = iso_form_schedule(line, coverage_id=coverage_id, product_id=product_id)
    out["iso_forms_source"] = "standard_jacket_map"
    return out
