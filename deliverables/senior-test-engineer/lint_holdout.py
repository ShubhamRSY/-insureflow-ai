#!/usr/bin/env python3
"""T-106d: test-file lint, must pass before any hold-out gold is frozen (D-111).

Usage: .venv/bin/python deliverables/senior-test-engineer/lint_holdout.py PLAN.json [--run-date YYYY-MM-DD]
Env:   HOLDOUT_INBOX / HOLDOUT_GOLD override the folders (temp copies for self-checks, D-069).
Read-only: no pipeline run, no model call, writes nothing. Exit 1 on any failure, one plain line per file.

PLAN.json (written by hand from the mix .md, before gold exists):
  {"ids": "174-205", "in": 20, "out": 12,
   "per_criterion": {"1": 4, "2": 5, "3": 4, "4": 2},   # optional: out-of-scope files naming each criterion
   "two_criteria": 3, "criterion_4": 2,                 # optional counts
   "routes": {"carrier_a": 5, "senior_referral": 3}}    # optional: gold route counts over in-scope files
Only keys present are checked.

Scorer test (D-116 item 5, "test the test"), with --scorer NAME (default eval_holdout_v10, the scorer the set will be scored with once P-068 is approved):
  (a) a perfect answer built from each gold card is scored by the scorer itself (score_report, no pipeline run, no model call): no mark
      may be "miss" or "call_failed", and the set's route gate and P-055 gate must PASS with 0 false completes;
  (b) deliberately wrong answers, each must be caught: one per field on every in-scope file (named insured, premises, effective date,
      operations, sales, TIV, construction, year built, loss-run date, conflict, status, route -> that mark is "miss"), a leak on every
      out-of-scope file (answered as in scope, and manual intake with a value shown -> a leak, and the P-055 gate FAILS), and an unsafe
      route (carrier_a where gold says senior_referral or no_match -> the route gate counts it unsafe and FAILS).
  A gold line the scorer cannot read (e.g. no "Loss runs valued as of" line for a card that expects a date) is a FAIL. Freeze is blocked
  on any failure. The scorer's own readers are used where it has one (v9: conflict_none for a "none (…)" conflict, review_expected for
  "needs review" anywhere on the Expected loss run line), so the perfect answer follows the scorer it is tested against.
  The scorer's route is read from the answer (the test patches route_used); leaks_of runs as written.

Loss-run dates: in each loss-run file (loss-run*.{md,csv,txt}; PDF via pdftotext; JPG/scanned PDF via tesseract
when installed) every date on a "valued / as of / evaluated / run date / date:" line and every table-row date must be
before the run date. A loss run with no date the lint can read (unreadable scan, or no date) is a FAIL. Month-name dates (Nov 30, 2026) are read.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "underwriting_pipeline" / "ai"))
sys.path.insert(0, str(ROOT / "underwriting_pipeline"))
sys.path.insert(0, str(ROOT / "underwriting_pipeline" / "app"))
import eval_holdout_v6 as v6  # noqa: E402  # pyright: ignore[reportMissingImports] frozen; only its Scope/gold parsers are used

INBOX = Path(os.environ.get("HOLDOUT_INBOX") or v6.INBOX)
GOLD = Path(os.environ.get("HOLDOUT_GOLD") or v6.GOLD)
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
MON = "|".join(MONTHS)
NUM = re.compile(r"(?<![\w.])(\d{1,4})([-/.])(\d{1,2})\2(\d{1,4})(?![\w.]\d)")  # 2026-11-30, 2026/11/30, 11/30/26, 11.30.2026
DMY = re.compile(rf"(?<!\w)(\d{{1,2}})(?:st|nd|rd|th)?[-\s]+({MON})[a-z]*\.?,?[-\s]+(\d{{2,4}})(?!\d)", re.I)  # 30-Nov-2026, 30 Nov 2026
MDY = re.compile(rf"(?<![\w])({MON})[a-z]*\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{2,4}})(?!\d)", re.I)  # Nov 30, 2026 / Nov 30, 26
LOOSE = re.compile(rf"\d{{1,4}}[-/.]\d{{1,2}}[-/.]\d{{1,4}}|\b(?:{MON})[a-z]*\.?\s+\d{{1,2}}\b", re.I)  # anything date-like, to catch what the parsers refused
LABEL = re.compile(r"(?i)valued|as of|evaluated|run date|report date|\bdate\s*:")


def year4(y: int) -> int:
    return y + 2000 if y < 100 else y


def dates_in(line: str, run: date) -> tuple[list[date], list[str]]:
    """(dates read, plain problems). A date-like token that cannot be read, or a day/month order that changes the answer, is a problem."""
    out: list[date] = []
    bad: list[str] = []
    for m in NUM.finditer(line):
        a, b, c, tok = int(m[1]), int(m[3]), int(m[4]), m[0]
        try:
            if len(m[1]) == 4:  # year first: Y-M-D
                out.append(date(a, b, c))
            else:  # A/B/Y: month-first unless that is impossible; both readings must agree on before/after the run date
                reads = []
                for mo, d in ((a, b), (b, a)):
                    try:
                        reads.append(date(year4(c), mo, d))
                    except ValueError:
                        pass
                if not reads:
                    raise ValueError
                if len(reads) == 2 and reads[0] != reads[1] and (reads[0] < run) != (reads[1] < run):
                    bad.append(f"{tok!r} could be read day-first or month-first and the answer differs")
                else:
                    out.append(reads[0])
        except ValueError:
            bad.append(f"cannot read the date {tok!r}")
    for m in DMY.finditer(line):
        try:
            out.append(date(year4(int(m[3])), MONTHS.index(m[2].lower()) + 1, int(m[1])))
        except ValueError:
            bad.append(f"cannot read the date {m[0]!r}")
    for m in MDY.finditer(line):
        try:
            out.append(date(year4(int(m[3])), MONTHS.index(m[1].lower()) + 1, int(m[2])))
        except ValueError:
            bad.append(f"cannot read the date {m[0]!r}")
    if not bad:  # date-like text no parser took
        covered = " ".join(m[0] for p in (NUM, DMY, MDY) for m in p.finditer(line))
        for tok in LOOSE.findall(line):
            if tok not in covered:
                bad.append(f"cannot read the date-like text {tok!r}")
    return out, bad


def text_of(path: Path) -> str | None:
    """Text of a loss-run file, or None when it cannot be read here."""
    suf = path.suffix.lower()
    try:
        if suf in (".md", ".csv", ".txt"):
            return path.read_text(errors="replace")
        if suf == ".pdf" and shutil.which("pdftotext"):
            t = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True, timeout=60).stdout
            if t.strip():
                return t
        if suf in (".jpg", ".jpeg", ".png") and shutil.which("tesseract"):
            return subprocess.run(["tesseract", str(path), "-"], capture_output=True, text=True, timeout=120).stdout
        if suf == ".pdf" and shutil.which("tesseract") and shutil.which("pdftoppm"):  # image-only PDF
            tmp = Path(os.environ.get("TMPDIR") or "/tmp") / f"lint_{os.getpid()}"
            subprocess.run(["pdftoppm", "-r", "200", "-png", str(path), str(tmp)], timeout=120)
            pages = sorted(tmp.parent.glob(tmp.name + "*.png"))
            t = "\n".join(subprocess.run(["tesseract", str(p), "-"], capture_output=True, text=True, timeout=120).stdout for p in pages)
            for p in pages:
                p.unlink()
            return t
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def check_text(sid: str, name: str, text: str | None, run: date, declared: bool) -> tuple[list[str], list[str]]:
    """(fails, infos) for one loss-run file. declared = the plan says this submission's loss runs carry no valued date."""
    who = f"{sid}/{name}"
    if text is None:
        return [f"{who}: this scan or file could not be read here, so its dates cannot be checked (read it by eye and fix the file or the tool)"], []
    fails, valued, other = [], [], []
    for ln in text.splitlines():
        labeled = bool(LABEL.search(ln))
        if not (labeled or ln.lstrip().startswith("|")):
            continue
        ds, bad = dates_in(ln, run)
        fails += [f"{who}: {b} (line: {ln.strip()[:60]!r})" for b in bad]
        if labeled and not ds and not bad:
            fails.append(f"{who}: the line {ln.strip()[:60]!r} names a valued/as-of date but has none the lint can read")
        (valued if labeled else other).extend(ds)
    late = sorted({d for d in valued + other if d >= run})
    if late:
        fails.append(f"{who}: loss run dated {', '.join(map(str, late))}, not before the run date {run}")
    infos = []
    if not valued and not fails:
        if declared:
            infos.append(f"{who}: declared undated in the plan; no valued date found, as declared")
        else:
            fails.append(f"{who}: typed file with no valued/as-of date, and the plan does not declare it undated (undated_loss_runs)")
    elif valued and declared:
        fails.append(f"{who}: the plan declares this file undated but it has a valued date {valued[0]}")
    return fails, infos


def lint_dates(ids: list[str], run: date, declared: set[str]) -> tuple[list[str], list[str]]:
    fails, infos = [], []
    for sid in ids:
        files = sorted((INBOX / sid).glob("loss-run*")) if (INBOX / sid).is_dir() else []
        for f in files:
            fl, inf = check_text(sid, f.name, text_of(f), run, sid in declared)
            fails += fl
            infos += inf
    return fails, infos


def lint_gold_and_mix(ids: list[str], plan: dict) -> list[str]:
    fails, found, routes = [], {}, {}
    for sid in ids:
        g = GOLD / f"{sid}.md"
        try:
            text = g.read_text()
        except OSError:
            fails.append(f"{sid}: gold file not found")
            continue
        try:
            found[sid] = v6.gold_scope(text)
        except ValueError as why:
            fails.append(f"{sid}/gold: Scope line invalid: {why}")
            continue
        if not found[sid]["out"]:
            routes[sid] = v6.gold_route_of(v6.parse_gold(text).get("expected carrier route", "")) or "none"
    if fails:  # counts of a half-read set would mislead
        return fails
    t = v6.scope_totals(found)
    def chk(name: str, want, got) -> None:
        if want is not None and want != got:
            fails.append(f"mix: {name}: plan says {want}, files give {got}")
    chk("in-scope files", plan.get("in"), t["in"])
    chk("out-of-scope files", plan.get("out"), t["out"])
    for c, n in (plan.get("per_criterion") or {}).items():
        chk(f"files naming criterion {c}", n, t["per_criterion"].get(int(c)))
    chk("files with two or more criteria", plan.get("two_criteria"), len(t["two_criteria"]))
    chk("files naming criterion 4", plan.get("criterion_4"), len(t["criterion_4"]))
    if "routes" in plan:
        got = {r: sum(v == r for v in routes.values()) for r in set(routes.values()) | set(plan["routes"])}
        for r, n in got.items():
            chk(f"in-scope gold route {r}", plan["routes"].get(r, 0), n)
    return fails


PERFECT_MARKS = {"hit", "flagged", "not_credited"}  # not_credited = the scorer's own "null where gold says missing" (judge v1): not a wrong mark
WRONG = {  # field_id -> (check name, a wrong value)
    "named_insured": ("named_insured", "Zzyzx Holdings Wrong LLC"), "premises_address": ("premises", "1 Wrong Rd, Nowhere, TX 00000"),
    "effective_date": ("effective_date", "2031-07-04"), "operations": ("operations", "Unrelated widget assembly"),
    "sales_or_payroll": ("sales", "123457"), "tiv_building": ("tiv", "7654321"), "construction": ("construction", "Unobtainium"),
    "year_built": ("year_built", "1066"), "loss_run_valued_through": ("loss_runs", "2019-01-01"),
}

# P-068: near-miss negatives. A wrong answer that states the opposite or a neighbouring fact must still be
# caught, not waved through by the facts-not-wording reader. Each is (gold phrase to look for, wrong text to swap in).
# Applied to every in-scope card whose operations items hold the phrase; the operations mark must be "miss".
NEARMISS = [  # (present-phrase, wrong replacement) -- no alcohol vs beer and wine, hood vs no hood, count, cooking
    ("no alcohol", "beer and wine served"),
    ("beer and wine only", "full liquor bar"),
    ("no cooking", "full commercial kitchen with cooking"),
    ("no hood", "Type I hood installed"),
    ("no fryer", "two deep fryers"),
    ("no bar", "full bar"),
    ("96 seats", "60 seats"),
    ("24 seats", "40 seats"),
    ("18 seats", "34 seats"),
    ("14 units", "20 units"),
    ("no processing", "processing and packaging on site"),
    ("no manufacturing", "on-site manufacturing"),
]


def _empty(line: str) -> bool:
    low = (line or "").strip().lower()
    return low.startswith(("missing", "not in documents", "both", "none")) or not low


def perfect_value(report: dict, field_id: str) -> str | None:
    for r in report.get("fields", []):
        if r.get("field_id") == field_id:
            return r.get("value")
    return None


def perfect_report(scorer, sid: str, gold_text: str) -> dict:
    """The answer a perfect pipeline gives for this gold card, in the report shape score_report reads."""
    import prepare  # pyright: ignore[reportMissingImports]
    gold = scorer.parse_gold(gold_text)
    sc = scorer.gold_scope(gold_text)
    if sc["out"]:
        codes = {v: k for k, v in scorer.CODE_CRITERION.items()}
        found = {"version": "lint", "in_scope": False, "reasons": [{"code": codes[c], "text": scorer.CRITERIA[c]} for c in sc["criteria"]]}
        return prepare._manual_intake(INBOX / sid, [], found)
    conflict = gold.get("conflict", "")
    # v9 (B-437 F1): "none (…)" is no conflict. Before v9 only an exact "none" start counts, and that is what is being tested.
    has_conflict = not (scorer.conflict_none(conflict) if hasattr(scorer, "conflict_none") else conflict.strip().lower().startswith("none"))
    flagged_topics = {f for f, words in (("effective_date", "effective"), ("sales_or_payroll", "sales"), ("tiv_building", "tiv"), ("operations", "operations"),
                                         ("construction", "construction"), ("year_built", "year"), ("loss_run_valued_through", "loss")) if has_conflict and words in conflict.lower()}
    expected = (gold.get("expected loss run") or "").strip().lower()
    # v9 (B-437 F3): the scorer's own reader; v8 and older read the prefix only
    review = scorer.review_expected(expected) if hasattr(scorer, "review_expected") else expected.startswith(("needs review", "loss run found but no valued-as-of date"))
    # the truth comes from gold, never from the scorer's rule: the valued-as-of line (D-116); a card without it falls back to the old first-date reading
    date = re.search(r"20\d\d-\d\d-\d\d", gold.get("loss runs valued as of") or gold.get("loss runs", ""))
    values = {
        "named_insured": gold.get("named insured"), "premises_address": None if _empty(gold.get("premises", "")) else gold["premises"],
        "effective_date": None if _empty(gold.get("effective date", "")) else gold["effective date"],
        "operations": gold.get("operations items") or gold.get("operations"), "sales_or_payroll": None if _empty(gold.get("sales", "")) else gold["sales"],
        "tiv_building": None if _empty(gold.get("tiv", "")) else gold["tiv"], "construction": None if _empty(gold.get("construction", "")) else gold["construction"],
        "year_built": None if _empty(gold.get("year built", "")) else gold["year built"], "loss_run_valued_through": None if review or not date else date.group(0),
    }
    fields = [{"field_id": f, "value": None if f in flagged_topics else values[f], "needs_review": f in flagged_topics or (f == "loss_run_valued_through" and review)}
              for f in prepare.FIELDS]
    conflicts = [{"field": "lint", "text": line, "resolution": "open"} for line in (conflict if has_conflict else "", gold.get("premises", "") if gold.get("premises", "").lower().startswith("both") else "") if line]
    complete = gold.get("status", "").lower().startswith("complete")
    return {"fields": fields, "conflicts": conflicts, "complete": complete, "status": "complete" if complete else "incomplete", "error": None,
            "request": None, "scope": {"version": "lint", "in_scope": True, "reasons": []}, "_route": scorer.gold_route_of(gold.get("expected carrier route") or "")}


def lint_scorer(ids: list[str], scorer_name: str) -> list[str]:
    """D-116 item 5: (a) perfect answers score clean, (b) every deliberately wrong answer is caught. Read-only; no pipeline run."""
    import copy
    import importlib
    from typing import Any
    scorer: Any = importlib.import_module(scorer_name)
    fails: list[str] = []
    saved = scorer.GOLD, scorer.route_used
    scorer.GOLD, scorer.route_used = GOLD, lambda report: report.get("_route") or "hold"
    try:
        bad = scorer.gold_problems(ids) if hasattr(scorer, "gold_problems") else scorer.gold_scopes(ids)[1]
        fails += [f"{b.split(':')[0]}/gold: {scorer_name} cannot read it:{b.split(':', 1)[1]}" for b in bad]
        broken = {b.split(":")[0] for b in bad}

        def score(sid, text, report):
            try:
                if hasattr(scorer, "score_report"):
                    return scorer.score_report(sid, text, report)
                real = scorer.prepare.process_submission  # a frozen scorer (v7 and older): its own score_one, the pipeline call answered by the report
                scorer.prepare.process_submission = lambda folder: report
                try:
                    return scorer.score_one(sid)
                finally:
                    scorer.prepare.process_submission = real
            except (SystemExit, KeyError, ValueError) as why:  # a gold card the scorer cannot read is a failure, never a crash
                fails.append(f"{sid}/gold: {scorer_name} stopped: {why!r}")
                return None

        rows_in, rows_out = [], []
        for sid in (i for i in ids if i not in broken):
            text = (GOLD / sid).with_suffix(".md").read_text()
            perfect = perfect_report(scorer, sid, text)
            row = score(sid, text, perfect)
            if row is None:
                continue
            if row["scope"] == "out":
                rows_out.append(row)
                if row["leaks"] or not row["detected"]:
                    fails.append(f"{sid}/scorer: the perfect manual-intake answer is marked as a leak or missed ({', '.join(row['leaks']) or 'not detected'})")
                for label, change in (("answered as in scope", {"status": "incomplete", "request": "draft"}), ("manual intake with a value shown", {})):
                    wrong = copy.deepcopy(perfect) | change
                    wrong["fields"][0]["value"] = "Shown Value LLC"
                    got = score(sid, text, wrong)
                    if got is not None and not (got["leaks"] and scorer.p055_gate([got], [])["verdict"] == "FAIL"):
                        fails.append(f"{sid}/scorer: a leak ({label}) is not caught")
                continue
            rows_in.append(row)
            for check, mark in row["checks"].items():
                if mark not in PERFECT_MARKS:
                    fails.append(f"{sid}/scorer: the perfect answer is marked {mark} on {check} (gold line not scorable as written)")
            for field, (check, value) in WRONG.items():
                wrong = copy.deepcopy(perfect)
                for r in wrong["fields"]:
                    if r["field_id"] == field:
                        r["value"], r["needs_review"] = value, False
                got = score(sid, text, wrong)
                if got is not None and got["checks"].get(check) != "miss":
                    fails.append(f"{sid}/scorer: a wrong {check} ({value!r}) is not caught (marked {got['checks'].get(check)})")
            gold_ops = (perfect_value(perfect, "operations") or "")
            for phrase, wrong_ops in NEARMISS:  # P-068: a near-miss (facts not wording) is still a miss
                if phrase.lower() not in gold_ops.lower():
                    continue
                wrong = copy.deepcopy(perfect)
                for r in wrong["fields"]:
                    if r["field_id"] == "operations":
                        r["value"], r["needs_review"] = wrong_ops, False
                got = score(sid, text, wrong)
                if got is not None and got["checks"].get("operations") != "miss":
                    fails.append(f"{sid}/scorer: a near-miss operations ({phrase!r} -> {wrong_ops!r}) is not caught (marked {got['checks'].get('operations')})")
            for check, change in (("conflict", {"conflicts": [] if perfect["conflicts"] else [{"field": "x", "text": "sales: 1 vs 2", "resolution": "open"}]}),
                                  ("status", {"complete": not perfect["complete"], "status": "incomplete" if perfect["complete"] else "complete"}),
                                  ("route", {"_route": "carrier_b" if perfect["_route"] != "carrier_b" else "carrier_a"})):
                if check not in row["checks"]:
                    continue
                got = score(sid, text, copy.deepcopy(perfect) | change)
                if got is not None and got["checks"].get(check) != "miss":
                    fails.append(f"{sid}/scorer: a wrong {check} is not caught (marked {got['checks'].get(check)})")
        gate = scorer.route_gate(rows_in) if rows_in else {"verdict": "NOT EVALUABLE"}
        p055 = scorer.p055_gate(rows_out, rows_in)
        if gate["verdict"] != "PASS":
            fails.append(f"scorer: the perfect answers do not pass the route gate ({gate['verdict']})")
        if p055["verdict"] != "PASS":
            fails.append(f"scorer: the perfect answers do not pass the P-055 gate ({p055['verdict']})")
        if scorer.status_counts(rows_in)["false_complete"]:
            fails.append("scorer: the perfect answers show a false complete")
        unsafe = [r for r in rows_in if r.get("gold_route") in scorer.UNSAFE_GOLD]
        if not unsafe:
            fails.append("scorer: no in-scope gold file routes to senior_referral or no_match, so an unsafe route cannot be tested on this set")
        for r in unsafe:
            text = (GOLD / r["submission"]).with_suffix(".md").read_text()
            wrong = perfect_report(scorer, r["submission"], text) | {"_route": "carrier_a"}
            got = score(r["submission"], text, wrong)
            if got is not None and scorer.route_gate([got])["unsafe"] != 1:
                fails.append(f"{r['submission']}/scorer: an unsafe route (carrier_a, gold {r['gold_route']}) is not counted unsafe")
    finally:
        scorer.GOLD, scorer.route_used = saved
    return fails


def self_check() -> int:
    """Runnable cases for the date rules, the undated declaration, and a clean temp set (no real files touched)."""
    import tempfile
    run = date(2026, 10, 17)
    def ok(label: str, text: str | None, want_fail: bool, declared: bool = False, want_info: bool = False) -> bool:
        f, i = check_text("SUB-9", "loss-runs.md", text, run, declared)
        good = bool(f) == want_fail and bool(i) == want_info
        print(("ok   " if good else "BAD  ") + label)
        return good
    r = [
        ok("ISO before run date passes", "Valued as of: 2026-09-01", False),
        ok("month name before passes", "Valued as of: September 1, 2026", False),
        ok("Sept abbreviation before passes", "Valued: Sept 1, 2026", False),
        ok("month name after fails", "Valued as of: November 30, 2026", True),
        ok("Nov 30, 2026 after fails", "Valued as of: Nov 30, 2026", True),
        ok("30-Nov-2026 after fails", "Valued: 30-Nov-2026", True),
        ok("30-Aug-2026 before passes", "Valued: 30-Aug-2026", False),
        ok("YYYY/MM/DD after fails", "Valued: 2026/11/30", True),
        ok("MM.DD.YYYY after fails", "Valued: 11.30.2026", True),
        ok("two-digit year after fails", "Valued as of: Nov 30, 26", True),
        ok("two-digit year numeric after fails", "Valued: 11/30/26", True),
        ok("two-digit year before passes", "Valued: 9/1/26", False),
        ok("ambiguous 10/11/2026 (Oct 11 before, Nov 10 after) fails", "Valued: 10/11/2026", True),
        ok("ambiguous 02/03/2026 (both before) passes", "Valued: 02/03/2026", False),
        ok("impossible date 2026-13-45 fails", "Valued: 2026-13-45", True),
        ok("Nov 31, 2026 fails", "Valued: Nov 31, 2026", True),
        ok("valued line with no date fails even if a date is elsewhere", "Valued as of: sometime\n| 2025 | X | P | Fire | 2025-03-02 | $1 |", True),
        ok("typed file, no valued date, undeclared fails", "| 2025 | X | P | No losses | - | $0 |", True),
        ok("typed file, no valued date, declared passes with INFO", "| 2025 | X | P | No losses | - | $0 |", False, True, True),
        ok("declared undated but has a valued date fails", "Valued as of: 2026-09-01", True, True),
        ok("unreadable scan fails (own message)", None, True, True),
    ]
    f, _ = check_text("SUB-9", "x.jpg", None, run, False)
    r.append("could not be read" in f[0] and "no valued" not in f[0])
    print(("ok   " if r[-1] else "BAD  ") + "unreadable-scan message differs from typed-no-date message")
    global INBOX, GOLD
    saved = INBOX, GOLD
    with tempfile.TemporaryDirectory() as t:
        tp = Path(t)
        (tp / "inbox" / "SUB-901").mkdir(parents=True)
        (tp / "inbox" / "SUB-902").mkdir(parents=True)
        (tp / "gold").mkdir()
        (tp / "inbox" / "SUB-901" / "loss-runs.md").write_text("Valued as of: Sept 1, 2026\n| 2025 | X | P1 | Fire | Mar 2, 2025 | $1 |\n")
        (tp / "inbox" / "SUB-902" / "loss-runs.md").write_text("| 2025 | X | P | No losses | - | $0 |\n")
        (tp / "inbox" / "SUB-903").mkdir(parents=True)
        card = ("- Status: complete\n- Scope: in scope\n- Named insured: Example Roofing LLC\n- Premises: 100 Main St, Austin, TX 78701\n- Effective date: 2027-01-01\n"
                "- Operations: office lessor\n- Operations items: office building lessor\n- Sales: 742000\n- TIV: 2450000\n- Construction: Masonry\n- Year built: 2005\n"
                "- Loss runs: Carrier A format, 3 policy periods 2023-06-01 to 2026-06-01, valued as of 2026-08-15\n- Loss runs valued as of: 2026-08-15\n"
                "- Conflict: none\n- Expected loss run: Carrier A format recognised\n- Expected carrier route: carrier_a (R14)\n")
        (tp / "gold" / "SUB-901.md").write_text(card)
        (tp / "gold" / "SUB-902.md").write_text("- Scope: out of scope - criterion 1 (scanned). Reason.\n- Status: manual intake\n")
        (tp / "gold" / "SUB-903.md").write_text(card.replace("Status: complete", "Status: incomplete — hold: open conflict (sales)").replace("carrier_a (R14)", "senior_referral (R2)")
                                                 .replace("Conflict: none", "Conflict: sales: 742000 (application) vs 940000 (email)"))
        plan = tp / "plan.json"
        plan.write_text(json.dumps({"ids": "901-903", "in": 2, "out": 1, "per_criterion": {"1": 1}, "routes": {"carrier_a": 1, "senior_referral": 1}, "undated_loss_runs": ["SUB-902"]}))
        INBOX, GOLD = tp / "inbox", tp / "gold"
        import eval_holdout_v9 as v9  # noqa: E402  # pyright: ignore[reportMissingImports] used by the explicit --scorer cases below
        import eval_holdout_v10 as v10  # noqa: E402  # pyright: ignore[reportMissingImports] the default scorer the temp set is checked with
        tiny = lambda real: lambda out, rows: real(out, rows) | ({"verdict": "PASS"} if out and rows and not any(r["leaks"] or not r["detected"] for r in out) else {})  # one criterion only in this tiny set
        v9_p055_real, v10_p055_real = v9.p055_gate, v10.p055_gate
        v9.p055_gate, v10.p055_gate = tiny(v9_p055_real), tiny(v10_p055_real)
        try:
            r.append(main([str(plan), "--run-date", "2026-10-17"]) == 0)
            print(("ok   " if r[-1] else "BAD  ") + "clean temp set passes, scorer test included (perfect answers clean, every wrong answer caught)")
            real_mark = v9.loss_run_mark
            v9.loss_run_mark = lambda *a: "hit"  # a blind loss-run mark
            got = lint_scorer(["SUB-901", "SUB-902", "SUB-903"], "eval_holdout_v9")
            v9.loss_run_mark = real_mark
            r.append(any("wrong loss_runs" in f for f in got))
            print(("ok   " if r[-1] else "BAD  ") + "a scorer that cannot see a wrong loss-run date is caught")
            v7_like = card.replace("- Loss runs valued as of: 2026-08-15\n", "")  # the T-108 shape: no valued-as-of line
            (tp / "gold" / "SUB-901.md").write_text(v7_like)
            got = lint_scorer(["SUB-901", "SUB-902", "SUB-903"], "eval_holdout_v9")
            r.append(any(f.startswith("SUB-901/gold") and "valued as of" in f for f in got))
            print(("ok   " if r[-1] else "BAD  ") + "a gold card with no valued-as-of line fails (v9)")
            (tp / "gold" / "SUB-901.md").write_text(card)
            got = lint_scorer(["SUB-901", "SUB-902", "SUB-903"], "eval_holdout_v7")
            r.append(any(f.startswith("SUB-901/scorer: the perfect answer is marked miss on loss_runs") for f in got))
            print(("ok   " if r[-1] else "BAD  ") + "v7 on the same card: the perfect answer is a loss-run miss (B-435 found by the lint)")
            if not r[-1]:
                print("     got:", got)
            (tp / "gold" / "SUB-901.md").write_text(card)
            # B-437 F1-F3 (P-065): the same three gold shapes, v8 must fail them and v9 must score them clean
            f1_card = card.replace("- Conflict: none\n", "- Conflict: none (schedule matches application on TIV/sq ft/construction/year built)\n")
            f2_card = (card.replace("- Operations: office lessor", "- Operations: full-service restaurant")
                           .replace("- Operations items: office building lessor",
                                    "- Operations items: full-service restaurant; 48 seats; closes 11 p.m.; open until 2:00 a.m.; no dancing"))
            f3_card = (card.replace("- Loss runs valued as of: 2026-08-15\n", "")
                           .replace("- Loss runs: Carrier A format, 3 policy periods 2023-06-01 to 2026-06-01, valued as of 2026-08-15",
                                    "- Loss runs: Carrier A layout, 3 policy periods 2023-08-01 to 2026-08-01, no valued-as-of line (undated)")
                           .replace("- Expected loss run: Carrier A format recognised",
                                    "- Expected loss run: Carrier A layout but no valued-as-of date; needs review — ask for a dated carrier run"))
            for sid, text in (("SUB-904", f1_card), ("SUB-905", f2_card), ("SUB-906", f3_card)):
                (tp / "gold" / f"{sid}.md").write_text(text)
            fids = ["SUB-904", "SUB-905", "SUB-906"]
            v8_findings = lint_scorer(fids, "eval_holdout_v8")
            v9_findings = lint_scorer(fids, "eval_holdout_v9")
            per = lambda findings, sid: [x for x in findings if x.startswith(sid)]
            r.append(any("marked miss on conflict" in x for x in per(v8_findings, "SUB-904")))
            print(("ok   " if r[-1] else "BAD  ") + "F1: v8 marks the perfect answer miss on conflict for 'Conflict: none (…)'")
            r.append(any("marked miss on operations" in x for x in per(v8_findings, "SUB-905")))
            print(("ok   " if r[-1] else "BAD  ") + "F2: v8 marks the perfect answer miss on operations for an a.m./p.m. checklist item")
            r.append(any(x.startswith("SUB-906/gold") and "cannot read it" in x for x in v8_findings))
            print(("ok   " if r[-1] else "BAD  ") + "F3: v8 cannot read a card whose 'needs review' is not at the start of the line")
            f9 = [x for x in v9_findings if x.startswith(tuple(fids))]  # per-file findings; the set-wide gate lines are not these cards
            r.append(not f9 and not any("not caught" in x for x in v9_findings))
            print(("ok   " if r[-1] else "BAD  ") + "F1-F3: v9 scores all three cards clean and still catches every wrong answer" + (f"  got: {f9}" if f9 else ""))
            # P-068: the near-miss negatives are part of the wrong-answer set and must be caught; prove a blind scorer fails them
            nm_card = card.replace("- Operations: office lessor", "- Operations: retail store").replace(
                "- Operations items: office building lessor", "- Operations items: retail store; 24 seats; no hood; no cooking; no alcohol")
            (tp / "gold" / "SUB-907.md").write_text(nm_card)
            v10_ops_real = v10.ops_items_hit
            good_nm = [x for x in lint_scorer(["SUB-907"], "eval_holdout_v10") if "near-miss operations" in x]  # v10 catches every near-miss on this card
            v10.ops_items_hit = lambda *a: True  # a scorer blind to every operation (near-miss included)
            blind_nm = [x for x in lint_scorer(["SUB-907"], "eval_holdout_v10") if "near-miss operations" in x]
            v10.ops_items_hit = v10_ops_real
            r.append(not good_nm and bool(blind_nm))
            print(("ok   " if r[-1] else "BAD  ") + f"near-miss negatives are tested ({len(blind_nm)} caught when blind, 0 uncaught by v10)" + (f"  got: {good_nm}" if good_nm else ""))
            # P-068 / @model-risk H1: the exact adversarial repros that broke the v10 draft (interleaved counts,
            # a negation spanned across the item, a neighbouring fact). Each must be a miss; each true positive a hit.
            h1 = [  # (answer, gold items, want_hit)
                ("40 seats and 48 parking spaces", "48 seats", False),
                ("Seating for 40 with 24 parking spaces", "24 seats", False),
                ("6 units with 14 garage spaces", "14 units", False),
                ("Beer with no wine or liquor", "beer wine liquor", False),
                ("Counter space for 12 with table service", "counter service", False),
                ("Live band music - no.", "live music", False),
                ("Full liquor license, 90 seats", "beer and wine only", False),
                ("Type II hood, I think", "Type I hood", False),
                ("No liquor; beer and wine", "beer only", False),
                ("48 seats", "4 seats", False),
                ("Full bar, alcohol served, no patio", "no alcohol", False),
                ("The dining room has 48 seats.", "48 seats", True),
                ("Sin cocina, 24 asientos", "no cooking; 24 seats", True),
                ("Type I hood with UL 300", "Type I hood; UL 300", True),
                ("Retail seating for 24", "24 seats", True),
                # H3/H4/H5 (second @model-risk pass): a negation for one fact must not flip a neighbouring one
                ("Full bar, no patio", "no alcohol", False),
                ("Beer and wine, no delivery", "no alcohol", False),
                ("Type I hood, no delivery", "no hood", False),
                ("2 fryers, no hood", "no fryer", False),
                ("Type I hood, no delivery", "Type I hood", True),
                ("Beer and wine only, no liquor license", "beer and wine only", True),
                ("Beer and wine only, no liquor license", "no alcohol", False),
                ("Beer and wine: no liquor license", "beer and wine only", True),
                ("Fire sprinkler suppression system in the building", "Type I hood", False),
                ("Type I hood with UL 300 suppression", "Type I hood", True),
                # H6/H7/H8 (third @model-risk pass): a trailing negation still voids its own fact; a positive
                # value across clauses beats an absence; a negated unit count is skipped.
                ("Live music, no", "live music", False),
                ("Beer and wine, no", "beer and wine only", False),
                ("48 seats, no", "48 seats", False),
                ("Beer and wine: no liquor license", "beer and wine only", True),
                ("No hard liquor; beer and wine only", "beer and wine only", True),
                ("No liquor license; beer and wine served", "beer and wine only", True),
                ("Not 6 units, 8 units", "6 units", False),
                ("No oven on site", "oven", False),
                # H9/H10 (fourth @model-risk pass): a later-stated value wins; a negated repeat of the same
                # fact must not void an earlier positive.
                ("40 seats. 48 seats.", "48 seats", True),
                ("48 seats. 60 seats.", "48 seats", False),
                ("Type I hood, no hood", "Type I hood", True),
                ("No hood, Type I hood", "Type I hood", True),
            ]
            h1_bad = [f"{a!r} vs {i!r} (want hit={w})" for a, i, w in h1 if v10.ops_items_hit(a, i) != w]
            r.append(not h1_bad)
            print(("ok   " if r[-1] else "BAD  ") + f"H1 repros all close ({len(h1)} cases, 0 false positives, 0 false negatives)" + (f"  got: {h1_bad}" if h1_bad else ""))
        finally:
            v9.p055_gate, v10.p055_gate = v9_p055_real, v10_p055_real
        plan.write_text(json.dumps({"ids": "901-903", "in": 2, "out": 1}))
        r.append(main([str(plan), "--run-date", "2026-10-17"]) == 1)
        print(("ok   " if r[-1] else "BAD  ") + "same set without the undated declaration fails")
    INBOX, GOLD = saved
    print("SELF-CHECK", "PASS" if all(r) else "FAIL")
    return 0 if all(r) else 1


def main(argv: list[str]) -> int:
    if "--self-check" in argv:
        return self_check()
    args = [a for a in argv if not a.startswith("--")]
    run = date.today()
    if "--run-date" in argv:
        run = date.fromisoformat(argv[argv.index("--run-date") + 1])
        args.remove(argv[argv.index("--run-date") + 1])
    if "--scorer" in argv:
        args.remove(argv[argv.index("--scorer") + 1])
    plan = json.loads(Path(args[0]).read_text())
    a, b = (int(n) for n in plan["ids"].split("-"))
    ids = [f"SUB-{n:03d}" for n in range(a, b + 1)]
    f1, infos = lint_dates(ids, run, set(plan.get("undated_loss_runs") or []))
    fails = f1 + lint_gold_and_mix(ids, plan)
    scorer = argv[argv.index("--scorer") + 1] if "--scorer" in argv else "eval_holdout_v10"
    if not fails:  # the scorer test needs readable Scope lines
        fails += lint_scorer(ids, scorer)
    for w in infos:
        print("INFO ", w)
    for f in fails:
        print("FAIL ", f)
    print(f"{'FAIL' if fails else 'PASS'}: {len(fails)} failure(s), {len(infos)} info, {len(ids)} files, run date {run}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
