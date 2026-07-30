"""Load redacted partner pilot packages from disk and run the insurance pipeline.

Expected folder layout (per submission):

  pilot_packages/<partner>/<submission_id>/
    acord.xml          (or *.xml)
    loss_run.md        (or *loss*)
    sov.md             (or *sov* / *schedule*)
    inspection.md      (optional, or *inspect*)
    supplemental/      (optional extra docs)
    meta.json          (optional: insured_name, expected_decision, notes)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PilotPackage:
    partner: str
    submission_id: str
    path: Path
    acord_xml: str | None = None
    loss_run: str | None = None
    schedule_of_values: str | None = None
    inspection_reports: list[str] = field(default_factory=list)
    supplemental_docs: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def insured_name(self) -> str:
        return str(self.meta.get("insured_name") or self.submission_id)


def discover_pilot_packages(root: Path | None = None) -> list[PilotPackage]:
    base = root or Path.cwd() / "pilot_packages"
    if not base.exists():
        return []
    packages: list[PilotPackage] = []
    for partner_dir in sorted(p for p in base.iterdir() if p.is_dir() and not p.name.startswith(("_", "."))):
        # Either partner/submission/… or flat submission folders
        children = [c for c in partner_dir.iterdir() if c.is_dir() and not c.name.startswith(("_", "."))]
        if any(_looks_like_package(c) for c in children):
            for sub in children:
                if _looks_like_package(sub):
                    packages.append(load_pilot_package(sub, partner=partner_dir.name))
        elif _looks_like_package(partner_dir):
            packages.append(load_pilot_package(partner_dir, partner="default"))
    return packages


def load_pilot_package(path: Path, partner: str = "default") -> PilotPackage:
    meta: dict[str, Any] = {}
    meta_path = path / "meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))

    acord = _read_first(path, patterns=("acord.xml", "*.xml"), exclude=("meta",))
    loss = _read_first(path, patterns=("loss_run.md", "*loss*", "*.md"), name_hint="loss")
    sov = _read_first(path, patterns=("sov.md", "*sov*", "*schedule*"))
    inspections = _read_all(path, patterns=("inspection.md", "*inspect*", "*loss_control*"))
    supplemental: list[str] = []
    supp_dir = path / "supplemental"
    if supp_dir.is_dir():
        for f in sorted(supp_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in {".md", ".txt", ".xml", ".json"}:
                supplemental.append(f.read_text(encoding="utf-8", errors="replace"))

    # Avoid double-counting: if loss/sov/inspection matched generic *.md, filter
    if loss and sov and loss == sov:
        sov = None

    return PilotPackage(
        partner=partner,
        submission_id=path.name,
        path=path,
        acord_xml=acord,
        loss_run=loss,
        schedule_of_values=sov,
        inspection_reports=inspections,
        supplemental_docs=supplemental,
        meta=meta,
    )


def run_pilot_package(
    package: PilotPackage,
    *,
    org_id: str | None = None,
    shadow: bool | None = None,
    use_llm: bool = False,
) -> dict[str, Any]:
    from insureflow.insurance.pipeline import InsurancePipeline
    from insureflow.pilot.sandbox_readiness import is_shadow_mode

    if not package.acord_xml:
        raise ValueError(f"Pilot package missing ACORD/XML: {package.path}")

    org = org_id or f"pilot-{package.partner}"
    shadow_mode = is_shadow_mode() if shadow is None else shadow
    pipeline = InsurancePipeline(org_id=org, use_llm=use_llm)
    result = pipeline.run(
        acord_xml=package.acord_xml,
        loss_run=package.loss_run,
        schedule_of_values=package.schedule_of_values,
        inspection_reports=package.inspection_reports or None,
        supplemental_docs=package.supplemental_docs or None,
        bundle_id=f"pilot-{package.partner}-{package.submission_id}",
        skip_core_integration=shadow_mode,  # never push to PAS in shadow
    )
    result["pilot"] = {
        "partner": package.partner,
        "submission_id": package.submission_id,
        "path": str(package.path),
        "shadow_mode": shadow_mode,
        "bind_allowed": not shadow_mode,
        "meta": package.meta,
    }
    if shadow_mode:
        result["pilot_note"] = (
            "Shadow mode: AI recommendation + UW review only. "
            "Policy bind is disabled until live PAS credentials are configured "
            "and PILOT_SHADOW_MODE=false."
        )
    expected = package.meta.get("expected_decision")
    if expected:
        actual = str(result.get("ai_decision") or "").lower()
        result["pilot"]["expected_decision"] = expected
        result["pilot"]["decision_match"] = actual == str(expected).lower()

    # Persist calibration row
    try:
        from insureflow.pilot.calibration import PilotCalibrationStore, record_from_pipeline_result

        PilotCalibrationStore().record(record_from_pipeline_result(result))
    except Exception:
        pass

    return result


def export_scenario_as_pilot_package(scenario_id: str, dest: Path) -> Path:
    """Materialize a built-in realworld scenario into a pilot_packages folder."""
    from insureflow.testing.realworld_scenarios import scenario_by_id

    scenario = scenario_by_id(scenario_id)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "acord.xml").write_text(scenario.acord_xml, encoding="utf-8")
    if scenario.loss_run:
        (dest / "loss_run.md").write_text(scenario.loss_run, encoding="utf-8")
    if scenario.schedule_of_values:
        (dest / "sov.md").write_text(scenario.schedule_of_values, encoding="utf-8")
    for i, report in enumerate(scenario.inspection_reports):
        name = "inspection.md" if i == 0 else f"inspection_{i + 1}.md"
        (dest / name).write_text(report, encoding="utf-8")
    if scenario.supplemental_docs:
        supp = dest / "supplemental"
        supp.mkdir(exist_ok=True)
        for i, doc in enumerate(scenario.supplemental_docs):
            (supp / f"supplemental_{i + 1}.md").write_text(doc, encoding="utf-8")
    meta = {
        "insured_name": scenario.insured_name,
        "condition": scenario.condition,
        "title": scenario.title,
        "source": f"realworld_scenario:{scenario.id}",
        "expected_decision": scenario.expectation.decision_in[0]
        if len(scenario.expectation.decision_in) == 1
        else None,
        "notes": scenario.expectation.description,
    }
    (dest / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return dest


def _looks_like_package(path: Path) -> bool:
    names = {p.name.lower() for p in path.iterdir() if p.is_file()}
    if "acord.xml" in names:
        return True
    return any(n.endswith(".xml") for n in names)


def _read_first(
    path: Path,
    patterns: tuple[str, ...],
    name_hint: str = "",
    exclude: tuple[str, ...] = (),
) -> str | None:
    for pattern in patterns:
        for f in sorted(path.glob(pattern)):
            if not f.is_file():
                continue
            low = f.name.lower()
            if any(x in low for x in exclude):
                continue
            # Broad globs must match hint when provided
            if name_hint and ("*" in pattern) and name_hint not in low:
                continue
            if low in {"meta.json"} or low.startswith("inspection"):
                if name_hint != "inspect":
                    continue
            return f.read_text(encoding="utf-8", errors="replace")
    if name_hint:
        for f in sorted(path.iterdir()):
            if f.is_file() and name_hint in f.name.lower() and f.suffix.lower() in {".md", ".txt", ".csv"}:
                return f.read_text(encoding="utf-8", errors="replace")
    return None


def _read_all(path: Path, patterns: tuple[str, ...]) -> list[str]:
    found: list[str] = []
    seen: set[Path] = set()
    for pattern in patterns:
        for f in sorted(path.glob(pattern)):
            if f.is_file() and f not in seen and f.suffix.lower() in {".md", ".txt"}:
                seen.add(f)
                found.append(f.read_text(encoding="utf-8", errors="replace"))
    return found
