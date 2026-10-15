"""Step 4 — point hazard rank. Not a price, not a decline, not a carrier pick.

# ponytail: fixed points, no fit. Replace weights when loss labels exist.

P-015 (D-040: S3 H1 M1 T2 V3 W1 A1 E2; built per D-070). Synthetic. Weights are placeholders, nothing is refit.
Entry point for the page: score_run(saved_run). It returns either a score or "not scored" with a reason, never a number
for a file that is not scored. score(facts) is the inner table and is kept for old callers.

Run: .venv/bin/python underwriting_pipeline/models/points.py   (LLM_* unset)
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ai"))
import prepare  # noqa: E402  (HAZARD_TERMS and NO_WORDS live there, one list; nothing is called)

# code -> points. Range 0 to 80 (LOSS_HISTORY was removed: no claim fact is extracted).
TABLE = {"FRAME_CONSTRUCTION": 15, "COOKING": 25, "HABITATIONAL": 15, "CONTRACTING": 15, "TIV_OVER_1M": 10}
CODES = tuple(TABLE)
LOSS_LINE = "Loss history: not scored"  # shown on every file; it does not mean no losses
HOOD_WORDS = {"stated": "stated", "none": "stated none", "not_stated": "not stated"}
# The facts() word lists (moved from app/workbench.py, unchanged). They are part of the version.
HABITATIONAL_WORDS = ("habitational", "apartment", "flats")
CONTRACTING_WORDS = ("contractor", "painting")
# Status -> reason when not scored. "complete" and "complete — review pending" (P-041) are the scored statuses.
NOT_SCORED = {
    "extraction_failed": "extraction failed",
    "all_values_rejected": "every value was rejected",  # D-024; the status is decided, T-070 puts it in the code
}


def _hash_version() -> str:
    """V3 today = V2: a hash of the table, the fact word lists and the cooking term list, as PROMPT_VERSION is hashed."""
    rules = [TABLE, HABITATIONAL_WORDS, CONTRACTING_WORDS, prepare.HAZARD_TERMS, prepare.NO_WORDS.pattern, prepare.ITEM_SPLIT.pattern, prepare.NONE_AFTER.pattern, prepare.NEG_WORD.pattern, prepare.REASON_COOKING]  # P-027, P-031: the rules move the version
    return hashlib.sha256(json.dumps(rules, sort_keys=True).encode()).hexdigest()[:12]


# V3: hash + git commit hash of the rules and points code. P-017 is not built, so the commit slot is None today and
# the id reads "points-<hash>+git:not-recorded". Nothing shells out to git, so an environment change cannot move it.
GIT_COMMIT: str | None = None
POINTS_VERSION = f"points-{_hash_version()}+git:{GIT_COMMIT or 'not-recorded'}"


def facts(report: dict) -> dict:
    """The inputs to score(), from a saved run. Moved from workbench.py; cooking is no longer read from `operations` (H1/S3)."""
    by = {row["field_id"]: (row["value"] or "") for row in report.get("fields") or []}
    ops = by.get("operations", "").lower()
    tiv = "".join(ch for ch in by.get("tiv_building", "") if ch.isdigit())
    cooking = report.get("cooking") or {}  # a run saved before P-015 has no key: not_stated
    return {
        "cooking_equipment": cooking.get("equipment") or {"state": "not_stated"},
        "hood_suppression": cooking.get("hood_suppression") or {"state": "not_stated"},
        "habitational": any(word in ops for word in HABITATIONAL_WORDS),
        "contracting": any(word in ops for word in CONTRACTING_WORDS),
        "construction": by.get("construction", "").lower(),
        "tiv": int(tiv) if tiv else 0,
    }


def cooking_line(fact: dict) -> str:
    """Three outcomes, never a silent zero."""
    state = fact.get("state", "not_stated")
    call = fact.get("call")
    if call:  # B-278 (D-073): the underwriter's recorded call on a needs-review line
        said = f"underwriter recorded {call['call']} ({call['underwriter_id']}: {call['reason']})"
        return (f"COOKING +{TABLE['COOKING']} — {said}" if state == "yes" else f"Cooking: {said}") + f": \"{fact.get('quote')}\""
    denied = f"; stated not present: {', '.join(fact['negated'])}" if fact.get("negated") else ""  # P-027 (D-071)
    if state == "yes":
        return f"COOKING +{TABLE['COOKING']} — {', '.join(fact.get('terms') or ['hazard'])} stated{denied}: \"{fact.get('quote')}\""
    if state == "needs_review":  # P-030 (D-073): no cooking points until the underwriter records the call
        return f"Cooking: needs review — \"{fact.get('quote')}\""
    if state == "none":
        return "Cooking: stated none" + (f" — \"{fact.get('quote')}\"" if fact.get("quote") else "")
    if state == "other":
        return f"Cooking: not scored — equipment stated is not a fryer or open flame{denied}: \"{fact.get('quote')}\""
    return "Cooking: not scored — no cooking equipment stated in the file"


def score(f: dict) -> dict:
    points, reasons = 0, []
    if f.get("construction") == "frame":
        points += TABLE["FRAME_CONSTRUCTION"]
        reasons.append("FRAME_CONSTRUCTION")
    if (f.get("cooking_equipment") or {}).get("state") == "yes":  # only a stated, non-negated fryer or open flame
        points += TABLE["COOKING"]
        reasons.append("COOKING")
    if f.get("habitational"):
        points += TABLE["HABITATIONAL"]
        reasons.append("HABITATIONAL")
    if f.get("contracting"):
        points += TABLE["CONTRACTING"]
        reasons.append("CONTRACTING")
    if (f.get("tiv") or 0) > 1_000_000:
        points += TABLE["TIV_OVER_1M"]
        reasons.append("TIV_OVER_1M")
    return {"points": points, "reason_codes": reasons}


def not_scored_reason(report: dict) -> str | None:
    """None when the file is scored. Otherwise the plain reason. Unknown, missing, or empty never becomes a number."""
    status = report.get("status") if isinstance(report, dict) else None
    if status in NOT_SCORED:
        why = NOT_SCORED[status]
        return f"{why}: {report.get('error')}" if status == "extraction_failed" and report.get("error") else why
    if status == "incomplete":
        conflicts = [c.get("field") for c in report.get("conflicts") or [] if c.get("resolution") != "resolved"]
        parts = []
        if report.get("missing"):
            parts.append("missing " + ", ".join(report["missing"]))
        parts += [f"open conflict on {field}" for field in conflicts]
        parts += [f"asked of the producer: {item}" for item in report.get("extra") or []]
        return "file incomplete: " + ("; ".join(parts) or "see status")
    if status in ("complete", prepare.REVIEW_PENDING) and any(r.get("value") for r in report.get("fields") or []):
        return None  # P-041 (D-088): review pending is scored as complete was; the card says what is pending
    return "unknown status" if status not in ("complete", prepare.REVIEW_PENDING) else "file complete but holds no values"


def score_run(report: dict) -> dict:
    """What the page shows and the decision row saves. Keys: scored, points (None if not scored), reason_codes, not_scored_reason,
    lines (display), cooking, hood_suppression, points_version. A mark on a code does not change any of these (W1)."""
    why = not_scored_reason(report)
    f = facts(report) if isinstance(report, dict) else facts({})
    hood = f["hood_suppression"]
    hood_line = f"Hood and suppression: {HOOD_WORDS.get(hood.get('state'), 'not stated')}" + (f" — \"{hood.get('quote')}\"" if hood.get("quote") else "")
    lines = [LOSS_LINE, cooking_line(f["cooking_equipment"]), hood_line]
    if isinstance(report, dict) and report.get("status") == "extraction_failed":  # D-079 (B-295): nothing was read
        lines = [f"{label}: Not read — extraction failed" for label in ("Loss history", "Cooking", "Hood and suppression")]
    out = {"scored": why is None, "points": None, "reason_codes": [], "not_scored_reason": why and f"Not scored — {why}",
           "lines": lines, "points_version": POINTS_VERSION}
    if why is None and f["cooking_equipment"].get("state") == "needs_review":  # B-278 (D-073): never a normal number
        out.update(scored=False, provisional=True, not_scored_reason="Provisional — cooking not scored")
    elif why is None:
        out.update(score(f))
    return out


def apply_cooking_call(report: dict, call: dict | None) -> dict:
    """B-278 (D-073): a copy of the run with the underwriter's cooking call in place of a needs-review equipment fact.
    Only a call for this run (same run_hash) counts; otherwise the run is returned unchanged (still provisional)."""
    eq = ((report.get("cooking") or {}).get("equipment") or {})
    if not call or eq.get("state") != "needs_review" or call.get("run_hash") != report.get("saved_hash"):
        return report
    state = "yes" if call["call"] == "present" else "none"
    cooking = {**(report.get("cooking") or {}), "equipment": {**eq, "state": state, "terms": ["fryer or open flame"] if state == "yes" else [], "call": call}}
    return {**report, "cooking": cooking}


if __name__ == "__main__":
    def run(ops: str = "restaurant", equipment: dict | None = None, **kw) -> dict:
        base = {"status": "complete", "missing": [], "conflicts": [], "extra": [],
                "fields": [{"field_id": "operations", "value": ops}, {"field_id": "tiv_building", "value": "800000"},
                           {"field_id": "construction", "value": "masonry"}]}
        if equipment is not None:
            base["cooking"] = {"equipment": equipment, "hood_suppression": {"state": "not_stated"}}
        return {**base, **kw}

    yes = {"state": "yes", "terms": ["fryer"], "quote": "two floor fryers"}
    none_ = {"state": "none", "terms": [], "quote": "none"}
    assert "LOSS_HISTORY" not in TABLE and sum(TABLE.values()) == 80
    # Wording pair: swap the class or cuisine word and the points do not move; stated hazard moves them; stated none gives none.
    words = ["taco", "taqueria", "pizzeria", "barbecue", "steakhouse", "catering, commercial cooking", "restaurant",
             "restaurant supply wholesale", "apartamentos", "office, no kitchen", "office, no fryer", "restaurant with fryer",
             "taqueria with fryer", "restaurante con freidora", "childhood education office", "office with fryer"]
    for w in words:
        for eq, want in ((None, 0), ({"state": "not_stated"}, 0), ({"state": "other", "terms": [], "quote": "microwave"}, 0), (none_, 0), (yes, 25)):
            got = score_run(run(w, eq))
            assert got["scored"] and got["points"] == want, (w, eq, got)  # "apartamentos" gives 0: HABITATIONAL reads "apartment" only (B-064)
            assert ("COOKING" in got["reason_codes"]) == (want == 25)
    assert "not scored — no cooking equipment stated" in score_run(run("restaurant"))["lines"][1]
    assert score_run(run("office, no fryer", none_))["lines"][1].startswith("Cooking: stated none")
    # P-027: the negated item is named and the quote is shown.
    p27 = {"state": "yes", "terms": ["charbroiler", "grill"], "negated": ["fryer"], "quote": "no fryer; gas grill and charbroiler"}
    assert cooking_line(p27) == 'COOKING +25 — charbroiler, grill stated; stated not present: fryer: "no fryer; gas grill and charbroiler"', cooking_line(p27)
    assert cooking_line({"state": "none", "negated": ["fryer"], "quote": "fryer: none"}) == 'Cooking: stated none — "fryer: none"' 
    nr = {"state": "needs_review", "terms": [], "quote": "no fryer but charbroiler"}
    assert cooking_line(nr) == 'Cooking: needs review — "no fryer but charbroiler"'
    assert "COOKING" not in score_run(run(cooking={"equipment": nr, "hood_suppression": {"state": "not_stated"}}))["reason_codes"], "P-029: no points"
    # D-079 (B-295): a failed extraction never reads "none stated".
    failed = score_run({"status": "extraction_failed", "fields": []})
    assert failed["points"] is None and all(line.endswith("Not read — extraction failed") for line in failed["lines"]), failed["lines"]
    assert not any("stated" in line for line in failed["lines"])
    # B-278 (D-073): provisional until the underwriter records the call for this run; points apply only after it.
    pr = run(cooking={"equipment": nr, "hood_suppression": {"state": "not_stated"}}, saved_hash="h1")
    got = score_run(pr)
    assert got["points"] is None and got["not_scored_reason"] == "Provisional — cooking not scored" and got.get("provisional")
    c = {"call": "present", "reason": "fryer seen on photos", "underwriter_id": "UW-001", "run_hash": "h1"}
    assert "COOKING" in score_run(apply_cooking_call(pr, c))["reason_codes"] and score_run(apply_cooking_call(pr, c))["points"] is not None
    assert "COOKING" not in score_run(apply_cooking_call(pr, {**c, "call": "none"}))["reason_codes"]
    assert score_run(apply_cooking_call(pr, {**c, "run_hash": "old"}))["points"] is None, "a call for another run does not count"
    assert score_run(run("x", yes))["lines"][1].startswith("COOKING +25 — fryer stated:")
    # M1: a complete file with no cooking fact keeps its number. H1: hood gives no points either way.
    h = {"hood_suppression": {"state": "stated", "quote": "wet chemical"}, "equipment": {"state": "not_stated"}}
    assert score_run(run(cooking=h))["points"] == 0 and "stated" in score_run(run(cooking=h))["lines"][2]
    assert score_run(run(cooking={"equipment": yes, "hood_suppression": {"state": "none"}}))["points"] == 25
    # Each remaining code fires from a report (B-067).
    ex = run("apartments, painting", yes, fields=[{"field_id": "operations", "value": "apartments, painting"},
         {"field_id": "tiv_building", "value": "$1,200,000"}, {"field_id": "construction", "value": "Frame"}])
    assert sorted(score_run(ex)["reason_codes"]) == sorted(CODES) and score_run(ex)["points"] == 80
    # Failed, incomplete, unknown, empty and rejected reports return no number, and say why.
    bad = [{"status": "extraction_failed", "error": "HTTP 429"}, {"status": "incomplete", "missing": ["tiv_building"]},
           {"status": "incomplete", "conflicts": [{"field": "premises_address"}]}, {"status": "all_values_rejected"},
           {"status": "weird"}, {}, {"status": "complete", "fields": []}, {"status": "complete", "fields": [{"field_id": "operations", "value": None}]}]
    for r in bad:
        got = score_run(r)
        assert not got["scored"] and got["points"] is None and got["reason_codes"] == [] and got["not_scored_reason"].startswith("Not scored — "), r
        assert got["lines"][0] == (LOSS_LINE if r.get("status") != "extraction_failed" else "Loss history: Not read — extraction failed")
    assert "HTTP 429" in score_run(bad[0])["not_scored_reason"] and "tiv_building" in score_run(bad[1])["not_scored_reason"]
    assert "premises_address" in score_run(bad[2])["not_scored_reason"]
    # A resolved conflict does not block. A run saved before P-015 (no cooking key) reads as not stated.
    assert score_run(run(conflicts=[{"field": "x", "resolution": "resolved"}]))["scored"]
    assert score_run({**run(), "status": prepare.REVIEW_PENDING})["scored"], "P-041: review pending is scored as complete was"
    assert score_run(run())["lines"][1].endswith("no cooking equipment stated in the file")
    # The version does not move with the environment; it moves with the table or a term list.
    import os
    before = POINTS_VERSION
    os.environ["LLM_MODEL"] = "other-model"
    assert before == f"points-{_hash_version()}+git:not-recorded" == POINTS_VERSION
    TABLE["COOKING"] = 26
    assert _hash_version() != before.split("-")[1].split("+")[0]
    TABLE["COOKING"] = 25
    assert "decline" not in score_run(run()) and "premium" not in score_run(run())
    print("points ok", POINTS_VERSION)
