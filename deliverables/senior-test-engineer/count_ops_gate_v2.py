"""T-027 operations-gate counter v2 (B-491, D-141). Stdlib only. Frozen and hashed before any T-121 gold exists.
v1 (`count_ops_gate.py`, sha256 f942010d...9aa1) stays frozen and unchanged; it scored T-120.

Usage: count_ops_gate_v2.py --v11 <score .json> --runs <saved extractions dir>
       count_ops_gate_v2.py --self-check
Reads only. No rescoring, no reclassifying: the scorer's operations mark is taken as written.
C2: in-scope file, operations == miss, and no specific reason -> silent. Target 0 silent.
    v2 change (memo T-120 M2): a reason counts only if it names the item or its evidence. Specific is one of:
      - "operations may be missing: <items>" with at least one item named;
      - a cooking reason ("cooking ...", "the cooking line ..."): names the cooking item and its line;
      - an open conflict (resolution != resolved) whose field is operations or cooking: names the field and both values.
    Anything else is generic and does not count: "value is not in the cited text (translated or reworded)",
    the policy note, address/scan notes, and any text this counter does not know (fail closed; shown in the report).
C4: operations value present on >= 18 in-scope files and operations hits >= 15 (in-scope only). Unchanged from v1.
"""
import argparse
import json
import re
import sys
from pathlib import Path

PRESENT_MIN, HITS_MIN = 18, 15
ITEM_SHAPES = (
    re.compile(r"^operations may be missing:\s*\S"),  # prepare.OPS_MISSING with the items it found
    re.compile(r"^(?:the )?cooking\b"),  # prepare.REASON_COOKING / _COPIED / _CONFLICT
)


def specific_reason(run: dict) -> tuple[str, str]:
    """(specific, generic): the first reason that names the item, and the reason text that did not count."""
    row = next((r for r in run.get("fields") or [] if r.get("field_id") == "operations"), {})
    parts = [p.strip() for p in (row.get("reason") or "").split(";") if p.strip()]
    named = [p for p in parts if any(s.match(p) for s in ITEM_SHAPES)]
    generic = "; ".join(p for p in parts if p not in named)
    if named:
        return named[0], generic
    for c in run.get("conflicts") or []:
        if c.get("resolution") != "resolved" and c.get("field") in ("operations", "cooking"):
            return f"open {c['field']} conflict", generic
    return "", generic


def count(score: dict, runs: dict) -> dict:
    """score: parsed score json. runs: {submission: saved run}. Returns rows and verdicts."""
    rows = []
    for r in score["submissions"]:
        if r.get("scope") != "in":
            continue
        sid = r["submission"]
        mark = (r.get("checks") or {}).get("operations", "call_failed")
        run = runs.get(sid)
        if run is None:
            raise SystemExit(f"no saved run for {sid}; nothing counted")
        ops = next((x for x in run.get("fields") or [] if x.get("field_id") == "operations"), {})
        why, generic = specific_reason(run)
        rows.append({"sid": sid, "mark": mark, "present": bool(ops.get("value")), "reason": why, "generic": generic,
                     "silent": mark == "miss" and not why})
    silent = sum(x["silent"] for x in rows)
    present = sum(x["present"] for x in rows)
    hits = sum(x["mark"] in ("hit", "hit (needs review)") for x in rows)
    return {"rows": rows, "files": len(rows), "silent": silent, "present": present, "hits": hits,
            "c2": silent == 0, "c4": present >= PRESENT_MIN and hits >= HITS_MIN}


def report(res: dict) -> str:
    out = [f"{'file':<9}{'ops mark':<20}{'present':<9}{'specific reason (v2)':<40}{'silent':<8}not counted"]
    for x in res["rows"]:
        out.append(f"{x['sid']:<9}{x['mark']:<20}{'yes' if x['present'] else 'no':<9}{(x['reason'] or 'none')[:38]:<40}"
                   f"{'YES' if x['silent'] else 'no':<8}{x['generic'][:60]}")
    out.append(f"in-scope files {res['files']}; silent {res['silent']}; present {res['present']}; hits {res['hits']}")
    out.append(f"C2 v2 (silent errors == 0, reason must name the item): {'PASS' if res['c2'] else 'FAIL'}")
    out.append(f"C4 (present >= {PRESENT_MIN}/20 and hits >= {HITS_MIN}/20): {'PASS' if res['c4'] else 'FAIL'}")
    return "\n".join(out)


def self_check() -> None:
    def run(value: "str | None" = "x", reason=None, conflicts=()):
        return {"fields": [{"field_id": "operations", "value": value, "reason": reason, "policy_review": True}], "conflicts": list(conflicts)}

    def one(mark, rn):
        return count({"submissions": [{"submission": "S", "scope": "in", "checks": {"operations": mark}}]}, {"S": rn})["rows"][0]

    reworded = "value is not in the cited text (translated or reworded)"
    policy = "Operations is always checked by the underwriter (T-027 C1, D-135)"
    assert one("miss", run())["silent"]                                                  # no reason
    assert one("miss", run(reason=reworded))["silent"]                                   # M2: generic, names no item
    assert one("miss", run(reason=policy))["silent"]                                     # policy text only
    assert one("miss", run(reason="operations may be missing: "))["silent"]              # the template with no item
    assert one("miss", run(reason="something the counter does not know"))["silent"]      # unknown text fails closed
    assert one("miss", run(reason="address check: no five-digit ZIP; the page needs a person"))["silent"]
    assert not one("miss", run(reason="operations may be missing: liquor, bar"))["silent"]
    assert not one("miss", run(reason=f"{reworded}; operations may be missing: fryer"))["silent"]
    assert not one("miss", run(reason="cooking line copied from the application (P-075); check the other documents for cooking"))["silent"]
    assert not one("miss", run(reason="cooking: the documents disagree"))["silent"]
    assert not one("miss", run(reason="the cooking line contains a negation word (P-031): the underwriter records present or none"))["silent"]
    assert not one("miss", run(conflicts=[{"field": "operations", "resolution": "unresolved"}]))["silent"]
    assert one("miss", run(conflicts=[{"field": "cooking", "resolution": "resolved"}]))["silent"]
    assert one("miss", run(conflicts=[{"field": "sales"}]))["silent"]
    assert not one("hit", run(reason=reworded))["silent"]                                # only a miss can be silent
    assert one("miss", run(reason=f"{reworded}; operations may be missing: fryer"))["generic"] == reworded

    def many(hits, present):
        subs = [{"submission": f"S{i}", "scope": "in", "checks": {"operations": "hit" if i < hits else "miss"}} for i in range(20)]
        rs = {f"S{i}": run(value="x" if i < present else None, reason="operations may be missing: bar") for i in range(20)}
        return count({"submissions": subs + [{"submission": "O", "scope": "out", "checks": {}}]}, {**rs, "O": run()})
    assert many(15, 18)["c4"] and not many(14, 18)["c4"] and not many(15, 17)["c4"]
    assert many(15, 18)["files"] == 20 and many(15, 18)["c2"]
    print("SELF-CHECK PASS")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v11")
    ap.add_argument("--runs")
    ap.add_argument("--self-check", action="store_true")
    a = ap.parse_args()
    if a.self_check:
        return self_check()
    if not (a.v11 and a.runs):
        ap.error("--v11 and --runs are required")
    score = json.loads(Path(a.v11).read_text())
    runs = {p.stem: json.loads(p.read_text()) for p in Path(a.runs).glob("SUB-*.json")}
    res = count(score, runs)
    print(report(res))
    sys.exit(0 if res["c2"] and res["c4"] else 1)


if __name__ == "__main__":
    main()
