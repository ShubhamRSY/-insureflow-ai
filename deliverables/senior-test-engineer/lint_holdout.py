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
        (tp / "gold" / "SUB-901.md").write_text("- Scope: in scope\n- Expected carrier route: carrier_a\n")
        (tp / "gold" / "SUB-902.md").write_text("- Scope: out of scope - criterion 1 (scanned). Reason.\n")
        plan = tp / "plan.json"
        plan.write_text(json.dumps({"ids": "901-902", "in": 1, "out": 1, "per_criterion": {"1": 1}, "routes": {"carrier_a": 1}, "undated_loss_runs": ["SUB-902"]}))
        INBOX, GOLD = tp / "inbox", tp / "gold"
        r.append(main([str(plan), "--run-date", "2026-10-17"]) == 0)
        print(("ok   " if r[-1] else "BAD  ") + "clean temp set passes")
        plan.write_text(json.dumps({"ids": "901-902", "in": 1, "out": 1}))
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
    plan = json.loads(Path(args[0]).read_text())
    a, b = (int(n) for n in plan["ids"].split("-"))
    ids = [f"SUB-{n:03d}" for n in range(a, b + 1)]
    f1, infos = lint_dates(ids, run, set(plan.get("undated_loss_runs") or []))
    fails = f1 + lint_gold_and_mix(ids, plan)
    for w in infos:
        print("INFO ", w)
    for f in fails:
        print("FAIL ", f)
    print(f"{'FAIL' if fails else 'PASS'}: {len(fails)} failure(s), {len(infos)} info, {len(ids)} files, run date {run}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
