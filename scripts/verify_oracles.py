#!/usr/bin/env python3
"""Verify oracle live wiring without printing secret values.

Usage:
  PYTHONPATH=src python scripts/verify_oracles.py
  PYTHONPATH=src python scripts/verify_oracles.py --ping
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _mask(val: str) -> str:
    v = (val or "").strip()
    if not v:
        return "MISSING"
    if "YOUR-" in v or v.upper().startswith("REPLACE"):
        return "PLACEHOLDER"
    return f"SET({len(v)} chars)"


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=True)

    parser = argparse.ArgumentParser()
    parser.add_argument("--ping", action="store_true", help="HTTP health_check when configured")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    import os

    from insureflow.oracles.factory import (
        build_aplus_client,
        build_cat_client,
        build_clue_client,
        build_ncci_client,
    )
    from insureflow.pilot.sandbox_readiness import assess_sandbox_readiness

    specs = [
        ("CLUE", "CLUE_API_KEY", "CLUE_API_URL", build_clue_client, True),
        ("A-PLUS", "APLUS_API_KEY", "APLUS_API_URL", build_aplus_client, True),
        ("NCCI", "NCCI_API_KEY", "NCCI_API_URL", build_ncci_client, False),
        ("CAT", "CAT_API_KEY", "CAT_API_URL", build_cat_client, False),
    ]

    feeds = []
    blockers = []
    for name, key_env, url_env, builder, required in specs:
        key = (os.getenv(key_env) or "").strip()
        url = (os.getenv(url_env) or "").strip()
        key_ok = bool(key) and "YOUR-" not in key and not key.upper().startswith("REPLACE")
        url_ok = bool(url) and "YOUR-" not in url
        client = builder()
        mode = getattr(client, "_resolved_mode", lambda: "unknown")()
        reachable = None
        if args.ping and key_ok and url_ok:
            try:
                health = client.http.health_check()
                reachable = bool(health.get("reachable"))
            except Exception as exc:  # noqa: BLE001
                reachable = False
                mode = f"error:{exc}"

        status = "ready" if key_ok and url_ok and (reachable is not False) else ("degraded" if key_ok and reachable is False else "simulated")
        row = {
            "name": name,
            "required_for_pilot": required,
            "key": _mask(key),
            "url": url if url_ok else _mask(url),
            "resolved_mode": mode,
            "reachable": reachable,
            "status": status,
        }
        feeds.append(row)
        if required and status != "ready":
            blockers.append(f"{name}: set {key_env} + {url_env}")

    report = assess_sandbox_readiness(ping=args.ping)
    out = {
        "oracle_mode": (os.getenv("ORACLE_MODE") or "").strip() or "auto",
        "pilot_shadow_mode": (os.getenv("PILOT_SHADOW_MODE") or "").strip() or "(default)",
        "sandbox_overall": report.get("overall"),
        "feeds": feeds,
        "blockers": blockers,
        "next": ("Paste sandbox keys into .env then re-run with --ping" if blockers else "Required oracles configured — verify GET /pipeline/ecosystem/status"),
        "ok": not blockers,
    }

    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"ORACLE_MODE={out['oracle_mode']}  PILOT_SHADOW_MODE={out['pilot_shadow_mode']}")
        print(f"Sandbox overall: {out['sandbox_overall']}")
        print()
        for f in feeds:
            req = "*" if f["required_for_pilot"] else " "
            print(f"[{req}] {f['name']:<8} status={f['status']:<10} mode={f['resolved_mode']:<12} key={f['key']:<16} url={f['url']}")
        print()
        if blockers:
            print("BLOCKERS (required for live loss history):")
            for b in blockers:
                print(f"  - {b}")
            print()
            print("Paste into .env then:")
            print("  PYTHONPATH=src python scripts/verify_oracles.py --ping")
        else:
            print("OK — required oracle keys present.")
            if not args.ping:
                print("Tip: re-run with --ping to confirm vendor hosts are reachable.")

    return 0 if out["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
