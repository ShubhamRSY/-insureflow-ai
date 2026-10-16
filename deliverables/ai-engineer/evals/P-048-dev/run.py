"""D-095 dev re-check of P-048 on SUB-127-146 (development data). Not a hold-out. Cache only: LLM_CACHE_DIR points at a temp copy (D-069).

Runs the pipeline's own retries (RUN-RULES.md) through regression_dev --holdout eval_holdout_v2, saves each file's report,
then reads out operations, silent errors and routes (workbench.match) against gold. Synthetic. Not a production approval.
Run: HOLDOUT_IDS=127-146 HOLDOUT_OUT=deliverables/ai-engineer/evals/P-048-dev/SUB-127-146-dev-v2 LLM_CACHE_DIR=<temp copy> .venv/bin/python deliverables/ai-engineer/evals/P-048-dev/run.py
     add --readout to read saved reports only (no model call).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "underwriting_pipeline" / "ai"), str(ROOT / "underwriting_pipeline" / "app")]
import prepare  # noqa: E402
import regression_dev  # noqa: E402
import workbench  # noqa: E402
import eval_holdout_v2  # noqa: E402

IDS = [f"SUB-{n:03d}" for n in range(127, 147)]
GOLD = ROOT / "deliverables/senior-underwriter/gold-set"


def gold_of(sid: str) -> dict:
    return {k.strip().lower(): v.strip() for k, v in (l[2:].split(":", 1) for l in (GOLD / f"{sid}.md").read_text().splitlines() if l.startswith("- ") and ":" in l)}


def run() -> None:
    (HERE / "reports-cache").mkdir(exist_ok=True)
    real = prepare.process_submission

    def saving(folder, *a, **k):
        report = real(folder, *a, **k)
        (HERE / "reports-cache" / f"{Path(folder).name}.json").write_text(json.dumps(report, indent=2, default=str))
        return report

    prepare.process_submission = saving
    regression_dev.holdout("eval_holdout_v2")


def readout() -> None:
    scores = {r["submission"]: r for r in json.loads((HERE / "SUB-127-146-dev-v2-cache-rescore.json").read_text())["submissions"]}
    rows, right = [], 0
    for sid in IDS:
        rep, g = json.loads((HERE / "reports-cache" / f"{sid}.json").read_text()), gold_of(sid)
        m = workbench.match(rep) if not rep.get("error") else {"route": "call_failed", "note": rep["error"]}
        m = {**m, "route": eval_holdout_v2.route_used(rep), "held": m["route"] == "hold"}  # P-048 (c): the provisional route of a held file
        lr = next(f for f in rep["fields"] if f["field_id"] == "loss_run_valued_through")
        want = g.get("expected carrier route", "?").split()[0].strip(".,;")
        right += m["route"] == want
        ops = next(f for f in rep["fields"] if f["field_id"] == "operations")
        checks = scores[sid]["checks"]
        silent = [k for k, v in checks.items() if v == "miss" and not next((f for f in rep["fields"] if f["field_id"] == regression_dev.CHECK_FIELD.get(k, k)), {}).get("needs_review", True)]
        rows.append({"sid": sid, "status": rep.get("status"), "ops_mark": checks.get("operations"), "ops": ops["value"], "ops_review": ops.get("needs_review"),
                     "ops_reason": ops.get("reason"), "gold_ops": g.get("operations"), "silent": silent, "route": m["route"], "note": m.get("note"),
                     "gold_route": want, "held": m.get("held"), "loss_mark": checks.get("loss_runs"), "loss_value": lr["value"], "loss_reason": lr.get("reason"), "gold_loss": g.get("loss runs"), "retries": [r["kind"] for r in rep.get("retries") or []]})
    (HERE / "readout.json").write_text(json.dumps(rows, indent=2))
    for r in rows:
        print(r["sid"], "| loss", r["loss_mark"], r["loss_value"], "|", r["loss_reason"] or "", "| held" if r["held"] else "")
        print(r["sid"], r["status"], "| ops", r["ops_mark"], "review" if r["ops_review"] else "plain", "|", r["ops_reason"] or "", "| silent", r["silent"] or "-",
              "| route", r["route"], "/ gold", r["gold_route"], "| retries", r["retries"] or "-")
    hits = sum(r["ops_mark"] in ("hit", "hit (needs review)") for r in rows)
    print("operations hits", hits, "/ 20; silent errors", sum(len(r["silent"]) for r in rows), "(operations", sum("operations" in r["silent"] for r in rows), ")")
    print("loss runs", {k: sum(r["loss_mark"] == k for r in rows) for k in ("hit", "hit (needs review)", "miss", "not_credited")}, "; false completes", sum(r["status"] == "complete" and not (gold_of(r["sid"]).get("status", "").lower().startswith("complete")) for r in rows))
    print("route", right, "/ 20; senior_referral", sum(r["route"] == "senior_referral" for r in rows), "of gold", sum(r["gold_route"] == "senior_referral" for r in rows),
          "; carrier_c", sum(r["route"] == "carrier_c" for r in rows), "of gold", sum(r["gold_route"] == "carrier_c" for r in rows))


if __name__ == "__main__":
    if "--readout" not in sys.argv:
        run()
    readout()
