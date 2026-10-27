"""Tests for the pipeline workbench. No model calls, no writes to real team files.

Run from the repo root: python -m pytest tests/pipeline -q
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for folder in ("underwriting_pipeline/ai", "underwriting_pipeline/app"):
    path = str(ROOT / folder)
    if path not in sys.path:
        sys.path.insert(0, path)
