"""Score prepare.process_submission against the senior-underwriter gold set.

Run: python underwriting_pipeline/ai/eval_gold.py
Writes deliverables/ai-engineer/evals/SUB-007-016-field-accuracy.md
Synthetic submissions only. Not a production approval.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare

ROOT = Path(__file__).resolve().parents[2]
INBOX = ROOT / "simulation" / "inbox"
GOLD = ROOT / "deliverables" / "senior-underwriter" / "gold-set"
OUT = ROOT / "deliverables" / "ai-engineer" / "evals" / "SUB-007-016-field-accuracy.md"
IDS = [f"SUB-{n:03d}" for n in range(7, 17)]
STOP = {"with", "and", "the", "that", "this", "from", "for", "not"}
CUES = {
    "SUB-007": "Carrier A",
    "SUB-008": "Carrier A",
    "SUB-009": "Carrier A",
    "SUB-010": "Carrier B",
    "SUB-011": "Do not match",
    "SUB-012": "location schedule",
    "SUB-013": "Do not match",
    "SUB-014": "Do not pick",
    "SUB-015": "both pairs",
    "SUB-016": "No placeholder",
}
ROUTE = {
    "SUB-007": "carrier_a",
    "SUB-008": "carrier_a",
    "SUB-009": "carrier_a",
    "SUB-010": "carrier_b",
    "SUB-011": "hold",
    "SUB-012": "hold",
    "SUB-013": "hold",
    "SUB-014": "hold",
    "SUB-015": "hold",
    "SUB-016": "no_match",
}
FIVE = (
    "cooking equipment",
    "hood and fire suppression",
    "sprinklers",
    "liquor sales",
    "hours",
)


def parse_gold(text: str) -> dict:
    out = {}
    for raw in text.splitlines():
        if not raw.startswith("- ") or ":" not in raw:
            continue
        key, val = raw[2:].split(":", 1)
        out[key.strip().lower()] = val.strip()
    return out


def words(text: str) -> list[str]:
    raw = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in raw if w not in STOP and (len(w) >= 4 or w.isdigit())]


def field_map(report: dict) -> dict:
    return {row["field_id"]: row for row in report["fields"]}


def expected_conflict_fields(line: str) -> set[str]:
    low = line.lower()
    if low == "none" or low.startswith("loss runs show") or low.startswith("must ask"):
        return set()
    found = set()
    if "premises" in low or "address" in low:
        found.add("premises_address")
    if "sales" in low:
        found.add("sales_or_payroll")
    if "square" in low:
        found.add("square_feet")
    return found


def loss_should_be_missing(missing: str) -> bool:
    low = missing.lower()
    return "loss" in low and low != "none"


def cite_ok(folder: Path, row: dict) -> bool | None:
    if not row.get("value") or row.get("start") is None:
        return None
    source = row.get("source")
    if not source:
        return False
    text = (folder / source).read_text()
    return text[row["start"] : row["end"]] == row["value"]


def route_of(folder: Path, report: dict) -> str:
    by = field_map(report)
    ops = (by["operations"]["value"] or "").lower()
    if any(token in ops for token in ("firework", "explosive", "nightclub")):
        return "no_match"
    if re.search(r"\bbar\b", ops):
        return "no_match"
    if any(c.get("resolution") != "resolved" for c in report["conflicts"]):
        return "hold"
    if not by["loss_run_valued_through"]["value"]:
        return "hold"
    if any("location schedule" in item for item in report["extra"]):
        return "hold"
    runs = (folder / "loss-runs.md").read_text().lower() if (folder / "loss-runs.md").exists() else ""
    clean = "zero claims" in runs or "none open" in runs or "no claims" in runs
    if "restaurant" in ops or "fryer" in ops or ("contractor" in ops and "no roof" in ops):
        return "carrier_b" if clean else "hold"
    if "habitational" in ops or "apartment" in ops:
        sprinklered = "sprinkler" in ops and "yes" in ops
        return "carrier_c" if sprinklered else "hold"
    tiv_raw = by["tiv_building"]["value"] or ""
    tiv = int(tiv_raw) if tiv_raw.isdigit() else None
    office_like = any(token in ops for token in ("office", "dry retail", "wholesale"))
    if office_like and tiv is not None and tiv <= 5_000_000:
        return "carrier_a"
    return "hold"


def main() -> None:
    if (INBOX / "SUB-011" / "loss-runs.md").exists() or (INBOX / "SUB-014" / "reply.md").exists():
        raise SystemExit(
            "Refusing to score. Gold SUB-007–SUB-016 is the original pack. "
            "Hold this round's producer replies out of the inbox before re-running."
        )
    rows_out = []
    tallies = {
        "named_insured": [],
        "premises_address": [],
        "operations": [],
        "loss_run_valued_through": [],
        "schedule_request": [],
        "conflict_fields": [],
        "conflict_values": [],
        "resolution": [],
        "status": [],
        "restaurant_questions": [],
        "citation": [],
        "carrier_route": [],
    }
    details = []
    for sub in IDS:
        folder = INBOX / sub
        gold = parse_gold((GOLD / f"{sub}.md").read_text())
        if CUES[sub] not in gold["expected recommendation"]:
            raise SystemExit(f"gold cue drifted for {sub}")
        report = prepare.process_submission(folder)
        by = field_map(report)
        got_conflicts = {c["field"] for c in report["conflicts"]}
        expect_conflicts = expected_conflict_fields(gold["conflict"])

        name_hit = by["named_insured"]["value"] == gold["named insured"]
        if ";" in gold["premises"]:
            parts = [part.strip().split(" ", 1)[1].strip() for part in gold["premises"].split(";")]
            blob = " | ".join(
                v["value"]
                for c in report["conflicts"]
                if c["field"] == "premises_address"
                for v in c["values"]
            )
            prem_hit = all(part in blob for part in parts)
        else:
            prem_hit = by["premises_address"]["value"] == gold["premises"]
        ops_words = words(gold["operations"])
        ops_text = (by["operations"]["value"] or "").lower()
        ops_hit = bool(ops_words) and all(word in ops_text for word in ops_words)
        loss_missing = by["loss_run_valued_through"]["value"] is None
        loss_hit = loss_missing == loss_should_be_missing(gold["missing"])
        schedule_expected = "schedule" in gold["missing"].lower()
        schedule_got = any("location schedule" in item for item in report["extra"])
        schedule_hit = schedule_got == schedule_expected
        conflict_hit = got_conflicts == expect_conflicts
        value_hits = []
        if sub == "SUB-014":
            vals = {
                (v["value"], v["source"])
                for c in report["conflicts"]
                for v in c["values"]
            }
            value_hits.append(
                (
                    "12 Nogal St, San Antonio, TX 78212",
                    "application.md",
                )
                in vals
                and (
                    "120 Nogal St, San Antonio, TX 78212",
                    "schedule.csv",
                )
                in vals
            )
        if sub == "SUB-015":
            vals = {
                (c["field"], v["value"], v["source"])
                for c in report["conflicts"]
                for v in c["values"]
            }
            value_hits.append(
                ("sales_or_payroll", "880000", "application.md") in vals
                and ("sales_or_payroll", "300000", "email.md") in vals
                and ("square_feet", "3000", "application.md") in vals
                and ("square_feet", "4500", "schedule.csv") in vals
            )
        value_hit = all(value_hits) if value_hits else None
        res_hits = [
            c.get("resolution") == "unresolved" and c.get("resolved_value") is None
            for c in report["conflicts"]
            if c["field"] in expect_conflicts
        ]
        res_hit = all(res_hits) if res_hits else None
        status = gold["status"].lower()
        if status == "complete" or status.startswith("complete on fields"):
            status_hit = not report["missing"] and not report["conflicts"]
        elif status == "incomplete":
            status_hit = report["complete"] is False
        elif status == "conflict":
            status_hit = bool(report["conflicts"]) and report["complete"] is False
        else:
            status_hit = False
        rest_hit = None
        if "cooking equipment" in gold["conflict"].lower() or "must ask" in gold["conflict"].lower():
            rest_hit = all(item in report["extra"] for item in FIVE)
        cites = [cite_ok(folder, row) for row in report["fields"]]
        cite_flags = [flag for flag in cites if flag is not None]
        cite_hit = all(cite_flags) if cite_flags else None
        routed = route_of(folder, report)
        route_hit = routed == ROUTE[sub]

        pairs = {
            "named_insured": name_hit,
            "premises_address": prem_hit,
            "operations": ops_hit,
            "loss_run_valued_through": loss_hit,
            "schedule_request": schedule_hit,
            "conflict_fields": conflict_hit,
            "conflict_values": value_hit,
            "resolution": res_hit,
            "status": status_hit,
            "restaurant_questions": rest_hit,
            "citation": cite_hit,
            "carrier_route": route_hit,
        }
        for key, hit in pairs.items():
            if hit is None or key == "resolution":
                continue
            tallies[key].append(hit)
        tallies["resolution"].extend(res_hits)
        details.append(
            {
                "submission": sub,
                "extracted_operations": by["operations"]["value"],
                "hits": {key: hit for key, hit in pairs.items()},
                "routed": routed,
                "expected_route": ROUTE[sub],
                "conflicts": report["conflicts"],
                "missing": report["missing"],
                "extra": report["extra"],
            }
        )
        rows_out.append(pairs)

    def frac(key: str) -> str:
        hits = tallies[key]
        if not hits:
            return "n/a"
        good = sum(1 for hit in hits if hit)
        return f"{good}/{len(hits)} ({good / len(hits):.0%})"

    lines = [
        "# Extraction accuracy — SUB-007 through SUB-016",
        "",
        "- Author: @ai-engineer",
        "- Reviewed with: @senior-underwriter",
        "- Date: 2026-10-09",
        "- Synthetic gold set only. Not a production approval.",
        "- Command: `python underwriting_pipeline/ai/eval_gold.py`",
        "- Scored with `prepare.process_submission` on `simulation/inbox` before this round's producer replies.",
        "",
        "## How a hit is counted",
        "",
        "- named_insured and a single premises address must match the gold string.",
        "- SUB-014 premises is a hit only when both addresses are stored with their sources.",
        "- operations is a hit when every gold content word (length 4+, or a number) appears in the extracted operations text. Gold lines are class labels, not a second copy of the ACORD sentence.",
        "- loss_run_valued_through is a hit when a gold 'no loss-runs' line stays null, and a gold 'missing: none' line has a value. A no-known-loss letter stays null.",
        "- schedule_request is a hit when the draft asks for a location schedule only if the gold missing line says the schedule is absent.",
        "- conflict_fields is the set of disagreeing fields. conflict_values checks the gold numbers and which file they came from.",
        "- resolution is one row per open gold conflict (3 rows across SUB-014 and SUB-015). A hit means that row is unresolved and resolved_value is null. Both values stay.",
        "- restaurant_questions is scored only where the gold says to ask the five industry items.",
        "- citation is a hit when every extracted value that has a character span matches that span in the source file.",
        "- carrier_route uses deliverables/head-of-underwriting/carrier-appetite.md: Carrier A office/dry retail/light wholesale at TIV <= $5M; Carrier B restaurants and light contractors with clean runs; bars, nightclubs, fireworks are no-match. An open conflict or a missing loss run is hold, not a decline.",
        "",
        "## Per-field accuracy",
        "",
        "| Field | Correct |",
        "|---|---|",
    ]
    for key in tallies:
        lines.append(f"| {key} | {frac(key)} |")
    lines.extend(["", "## Per submission", ""])
    for item in details:
        misses = [key for key, hit in item["hits"].items() if hit is False]
        lines.append(
            f"- {item['submission']}: route {item['routed']} (gold {item['expected_route']}). "
            + ("Misses: " + ", ".join(misses) if misses else "No field misses.")
        )
    lines.extend(
        [
            "",
            "## Not in this score",
            "",
            "effective_date, sales, TIV, construction, and year built are extracted and cited, and the gold files do not state an expected value for them, so they are not in the accuracy denominator.",
            "",
        ]
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines))
    (OUT.with_suffix(".json")).write_text(json.dumps(details, indent=2) + "\n")
    print(OUT)
    for key in tallies:
        print(f"{key}: {frac(key)}")


if __name__ == "__main__":
    main()
