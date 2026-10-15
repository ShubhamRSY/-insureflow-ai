"""D-082 item 3: error analysis only. For each premises miss on a typed file, show the address in the documents,
what the model returned, what the gate kept, and which rule cleared it (P-001 ZIP, P-002 validation, P-005 locations, or the model).
No fix. No model call: run with env -u LLM_API_KEY and LLM_CACHE_DIR set to the T-093 rerun cache; the OCR settings line of the
rerun commit (9e725e3) is used so the cache keys match.

Run: env -u LLM_API_KEY LLM_BASE_URL=http://localhost:9/v1 LLM_MODEL=openai/gpt-oss-120b LLM_CACHE_DIR=<rerun cache> .venv/bin/python deliverables/ai-engineer/analysis/premises_trace.py
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

sources.OCR_SETTINGS = "tesseract psm6; osd turn; deskew +-12; rule lift; x2 lanczos; pdf 200dpi"  # as at 9e725e3
llm_extract._host = lambda: "api.groq.com"  # the rerun's host is part of the cache key; LLM_BASE_URL points at a dead local port


def _no_call(*_a, **_k):
    raise RuntimeError("analysis: no model call; this file was not in the rerun cache")


llm_extract._post = _no_call
IDS = ("SUB-089", "SUB-092", "SUB-098", "SUB-099", "SUB-103")
TRACE: dict = {}


def wrap(module, name, label, fields=("premises_address",)):
    real = getattr(module, name)

    def run(merged, *a, **k):
        before = {f: (merged[f].get("value") if merged.get(f) else None) for f in fields}
        out = real(merged, *a, **k)
        after = {f: (merged[f].get("value") if merged.get(f) else None) for f in fields}
        for f in fields:
            if before[f] != after[f]:
                TRACE.setdefault(f, []).append(f"{label}: {before[f]!r} -> {after[f]!r}")
        return out

    setattr(module, name, run)


FIELDS = ("premises_address", "named_insured", "operations")
wrap(prepare, "drop_premises_without_zip", "P-001 ZIP rule")
wrap(prepare, "apply_locations", "P-005 locations")
wrap(prepare, "apply_document_rules", "document rules", FIELDS)


def gold(sid):
    return dict(l[2:].split(":", 1) for l in (ROOT / f"deliverables/senior-underwriter/gold-set/{sid}.md").read_text().splitlines() if l.startswith("- ") and ":" in l)


def lines_with(texts, needle):
    out = []
    for name, text in texts.items():
        for line in text.splitlines():
            if needle and needle.lower() in line.lower():
                out.append(f"{name}: {line.strip()[:160]}")
    return out[:4]


def main():
    out = ["# Premises, name and operations trace — typed files, T-093 rerun (D-082 item 3)", "",
           "Error analysis only. No fix. Replies from the T-093 rerun cache (commit 9e725e3, openai/gpt-oss-120b); no model call.", ""]
    for sid in IDS:
        TRACE.clear()
        folder = ROOT / "simulation/inbox" / sid
        docs = sources.read_folder(folder)
        texts = {d["name"]: d["text"] for d in docs}
        key = llm_extract.key_for(docs)
        saved = llm_extract.CACHE / "extractions" / f"{key}.json"
        raw = json.loads(saved.read_text())["parsed"] if saved.exists() else None
        gate = llm_extract.llm_extract(docs) if raw else None
        report = prepare.process_submission(folder)
        g = gold(sid)
        fields = ("premises_address", "named_insured", "operations") if sid == "SUB-098" else ("premises_address",)
        out += [f"## {sid}", ""]
        for field in fields:
            gkey = {"premises_address": "Premises", "named_insured": "Named insured", "operations": "Operations"}[field]
            gv = g.get(gkey, "").strip()
            street = re.match(r"\d+\s+\S+(\s+\S+)?", gv)
            needle = street.group(0) if street and field == "premises_address" else gv[:20]
            raw_rows = [r for r in (raw or {}).get("fields", []) if r.get("field_id") == field]
            raw_conf = [c for c in (raw or {}).get("conflicts", []) if c.get("field") == field]
            gate_rows = [r for r in (gate or {}).get("fields", []) if r.get("field_id") == field]
            gate_conf = [c for c in (gate or {}).get("conflicts", []) if c.get("field") == field]
            final = next(r for r in report["fields"] if r["field_id"] == field)
            fin_conf = [c for c in report["conflicts"] if c.get("field") == field]
            out += [f"### {field}", "",
                    f"- Gold: {gv}",
                    "- In the documents: " + ("; ".join(lines_with(texts, needle)) or "not found by the street/name search"),
                    "- Model returned: " + (json.dumps([{k: r.get(k) for k in ("value", "source", "quote")} for r in raw_rows]) if raw_rows else "no row") +
                    (f"; conflict sides {json.dumps([[s.get('value') for s in c.get('values') or []] for c in raw_conf])}" if raw_conf else ""),
                    "- After the gate (accept_field): " + (json.dumps([{k: r.get(k) for k in ("value", "reason", "needs_review")} for r in gate_rows]) if gate_rows else "no row") +
                    (f"; conflicts kept {json.dumps([[s.get('value') for s in c['values']] for c in gate_conf])}" if gate_conf else ""),
                    "- Rules on the way: " + ("; ".join(TRACE.get(field, [])) or "none changed it"),
                    f"- Final: {final.get('value')!r}, address_check {final.get('address_check')!r}, needs_review {final.get('needs_review')}"
                    + (f"; open conflict {json.dumps([[s.get('value') for s in c.get('values') or []] for c in fin_conf])}" if fin_conf else "")
                    + (f"; locations {json.dumps(report.get('locations'))}" if field == 'premises_address' and report.get("locations") else ""),
                    ""]
    print("\n".join(out))


if __name__ == "__main__":
    main()
