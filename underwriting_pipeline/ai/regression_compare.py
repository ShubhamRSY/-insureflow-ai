"""Report every field whose hit count dropped between two scores of SUB-017 through SUB-076.

Reads score files only. Calls no model and rewrites no score file.

Run: python underwriting_pipeline/ai/regression_compare.py NEW.json [OLD.json] > report.md

NEW and OLD are files written by regression_dev.py. Without OLD, NEW is compared
with the published hold-out scores in deliverables/ai-engineer/evals/.
"""

import json
import re
import sys
from pathlib import Path

EVALS = Path(__file__).resolve().parents[2] / "deliverables" / "ai-engineer" / "evals"


def load(path: Path) -> dict:
    """{band: {"hits": {field: n}, "rows": {submission: {field: mark}}}}"""
    out = {}
    for item in json.loads(path.read_text())["bands"]:
        out[item["band"]] = {
            "hits": {field: marks.get("hit", 0) for field, marks in item["counted"].items()},
            "rows": {row["submission"]: row["checks"] for row in item["rows"]},
        }
    return out


def hit(mark) -> bool:
    return mark is True or mark == "hit"


def published(band: str) -> dict:
    """The published score: hit counts from the .md table, rows from the .json when it exists."""
    hits = {}
    for line in (EVALS / f"SUB-{band}-holdout.md").read_text().splitlines():
        found = re.match(r"\| (\w+) \| (\d+)", line)
        if found:
            hits[found.group(1)] = int(found.group(2))
    rows = {}
    saved = EVALS / f"SUB-{band}-holdout.json"
    if saved.exists():
        rows = {row["submission"]: row["checks"] for row in json.loads(saved.read_text())["submissions"]}
    return {"hits": hits, "rows": rows}


def compare(new: dict, old: dict, old_label: str, new_label: str) -> list[str]:
    lines = [f"| Set | Field | {old_label} hits | {new_label} hits | Change | Files that lost the hit |", "|---|---|---|---|---|---|"]
    drops = 0
    for band, now in new.items():
        was = old.get(band) or published(band)
        for field, hits in now["hits"].items():
            before = was["hits"].get(field)
            if before is None or hits == before:
                continue
            lost = sorted(
                sid for sid, checks in now["rows"].items()
                if hit(was["rows"].get(sid, {}).get(field)) and not hit(checks.get(field))
            )
            drops += hits < before
            lines.append(f"| SUB-{band} | {field} | {before} | {hits} | {hits - before:+d} | {', '.join(lost) or '—'} |")
    if len(lines) == 2:
        lines.append("| all | all | — | — | no change | — |")
    lines.append("")
    lines.append(f"Fields with a lower hit count: {drops}.")
    return lines


def demo() -> None:
    row = lambda mark: {"hits": {"year_built": int(mark)}, "rows": {"SUB-001": {"year_built": mark}}}
    out = compare({"001-010": row(False)}, {"001-010": row(True)}, "old", "new")
    assert "| SUB-001-010 | year_built | 1 | 0 | -1 | SUB-001 |" in out and out[-1].endswith(": 1."), out
    assert compare({"001-010": row(True)}, {"001-010": row(True)}, "old", "new")[-1].endswith(": 0.")


if __name__ == "__main__":
    demo()
    new_path = Path(sys.argv[1])
    old_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    print("\n".join(compare(load(new_path), load(old_path) if old_path else {}, old_path.name if old_path else "Published", new_path.name)))
