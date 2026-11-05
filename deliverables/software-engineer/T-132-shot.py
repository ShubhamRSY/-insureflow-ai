#!/usr/bin/env python3
"""T-132 (P-084, D-165): render the workbench page with no cards to a temp folder (D-069) so the What's new panel shows the P-084 line.
Run: python deliverables/software-engineer/T-132-shot.py <temp-folder>, then screenshot the html with playwright."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for sub in ("app", "ai", "models"):
    sys.path.insert(0, str(ROOT / "underwriting_pipeline" / sub))
import workbench  # noqa: E402

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
(out / "T-132-whats-new.html").write_text(workbench.render([], None))
