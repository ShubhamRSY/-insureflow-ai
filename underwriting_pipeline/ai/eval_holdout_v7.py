"""Scorer v7 (D-111, P-060). A copy of eval_holdout_v6.py (now frozen) plus one change, in the loss-run mark only, and nothing else:
12. Loss runs follow the gold "Expected loss run" line. When it says "needs review" (or "loss run found but no valued-as-of date", without
    "missing" first), the pipeline is correct when the loss-run field is flagged needs_review (no date, or a date that is flagged), and a miss
    when it gives a date with no flag. When gold expects a date and the pipeline returns null + needs review, the mark is "not_credited"
    (the pipeline stopped for a human; that is not a miss and not a hit). Every other loss-run case is scored exactly as in v6.
    Built from the gold FORMAT (dev gold has the line); no T-104 file or gold was read to write it.

Scorer v6 notes follow.

Scorer v6 (D-108, P-057). A copy of eval_holdout_v5.py (now frozen) plus the P-055 measures, and nothing else. Built from the gold FORMAT only:
no T-104 file or gold was read to write it.
10. Scope label. Every gold file has one line: "- Scope: in scope" or "- Scope: out of scope — <criteria>" (every criterion that applies, e.g.
    "1 scanned application; 2 multiple locations", an optional short reason after a dash). Criteria: 1 scanned application, 2 multiple
    locations, 3 non-English, 4 application not identified. Numbers and/or names are read; a number and a name that disagree, a number outside
    1-4, a missing, repeated or unreadable Scope line stops the run with a plain error BEFORE any file is scored or written (never a guess).
    Criteria are read only from the list right after "out of scope" (all numbered or all named); a reason after a dash, colon, full stop, comma or
    "because" is never read for criteria ("4 email only, scanned attachment" is criterion 4); parentheses are dropped first; bold and case variants are read.
    The hold-out is the 32-file set (D-103 exception: 20 in scope + 12 out); false manual intake is at most 2 of the 20 in-scope files.
    --check-gold (read-only, uses HOLDOUT_IDS, HOLDOUT_GOLD optional) only parses every gold Scope line: no extraction, no report read.
11. Out-of-scope gold files are not field-scored. For each, the pipeline's report is checked:
    - Leakage (hard gate, must be 0, one leak fails): any field with a value, report complete or status complete / complete - review pending,
      a carrier route, a provisional route, a suggested market, an automated missing-info draft (report["request"] present; written or would be
      written), or an enabled send (status not one of prepare.REFUSED_STATUSES, the statuses the send gate refuses by status). A route check
      that cannot be computed is a leak (fail closed).
    - Detection recall: status manual_intake / out-of-scope files, per gold criterion (a file counts under each of its criteria) and overall
      (each file once). Must be 100%. A criterion with no gold file makes the gate NOT EVALUABLE (never a pass); a leak or a missed file fails.
    - Reason accuracy (reported, not a gate): manual-intake cards whose reason codes include every gold criterion (scanned_application = 1,
      multiple_locations = 2, non_english = 3, not_identified = 4; extra reasons allowed; a "language not clear" or "text layer unknown" reason
      is not a criterion).
    - False manual intake: in-scope gold files sent to manual intake, at most 2. At 2 or fewer they are left out of the in-scope field,
      status and route denominators and listed; at 3 or more the gate fails and they stay in as misses.
    Everything in v5 (fields, operations checklist, status, false completes, silent errors, route gate: 0 unsafe, route at least 90%
    of the in-scope files counted) is computed on the in-scope files. The P-055 gate (PASS / FAIL / NOT EVALUABLE) is reported beside the T-027 gate.
    Same write rules as v5: --write only, a live run refuses to overwrite, HOLDOUT_RESCORE=1 makes no model call.
Built before any T-104 file is scored with it.

Scorer v5 notes follow.

Scorer v5 (D-103 item 3). A copy of eval_holdout_v4.py (now frozen) with one change and nothing else:
9. Operations gold is a checklist: the gold line "- Operations items:" lists the operations-gold-rule.md items the documents state,
   one per ";", in the documents' own words. Operations is a hit when every item is in the answer: the item's words (any length,
   so "no" and "I" count; joining words and/of/the/a/an/with are left out) appear together and in that order in the answer. Gold words outside the
   items (connectors such as "under", reworded business words) are not required. A gold file with no "Operations items:" line is
   scored by the v4 word rule and counted apart (ops_rule "v4 words"), so old gold is never re-read as a checklist.
   D-102 conventions are unchanged: "not in documents" makes an empty answer the hit; "hold" is a status, never a route.
   @model-risk check H2 and look-again (D-103, before any gold): an item's words must appear together and in order inside one clause of
   the answer (split on . ; : , newline), stop words aside; a match right after no/not/non/without/zero, or followed by a clause that is
   only no/none/n/0, or whose own clause goes on with only no/none/n/0 ("Live music - no"), is a miss unless the item itself starts with
   that word.
Built before any gold is written for it.

Scorer v4 notes follow.

Scorer v4 (D-097 item 2, H3). A copy of eval_holdout_v3.py (now frozen) with one change and nothing else:
8. Gold route = where the file should go once any hold clears; "hold" is a status, not a route. An unsafe route is a carrier route
   (carrier_a/b/c) where gold says senior_referral or no_match, whether the file is held (its provisional route) or not. A held file
   with no provisional route scores as "hold", which is never a gold route, so it is a miss and never unsafe.
Built before any hold-out is scored with it.

Scorer v3 notes follow.

Scorer v3 (D-096 item 2, B-372). A copy of eval_holdout_v2.py (now frozen) with two changes and nothing else:
6. The T-027 route gate: unsafe routes (a carrier route where gold says senior_referral or hold; held files by their provisional
   route) must be 0, and route accuracy must be at least 18/20: 0.9 of every file in the set (@model-risk H2 of P-050). A file with no
   route mark (failed call, no gold route) makes the gate NOT EVALUABLE, never a pass. Reported as PASS, FAIL or NOT EVALUABLE.
7. D-096 item 4: run directly, main() writes only with --write. Through regression_dev the driver's --write flag decides.
Built before any hold-out is scored with it.

Scorer v2 notes follow.

Scorer v2 (D-094 item 4). A copy of the frozen eval_holdout_127.py with three changes and nothing else:
1. Gold may say "not in documents" for a field: an empty answer is then a hit, any value a miss. Every other gold line scores as in v1
   (a null on "missing" stays not credited or a miss, as before; M5 is not applied backward).
2. Each row carries the file's own failed attempts and retries (report["retries"], D-094 item 5).
3. The header names the last commit that changed underwriting_pipeline/, beside HEAD (T-027 L4).
P-048 (D-095), added before any hold-out is scored with v2 (only dev re-checks exist), and no other change:
4. A "route" column: the provisional route of a held file (workbench.match), else its route, against the gold "Expected carrier route"
   (first word). A held file with no provisional route counts as "hold".
5. B-363 (@model-risk H1 of P-048): HOLDOUT_RESCORE=1 is a re-score: it makes no model call (a file with no saved reply stops the run,
   nothing written) and writes <name>-cache-rescore.json/.md. A live run refuses to start if its score file exists, so it never overwrites one.
The ids and output names come from the command line, so one scorer serves each new set. eval_holdout_127.py stays frozen.

v1 notes follow. A null is never a correct answer, except under change 1.

A refusal to pick, when the documents really disagree and both sides are stored,
is flagged. It is not a hit and not a miss.

Written before that hold-out exists. Do not edit this file to improve the score.
Synthetic only. Not a production approval.

Author: orchestrator (main session, budget rule 3). Built 2026-10-15 (D-088 item 3) before any SUB-127..146 submission or gold exists.
A copy of eval_holdout_107.py with the ids, the output names and the address comparison (commas set aside, @model-risk M1) changed,
and nothing else. SUB-107..126 is development data (D-088).
D-089 item 4 (B-325), before any gold: gold says complete or incomplete only. Status safety (a plain "complete" on a gold-incomplete
file is a false complete: critical, must be 0) and status automation (a gold-complete file shown as plain "complete") are reported
apart. "complete — review pending" is safe but not automated. The status hit/miss column is unchanged.

Run: HOLDOUT_IDS=154-173 HOLDOUT_OUT=deliverables/ai-engineer/evals/<name> .venv/bin/python underwriting_pipeline/ai/regression_dev.py --holdout eval_holdout_v7 --write
Format check: HOLDOUT_IDS=174-205 .venv/bin/python underwriting_pipeline/ai/eval_holdout_v7.py --check-gold
"""

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import llm_extract
import prepare

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import workbench  # noqa: E402  P-048 (c): the route the workbench shows

ROOT = Path(__file__).resolve().parents[2]
INBOX = ROOT / "simulation" / "inbox"
import os

GOLD = ROOT / (os.environ.get("HOLDOUT_GOLD") or "deliverables/senior-underwriter/gold-set")  # HOLDOUT_GOLD: a temp copy for self-checks (D-069)

_FIRST, _LAST = (int(n) for n in (os.environ.get("HOLDOUT_IDS") or "0-0").split("-"))
IDS = [f"SUB-{n:03d}" for n in range(_FIRST, _LAST + 1)]
_OUT = ROOT / (os.environ.get("HOLDOUT_OUT") or f"deliverables/ai-engineer/evals/SUB-{_FIRST:03d}-{_LAST:03d}-holdout-v7")
OUT_MD, OUT_JSON = _OUT.with_suffix(".md"), _OUT.with_suffix(".json")
NOT_IN_DOCUMENTS = "not in documents"
LABEL = "9 of 9 extracted fields scored; claims not read; loss runs = date only"  # D-039
CHECKED = ("underwriting_pipeline/", "deliverables/senior-underwriter/gold-set/", "simulation/inbox/")  # P-017 V2
FIELDS = (
    "named_insured",
    "premises",
    "effective_date",
    "operations",
    "sales",
    "tiv",
    "construction",
    "year_built",
    "loss_runs",
    "conflict",
    "status",
    "route",  # P-048 (c)
)


def parse_gold(text: str) -> dict:
    out = {}
    for raw in text.splitlines():
        if not raw.startswith("- ") or ":" not in raw:
            continue
        key, val = raw[2:].split(":", 1)
        out[key.strip().lower()] = val.strip()
    return out


CRITERIA = {1: "scanned application", 2: "multiple locations", 3: "non-English", 4: "application not identified"}
_NAMES = {1: r"scanned(?:\s+application)?|scan\b", 2: r"multi[\s-]*locations?|multiple\s+(?:locations?|premises)", 3: r"non[\s-]*english|spanish|foreign[\s-]+language",
          4: r"(?:application\s+)?(?:not|un)[\s-]*identifi(?:ed|able)|email[\s-]*only"}
CODE_CRITERION = {"scanned_application": 1, "multiple_locations": 2, "non_english": 3, "not_identified": 4}  # scope.py reason codes; other codes are not criteria
SCOPE_LINE = re.compile(r"(?im)^\s*(?:[-*]\s*)?(?:\*\*|__)?scope(?:\*\*|__)?\s*[:\-–—]\s*(?:\*\*|__)?(.*)$")  # "- Scope: ...", "- **Scope:** ...", "Scope - ..."
_SEP = r"\s*(?:[;,&+/]|\band\b)\s*"
_REASON = re.compile(r"(?i)^\s*(?:$|[—–:.,]|-(?:\s|$)|;\s*reason\b|\b(?:because|since|reason|why)\b)")  # what may follow the criteria list


def _name_at(text: str, pos: int) -> tuple[int | None, int]:
    for c, rx in _NAMES.items():
        m = re.compile(rx, re.I).match(text, pos)
        if m:
            return c, m.end()
    return None, pos


def gold_scope(text: str) -> dict:
    """{"out": bool, "criteria": [1..4]} from the one Scope line. ValueError (plain words) when it is missing, repeated or unreadable.
    Criteria are read only from the list right after "out of scope": numbers 1-4 and/or criterion names, in one style (all numbered, or all
    named). The list ends at the first thing that is not another criterion; what follows must start like a reason (a dash, colon, full stop,
    comma, "because"...). A reason is never read for criteria: "4 email only, scanned attachment" is criterion 4. Parentheses are dropped first."""
    lines = SCOPE_LINE.findall(text)
    if len(lines) != 1:
        raise ValueError("no Scope line" if not lines else "more than one Scope line")
    value = lines[0].strip()
    while (cut := re.sub(r"\([^()]*\)", " ", value)) != value:
        value = cut
    value = re.sub(r"[*_]{2}", "", value).strip()
    if re.match(r"(?i)in[\s-]*scope\b", value):
        return {"out": False, "criteria": []}
    out = re.match(r"(?i)out[\s-]*of[\s-]*scope\b[\s:—–-]*", value)
    if not out:
        raise ValueError(f"Scope line is neither 'in scope' nor 'out of scope': {value[:60]!r}")
    pos, found, numbered = out.end(), [], None
    while True:
        m = re.compile(r"(?i)(?:criteri(?:on|a)\s*)?(\d)\b\s*").match(value, pos) if numbered is not False else None
        if m:
            numbered, c, end = True, int(m.group(1)), m.end()
            named, end2 = _name_at(value, end)
            if c not in CRITERIA or (named is not None and named != c):
                raise ValueError(f"cannot read criterion in {value[pos:pos + 40]!r}")
            end = end2
        elif numbered is not True:
            c, end = _name_at(value, pos)
            if c is None:
                break
            numbered = False
        else:
            break
        found.append(c)
        sep = re.compile(_SEP, re.I).match(value, end)
        if not sep:
            pos = end
            break
        nxt_ok = re.compile(r"(?i)(?:criteri(?:on|a)\s*)?\d\b").match(value, sep.end()) if numbered else _name_at(value, sep.end())[0] is not None
        if not nxt_ok:
            pos = end  # the separator belongs to the reason ("4 email only, scanned attachment")
            break
        pos = sep.end()
    if not found:
        raise ValueError("out of scope with no criterion named" if not value[out.end():].strip() else f"cannot read the criteria after 'out of scope': {value[out.end():][:50]!r}")
    if not _REASON.match(value[pos:]):
        raise ValueError(f"cannot read what follows the criteria: {value[pos:][:50]!r}")
    return {"out": True, "criteria": sorted(set(found))}


def gold_scopes(ids: list[str]) -> tuple[dict, list[str]]:
    """Every gold Scope line for ids: ({id: scope}, [plain error lines]). Reads only the gold files."""
    found, errors = {}, []
    for sid in ids:
        path = GOLD / f"{sid}.md"
        try:
            found[sid] = gold_scope(path.read_text())
        except OSError:
            errors.append(f"{sid}: gold file not found")
        except ValueError as why:
            errors.append(f"{sid}: {why}")
    return found, errors


def scope_totals(found: dict) -> dict:
    """In/out counts, files per criterion, two-criteria files and criterion-4 files, from parsed Scope lines."""
    out = {sid: sc["criteria"] for sid, sc in found.items() if sc["out"]}
    return {"in": len(found) - len(out), "out": len(out), "per_criterion": {c: sum(c in v for v in out.values()) for c in CRITERIA},
            "two_criteria": [sid for sid, v in out.items() if len(v) >= 2], "criterion_4": [sid for sid, v in out.items() if 4 in v]}


def leaks_of(report: dict) -> list[str]:
    """P-055 leakage: what an out-of-scope file shows that it must not. Empty is clean. Stricter on purpose; a check that fails is a leak."""
    found = []
    if any(r.get("value") is not None and r.get("value") != "" for r in report.get("fields") or []):  # fail closed: 0 and False are shown values
        found.append("field shown")
    if report.get("complete") or report.get("status") in ("complete", prepare.REVIEW_PENDING):
        found.append("complete status")
    try:
        m = workbench.match(report)
        if m.get("route") in CARRIERS:
            found.append("carrier route")
        if m.get("provisional"):
            found.append("provisional route")
        if m.get("suggested"):
            found.append("suggested market")
    except Exception:  # fail closed
        found.append("route unreadable")
    if report.get("request"):
        found.append("automated draft")
    if report.get("status") not in prepare.REFUSED_STATUSES:
        found.append("send enabled")
    return found


def scope_row(sid: str, sc: dict, report: dict) -> dict:
    codes = [r["code"] for r in (report.get("scope") or {}).get("reasons") or []]
    detected = report.get("status") == prepare.MANUAL_INTAKE
    return {"submission": sid, "criteria": sc["criteria"], "detected": detected, "reason_codes": codes, "leaks": leaks_of(report),
            "reasons_ok": detected and set(sc["criteria"]) <= {CODE_CRITERION[c] for c in codes if c in CODE_CRITERION}}


MAX_FALSE_MANUAL = 2  # P-055: in-scope files sent to manual intake by mistake, at most 2 of the 20 in-scope files (the 32-file set, D-103 exception: 20 in + 12 out)


def p055_gate(out_rows: list[dict], in_rows: list[dict]) -> dict:
    """P-055 measures. out_rows: scope_row of each out-of-scope gold file. in_rows: score_one rows of the in-scope gold files (each has "manual_intake")."""
    per = {c: [r for r in out_rows if c in r["criteria"]] for c in CRITERIA}
    recall = {c: {"detected": sum(r["detected"] for r in rows), "files": len(rows)} for c, rows in per.items()}
    leaked = [r["submission"] for r in out_rows if r["leaks"]]
    missed = [r["submission"] for r in out_rows if not r["detected"]]
    false_manual = [r["submission"] for r in in_rows if r.get("manual_intake")]
    ceiling = len(false_manual) <= MAX_FALSE_MANUAL
    gaps = [c for c, v in recall.items() if not v["files"]]
    failed = bool(leaked or missed or not ceiling)
    verdict = "FAIL" if failed else "NOT EVALUABLE" if gaps or not in_rows else "PASS"
    detected_rows = [r for r in out_rows if r["detected"]]
    return {"out_of_scope": len(out_rows), "in_scope": len(in_rows), "leaks": len(leaked), "leak_ids": leaked, "recall": recall,
            "recall_overall": {"detected": len(out_rows) - len(missed), "files": len(out_rows), "missed_ids": missed},
            "reasons_ok": sum(r["reasons_ok"] for r in detected_rows), "reasons_cards": len(detected_rows),
            "reasons_bad_ids": [r["submission"] for r in detected_rows if not r["reasons_ok"]],
            "false_manual": len(false_manual), "false_manual_ids": false_manual, "ceiling_met": ceiling, "criteria_without_files": gaps, "verdict": verdict}


def digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def words(text: str) -> list[str]:
    stop = {"with", "and", "the", "that", "this", "from", "unit"}
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in stop and (len(w) >= 4 or w.isdigit())]


ITEM_STOP = {"and", "of", "the", "a", "an", "with"}


def item_words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in ITEM_STOP]


NEGATION = {"no", "not", "non", "without", "zero"}
NO_CLAUSE = {"no", "none", "n", "0"}


def _clauses(text: str) -> list[list[str]]:
    return [item_words(part) for part in re.split(r"[.;:,\n]", (text or "").lower())]


def ops_items_hit(answer: str, items_line: str) -> bool:
    """v5: every checklist item is in the answer: its words together and in order inside one clause (split on . ; : , newline), stop words
    aside. @model-risk check H2 and look-again: a match right after no/not/non/without/zero, or whose next clause is only no/none/n/0,
    does not count, unless the item itself starts with that word. An empty checklist is never a hit."""
    clauses = _clauses(answer)
    items = [item_words(item) for item in items_line.split(";") if item_words(item)]

    def found(item: list[str]) -> bool:
        for n, words in enumerate(clauses):
            nxt = clauses[n + 1] if n + 1 < len(clauses) else []
            for at in range(len(words) - len(item) + 1):
                if words[at : at + len(item)] != item:
                    continue
                negated = at > 0 and words[at - 1] in NEGATION and item[0] not in NEGATION
                rest = words[at + len(item) :]
                negated = negated or bool(rest) and set(rest) <= NO_CLAUSE  # look-again H3: "Live music - no", "Beer and wine (none)"
                if not negated and not (nxt and set(nxt) <= NO_CLAUSE):
                    return True
        return False

    return bool(items) and all(found(item) for item in items)


def commit() -> tuple[str, list[str]]:
    """P-017 Part 2: HEAD and the uncommitted paths under the checked folders. "unknown" when git cannot say."""
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        code = subprocess.run(["git", "log", "-1", "--format=%H", "--", "underwriting_pipeline/"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        head = f"{head} (last pipeline commit {code})"
        dirty = subprocess.run(["git", "status", "--porcelain", "--", *CHECKED], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return "unknown", []
    return head, [line[3:] for line in dirty.splitlines()]


def call_sentence(report: dict, new_usage: list[dict]) -> str:
    """P-017 Part 1, computed here from the report and this call's usage rows; prepare.py is not changed."""
    if report.get("error"):
        return "called: reply not usable" if report.get("error") == "reply_not_usable" else f"call failed: {report['error']}"
    if report.get("status") == "all_values_rejected":
        return "called: every value rejected by the gate"
    if not new_usage:
        return "not sent: no readable text"
    return "from cache: saved reply used, no call in this run" if new_usage[-1].get("cached") else "called: reply used"


def address(value: str | None) -> str:
    """B-305 (D-083): a parenthetical note ("(shop and yard)") is not part of the address. D-088 item 3: commas are set aside ("Austin TX" = "Austin, TX")."""
    return re.sub(r"\s+", " ", re.sub(r"\([^)]*\)", "", value or "").replace(",", " ")).strip()


def field_map(report: dict) -> dict:
    return {row["field_id"]: row for row in report["fields"]}


def judge(gold_missing: bool, got: str | None, matches: bool, gold_line: str = "") -> str:
    """v1: null never counts as correct, including when the gold line says missing. v2: gold "not in documents" -> empty is a hit."""
    if gold_line.strip().lower().rstrip(".") == NOT_IN_DOCUMENTS:
        return "miss" if got else "hit"
    if not got:
        return "not_credited" if gold_missing else "miss"
    return "hit" if matches else "miss"


def money(text: str) -> str:
    """B-319 (D-086): "$1,520,000" and "1520000" are the same amount: drop "$" and thousands commas."""
    return re.sub(r"(?<=\d),(?=\d{3}\b)", "", text.replace("$", ""))


def sides_stored(gold_line: str, blob: str) -> bool:
    gold_line, blob = money(gold_line), money(blob)
    dates = re.findall(r"20\d\d-\d\d-\d\d", gold_line)
    if len(dates) >= 2:
        return all(date in blob for date in dates)
    needles = [
        needle
        for needle in re.findall(r"\d+\s+[A-Za-z]+", gold_line)
        if not needle.lower().endswith(" and")
    ] or re.findall(r"\d+", gold_line)
    return bool(needles) and all(needle.lower() in blob for needle in needles)


def mentions(gold_line: str, *words: str) -> bool:
    low = gold_line.lower()
    return low != "none" and any(word in low for word in words)


def loss_run_mark(gold: dict, runs: str | None, flagged: bool, runs_missing: bool, date: "re.Match[str] | None") -> str:
    """v7 (P-060). v6 rule, except: gold expects review -> flagged is correct; gold expects a date, null + needs review -> not_credited."""
    expected = (gold.get("expected loss run") or "").strip().lower()
    wants_review = expected.startswith("needs review") or expected.startswith("loss run found but no valued-as-of date")
    if wants_review:
        return "hit" if flagged else "miss"
    if not runs and flagged and not runs_missing and date:
        return "not_credited"
    return judge(runs_missing, runs, bool(date) and bool(runs) and date.group(0) in runs, gold["loss runs"])


def score_one(sid: str) -> dict:
    gold_text = (GOLD / f"{sid}.md").read_text()
    gold = parse_gold(gold_text)
    try:
        sc = gold_scope(gold_text)  # v6: also checked for the whole set in main() before anything runs
    except ValueError as why:
        raise SystemExit(f"scorer v7 stopped: {sid}: {why}")
    used = len(llm_extract.USAGE)
    report = prepare.process_submission(INBOX / sid)
    call = call_sentence(report, llm_extract.USAGE[used:])
    if sc["out"]:  # v6: not field-scored; the P-055 measures only
        return {**scope_row(sid, sc, report), "scope": "out", "format": gold.get("format"), "error": None, "call": call, "checks": {}, "retries": report.get("retries", [])}
    got = field_map(report)
    named = got["named_insured"]["value"]
    premises = got["premises_address"]["value"]
    effective = got["effective_date"]["value"]
    ops = got["operations"]["value"]
    sales = got["sales_or_payroll"]["value"]
    tiv = got["tiv_building"]["value"]
    construction = got["construction"]["value"]
    year = got["year_built"]["value"]
    runs = got["loss_run_valued_through"]["value"]
    identity = bool(named or premises or ops)
    open_conflicts = [c for c in report["conflicts"] if c.get("resolution") != "resolved"]
    conflict_blob = json.dumps(open_conflicts).lower()

    def has_all(needles: list[str]) -> bool:
        return bool(needles) and all(needle.lower() in conflict_blob for needle in needles)

    checks = {
        "named_insured": judge(False, named, named == gold["named insured"], gold["named insured"]),
        "effective_date": judge(gold["effective date"].lower().startswith("missing"), effective, effective == gold["effective date"], gold["effective date"]),  # X1: exact
        "operations": judge(False, ops, bool(ops) and (ops_items_hit(ops, gold["operations items"]) if gold.get("operations items") else all(word in set(words(ops)) for word in words(gold["operations"]))), gold["operations"]),
        "sales": judge(False, sales, bool(sales) and digits(sales) == digits(gold["sales"]), gold["sales"]),
        "construction": judge(False, construction, bool(construction) and gold["construction"].lower() in construction.lower(), gold["construction"]),
        "year_built": judge(False, year, bool(year) and digits(year) == digits(gold["year built"]), gold["year built"]),
    }
    if gold["premises"].lower().startswith("both"):
        if sides_stored(gold["premises"], conflict_blob) and not premises:
            checks["premises"] = "flagged"
        else:
            checks["premises"] = "miss"
    else:
        checks["premises"] = judge(False, premises, bool(premises) and address(premises) == address(gold["premises"]), gold["premises"])
    if gold["tiv"].strip() == "0":
        checks["tiv"] = "hit" if tiv is not None and digits(tiv) in {"", "0"} else "miss"
    else:
        checks["tiv"] = judge(False, tiv, bool(tiv) and digits(tiv) == digits(gold["tiv"]), gold["tiv"])
    runs_missing = gold["loss runs"].lower().startswith("missing")
    date = re.search(r"20\d\d-\d\d-\d\d", gold["loss runs"])
    checks["loss_runs"] = loss_run_mark(gold, runs, bool(got["loss_run_valued_through"].get("needs_review")), runs_missing, date)
    if gold["conflict"].lower() == "none":
        if not identity:
            checks["conflict"] = "not_credited"
        else:
            checks["conflict"] = "hit" if not open_conflicts else "miss"
    else:
        checks["conflict"] = "flagged" if sides_stored(gold["conflict"], conflict_blob) else "miss"
    topic_values = {
        "effective_date": effective,
        "sales": sales,
        "tiv": tiv,
        "operations": ops,
        "construction": construction,
        "year_built": year,
        "loss_runs": runs,
    }
    topic_words = {
        "effective_date": ("effective",),
        "sales": ("sales",),
        "tiv": ("tiv",),
        "operations": ("operations",),
        "construction": ("construction",),
        "year_built": ("year",),
        "loss_runs": ("loss",),
    }
    for field, topics in topic_words.items():
        if not mentions(gold["conflict"], *topics):
            continue
        if sides_stored(gold["conflict"], conflict_blob) and not topic_values[field]:
            checks[field] = "flagged"
        elif sides_stored(gold["conflict"], conflict_blob):
            checks[field] = "miss"
    gold_complete = gold["status"].lower().startswith("complete")
    if not identity:
        checks["status"] = "miss" if gold_complete else "not_credited"
    else:
        checks["status"] = "hit" if report["complete"] is gold_complete else "miss"
    system_status = report.get("status")
    safety = "false_complete" if system_status == "complete" and not gold_complete else "safe"  # B-325: review pending is safe
    automation = ("automated" if system_status == "complete" else "not_automated") if gold_complete else None  # gold-complete files only
    gold_route = gold_route_of(gold.get("expected carrier route") or "")
    used = route_used(report) if gold_route and not report.get("error") else None
    if used:  # P-048 (c): the provisional route of a held file
        checks["route"] = "hit" if used == gold_route else "miss"
    if report.get("error"):
        checks = dict.fromkeys(checks, "call_failed")  # a failed or empty model call is not a miss
        safety, automation = "call_failed", ("call_failed" if gold_complete else None)
    return {
        "submission": sid,
        "format": gold.get("format"),
        "error": report.get("error"),
        "call": call,
        "checks": checks,
        "system_status": system_status,
        "status_safety": safety,
        "status_automation": automation,
        "extracted_named_insured": named,
        "scope": "in",
        "manual_intake": report.get("status") == prepare.MANUAL_INTAKE,  # v6: an in-scope file sent to manual intake by mistake
        "ops_rule": "checklist" if gold.get("operations items") else "v4 words",  # v5
        "retries": report.get("retries", []),  # D-094 item 5
        "gold_route": gold_route,
        "route_used": used,  # D-096: kept for the unsafe-route count
    }


def gold_route_of(line: str) -> str | None:
    """The route a gold line names first: "Carrier A" is carrier_a; a sentence ("TIV missing") names none (code-review)."""
    found = re.match(r"\s*(carrier[ _][abc]|senior_referral|senior referral|no_match|no match|hold)\b", line.lower())
    return found.group(1).replace(" ", "_") if found else None


def route_used(report: dict) -> str:
    m = workbench.match(report)
    return (m.get("provisional") or "hold") if m["route"] == "hold" else m["route"]


RESCORE = os.environ.get("HOLDOUT_RESCORE") == "1"


def out_paths(rescore: bool) -> tuple[Path, Path]:
    """B-363: a re-score writes its own files; a live run never overwrites an existing score file."""
    base = _OUT.with_name(_OUT.name + "-cache-rescore") if rescore else _OUT
    paths = base.with_suffix(".json"), base.with_suffix(".md")
    if not rescore and any(path.exists() for path in paths):
        raise SystemExit(f"refused: {paths[0].name} exists; a live run never overwrites a score file (B-363). Use a new HOLDOUT_OUT, or HOLDOUT_RESCORE=1 to re-score.")
    return paths


def _no_call(settings: dict, payload: dict) -> dict:
    raise SystemExit("re-score refused: a file has no saved reply in the cache; HOLDOUT_RESCORE=1 makes no model call (B-363). Nothing written.")


CARRIERS = ("carrier_a", "carrier_b", "carrier_c")
UNSAFE_GOLD = ("senior_referral", "no_match")  # D-097 H3
ROUTE_FLOOR = 0.9  # D-096: at least 18/20


def route_gate(rows: list[dict]) -> dict:
    """D-096 (B-372): unsafe routes must be 0; route accuracy at least 18/20. Failed calls are left out, as everywhere."""
    marked = [r for r in rows if r["checks"].get("route") in ("hit", "miss")]
    unsafe = [r["submission"] for r in marked if r.get("gold_route") in UNSAFE_GOLD and r.get("route_used") in CARRIERS]
    hits = sum(r["checks"]["route"] == "hit" for r in marked)
    evaluable = bool(rows) and len(marked) == len(rows)  # @model-risk H2: 17/18 with 2 failed calls is not 18/20
    passed = evaluable and not unsafe and hits >= ROUTE_FLOOR * len(rows)
    verdict = "PASS" if passed else "FAIL" if evaluable or unsafe else "NOT EVALUABLE"  # @model-risk M4: an unsafe route always fails
    return {"unsafe": len(unsafe), "unsafe_ids": unsafe, "hits": hits, "scored": len(marked), "files": len(rows), "evaluable": evaluable, "pass": passed, "verdict": verdict}


def status_counts(rows: list[dict]) -> dict:
    """B-325: false completes (critical) and plain-complete automation on gold-complete files, from each row's own marks."""
    return {"false_complete": sum(r.get("status_safety") == "false_complete" for r in rows),
            "false_complete_ids": [r["submission"] for r in rows if r.get("status_safety") == "false_complete"],
            "gold_complete": sum(r.get("status_automation") in ("automated", "not_automated") for r in rows),
            "automated": sum(r.get("status_automation") == "automated" for r in rows),
            "call_failed": sum(r.get("status_safety") == "call_failed" for r in rows)}


def main() -> None:
    global OUT_JSON, OUT_MD
    _, bad = gold_scopes(IDS)
    if bad:  # v6: before any call and before anything is written
        raise SystemExit("scorer v7 stopped, nothing scored or written. Gold Scope line problems:\n  " + "\n  ".join(bad))
    OUT_JSON, OUT_MD = out_paths(RESCORE)  # before any call: a refused live run spends nothing
    if RESCORE:
        llm_extract._post = _no_call
    every = [score_one(sid) for sid in IDS]
    out_rows = [r for r in every if r["scope"] == "out"]
    in_all = [r for r in every if r["scope"] == "in"]
    p055 = p055_gate(out_rows, in_all)
    rows = in_all if not p055["ceiling_met"] else [r for r in in_all if not r["manual_intake"]]  # v6: false manual intake leaves the in-scope denominators only when the ceiling is met
    head, dirty = commit()
    counted = {field: {"hit": 0, "hit (needs review)": 0, "miss": 0, "not_credited": 0, "call_failed": 0, "flagged": 0} for field in FIELDS}
    for row in rows:
        for field, mark in row["checks"].items():
            counted[field][mark] += 1
    status_split = status_counts(rows)
    gate = route_gate(rows)
    OUT_JSON.write_text(json.dumps({"label": LABEL, "commit": head, "uncommitted": dirty, "model": llm_extract.endpoint_settings()["model"], "host": llm_extract._host(), "submissions": rows, "counted": counted, "status_split": status_split, "route_gate": gate, "p055_gate": p055, "scope_rows": out_rows + [r for r in in_all if r not in rows]}, indent=2) + "\n")
    lines = [
        f"# Extraction score (scorer v7) — {IDS[0]} through {IDS[-1]}",
        "",
        "- Author: @ai-engineer-assistant",
        f"- {LABEL}.",
        f"- Commit: {head}" + (f", with uncommitted changes in: {', '.join(dirty)}. This is not a score of that commit." if dirty else "."),
        "- Scored with this file unchanged after the gold answers were written. A development re-check is not a hold-out.",
        "- A null that matches a missing gold line is not_credited. It is not a correct answer.",
        "- Correctly flagged for human means the documents disagree and the AI stored both sides without picking one. It is not a hit and not a miss.",
        "- Synthetic. Not a production approval.",
        "",
        "## Per-field",
        "",
        "| Field | Hit | Hit (needs review) | Miss | Not credited | Correctly flagged for human | Call failed |",
        "|---|---|---|---|---|---|---|",
    ]
    for field in FIELDS:
        item = counted[field]
        lines.append(
            f"| {field} | {item['hit']} | {item['hit (needs review)']} | {item['miss']} | {item['not_credited']} | {item['flagged']} | {item['call_failed']} |"
        )
    lines += ["", "## Status safety and status automation (B-325)", "",
              f"- False completes (plain \"complete\" on a gold-incomplete file): **{status_split['false_complete']}** ({', '.join(status_split['false_complete_ids']) or 'none'}). Critical: must be 0.",
              f"- Status automation: {status_split['automated']} of {status_split['gold_complete']} gold-complete files shown as plain \"complete\". \"complete — review pending\" is safe but not automated.",
              f"- Failed calls, left out of both: {status_split['call_failed']}.",
              f"- Operations scored by checklist (v5): {sum(r['ops_rule'] == 'checklist' for r in rows)} of {len(rows)} files; the rest by the v4 word rule.",
              "", "## T-027 route gate (D-096, D-097)", "",
              f"- Unsafe routes (a carrier, held or not, where gold says senior_referral or no_match): **{gate['unsafe']}** ({', '.join(gate['unsafe_ids']) or 'none'}). Must be 0.",
              f"- Route accuracy: {gate['hits']}/{gate['files']} ({gate['files'] - gate['scored']} files with no route mark). Must be at least 18/20.",
              f"- Route hits over all {len(in_all)} in-scope gold files (none left out): {sum(r['checks'].get('route') == 'hit' for r in in_all)}/{len(in_all)}. Gate rule unchanged.",
              f"- Route gate: **{gate['verdict']}**.",
              "", "## P-055 scope gate (D-108, P-057), apart from the T-027 gate", "",
              f"- Files: {p055['out_of_scope']} out of scope, {p055['in_scope']} in scope (gold Scope lines). Out-of-scope files are not field-scored.",
              f"- Leakage (hard gate): **{p055['leaks']}** of {p055['out_of_scope']} ({', '.join(p055['leak_ids']) or 'none'}). Must be 0."]
    for r in out_rows:
        if r["leaks"]:
            lines.append(f"  - {r['submission']}: {', '.join(r['leaks'])}")
    lines += [f"- Detection recall, overall: {p055['recall_overall']['detected']}/{p055['recall_overall']['files']} (missed: {', '.join(p055['recall_overall']['missed_ids']) or 'none'}). Must be 100%.",
              *[f"  - criterion {c} {CRITERIA[c]}: {v['detected']}/{v['files']}" + ("" if v["files"] else " (no gold file: gate cannot pass)") for c, v in p055["recall"].items()],
              f"- Reason accuracy (reported): {p055['reasons_ok']}/{p055['reasons_cards']} manual-intake cards list every gold criterion" + (f" (not: {', '.join(p055['reasons_bad_ids'])})" if p055["reasons_bad_ids"] else "") + ".",
              f"- False manual intake: {p055['false_manual']} of {p055['in_scope']} in-scope files ({', '.join(p055['false_manual_ids']) or 'none'}). At most {MAX_FALSE_MANUAL}; "
              + ("within the ceiling, they are left out of the in-scope counts above." if p055["ceiling_met"] else "ABOVE the ceiling: they stay in the in-scope counts as misses."),
              f"- P-055 scope gate: **{p055['verdict']}**."]
    lines.append("")
    lines.append("## Per submission")
    lines.append("")
    for row in out_rows:
        lines.append(f"- {row['submission']} (out of scope, criteria {', '.join(map(str, row['criteria']))}): manual intake: {'yes' if row['detected'] else 'NO'}. Reason codes: {', '.join(row['reason_codes']) or 'none'}. Leaks: {', '.join(row['leaks']) or 'none'}.")
    for row in rows:
        missed = [name for name, mark in row["checks"].items() if mark == "miss"]
        flagged = [name for name, mark in row["checks"].items() if mark == "flagged"]
        lines.append(
            f"- {row['submission']} ({row['format']}): extracted name {row['extracted_named_insured'] or 'null'}. "
            f"Misses: {', '.join(missed) or 'none'}. "
            f"Flagged: {', '.join(flagged) or 'none'}. "
            f"Call: {row['call']}. Retries: {len(row['retries'])}" + (f" ({', '.join(r['kind'] for r in row['retries'])})" if row['retries'] else "") + "."
        )
    lines.append("")
    OUT_MD.write_text("\n".join(lines))
    print(OUT_MD)
    for field in FIELDS:
        item = counted[field]
        print(field, item)


def _v7_self_check() -> None:
    """P-060: the loss-run mark, on synthetic gold lines only."""
    d = lambda text: re.search(r"20\d\d-\d\d-\d\d", text)
    mark = lambda exp, line, runs, flag: loss_run_mark({"expected loss run": exp, "loss runs": line}, runs, flag, line.lower().startswith("missing"), d(line))
    rev = "needs review — not a recognised carrier loss run"
    assert mark(rev, "typed table, no valued date", None, True) == "hit", "gold review, pipeline null + review: correct"
    assert mark(rev, "typed table, no valued date", "2026-09-30", True) == "hit" and mark(rev, "typed table", "2026-09-30", False) == "miss" and mark(rev, "typed table", None, False) == "miss"
    assert mark("loss run found but no valued-as-of date; ask the producer", "Carrier B document with no valuation date", None, True) == "hit"
    assert mark("2026-09-30 accepted", "valued through 2026-09-30, 1 claim", None, True) == "not_credited", "null + review where gold expects a date"
    assert mark("2026-09-30 accepted", "valued through 2026-09-30, 1 claim", None, False) == "miss", "null with no flag is still a miss"
    assert mark("2026-09-30 accepted", "valued through 2026-09-30, 1 claim", "2026-09-30", False) == "hit" and mark("2026-09-30 accepted", "valued through 2026-09-30", "2026-08-01", False) == "miss"
    assert mark("missing — no loss run provided", "missing, none provided", None, False) == "not_credited" and mark("missing — x", "missing, x", "2026-09-30", False) == "miss", "v6 unchanged"
    assert mark("missing — loss run found but no valued-as-of date", "missing, undated", None, True) == "not_credited", "missing first: v6 rule"
    _v6_self_check()


def _v6_self_check() -> None:
    """Synthetic gold lines and reports only; no gold file, no pipeline run."""
    g = lambda line: gold_scope(f"# x\n- Named insured: A\n{line}\n")
    assert g("- Scope: in scope") == {"out": False, "criteria": []} and g("- Scope: In scope — typed application, scanned loss run")["out"] is False
    assert g("- Scope: out of scope — 1 scanned application") == {"out": True, "criteria": [1]}
    assert g("- Scope: out of scope — 1 scanned application; 2 multiple locations")["criteria"] == [1, 2]
    assert g("- Scope: Out of scope - 3 non-English (Spanish), 4 application not identified - email only")["criteria"] == [3, 4]
    assert g("- Scope: out of scope — multiple locations and scanned application. Reason: two sites")["criteria"] == [1, 2]
    assert g("- Scope: out of scope: criterion 2")["criteria"] == [2] and g("- Scope: out of scope — 1, 2 & 3")["criteria"] == [1, 2, 3]
    assert g("- Scope: out of scope — email-only")["criteria"] == [4] and g("- Scope: out of scope — Multi-location; Non English")["criteria"] == [2, 3]
    # markdown and case variants; a reason is never a criterion; parentheses are dropped
    assert g("- **Scope:** out of scope — 1 scanned application")["criteria"] == [1] and g("Scope - in scope")["out"] is False and g("- SCOPE: OUT OF SCOPE — 2")["criteria"] == [2]
    assert g("- **Scope**: out of scope — 3 non-English")["criteria"] == [3] and g("- scope: Out-of-scope: 1; 2")["criteria"] == [1, 2]
    assert g("- Scope: out of scope — 4 email only, scanned attachment")["criteria"] == [4], "a reason after a comma is not a criterion"
    assert g("- Scope: out of scope — 3 non-English (Spanish, some English)")["criteria"] == [3] and g("- Scope: out of scope — 2 multiple locations (Loc 1 and Loc 2)")["criteria"] == [2]
    assert g("- Scope: out of scope — 1 scanned application because page 2 is a photo")["criteria"] == [1]
    assert g("- Scope: out of scope — 1 scanned application; 4 application not identified: no application")["criteria"] == [1, 4]
    assert g("- Scope: out of scope — scanned application, multiple locations — reason: a photo of page 2")["criteria"] == [1, 2]
    for bad in ("- Scope: out of scope", "- Scope: out of scope — 5 other", "- Scope: out of scope — 1 multiple locations", "- Scope: maybe", "- Scope: out of scope — soon",
                "- Scope: out of scope — 1 and 2 pages", "- Scope:", "- Scope: out of scope — scanned attachment only",
                "- Scope: out of scope — 4 email only; scanned attachment", "- Scope: out of scope — 1 scanned application and the second page", "- Scope: out of scope — 3 multiple locations"):
        try:
            g(bad)
            raise AssertionError(("parsed", bad))
        except ValueError:
            pass
    for text in ("- Named insured: A\n", "- Scope: in scope\n- Scope: out of scope — 1\n"):
        try:
            gold_scope(text)
            raise AssertionError("missing or repeated Scope line parsed")
        except ValueError:
            pass
    global GOLD, _OUT
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:  # an unparseable line stops the run before anything is scored or written
        real_gold, real_ids, real_out = GOLD, IDS[:], _OUT
        GOLD, _OUT = Path(tmp), Path(tmp) / "x"  # gold and output are temp folders, restored in finally
        (GOLD / "SUB-901.md").write_text("- Scope: in scope\n")
        (GOLD / "SUB-902.md").write_text("- Scope: out of scope — 9\n")
        (GOLD / "SUB-903.md").write_text("- Named insured: X\n")
        found, errs = gold_scopes(["SUB-901", "SUB-902", "SUB-903", "SUB-904"])
        assert list(found) == ["SUB-901"] and len(errs) == 3, (found, errs)
        IDS[:] = ["SUB-901", "SUB-902"]
        try:
            try:
                main()
                raise AssertionError("main ran with an unparseable Scope line")
            except SystemExit as stop:
                assert "nothing scored or written" in str(stop) and "SUB-902" in str(stop), stop
            assert not list(Path(tmp).glob("*.json")) and not list(Path(tmp).glob("x*")), "nothing written"
        finally:
            GOLD, IDS[:], _OUT = real_gold, real_ids, real_out
        tot = scope_totals({"A": {"out": False, "criteria": []}, "B": {"out": True, "criteria": [1, 2]}, "C": {"out": True, "criteria": [4]}, "D": {"out": True, "criteria": [4, 3]}})
        assert tot == {"in": 1, "out": 3, "per_criterion": {1: 1, 2: 1, 3: 1, 4: 2}, "two_criteria": ["B", "D"], "criterion_4": ["C", "D"]}, tot
    # leakage: each way an out-of-scope file can leak fails, a clean manual-intake report does not
    clean = {"status": prepare.MANUAL_INTAKE, "complete": False, "request": None, "scope": {"reasons": [{"code": "scanned_application"}]},
             "fields": [{"field_id": "operations", "value": None}, {"field_id": "tiv_building", "value": None}]}
    assert leaks_of(clean) == [], leaks_of(clean)
    office = [{"field_id": "operations", "value": "office"}, {"field_id": "tiv_building", "value": None}]
    big = [{"field_id": "operations", "value": "office"}, {"field_id": "tiv_building", "value": "$500,000"}]
    cases = {
        "complete status": ({**clean, "status": "complete", "complete": True}, "complete status"),
        "review pending": ({**clean, "status": prepare.REVIEW_PENDING}, "complete status"),
        "field shown": ({**clean, "fields": office}, "field shown"),
        "zero shown": ({**clean, "fields": [{"field_id": "tiv_building", "value": 0}]}, "field shown"),
        "false shown": ({**clean, "fields": [{"field_id": "x", "value": False}]}, "field shown"),
        "carrier route": ({"status": "complete", "complete": True, "fields": big, "request": None, "conflicts": []}, "carrier route"),
        "provisional route": ({"status": "incomplete", "complete": False, "fields": office, "request": None, "conflicts": []}, "provisional route"),
        "draft": ({**clean, "request": "Please send the missing items"}, "automated draft"),
        "send enabled": ({**clean, "status": "incomplete"}, "send enabled"),
    }
    for label, (report, expect) in cases.items():
        assert expect in leaks_of(report), (label, leaks_of(report))
    real_match = workbench.match
    workbench.match = lambda r: {"route": "manual_intake", "suggested": "carrier_b"}
    try:
        assert "suggested market" in leaks_of(clean)
    finally:
        workbench.match = real_match
    assert "route unreadable" in leaks_of({**clean, "fields": None, "status": "complete"})
    # the gate: build files from reports
    row = lambda sid, crit, report: scope_row(sid, {"out": True, "criteria": crit}, report)
    ok = lambda sid, crit, codes: row(sid, crit, {**clean, "scope": {"reasons": [{"code": c} for c in codes]}})
    base = [ok("A", [1], ["scanned_application"]), ok("B", [2], ["multiple_locations"]), ok("C", [3], ["non_english"]), ok("D", [4], ["not_identified"]),
            ok("E", [1, 2], ["scanned_application", "multiple_locations", "non_english"])]
    ins = lambda n, mi=0: [{"submission": f"I{i}", "manual_intake": i < mi} for i in range(n)]
    g = p055_gate(base, ins(20))
    assert g["verdict"] == "PASS" and g["leaks"] == 0 and g["recall"][1] == {"detected": 2, "files": 2} and g["recall"][2]["files"] == 2 and g["recall_overall"] == {"detected": 5, "files": 5, "missed_ids": []}, g
    assert g["reasons_ok"] == 5 and g["false_manual"] == 0
    for label, report in cases.items():  # one leak fails, whichever kind
        bad = base[:4] + [row("E", [1], cases[label][0])]
        assert p055_gate(bad, ins(20))["verdict"] == "FAIL" and p055_gate(bad, ins(20))["leak_ids"] == ["E"], label
    missed = base[:4] + [row("E", [1, 3], {**clean, "status": "incomplete", "request": None})]
    gm = p055_gate(missed, ins(20))
    assert gm["verdict"] == "FAIL" and gm["recall"][1] == {"detected": 1, "files": 2} and gm["recall"][3] == {"detected": 1, "files": 2} and gm["recall_overall"]["missed_ids"] == ["E"], gm  # per criterion and multi-criteria
    wrong = base[:4] + [ok("E", [1, 2], ["scanned_application"])]
    gw = p055_gate(wrong, ins(20))
    assert gw["verdict"] == "PASS" and gw["reasons_ok"] == 4 and gw["reasons_bad_ids"] == ["E"], "reason accuracy is reported, not a gate"
    assert ok("X", [3], ["language_unsure"])["reasons_ok"] is False and ok("X", [1], ["scanned_application", "detector_error"])["reasons_ok"] is True, "extra reasons allowed"
    assert p055_gate(base, ins(20, 2))["verdict"] == "PASS" and p055_gate(base, ins(20, 2))["ceiling_met"], "false manual intake at 2 passes"
    g3 = p055_gate(base, ins(20, 3))
    assert g3["verdict"] == "FAIL" and not g3["ceiling_met"] and g3["false_manual"] == 3, "at 3 it fails"
    assert p055_gate(base[:3], ins(20))["verdict"] == "NOT EVALUABLE" and p055_gate(base[:3], ins(20))["criteria_without_files"] == [4], "a criterion with no file cannot pass"
    assert p055_gate([], ins(20))["verdict"] == "NOT EVALUABLE" and p055_gate(base, [])["verdict"] == "NOT EVALUABLE"
    assert p055_gate(base[:3], ins(20, 3))["verdict"] == "FAIL", "a hard fail beats not evaluable"


if __name__ == "__main__":
    if sys.argv[1:2] == ["--self-check"]:  # B-325 counting only; no model call, no gold read
        rows = [{"submission": "A", "status_safety": "false_complete", "status_automation": None}, {"submission": "B", "status_safety": "safe", "status_automation": "not_automated"},
                {"submission": "C", "status_safety": "safe", "status_automation": "automated"}, {"submission": "D", "status_safety": "call_failed", "status_automation": "call_failed"}]
        assert status_counts(rows) == {"false_complete": 1, "false_complete_ids": ["A"], "gold_complete": 2, "automated": 1, "call_failed": 1}, status_counts(rows)
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:  # B-363 (@model-risk H1): never the real score files
            _OUT = Path(tmp) / "SUB-1-2-dev"
            assert [p.name for p in out_paths(True)] == ["SUB-1-2-dev-cache-rescore.json", "SUB-1-2-dev-cache-rescore.md"] and [p.name for p in out_paths(False)] == ["SUB-1-2-dev.json", "SUB-1-2-dev.md"]
            (Path(tmp) / "SUB-1-2-dev.json").write_text("{}")
            try:
                out_paths(False)
                raise AssertionError("a live run overwrote a score file")
            except SystemExit as stop:
                assert "never overwrites" in str(stop)
            assert out_paths(True)[0].name == "SUB-1-2-dev-cache-rescore.json", "a re-score still runs beside a live file"
        try:
            _no_call({}, {})
            raise AssertionError("re-score made a call")
        except SystemExit as stop:
            assert "no model call" in str(stop)
        held = {"complete": False, "status": "incomplete", "sprinklers": "yes", "fields": [{"field_id": "operations", "value": "apartments, 8 units"}, {"field_id": "tiv_building", "value": "$3,000,000"}]}
        assert route_used(held) == "senior_referral" and route_used({**held, "sprinklers": None}) == "hold" and route_used({**held, "complete": True}) == "senior_referral"  # P-049 R12
        office = {"complete": False, "status": "incomplete", "fields": [{"field_id": "operations", "value": "office"}, {"field_id": "tiv_building", "value": None}]}
        assert route_used(office) == "carrier_a", "P-050: a held file is scored by its provisional route"
        assert [judge(False, None, False, "not in documents"), judge(False, "x", False, "Not in documents."), judge(False, None, False, "missing, not given"),
                judge(True, None, False, "missing"), judge(False, "a", True, "a")] == ["hit", "miss", "miss", "not_credited", "hit"], "v2 rule; v1 lines unchanged"
        mk = lambda sid, mark, gold, used: {"submission": sid, "checks": {"route": mark}, "gold_route": gold, "route_used": used}
        good = [mk(f"S{i}", "hit", "carrier_a", "carrier_a") for i in range(18)] + [mk("M1", "miss", "carrier_a", "carrier_b"), mk("M2", "miss", "carrier_b", "no_match")]
        assert [gold_route_of(x) for x in ("Carrier A", "carrier_b — hold: x", "Senior referral (AG:38)", "TIV missing")] == ["carrier_a", "carrier_b", "senior_referral", None]
        assert route_gate(good) == {"unsafe": 0, "unsafe_ids": [], "hits": 18, "scored": 20, "files": 20, "evaluable": True, "pass": True, "verdict": "PASS"}, route_gate(good)
        bad = good[:19] + [mk("U", "miss", "senior_referral", "carrier_c")]
        assert route_gate([mk("N", "miss", "no_match", "carrier_a")])["unsafe"] == 1 and route_gate([mk("N", "miss", "senior_referral", "hold")])["unsafe"] == 0, "D-097 H3"
        assert route_gate(bad)["unsafe_ids"] == ["U"] and not route_gate(bad)["pass"], "one unsafe route fails the gate even at 18/20"
        low = good[:17] + [mk(f"X{i}", "miss", "carrier_a", "no_match") for i in range(3)]
        assert route_gate(low)["hits"] == 17 and not route_gate(low)["pass"] and route_gate(good[:18] + [{"submission": "F", "checks": {"route": "call_failed"}}])["scored"] == 18
        h2 = good[:17] + [mk("M", "miss", "carrier_a", "no_match")] + [{"submission": f"F{i}", "checks": {"route": "call_failed"}} for i in range(2)]
        assert route_gate(h2)["verdict"] == "NOT EVALUABLE" and route_gate(good[:18] + [mk("U", "miss", "no_match", "carrier_b"), {"submission": "F", "checks": {"route": "call_failed"}}])["verdict"] == "FAIL", "M4"
        assert not route_gate(h2)["evaluable"] and not route_gate(h2)["pass"], "@model-risk H2: 17/18 with 2 failed calls is not a pass"
        assert not route_gate(good[:18] + [{"submission": f"F{i}", "checks": {"route": "call_failed"}} for i in range(2)])["pass"], "18 hits, 2 unmarked: not evaluable"
        assert route_gate([mk("H", "miss", "hold", "carrier_a")])["unsafe"] == 0, "D-097: hold is not a gold route; v3 counted this"
        ops = "Restaurant. Breakfast and lunch counter service, 48 seats, dine-in and takeout. No alcohol of any kind. Flat-top, 2 fryers, 4-burner range, Type I hood with UL 300 suppression"
        items = "restaurant; no alcohol; 48 seats; flat-top; 2 fryers; 4-burner range; Type I hood; UL 300; counter service; dine-in; takeout"
        assert ops_items_hit(ops, items), "SUB-156: every item present; the gold connector 'under' is not an item"
        assert not ops_items_hit(ops.replace("No alcohol", "Full liquor"), items), "'no' counts: full liquor is not 'no alcohol'"
        assert not ops_items_hit(ops.replace("48 seats", "40 seats"), items) and not ops_items_hit(ops, "") and not ops_items_hit("", items)
        assert not ops_items_hit("Restaurant, 48 seats", "restaurant; 48 seats; live music"), "a dropped item is a miss"
        for answer, item in (("Full bar, alcohol served, no patio", "no alcohol"), ("4 fryers, 2-burner range", "2 fryers"), ("48 seats", "4 seats"),
                             ("Type II hood, I think", "Type I hood"), ("No liquor; beer and wine", "beer only")):
            assert not ops_items_hit(answer, item), ("check H2", answer, item)
        for answer, item in (("Alcohol: no. Live music Fridays", "no live music"), ("Beer and wine: no.", "beer and wine"), ("not 2 fryers, 4 fryers", "2 fryers")):
            assert not ops_items_hit(answer, item), ("look-again H2", answer, item)
        for answer in ("Live music - no", "Live music? No", "Live music (no)", "Live music no", "Live music – none"):
            assert not ops_items_hit(answer, "live music"), ("look-again H3", answer)
        assert not ops_items_hit("Beer and wine (none)", "beer and wine") and ops_items_hit("Beer and wine only, no liquor", "beer and wine only; no liquor"), "H3"
        assert ops_items_hit("No alcohol of any kind", "no alcohol") and ops_items_hit("Type I hood with UL 300", "Type I hood; UL 300")
        assert parse_gold("- Operations items: a; b\n- Operations: x")["operations items"] == "a; b"
        _v7_self_check()
        print("eval_holdout_v7 self-check ok")
        sys.exit(0)
    if sys.argv[1:2] == ["--check-gold"]:  # v6: format check only; reads the gold Scope lines of HOLDOUT_IDS, nothing else
        found, bad = gold_scopes(IDS)
        for sid, sc in found.items():
            print(sid, "parse ok:", "out of scope, criteria " + ", ".join(f"{c} {CRITERIA[c]}" for c in sc["criteria"]) if sc["out"] else "in scope")
        for line in bad:
            print(line, "parse FAIL")
        t = scope_totals(found)
        print(f"totals: {t['in']} in scope, {t['out']} out of scope; per criterion " + ", ".join(f"{c} {CRITERIA[c]}: {n}" for c, n in t["per_criterion"].items())
              + f"; two-criteria files: {len(t['two_criteria'])} ({', '.join(t['two_criteria']) or 'none'}); criterion 4 files: {len(t['criterion_4'])} ({', '.join(t['criterion_4']) or 'none'})")
        print(f"gold Scope lines: {len(found)} ok, {len(bad)} fail ({len(IDS)} files)")
        sys.exit(1 if bad or not IDS else 0)
    if "--write" not in sys.argv:  # D-096 item 4
        sys.exit("read-only: eval_holdout_v7 writes score files only with --write (or through regression_dev.py --write)")
    main()
