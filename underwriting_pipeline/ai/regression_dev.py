"""Score current code on development sets SUB-017 through SUB-076.

Writes a new report only. Does not touch the official hold-out score files.

Run: python underwriting_pipeline/ai/regression_dev.py
"""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else (
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


def tally(rows: list[dict]) -> dict:
    counted: dict[str, dict[str, int]] = {}
    for row in rows:
        for field, mark in row["checks"].items():
            bucket = counted.setdefault(field, {})
            label = "hit" if mark is True else "miss" if mark is False else str(mark)
            bucket[label] = bucket.get(label, 0) + 1
    return counted


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
            # A failed model call is not a score of the code: try it again, and keep the error if it never succeeds.
            for attempt in range(1, 4):
                row = module.score_one(sid)
                if not row.get("error"):
                    break
                time.sleep(60)
            rows.append(
                {
                    "submission": sid,
                    "checks": row["checks"],
                    "name": row.get("extracted_named_insured"),
                    "error": row.get("error"),
                    "attempts": attempt,
                }
            )
            print(sid, row.get("error") or "ok", flush=True)
        done["bands"].append({"band": band, "counted": tally(rows), "rows": rows})
        OUT.write_text(json.dumps(done, indent=2) + "\n")
        print("band", band, done["bands"][-1]["counted"], flush=True)
    print(OUT)


if __name__ == "__main__":
    main()
