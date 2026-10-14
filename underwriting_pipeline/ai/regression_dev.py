"""Score current code on development sets SUB-017 through SUB-076.

Writes a new report only. Does not touch the official hold-out score files.

Run: python underwriting_pipeline/ai/regression_dev.py [OUT.json]            all 60, at milestones
     python underwriting_pipeline/ai/regression_dev.py --quick [OUT.json]    15 files, after each change
     python underwriting_pipeline/ai/regression_dev.py --holdout eval_holdout_077

Model results come from the extraction cache when the files, prompt, OCR settings, and model are unchanged,
so an interrupted run continues where it stopped.
"""

import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("LLM_MAX_WAIT", "1800")  # a batch score waits out a daily token limit; set before llm_extract loads
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import llm_extract  # noqa: E402
import prepare  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else (
    ROOT / "deliverables" / "ai-engineer" / "evals" / "regression-SUB-017-076.json"
)
BANDS = (
    ("017-026", "eval_holdout"),
    ("027-036", "eval_holdout_027"),
    ("037-046", "eval_holdout_037"),
    ("047-056", "eval_holdout_047"),
    ("057-066", "eval_holdout_057"),
    ("067-076", "eval_holdout_067"),
)

# P-007. Fifteen development files for the check after each change. The full 60 run only at milestones.
QUICK = (
    "SUB-027",  # text PDF
    "SUB-029",  # Excel, no loss runs
    "SUB-038",  # scanned page
    "SUB-042",  # text PDF plus email, premises conflict
    "SUB-044",  # Excel plus email, square-feet conflict
    "SUB-050",  # email body, no loss runs
    "SUB-051",  # Spanish
    "SUB-053",  # scanned page, no loss runs
    "SUB-056",  # carrier loss run and a no-known-loss letter
    "SUB-067",  # handwritten tilted scan
    "SUB-070",  # multiple locations in Excel
    "SUB-071",  # blank ACORD plus attachment
    "SUB-073",  # resubmission, sales conflict
    "SUB-074",  # handwritten Spanish scan
    "SUB-076",  # two loss-run dates
)


def scorer_for(sid: str):
    number = int(sid[4:])
    for band, module_name in BANDS:
        low, high = (int(part) for part in band.split("-"))
        if low <= number <= high:
            return __import__(module_name)
    raise ValueError(sid)


def quick(out: Path) -> None:
    rows = []
    for sid in QUICK:
        row = score_retry(scorer_for(sid), sid)
        rows.append({"submission": sid, "checks": row["checks"], "name": row.get("extracted_named_insured"), "error": row.get("error"), "attempts": row["attempts"]})
    done = {"bands": [{"band": "quick-15", "counted": tally(rows), "rows": rows}], "failed_attempts": report_failures()}
    out.write_text(json.dumps(done, indent=2) + "\n")
    print("band quick-15", done["bands"][0]["counted"], flush=True)
    print(out)


def tally(rows: list[dict]) -> dict:
    counted: dict[str, dict[str, int]] = {}
    for row in rows:
        for field, mark in row["checks"].items():
            bucket = counted.setdefault(field, {})
            label = "hit" if mark is True else "miss" if mark is False else str(mark)
            bucket[label] = bucket.get(label, 0) + 1
    return counted


# P-025 (D-067): check name -> stored field id. A hit on a field stored with the low-confidence scan reason is "hit (needs review)".
CHECK_FIELD = {"sales": "sales_or_payroll", "tiv": "tiv_building", "loss_runs": "loss_run_valued_through"}
NEEDS_REVIEW_HIT = "hit (needs review)"


def split_review_hits(checks: dict, report: dict | None) -> dict:
    """Computed here; the frozen scorers and published score files are not touched. status counts as such when any stored row is a low-confidence scan read."""
    if not report:
        return checks
    low = {r["field_id"] for r in report.get("fields") or [] if r.get("value") and r.get("reason") == llm_extract.REASON_LOW_SCAN}
    return {k: (NEEDS_REVIEW_HIT if v == "hit" and (bool(low) if k == "status" else CHECK_FIELD.get(k, k) in low) else v) for k, v in checks.items()}


def score_retry(module, sid: str, score=None) -> dict:
    """A failed model call is not a score of the code: try it again, and keep the error if it never succeeds."""
    score = score or module.score_one
    seen = []
    real = prepare.process_submission
    prepare.process_submission = lambda *a, **k: seen.append(real(*a, **k)) or seen[-1]  # the scorer calls prepare.process_submission; keep its report
    try:
        for attempt in range(1, 4):
            row = score(sid)
            if not row.get("error"):
                break
            time.sleep(60)
    finally:
        prepare.process_submission = real
    row = {**row, "checks": split_review_hits(row["checks"], seen[-1] if seen else None)}
    print(time.strftime("%H:%M"), sid, row.get("error") or "ok", "attempts", attempt, flush=True)
    return {**row, "attempts": attempt}


def holdout(module_name: str) -> None:
    """Run one hold-out scorer's own report, with the same retry. python regression_dev.py --holdout eval_holdout_077"""
    module = __import__(module_name)
    plain = module.score_one
    module.score_one = lambda sid: score_retry(module, sid, plain)
    module.main()
    report_failures()


def report_failures() -> dict:
    import llm_extract

    kinds = llm_extract.failure_counts()  # D-028: 429, timeout, other, and reply_not_usable, each shown even at 0
    print("failed attempts", kinds, {i["kind"]: i["detail"] for i in llm_extract.CALL_LOG}, flush=True)
    print("tokens", json.dumps(llm_extract.budget()), flush=True)
    run = llm_extract.budget()["run"]  # P-014 (T2): the run id, and this run's totals rebuilt from the token log alone
    return {"run": run, "run_totals": llm_extract.run_totals().get(run), "counts": kinds, "samples": {i["kind"]: i["detail"] for i in llm_extract.CALL_LOG}, "tokens": llm_extract.budget()}


def main() -> None:
    done = {"bands": []}
    if OUT.exists():
        done = json.loads(OUT.read_text())
    finished = {item["band"] for item in done["bands"]}
    for band, module_name in BANDS:
        if band in finished:
            print("skip", band, flush=True)
            continue
        module = __import__(module_name)
        rows = []
        for sid in module.IDS:
            row = score_retry(module, sid)
            rows.append({"submission": sid, "checks": row["checks"], "name": row.get("extracted_named_insured"), "error": row.get("error"), "attempts": row["attempts"]})
        done["bands"].append({"band": band, "counted": tally(rows), "rows": rows})
        OUT.write_text(json.dumps(done, indent=2) + "\n")
        print("band", band, done["bands"][-1]["counted"], flush=True)
    done["failed_attempts"] = report_failures()
    OUT.write_text(json.dumps(done, indent=2) + "\n")
    print(OUT)


if __name__ == "__main__":
    import llm_extract

    llm_extract.provider_guard(calling=False)  # P-008: print the host and the model. A refused host stops at its first model call, inside llm_extract
    if sys.argv[1:2] == ["--holdout"]:
        holdout(sys.argv[2])
    elif sys.argv[1:2] == ["--quick"]:
        quick(Path(sys.argv[2]) if len(sys.argv) > 2 else OUT.with_name("regression-quick-15.json"))
    else:
        main()
