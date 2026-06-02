from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

from evaluations.golden_dataset import GoldenCase, golden_dataset
from insureflow.pipeline import UnderwritingPipeline

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def extract_field(profile: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        val = profile.get(key)
        if val is not None:
            return val
    return None


def run_case(case: GoldenCase) -> dict[str, Any]:
    pipeline = UnderwritingPipeline()
    result = pipeline.run(acord_xml=case.acord_xml)

    step_results = result.get("steps", {})
    synthesis = result.get("synthesis", {})
    profile = synthesis.get("synthesized_profile", {})
    status = result.get("status", "unknown")

    actual = {
        "insured_name": extract_field(profile, "legal_name", "named_insured"),
        "construction": extract_field(profile, "construction_type"),
        "occupancy": extract_field(profile, "occupancy_type"),
        "protection_class": extract_field(profile, "protection_class"),
        "square_footage": extract_field(profile, "total_square_footage", "square_footage"),
        "stories": extract_field(profile, "number_of_stories"),
        "naics": extract_field(profile, "naics_code"),
        "revenue": extract_field(profile, "annual_revenue"),
        "payroll": extract_field(profile, "payroll"),
        "coverage_count": len(synthesis.get("synthesized_profile", {}).get("coverages", [])),
        "location_count": len(synthesis.get("synthesized_profile", {}).get("locations", [])),
    }

    return {
        "case": case.name,
        "status": status,
        "actual": actual,
        "expected": {
            "insured_name": case.expected_insured_name,
            "construction": case.expected_construction,
            "occupancy": case.expected_occupancy,
            "protection_class": case.expected_protection_class,
            "square_footage": case.expected_square_footage,
            "stories": case.expected_stories,
            "naics": case.expected_naics,
            "revenue": case.expected_revenue,
            "payroll": case.expected_payroll,
            "coverage_count": case.expected_coverage_count,
            "location_count": case.expected_location_count,
        },
        "ingestion_status": step_results.get("ingestion", {}).get("status"),
        "extraction_status": step_results.get("extraction", {}).get("status"),
        "match_rate": step_results.get("reconciliation", {}).get("match_rate", 0.0),
    }


def run_all(output_path: str | None = None) -> list[dict[str, Any]]:
    cases = golden_dataset()
    results: list[dict[str, Any]] = []
    passed = 0
    failed = 0

    for case in cases:
        try:
            r = run_case(case)
            results.append(r)
            has_errors = any(
                r.get("errors", [])
            )
            status = r.get("status", "failed")
            if status == "completed" and not has_errors:
                passed += 1
            else:
                failed += 1
            logger.info("[%s] status=%s", case.name, status)
        except Exception as exc:
            results.append({
                "case": case.name,
                "status": "error",
                "error": str(exc),
            })
            failed += 1

    summary = {
        "total": len(cases),
        "passed": passed,
        "failed": failed,
        "pass_rate": passed / max(len(cases), 1),
        "results": results,
    }

    if output_path:
        path = Path(output_path)
        path.write_text(json.dumps(summary, indent=2, default=str))

    return results


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "evaluation_results.json"
    run_all(out)
    print(f"Results written to {out}")
