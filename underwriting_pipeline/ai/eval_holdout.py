"""Score SUB-017 through SUB-026 against gold written before this run.

Does not modify prepare.py. Synthetic only. Not a production approval.

Run: python underwriting_pipeline/ai/eval_holdout.py
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
OUT_MD = ROOT / "deliverables" / "ai-engineer" / "evals" / "SUB-017-026-holdout.md"
OUT_JSON = ROOT / "deliverables" / "ai-engineer" / "evals" / "SUB-017-026-holdout.json"
IDS = [f"SUB-{n:03d}" for n in range(17, 27)]
FIELDS = (
    "named_insured",
    "premises",
    "operations",
    "sales",
    "tiv",
    "construction",
    "year_built",
    "loss_runs",
    "conflict",
    "status",
)


def parse_gold(text: str) -> dict:
    out = {}
    for raw in text.splitlines():
        if not raw.startswith("- ") or ":" not in raw:
            continue
        key, val = raw[2:].split(":", 1)
        out[key.strip().lower()] = val.strip()
    return out


def digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def words(text: str) -> list[str]:
    stop = {"with", "and", "the", "that", "this", "from", "unit"}
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in stop and (len(w) >= 4 or w.isdigit())]


def field_map(report: dict) -> dict:
    return {row["field_id"]: row for row in report["fields"]}


def hit_named(gold: str, got: str | None) -> bool:
    return bool(got) and got.strip() == gold


def hit_premises(gold: str, report: dict, got: str | None) -> bool:
    if gold.lower().startswith("both"):
        blob = json.dumps(report["conflicts"])
        nums = re.findall(r"\d+", gold)
        return len(nums) >= 2 and all(n in blob for n in nums[:2])
    return bool(got) and got.strip() == gold


def hit_ops(gold: str, got: str | None) -> bool:
    if not got:
        return False
    need = words(gold)
    have = set(words(got))
    return bool(need) and all(w in have for w in need)


def hit_number(gold: str, got: str | None) -> bool:
    if gold.strip() == "0":
        return got is not None and digits(got) in {"", "0"}
    return bool(got) and digits(gold) == digits(got) and digits(gold) != ""


def hit_text(gold: str, got: str | None) -> bool:
    return bool(got) and gold.lower() in got.lower()


def hit_loss(gold: str, got: str | None) -> bool:
    if gold.lower().startswith("missing"):
        return not got
    date = re.search(r"20\d\d-\d\d-\d\d", gold)
    return bool(got and date and date.group(0) in got)


def hit_conflict(gold: str, report: dict) -> bool:
    if gold.lower() == "none":
        return not [c for c in report["conflicts"] if c.get("resolution") != "resolved"]
    blob = json.dumps(report["conflicts"]).lower()
    if "square" in gold.lower():
        return "square_feet" in blob and "3000" in blob and "4500" in blob
    if "premises" in gold.lower() or "address" in gold.lower():
        return "premises_address" in blob and "15 perez" in blob and "51 perez" in blob
    return False


def hit_status(gold: str, report: dict) -> bool:
    complete = gold.lower().startswith("complete")
    return report["complete"] is complete


def score_one(sid: str) -> dict:
    gold = parse_gold((GOLD / f"{sid}.md").read_text())
    folder = INBOX / sid
    report = prepare.process_submission(folder)
    got = field_map(report)
    ignored = sorted(
        p.name for p in folder.iterdir() if p.is_file() and p.suffix.lower() not in {".md", ".csv"}
    )
    checks = {
        "named_insured": hit_named(gold["named insured"], got["named_insured"]["value"]),
        "premises": hit_premises(gold["premises"], report, got["premises_address"]["value"]),
        "operations": hit_ops(gold["operations"], got["operations"]["value"]),
        "sales": hit_number(gold["sales"], got["sales_or_payroll"]["value"]),
        "tiv": hit_number(gold["tiv"], got["tiv_building"]["value"]),
        "construction": hit_text(gold["construction"], got["construction"]["value"]),
        "year_built": hit_number(gold["year built"], got["year_built"]["value"]),
        "loss_runs": hit_loss(gold["loss runs"], got["loss_run_valued_through"]["value"]),
        "conflict": hit_conflict(gold["conflict"], report),
        "status": hit_status(gold["status"], report),
    }
    return {
        "submission": sid,
        "format": gold.get("format"),
        "ignored_files": ignored,
        "extracted_named_insured": got["named_insured"]["value"],
        "complete": report["complete"],
        "missing": report["missing"],
        "conflicts": [c["field"] for c in report["conflicts"]],
        "checks": checks,
        "correct": sum(checks.values()),
        "scored": len(checks),
    }


def main() -> None:
    rows = [score_one(sid) for sid in IDS]
    totals = {field: 0 for field in FIELDS}
    for row in rows:
        for field, ok in row["checks"].items():
            totals[field] += int(ok)
    n = len(rows)
    payload = {"submissions": rows, "per_field": totals, "n": n}
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n")
    lines = [
        "# Hold-out extraction score — SUB-017 through SUB-026",
        "",
        "- Author: @ai-engineer",
        "- prepare.py was not edited for this run.",
        "- Gold files were already in deliverables/senior-underwriter/gold-set/.",
        "- Synthetic. Not a production approval.",
        "- Command: `python underwriting_pipeline/ai/eval_holdout.py`",
        "",
        "A hit means the unchanged extractor matched that gold line. PDF and Excel files are ignored by prepare.process_submission, which only reads .md and .csv.",
        "",
        "## Per-field accuracy",
        "",
        "| Field | Correct |",
        "|---|---|",
    ]
    for field in FIELDS:
        lines.append(f"| {field} | {totals[field]}/{n} |")
    lines.append("")
    lines.append("## Per submission")
    lines.append("")
    for row in rows:
        missed = [k for k, ok in row["checks"].items() if not ok]
        lines.append(
            f"- {row['submission']} ({row['format']}): {row['correct']}/{row['scored']}. "
            f"Ignored: {', '.join(row['ignored_files']) or 'none'}. "
            f"Misses: {', '.join(missed) or 'none'}."
        )
    lines.append("")
    OUT_MD.write_text("\n".join(lines))
    print(OUT_MD)
    for field in FIELDS:
        print(f"{field} {totals[field]}/{n}")


if __name__ == "__main__":
    main()
