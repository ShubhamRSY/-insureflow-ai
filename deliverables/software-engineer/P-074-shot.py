#!/usr/bin/env python3
"""Render the P-074 (D-132) workbench cards to HTML for the screenshot.

D-069: nothing real is written. The page is rendered from synthetic cards into a temporary
folder; the real workbench page, the decision log and the outboxes are not touched.

Run: python deliverables/software-engineer/P-074-shot.py <out-html-folder>
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


def side(value, source, quote, **flags):
    return {"value": value, "source": source, "quote": quote, "needs_review": bool(flags), **flags}


def card(sub, name, sales_conflict):
    return item(sub, "incomplete", [
        field("named_insured", name, f"Named insured: {name}"),
        field("premises_address", "5120 Cedar Ridge Ln, Temple TX 76502", "Premises address: 5120 Cedar Ridge Ln, Temple TX 76502"),
        field("effective_date", "2026-12-01", "Effective date: 2026-12-01"),
        field("operations", "Wholesale paper and packaging supplies, warehouse", "Operations: Wholesale paper and packaging supplies, warehouse"),
        field("sales_or_payroll", None, "", needs_review=True, confidence=0.0),
        field("tiv_building", "640000", "Building TIV: $640000"),
        field("construction", "Metal", "Construction: Metal"),
        field("year_built", "2001", "Year built: 2001"),
        field("loss_run_valued_through", "2026-07-15", "Valued as of: 2026-07-15"),
    ], [{"field": "sales_or_payroll", "values": sales_conflict, "resolution": "unresolved", "resolved_value": None, "resolved_by": None}],
        ["sales or payroll"])


c297 = card("SUB-297", "Cedar Ridge Paper Supply LLC", [
    side("1180000", "application.md", "Annual sales: $1180000"),
    side("1350000", "email.md", "Last year we did about $1.35 million", reason="approximate figure: Last year we did about $1.35 million", approximate=True)])
c298 = card("SUB-298", "Pinecrest Tile Supply LLC", [
    side("1150000", "application.md", "Sales 1.15 million", reason="quote not found in application.md", unverified=True),
    side("1200000", "email.md", "we did 1.2 million", reason="quote not found in email.md", unverified=True)])


def main() -> int:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    (out / "P-074.html").write_text(workbench.render([c297, c298], None))
    print(f"rendered to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
