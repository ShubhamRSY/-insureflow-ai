#!/usr/bin/env python3
"""Deploy smoke checks for pilot/sandbox readiness (no live vendor calls required)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    errors: list[str] = []

    # Version surface
    try:
        import tomllib

        data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        version = data["project"]["version"]
    except Exception as exc:  # noqa: BLE001
        errors.append(f"pyproject version unreadable: {exc}")
        version = "?"

    from insureflow.pilot.sandbox_readiness import assess_sandbox_readiness, is_shadow_mode
    from insureflow.pilot.auto_redact import redact_blocking_categories_in_text
    from insureflow.pilot.email_intake import documents_to_pilot_package

    report = assess_sandbox_readiness(ping=False)
    if "overall" not in report:
        errors.append("sandbox readiness missing overall")

    sample = "Applicant SSN 123-45-6789 and email broker@example.com"
    redacted = redact_blocking_categories_in_text(sample)
    if "123-45-6789" in redacted:
        errors.append("auto-redact left SSN intact")
    if "broker@example.com" not in redacted:
        errors.append("auto-redact should leave broker email (warn-only)")

    tmp = ROOT / ".smoke_pilot_tmp"
    try:
        result = documents_to_pilot_package(
            [{"filename": "acord.xml", "content": "<ACORD>SSN 123-45-6789</ACORD>", "encoding": "utf-8"}],
            partner="smoke",
            submission_id="smoke-1",
            root=tmp,
            auto_redact=True,
        )
        after = (result.get("redaction") or {}).get("after") or {}
        if not after.get("ok_to_run"):
            errors.append("email package auto-redact did not clear blocking PII")
    finally:
        import shutil

        if tmp.exists():
            shutil.rmtree(tmp)

    out = {
        "ok": not errors,
        "version": version,
        "shadow_mode": is_shadow_mode(),
        "sandbox_overall": report.get("overall"),
        "required_ready": f"{report.get('required_ready')}/{report.get('required_total')}",
        "errors": errors,
        "railway_healthcheck": "/health",
        "hint": "Set IMAP_* for email ingest; keep PILOT_SHADOW_MODE=true until Guidewire live",
    }
    print(json.dumps(out, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
