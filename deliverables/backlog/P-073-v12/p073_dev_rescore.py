#!/usr/bin/env python3
"""P-073 (D-126) dev re-score, scorer v11 vs v12, SUB-127-296, cached replies only, 0 model calls.
Run (env LLM_* unset): .venv/bin/python deliverables/senior-test-engineer/p073_dev_rescore.py CACHE_COPY_DIR OUT_JSON
CACHE_COPY_DIR is a temp copy of an extractions cache (D-069: the real cache is never opened for writing). The cache key includes the model and host
the replies were saved with, so those two values are patched in-process (env stays unset); no API key exists and _post raises, so a file with no saved
reply is recorded as such and never sent. Reads inboxes and gold; writes only OUT_JSON."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "underwriting_pipeline" / "ai"))
sys.path.insert(0, str(ROOT / "underwriting_pipeline" / "app"))
import llm_extract  # noqa: E402
import prepare  # noqa: E402
import eval_holdout_v11 as v11  # noqa: E402
import eval_holdout_v12 as v12  # noqa: E402

MODEL, HOST = "qwen/qwen3.8-27b", "api.groq.com"  # from the saved score files' "model" and "host"
cache = Path(sys.argv[1])
llm_extract.CACHE = cache
llm_extract._host = lambda: HOST
llm_extract.endpoint_settings = lambda: {"base": "https://api.groq.com/openai/v1", "model": MODEL, "key": ""}
llm_extract.provider_guard = lambda calling=True: llm_extract.endpoint_settings()


def _no_call(settings, payload):
    raise RuntimeError("no saved reply (0 model calls allowed)")


llm_extract._post = _no_call
G = ROOT / "deliverables"
SETS = [  # (first, last, gold dir, inbox dir)
    (127, 173, G / "ai-engineer/evals/P-069-dev/gold-SUB-127-173", ROOT / "simulation/inbox"),
    (174, 205, G / "senior-underwriter/gold-set", ROOT / "simulation/inbox"),
    (206, 237, G / "ai-engineer/evals/P-069-dev/gold-T-108", ROOT / "simulation/inbox"),
    (238, 269, G / "senior-underwriter/gold-set", ROOT / "simulation/inbox"),
    (270, 279, G / "senior-underwriter/gold-set-commercial_package/dev", ROOT / "simulation/inbox-dev/commercial_package"),
    (280, 289, G / "senior-underwriter/gold-set-commercial_property/dev", ROOT / "simulation/inbox-dev/commercial_property"),
    (290, 296, G / "senior-underwriter/gold-set-document_conflicts/dev", ROOT / "simulation/inbox-dev/document_conflicts"),
]


def cooking(scorer, answer: str, items: str):
    """(gold cooking value, hit?) for a card whose gold has a cooking slot; None otherwise."""
    bt, rest, bad = scorer.split_items(items)
    if bad or any(not scorer._slots(r) for r in rest):
        return None
    want = scorer._slots("; ".join(rest)).get("cooking")
    if want is None:
        return None
    low = scorer.BT_TOKEN.sub(" ", (answer or "").lower())
    got = scorer._slots(low).get("cooking")
    if scorer is v12 and want == "none":
        ok = not v12.cooking_evidence(low) and got in (None, "none")
    else:
        ok = got == want
    return want, ok, got


rows = []
for a, b, gold_dir, inbox in SETS:
    for n in range(a, b + 1):
        sid = f"SUB-{n:03d}"
        row = {"id": sid, "set": f"{a}-{b}"}
        try:
            gold_text = (gold_dir / f"{sid}.md").read_text()
            report = prepare.process_submission(inbox / sid)
        except (SystemExit, Exception) as why:  # a missing saved reply
            row["error"] = f"{type(why).__name__}: {str(why)[:160]}"
            rows.append(row)
            continue
        ops = next((f["value"] for f in report["fields"] if f["field_id"] == "operations"), None)
        items = v11.parse_gold(gold_text).get("operations items") or ""
        try:
            m11, m12 = v11.score_report(sid, gold_text, report), v12.score_report(sid, gold_text, report)
            row.update(scope=m11["scope"], v11=m11["checks"], v12=m12["checks"])
        except (SystemExit, Exception) as why:  # gold card the scorers stop on (no Scope / valued-as-of line): operations only, from the Operations items
            row.update(scope="in" if ops else "out", ops_only=str(why)[:100], v11={"operations": "hit" if ops and v11.ops_items_hit(ops, items) else "miss"},
                       v12={"operations": "hit" if ops and v12.ops_items_hit(ops, items) else "miss"})
        if "call_failed" in row["v11"].values() or "call_failed" in row["v12"].values():
            row["no_saved_reply"] = True  # the cache copy holds no reply for this file: not re-scorable, excluded from every table
        elif row["scope"] == "in":
            row["ops_answer"], row["gold_items"] = ops, items
            row["cooking_v11"], row["cooking_v12"] = cooking(v11, ops or "", items), cooking(v12, ops or "", items)
        rows.append(row)
Path(sys.argv[2]).write_text(json.dumps(rows, indent=1))
print(f"{len(rows)} ids, {sum(1 for r in rows if r.get('error'))} not re-scorable, calls made: {len([u for u in llm_extract.USAGE if not u.get('cached')])}")
