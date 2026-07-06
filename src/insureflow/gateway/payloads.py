from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import uuid4


def _today() -> date:
    return date.today()


def clue_query(body: dict[str, Any]) -> dict[str, Any]:
    name = str(body.get("legal_name", "Unknown"))
    records: list[dict[str, Any]] = []
    if "pacific" in name.lower() or "marine" in name.lower():
        records.append(
            {
                "claim_id": f"CLUE-{uuid4().hex[:8].upper()}",
                "date_of_loss": (_today() - timedelta(days=730)).isoformat(),
                "loss_type": "general_liability",
                "paid_amount": 15000,
                "current_status": "closed",
                "policy_type": "CGL",
                "claimant_name": "Third Party Vendor",
                "description": "Slip and fall at insured premises",
            }
        )
    return {
        "records": records,
        "total_claims_found": len(records),
        "total_paid": sum(float(r.get("paid_amount", 0)) for r in records),
        "has_prior_litigation": False,
        "has_prior_cancellation": False,
    }


def ncci_query(body: dict[str, Any]) -> dict[str, Any]:
    name = str(body.get("legal_name", ""))
    mod = 1.12 if "pacific" in name.lower() else 1.0
    return {
        "experience_mods": [
            {
                "mod_factor": mod,
                "class_code": "8810",
                "class_code_description": "Clerical Office",
                "expected_losses": 45000,
                "actual_losses": 45000 * mod,
                "primary_losses": 12000,
                "excess_losses": 33000,
                "payroll": 1800000,
            }
        ],
        "total_expected_losses": 45000,
        "total_actual_losses": 45000 * mod,
    }


def aplus_query(body: dict[str, Any]) -> dict[str, Any]:
    return {
        "records": [],
        "total_claims_found": 0,
        "total_paid": 0,
        "has_repeated_property_claims": False,
        "has_arson_or_fraud_flag": False,
    }


def cat_query(body: dict[str, Any]) -> dict[str, Any]:
    return {
        "exposures": [
            {
                "peril": "wind",
                "aal": 12500,
                "pml_100yr": 85000,
                "pml_250yr": 142000,
            }
        ],
        "portfolio_aggregate_aal": 12500,
        "portfolio_aggregate_pml_100yr": 85000,
        "portfolio_aggregate_pml_250yr": 142000,
    }


def iso_health() -> dict[str, Any]:
    return {"status": "ok", "service": "iso_loss_costs", "version": "1.0"}


def policy_submit(system: str, body: dict[str, Any]) -> dict[str, Any]:
    ref = f"{system[:2].upper()}-JOB-{uuid4().hex[:10].upper()}"
    return {
        "success": True,
        "external_reference": ref,
        "job_number": ref,
        "status": "quoted",
        "insured_name": body.get("insured_name", ""),
    }


def policy_bind(system: str, body: dict[str, Any]) -> dict[str, Any]:
    policy = f"{system[:2].upper()}-POL-{_today().year}-{uuid4().hex[:8].upper()}"
    return {
        "success": True,
        "policy_number": policy,
        "status": "in_force",
        "quote_reference": body.get("quote_reference", ""),
    }


def enterprise_ack(service: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "status": "accepted",
        "service": service,
        "reference_id": f"{service[:3].upper()}-{uuid4().hex[:8]}",
        "payload": body or {},
    }
