"""Auto-redact blocking PII in pilot package text files."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from insureflow.pilot.package_loader import PilotPackage, load_pilot_package
from insureflow.pilot.pii_gate import BLOCKING, scan_pilot_package
from insureflow.redaction.detector import PIIDetector
from insureflow.redaction.redactor import PIIRedactor

TEXT_SUFFIXES = {".xml", ".md", ".txt", ".json", ".csv"}


class BlockingOnlyRedactor(PIIRedactor):
    """Redact only high-risk categories; leave broker emails/phones as warnings."""

    def redact(self, text: str, mask: bool = True) -> str:
        spans = [s for s in self.detector.detect(text) if s.category in BLOCKING]
        if not spans:
            return text
        spans.sort(key=lambda s: s.start)
        result: list[str] = []
        pos = 0
        for span in spans:
            if span.start > pos:
                result.append(text[pos : span.start])
            result.append(self._replace(span, mask))
            pos = max(pos, span.end)
        result.append(text[pos:])
        return "".join(result)


def redact_pilot_package(
    package: PilotPackage,
    *,
    inplace: bool = False,
    dest: Path | None = None,
) -> dict[str, Any]:
    """Write a redacted copy of a package (or overwrite). Returns scan before/after."""
    before = scan_pilot_package(package)
    src = package.path
    if inplace:
        out = src
    else:
        out = dest or (src.parent / f"{src.name}_redacted")
        if out.exists():
            shutil.rmtree(out)
        shutil.copytree(src, out)

    redactor = BlockingOnlyRedactor(detector=PIIDetector())
    changed: list[str] = []
    for path in sorted(out.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if path.name == "meta.json":
            continue
        original = path.read_text(encoding="utf-8", errors="replace")
        redacted = redactor.redact(original)
        if redacted != original:
            path.write_text(redacted, encoding="utf-8")
            changed.append(str(path.relative_to(out)))

    meta_path = out / "meta.json"
    meta: dict[str, Any] = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            meta = {}
    meta["pii_redacted"] = True
    meta["pii_redacted_files"] = changed
    meta["pii_blocking_before"] = before["blocking_count"]
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    reloaded = load_pilot_package(out, partner=package.partner)
    after = scan_pilot_package(reloaded)
    return {
        "path": str(out),
        "partner": package.partner,
        "submission_id": out.name,
        "files_changed": changed,
        "before": before,
        "after": after,
        "ok_to_run": after["ok_to_run"],
    }


def redact_blocking_categories_in_text(text: str) -> str:
    return BlockingOnlyRedactor().redact(text)
