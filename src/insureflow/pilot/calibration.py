"""Pilot calibration — compare AI decisions to expected / human labels."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class PilotRunRecord:
    partner: str
    submission_id: str
    bundle_id: str
    ai_decision: str
    expected_decision: str | None = None
    human_decision: str | None = None
    appetite_passed: bool | None = None
    human_review_required: bool | None = None
    decision_match: bool | None = None
    override: bool | None = None
    ran_at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())
    notes: str = ""


class PilotCalibrationStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path.cwd() / "evaluation_baselines" / "pilot_calibration.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, row: PilotRunRecord) -> None:
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(row)) + "\n")

    def load(self, limit: int = 500) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows[-limit:]

    def summarize(self) -> dict[str, Any]:
        rows = self.load()
        if not rows:
            return {
                "sample_size": 0,
                "match_rate": None,
                "override_rate": None,
                "by_decision": {},
                "mismatches": [],
                "message": "No pilot runs recorded yet — run packages with expected_decision in meta.json",
            }

        with_expected = [r for r in rows if r.get("expected_decision")]
        matches = [r for r in with_expected if r.get("decision_match")]
        overrides = [r for r in rows if r.get("override")]
        by_decision: dict[str, int] = {}
        for r in rows:
            d = str(r.get("ai_decision") or "unknown")
            by_decision[d] = by_decision.get(d, 0) + 1

        mismatches = [
            {
                "partner": r.get("partner"),
                "submission_id": r.get("submission_id"),
                "ai": r.get("ai_decision"),
                "expected": r.get("expected_decision"),
            }
            for r in with_expected
            if not r.get("decision_match")
        ][-20:]

        return {
            "sample_size": len(rows),
            "labeled_sample_size": len(with_expected),
            "match_rate": (len(matches) / len(with_expected)) if with_expected else None,
            "override_rate": (len(overrides) / len(rows)) if rows else None,
            "by_decision": by_decision,
            "mismatches": mismatches,
            "target_override_rate": 0.25,
            "on_track": (
                (len(overrides) / len(rows) < 0.25) if rows and overrides is not None else None
            ),
        }


def record_from_pipeline_result(result: dict[str, Any], *, human_decision: str | None = None) -> PilotRunRecord:
    pilot = result.get("pilot") or {}
    ai = str(result.get("ai_decision") or "").lower()
    expected = pilot.get("expected_decision")
    if expected is not None:
        expected = str(expected).lower()
    human = human_decision.lower() if human_decision else None
    match = None
    if expected is not None:
        match = ai == expected
    override = None
    if human is not None:
        override = human != ai
    return PilotRunRecord(
        partner=str(pilot.get("partner") or "unknown"),
        submission_id=str(pilot.get("submission_id") or result.get("bundle_id") or ""),
        bundle_id=str(result.get("bundle_id") or ""),
        ai_decision=ai,
        expected_decision=expected,
        human_decision=human,
        appetite_passed=result.get("appetite_filter_passed"),
        human_review_required=result.get("human_review_required"),
        decision_match=match if match is not None else pilot.get("decision_match"),
        override=override,
        notes=str((pilot.get("meta") or {}).get("notes") or ""),
    )


def run_batch_calibration(
    packages: list[Any],
    *,
    org_id: str = "pilot-cal",
    use_llm: bool = False,
    store: PilotCalibrationStore | None = None,
) -> dict[str, Any]:
    from insureflow.pilot.package_loader import run_pilot_package
    from insureflow.pilot.pii_gate import scan_pilot_package

    store = store or PilotCalibrationStore()
    results: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []

    for pkg in packages:
        scan = scan_pilot_package(pkg)
        if not scan["ok_to_run"]:
            blocked.append(scan)
            continue
        result = run_pilot_package(pkg, org_id=org_id, use_llm=use_llm, shadow=True)
        store.record(record_from_pipeline_result(result))
        results.append(
            {
                "partner": pkg.partner,
                "submission_id": pkg.submission_id,
                "decision": result.get("ai_decision"),
                "expected": (result.get("pilot") or {}).get("expected_decision"),
                "match": (result.get("pilot") or {}).get("decision_match"),
                "bundle_id": result.get("bundle_id"),
                "pii": {"blocking": scan["blocking_count"], "warnings": scan["warning_count"]},
            }
        )

    return {
        "ran": len(results),
        "blocked_pii": len(blocked),
        "blocked_packages": blocked,
        "results": results,
        "summary": store.summarize(),
    }
