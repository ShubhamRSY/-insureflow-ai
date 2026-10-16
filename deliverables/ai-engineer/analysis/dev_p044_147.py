"""D-091 item 2: run the pipeline on the dev files SUB-147..152 (P-044 accept and reject cases) and compare with the gold written first.
Development data, not a hold-out. process_submission only: no drafts, outboxes or saved runs are written.

Uncached: set LLM_CACHE_DIR to a new empty folder. Paced by LLM_PACE_SECONDS through regression_dev.score_retry (failed calls retried).
Run: LLM_CACHE_DIR=<empty dir> .venv/bin/python deliverables/ai-engineer/analysis/dev_p044_147.py
"""
import json
import os
import re
import subprocess
import sys
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "underwriting_pipeline" / "ai"))
import llm_extract  # noqa: E402
import prepare  # noqa: E402
import regression_dev  # noqa: E402

IDS = [f"SUB-{n}" for n in range(147, 153)]
GOLD = ROOT / "deliverables" / "senior-underwriter" / "gold-set"
OUT = ROOT / "deliverables" / "ai-engineer" / "evals" / f"dev-SUB-147-152-{os.environ.get('DEV_TAG') or 'D-091'}"  # D-092: a tagged re-run never overwrites D-091


def gold(sid: str) -> dict:
    text = (GOLD / f"{sid}.md").read_text()
    line = lambda key: (re.search(rf"^- {key}: (.*)$", text, re.M) or [None, ""])[1].strip()
    return {"status": line("Status"), "loss_run": line("Expected loss run"), "pipeline_status": line("Expected pipeline status")}


def one(sid: str) -> dict:
    report = prepare.process_submission(prepare.INBOX_DIR / sid)
    row = {r["field_id"]: r for r in report["fields"]}["loss_run_valued_through"]
    flagged = [r["field_id"] for r in report["fields"] if r.get("value") and r.get("needs_review")]
    g = gold(sid)
    accepted = bool(row.get("value")) and not row.get("needs_review")
    want_accept = bool(re.match(r"20\d\d-\d\d-\d\d", g["loss_run"]))
    return {"submission": sid, "error": report.get("error"), "status": report.get("status"),
            "loss_run": {"value": row.get("value"), "accepted": accepted, "needs_review": bool(row.get("needs_review")), "reason": row.get("reason"), "source": row.get("source")},
            "other_review": [f for f in flagged if f != "loss_run_valued_through"], "missing": report.get("missing"),
            "gold": g, "loss_run_as_gold": accepted == want_accept and (not accepted or g["loss_run"].startswith(row.get("value") or "-")),
            "status_as_gold": report.get("status") == g["pipeline_status"],
            "false_complete": report.get("status") == "complete" and not g["status"].lower().startswith("complete")}


def main() -> None:
    llm_extract.provider_guard(calling=False)
    rows = []
    for sid in IDS:
        out = regression_dev.score_retry(type("M", (), {"score_one": staticmethod(lambda s: {**one(s), "checks": {}})}), sid)
        rows.append({k: v for k, v in out.items() if k not in ("checks", "metrics", "attempts")} | {"attempts": out["attempts"]})
    env = {"commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
           "model": llm_extract.endpoint_settings()["model"], "python": sys.executable,
           "libraries": {p: metadata.version(p) for p in ("pdfplumber", "openpyxl", "pytesseract", "pdf2image", "pillow")},
           "pace_seconds": regression_dev.PACE, "tokens": llm_extract.budget()["this_run"], "failed_attempts": llm_extract.failure_counts()}
    summary = {"plain_complete": [r["submission"] for r in rows if r["status"] == "complete"], "false_completes": [r["submission"] for r in rows if r["false_complete"]],
               "loss_run_as_gold": sum(r["loss_run_as_gold"] for r in rows), "status_as_gold": sum(r["status_as_gold"] for r in rows), "files": len(rows)}
    OUT.with_suffix(".json").write_text(json.dumps({"env": env, "summary": summary, "rows": rows}, indent=2, ensure_ascii=False) + "\n")
    lines = [f"# DEVELOPMENT CHECK — P-044/P-045 accept/reject cases SUB-147 to SUB-152 ({OUT.name}), not a hold-out", "",
             f"- Commit {env['commit']}, model {env['model']}, paced {env['pace_seconds']} s, python {env['python']}, {json.dumps(env['libraries'])}.",
             f"- Model calls: {json.dumps(env['tokens'])}; failed attempts: {json.dumps(env['failed_attempts'])}.",
             f"- Plain \"complete\": {', '.join(summary['plain_complete']) or 'none'}. False completes: **{len(summary['false_completes'])}** ({', '.join(summary['false_completes']) or 'none'}).",
             f"- Loss run as gold: {summary['loss_run_as_gold']} of {summary['files']}. Pipeline status as gold: {summary['status_as_gold']} of {summary['files']}.", "",
             "| File | Loss run | Reason | Status | Gold loss run | Gold pipeline status | Other values to review |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        lr = r["loss_run"]
        what = r["error"] and f"call failed: {r['error']}" or (f"accepted {lr['value']}" if lr["accepted"] else ("review " + (lr["value"] or "(empty)") if lr["value"] else "missing"))
        lines.append(f"| {r['submission']} | {what} | {lr['reason'] or '—'} | {r['status']} | {r['gold']['loss_run']} | {r['gold']['pipeline_status']} | {', '.join(r['other_review']) or 'none'} |")
    OUT.with_suffix(".md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
