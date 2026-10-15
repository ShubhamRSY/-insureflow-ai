"""@model-risk T-027 analysis: carrier route on SUB-107..126 (copy of route_holdout_087.py, ids changed only) vs gold "Expected carrier route".

Reads extractions from a TEMP COPY of the cache (D-069: the real token log is never written).
Run with: env -u LLM_API_KEY [LLM_CACHE_DIR=<run cache>] .venv/bin/python deliverables/model-risk/route_holdout_107.py
(the venv has the reader libraries; system python3 does not). LLM_CACHE_DIR picks the cache to copy.
No key, so no model call can be made; a cache miss shows as call failed, not a miss.
Not a frozen scorer. Synthetic. Not a production approval.
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
assert not os.environ.get("LLM_API_KEY"), "run with env -u LLM_API_KEY"
tmp = Path(tempfile.mkdtemp())
shutil.copytree(os.environ.get("LLM_CACHE_DIR") or ROOT / "underwriting_pipeline" / "cache", tmp / "cache")
os.environ["LLM_CACHE_DIR"] = str(tmp / "cache")
sys.path.insert(0, str(ROOT / "underwriting_pipeline" / "app"))
import workbench  # noqa: E402

prepare = workbench.prepare
llm = workbench.llm_extract
# The cache lookup still asks endpoint_settings for a key. In this process only: hand it a placeholder
# and make the network unreachable, so a cache miss fails instead of calling a model.
_settings = llm.endpoint_settings
llm.endpoint_settings = lambda: _settings() if os.environ.get("LLM_API_KEY") else {**{"base": os.environ["LLM_BASE_URL"].rstrip("/"), "model": os.environ["LLM_MODEL"]}, "key": "no-key-cache-only"}


def _no_network(*a, **k):
    raise RuntimeError("cache miss: no model call allowed in this analysis")


llm.urllib.request.urlopen = _no_network
IDS = [f"SUB-{n:03d}" for n in range(107, 127)]
GOLD = ROOT / "deliverables" / "senior-underwriter" / "gold-set"
FIELDS = {"named_insured": "named insured", "premises_address": "premises", "effective_date": "effective date",
          "operations": "operations", "sales_or_payroll": "sales", "tiv_building": "tiv", "construction": "construction",
          "year_built": "year built", "loss_run_valued_through": "loss runs"}

rows = []
for sid in IDS:
    gold = {}
    for line in (GOLD / f"{sid}.md").read_text().splitlines():
        if line.startswith("- ") and ":" in line:
            k, v = line[2:].split(":", 1)
            gold[k.strip().lower()] = v.strip()
    report = prepare.process_submission(ROOT / "simulation" / "inbox" / sid)
    want = gold["expected carrier route"]
    if report.get("error"):
        got, mark = "call failed", "call failed"
    else:
        got = workbench.route(report)
        mark = "hit" if got == want else "miss"
    vals = {f["field_id"]: f["value"] for f in report.get("fields", [])}
    rows.append({"submission": sid, "expected": want, "got": got, "mark": mark, "note": None if report.get("error") else workbench.match(report)["note"],
                 "complete": report.get("complete"), "unread": report.get("unread") or [], "gold_status": gold["status"], "error": report.get("error"),
                 "fields": {f: [vals.get(f), gold.get(g)] for f, g in FIELDS.items()}})
shutil.rmtree(tmp)
print(json.dumps(rows, indent=1, ensure_ascii=False))
scored = [r for r in rows if r["mark"] != "call failed"]
print("route hits", sum(r["mark"] == "hit" for r in scored), "of", len(scored), "| call failed", len(rows) - len(scored))
print("unread rows", {r["submission"]: r["unread"] for r in rows if r["unread"]})
print("errors", {r["submission"]: r["error"] for r in rows if r["error"]})
