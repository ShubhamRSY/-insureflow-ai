from __future__ import annotations

from datetime import date, timedelta
from typing import Any
from uuid import uuid4


def _today() -> date:
    return date.today()


def clue_query(body: dict[str, Any]) -> dict[str, Any]:
    """Synthetic CLUE Commercial responses keyed off legal_name for lab scenarios."""
    name = str(body.get("legal_name", "Unknown"))
    key = name.lower()
    records: list[dict[str, Any]] = []
    has_litigation = False
    has_cancellation = False

    if any(t in key for t in ("pacific", "marine", "coast")):
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
    elif any(t in key for t in ("arson", "fraud", "torch")):
        records.append(
            {
                "claim_id": f"CLUE-{uuid4().hex[:8].upper()}",
                "date_of_loss": (_today() - timedelta(days=400)).isoformat(),
                "loss_type": "fire",
                "paid_amount": 285000,
                "current_status": "closed",
                "policy_type": "CP",
                "claimant_name": name,
                "description": "Structure fire — cause under investigation (synthetic arson-flag scenario)",
                "flags": ["arson_investigation"],
            }
        )
        has_litigation = True
        has_cancellation = True
    elif any(t in key for t in ("litigat", "lawsuit", "northwind")):
        records.extend(
            [
                {
                    "claim_id": f"CLUE-{uuid4().hex[:8].upper()}",
                    "date_of_loss": (_today() - timedelta(days=1100)).isoformat(),
                    "loss_type": "general_liability",
                    "paid_amount": 92000,
                    "current_status": "closed",
                    "policy_type": "CGL",
                    "claimant_name": "Injured Party",
                    "description": "Product liability claim — settled",
                },
                {
                    "claim_id": f"CLUE-{uuid4().hex[:8].upper()}",
                    "date_of_loss": (_today() - timedelta(days=180)).isoformat(),
                    "loss_type": "auto_liability",
                    "paid_amount": 41000,
                    "current_status": "open",
                    "policy_type": "CA",
                    "claimant_name": "Third Party Driver",
                    "description": "Fleet collision with BI reserve — litigation pending",
                    "flags": ["litigation"],
                },
            ]
        )
        has_litigation = True
    elif any(t in key for t in ("clean", "greenfield", "newco")):
        records = []
    # else: empty history (default clean)

    return {
        "records": records,
        "total_claims_found": len(records),
        "total_paid": sum(float(r.get("paid_amount", 0)) for r in records),
        "has_prior_litigation": has_litigation,
        "has_prior_cancellation": has_cancellation,
        "synthetic": True,
        "mode": "gateway_synthetic",
        "scenario": ("arson_flag" if has_cancellation else ("multi_claim_litigation" if has_litigation else ("prior_gl" if records else "clean"))),
    }


def aplus_query(body: dict[str, Any]) -> dict[str, Any]:
    """Synthetic A-PLUS property loss history keyed off legal_name / address."""
    name = str(body.get("legal_name", "") or body.get("named_insured", "")).lower()
    address = str(body.get("address", "") or body.get("location", "")).lower()
    blob = f"{name} {address}"
    records: list[dict[str, Any]] = []
    arson = False
    repeated = False

    if any(t in blob for t in ("flood", "water", "basement")):
        records.append(
            {
                "claim_id": f"APLUS-{uuid4().hex[:8].upper()}",
                "date_of_loss": (_today() - timedelta(days=540)).isoformat(),
                "loss_type": "water",
                "paid_amount": 18500,
                "current_status": "closed",
                "description": "Water damage — burst supply line (synthetic)",
            }
        )
    if any(t in blob for t in ("arson", "fraud", "torch")):
        records.append(
            {
                "claim_id": f"APLUS-{uuid4().hex[:8].upper()}",
                "date_of_loss": (_today() - timedelta(days=900)).isoformat(),
                "loss_type": "fire",
                "paid_amount": 210000,
                "current_status": "closed",
                "description": "Fire loss with arson indicator (synthetic)",
                "flags": ["arson"],
            }
        )
        arson = True
    if any(t in blob for t in ("repeat", "serial", "frequent")) or len(records) >= 2:
        if not records:
            records.append(
                {
                    "claim_id": f"APLUS-{uuid4().hex[:8].upper()}",
                    "date_of_loss": (_today() - timedelta(days=200)).isoformat(),
                    "loss_type": "theft",
                    "paid_amount": 6200,
                    "current_status": "closed",
                    "description": "Contents theft (synthetic repeated-claim scenario)",
                }
            )
        repeated = True

    return {
        "records": records,
        "total_claims_found": len(records),
        "total_paid": sum(float(r.get("paid_amount", 0)) for r in records),
        "has_repeated_property_claims": repeated,
        "has_arson_or_fraud_flag": arson,
        "synthetic": True,
        "mode": "gateway_synthetic",
        "scenario": "arson_flag" if arson else ("repeated_claims" if repeated else ("water" if records else "clean")),
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
        "synthetic": True,
        "mode": "gateway_synthetic",
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
        "synthetic": True,
        "mode": "gateway_synthetic",
    }


def bureau_query(body: dict[str, Any]) -> dict[str, Any]:
    name = str(body.get("legal_name", ""))
    if "veririsk" in name.lower() or "construction" in name.lower():
        return {
            "paydex_score": 35,
            "financial_strength_rating": "2A",
            "failure_risk_score": 0.46,
            "delinquency_score": 0.52,
            "records": [
                {
                    "trade_id": "TR-GW-1",
                    "creditor": "Heavy Equipment Leasing",
                    "credit_limit": 420000,
                    "highest_credit": 400000,
                    "current_balance": 310000,
                    "past_due_days": 120,
                    "payment_status": "derogatory",
                    "opened_at": "2022-03-01",
                }
            ],
            "total_credit_limit": 420000,
            "total_current_balance": 310000,
            "number_of_derogatory_trades": 1,
            "has_bankruptcy_indicator": True,
            "has_lien_indicator": True,
            "has_judgment_indicator": True,
            "synthetic": True,
            "mode": "gateway_synthetic",
        }
    return {
        "paydex_score": 82,
        "financial_strength_rating": "3A",
        "failure_risk_score": 0.09,
        "delinquency_score": 0.07,
        "records": [],
        "total_credit_limit": 0,
        "total_current_balance": 0,
        "number_of_derogatory_trades": 0,
        "has_bankruptcy_indicator": False,
        "has_lien_indicator": False,
        "has_judgment_indicator": False,
        "synthetic": True,
        "mode": "gateway_synthetic",
    }


def public_records_query(body: dict[str, Any]) -> dict[str, Any]:
    name = str(body.get("legal_name", ""))
    if "veririsk" in name.lower() or "construction" in name.lower():
        return {
            "records": [
                {
                    "record_id": "JUD-GW-1",
                    "record_type": "judgment",
                    "jurisdiction": "CA Superior Court, Alameda",
                    "amount": 125000,
                    "filed_at": "2025-02-01",
                    "status": "open",
                    "plaintiff": "Subcontractor Trust",
                    "description": "Unpaid subcontractor judgment",
                },
                {
                    "record_id": "LIE-GW-1",
                    "record_type": "lien",
                    "jurisdiction": "Internal Revenue Service",
                    "amount": 88000,
                    "filed_at": "2025-05-01",
                    "status": "open",
                    "description": "Federal tax lien",
                },
            ],
            "total_records_found": 2,
            "total_judgment_amount": 125000,
            "has_bankruptcy": True,
            "has_active_judgment": True,
            "has_ucc_filing": False,
            "has_active_lien": True,
            "synthetic": True,
            "mode": "gateway_synthetic",
        }
    return {
        "records": [],
        "total_records_found": 0,
        "total_judgment_amount": 0,
        "has_bankruptcy": False,
        "has_active_judgment": False,
        "has_ucc_filing": False,
        "has_active_lien": False,
        "synthetic": True,
        "mode": "gateway_synthetic",
    }


def osha_query(body: dict[str, Any]) -> dict[str, Any]:
    name = str(body.get("legal_name", ""))
    if "veririsk" in name.lower() or "construction" in name.lower():
        return {
            "violations": [
                {
                    "violation_id": "VIO-GW-1",
                    "inspection_number": "INSP-GW-1",
                    "inspection_type": "accident",
                    "violation_type": "willful",
                    "description": "Failure to provide fall protection on elevated work platform",
                    "penalty": 72000,
                    "inspected_at": "2025-01-10",
                    "closed": False,
                    "items": 3,
                    "serious": True,
                }
            ],
            "total_violations": 1,
            "total_penalty": 72000,
            "has_willful_violation": True,
            "has_repeat_violation": False,
            "has_open_inspection": True,
            "safety_rating": "critical",
            "synthetic": True,
            "mode": "gateway_synthetic",
        }
    return {
        "violations": [],
        "total_violations": 0,
        "total_penalty": 0,
        "has_willful_violation": False,
        "has_repeat_violation": False,
        "has_open_inspection": False,
        "safety_rating": "low",
        "synthetic": True,
        "mode": "gateway_synthetic",
    }


def rating_agency_query(body: dict[str, Any]) -> dict[str, Any]:
    name = str(body.get("legal_name", ""))
    if "veririsk" in name.lower() or "construction" in name.lower():
        return {
            "issuer_rating": "B",
            "outlook": "negative",
            "watch": "on-watch",
            "agency": "S&P Global",
            "not_rated": False,
            "synthetic": True,
            "mode": "gateway_synthetic",
        }
    return {
        "issuer_rating": "",
        "outlook": "stable",
        "watch": "",
        "agency": "S&P Global",
        "not_rated": True,
        "synthetic": True,
        "mode": "gateway_synthetic",
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
    }
