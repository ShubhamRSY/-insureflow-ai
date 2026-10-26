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
WRITE = "--write" in sys.argv  # D-096 item 4: score files are written only with --write; without it the run is read-only
_SCRATCH: list[Path] = []


def kept(path: Path) -> Path:
    """D-096 item 4: the path itself with --write; otherwise the same name in a temp folder that is not kept."""
    if WRITE:
        return path
    if not _SCRATCH:
        import tempfile

        _SCRATCH.append(Path(tempfile.mkdtemp(prefix="read-only-score-")))
        print(f"read-only (no --write): score files go to {_SCRATCH[0]}, nothing in the repo is written", flush=True)
    return _SCRATCH[0] / path.name


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
        rows.append({"submission": sid, "checks": row["checks"], "name": row.get("extracted_named_insured"), "error": row.get("error"), "attempts": row["attempts"], "retries": row["retries"], "metrics": row["metrics"]})
    done = {"bands": [{"band": "quick-15", "counted": tally(rows), "metrics": summarize(rows), "rows": rows}], "failed_attempts": report_failures()}
    out.write_text(json.dumps(done, indent=2) + "\n")
    print("band quick-15", done["bands"][0]["counted"], flush=True)
    print("metrics", json.dumps(done["bands"][0]["metrics"]["overall"]), flush=True)
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
CHECK_FIELD = {"sales": "sales_or_payroll", "tiv": "tiv_building", "loss_runs": "loss_run_valued_through", "premises": "premises_address"}
STATUS_LIKE = ("status", "conflict")  # depend on every stored row, so any low-confidence row flags them (D-068 H1)
NEEDS_REVIEW_HIT = "hit (needs review)"


def split_review_hits(checks: dict, report: dict | None) -> dict:
    """Computed here; the frozen scorers and published score files are not touched. status and conflict count as such when any stored row is a low-confidence scan read."""
    if not report:
        return checks
    low = {r["field_id"] for r in report.get("fields") or [] if r.get("value") and r.get("reason") == llm_extract.REASON_LOW_SCAN}
    return {k: (NEEDS_REVIEW_HIT if v == "hit" and (bool(low) if k in STATUS_LIKE else CHECK_FIELD.get(k, k) in low) else v) for k, v in checks.items()}


# D-084: two rates on every score report, from each file's own stored report. No hit/miss rule changes.
VALUE_CHECKS = {"named_insured": "named_insured", "premises": "premises_address", "effective_date": "effective_date", "operations": "operations",
                "sales": "sales_or_payroll", "tiv": "tiv_building", "construction": "construction", "year_built": "year_built",
                "loss_runs": "loss_run_valued_through"}


def value_metrics(checks: dict, report: dict | None) -> dict:
    """Per extracted field: correct (hit, with or without review), flagged (needs review, in an open conflict, or empty so it shows as
    missing), silent (a value is shown, it is wrong, and nothing flags it) and automated (correct and not flagged).
    A failed call is not scored; a file with no report gives nothing."""
    if not report or report.get("error"):
        return {}
    rows = {row["field_id"]: row for row in report.get("fields") or []}
    open_ = {c.get("field") for c in report.get("conflicts") or [] if c.get("resolution") != "resolved"}
    out = {}
    for check, field_id in VALUE_CHECKS.items():
        mark = checks.get(check)
        if mark in (None, "call_failed"):
            continue
        row = rows.get(field_id) or {}
        shown = bool(row.get("value"))
        flagged = bool(row.get("needs_review")) or field_id in open_ or not shown
        correct = mark in ("hit", NEEDS_REVIEW_HIT)
        out[check] = {"correct": correct, "flagged": flagged, "silent": not correct and shown and not flagged, "automated": correct and not flagged}
    return out


def summarize(rows: list[dict]) -> dict:
    """Silent error rate and automation rate per field and overall, over the scored field values (failed calls left out)."""
    per: dict[str, dict[str, int]] = {}
    for row in rows:
        for check, m in (row.get("metrics") or {}).items():
            bucket = per.setdefault(check, {"scored": 0, "silent": 0, "automated": 0})
            bucket["scored"] += 1
            bucket["silent"] += m["silent"]
            bucket["automated"] += m["automated"]
    total = {k: sum(b[k] for b in per.values()) for k in ("scored", "silent", "automated")}
    rate = lambda b: {**b, "silent_error_rate": round(b["silent"] / b["scored"], 3) if b["scored"] else None,
                      "automation_rate": round(b["automated"] / b["scored"], 3) if b["scored"] else None}
    failed = sum(1 for row in rows if "call_failed" in (row.get("checks") or {}).values())
    return {"fields": {k: rate(v) for k, v in per.items()}, "overall": rate(total), "failed_call_files": failed,
            "definitions": "silent error: a value is shown, it is wrong, and it is not flagged needs review or in an open conflict; "
                           "automation: the value is correct and not flagged. An empty field counts as flagged (it shows as missing). "
                           "Rates are over scored field values; files whose call failed are left out and counted apart (D-084)."}


def metrics_lines(summary: dict) -> list[str]:
    lines = ["", "## Silent error rate and automation rate (D-084)", "", summary["definitions"], "",
             f"Files with a failed call, not in the rates: {summary.get('failed_call_files', 0)}.", "",
             "| Field | Scored | Silent errors | Silent error rate | Automated | Automation rate |", "|---|---|---|---|---|---|"]
    for name, b in [*summary["fields"].items(), ("overall", summary["overall"])]:
        lines.append(f"| {name} | {b['scored']} | {b['silent']} | {b['silent_error_rate']} | {b['automated']} | {b['automation_rate']} |")
    return lines


def add_metrics(module) -> dict:
    """Write the two rates into a hold-out-style score's own JSON and memo after module.main() has written them."""
    data = json.loads(module.OUT_JSON.read_text())
    data["metrics"] = summarize(data["submissions"])
    module.OUT_JSON.write_text(json.dumps(data, indent=2) + "\n")
    module.OUT_MD.write_text(module.OUT_MD.read_text().rstrip("\n") + "\n" + "\n".join(metrics_lines(data["metrics"])) + "\n")
    print("metrics", json.dumps(data["metrics"]["overall"]), flush=True)
    return data["metrics"]


def _self_check() -> None:
    row = {"sales": "hit", "conflict": "hit", "premises": "hit", "status": "hit", "tiv": "miss"}
    flag = lambda fid: {"fields": [{"field_id": fid, "value": "x", "reason": llm_extract.REASON_LOW_SCAN}]}
    low = split_review_hits(row, flag("premises_address"))
    assert (low["conflict"], low["premises"], low["status"], low["sales"], low["tiv"]) == (NEEDS_REVIEW_HIT, NEEDS_REVIEW_HIT, NEEDS_REVIEW_HIT, "hit", "miss"), low
    plain = split_review_hits(row, {"fields": [{"field_id": "premises_address", "value": "x", "reason": "other"}]})
    assert plain == row, plain
    # D-084: silent = shown, wrong, not flagged; automated = correct, not flagged; empty is flagged (it shows as missing)
    rep_ = {"fields": [{"field_id": "named_insured", "value": "X LLC"}, {"field_id": "premises_address", "value": "1 A St", "needs_review": True},
                       {"field_id": "sales_or_payroll", "value": None}, {"field_id": "tiv_building", "value": "5"}, {"field_id": "year_built", "value": "1990"}],
            "conflicts": [{"field": "tiv_building", "resolution": "unresolved"}]}
    m = value_metrics({"named_insured": "miss", "premises": "miss", "sales": "miss", "tiv": "miss", "year_built": "hit", "construction": "call_failed"}, rep_)
    assert [m[k]["silent"] for k in ("named_insured", "premises", "sales", "tiv")] == [True, False, False, False] and "construction" not in m
    assert m["year_built"]["automated"] and not m["premises"]["automated"]
    assert value_metrics({"named_insured": "hit"}, {**rep_, "error": "rate_limit_429"}) == {}
    s_ = summarize([{"metrics": m}])
    assert s_["overall"] == {"scored": 5, "silent": 1, "automated": 1, "silent_error_rate": 0.2, "automation_rate": 0.2}, s_["overall"]
    assert summarize([{"metrics": m}, {"checks": {"sales": "call_failed"}, "metrics": {}}])["failed_call_files"] == 1
    global PACE  # P-039: pacing waits between file starts, and only then
    PACE, slept, real_sleep = 55, [], time.sleep
    time.sleep = slept.append
    try:
        _started[:] = [time.monotonic() - 10]
        try:
            score_retry(type("M", (), {"score_one": staticmethod(lambda sid: {"checks": {}, "error": None})}), "SUB-1")
        finally:
            time.sleep = real_sleep
        assert len(slept) == 1 and 44 < slept[0] <= 45, slept
    finally:
        PACE, _started[:] = 0, []
    real = Path("deliverables/x.json")
    assert kept(real) == (real if WRITE else _SCRATCH[0] / "x.json") and (WRITE or not str(kept(real)).startswith(str(ROOT))), "D-096 item 4"
    print("regression_dev self-check ok")


PACE = float(os.environ.get("LLM_PACE_SECONDS") or 0)  # P-039 (D-087): seconds between file starts; 55 for qwen's 1,000 output tokens a minute
_started: list[float] = []


def score_retry(module, sid: str, score=None) -> dict:
    """A failed model call is not a score of the code: try it again, and keep the error if it never succeeds."""
    if PACE and _started and time.monotonic() - _started[-1] < PACE:
        time.sleep(PACE - (time.monotonic() - _started[-1]))
    _started.append(time.monotonic())
    score = score or module.score_one
    seen = []
    import llm_extract

    tried = len(llm_extract.ATTEMPTS)  # D-094 item 5: every failed attempt and retry of this file, across all attempts below
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
    row = {**row, "checks": split_review_hits(row["checks"], seen[-1] if seen else None),
           "metrics": value_metrics(row["checks"], seen[-1] if seen else None)}  # D-084
    retries = llm_extract.ATTEMPTS[tried:]
    print(time.strftime("%H:%M"), sid, row.get("error") or "ok", "attempts", attempt, "retries", [r["kind"] for r in retries], flush=True)
    return {**row, "attempts": attempt, "retries": retries}


def holdout(module_name: str) -> None:
    """Run one hold-out scorer's own report, with the same retry. python regression_dev.py --holdout eval_holdout_077"""
    module = __import__(module_name)
    for name in ("OUT_JSON", "OUT_MD", "_OUT"):  # D-096 item 4: frozen scorers stay unedited; the driver decides where they write
        if hasattr(module, name):
            setattr(module, name, kept(getattr(module, name)))
    plain = module.score_one
    module.score_one = lambda sid: score_retry(module, sid, plain)
    module.main()
    add_metrics(module)  # D-084
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
            rows.append({"submission": sid, "checks": row["checks"], "name": row.get("extracted_named_insured"), "error": row.get("error"), "attempts": row["attempts"], "retries": row["retries"], "metrics": row["metrics"]})
        done["bands"].append({"band": band, "counted": tally(rows), "metrics": summarize(rows), "rows": rows})
        OUT.write_text(json.dumps(done, indent=2) + "\n")
        print("band", band, done["bands"][-1]["counted"], flush=True)
    done["failed_attempts"] = report_failures()
    OUT.write_text(json.dumps(done, indent=2) + "\n")
    print(OUT)


if __name__ == "__main__":
    import llm_extract

    if sys.argv[1:2] == ["--self-check"]:
        _self_check()
        sys.exit(0)
    llm_extract.provider_guard(calling=False)  # P-008: print the host and the model. A refused host stops at its first model call, inside llm_extract
    if sys.argv[1:2] == ["--holdout"]:
        holdout(sys.argv[2])
    elif sys.argv[1:2] == ["--quick"]:
        quick(kept(Path(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] != "--write" else OUT.with_name("regression-quick-15.json")))
    else:
        OUT = kept(OUT)
        main()
