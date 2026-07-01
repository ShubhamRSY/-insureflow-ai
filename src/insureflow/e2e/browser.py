"""Browser UI click-through tests via Playwright."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


@dataclass
class BrowserResult:
    name: str
    passed: bool
    detail: str = ""
    duration_ms: float = 0.0


def _step(name: str, fn) -> BrowserResult:
    t0 = time.perf_counter()
    try:
        detail = fn() or "ok"
        return BrowserResult(name=name, passed=True, detail=detail, duration_ms=(time.perf_counter() - t0) * 1000)
    except Exception as exc:
        return BrowserResult(
            name=name,
            passed=False,
            detail=str(exc) or repr(exc),
            duration_ms=(time.perf_counter() - t0) * 1000,
        )


def run_browser_tests(
    base_url: str,
    *,
    username: str,
    password: str,
    headless: bool = True,
) -> dict[str, Any]:
    """Exercise dashboard login and main navigation in a real browser."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        return {
            "passed": 0,
            "failed": 1,
            "total": 1,
            "success": False,
            "results": [
                {
                    "name": "Playwright import",
                    "passed": False,
                    "detail": f"Install playwright: pip install playwright && playwright install chromium ({exc})",
                    "duration_ms": 0,
                }
            ],
        }

    dashboard = f"{base_url.rstrip('/')}/dashboard/"
    results: list[BrowserResult] = []

    try:
        urlopen(f"{base_url.rstrip('/')}/health", timeout=5)
    except URLError as exc:
        return {
            "passed": 0,
            "failed": 1,
            "total": 1,
            "success": False,
            "results": [
                {
                    "name": "Browser preflight",
                    "passed": False,
                    "detail": str(exc),
                    "duration_ms": 0,
                },
            ],
        }

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        def _main_heading() -> str:
            page.wait_for_selector("main h1", timeout=10000)
            return page.locator("main h1").first.inner_text()

        def load_dashboard() -> str:
            page.goto(dashboard, wait_until="networkidle", timeout=30000)
            page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
            page.reload(wait_until="networkidle", timeout=30000)
            assert page.locator("text=InsureFlow AI").count() > 0
            return "shell loaded (session cleared)"

        def login_flow() -> str:
            if page.locator(f"aside >> text={username}").count() == 0:
                page.get_by_role("button", name="Sign In").first.click()
                page.wait_for_selector('input[name="username"]', timeout=5000)
                pwd = page.locator('input[name="password"]')
                assert pwd.get_attribute("type") == "password"
                page.get_by_role("button", name="Show password").click()
                assert pwd.get_attribute("type") == "text"
                page.get_by_role("button", name="Hide password").click()
                page.locator('input[name="username"]').fill(username)
                pwd.fill(password)
                page.locator("form").get_by_role("button", name="Sign In", exact=True).click()
                page.wait_for_selector(f"aside >> text={username}", timeout=15000)
            assert page.locator(f"aside >> text={username}").count() > 0
            return f"logged in as {username} (password toggle ok)"

        def nav_system() -> str:
            page.get_by_role("link", name="System Health").click()
            heading = _main_heading()
            assert "System" in heading
            return heading

        def nav_insurance() -> str:
            page.get_by_role("link", name="Insurance").click()
            heading = _main_heading()
            assert "Insurance" in heading
            assert page.locator("text=Connect a document source").count() > 0
            return heading

        def nav_mortgage() -> str:
            page.get_by_role("link", name="Mortgage").click()
            heading = _main_heading()
            assert "Mortgage" in heading
            return heading

        def nav_workflow() -> str:
            page.get_by_role("link", name="UW Sign-off").click()
            heading = _main_heading()
            assert "Sign-off" in heading
            return heading

        def nav_settings() -> str:
            page.get_by_role("link", name="Settings").click()
            heading = _main_heading()
            assert "Settings" in heading
            return heading

        def refresh_button() -> str:
            page.get_by_role("link", name="Overview").click()
            page.get_by_role("button", name="Refresh").click()
            page.wait_for_timeout(500)
            assert "Dashboard" in _main_heading()
            return "refreshed"

        steps = [
            ("Browser: load dashboard", load_dashboard),
            ("Browser: login + password visibility", login_flow),
            ("Browser: navigate System Health", nav_system),
            ("Browser: navigate Insurance", nav_insurance),
            ("Browser: navigate Mortgage", nav_mortgage),
            ("Browser: navigate UW Sign-off", nav_workflow),
            ("Browser: navigate Settings", nav_settings),
            ("Browser: refresh dashboard", refresh_button),
        ]

        for name, fn in steps:
            results.append(_step(name, fn))

        context.close()
        browser.close()

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    return {
        "passed": passed,
        "failed": failed,
        "total": len(results),
        "success": failed == 0,
        "results": [
            {
                "name": r.name,
                "passed": r.passed,
                "detail": r.detail,
                "duration_ms": round(r.duration_ms, 1),
            }
            for r in results
        ],
    }
