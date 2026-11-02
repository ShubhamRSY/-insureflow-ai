#!/usr/bin/env python3
"""Render the P-075 (D-133) workbench cards (SUB-299 held on a cooking conflict, SUB-301 line copied) to HTML for the screenshot.

D-069: nothing real is written. The model host is stubbed (the application's own labelled lines, as the real model returns them),
the cache is a temp folder, and the page goes to the folder you pass. No model call.

Run: python deliverables/software-engineer/P-075-shot.py <out-html-folder>
"""
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for sub in ("app", "ai", "models"):
    sys.path.insert(0, str(ROOT / "underwriting_pipeline" / sub))

import llm_extract  # noqa: E402
import points  # noqa: E402
import prepare  # noqa: E402
import sources  # noqa: E402
import workbench  # noqa: E402

DEV = ROOT / "simulation" / "inbox-dev" / "document_conflicts"


def run(sid: str) -> dict:
    folder = DEV / sid
    rows = []
    for doc in sources.read_folder(folder):
        labels = {"loss_run_valued_through": ("valued as of:",)} if doc["name"] == "loss-runs.md" else prepare.LABELS if doc["name"] == "application.md" else {}
        for fid, label in labels.items():
            row = prepare.extract_labeled(doc["text"], label)[0]
            if row["value"] is not None and fid != "sales_or_payroll":
                rows.append({"field_id": fid, "value": row["value"], "source": doc["name"], "quote": doc["text"][row["start"] : row["end"]], "confidence": 0.95})
    sales = re.search(r"Annual sales: \$(\d+)", (folder / "application.md").read_text())
    assert sales
    rows.append({"field_id": "sales_or_payroll", "value": int(sales.group(1)), "source": "application.md", "quote": sales.group(0), "confidence": 1.0})
    reply = {"fields": rows, "conflicts": []}
    llm_extract._post = lambda settings, payload: {"choices": [{"message": {"content": json.dumps(reply)}}], "usage": {"total_tokens": 1}}
    report = prepare.process_submission(folder)
    report["saved_hash"] = "p075" + "0" * 60
    return {"id": sid, "report": report, "files": sorted(p.name for p in folder.iterdir()), "ignored": [], "route": "hold", "score": points.score_run(report), "snippets": {}}


def main() -> int:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    os.environ["LLM_BASE_URL"], os.environ["LLM_MODEL"], os.environ["LLM_API_KEY"] = "http://localhost:11434/v1", "p075-stub", "stub"
    llm_extract.CACHE = Path(tempfile.mkdtemp(prefix="p075-cache-"))
    cards = {"P-075": run("SUB-299"), "P-075-copied": run("SUB-301")}
    for name, card in cards.items():  # one page per card, so each screenshot shows its own card first
        (out / f"{name}.html").write_text(workbench.render([card], None))
    print(f"rendered to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
