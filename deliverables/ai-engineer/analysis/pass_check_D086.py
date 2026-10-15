"""D-086 item 3: the pass criteria set before the run. Development data, not a hold-out. No model call.
sales >= 8 of 9 on the shared files; silent error rate <= 2.5% and automation rate >= 71% on all 20 files.
Run: .venv/bin/python deliverables/ai-engineer/analysis/pass_check_D086.py
"""
import json
from pathlib import Path

EVALS = Path(__file__).resolve().parents[2] / "ai-engineer" / "evals"
SHARED = ("SUB-087", "SUB-089", "SUB-090", "SUB-091", "SUB-092", "SUB-093", "SUB-095", "SUB-097", "SUB-098")
d = json.loads((EVALS / "dev-SUB-087-106-D-086-qwen-qwen3-8-27b.json").read_text())
rows = {r["submission"]: r for r in d["submissions"]}
sales = sum(rows[s]["checks"].get("sales") in ("hit", "hit (needs review)") for s in SHARED)
silent, auto = d["metrics"]["overall"]["silent_error_rate"], d["metrics"]["overall"]["automation_rate"]
checks = [("sales on the 9 shared files", f"{sales} of 9", sales >= 8, ">= 8 of 9"),
          ("silent error rate, 20 files", f"{silent:.1%}", silent <= 0.025, "<= 2.5%"),
          ("automation rate, 20 files", f"{auto:.1%}", auto >= 0.71, ">= 71%")]
out = ["# D-086 re-check: qwen/qwen3.8-27b after P-038, pass criteria", "", "| Criterion | Result | Needed | Pass |", "|---|---|---|---|"]
out += [f"| {n} | {r} | {need} | {'PASS' if ok else 'FAIL'} |" for n, r, ok, need in checks]
out += ["", f"All pass: {'yes' if all(c[2] for c in checks) else 'no'}.",
        "Sales on all 20: " + str(sum(r["checks"].get("sales") in ("hit", "hit (needs review)") for r in rows.values())) + f" of {len(rows)}.",
        f"Run: {json.dumps(d['run'])}"]
print("\n".join(out))
