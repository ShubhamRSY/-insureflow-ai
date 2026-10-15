"""Development check on SUB-087..106 (development data since D-082), not a hold-out score. Scored by the frozen eval_holdout_087.py into
dev file names; its published output paths are never written. D-083 item 3; D-084 adds the two rates, the model and timing.

Uncached: set LLM_CACHE_DIR to a new empty folder. Failed calls are retried by regression_dev.score_retry. DEV_TAG names the output
(dev-SUB-087-106-<DEV_TAG>.*). A daily token or request limit stops the run for that model (D-084), with the files done so far.

Run: LLM_CACHE_DIR=<empty dir> DEV_TAG=D-083 .venv/bin/python deliverables/ai-engineer/analysis/dev_rerun_087.py
"""
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("LLM_MAX_WAIT", "1800")
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "underwriting_pipeline" / "ai"))
import eval_holdout_087 as scorer  # noqa: E402
import llm_extract  # noqa: E402
import regression_dev  # noqa: E402
import sources  # noqa: E402

CACHED_ONLY = os.environ.get("DEV_CACHED_ONLY") == "1"  # score only files already in LLM_CACHE_DIR; no model call

TAG = os.environ.get("DEV_TAG") or "D-083"
EVALS = ROOT / "deliverables" / "ai-engineer" / "evals"
scorer.OUT_JSON, scorer.OUT_MD = EVALS / f"dev-SUB-087-106-{TAG}.json", EVALS / f"dev-SUB-087-106-{TAG}.md"
plain, seconds, stopped = scorer.score_one, {}, []


class DailyLimit(Exception):
    pass


def timed(sid: str) -> dict:
    not_run = {"submission": sid, "format": None, "error": "not run: daily limit hit", "call": "not run", "checks": {}, "extracted_named_insured": None}
    if stopped:
        return not_run
    if CACHED_ONLY and not (llm_extract.CACHE / "extractions" / f"{llm_extract.key_for(sources.read_folder(scorer.INBOX / sid))}.json").exists():
        stopped.append(sid)  # re-scoring a stopped run from its cache: the first file it never reached ends it
        return not_run
    start = time.monotonic()
    row = regression_dev.score_retry(scorer, sid, plain)
    seconds[sid] = round(time.monotonic() - start, 1)
    if any("per day" in str(item.get("detail")) for item in llm_extract.CALL_LOG):
        stopped.append(sid)  # D-084: the model hit its daily budget on this file (even if a wait let it finish); the rest are not run
    return {**row, "seconds": seconds[sid]}


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
scorer.OUT_JSON.write_text(json.dumps(data, indent=2) + "\n")
md = scorer.OUT_MD.read_text().replace("# Hold-out extraction score — SUB-087 through SUB-106",
                                       f"# DEVELOPMENT CHECK — SUB-087 through SUB-106 ({TAG}), not a hold-out score", 1)
md = md.replace("- Scored by @model-risk with this file unchanged after the gold answers were written.",
                "- Development data since D-082: the gold was seen while the code changed. Not a hold-out.", 1)
scorer.OUT_MD.write_text(md + f"\n- Run: {json.dumps(data['run'])}\n" + (f"- STOPPED: daily limit hit at {stopped[0]}; later files not run.\n" if stopped else ""))
print("run", json.dumps(data["run"]), flush=True)
