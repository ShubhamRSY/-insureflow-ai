from __future__ import annotations

import json
import logging
import sys
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# Lazy import — Giskard is heavy (~10s import)
_GSKARD_AVAILABLE = False


def _import_giskard() -> None:
    global _GSKARD_AVAILABLE
    if _GSKARD_AVAILABLE:
        return
    try:
        import giskard  # noqa: F401
        _GSKARD_AVAILABLE = True
    except ImportError:
        logger.warning("Giskard not installed. Run: pip install giskard")
        _GSKARD_AVAILABLE = False


def _predict(df: pd.DataFrame) -> list[str]:
    """Prediction function wrapping the underwriting pipeline."""
    from insureflow.pipeline import UnderwritingPipeline
    pipeline = UnderwritingPipeline()

    results: list[str] = []
    for _, row in df.iterrows():
        acord = row.get("acord_xml", "")
        if not acord:
            results.append("ERROR: no ACORD XML provided")
            continue
        try:
            out = pipeline.run(acord_xml=acord)
            synthesis = out.get("synthesis", {})
            decision = synthesis.get("underwriting_decision", "UNKNOWN")
            analysis = (synthesis.get("analysis", "") or "")[:200]
            results.append(f"Decision: {decision}. Analysis: {analysis}")
        except Exception as exc:
            results.append(f"ERROR: {exc}")
    return results


def scan_pipeline(output_path: str | None = None) -> dict[str, Any]:
    """Scan the underwriting pipeline with Giskard for bias, robustness, etc."""
    _import_giskard()
    if not _GSKARD_AVAILABLE:
        return {"framework": "giskard", "error": "Giskard not installed"}

    import giskard
    from giskard import Dataset, Model, scan

    from evaluations.golden_dataset import golden_dataset

    cases = golden_dataset()
    records = [
        {
            "acord_xml": c.acord_xml,
            "insured_name": c.expected_insured_name,
            "construction": c.expected_construction,
            "occupancy": c.expected_occupancy,
            "naics": c.expected_naics or "",
            "protection_class": c.expected_protection_class or 0,
        }
        for c in cases
    ]
    df = pd.DataFrame(records)

    giskard_dataset = Dataset(
        df=df,
        name="InsureFlow Golden Dataset",
    )

    model = Model(
        model=_predict,
        model_type="text_generation",
        name="InsureFlow Underwriting Pipeline",
        description="Multi-agent AI underwriting pipeline that analyzes ACORD XML submissions and produces risk assessments, extraction results, and an underwriting decision (ACCEPT/REFER/DECLINE).",
        feature_names=["acord_xml"],
    )

    logger.info("Running Giskard scan (this may take a while)...")
    scanned = scan(model, giskard_dataset, verbose=False)

    issues = []
    if hasattr(scanned, "issues"):
        for issue in scanned.issues:
            issues.append({
                "tag": str(issue.tag),
                "group": str(issue.group),
                "description": str(issue.description),
                "severity": str(getattr(issue, "severity", "unknown")),
            })

    summary = {
        "framework": "giskard",
        "version": getattr(giskard, "__version__", "unknown"),
        "total_issues": len(issues),
        "issues": issues,
        "model_name": "InsureFlow Underwriting Pipeline",
        "dataset_name": "InsureFlow Golden Dataset",
        "dataset_size": len(df),
    }

    if output_path:
        import pathlib
        pathlib.Path(output_path).write_text(json.dumps(summary, indent=2, default=str))
        logger.info("Written to %s", output_path)

    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    out = sys.argv[1] if len(sys.argv) > 1 else "giskard_scan.json"
    result = scan_pipeline(out)
    print(json.dumps(result, indent=2, default=str))
