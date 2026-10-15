"""D-084 item 3: one table from the dev-SUB-087-106-D-084-<model>.json files (development data, not a hold-out). No model call.
Run: .venv/bin/python deliverables/ai-engineer/analysis/model_compare.py > deliverables/ai-engineer/analysis/model-compare-D-084.md
"""
import json
from pathlib import Path

EVALS = Path(__file__).resolve().parents[2] / "ai-engineer" / "evals"
MODELS = ("openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b")
FIELDS = ("named_insured", "premises", "effective_date", "operations", "sales", "tiv", "construction", "year_built", "loss_runs")
NOTES = {"openai/gpt-oss-120b": "Stopped at SUB-099 (daily token limit hit; 12 of 20 files). Seconds per file before the limit: 12.7; the two files after it took 468 s and 555 s. Tokens: 33,145 for 12 calls (2,762 per file)."}

rows = {}
for model in MODELS:
    path = EVALS / f"dev-SUB-087-106-D-084-{model.replace('/', '-').replace('.', '-')}.json"
    if path.exists():
        rows[model] = json.loads(path.read_text())
out = ["# Model comparison on SUB-087–106 (D-084), development data, not a hold-out", "",
       "Same code (P-035, P-036, P-037), one uncached run per model on Groq, frozen eval_holdout_087.py marks, D-084 rates.", "",
       "| Field | " + " | ".join(rows) + " |", "|---|" + "---|" * len(rows)]
for f in FIELDS:
    out.append(f"| {f} hits | " + " | ".join(f"{d['counted'][f]['hit'] + d['counted'][f]['hit (needs review)']} of {sum(v for k, v in d['counted'][f].items() if k != 'call_failed')}" for d in rows.values()) + " |")
for label, key in (("silent error rate", "silent_error_rate"), ("automation rate", "automation_rate")):
    out.append(f"| **{label} (overall)** | " + " | ".join(str(d["metrics"]["overall"][key]) for d in rows.values()) + " |")
out.append("| files run | " + " | ".join(str(d["run"]["files_run"]) for d in rows.values()) + " |")
out.append("| failed calls (files) | " + " | ".join(str(d["metrics"].get("failed_call_files")) for d in rows.values()) + " |")
out.append("| failed attempts | " + " | ".join(json.dumps({k: v for k, v in d["run"]["failed_attempts"].items() if v}) or "none" for d in rows.values()) + " |")
out.append("| tokens per file | " + " | ".join(str(round(d["run"]["tokens"]["tokens"] / d["run"]["tokens"]["model_calls"])) if d["run"]["tokens"]["model_calls"] else "see note" for d in rows.values()) + " |")
out.append("| seconds per file (incl. rate-limit waits) | " + " | ".join(str(d["run"]["seconds_per_file"]) if d["run"]["tokens"]["model_calls"] else "see note" for d in rows.values()) + " |")
out.append("| stopped (daily limit) | " + " | ".join(str(d["run"]["stopped_at"] or "no") for d in rows.values()) + " |")
out += ["", *[f"- {m}: {n}" for m, n in NOTES.items() if m in rows]]
print("\n".join(out))
