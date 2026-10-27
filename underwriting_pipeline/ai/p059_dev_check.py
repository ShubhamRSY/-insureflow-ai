"""P-059 (D-111) self-check on development files SUB-001..173 (no T-104 file, no model call, no cache).
For each dev application with a Cooking, Hood or Line of business line it builds two answers from the file itself:
  A = the "Operations:" line only (what the extractor copied before P-059), B = A plus every stated line (what a complete answer carries).
B must not be flagged (false flags); A is flagged by the new check where the other lines add an item. Run: .venv/bin/python underwriting_pipeline/ai/p059_dev_check.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prepare  # noqa: E402

INBOX = Path(__file__).resolve().parents[2] / "simulation" / "inbox"
LINE = lambda label, text: next((m.group(1).strip() for m in re.finditer(rf"(?im)^{label}\s*:\s*(.+)$", text)), "")


def before(value: str, text: str) -> list[str]:
    """The check as it was before P-059: the word list only."""
    extra, prepare.OPS_EXTRA = prepare.OPS_EXTRA, ()
    try:
        return prepare.ops_missing(value, text)
    finally:
        prepare.OPS_EXTRA = extra


def main() -> int:
    rows, false_flags = [], []
    for n in range(1, 174):
        app = INBOX / f"SUB-{n:03d}" / "application.md"
        if not app.exists():
            continue
        text = app.read_text()
        cook, hood, lob = LINE(r"cooking operations", text), LINE(r"hood[\w &/-]*", text), LINE(r"line of business", text)
        ops = LINE(r"(?:description of )?operations", text)
        if not ops or not (cook or hood):
            continue
        full = " ".join([ops, cook, hood, lob])
        a_old = before(ops, text)
        extra = prepare.ops_line_missing(ops, text) + prepare.ops_missing(ops, text)
        b = prepare.ops_missing(full, text) + prepare.ops_line_missing(full, text)
        rows.append((f"SUB-{n:03d}", a_old, [m for m in extra if m not in a_old], b))
        if b:
            false_flags.append((f"SUB-{n:03d}", b))
    caught = [r for r in rows if r[2]]
    print(f"{len(rows)} dev applications with a cooking or hood line")
    print(f"A (Operations line only): {sum(bool(r[1]) for r in rows)} flagged by the word list before P-059; {len(caught)} gain at least one new item")
    for sid, _, new, _ in caught:
        print(f"  {sid} new: {new}")
    print(f"B (all lines carried): {len(false_flags)} flagged (must be 0)")
    for sid, b in false_flags:
        print(f"  {sid} B flagged: {b}")
    return 1 if false_flags else 0


if __name__ == "__main__":
    sys.exit(main())
