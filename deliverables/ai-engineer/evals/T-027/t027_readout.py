"""Read-only readout after the T-027 run: route vs gold, loss-run accept/review per document, tokens per file. No model call."""
import json
import re
import sys
from pathlib import Path

ROOT = Path("/Users/disastershubz/INSURANCE FLOW AI/-insureflow-ai-1")
HERE = Path(__file__).resolve().parent / "t027"
sys.path[:0] = [str(ROOT / "underwriting_pipeline" / "ai"), str(ROOT / "underwriting_pipeline" / "app")]
import prepare  # noqa: E402
import sources  # noqa: E402
import workbench  # noqa: E402

gold_of = lambda sid: {k.strip().lower(): v.strip() for k, v in (l[2:].split(":", 1) for l in (ROOT / "deliverables/senior-underwriter/gold-set" / f"{sid}.md").read_text().splitlines() if l.startswith("- ") and ":" in l)}
rows, right = [], 0
for n in range(127, 147):
    sid = f"SUB-{n:03d}"
    saved = json.loads((HERE / f"{sid}.json").read_text())
    rep, g = saved["report"], gold_of(sid)
    m = workbench.match(rep) if rep and not rep.get("error") else {"route": "call_failed", "note": rep.get("error") if rep else "no report"}
    want = g.get("expected carrier route", "?").split()[0].strip(".,;")
    right += m["route"] == want
    docs = sources.read_folder(ROOT / "simulation/inbox" / sid)
    texts = {d["name"]: d["text"] for d in docs}
    scans = {d["name"]: d["ocr_words"] for d in docs if d.get("ocr_words")}
    sheet = lambda x: x in scans or x.lower().endswith((".xlsx", ".xls", ".csv"))
    per_doc = {}
    for name, t in texts.items():
        chk = prepare.carrier_run_check(t)
        why = prepare._run_doc_reason(name, t, chk, prepare.loss_run_kind(t), sheet(name))
        if why or chk[0] == "accepted":
            per_doc[name] = "accept" if not why else "review: " + why
    lr = next((f for f in (rep or {}).get("fields") or [] if f["field_id"] == "loss_run_valued_through"), {})
    rows.append({"sid": sid, "status": rep.get("status") if rep else None, "gold_status": g.get("expected pipeline status"),
                 "route": m["route"], "route_note": m.get("note"), "gold_route": want, "loss_run_field": {k: lr.get(k) for k in ("value", "needs_review", "reason")},
                 "gold_loss_run": g.get("expected loss run"), "per_doc": per_doc, "posts": saved["posts"]})
(HERE / "readout.json").write_text(json.dumps(rows, indent=2))
for r in rows:
    print(r["sid"], "| status", r["status"], "/ gold", r["gold_status"], "| route", r["route"], "/ gold", r["gold_route"], "| lr", r["loss_run_field"]["value"], "/ gold", r["gold_loss_run"])
    for d, v in r["per_doc"].items():
        print("     ", d, "->", v)
print("route accuracy", right, "/ 20")
log = [json.loads(l) for l in (ROOT / "underwriting_pipeline/cache/token_log.jsonl").read_text().splitlines() if l.strip()]
run = log[-1].get("run")
calls = [r for r in log if r.get("run") == run and not r.get("event")]
fails = [r for r in log if r.get("run") == run and r.get("event") and r["event"] != "cache_hit"]
tok = [r.get("total_tokens", 0) for r in calls]
pin, pout = sum(r.get("prompt_tokens", 0) for r in calls), sum(r.get("completion_tokens", 0) for r in calls)
est = (pin * 0.30 + pout * 2.50) / 1e6 / max(len(calls), 1)
print("prompt", pin, "completion", pout, "est $/file at 8.3 list prices ($0.30 in / $2.50 out per M):", round(est, 5))
print("run", run, "calls", len(calls), "failed attempts", [(r["event"], r.get("detail", "")[:80]) for r in fails])
print("tokens total", sum(tok), "mean per call", round(sum(tok) / max(len(tok), 1)), "max", max(tok or [0]))
