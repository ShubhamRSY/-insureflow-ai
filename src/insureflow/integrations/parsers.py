from __future__ import annotations

from typing import Any


def _records_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("records", "claims", "items", "results", "data"):
        val = payload.get(key)
        if isinstance(val, list):
            return [x for x in val if isinstance(x, dict)]
        if isinstance(val, dict):
            nested = val.get("records") or val.get("claims") or val.get("items")
            if isinstance(nested, list):
                return [x for x in nested if isinstance(x, dict)]
    return []


def parse_clue_response(payload: dict[str, Any]) -> dict[str, Any]:
    records = _records_list(payload)
    return {
        "records": records,
        "total_claims_found": payload.get("total_claims_found", len(records)),
        "total_paid": payload.get("total_paid", sum(float(r.get("paid_amount", 0) or 0) for r in records)),
        "has_prior_litigation": bool(payload.get("has_prior_litigation")),
        "has_prior_cancellation": bool(payload.get("has_prior_cancellation")),
    }


def parse_ncci_response(payload: dict[str, Any]) -> dict[str, Any]:
    mods_raw = payload.get("experience_mods") or payload.get("mods") or _records_list(payload)
    mods: list[dict[str, Any]] = []
    for item in mods_raw:
        if not isinstance(item, dict):
            continue
        mods.append(
            {
                "mod_factor": float(item.get("mod_factor", item.get("experience_mod", 1.0)) or 1.0),
                "class_code": str(item.get("class_code", item.get("code", ""))),
                "class_code_description": str(item.get("class_code_description", item.get("description", ""))),
                "expected_losses": float(item.get("expected_losses", 0) or 0),
                "actual_losses": float(item.get("actual_losses", 0) or 0),
                "primary_losses": float(item.get("primary_losses", 0) or 0),
                "excess_losses": float(item.get("excess_losses", 0) or 0),
                "payroll": float(item.get("payroll", 0) or 0),
            }
        )
    return {
        "experience_mods": mods,
        "total_expected_losses": float(payload.get("total_expected_losses", sum(m["expected_losses"] for m in mods)) or 0),
        "total_actual_losses": float(payload.get("total_actual_losses", sum(m["actual_losses"] for m in mods)) or 0),
    }


def parse_aplus_response(payload: dict[str, Any]) -> dict[str, Any]:
    records = _records_list(payload)
    return {
        "records": records,
        "total_claims_found": payload.get("total_claims_found", len(records)),
        "total_paid": payload.get("total_paid", sum(float(r.get("paid_amount", 0) or 0) for r in records)),
        "has_repeated_property_claims": bool(payload.get("has_repeated_property_claims", len(records) >= 2)),
        "has_arson_or_fraud_flag": bool(payload.get("has_arson_or_fraud_flag")),
    }


def parse_cat_response(payload: dict[str, Any]) -> dict[str, Any]:
    exposures = payload.get("exposures") or _records_list(payload)
    return {
        "exposures": exposures,
        "portfolio_aggregate_aal": float(payload.get("portfolio_aggregate_aal", 0) or 0),
        "portfolio_aggregate_pml_100yr": float(payload.get("portfolio_aggregate_pml_100yr", 0) or 0),
        "portfolio_aggregate_pml_250yr": float(payload.get("portfolio_aggregate_pml_250yr", 0) or 0),
    }


def parse_bureau_response(payload: dict[str, Any]) -> dict[str, Any]:
    records = _records_list(payload)
    return {
        "records": records,
        "paydex_score": int(payload.get("paydex_score", payload.get("paydex", 0)) or 0),
        "financial_strength_rating": str(payload.get("financial_strength_rating", "")),
        "failure_risk_score": float(payload.get("failure_risk_score", 0) or 0),
        "delinquency_score": float(payload.get("delinquency_score", 0) or 0),
        "total_credit_limit": float(payload.get("total_credit_limit", sum(float(r.get("credit_limit", 0) or 0) for r in records))),
        "total_current_balance": float(payload.get("total_current_balance", sum(float(r.get("current_balance", 0) or 0) for r in records))),
        "number_of_derogatory_trades": int(payload.get("number_of_derogatory_trades", 0) or 0),
        "has_bankruptcy_indicator": bool(payload.get("has_bankruptcy_indicator")),
        "has_lien_indicator": bool(payload.get("has_lien_indicator")),
        "has_judgment_indicator": bool(payload.get("has_judgment_indicator")),
    }


def parse_public_records_response(payload: dict[str, Any]) -> dict[str, Any]:
    records = _records_list(payload)
    return {
        "records": records,
        "total_records_found": payload.get("total_records_found", len(records)),
        "total_judgment_amount": float(payload.get("total_judgment_amount", 0) or 0),
        "has_bankruptcy": bool(payload.get("has_bankruptcy")),
        "has_active_judgment": bool(payload.get("has_active_judgment")),
        "has_ucc_filing": bool(payload.get("has_ucc_filing")),
        "has_active_lien": bool(payload.get("has_active_lien")),
    }


def parse_osha_response(payload: dict[str, Any]) -> dict[str, Any]:
    violations = payload.get("violations") or _records_list(payload)
    return {
        "violations": violations,
        "total_violations": payload.get("total_violations", len(violations)),
        "total_penalty": float(payload.get("total_penalty", 0) or 0),
        "has_willful_violation": bool(payload.get("has_willful_violation")),
        "has_repeat_violation": bool(payload.get("has_repeat_violation")),
        "has_open_inspection": bool(payload.get("has_open_inspection")),
        "safety_rating": str(payload.get("safety_rating", "not_scored")),
    }


def parse_rating_agency_response(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "issuer_rating": str(payload.get("issuer_rating", "")),
        "outlook": str(payload.get("outlook", "stable")),
        "watch": str(payload.get("watch", "")),
        "agency": str(payload.get("agency", "rating_agency")),
        "not_rated": bool(payload.get("not_rated", False)),
    }
