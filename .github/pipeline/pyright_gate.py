"""Pyright gate for the underwriting pipeline: no new type error.

The pipeline has known type errors, mostly in underwriting_pipeline/ai/ (changes need an approved P-###) and in
frozen eval_holdout_*.py scorers (never edited). They are counted per file and rule in pyright_baseline.json.
CI fails when any count goes up. When a cleanup lowers a count, run with --write to lower the baseline.

    pyright --outputjson underwriting_pipeline/ deliverables/senior-test-engineer/lint_holdout.py > out.json
    python .github/pipeline/pyright_gate.py out.json            # check
    python .github/pipeline/pyright_gate.py out.json --write    # lower the baseline after a cleanup
"""

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASELINE = Path(__file__).with_name("pyright_baseline.json")


def counts(report: dict) -> Counter:
    return Counter(
        f"{Path(d['file']).resolve().relative_to(ROOT)} {d.get('rule', '?')}"
        for d in report["generalDiagnostics"]
        if d["severity"] == "error"
    )


def main() -> int:
    now = counts(json.loads(Path(sys.argv[1]).read_text()))
    if "--write" in sys.argv:
        BASELINE.write_text(json.dumps(dict(sorted(now.items())), indent=1) + "\n")
        print(f"baseline written: {sum(now.values())} errors")
        return 0
    base = json.loads(BASELINE.read_text())
    new = {key: n - base.get(key, 0) for key, n in now.items() if n > base.get(key, 0)}
    for key, extra in sorted(new.items()):
        print(f"NEW pyright error: {key} (+{extra})")
    print(f"pyright: {sum(now.values())} errors, baseline {sum(base.values())}, new {sum(new.values())}")
    return 1 if new else 0


if __name__ == "__main__":
    assert counts({"generalDiagnostics": [{"file": str(ROOT / "a.py"), "severity": "error", "rule": "r"}]}) == Counter({"a.py r": 1})
    sys.exit(main())
