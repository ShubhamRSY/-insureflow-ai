"""Development check on SUB-107..126 (development data since D-088), not a hold-out score. Scored by the frozen eval_holdout_107.py into
dev file names; its published output paths are never written. D-088 item 4, a copy of dev_rerun_087.py with the ids and names changed.

Uncached: set LLM_CACHE_DIR to a new empty folder. Failed calls are retried by regression_dev.score_retry. DEV_TAG names the output
(dev-SUB-107-126-<DEV_TAG>.*). A daily token or request limit stops the run for that model (D-084), with the files done so far.

Run: LLM_CACHE_DIR=<empty dir> DEV_TAG=D-083 .venv/bin/python deliverables/ai-engineer/analysis/dev_rerun_107.py
"""
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("LLM_MAX_WAIT", "1800")
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "underwriting_pipeline" / "ai"))
import eval_holdout_107 as scorer  # noqa: E402
import llm_extract  # noqa: E402
import prepare  # noqa: E402
import regression_dev  # noqa: E402
import sources  # noqa: E402

CACHED_ONLY = os.environ.get("DEV_CACHED_ONLY") == "1"
PACE = float(os.environ.get("DEV_PACE_SECONDS") or 0)  # D-085: at least this many seconds between file starts (Groq per-minute limits)
_last: list[float] = []  # score only files already in LLM_CACHE_DIR; no model call

TAG = os.environ.get("DEV_TAG") or "D-083"
EVALS = ROOT / "deliverables" / "ai-engineer" / "evals"
scorer.OUT_JSON, scorer.OUT_MD = EVALS / f"dev-SUB-107-126-{TAG}.json", EVALS / f"dev-SUB-107-126-{TAG}.md"
plain, seconds, stopped = scorer.score_one, {}, []
statuses: dict[str, str] = {}  # D-089 item 6: each file's own status, for status safety/automation beside the frozen scorer
_real_process = prepare.process_submission


def _keep_status(folder, *a, **k):
    report = _real_process(folder, *a, **k)
    statuses[Path(folder).name] = report.get("status")
    return report


prepare.process_submission = _keep_status


class DailyLimit(Exception):
    pass


def timed(sid: str) -> dict:
    not_run = {"submission": sid, "format": None, "error": "not run: daily limit hit", "call": "not run", "checks": {}, "extracted_named_insured": None}
    if stopped:
        return not_run
    if CACHED_ONLY and not (llm_extract.CACHE / "extractions" / f"{llm_extract.key_for(sources.read_folder(scorer.INBOX / sid))}.json").exists():
        stopped.append(sid)  # re-scoring a stopped run from its cache: the first file it never reached ends it
        return not_run
    if PACE and _last and time.monotonic() - _last[-1] < PACE:
        time.sleep(PACE - (time.monotonic() - _last[-1]))
    start = time.monotonic()
    _last.append(start)
    row = regression_dev.score_retry(scorer, sid, plain)
    seconds[sid] = round(time.monotonic() - start, 1)
    if any("per day" in str(item.get("detail")) for item in llm_extract.CALL_LOG):
        stopped.append(sid)  # D-084: the model hit its daily budget on this file (even if a wait let it finish); the rest are not run
    return {**row, "seconds": seconds[sid], "system_status": statuses.get(sid)}


scorer.score_one = timed
llm_extract.provider_guard(calling=False)
scorer.main()
regression_dev.add_metrics(scorer)
failures = regression_dev.report_failures()
data = json.loads(scorer.OUT_JSON.read_text())
done = [s for s in seconds if s not in stopped]
data["run"] = {"model": llm_extract.endpoint_settings()["model"], "stopped_at": stopped[0] if stopped else None,
               "files_run": len(seconds), "seconds_per_file": round(sum(seconds[s] for s in done) / len(done), 1) if done else None,
               "tokens": failures["run_totals"], "failed_attempts": failures["counts"]}
# D-089 item 6 (B-325 rule): a plain "complete" on a gold-incomplete file is a false complete (critical); a gold-complete file shown as plain
# "complete" is automated; "complete — review pending" is safe but not automated. Failed calls are left out of both.
gold_ok = {r["submission"]: scorer.parse_gold((scorer.GOLD / f"{r['submission']}.md").read_text())["status"].lower().startswith("complete") for r in data["submissions"]}
ran = [r for r in data["submissions"] if not r.get("error")]
false_c = [r["submission"] for r in ran if r.get("system_status") == "complete" and not gold_ok[r["submission"]]]
gold_c = [r for r in ran if gold_ok[r["submission"]]]
data["status_split"] = {"false_complete": len(false_c), "false_complete_ids": false_c, "gold_complete": len(gold_c),
                        "automated": sum(r.get("system_status") == "complete" for r in gold_c), "call_failed": len(data["submissions"]) - len(ran),
                        "statuses": {r["submission"]: r.get("system_status") for r in data["submissions"]}}
scorer.OUT_JSON.write_text(json.dumps(data, indent=2) + "\n")
split = data["status_split"]
md = scorer.OUT_MD.read_text().replace("# Hold-out extraction score — SUB-107 through SUB-126",
                                       f"# DEVELOPMENT CHECK — SUB-107 through SUB-126 ({TAG}), not a hold-out score", 1)
md = md.replace("- Scored by @model-risk with this file unchanged after the gold answers were written.",
                "- Development data since D-088: the gold was seen while the code changed. Not a hold-out.", 1)
md += ("\n## Status safety and status automation (D-089 item 6, B-325 rule; computed here, the frozen scorer is unchanged)\n\n"
       f"- False completes: **{split['false_complete']}** ({', '.join(split['false_complete_ids']) or 'none'}). Critical: must be 0.\n"
       f"- Status automation: {split['automated']} of {split['gold_complete']} gold-complete files shown as plain \"complete\".\n"
       f"- Statuses: {json.dumps(split['statuses'], ensure_ascii=False)}\n")
scorer.OUT_MD.write_text(md + f"\n- Run: {json.dumps(data['run'])}\n" + (f"- STOPPED: daily limit hit at {stopped[0]}; later files not run.\n" if stopped else ""))
print("run", json.dumps(data["run"]), flush=True)
