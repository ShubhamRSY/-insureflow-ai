#!/usr/bin/env python3
"""Shim — use scripts/ops/e2e_test.py."""

import runpy
import sys
from pathlib import Path

sys.argv[0] = str(Path(__file__).resolve().parent / "ops" / "e2e_test.py")
runpy.run_path(sys.argv[0], run_name="__main__")
