#!/usr/bin/env python3
"""Run full end-to-end tests against InsureFlow API and pipelines.

Examples:
  python scripts/e2e_test.py                    # live server :8002
  python scripts/e2e_test.py --in-process       # TestClient (no server needed)
  python scripts/e2e_test.py --port 8002 --json
  python cli.py e2e --fast
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from insureflow.e2e.runner import run_inprocess, run_live  # noqa: E402


def _print_report(report: dict) -> None:
    print("\n" + "=" * 60)
    print("InsureFlow E2E Test Report")
    print("=" * 60)
    for row in report["results"]:
        mark = "PASS" if row["passed"] else "FAIL"
        ms = row.get("duration_ms", 0)
        line = f"  [{mark}] {row['name']}"
        if ms:
            line += f" ({ms:.0f}ms)"
        print(line)
        if row.get("detail") and (not row["passed"] or row["detail"] != "ok"):
            print(f"         {row['detail']}")
    print("-" * 60)
    print(f"  Total: {report['total']}  Passed: {report['passed']}  Failed: {report['failed']}")
    print("=" * 60)
    if report["success"]:
        print("  ALL TESTS PASSED")
    else:
        print("  SOME TESTS FAILED")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="InsureFlow end-to-end test suite")
    parser.add_argument("--port", type=int, default=8002, help="API port for live tests")
    parser.add_argument(
        "--base-url", default="", help="Override base URL (e.g. http://127.0.0.1:8002)"
    )
    parser.add_argument(
        "--in-process", action="store_true", help="Use FastAPI TestClient (no live server)"
    )
    parser.add_argument("--use-llm", action="store_true", help="Enable LLM in sync pipeline tests")
    parser.add_argument("--fast", action="store_true", help="Skip connector pull tests")
    parser.add_argument(
        "--no-browser", action="store_true", help="Skip Playwright browser UI tests"
    )
    parser.add_argument("--no-celery", action="store_true", help="Skip Celery worker mortgage test")
    parser.add_argument(
        "--headed", action="store_true", help="Run browser tests with visible window"
    )
    parser.add_argument("--timeout", type=int, default=180, help="Job poll timeout seconds")
    parser.add_argument("--json", action="store_true", help="Print JSON report only")
    args = parser.parse_args(argv)

    kwargs = {
        "use_llm": args.use_llm,
        "test_connectors": not args.fast,
        "test_browser": not args.no_browser,
        "test_celery": not args.no_celery,
        "browser_headless": not args.headed,
        "job_timeout": args.timeout,
    }

    if args.in_process:
        report = run_inprocess(**kwargs)
    else:
        base = args.base_url or f"http://127.0.0.1:{args.port}"
        report = run_live(base_url=base, **kwargs)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_report(report)

    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
