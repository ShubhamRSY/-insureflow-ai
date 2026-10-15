"""D-085 item 3: error analysis only, no fix. For each qwen/qwen3.8-27b sales miss in the D-084 run, show the gold, what the model
returned, what the gate and merge kept, and the sales/revenue/payroll lines in the documents. Replies come from that run's cache; no model call.

Run: env -u LLM_API_KEY LLM_BASE_URL=http://localhost:9/v1 LLM_MODEL=qwen/qwen3.8-27b LLM_CACHE_DIR=<qwen D-084 cache> .venv/bin/python deliverables/ai-engineer/analysis/sales_trace_qwen.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "underwriting_pipeline" / "ai"))
import llm_extract  # noqa: E402
import prepare  # noqa: E402
import sources  # noqa: E402

llm_extract._host = lambda: "api.groq.com"  # the run's host is in the cache key; LLM_BASE_URL is a dead local port


def _no_call(*_a, **_k):
    raise RuntimeError("analysis: no model call")


llm_extract._post = _no_call
run = json.loads((ROOT / "deliverables/ai-engineer/evals/dev-SUB-087-106-D-084-qwen-qwen3-8-27b.json").read_text())
misses = [r["submission"] for r in run["submissions"] if r["checks"].get("sales") not in ("hit", "hit (needs review)")]
CUE = re.compile(r"sales|revenue|receipts|payroll|gross|ventas|ingresos|nómina|annual", re.I)
out = ["# qwen/qwen3.8-27b sales misses, D-084 run (D-085 item 3)", "", "Error analysis only. No fix. No model call.", ""]
for sid in misses:
    folder = ROOT / "simulation/inbox" / sid
    docs = sources.read_folder(folder)
    saved = llm_extract.CACHE / "extractions" / f"{llm_extract.key_for(docs)}.json"
    raw = json.loads(saved.read_text())["parsed"] if saved.exists() else {}
    gate = llm_extract.llm_extract(docs) if raw else {"fields": [], "conflicts": []}
    report = prepare.process_submission(folder)
    gold = next((l.split(":", 1)[1].strip() for l in (ROOT / f"deliverables/senior-underwriter/gold-set/{sid}.md").read_text().splitlines() if l.startswith("- Sales:")), "?")
    pick = lambda rows: [{k: r.get(k) for k in ("value", "source", "quote", "reason")} for r in rows if r.get("field_id") == "sales_or_payroll"]
    conf = lambda cs: [[(s.get("value"), s.get("source")) for s in c.get("values") or []] for c in cs if c.get("field") == "sales_or_payroll"]
    final = next(r for r in report["fields"] if r["field_id"] == "sales_or_payroll")
    lines = [f"{d['name']}: {line.strip()[:150]}" for d in docs for line in (d.get("text") or "").splitlines() if CUE.search(line)][:6]
    out += [f"## {sid}", "", f"- Gold: {gold}", f"- Model returned: {json.dumps(pick(raw.get('fields') or []))}" + (f"; conflict {conf(raw.get('conflicts') or [])}" if conf(raw.get("conflicts") or []) else ""),
            f"- After the gate: {json.dumps(pick(gate['fields']))}" + (f"; conflict {conf(gate['conflicts'])}" if conf(gate["conflicts"]) else ""),
            f"- Final: {final.get('value')!r}, needs_review {final.get('needs_review')}, reason {final.get('reason')!r}" + (f"; open conflict {conf(report['conflicts'])}" if conf(report["conflicts"]) else ""),
            "- Document lines:", *[f"  - {l}" for l in lines], "- Cause: ", ""]
print("\n".join(out))
