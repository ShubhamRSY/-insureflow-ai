#!/usr/bin/env python3
"""Render the T-118 (P-070) workbench cards to HTML for the screenshot.

D-069: nothing real is written. The page is rendered from synthetic cards into a temporary
folder; the real workbench page, the decision log and the outboxes are not touched.

Run: python deliverables/software-engineer/T-118-shot.py <out-html-folder>
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "underwriting_pipeline" / "app"))
sys.path.insert(0, str(ROOT / "underwriting_pipeline" / "ai"))
sys.path.insert(0, str(ROOT / "underwriting_pipeline" / "models"))

import points  # noqa: E402
import prepare  # noqa: E402
import workbench  # noqa: E402


def field(field_id, value, quote, source="application.md", needs_review=False, reason=None, confidence=0.95):
    return {"field_id": field_id, "value": value, "source": source, "quote": quote,
            "confidence": confidence, "needs_review": needs_review, "reason": reason}


def item(sub, status, fields, conflicts, missing, route="hold"):
    report = {
        "status": status, "status_reason": None, "error": None, "complete": not missing,
        "fields": fields, "conflicts": conflicts, "needs_human": [], "missing": missing,
        "extra": [], "locations": [], "saved_hash": "t1180000000000000000000000000000000000000000000000000000000dead",
        "sprinklers": "yes", "cooking": {"state": "none"}, "folder": sub, "class_lines": {},
    }
    return {"id": sub, "report": report, "files": ["application.md", "email.md", "loss-runs.md", "schedule.csv"],
            "ignored": [], "route": route, "score": points.score_run(report), "snippets": {}}


def conflict(field_id, left, right):
    return {"field": field_id,
            "values": [{"value": left[0], "source": left[1], "quote": left[2]}, {"value": right[0], "source": right[1], "quote": right[2]}],
            "resolution": "unresolved", "resolved_value": None, "resolved_by": None}


OPS = "Lessor of professional office building with two office suites on the second floor"

conflicts_card = item(
    "SUB-292",
    prepare.REVIEW_PENDING,
    [
        field("named_insured", "Lakeshore Holdings LLC", "Named insured: Lakeshore Holdings LLC"),
        field("premises_address", "2300 Lakeshore Dr, Killeen TX 76541", "Premises address: 2300 Lakeshore Dr, Killeen TX 76541"),
        field("effective_date", "2026-12-01", "Effective date: 2026-12-01"),
        field("operations", OPS, "Operations: " + OPS, needs_review=True, reason="operations may be missing: no cooking", confidence=0.74),  # P-072 (D-124)
        field("sales_or_payroll", None, "Annual sales: $412,000", needs_review=True,
              reason="the documents state different sales figures", confidence=0.0),
        field("tiv_building", "1500000", "Building TIV: $1500000"),
        field("construction", "Masonry", "Construction: Masonry"),
        field("year_built", "2000", "Year built: 2000"),
        field("loss_run_valued_through", "2026-07-15", "Valued as of: 2026-07-15"),
    ],
    [
        conflict("square_feet", ("2800", "application.md", "Square footage: 2800"), ("3150", "schedule.csv", "Main building\t3150\t2025")),
        conflict("sales_or_payroll", ("412000", "application.md", "Annual sales: $412,000"), ("540000", "email.md", "Last year we did about 540k in sales.")),
        conflict("suite_count", ("2", "application.md", "Operations: " + OPS), ("3", "email.md", "The second floor holds three suites.")),
    ],
    [],
)

# P-072 (D-124): "no cooking" is never added; the operations value keeps its review note.
no_cooking_card = item(
    "SUB-293",
    prepare.REVIEW_PENDING,
    [
        field("named_insured", "Brookfield Design Studio LLC", "Named insured: Brookfield Design Studio LLC"),
        field("premises_address", "915 Brookfield Rd, Plano TX 75074", "Premises address: 915 Brookfield Rd, Plano TX 75074"),
        field("effective_date", "2026-12-01", "Effective date: 2026-12-01"),
        field("operations", "Office of an architectural design studio", "Operations: Office of an architectural design studio",
              needs_review=True, reason="operations may be missing: no cooking", confidence=0.74),
        field("sales_or_payroll", "950000", "Annual sales: $950000"),
        field("tiv_building", "900000", "Building TIV: $900000"),
        field("construction", "Masonry", "Construction: Masonry"),
        field("year_built", "2005", "Year built: 2005"),
        field("loss_run_valued_through", "2026-07-15", "Valued as of: 2026-07-15"),
    ],
    [],
    [],
)


def main() -> int:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    (out / "T-118-document-conflicts.html").write_text(workbench.render([conflicts_card], None))
    (out / "T-118-no-cooking-cited.html").write_text(workbench.render([no_cooking_card], None))
    print(f"rendered 2 pages to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
