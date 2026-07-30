#!/usr/bin/env python3
"""Shim — use scripts/pilot/verify_oracles.py."""

import runpy
import sys
from pathlib import Path

sys.argv[0] = str(Path(__file__).resolve().parent / "pilot" / "verify_oracles.py")
runpy.run_path(sys.argv[0], run_name="__main__")
