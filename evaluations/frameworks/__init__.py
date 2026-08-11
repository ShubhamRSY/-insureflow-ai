"""Four-framework evaluation harnesses: deepeval, promptfoo, Arize Phoenix, and the shared runner.

Import harnesses lazily via `evaluations.frameworks.suite_runner` (or the
individual modules) — this package must stay a cheap import so scheduled and CI
runners can load it without pulling the optional framework SDKs.
"""

from __future__ import annotations

__all__ = [
    "suite_runner",
    "deepeval_suite",
    "promptfoo_suite",
    "phoenix_suite",
    "phoenix_tracing",
]
