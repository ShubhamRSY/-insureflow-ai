"""T-120 operations-gate counter (D-134 C2 and C4). Stdlib only. Frozen and hashed before any T-120 gold exists.

Usage: count_ops_gate.py --v11 <v11 --write score .json> --runs <saved extractions dir> [--exclude SUB-n ...]
       count_ops_gate.py --self-check
Reads only. No rescoring, no reclassifying: the v11 operations mark is taken as written.
C2: in-scope file, v11 operations == miss, and no specific reason -> silent. Target 0 silent.
    Specific reason = non-empty `reason` text on the operations row, or an open conflict (resolution != resolved)
    whose `field` is operations or cooking. policy_review / POLICY_NOTE never counts.
C4: operations value present on >= 18 in-scope files and v11 operations hits >= 15 (in-scope only).
"""
import argparse
import json
import sys
from pathlib import Path

POLICY_NOTE = "Operations is always checked by the underwriter (T-027 C1, D-135)"  # copy of prepare.POLICY_NOTE
PRESENT_MIN, HITS_MIN = 18, 15


def specific_reason(run: dict) -> str:
    """The text of the first specific reason on the operations row or an open operations/cooking conflict; '' if none."""
    row = next((r for r in run.get("fields") or [] if r.get("field_id") == "operations"), {})
    reason = (row.get("reason") or "").strip()
    if reason and reason != POLICY_NOTE:  # ponytail: a reason equal to the policy note is treated as policy, not specific
        return reason
    for c in run.get("conflicts") or []:
        if c.get("resolution") != "resolved" and c.get("field") in ("operations", "cooking"):
            return f"open {c['field']} conflict"
    return ""


def count(v11: dict, runs: dict) -> dict:
    """v11: parsed score json. runs: {submission: saved run}. Returns rows and verdicts."""
    rows = []
    for r in v11["submissions"]:
        if r.get("scope") != "in":
            continue
        sid = r["submission"]
        mark = (r.get("checks") or {}).get("operations", "call_failed")
        run = runs.get(sid)
        if run is None:
            raise SystemExit(f"no saved run for {sid}; nothing counted")
        ops = next((x for x in run.get("fields") or [] if x.get("field_id") == "operations"), {})
        why = specific_reason(run)
        rows.append({"sid": sid, "mark": mark, "present": bool(ops.get("value")), "reason": why,
                     "silent": mark == "miss" and not why})
    silent = sum(x["silent"] for x in rows)
    present = sum(x["present"] for x in rows)
    hits = sum(x["mark"] in ("hit", "hit (needs review)") for x in rows)
    return {"rows": rows, "files": len(rows), "silent": silent, "present": present, "hits": hits,
            "c2": silent == 0, "c4": present >= PRESENT_MIN and hits >= HITS_MIN}


def report(res: dict) -> str:
    out = [f"{'file':<9}{'v11 ops':<20}{'present':<9}{'specific reason':<40}silent"]
    for x in res["rows"]:
        out.append(f"{x['sid']:<9}{x['mark']:<20}{'yes' if x['present'] else 'no':<9}{(x['reason'] or 'none')[:38]:<40}{'YES' if x['silent'] else 'no'}")
    out.append(f"in-scope files {res['files']}; silent {res['silent']}; present {res['present']}; hits {res['hits']}")
    out.append(f"C2 (silent errors == 0): {'PASS' if res['c2'] else 'FAIL'}")
    out.append(f"C4 (present >= {PRESENT_MIN}/20 and hits >= {HITS_MIN}/20): {'PASS' if res['c4'] else 'FAIL'}")
    return "\n".join(out)


def self_check() -> None:
    def run(value="x", reason=None, policy=True, conflicts=()):
        return {"fields": [{"field_id": "operations", "value": value, "reason": reason, **({"policy_review": True} if policy else {})}],
                "conflicts": list(conflicts)}
    def one(mark, rn):
        return count({"submissions": [{"submission": "S", "scope": "in", "checks": {"operations": mark}}]}, {"S": rn})["rows"][0]
    assert one("miss", run())["silent"]                                    # miss, no reason
    assert one("miss", run(reason=POLICY_NOTE))["silent"]                  # policy text only
    assert not one("miss", run(reason="operations may be missing: no cooking"))["silent"]
    assert not one("miss", run(conflicts=[{"field": "cooking"}]))["silent"]
    assert one("miss", run(conflicts=[{"field": "cooking", "resolution": "resolved"}]))["silent"]
    assert one("miss", run(conflicts=[{"field": "sales"}]))["silent"]
    assert not one("hit", run())["silent"]
    def many(hits, present):
        subs = [{"submission": f"S{i}", "scope": "in", "checks": {"operations": "hit" if i < hits else "miss"}} for i in range(20)]
        rs = {f"S{i}": run(value="x" if i < present else None, reason="r") for i in range(20)}
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
    v11 = json.loads(Path(a.v11).read_text())
    runs = {p.stem: json.loads(p.read_text()) for p in Path(a.runs).glob("SUB-*.json")}
    res = count(v11, runs)
    print(report(res))
    sys.exit(0 if res["c2"] and res["c4"] else 1)


if __name__ == "__main__":
    main()
