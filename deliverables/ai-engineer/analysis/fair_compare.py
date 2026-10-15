"""D-085 item 1: the three D-084 model runs on only the files every model completed (no failed call, not stopped). No model call.
Run: .venv/bin/python deliverables/ai-engineer/analysis/fair_compare.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "underwriting_pipeline" / "ai"))
import regression_dev  # noqa: E402

EVALS = ROOT / "deliverables" / "ai-engineer" / "evals"
MODELS = {"openai/gpt-oss-120b": "openai-gpt-oss-120b", "openai/gpt-oss-20b": "openai-gpt-oss-20b", "qwen/qwen3.8-27b": "qwen-qwen3-8-27b"}
runs = {m: {r["submission"]: r for r in json.loads((EVALS / f"dev-SUB-087-106-D-084-{t}.json").read_text())["submissions"]} for m, t in MODELS.items()}
done = lambda r: r.get("checks") and "call_failed" not in r["checks"].values() and not str(r.get("error") or "").startswith("not run")
common = sorted(set.intersection(*({s for s, r in rows.items() if done(r)} for rows in runs.values())))
out = [f"# Fair comparison on the {len(common)} files all three models completed (D-085 item 1)", "",
       "Development data. Files: " + ", ".join(common), "", "| Field | " + " | ".join(MODELS) + " |", "|---|" + "---|" * len(MODELS)]
for check in regression_dev.VALUE_CHECKS:
    out.append(f"| {check} | " + " | ".join(str(sum(runs[m][s]["checks"][check] in ("hit", "hit (needs review)") for s in common)) + f" of {len(common)}" for m in MODELS) + " |")
summ = {m: regression_dev.summarize([runs[m][s] for s in common]) for m in MODELS}
for label, key in (("silent error rate", "silent_error_rate"), ("automation rate", "automation_rate")):
    out.append(f"| **{label}** | " + " | ".join(f"{summ[m]['overall'][key]:.1%} ({summ[m]['overall']['silent' if 'silent' in key else 'automated']} of {summ[m]['overall']['scored']})" for m in MODELS) + " |")
out.append(f"| **hits, all 9 fields** | " + " | ".join(str(sum(runs[m][s]["checks"][c] in ("hit", "hit (needs review)") for s in common for c in regression_dev.VALUE_CHECKS)) + f" of {9 * len(common)}" for m in MODELS) + " |")
print("\n".join(out))
