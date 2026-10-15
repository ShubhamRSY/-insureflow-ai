"""D-085 item 2: qwen/qwen3.8-27b run 1 (D-084) vs run 2 (D-085), both uncached on SUB-087..106: per-field hits and every file whose mark changed.
Run: .venv/bin/python deliverables/ai-engineer/analysis/stability_qwen.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "underwriting_pipeline" / "ai"))
import regression_dev  # noqa: E402

EVALS = ROOT / "deliverables" / "ai-engineer" / "evals"
load = lambda name: json.loads((EVALS / name).read_text())
a, b = load("dev-SUB-087-106-D-084-qwen-qwen3-8-27b.json"), load("dev-SUB-087-106-D-085-qwen-qwen3-8-27b-run2.json")
ra, rb = ({r["submission"]: r for r in d["submissions"]} for d in (a, b))
hit = lambda m: m in ("hit", "hit (needs review)")
out = ["# qwen/qwen3.8-27b run-to-run stability on SUB-087–106 (D-085 item 2)", "", "Two uncached runs, same code, development data.", "",
       "| Field | Run 1 hits | Run 2 hits | Files whose mark changed |", "|---|---|---|---|"]
changed_total = 0
for c in regression_dev.VALUE_CHECKS:
    moved = [f"{s} {ra[s]['checks'].get(c)}→{rb[s]['checks'].get(c)}" for s in ra if ra[s]["checks"].get(c) != rb[s]["checks"].get(c)]
    changed_total += len(moved)
    out.append(f"| {c} | {sum(hit(r['checks'].get(c)) for r in ra.values())} | {sum(hit(r['checks'].get(c)) for r in rb.values())} | {len(moved)}: {', '.join(moved) or '—'} |")
for label, key in (("silent error rate", "silent_error_rate"), ("automation rate", "automation_rate")):
    out.append(f"| **{label}** | {a['metrics']['overall'][key]:.1%} | {b['metrics']['overall'][key]:.1%} | |")
out += ["", f"Marks that changed between runs: {changed_total} of {9 * len(ra)}.",
        f"Run 2: {json.dumps(b['run'])}"]
print("\n".join(out))
